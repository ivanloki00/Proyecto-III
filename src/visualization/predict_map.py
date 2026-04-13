"""
Fase 8 - Predicción Espacial (Generar Mapa)
Calcula las variables retenidas por los modelos LUR para todos los 
tramos viarios de Liverpool y predice los niveles de PM2.5 y PM10.
"""

import pickle
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DATA_RAW  = ROOT / "data" / "raw"
DATA_INT  = ROOT / "data" / "interim"
OUT_DIR   = ROOT / "outputs"

MODEL_PM25_PKL = OUT_DIR / "lur_model_PM25.pkl"
MODEL_PM10_PKL = OUT_DIR / "lur_model_PM10.pkl"

STREETS_GPKG   = DATA_INT / "streets_with_traffic.gpkg"
BUILDINGS_GPKG = DATA_RAW / "buildings_liverpool.gpkg"
LANDUSE_GPKG   = DATA_RAW / "landuse_liverpool.gpkg"
OUT_GEOJSON    = OUT_DIR / "liverpool_pollution_map.geojson"

# Variables específicas que seleccionaron los modelos
# (En caso de cambiar, se leerán del .pkl, pero necesitamos 
#  saber qué radios calcular implícitamente).
# Variables según ejecución anterior:
# ['road_length_residential_m_500m', 'landuse_green_ratio_100m', 'dist_industrial_m_50m']

HIGHWAY_CATS = {
    "residential": ["residential", "tertiary", "tertiary_link", "unclassified", "living_street", "service"],
}
LANDUSE_CATS = {
    "industrial": ["industrial"],
    "green":      ["grass", "forest", "park", "garden"],
}

def load_models():
    with open(MODEL_PM25_PKL, "rb") as f:
        m_pm25 = pickle.load(f)
    with open(MODEL_PM10_PKL, "rb") as f:
        m_pm10 = pickle.load(f)
    return m_pm25, m_pm10


def clip_and_area(gdf, buffer_geom):
    try:
        clipped = gdf.clip(buffer_geom)
        return clipped.geometry.area.sum()
    except Exception:
        return 0.0

def clip_and_length(gdf, buffer_geom):
    try:
        clipped = gdf.clip(buffer_geom)
        return clipped.geometry.length.sum()
    except Exception:
        return 0.0


def main():
    log.info("=== FASE 8: Generación de Mapa Predictivo ===")
    
    m_pm25, m_pm10 = load_models()
    vars_pm25 = m_pm25["features"]
    vars_pm10 = m_pm10["features"]
    
    all_vars = list(set(vars_pm25 + vars_pm10))
    log.info(f"Variables necesarias a calcular para la red: {all_vars}")
    
    log.info("Cargando capas ...")
    streets = gpd.read_file(STREETS_GPKG)
    landuse = gpd.read_file(LANDUSE_GPKG)
    if landuse.crs != streets.crs:
        landuse = landuse.to_crs(streets.crs)
        
    # Preparar subcapas para agilizar
    # 1. Zonas industriales (para distancias)
    mask_ind = pd.Series(False, index=landuse.index)
    for col in ["landuse", "leisure"]:
        if col in landuse.columns:
            mask_ind = mask_ind | landuse[col].isin(LANDUSE_CATS["industrial"])
    ind_zones = landuse[mask_ind]
    
    # 2. Zonas verdes
    mask_green = pd.Series(False, index=landuse.index)
    for col in ["landuse", "leisure"]:
        if col in landuse.columns:
            mask_green = mask_green | landuse[col].isin(LANDUSE_CATS["green"])
    green_zones = landuse[mask_green]
    
    # 3. Calles residenciales
    streets["hw_norm"] = streets["highway"].apply(
        lambda x: x[0] if isinstance(x, list) else str(x).split(",")[0].strip().lower()
    )
    res_streets = streets[streets["hw_norm"].isin(HIGHWAY_CATS["residential"])]
    
    # CORRECCIÓN A4: en vez del centroide, interpolamos puntos a lo largo del tramo.
    # Para tramos cortos (<100m) usamos el centroide; para largos (≥100m) usamos
    # 3 puntos (25%, 50%, 75%) y promediamos las features. Esto evita que el buffer
    # de 100m desde el centroide de un tramo de 400m no cubra sus extremos.
    LONG_SEGMENT_THRESHOLD_M = 100.0
    N_INTERP_POINTS = 3  # fracciones: 0.25, 0.5, 0.75

    def get_sample_points(geom):
        """Devuelve lista de puntos de muestreo para un tramo."""
        length = geom.length
        if length < LONG_SEGMENT_THRESHOLD_M:
            return [geom.centroid]
        return [geom.interpolate(f, normalized=True)
                for f in [i/(N_INTERP_POINTS+1) for i in range(1, N_INTERP_POINTS+1)]]

    # Empezamos a llenar las variables
    X_df = pd.DataFrame(index=streets.index)

    total = len(streets)
    log.info(f"Iniciando cálculo para {total} tramos (interpolación multi-punto en tramos ≥{LONG_SEGMENT_THRESHOLD_M}m) ...")
    
    # Para hacerlo eficiente sin bucle infinito, calculamos las tres variables manualmente
    # ya que ya sabemos cuáles son.
    
    dist_industrial = []
    len_res_500 = []
    green_100 = []
    ind_ratio_250 = []

    for i, geom in enumerate(streets.geometry):
        sample_pts = get_sample_points(geom)

        # ── Por cada punto de muestreo, calculamos las features y promediamos ──
        d_vals, lr_vals, gr_vals, ir_vals = [], [], [], []

        for point in sample_pts:
            # 1. Dist industrial
            if len(ind_zones) > 0:
                d_vals.append(ind_zones.geometry.distance(point).min())
            else:
                d_vals.append(np.nan)

            # 2. Road length residencial 500m
            buf_500 = point.buffer(500)
            l = clip_and_length(res_streets[res_streets.geometry.intersects(buf_500)], buf_500)
            lr_vals.append(l)

            # 3. Green ratio 100m
            buf_100 = point.buffer(100)
            b100_area = buf_100.area
            green_intersect = green_zones[green_zones.geometry.intersects(buf_100)]
            g_area = clip_and_area(green_intersect, buf_100)
            gr_vals.append(g_area / b100_area if b100_area > 0 else 0.0)

            # 4. Industrial ratio 250m
            buf_250 = point.buffer(250)
            b250_area = buf_250.area
            ind_intersect = ind_zones[ind_zones.geometry.intersects(buf_250)]
            i_area = clip_and_area(ind_intersect, buf_250)
            ir_vals.append(i_area / b250_area if b250_area > 0 else 0.0)

        dist_industrial.append(float(np.nanmean(d_vals)))
        len_res_500.append(float(np.mean(lr_vals)))
        green_100.append(float(np.mean(gr_vals)))
        ind_ratio_250.append(float(np.mean(ir_vals)))

        if (i + 1) % 1000 == 0:
            log.info(f"  Tramos procesados: {i+1}/{total}")
            

    X_df["dist_industrial_m_50m"]          = dist_industrial
    X_df["road_length_residential_m_500m"] = len_res_500
    X_df["landuse_green_ratio_100m"]       = green_100
    X_df["landuse_industrial_ratio_250m"]  = ind_ratio_250

    # CORRECCIÓN A3: distancias NaN → centinela, no 0
    dist_cols = [c for c in X_df.columns if c.startswith("dist_")]
    for dc in dist_cols:
        max_val = X_df[dc].max()
        fill_val = max_val * 1.5 if (pd.notna(max_val) and max_val > 0) else 9999.0
        X_df[dc] = X_df[dc].fillna(fill_val)
        log.info(f"  NaN en '{dc}' rellenados con centinela={fill_val:.1f}m")

    # Predecir
    log.info("Calculando predicciones ...")

    # PM2.5
    X_pm25 = X_df[vars_pm25].fillna(0).values
    pred_pm25 = m_pm25["model"].predict(X_pm25)
    streets["pm25_pred"] = pred_pm25

    # PM10
    X_pm10 = X_df[vars_pm10].fillna(0).values
    pred_pm10 = m_pm10["model"].predict(X_pm10)
    streets["pm10_pred"] = pred_pm10

    # E2 — Intervalos de predicción bootstrap (90%)
    try:
        from sklearn.linear_model import RidgeCV as _RidgeCV
        features_csv = Path(__file__).resolve().parents[2] / "data" / "interim" / "lur_features.csv"
        if features_csv.exists():
            log.info("  Calculando intervalos bootstrap para el mapa (50 iteraciones) ...")
            import pandas as _pd

            df_feat = _pd.read_csv(features_csv)
            RIDGE_ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0]
            rng = np.random.default_rng(42)

            def _build_train(df, features, target):
                rows = []
                for sid in df["sensor_id"].unique():
                    rec = {}
                    sid_rows = df[df["sensor_id"] == sid]
                    rec[target] = sid_rows[target].iloc[0]
                    for feat in features:
                        no_m = feat[:-1]
                        idx  = no_m.rfind("_")
                        if idx > 0 and no_m[idx+1:].isdigit():
                            buf  = int(no_m[idx+1:])
                            base = feat[:idx]
                        else:
                            buf  = None
                            base = feat
                        sub = sid_rows[sid_rows["buffer_m"] == buf] if buf else sid_rows
                        rec[feat] = float(sub[base].iloc[0]) if (len(sub) > 0 and base in sub.columns) else 0.0
                    rows.append(rec)
                out = _pd.DataFrame(rows).fillna(0)
                return out[features].values, out[target].values

            for m_info, X_pred_np, col_lo, col_hi in [
                (m_pm25, X_pm25, "pm25_lo90", "pm25_hi90"),
                (m_pm10, X_pm10, "pm10_lo90", "pm10_hi90"),
            ]:
                tgt  = m_info["target"]
                feats = m_info["features"]
                X_tr, y_tr = _build_train(df_feat, feats, tgt)
                n = len(y_tr)
                boot_preds = np.zeros((50, len(X_pred_np)))
                for b in range(50):
                    idx = rng.integers(0, n, size=n)
                    mb  = _RidgeCV(alphas=RIDGE_ALPHAS, cv=None)
                    mb.fit(X_tr[idx], y_tr[idx])
                    boot_preds[b] = mb.predict(X_pred_np)
                streets[col_lo] = np.percentile(boot_preds, 5,  axis=0)
                streets[col_hi] = np.percentile(boot_preds, 95, axis=0)
                width = (streets[col_hi] - streets[col_lo]).mean()
                log.info(f"  Intervalo 90% {tgt}: ancho medio = {width:.2f} µg/m³")
        else:
            log.info("  lur_features.csv no encontrado — omitiendo intervalos bootstrap en mapa")
    except Exception as e:
        log.warning(f"  Intervalos bootstrap en mapa fallaron (no crítico): {e}")

    # Limpiar columnas complejas para exportar a GeoJSON
    drop_cols = ["road_idx", "dist_aadf_m", "index_aadf", "hw_cat", "hw_norm"]
    for c in drop_cols:
        if c in streets.columns:
            streets = streets.drop(columns=[c])

    # Proyectar a lat/lon normal para mapeo web/GeoJSON
    log.info("Transformando a EPSG:4326 (WGS84) para salida ...")
    streets_map = streets.to_crs("EPSG:4326")

    if OUT_GEOJSON.exists():
        OUT_GEOJSON.unlink()

    streets_map.to_file(OUT_GEOJSON, driver="GeoJSON")
    log.info(f"GeoJSON guardado exitosamente → {OUT_GEOJSON}")
    log.info("=== PROCESO COMPLETADO ===")


if __name__ == "__main__":
    main()
