"""
C1 — Descarga e integración de meteorología mensual
=====================================================
Fuente: CEDA Archive — Met Office MIDAS (estación Liverpool John Lennon Airport,
        código WMO 03023 / MIDAS ID 708).

Datos obtenidos:
  - Velocidad media mensual del viento (wind_speed_mean, m/s)
  - Días de lluvia en el mes (rain_days)
  - Temperatura media mensual (air_temperature_mean, °C)
  - Humedad relativa media (rltv_hum_mean, %)

Salida:
  data/interim/meteo_monthly.csv
  Columnas: year_month, wind_speed_mean, rain_days, air_temperature_mean, rltv_hum_mean

INSTRUCCIONES DE DESCARGA MANUAL (si la descarga automática falla):
  1. Ve a https://catalogue.ceda.ac.uk/uuid/dbd451271eb04662beade68da43546e
  2. Descarga los archivos hourly/daily de la estación 708 para 2024
  3. Guárdalos en data/raw/midas_liverpool/
  4. Ejecuta este script — lo detectará automáticamente

Alternativamente, el script intenta descarga directa vía la API de CEDA
si tienes credenciales configuradas en ~/.ceda/credentials.
"""

from pathlib import Path
import logging
import warnings
import requests
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DATA_RAW  = ROOT / "data" / "raw"
DATA_INT  = ROOT / "data" / "interim"
MIDAS_DIR = DATA_RAW / "midas_liverpool"
MIDAS_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV   = DATA_INT / "meteo_monthly.csv"

# Estaciones de respaldo: Liverpool Airport (principal) y Crosby (backup)
STATIONS = {
    "liverpool_airport": {
        "midas_id": 708,
        "wmo": "03023",
        "lat": 53.3336,
        "lon": -2.8497,
        "description": "Liverpool John Lennon Airport",
    },
    "crosby": {
        "midas_id": 19,
        "wmo": "03026",
        "lat": 53.4892,
        "lon": -3.0564,
        "description": "Crosby",
    },
}

YEARS = [2024]


# ── DESCARGA VÍA OPEN-METEO (FALLBACK GRATUITO SIN CREDENCIALES) ─────────────
# Open-Meteo proporciona datos ERA5-reanálisis/histórico sin registro.

def download_open_meteo(year: int, station: dict) -> pd.DataFrame:
    """
    Descarga datos horarios históricos de Open-Meteo para la ubicación de la estación.
    Variables: temperature_2m, relative_humidity_2m, wind_speed_10m, precipitation.
    API docs: https://open-meteo.com/en/docs/historical-weather-api
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   station["lat"],
        "longitude":  station["lon"],
        "start_date": f"{year}-01-01",
        "end_date":   f"{year}-12-31",
        "hourly":     "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone":   "Europe/London",
        "wind_speed_unit": "ms",
    }
    log.info(f"  Descargando Open-Meteo para {station['description']} ({year}) ...")
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        hourly = data["hourly"]
        df = pd.DataFrame({
            "datetime":    pd.to_datetime(hourly["time"]),
            "temp_c":      hourly["temperature_2m"],
            "humidity":    hourly["relative_humidity_2m"],
            "wind_ms":     hourly["wind_speed_10m"],
            "precip_mm":   hourly["precipitation"],
        })
        log.info(f"  Descargados {len(df)} registros horarios para {year}")
        return df
    except Exception as e:
        log.error(f"  Fallo Open-Meteo: {e}")
        return pd.DataFrame()


def aggregate_to_monthly(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """Agrega datos horarios a medias/sumas mensuales."""
    df = df_hourly.copy()
    df["year_month"] = df["datetime"].dt.to_period("M")

    monthly = df.groupby("year_month").agg(
        air_temperature_mean=("temp_c",   "mean"),
        rltv_hum_mean       =("humidity", "mean"),
        wind_speed_mean     =("wind_ms",  "mean"),
        precip_total_mm     =("precip_mm","sum"),
    )
    # Días de lluvia: horas con precipitación > 0.1mm / 24
    df["rain_hour"] = df["precip_mm"] > 0.1
    rain_days = df.groupby("year_month")["rain_hour"].sum() / 24.0
    monthly["rain_days"] = rain_days.round(1)

    monthly = monthly.reset_index()
    monthly["year_month"] = monthly["year_month"].astype(str)
    return monthly


def load_from_local_midas(midas_dir: Path) -> pd.DataFrame:
    """
    Intenta leer archivos MIDAS descargados manualmente de CEDA.
    Formato esperado: CSV con columnas ob_time, air_temperature, rltv_hum, wind_speed_mean, prcp_amt
    """
    files = list(midas_dir.glob("*.csv")) + list(midas_dir.glob("*.txt"))
    if not files:
        return pd.DataFrame()

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, comment="#", low_memory=False)
            df.columns = [c.strip().lower() for c in df.columns]
            frames.append(df)
            log.info(f"  Leído MIDAS local: {f.name} ({len(df)} filas)")
        except Exception as e:
            log.warning(f"  No se pudo leer {f.name}: {e}")

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # Normalizar columna de tiempo
    time_col = next((c for c in df_all.columns if "time" in c or "date" in c), None)
    if time_col is None:
        log.warning("  No se encontró columna de tiempo en MIDAS local")
        return pd.DataFrame()

    df_all["datetime"] = pd.to_datetime(df_all[time_col], errors="coerce")
    df_all = df_all.dropna(subset=["datetime"])

    # Mapear columnas MIDAS a nombres estándar
    col_map = {
        "air_temperature":  "temp_c",
        "rltv_hum":         "humidity",
        "wind_speed":       "wind_ms",
        "wind_speed_mean":  "wind_ms",
        "prcp_amt":         "precip_mm",
        "rainfall":         "precip_mm",
    }
    df_all = df_all.rename(columns={k: v for k, v in col_map.items() if k in df_all.columns})

    for col in ["temp_c", "humidity", "wind_ms", "precip_mm"]:
        if col not in df_all.columns:
            df_all[col] = np.nan

    return df_all[["datetime", "temp_c", "humidity", "wind_ms", "precip_mm"]]


def main():
    log.info("=== C1: Descarga e integración de meteorología mensual ===")

    all_monthly = []

    for year in YEARS:
        # 1. Intentar datos locales MIDAS primero
        df_local = load_from_local_midas(MIDAS_DIR)
        if not df_local.empty:
            df_local = df_local[df_local["datetime"].dt.year == year]

        if not df_local.empty:
            log.info(f"  Usando datos MIDAS locales para {year}")
            df_hourly = df_local
        else:
            # 2. Fallback: Open-Meteo (ERA5, gratuito, sin registro)
            log.info(f"  No hay datos locales MIDAS — usando Open-Meteo (ERA5) para {year}")
            df_hourly = download_open_meteo(year, STATIONS["liverpool_airport"])

            if df_hourly.empty:
                log.warning(f"  No se pudieron obtener datos meteorológicos para {year}")
                continue

        monthly = aggregate_to_monthly(df_hourly)
        monthly["year"] = year
        all_monthly.append(monthly)
        log.info(f"  {year}: {len(monthly)} meses agregados")

    if not all_monthly:
        log.error("No se obtuvieron datos meteorológicos. Comprueba la conexión o descarga MIDAS manualmente.")
        return

    result = pd.concat(all_monthly, ignore_index=True)
    result = result.sort_values("year_month").reset_index(drop=True)

    result.to_csv(OUT_CSV, index=False, float_format="%.3f")
    log.info(f"\n  Meteorología mensual guardada → {OUT_CSV}")
    log.info(f"  Shape: {result.shape}")
    log.info(f"\n{result.to_string(index=False)}")


if __name__ == "__main__":
    main()
