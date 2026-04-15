"""
C4 — Densidad de población ONS Census 2021 a nivel LSOA
==========================================================
Fuente: ONS Open Geography Portal
  - Boundaries LSOA (Lower Layer Super Output Areas) 2021 para Merseyside
  - Tabla de población por LSOA (Census 2021, tabla TS001)

Salida: data/interim/population_density.csv
  Columnas: sensor_id, lsoa_code, population, area_km2, pop_density_km2

La densidad de población se añade a feature_engineering.py como
SENSOR_LEVEL_VAR — el sensor hereda la densidad del LSOA donde cae.
"""

from pathlib import Path
import logging
import requests
import zipfile
import io
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT     = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INT = ROOT / "data" / "interim"
LSOA_DIR = DATA_RAW / "lsoa_boundaries"
LSOA_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV  = DATA_INT / "population_density.csv"
SENSORS_GPKG = DATA_INT / "sensores_snapped.gpkg"

# ONS LSOA 2021 boundaries (England & Wales, simplified 200m)
LSOA_BOUNDARIES_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "LSOA_2021_EW_BSC_V4/FeatureServer/0/query?"
    "where=LSOA21NM+LIKE+%27Liverpool%25%27"
    "&outFields=LSOA21CD,LSOA21NM,Shape__Area"
    "&f=geojson"
)

# Census 2021 TS001 — Usual resident population (ONS bulk download)
CENSUS_POP_URL = (
    "https://static.ons.gov.uk/datasets/TS001/TS001-2021-1-filtered-2024-04-21T12:08:15Z.csv"
)


def download_lsoa_boundaries() -> gpd.GeoDataFrame:
    """Descarga los límites LSOA de Liverpool desde ONS."""
    local_file = LSOA_DIR / "lsoa_liverpool.gpkg"
    if local_file.exists():
        log.info(f"  Usando boundaries locales: {local_file}")
        return gpd.read_file(local_file)

    log.info("  Descargando boundaries LSOA de Liverpool (ONS ArcGIS) ...")
    try:
        r = requests.get(LSOA_BOUNDARIES_URL, timeout=60)
        r.raise_for_status()
        import tempfile, json
        gdf = gpd.read_file(io.BytesIO(r.content))
        gdf = gdf.to_crs("EPSG:27700")
        gdf.to_file(local_file, driver="GPKG")
        log.info(f"  Descargados {len(gdf)} LSOAs de Liverpool → {local_file}")
        return gdf
    except Exception as e:
        log.error(f"  Fallo descarga LSOA boundaries: {e}")
        return gpd.GeoDataFrame()


def download_census_population() -> pd.DataFrame:
    """Descarga tabla de población por LSOA del Census 2021."""
    local_file = DATA_RAW / "census_ts001_lsoa.csv"
    if local_file.exists():
        log.info(f"  Usando tabla de población local: {local_file}")
        return pd.read_csv(local_file)

    log.info("  Descargando tabla de población Census 2021 (ONS) ...")
    try:
        r = requests.get(CENSUS_POP_URL, timeout=120)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.to_csv(local_file, index=False)
        log.info(f"  Descargados {len(df)} LSOAs con población → {local_file}")
        return df
    except Exception as e:
        log.warning(f"  Fallo descarga Census TS001: {e}")
        log.info("  Instrucciones manuales:")
        log.info("    1. Ve a https://www.nomisweb.co.uk/census/2021/ts001")
        log.info("    2. Descarga por LSOA para Liverpool (E08000012)")
        log.info(f"    3. Guarda como {local_file}")
        return pd.DataFrame()


def assign_population_to_sensors(
    sensors: gpd.GeoDataFrame,
    lsoa: gpd.GeoDataFrame,
    pop: pd.DataFrame,
) -> pd.DataFrame:
    """Asigna a cada sensor la densidad de población del LSOA en que cae."""

    # Normalizar columnas de población
    pop.columns = [c.strip().lower() for c in pop.columns]
    lsoa_col = next((c for c in pop.columns if "lsoa" in c and "cd" in c), None)
    pop_col  = next((c for c in pop.columns if "count" in c or "population" in c or "resident" in c), None)

    if lsoa_col is None or pop_col is None:
        log.warning(f"  No se encontraron columnas esperadas en tabla de población: {pop.columns.tolist()}")
        # Fallback: usar área del LSOA sin datos de población
        lsoa["pop_density_km2"] = np.nan
    else:
        pop_clean = pop.rename(columns={lsoa_col: "LSOA21CD", pop_col: "population"})
        pop_clean["population"] = pd.to_numeric(pop_clean["population"], errors="coerce")
        lsoa = lsoa.merge(pop_clean[["LSOA21CD", "population"]], on="LSOA21CD", how="left")
        # Área en km²
        lsoa["area_km2"]        = lsoa.geometry.area / 1e6
        lsoa["pop_density_km2"] = lsoa["population"] / lsoa["area_km2"]

    # Spatial join: sensor → LSOA
    sensors_proj = sensors.to_crs(lsoa.crs)
    joined = gpd.sjoin(sensors_proj, lsoa[["LSOA21CD", "LSOA21NM", "population",
                                           "area_km2", "pop_density_km2", "geometry"]],
                       how="left", predicate="within")

    sid_col = "sensor_id" if "sensor_id" in joined.columns else joined.index.name
    result = joined[[sid_col, "LSOA21CD", "LSOA21NM", "population",
                     "area_km2", "pop_density_km2"]].copy()
    result = result.rename(columns={sid_col: "sensor_id"})

    n_matched = result["pop_density_km2"].notna().sum()
    log.info(f"  Sensores con densidad de población: {n_matched}/{len(result)}")
    return result


def main():
    import numpy as np
    log.info("=== C4: Densidad de población ONS 2021 ===")

    sensors = gpd.read_file(SENSORS_GPKG)
    lsoa    = download_lsoa_boundaries()
    pop     = download_census_population()

    if lsoa.empty:
        log.error("  Sin datos LSOA — descarga manual necesaria.")
        return

    result = assign_population_to_sensors(sensors, lsoa, pop)
    result.to_csv(OUT_CSV, index=False, float_format="%.2f")
    log.info(f"  Guardado → {OUT_CSV}")
    log.info(f"\n{result.to_string(index=False)}")


if __name__ == "__main__":
    main()
