"""
Fase 1 — Procesado de sensores
================================
Produce DOS salidas según el modo seleccionado:

  MODE = "annual"  (modo original)
    → data/interim/sensores_2024_agregados.csv  (1 fila por sensor, media anual 2024)
    → data/interim/sensores_2024_agregados.gpkg

  MODE = "monthly"  (panel temporal — MEJORA B1)
    → data/interim/sensores_monthly.csv   (N_sensores × N_meses filas)
    → data/interim/sensores_monthly.gpkg  (geometry repetida por mes)

  Filtros aplicados en ambos modos:
    - Solo 2024 (o el rango YEAR_RANGE si se amplía a histórico)
    - Umbral de completitud: ≥ COMPLETENESS_THRESHOLD del total de mediciones
      posibles en el periodo. Con monthly: ≥ threshold POR MES.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

ROOT      = Path(__file__).resolve().parents[2]
DATA_PROC = ROOT / "data" / "processed"
DATA_INT  = ROOT / "data" / "interim"
DATA_INT.mkdir(exist_ok=True)

# ── CONFIG ────────────────────────────────────────────────────────────────────
MODE = "monthly"          # "annual" | "monthly"
YEAR_RANGE = [2024]       # lista de años a incluir; ampliar a [2022,2023,2024] si hay histórico
COMPLETENESS_THRESHOLD = 0.75   # fracción mínima de mediciones válidas

# Para modo monthly: fracción mínima de horas válidas dentro de cada mes
MONTHLY_COMPLETENESS = 0.50   # umbral más relajado (meses cortos, fines de semana, etc.)


# ── UTILIDADES ────────────────────────────────────────────────────────────────

def load_raw(input_file: Path) -> pd.DataFrame:
    logging.info(f"Leyendo dataset: {input_file}")
    df = pd.read_csv(input_file)
    logging.info(f"  Total registros brutos: {len(df)}")

    df["datetime"] = pd.to_datetime(df["datetime"], format="mixed", errors="coerce")
    n_bad = df["datetime"].isna().sum()
    if n_bad:
        logging.warning(f"  {n_bad} filas con datetime inválido → descartadas")
    df = df.dropna(subset=["datetime"])
    return df


def filter_years(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["datetime"].dt.year.isin(YEAR_RANGE)
    out = df[mask].copy()
    logging.info(f"  Registros en años {YEAR_RANGE}: {len(out)}")
    if len(out) == 0:
        raise ValueError(f"No hay registros para los años {YEAR_RANGE}.")
    return out


def to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Construye GeoDataFrame en EPSG:27700.
    NOTA: en el CSV, la columna 'lat' contiene longitud real (~-3) y
    'lon' contiene latitud real (~53). Los nombres están intercambiados.
    """
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lat"], df["lon"]),  # x=lon_real(≈-3), y=lat_real(≈53)
        crs="EPSG:4326"
    ).to_crs("EPSG:27700")
    return gdf


# ── MODO ANUAL ────────────────────────────────────────────────────────────────

def process_annual(df: pd.DataFrame):
    """Media anual por sensor con filtro de completitud global."""
    logging.info("── Modo ANNUAL ──────────────────────────────────────────────")

    conteos = df.groupby("sensor_id").size()
    max_posible = df.groupby("sensor_id")["datetime"].nunique().max()
    threshold = int(max_posible * COMPLETENESS_THRESHOLD)
    logging.info(f"  Max mediciones únicas: {max_posible} → umbral 75%: {threshold}")

    sensores_ok = conteos[conteos >= threshold].index
    logging.info(f"  Sensores válidos: {len(sensores_ok)} de {len(conteos)}")

    df_ok = df[df["sensor_id"].isin(sensores_ok)]

    resumen = (
        df_ok
        .groupby(["sensor_id", "lat", "lon"], as_index=False)[["PM2.5", "PM10"]]
        .mean()
    )

    out_csv  = DATA_INT / "sensores_2024_agregados.csv"
    out_gpkg = DATA_INT / "sensores_2024_agregados.gpkg"
    resumen.to_csv(out_csv, index=False)
    logging.info(f"  CSV guardado → {out_csv}  ({len(resumen)} sensores)")

    gdf = to_geodataframe(resumen)
    gdf.to_file(out_gpkg, driver="GPKG")
    logging.info(f"  GPKG guardado → {out_gpkg}")
    return resumen


# ── MODO MENSUAL (MEJORA B1) ──────────────────────────────────────────────────

def process_monthly(df: pd.DataFrame):
    """
    Media mensual por sensor.

    Filtro de completitud por mes: se conserva un (sensor, mes) si tiene
    al menos MONTHLY_COMPLETENESS × max_mediciones_en_ese_mes mediciones válidas.

    Salida: DataFrame con columnas:
        sensor_id, year_month, lat, lon, PM2.5, PM10, n_obs, completeness
    """
    logging.info("── Modo MONTHLY (panel temporal B1) ──────────────────────────")

    df = df.copy()
    df["year_month"] = df["datetime"].dt.to_period("M")

    # Número de observaciones por (sensor, mes)
    counts = df.groupby(["sensor_id", "year_month"]).size().rename("n_obs")

    # Máximo teórico por mes: tomamos el máximo observado entre todos los sensores
    # para ese mes (proxy del número de mediciones posibles si el sensor funciona bien)
    max_by_month = (
        df.groupby(["sensor_id", "year_month"])
        .size()
        .groupby("year_month")
        .max()
        .rename("max_obs_month")
    )

    # Coordenadas (invariantes)
    coords = (
        df.groupby("sensor_id")[["lat", "lon"]]
        .first()
    )

    # Medias PM por (sensor, mes)
    pm_means = (
        df.groupby(["sensor_id", "year_month"])[["PM2.5", "PM10"]]
        .mean()
    )

    # Unir todo
    panel = (
        pm_means
        .join(counts)
        .join(max_by_month, on="year_month")
    )
    panel["completeness"] = panel["n_obs"] / panel["max_obs_month"]
    panel = panel.join(coords, on="sensor_id")

    n_total = len(panel)
    panel = panel[panel["completeness"] >= MONTHLY_COMPLETENESS].copy()
    logging.info(
        f"  Filas (sensor×mes) antes del filtro: {n_total} → "
        f"después ({MONTHLY_COMPLETENESS*100:.0f}% completitud): {len(panel)}"
    )

    # Descartar meses con PM2.5 o PM10 NaN (sensor apagado)
    panel = panel.dropna(subset=["PM2.5", "PM10"])
    logging.info(f"  Filas tras descartar NaN en PM: {len(panel)}")

    panel = panel.reset_index()
    panel["year_month"] = panel["year_month"].astype(str)  # "2024-01", etc.

    out_csv  = DATA_INT / "sensores_monthly.csv"
    out_gpkg = DATA_INT / "sensores_monthly.gpkg"

    panel.to_csv(out_csv, index=False)
    logging.info(f"  CSV mensual guardado → {out_csv}  ({len(panel)} filas)")

    gdf = to_geodataframe(panel)
    gdf.to_file(out_gpkg, driver="GPKG")
    logging.info(f"  GPKG mensual guardado → {out_gpkg}")

    # Resumen por sensor
    n_meses = panel.groupby("sensor_id")["year_month"].count()
    logging.info(
        f"  Meses válidos por sensor:\n"
        f"{n_meses.describe().round(1).to_string()}"
    )
    logging.info(
        f"  Media PM2.5 global: {panel['PM2.5'].mean():.2f} µg/m³  "
        f"| Media PM10: {panel['PM10'].mean():.2f} µg/m³"
    )
    return panel


# ── MAIN ──────────────────────────────────────────────────────────────────────

def process_sensor_data_2024():
    input_file = DATA_PROC / "sensors_definitivo.csv"
    df = load_raw(input_file)
    df = filter_years(df)

    if MODE == "annual":
        process_annual(df)
    elif MODE == "monthly":
        process_monthly(df)
        # También producir el anual para backward compatibility con scripts que lo usen
        process_annual(df)
    else:
        raise ValueError(f"MODE no reconocido: '{MODE}'. Usa 'annual' o 'monthly'.")


if __name__ == "__main__":
    process_sensor_data_2024()
