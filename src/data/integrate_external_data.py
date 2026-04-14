"""
Integración de datos externos locales
======================================
1. census_ts001_lsoa.csv  → data/interim/population_density.csv
2. file1.csv (AURN)       → amplía sensores_2024_agregados.csv y sensores_monthly.csv

Ejecutar desde la raíz del proyecto:
    python src/data/integrate_external_data.py
"""

import re
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT     = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INT = ROOT / "data" / "interim"

# Coordenadas AURN en WGS84 (lat, lon)
AURN_META = {
    "Liverpool Speke":   {"sensor_id": "LISP", "lat": 53.3458, "lon": -2.8658},
    "Wirral Tranmere":   {"sensor_id": "WIRT", "lat": 53.3775, "lon": -3.0085},
}


# ═══════════════════════════════════════════════════════════
# 1. POBLACIÓN — parsear census_ts001_lsoa.csv
# ═══════════════════════════════════════════════════════════

def parse_census() -> pd.DataFrame:
    census_file = DATA_RAW / "census_ts001_lsoa.csv"
    log.info(f"Parseando {census_file} ...")

    rows = []
    with open(census_file, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue  # cabecera
            line = line.strip().strip('"')
            m = re.match(r'(E\d+)\s*:\s*([^,]+),""([\d,]+)""', line)
            if m:
                rows.append({
                    "LSOA21CD":   m.group(1),
                    "lsoa_name":  m.group(2).strip(),
                    "population": int(m.group(3).replace(",", "")),
                })

    df = pd.DataFrame(rows)
    log.info(f"  LSOAs parseadas: {len(df)}, población total: {df['population'].sum():,}")
    return df


def build_population_density() -> pd.DataFrame:
    """Une censo con geometrías LSOA → densidad → join espacial con sensores."""
    pop = parse_census()

    lsoa = gpd.read_file(DATA_RAW / "lsoa_liverpool.gpkg")   # EPSG:27700, cols: LSOA21CD, LSOA21NM, geometry
    lsoa = lsoa.merge(pop[["LSOA21CD", "population"]], on="LSOA21CD", how="left")
    lsoa["area_km2"]        = lsoa.geometry.area / 1e6
    lsoa["pop_density_km2"] = lsoa["population"] / lsoa["area_km2"]

    n_matched = lsoa["pop_density_km2"].notna().sum()
    log.info(f"  LSOAs con densidad calculada: {n_matched}/{len(lsoa)}")

    # Sensores snapped (EPSG:27700)
    sensors = gpd.read_file(DATA_INT / "sensores_snapped.gpkg")
    sensors_proj = sensors.to_crs(lsoa.crs)

    joined = gpd.sjoin(
        sensors_proj[["sensor_id", "geometry"]],
        lsoa[["LSOA21CD", "LSOA21NM", "population", "area_km2", "pop_density_km2", "geometry"]],
        how="left",
        predicate="within",
    )

    result = joined[["sensor_id", "LSOA21CD", "LSOA21NM", "population",
                     "area_km2", "pop_density_km2"]].copy()

    # Fallback: sensores fuera de cualquier LSOA → mediana
    med = result["pop_density_km2"].median()
    n_missing = result["pop_density_km2"].isna().sum()
    if n_missing > 0:
        result["pop_density_km2"] = result["pop_density_km2"].fillna(med)
        log.warning(f"  {n_missing} sensores fuera de LSOA → mediana ({med:.1f} hab/km²)")

    out = DATA_INT / "population_density.csv"
    result.to_csv(out, index=False)
    log.info(f"  Guardado: {out} ({len(result)} sensores)")
    log.info(f"  Densidad media: {result['pop_density_km2'].mean():.0f} hab/km²  "
             f"[{result['pop_density_km2'].min():.0f} – {result['pop_density_km2'].max():.0f}]")
    return result


# ═══════════════════════════════════════════════════════════
# 2. AURN — procesar file1.csv
# ═══════════════════════════════════════════════════════════

def process_aurn() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Lee file1.csv, filtra PM10 de LISP y WIRT, agrega a anual y mensual.
    Devuelve (df_annual, df_monthly) con la misma estructura que
    sensores_2024_agregados.csv y sensores_monthly.csv.
    """
    aurn_file = DATA_RAW / "file1.csv"
    log.info(f"Procesando {aurn_file} ...")

    df = pd.read_csv(aurn_file)
    df.columns = [c.strip() for c in df.columns]

    # Filtrar solo estaciones de interés y PM10
    stations_keep = list(AURN_META.keys())
    df = df[df["SiteName"].isin(stations_keep)].copy()
    df_pm10 = df[df["PollutantName"] == "PM10"].copy()

    if df_pm10.empty:
        log.error("  No hay datos de PM10 en file1.csv para las estaciones de interés")
        return pd.DataFrame(), pd.DataFrame()

    # Parsear tiempo
    df_pm10["datetime"] = pd.to_datetime(df_pm10["StartTime"], utc=True)
    df_pm10["year_month"] = df_pm10["datetime"].dt.to_period("M").astype(str)
    df_pm10["Value"] = pd.to_numeric(df_pm10["Value"], errors="coerce")

    # Solo valores válidos (Status == 'V')
    df_pm10 = df_pm10[df_pm10["Status"] == "V"].copy()

    log.info(f"  Registros PM10 válidos: {len(df_pm10)}")
    log.info(f"  Estaciones: {df_pm10['SiteName'].unique().tolist()}")

    # ── Agregado anual ───────────────────────────────────────────
    annual_rows = []
    for site_name, meta in AURN_META.items():
        sub = df_pm10[df_pm10["SiteName"] == site_name]
        if sub.empty:
            log.warning(f"  Sin datos PM10 para {site_name}")
            continue
        pm10_mean = sub["Value"].mean()
        annual_rows.append({
            "sensor_id": meta["sensor_id"],
            "lat":       meta["lon"],   # nota: en sensores_2024_agregados lat/lon están invertidos
            "lon":       meta["lat"],
            "PM2.5":     np.nan,        # no disponible en este archivo
            "PM10":      round(pm10_mean, 6),
        })
        log.info(f"  {site_name} ({meta['sensor_id']}): PM10 anual = {pm10_mean:.2f} µg/m³")

    df_annual = pd.DataFrame(annual_rows)

    # ── Agregado mensual ─────────────────────────────────────────
    monthly_rows = []
    for site_name, meta in AURN_META.items():
        sub = df_pm10[df_pm10["SiteName"] == site_name]
        if sub.empty:
            continue
        grp = sub.groupby("year_month")["Value"].agg(
            PM10="mean",
            n_obs="count",
            max_obs_month="max",
        ).reset_index()
        grp["sensor_id"]   = meta["sensor_id"]
        grp["PM2.5"]       = np.nan
        grp["completeness"] = (grp["n_obs"] / grp["n_obs"].max()).clip(0, 1)
        grp["lat"]         = meta["lon"]   # mismo orden invertido que el dataset original
        grp["lon"]         = meta["lat"]
        monthly_rows.append(grp)

    df_monthly = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()

    log.info(f"  Filas anuales AURN:   {len(df_annual)}")
    log.info(f"  Filas mensuales AURN: {len(df_monthly)}")
    return df_annual, df_monthly


# ═══════════════════════════════════════════════════════════
# 3. INTEGRAR AURN EN SENSORES
# ═══════════════════════════════════════════════════════════

def integrate_aurn(df_annual: pd.DataFrame, df_monthly: pd.DataFrame):
    """Añade estaciones AURN a sensores_2024_agregados y sensores_monthly."""
    if df_annual.empty:
        log.warning("Sin datos AURN para integrar — saltando")
        return

    # ── Anual ────────────────────────────────────────────────────
    agg_path = DATA_INT / "sensores_2024_agregados.csv"
    existing_annual = pd.read_csv(agg_path)

    # Eliminar entradas previas de AURN por si se re-ejecuta
    aurn_ids = df_annual["sensor_id"].tolist()
    existing_annual = existing_annual[~existing_annual["sensor_id"].isin(aurn_ids)]
    updated_annual = pd.concat([existing_annual, df_annual], ignore_index=True)
    updated_annual.to_csv(agg_path, index=False)
    log.info(f"  sensores_2024_agregados.csv: {len(existing_annual)} → {len(updated_annual)} sensores")

    # ── GPKG anual ───────────────────────────────────────────────
    gpkg_path = DATA_INT / "sensores_2024_agregados.gpkg"
    existing_gpkg = gpd.read_file(gpkg_path)
    existing_gpkg = existing_gpkg[~existing_gpkg["sensor_id"].isin(aurn_ids)]

    aurn_geom = []
    for _, row in df_annual.iterrows():
        meta = next(m for m in AURN_META.values() if m["sensor_id"] == row["sensor_id"])
        # Crear punto en WGS84 y reproyectar a EPSG:27700
        pt = gpd.GeoDataFrame(
            [{"sensor_id": row["sensor_id"], "PM2.5": row["PM2.5"], "PM10": row["PM10"],
              "lat": row["lat"], "lon": row["lon"]}],
            geometry=[Point(meta["lon"], meta["lat"])],
            crs="EPSG:4326"
        ).to_crs("EPSG:27700")
        aurn_geom.append(pt)

    if aurn_geom:
        aurn_gdf = pd.concat(aurn_geom, ignore_index=True)
        updated_gpkg = pd.concat([existing_gpkg, aurn_gdf], ignore_index=True)
        updated_gpkg.to_file(gpkg_path, driver="GPKG")
        log.info(f"  sensores_2024_agregados.gpkg: {len(existing_gpkg)} → {len(updated_gpkg)} sensores")

    # ── Mensual ──────────────────────────────────────────────────
    if not df_monthly.empty:
        monthly_path = DATA_INT / "sensores_monthly.csv"
        existing_monthly = pd.read_csv(monthly_path)
        existing_monthly = existing_monthly[~existing_monthly["sensor_id"].isin(aurn_ids)]

        # Reordenar columnas para que coincidan
        cols = list(existing_monthly.columns)
        df_monthly_aligned = df_monthly.reindex(columns=cols)
        updated_monthly = pd.concat([existing_monthly, df_monthly_aligned], ignore_index=True)
        updated_monthly.to_csv(monthly_path, index=False)
        log.info(f"  sensores_monthly.csv: {len(existing_monthly)} → {len(updated_monthly)} filas")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("INTEGRACIÓN DE DATOS EXTERNOS")
    log.info("=" * 60)

    # 1. Población
    log.info("\n── POBLACIÓN ──────────────────────────────────────────")
    pop_result = build_population_density()

    # 2. AURN
    log.info("\n── AURN ───────────────────────────────────────────────")
    df_annual, df_monthly = process_aurn()
    integrate_aurn(df_annual, df_monthly)

    log.info("\n" + "=" * 60)
    log.info("INTEGRACIÓN COMPLETADA")
    log.info(f"  population_density.csv: {len(pop_result)} sensores")
    log.info(f"  AURN integradas:        {len(df_annual)} estaciones")
    log.info("=" * 60)
