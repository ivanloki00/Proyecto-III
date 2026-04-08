"""
Fase 2 - Sensor-to-Road Matching
Cada sensor se ajusta (snap) al tramo de carretera más cercano,
heredando el osmid, highway type, y la distancia al tramo.
"""

from pathlib import Path
import logging
import geopandas as gpd
import pandas as pd
from shapely.ops import nearest_points

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

ROOT = Path(__file__).resolve().parents[2]
DATA_INT  = ROOT / "data" / "interim"
DATA_RAW  = ROOT / "data"  / "raw"

SENSORS_GPKG  = DATA_INT / "sensores_2024_agregados.gpkg"
STREETS_GPKG  = DATA_RAW / "streets_liverpool.gpkg"
OUT_GPKG      = DATA_INT / "sensores_snapped.gpkg"
MAX_SNAP_DIST = 500  # metros – umbral máximo para aceptar el snap


def load_data():
    logging.info("Cargando sensores ...")
    sensors = gpd.read_file(SENSORS_GPKG)
    
    logging.info("Cargando red viaria ...")
    streets = gpd.read_file(STREETS_GPKG)
    
    # Asegurar mismo CRS
    if sensors.crs != streets.crs:
        streets = streets.to_crs(sensors.crs)
    
    logging.info(f"Sensores: {len(sensors)} | Tramos: {len(streets)}")
    return sensors, streets


def snap_sensors_to_roads(sensors: gpd.GeoDataFrame, streets: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Para cada sensor: 
    1. Encuentra el tramo más cercano (sjoin_nearest).
    2. Calcula la distancia exacta en metros.
    3. Proyecta el punto del sensor SOBRE la geometría del tramo (snap geom).
    4. Descarta sensores cuya distancia supere MAX_SNAP_DIST.
    """
    logging.info("Ejecutando sjoin_nearest ...")
    
    # Seleccionar columnas relevantes de la red viaria
    cols_road = ['geometry', 'highway', 'name', 'ref', 'maxspeed', 'oneway', 'lanes']
    cols_avail = [c for c in cols_road if c in streets.columns]
    streets_slim = streets[cols_avail].copy()
    streets_slim['road_idx'] = streets_slim.index
    
    matched = sensors.sjoin_nearest(
        streets_slim,
        how='left',
        max_distance=MAX_SNAP_DIST,
        distance_col='dist_to_road_m',
        rsuffix='road'
    )

    n_unmatched = matched['dist_to_road_m'].isna().sum()
    if n_unmatched > 0:
        logging.warning(f"{n_unmatched} sensores sin tramo dentro de {MAX_SNAP_DIST}m – se eliminarán.")
    matched = matched.dropna(subset=['dist_to_road_m']).copy()
    
    logging.info(f"Sensores emparejados: {len(matched)}")
    
    # Calcular la geometría 'snapped' del sensor proyectada sobre el tramo
    logging.info("Calculando geometría snapped sobre el tramo ...")
    
    street_geoms = streets_slim.set_index('road_idx')['geometry']
    
    snapped_geoms = []
    for _, row in matched.iterrows():
        road_geom = street_geoms.loc[row['road_idx']]
        sensor_pt = row['geometry']
        snapped_pt = nearest_points(sensor_pt, road_geom)[1]
        snapped_geoms.append(snapped_pt)
    
    matched['geometry_snapped'] = snapped_geoms
    
    logging.info("Snap completado.")
    return matched


def main():
    sensors, streets = load_data()
    snapped = snap_sensors_to_roads(sensors, streets)
    
    # Resumen estadístico del snap
    logging.info(f"\n--- Resumen de distancias de snap ---\n{snapped['dist_to_road_m'].describe().round(2)}")
    
    snapped.to_file(OUT_GPKG, driver="GPKG")
    logging.info(f"GeoPackage snapped guardado → {OUT_GPKG}")
    
    # Exportar CSV de resumen para inspección
    cols_csv = ['sensor_id', 'lat', 'lon', 'PM2.5', 'PM10', 'highway', 'name', 'dist_to_road_m']
    cols_csv_avail = [c for c in cols_csv if c in snapped.columns]
    snapped[cols_csv_avail].to_csv(DATA_INT / "sensores_snapped_summary.csv", index=False)
    logging.info("CSV de resumen guardado.")


if __name__ == "__main__":
    main()
