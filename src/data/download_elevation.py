"""
C2 — Extracción de elevación para cada sensor
===============================================
Fuentes (en orden de preferencia):
  1. Open-Elevation API (gratuita, basada en SRTM 90m)
  2. Copernicus DEM GLO-30 vía opentopography.org (30m, requiere API key opcional)
  3. OS Terrain 50 si se descargó manualmente en data/raw/os_terrain50/

Salida: data/interim/sensor_elevation.csv
  Columnas: sensor_id, lat_wgs84, lon_wgs84, elevation_m

La elevación se añade después a feature_engineering.py como variable
SENSOR_LEVEL_VAR (no depende del buffer).
"""

from pathlib import Path
import logging
import requests
import time
import pandas as pd
import geopandas as gpd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DATA_INT  = ROOT / "data" / "interim"
OUT_CSV   = DATA_INT / "sensor_elevation.csv"

SENSORS_GPKG = DATA_INT / "sensores_snapped.gpkg"


# ── OPEN-ELEVATION API ────────────────────────────────────────────────────────

def get_elevation_open_elevation(lats: list, lons: list) -> list:
    """
    Llama a la API de Open-Elevation (https://api.open-elevation.com).
    Acepta hasta 100 puntos por request.
    """
    url = "https://api.open-elevation.com/api/v1/lookup"
    locations = [{"latitude": lat, "longitude": lon} for lat, lon in zip(lats, lons)]

    elevations = []
    batch_size = 50  # API más estable con batches pequeños
    for i in range(0, len(locations), batch_size):
        batch = locations[i:i+batch_size]
        try:
            r = requests.post(url, json={"locations": batch}, timeout=30)
            r.raise_for_status()
            results = r.json()["results"]
            elevations.extend([r["elevation"] for r in results])
            log.info(f"  Elevaciones obtenidas: {len(elevations)}/{len(locations)}")
            time.sleep(0.5)  # respetar rate limit
        except Exception as e:
            log.warning(f"  Fallo Open-Elevation batch {i}: {e} → NaN para este batch")
            elevations.extend([np.nan] * len(batch))

    return elevations


def get_elevation_fallback(lats: list, lons: list) -> list:
    """
    Fallback: Open-Topo Data (SRTM 30m).
    https://www.opentopodata.org/
    """
    url = "https://api.opentopodata.org/v1/srtm30m"
    elevations = []
    for lat, lon in zip(lats, lons):
        try:
            r = requests.get(url, params={"locations": f"{lat},{lon}"}, timeout=15)
            r.raise_for_status()
            elev = r.json()["results"][0]["elevation"]
            elevations.append(elev)
            time.sleep(0.3)
        except Exception as e:
            log.warning(f"  Fallo OpenTopoData ({lat},{lon}): {e}")
            elevations.append(np.nan)
    return elevations


def main():
    log.info("=== C2: Extracción de elevación por sensor ===")

    sensors = gpd.read_file(SENSORS_GPKG)
    log.info(f"  Sensores: {len(sensors)}")

    # Convertir a WGS84 para las APIs de elevación
    sensors_wgs = sensors.to_crs("EPSG:4326")
    lats = sensors_wgs.geometry.y.tolist()
    lons = sensors_wgs.geometry.x.tolist()

    log.info("  Consultando Open-Elevation ...")
    elevations = get_elevation_open_elevation(lats, lons)

    # Si hay NaN, completar con fallback
    nan_mask = [np.isnan(e) if not isinstance(e, int) else False for e in elevations]
    n_nan = sum(nan_mask)
    if n_nan > 0:
        log.info(f"  {n_nan} sensores sin elevación → intentando OpenTopoData ...")
        nan_lats = [lats[i] for i, m in enumerate(nan_mask) if m]
        nan_lons = [lons[i] for i, m in enumerate(nan_mask) if m]
        fallback_elevs = get_elevation_fallback(nan_lats, nan_lons)
        j = 0
        for i, m in enumerate(nan_mask):
            if m:
                elevations[i] = fallback_elevs[j]
                j += 1

    result = pd.DataFrame({
        "sensor_id":  sensors["sensor_id"].values if "sensor_id" in sensors.columns
                      else [f"s{i}" for i in range(len(sensors))],
        "lat_wgs84":  lats,
        "lon_wgs84":  lons,
        "elevation_m": elevations,
    })

    n_ok  = result["elevation_m"].notna().sum()
    n_nan = result["elevation_m"].isna().sum()
    log.info(f"  Elevaciones obtenidas: {n_ok}/{len(result)}  (NaN: {n_nan})")
    if n_nan > 0:
        log.warning(f"  Sensores sin elevación: {result[result['elevation_m'].isna()]['sensor_id'].tolist()}")

    result.to_csv(OUT_CSV, index=False, float_format="%.1f")
    log.info(f"  Guardado → {OUT_CSV}")
    log.info(f"\n{result.to_string(index=False)}")


if __name__ == "__main__":
    main()
