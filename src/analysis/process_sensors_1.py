import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PROC = ROOT / "data" / "processed"
DATA_INT = ROOT / "data" / "interim"
DATA_INT.mkdir(exist_ok=True)

def process_sensor_data_2024():
    input_file = DATA_PROC / "sensors_definitivo.csv"
    logging.info(f"Leyendo dataset de sensores: {input_file}")
    
    # Especificar columnas para minimizar memoria, aunque datetime no sabemos el formato exacto aún. Lo leemos como texto y convertimos.
    df = pd.read_csv(input_file)
    
    logging.info(f"Total registros: {len(df)}")
    
    # Convertir a datetime
    df['datetime'] = pd.to_datetime(df['datetime'], format='mixed', errors='coerce')
    
    # Filtrar solo 2024
    df_2024 = df[df['datetime'].dt.year == 2024].copy()
    logging.info(f"Registros en 2024: {len(df_2024)}")
    
    if len(df_2024) == 0:
        logging.error("No hay registros para 2024!")
        return

    # Umbral de completitud (75% del año). Un año tiene 366 días (2024 es bisiesto).
    # O si es hora: 366 * 24 = 8784 horas. El 75% es 6588 horas.
    # Dado que los sensores parecen medir cada 30 min, serian 366 * 48 = 17568 mediciones. 75% = 13176
    
    # Revisamos conteo total por sensor
    conteos = df_2024.groupby('sensor_id').size()
    max_mediciones_posibles = df_2024.groupby('sensor_id')['datetime'].nunique().max()
    threshold = int(max_mediciones_posibles * 0.75)
    
    logging.info(f"Máximo mediciones únicas en un sensor: {max_mediciones_posibles}. Umbral de 75%: {threshold}")
    
    sensores_validos_counts = conteos[conteos >= threshold]
    valid_sensor_ids = set(sensores_validos_counts.index)
    
    logging.info(f"Sensores que cumplen el umbral de 75%: {len(valid_sensor_ids)} de {len(conteos)}")
    
    df_validos = df_2024[df_2024['sensor_id'].isin(valid_sensor_ids)].copy()
    
    if 'tipo' in df_validos.columns:
        # Quizas DEFRA es un sensor valido tmb, no lo filtramos
        pass
        
    resumen = df_validos.groupby(['sensor_id', 'lat', 'lon'], as_index=False)[['PM2.5', 'PM10']].mean()
    
    output_file = DATA_INT / "sensores_2024_agregados.csv"
    resumen.to_csv(output_file, index=False)
    logging.info(f"Archivo guardado: {output_file}")

    # NOTA: En el CSV, 'lat' tiene valores ~-3 (longitud) y 'lon' tiene valores ~53 (latitud)
    # A pesar del nombre, lat ≈ lon_real y lon ≈ lat_real. Construimos correctamente:
    # x = longitud real (columna 'lat'), y = latitud real (columna 'lon')
    gdf = gpd.GeoDataFrame(
        resumen,
        geometry=gpd.points_from_xy(resumen['lat'], resumen['lon']),  # x=lon_real(≈-3), y=lat_real(≈53)
        crs="EPSG:4326"
    ).to_crs("EPSG:27700")
    
    gpkg_file = DATA_INT / "sensores_2024_agregados.gpkg"
    gdf.to_file(gpkg_file, driver="GPKG")
    logging.info(f"Archivo GeoPackage guardado en EPSG:27700: {gpkg_file}")

if __name__ == "__main__":
    process_sensor_data_2024()
