"""
build_full_panel.py — Panel histórico completo 2021-2025
=========================================================
1. Descarga meteorología mensual 2021-2025 via Open-Meteo (gratuito, sin registro).
2. Parsea los 321 archivos raw de sensores (todos los quartos/años).
3. Aplica filtros de calidad (sentinel, rango físico, completitud).
4. Agrega a nivel mensual por sensor.
5. Exporta:
     data/interim/sensores_monthly_full.csv   ← panel completo
     data/interim/meteo_monthly_full.csv      ← meteo 2021-2025
"""

from __future__ import annotations
import logging
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parents[2]
SENSOR_DIR = ROOT / "data" / "raw" / "sensores"
DATA_INT   = ROOT / "data" / "interim"

OUT_SENSORS = DATA_INT / "sensores_monthly_full.csv"
OUT_METEO   = DATA_INT / "meteo_monthly_full.csv"

# Estación Open-Meteo: Liverpool Airport
LAT, LON = 53.3336, -2.8497

# Años a descargar (2024 ya existe pero lo re-descargamos para consistencia)
YEARS = [2021, 2022, 2023, 2024, 2025]

# Filtros físicos de calidad
PM25_MIN, PM25_MAX = 0.0,  150.0
PM10_MIN, PM10_MAX = 0.0,  300.0
SENTINEL_APPROX    = -8.83e+29        # valor centinela de sensor Aeternum
SENTINEL_TOL       = 1e+20            # tolerancia para detectarlo

# Completitud mínima para incluir un mes (fracción del total esperado)
MIN_COMPLETENESS = 0.40

# Intervalo nominal de muestreo (minutos) → obs esperadas por mes
SAMPLE_INTERVAL_MIN = 30
HOURS_PER_MONTH     = 730             # ~24.3 días/mes promedio anual


# ═══════════════════════════════════════════════════════════════════════════════
# 1. METEOROLOGÍA
# ═══════════════════════════════════════════════════════════════════════════════

def download_open_meteo_year(year: int) -> pd.DataFrame:
    """Descarga datos horarios de Open-Meteo para un año dado."""
    end_date = f"{year}-12-31"
    if year == 2025:
        # Datos hasta hoy (evitar error por fechas futuras)
        today = pd.Timestamp.today().date()
        end_date = min(today, pd.Timestamp(f"{year}-12-31").date()).strftime("%Y-%m-%d")

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   LAT,
        "longitude":  LON,
        "start_date": f"{year}-01-01",
        "end_date":   end_date,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone": "Europe/London",
        "wind_speed_unit": "ms",
    }
    log.info("  Open-Meteo %d (%s → %s) ...", year, f"{year}-01-01", end_date)
    try:
        r = requests.get(url, params=params, timeout=90)
        r.raise_for_status()
        h = r.json()["hourly"]
        df = pd.DataFrame({
            "datetime":  pd.to_datetime(h["time"]),
            "temp_c":    h["temperature_2m"],
            "humidity":  h["relative_humidity_2m"],
            "wind_ms":   h["wind_speed_10m"],
            "precip_mm": h["precipitation"],
        })
        log.info("  %d: %d horas descargadas", year, len(df))
        return df
    except Exception as e:
        log.error("  Fallo Open-Meteo %d: %s", year, e)
        return pd.DataFrame()


def aggregate_meteo_monthly(df_h: pd.DataFrame) -> pd.DataFrame:
    """Agrega horario a mensual."""
    df = df_h.copy()
    df["year_month"] = df["datetime"].dt.to_period("M").astype(str)
    monthly = df.groupby("year_month").agg(
        air_temperature_mean=("temp_c",   "mean"),
        rltv_hum_mean       =("humidity", "mean"),
        wind_speed_mean     =("wind_ms",  "mean"),
        precip_total_mm     =("precip_mm","sum"),
    )
    df["rain_h"] = df["precip_mm"] > 0.1
    monthly["rain_days"] = (df.groupby("year_month")["rain_h"].sum() / 24.0).round(1)
    monthly = monthly.reset_index()
    monthly["year"] = pd.to_datetime(monthly["year_month"]).dt.year
    return monthly.round(3)


def build_meteo_full() -> pd.DataFrame:
    """Descarga y concatena meteo para todos los años."""
    frames = []
    for yr in YEARS:
        df_h = download_open_meteo_year(yr)
        if df_h.empty:
            log.warning("  Año %d sin meteo — se omite", yr)
            continue
        frames.append(aggregate_meteo_monthly(df_h))

    if not frames:
        raise RuntimeError("No se pudo descargar ningún año de meteo.")

    meteo = (
        pd.concat(frames, ignore_index=True)
        .sort_values("year_month")
        .drop_duplicates("year_month")
        .reset_index(drop=True)
    )
    meteo.to_csv(OUT_METEO, index=False, float_format="%.3f")
    log.info("Meteo guardada: %s (%d meses)", OUT_METEO, len(meteo))
    return meteo


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SENSORES — PARSE + QC
# ═══════════════════════════════════════════════════════════════════════════════

def extract_sensor_id(path: Path) -> str:
    """Extrae sensor_id del nombre de archivo, robusto a todos los formatos."""
    m = re.match(r"data_aeternum_(.+?)_\d{4}-\d{2}", path.stem)
    return m.group(1) if m else path.stem


def expected_obs_per_month(year_month: str) -> int:
    """Número de observaciones esperadas en un mes a resolución 30 min."""
    ym = pd.Period(year_month, freq="M")
    return int(ym.days_in_month * 24 * 60 / SAMPLE_INTERVAL_MIN)


def load_and_clean_file(path: Path) -> pd.DataFrame:
    """
    Lee un archivo raw de sensor y aplica QC básico.
    Devuelve DataFrame con columnas: datetime, PM2.5, PM10, sensor_id
    """
    try:
        df = pd.read_csv(path, parse_dates=["Date & Time"])
    except Exception as e:
        log.warning("  No se pudo leer %s: %s", path.name, e)
        return pd.DataFrame()

    df.rename(columns={"Date & Time": "datetime"}, inplace=True)
    df["sensor_id"] = extract_sensor_id(path)

    # Eliminar filas completamente vacías
    df = df.dropna(subset=["PM2.5", "PM10"], how="all")

    # Filtro sentinel (valor centinela de hardware Aeternum)
    mask_sentinel = (
        df["PM2.5"].notna() & (df["PM2.5"].abs() > SENTINEL_TOL)
    ) | (
        df["PM10"].notna() & (df["PM10"].abs() > SENTINEL_TOL)
    )
    df = df[~mask_sentinel]

    # Rango físico
    df = df[
        df["PM2.5"].between(PM25_MIN, PM25_MAX) &
        df["PM10"].between(PM10_MIN,  PM10_MAX)
    ]

    return df[["datetime", "PM2.5", "PM10", "sensor_id"]].copy()


def build_sensor_monthly(all_files: list[Path]) -> pd.DataFrame:
    """
    Procesa todos los archivos raw y devuelve el panel mensual agregado.
    """
    log.info("Procesando %d archivos de sensores ...", len(all_files))

    frames = []
    for i, f in enumerate(all_files):
        df = load_and_clean_file(f)
        if not df.empty:
            frames.append(df)
        if (i + 1) % 50 == 0:
            log.info("  %d / %d archivos procesados", i + 1, len(all_files))

    if not frames:
        raise RuntimeError("Ningún archivo de sensor pudo parsearse.")

    raw = pd.concat(frames, ignore_index=True)
    raw["year_month"] = raw["datetime"].dt.to_period("M").astype(str)

    log.info(
        "Total filas limpias: %s | Sensores únicos: %d | Rango: %s – %s",
        f"{len(raw):,}",
        raw["sensor_id"].nunique(),
        raw["year_month"].min(),
        raw["year_month"].max(),
    )

    # Agregación mensual
    monthly = (
        raw.groupby(["sensor_id", "year_month"])
        .agg(
            n_obs     = ("PM2.5", "count"),
            pm25_mean = ("PM2.5", "mean"),
            pm25_med  = ("PM2.5", "median"),
            pm25_std  = ("PM2.5", "std"),
            pm25_p95  = ("PM2.5", lambda x: x.quantile(0.95)),
            pm10_mean = ("PM10",  "mean"),
        )
        .reset_index()
    )

    # Completitud
    monthly["expected_obs"] = monthly["year_month"].map(expected_obs_per_month)
    monthly["completeness"]  = (monthly["n_obs"] / monthly["expected_obs"]).clip(upper=1.0)

    # Renombrar para compatibilidad con código existente
    monthly.rename(columns={"pm25_mean": "PM2.5", "pm10_mean": "PM10"}, inplace=True)

    # Filtro completitud
    before = len(monthly)
    monthly = monthly[monthly["completeness"] >= MIN_COMPLETENESS].reset_index(drop=True)
    log.info(
        "Panel mensual: %d filas (eliminadas %d por completitud<%d%%)",
        len(monthly), before - len(monthly), int(MIN_COMPLETENESS * 100),
    )

    return monthly


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("=== build_full_panel: Panel histórico completo 2021-2025 ===")

    # ── 1. Meteorología ──────────────────────────────────────────────────────
    log.info("-- FASE 1: Meteorología --")
    meteo = build_meteo_full()
    log.info(
        "Meteo: %d meses | %s – %s",
        len(meteo), meteo["year_month"].min(), meteo["year_month"].max(),
    )

    # ── 2. Sensores ──────────────────────────────────────────────────────────
    log.info("-- FASE 2: Sensores raw --")
    all_files = sorted(SENSOR_DIR.rglob("*.csv"))
    log.info("Archivos encontrados: %d", len(all_files))

    monthly = build_sensor_monthly(all_files)

    # Añadir coordenadas si disponibles (para referencia)
    coords_csv = ROOT / "data" / "raw" / "CoordsSensores.csv"
    if coords_csv.exists():
        coords = pd.read_csv(coords_csv)[["sensor_id", "lat", "lon"]]
        monthly = monthly.merge(coords, on="sensor_id", how="left")

    monthly.to_csv(OUT_SENSORS, index=False, float_format="%.4f")
    log.info("Panel guardado: %s (%d filas)", OUT_SENSORS, len(monthly))

    # ── Resumen ──────────────────────────────────────────────────────────────
    log.info("\n=== RESUMEN FINAL ===")
    log.info(
        "Sensores totales: %d | Meses totales: %d | Rango temporal: %s – %s",
        monthly["sensor_id"].nunique(),
        len(monthly),
        monthly["year_month"].min(),
        monthly["year_month"].max(),
    )

    by_ym = monthly.groupby("year_month").agg(
        n_sensores=("sensor_id", "count"),
        pm25_mean =("PM2.5", "mean"),
        pm25_std  =("PM2.5", "std"),
    ).round(2)
    log.info("\nObservaciones por mes:\n%s", by_ym.to_string())

    # Cobertura sensor × mes con meteo disponible
    panel_meteo = monthly.merge(meteo[["year_month"]], on="year_month", how="inner")
    log.info(
        "\nPanel con meteo disponible: %d filas (%d sensores × meses)",
        len(panel_meteo), len(panel_meteo),
    )

    return monthly, meteo


if __name__ == "__main__":
    main()
