"""
LUR LSOA-level Model — Issue #21
=================================
Construye un modelo de calidad del aire a nivel de barrio (LSOA) para Liverpool.

Estrategia:
1. Agrega predicciones del modelo de calles (liverpool_pollution_map.geojson) por LSOA
   → da cobertura a los 302 LSOAs sin depender solo de los 12 sensores reales
2. Construye matriz de features LSOA: landuse, edificios, densidad viaria, población
3. Entrena Ridge sobre las 302 LSOAs usando la agregación de calles como target
4. Valida R² contra los 12 LSOAs con sensor real (LOOCV)
5. Exporta GeoJSON y CSV de predicciones finales

Salidas:
    outputs/maps/lur_lsoa_predictions.geojson
    outputs/maps/lur_lsoa_predictions.csv
    outputs/models/lur_lsoa_PM25.pkl
    outputs/models/lur_lsoa_PM10.pkl
"""

import logging
import pickle
import re
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
while not (ROOT / "data").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent

RAW_DIR       = ROOT / "data" / "raw"
INTERIM_DIR   = ROOT / "data" / "interim"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR    = ROOT / "outputs" / "models"
MAPS_DIR      = ROOT / "outputs" / "maps"

for d in [MODELS_DIR, MAPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

CRS_GEO  = "EPSG:4326"
CRS_BNG  = "EPSG:27700"   # British National Grid — metros

TARGETS  = ["PM2.5", "PM10"]
ALPHA    = 1.0             # regularización Ridge — ajustable

# ---------------------------------------------------------------------------
# 1. CARGAR DATOS BASE
# ---------------------------------------------------------------------------

def load_lsoa_boundaries() -> gpd.GeoDataFrame:
    path = RAW_DIR / "lsoa_liverpool.gpkg"
    if not path.exists():
        raise FileNotFoundError(f"No encontrado: {path}")
    gdf = gpd.read_file(path)
    if gdf.crs.to_epsg() != 27700:
        gdf = gdf.to_crs(CRS_BNG)
    gdf["area_km2"] = gdf.geometry.area / 1e6
    log.info("LSOAs cargadas: %d | CRS: %s", len(gdf), gdf.crs)
    return gdf


def load_street_predictions() -> gpd.GeoDataFrame:
    path = MAPS_DIR / "liverpool_pollution_map.geojson"
    if not path.exists():
        raise FileNotFoundError(f"No encontrado: {path}. Ejecutar pipeline primero.")
    gdf = gpd.read_file(path).to_crs(CRS_BNG)
    log.info("Calles cargadas: %d tramos | cols: pm25_pred, pm10_pred", len(gdf))
    return gdf


def load_sensor_means() -> pd.DataFrame:
    """Media temporal por sensor para los 12 sensores con datos reales."""
    path = INTERIM_DIR / "sensores_monthly.csv"
    if not path.exists():
        path = INTERIM_DIR / "sensores_2024_agregados.csv"
    if not path.exists():
        path = PROCESSED_DIR / "sensores_definitivo.csv"
    if not path.exists():
        log.warning("No se encontró archivo de sensores mensuales — validación limitada.")
        return pd.DataFrame()

    df = pd.read_csv(path)
    # Calcular media por sensor
    target_cols = [c for c in ["PM2.5", "PM10"] if c in df.columns]
    group_cols  = ["sensor_id"] + [c for c in ["lat", "lon"] if c in df.columns]
    means = df.groupby("sensor_id", as_index=False)[target_cols].mean()

    # Coordenadas: tomar primera fila por sensor
    coords = df.groupby("sensor_id", as_index=False)[
        [c for c in ["lat", "lon"] if c in df.columns]
    ].first()
    means = means.merge(coords, on="sensor_id", how="left")
    log.info("Sensores con media calculada: %d", len(means))
    return means


def load_population() -> pd.DataFrame:
    """Población por LSOA desde el censo ONS 2021."""
    path = RAW_DIR / "census_ts001_lsoa.csv"
    if not path.exists():
        log.warning("census_ts001_lsoa.csv no encontrado — omitiendo densidad poblacional.")
        return pd.DataFrame(columns=["LSOA21CD", "population"])

    # Formato del ONS: "E01006651 : Liverpool 001A","1,616";;;;
    raw = pd.read_csv(path, header=0)
    col = raw.columns[0]
    records = []
    for _, row in raw.iterrows():
        val = str(row[col])
        # Extraer código LSOA
        code_match = re.match(r"(E\d{8})", val)
        if not code_match:
            continue
        code = code_match.group(1)
        # Extraer población (primer número entre comillas)
        pop_match = re.search(r'"([\d,]+)"', val)
        if pop_match:
            pop = int(pop_match.group(1).replace(",", ""))
        else:
            # Intentar extraer número sin comillas al final
            nums = re.findall(r"[\d,]+", val.split(":")[-1])
            if nums:
                pop = int(nums[0].replace(",", ""))
            else:
                continue
        records.append({"LSOA21CD": code, "population": pop})

    df = pd.DataFrame(records)
    log.info("Población ONS cargada: %d LSOAs", len(df))
    return df


# ---------------------------------------------------------------------------
# 2. AGREGACIÓN DE CALLES → LSOA
# ---------------------------------------------------------------------------

def aggregate_streets_to_lsoa(
    gdf_streets: gpd.GeoDataFrame,
    gdf_lsoa: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Asigna cada tramo de calle a su LSOA por centroide y calcula estadísticas
    (mean, p25, p75, max) de PM2.5 y PM10 por LSOA.
    """
    log.info("Asignando tramos a LSOAs por centroide...")

    streets = gdf_streets.copy()
    streets["centroid"] = streets.geometry.centroid
    streets_pts = streets.set_geometry("centroid")[
        ["pm25_pred", "pm10_pred", "centroid"]
    ].copy()

    joined = gpd.sjoin(
        streets_pts,
        gdf_lsoa[["LSOA21CD", "geometry"]],
        how="left",
        predicate="within",
    )

    # Tramos sin LSOA: asignar por nearest
    sin_lsoa = joined["LSOA21CD"].isna()
    if sin_lsoa.sum() > 0:
        nearest = gpd.sjoin_nearest(
            streets_pts[sin_lsoa],
            gdf_lsoa[["LSOA21CD", "geometry"]],
            how="left",
        )[["LSOA21CD"]]
        joined.loc[sin_lsoa, "LSOA21CD"] = nearest["LSOA21CD"].values
        log.info("  %d tramos asignados por nearest.", sin_lsoa.sum())

    stats = joined.groupby("LSOA21CD").agg(
        pm25_street_mean=("pm25_pred", "mean"),
        pm25_street_p25 =("pm25_pred", lambda x: x.quantile(0.25)),
        pm25_street_p75 =("pm25_pred", lambda x: x.quantile(0.75)),
        pm25_street_max =("pm25_pred", "max"),
        pm10_street_mean=("pm10_pred", "mean"),
        pm10_street_p25 =("pm10_pred", lambda x: x.quantile(0.25)),
        pm10_street_p75 =("pm10_pred", lambda x: x.quantile(0.75)),
        pm10_street_max =("pm10_pred", "max"),
        n_streets       =("pm25_pred", "count"),
    ).reset_index()

    coverage = len(stats)
    log.info("Agregación completada: %d/%d LSOAs con calles (%d sin cobertura)",
             coverage, len(gdf_lsoa),
             len(gdf_lsoa) - coverage)
    return stats


# ---------------------------------------------------------------------------
# 3. FEATURES ZONAL DESDE CSV EXISTENTE
# ---------------------------------------------------------------------------

def load_lsoa_features() -> pd.DataFrame:
    """
    Carga features zonales ya calculados (landuse, buildings, streets)
    del archivo generado por el notebook 3.2.
    """
    path = PROCESSED_DIR / "lur_barrios_predictions.csv"
    if not path.exists():
        log.warning("lur_barrios_predictions.csv no encontrado — features básicos solamente.")
        return pd.DataFrame()

    df = pd.read_csv(path)
    feature_cols = [
        "LSOA21CD",
        "pct_industrial", "pct_commercial", "pct_residential", "pct_green",
        "bcr", "n_buildings", "mean_bldg_area",
        "street_density_motorway", "street_density_primary",
        "street_density_secondary", "street_density_residential",
        "street_density_total",
    ]
    existing = [c for c in feature_cols if c in df.columns]
    log.info("Features zonales cargadas: %d columnas desde CSV", len(existing) - 1)
    return df[existing]


# ---------------------------------------------------------------------------
# 4. MODELO RIDGE CON LOOCV
# ---------------------------------------------------------------------------

def loocv_ridge(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> dict:
    """LOOCV sobre un Ridge. Devuelve R², RMSE y predicciones OOF."""
    loo    = LeaveOneOut()
    y_pred = np.zeros_like(y, dtype=float)
    scaler = StandardScaler()

    for train_idx, test_idx in loo.split(X):
        X_tr = scaler.fit_transform(X[train_idx])
        X_te = scaler.transform(X[test_idx])
        mdl  = Ridge(alpha=alpha)
        mdl.fit(X_tr, y[train_idx])
        y_pred[test_idx] = mdl.predict(X_te)

    r2   = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return {"r2": r2, "rmse": rmse, "y_pred_oof": y_pred}


def train_final_model(X: np.ndarray, y: np.ndarray, alpha: float = 1.0):
    """Entrena el modelo final sobre todos los datos."""
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)
    model  = Ridge(alpha=alpha)
    model.fit(X_sc, y)
    return model, scaler


# ---------------------------------------------------------------------------
# 5. VALIDACIÓN CONTRA SENSORES REALES
# ---------------------------------------------------------------------------

def validate_against_sensors(
    gdf_results: gpd.GeoDataFrame,
    df_sensors: pd.DataFrame,
    gdf_lsoa: gpd.GeoDataFrame,
) -> None:
    """Compara predicciones LSOA vs medias reales de sensores."""
    if df_sensors.empty:
        log.warning("Sin datos de sensores para validación.")
        return

    # Convertir sensores a GeoDataFrame
    # NOTA: en sensors_definitivo las columnas lat/lon pueden estar invertidas
    lat_col = "lat" if "lat" in df_sensors.columns else None
    lon_col = "lon" if "lon" in df_sensors.columns else None
    if lat_col is None:
        log.warning("Sensores sin columnas lat/lon — validación omitida.")
        return

    sample = df_sensors[[lat_col, lon_col]].iloc[0]
    # Si "lat" contiene valores ~-2.98 (lon real) los invertimos
    if abs(sample[lat_col]) < 10:   # latitudes UK > 50
        x_col, y_col = lon_col, lat_col
    else:
        x_col, y_col = lat_col, lon_col

    gdf_s = gpd.GeoDataFrame(
        df_sensors,
        geometry=gpd.points_from_xy(df_sensors[x_col], df_sensors[y_col]),
        crs=CRS_GEO,
    ).to_crs(CRS_BNG)

    joined = gpd.sjoin(
        gdf_s,
        gdf_lsoa[["LSOA21CD", "geometry"]],
        how="left",
        predicate="within",
    )
    # Nearest para sensores en borde
    sin = joined["LSOA21CD"].isna()
    if sin.any():
        near = gpd.sjoin_nearest(gdf_s[sin], gdf_lsoa[["LSOA21CD", "geometry"]], how="left")
        joined.loc[sin, "LSOA21CD"] = near["LSOA21CD"].values

    merged = joined.merge(
        gdf_results[["LSOA21CD", "PM2.5_final", "PM10_final"]],
        on="LSOA21CD",
        how="inner",
    )

    log.info("=== VALIDACIÓN VS SENSORES REALES (n=%d) ===", len(merged))
    for target, pred_col in [("PM2.5", "PM2.5_final"), ("PM10", "PM10_final")]:
        sensor_col = target
        if sensor_col not in merged.columns:
            continue
        valid = merged[[sensor_col, pred_col]].dropna()
        if len(valid) < 2:
            continue
        r2   = r2_score(valid[sensor_col], valid[pred_col])
        rmse = np.sqrt(mean_squared_error(valid[sensor_col], valid[pred_col]))
        log.info("  %s | n=%d | R²=%.3f | RMSE=%.3f µg/m³", target, len(valid), r2, rmse)


# ---------------------------------------------------------------------------
# 6. PIPELINE PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    log.info("=== LUR LSOA MODEL — INICIO ===")

    # --- Cargar datos ---
    gdf_lsoa    = load_lsoa_boundaries()
    gdf_streets = load_street_predictions()
    df_sensors  = load_sensor_means()
    df_pop      = load_population()
    df_features = load_lsoa_features()

    # --- Agregar calles → LSOA ---
    df_street_agg = aggregate_streets_to_lsoa(gdf_streets, gdf_lsoa)

    # --- Construir dataset completo ---
    gdf = gdf_lsoa.merge(df_street_agg, on="LSOA21CD", how="left")

    if not df_features.empty:
        gdf = gdf.merge(df_features, on="LSOA21CD", how="left")

    # Añadir población por LSOA
    if not df_pop.empty:
        gdf = gdf.merge(df_pop, on="LSOA21CD", how="left")
        gdf["pop_density_km2"] = gdf["population"] / gdf["area_km2"].replace(0, np.nan)
        log.info("Densidad poblacional añadida: %d LSOAs con datos",
                 gdf["pop_density_km2"].notna().sum())

    # --- Definir features para el modelo ---
    FEATURE_COLS = []

    # Features zonales del CSV (si disponibles)
    zonal_candidates = [
        "pct_industrial", "pct_commercial", "pct_residential", "pct_green",
        "bcr", "n_buildings", "mean_bldg_area",
        "street_density_motorway", "street_density_primary",
        "street_density_secondary", "street_density_residential",
        "street_density_total",
    ]
    FEATURE_COLS += [c for c in zonal_candidates if c in gdf.columns]

    # Densidad poblacional
    if "pop_density_km2" in gdf.columns:
        FEATURE_COLS.append("pop_density_km2")

    # Área LSOA
    if "area_km2" in gdf.columns:
        FEATURE_COLS.append("area_km2")

    log.info("Features del modelo: %d → %s", len(FEATURE_COLS), FEATURE_COLS)

    # --- Rellenar NaN en features con mediana ---
    for col in FEATURE_COLS:
        median_val = gdf[col].median()
        n_nan = gdf[col].isna().sum()
        if n_nan > 0:
            log.info("  Imputando %d NaN en '%s' con mediana=%.3f", n_nan, col, median_val)
        gdf[col] = gdf[col].fillna(median_val)

    X_all = gdf[FEATURE_COLS].values

    # --- Entrenar modelos por target ---
    model_results = {}

    for target in TARGETS:
        street_col = f"pm25_street_mean" if target == "PM2.5" else "pm10_street_mean"

        if street_col not in gdf.columns:
            log.warning("Columna %s no disponible — saltando %s", street_col, target)
            continue

        # Target: agregación de calles (n=302, mucho más robusto que n=12)
        mask  = gdf[street_col].notna()
        X_tr  = X_all[mask]
        y_tr  = gdf.loc[mask, street_col].values

        log.info("--- %s | n_train=%d (street aggregation) ---", target, len(y_tr))

        # LOOCV Ridge
        cv = loocv_ridge(X_tr, y_tr, alpha=ALPHA)
        log.info("  Ridge LOOCV → R²=%.3f | RMSE=%.3f µg/m³", cv["r2"], cv["rmse"])

        # Modelo final
        model, scaler = train_final_model(X_tr, y_tr, alpha=ALPHA)

        # Predicción completa
        X_sc_all          = scaler.transform(X_all)
        gdf[f"{target}_lsoa_pred"] = model.predict(X_sc_all)

        model_results[target] = {
            "model":  model,
            "scaler": scaler,
            "r2_cv":  cv["r2"],
            "rmse_cv": cv["rmse"],
            "feature_cols": FEATURE_COLS,
        }

        # Guardar pickle
        pkl_path = MODELS_DIR / f"lur_lsoa_{target.replace('.', '')}.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump({
                "model":        model,
                "scaler":       scaler,
                "feature_cols": FEATURE_COLS,
                "target":       target,
                "r2_cv":        cv["r2"],
                "rmse_cv":      cv["rmse"],
                "n_train":      len(y_tr),
                "trained_on":   "street_aggregation_lsoa",
            }, f)
        log.info("  Modelo guardado: %s", pkl_path.name)

    # --- Añadir valores de sensores reales donde disponibles ---
    # Cargar CSV existente con sensor means por LSOA
    csv_prev = PROCESSED_DIR / "lur_barrios_predictions.csv"
    if csv_prev.exists():
        df_prev = pd.read_csv(csv_prev)[
            [c for c in ["LSOA21CD", "PM2.5_mean", "PM10_mean", "n_sensores"]
             if c in pd.read_csv(csv_prev).columns]
        ]
        gdf = gdf.merge(df_prev, on="LSOA21CD", how="left")
        log.info("Medias de sensores reales integradas: %d LSOAs con datos",
                 gdf["PM2.5_mean"].notna().sum() if "PM2.5_mean" in gdf.columns else 0)

    # --- Columnas finales ---
    # Prioridad: sensor real > agregación calles > predicción Ridge
    for target in TARGETS:
        sensor_col  = f"{target}_mean"         # valor real del sensor
        street_col  = f"pm25_street_mean" if target == "PM2.5" else "pm10_street_mean"
        lsoa_pred   = f"{target}_lsoa_pred"    # Ridge sobre features LSOA
        final_col   = f"{target}_final"

        if final_col in gdf.columns:
            # Ya existe del CSV anterior — actualizar con nueva predicción donde mejore
            pass

        # Construcción: sensor real → street agg → Ridge
        if sensor_col in gdf.columns:
            gdf[final_col] = gdf[sensor_col].fillna(
                gdf.get(street_col, gdf[lsoa_pred]) if street_col in gdf.columns
                else gdf[lsoa_pred]
            )
        elif street_col in gdf.columns:
            gdf[final_col] = gdf[street_col]
        elif lsoa_pred in gdf.columns:
            gdf[final_col] = gdf[lsoa_pred]

    # Score A-F basado en WHO guidelines (PM2.5)
    def pm25_score(v):
        if pd.isna(v):   return None
        if v < 5:        return "A"
        elif v < 10:     return "B"
        elif v < 15:     return "C"
        elif v < 20:     return "D"
        elif v < 25:     return "E"
        else:            return "F"

    if "PM2.5_final" in gdf.columns:
        gdf["score_pm25"] = gdf["PM2.5_final"].apply(pm25_score)
        dist = gdf["score_pm25"].value_counts().sort_index()
        log.info("Distribución score PM2.5: %s", dict(dist))

    def pm10_score(v):
        if pd.isna(v):   return None
        if v < 15:       return "A"
        elif v < 30:     return "B"
        elif v < 45:     return "C"   # WHO 2021 PM10 daily guideline
        elif v < 60:     return "D"
        elif v < 75:     return "E"
        else:            return "F"

    if "PM10_final" in gdf.columns:
        gdf["score_pm10"] = gdf["PM10_final"].apply(pm10_score)
        dist = gdf["score_pm10"].value_counts().sort_index()
        log.info("Distribución score PM10: %s", dict(dist))

    # --- Validación contra sensores reales ---
    validate_against_sensors(gdf, df_sensors, gdf_lsoa)

    # --- Exportar ---
    export_cols = (
        ["LSOA21CD", "LSOA21NM", "area_km2"]
        + [c for c in FEATURE_COLS if c in gdf.columns]
        + [c for c in ["population", "pop_density_km2"] if c in gdf.columns]
        + [c for c in ["PM2.5_mean", "PM10_mean", "n_sensores"] if c in gdf.columns]
        + [c for c in gdf.columns if "street_mean" in c or "street_p25" in c
           or "street_p75" in c or "n_streets" in c]
        + [c for c in gdf.columns if "lsoa_pred" in c]
        + ["PM2.5_final", "PM10_final", "score_pm25", "score_pm10"]
    )
    # Dedup manteniendo orden
    seen = set()
    export_cols = [c for c in export_cols
                   if c in gdf.columns and not (c in seen or seen.add(c))]

    gdf_out = gdf[export_cols + ["geometry"]].to_crs(CRS_GEO)

    out_geojson = MAPS_DIR / "lur_lsoa_predictions.geojson"
    out_csv     = MAPS_DIR / "lur_lsoa_predictions.csv"

    gdf_out.to_file(out_geojson, driver="GeoJSON")
    gdf_out.drop(columns="geometry").to_csv(out_csv, index=False)

    log.info("=== EXPORTADO ===")
    log.info("  GeoJSON: %s (%d LSOAs)", out_geojson.name, len(gdf_out))
    log.info("  CSV:     %s", out_csv.name)
    log.info("")
    log.info("=== RESUMEN MÉTRICAS ===")
    for target, res in model_results.items():
        log.info("  %s | Ridge LOOCV R²=%.3f | RMSE=%.3f µg/m³",
                 target, res["r2_cv"], res["rmse_cv"])

    nan_pm25 = gdf_out["PM2.5_final"].isna().sum()
    nan_pm10 = gdf_out["PM10_final"].isna().sum()
    log.info("  PM2.5_final NaN: %d/%d", nan_pm25, len(gdf_out))
    log.info("  PM10_final  NaN: %d/%d", nan_pm10, len(gdf_out))
    log.info("=== FIN ===")


if __name__ == "__main__":
    main()
