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
    
    # Para ser rápidos, como hay 8450 tramos, usamos el CENTROIDE de cada tramo
    centroids = streets.geometry.centroid
    
    # Empezamos a llenar las variables
    X_df = pd.DataFrame(index=streets.index)
    
    total = len(centroids)
    log.info(f"Iniciando cálculo para {total} tramos ...")
    
    # Para hacerlo eficiente sin bucle infinito, calculamos las tres variables manualmente
    # ya que ya sabemos cuáles son.
    
    dist_industrial = []
    len_res_500 = []
    green_100 = []
    ind_ratio_250 = []
    
    for i, point in enumerate(centroids):
        # 1. Dist industrial
        if len(ind_zones) > 0:
            d = ind_zones.geometry.distance(point).min()
        else:
            d = np.nan
        dist_industrial.append(d)
        
        # 2. Res 500m
        buf_500 = point.buffer(500)
        l = clip_and_length(res_streets[res_streets.geometry.intersects(buf_500)], buf_500)
        len_res_500.append(l)
        
        # 3. Green 100m
        buf_100 = point.buffer(100)
        b100_area = buf_100.area
        green_intersect = green_zones[green_zones.geometry.intersects(buf_100)]
        g_area = clip_and_area(green_intersect, buf_100)
        green_100.append(g_area / b100_area if b100_area > 0 else 0.0)

        # 4. Industrial ratio 250m
        buf_250 = point.buffer(250)
        b250_area = buf_250.area
        ind_intersect = ind_zones[ind_zones.geometry.intersects(buf_250)]
        i_area = clip_and_area(ind_intersect, buf_250)
        ind_ratio_250.append(i_area / b250_area if b250_area > 0 else 0.0)
        
        if (i+1) % 1000 == 0:
            log.info(f"  Tramos procesados: {i+1}/{total}")
            
    X_df["dist_industrial_m_50m"] = dist_industrial
    X_df["road_length_residential_m_500m"] = len_res_500
    X_df["landuse_green_ratio_100m"] = green_100
    X_df["landuse_industrial_ratio_250m"] = ind_ratio_250
    
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
