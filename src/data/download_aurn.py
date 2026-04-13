"""
D1 — Descarga e integración de estaciones DEFRA AURN
======================================================
Las estaciones AURN (Automatic Urban and Rural Network) tienen PM2.5/PM10
con calibración trazable — calidad mucho mayor que los sensores de bajo coste.
Se integran como sensores adicionales en el dataset de entrenamiento.

Estaciones en Liverpool / Merseyside:
  - Liverpool Centre    (LCBO)  — lat 53.4097, lon -2.9779  [PM2.5, PM10]
  - Liverpool Speke     (LISP)  — lat 53.3458, lon -2.8658  [PM10]
  - Wirral Tranmere     (WIRT)  — lat 53.3775, lon -3.0085  [PM2.5, PM10]
  - Wigan Centre        (WGCN)  — lat 53.5425, lon -2.6378  [PM2.5]  (borde área)

Fuente: https://uk-air.defra.gov.uk/data/
API:    https://uk-air.defra.gov.uk/data/API_docs.pdf

Salida:
  data/raw/aurn_liverpool.csv        → datos horarios descargados
  data/interim/aurn_annual.csv       → medias anuales (modo annual)
  data/interim/aurn_monthly.csv      → medias mensuales (modo monthly)

Uso posterior: añadir filas de AURN a sensores_2024_agregados.csv /
               sensores_monthly.csv antes de feature_engineering.
"""

from pathlib import Path
import logging
import requests
import pandas as pd
import geopandas as gpd
import numpy as np
from io import StringIO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT     = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INT = ROOT / "data" / "interim"

AURN_STATIONS = {
    "LCBO": {"name": "Liverpool Centre",  "lat": 53.4097, "lon": -2.9779, "has_pm25": True,  "has_pm10": True},
    "LISP": {"name": "Liverpool Speke",   "lat": 53.3458, "lon": -2.8658, "has_pm25": False, "has_pm10": True},
    "WIRT": {"name": "Wirral Tranmere",   "lat": 53.3775, "lon": -3.0085, "has_pm25": True,  "has_pm10": True},
}

YEARS = [2024]

# API base de DEFRA — descarga CSV por estación y año
AURN_API = "https://uk-air.defra.gov.uk/data/csv_server.php"


def download_station_year(code: str, year: int) -> pd.DataFrame:
    """Descarga datos horarios de una estación AURN para un año dado."""
    params = {
        "site_id": code,
        "pollutant_ids": "10,11",  # 10=PM10, 11=PM2.5 (códigos DEFRA)
        "data_type": "hourly",
        "year": year,
        "format": "csv",
    }
    local_file = DATA_RAW / f"aurn_{code}_{year}.csv"
    if local_file.exists():
        log.info(f"    Usando caché local: {local_file}")
        return pd.read_csv(local_file, skiprows=4)

    try:
        r = requests.get(AURN_API, params=params, timeout=60)
        r.raise_for_status()
        # Los CSV de DEFRA tienen 4 líneas de cabecera de metadata
        df = pd.read_csv(StringIO(r.text), skiprows=4)
        df.to_csv(local_file, index=False)
        log.info(f"    Descargados {len(df)} registros para {code} {year}")
        return df
    except Exception as e:
        log.warning(f"    Fallo descarga {code} {year}: {e}")
        return pd.DataFrame()


def parse_aurn_csv(df: pd.DataFrame, station_code: str) -> pd.DataFrame:
    """Normaliza el formato CSV de DEFRA a columnas estándar."""
    if df.empty:
        return df

    df.columns = [c.strip() for c in df.columns]

    # Columna de fecha/hora
    time_col = next((c for c in df.columns if "date" in c.lower() or "time" in c.lower()), None)
    if time_col is None:
        log.warning(f"    No encontrada columna de tiempo en {station_code}")
        return pd.DataFrame()

    df["datetime"] = pd.to_datetime(df[time_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["datetime"])

    # Identificar columnas PM
    pm25_col = next((c for c in df.columns
                     if ("pm2" in c.lower() or "pm25" in c.lower()) and "flag" not in c.lower()), None)
    pm10_col = next((c for c in df.columns
                     if "pm10" in c.lower() and "flag" not in c.lower()), None)

    out = pd.DataFrame({"datetime": df["datetime"], "sensor_id": f"AURN_{station_code}"})

    if pm25_col:
        out["PM2.5"] = pd.to_numeric(df[pm25_col], errors="coerce")
    else:
        out["PM2.5"] = np.nan

    if pm10_col:
        out["PM10"] = pd.to_numeric(df[pm10_col], errors="coerce")
    else:
        out["PM10"] = np.nan

    out = out.dropna(subset=["PM2.5", "PM10"], how="all")
    return out


def main():
    log.info("=== D1: Descarga estaciones DEFRA AURN ===")

    all_hourly = []

    for code, info in AURN_STATIONS.items():
        log.info(f"  Estación {code} — {info['name']}")
        for year in YEARS:
            raw = download_station_year(code, year)
            parsed = parse_aurn_csv(raw, code)
            if not parsed.empty:
                parsed["lat"] = info["lon"]   # mismo convenio invertido que sensores del proyecto
                parsed["lon"] = info["lat"]
                all_hourly.append(parsed)

    if not all_hourly:
        log.error("No se obtuvieron datos AURN. Descarga manual necesaria.")
        log.info("  Instrucciones:")
        log.info("    1. Ve a https://uk-air.defra.gov.uk/data/")
        log.info("    2. Selecciona estaciones LCBO, LISP, WIRT")
        log.info("    3. Descarga datos horarios 2024 en formato CSV")
        log.info(f"    4. Guarda en {DATA_RAW} como aurn_LCBO_2024.csv, etc.")
        return

    df_all = pd.concat(all_hourly, ignore_index=True)
    df_all.to_csv(DATA_RAW / "aurn_liverpool.csv", index=False)
    log.info(f"  Datos horarios AURN guardados → {DATA_RAW / 'aurn_liverpool.csv'}")

    # ── Agregación anual ──────────────────────────────────────────────────────
    completeness = (
        df_all.groupby("sensor_id")[["PM2.5", "PM10"]]
        .apply(lambda x: x.notna().mean())
        .rename(columns={"PM2.5": "completeness_pm25", "PM10": "completeness_pm10"})
    )

    annual = (
        df_all.groupby(["sensor_id", "lat", "lon"])[["PM2.5", "PM10"]]
        .mean()
        .reset_index()
        .merge(completeness.reset_index(), on="sensor_id")
    )
    annual.to_csv(DATA_INT / "aurn_annual.csv", index=False, float_format="%.3f")
    log.info(f"  Medias anuales AURN → {DATA_INT / 'aurn_annual.csv'}")

    # ── Agregación mensual ────────────────────────────────────────────────────
    df_all["year_month"] = df_all["datetime"].dt.to_period("M").astype(str)
    monthly = (
        df_all.groupby(["sensor_id", "year_month", "lat", "lon"])[["PM2.5", "PM10"]]
        .mean()
        .reset_index()
    )
    monthly.to_csv(DATA_INT / "aurn_monthly.csv", index=False, float_format="%.3f")
    log.info(f"  Medias mensuales AURN → {DATA_INT / 'aurn_monthly.csv'}")

    log.info("\n  Resumen:")
    log.info(annual[["sensor_id", "PM2.5", "PM10",
                      "completeness_pm25", "completeness_pm10"]].to_string(index=False))


if __name__ == "__main__":
    main()
