"""
WP1.1: Ingesta y Limpieza de Sensores (Issue #16)

Asignados: ivanloki00, Juanjocepe05
Dificultad: 5/10

Descripción:
Transformar los datos brutos de los 40 sensores de Liverpool en un dataset limpio, 
estandarizado y listo para el análisis temporal y el modelado espacial.
Se integran estrategias avanzadas de remuestreo horario y control de calidad físico.
"""

import pandas as pd
import os
import glob

def cargar_y_unificar_csvs(ruta_datos_brutos: str) -> pd.DataFrame:
    """
    Paso 1: Unificación de Datos en formato Tidy
    Carga todos los archivos CSV de la ruta indicada y unifícalos en un solo DataFrame.
    (Nota: Los datos ya han sido descargados en la carpeta data/raw/DatosCompletos)
    El DataFrame debe tener (como mínimo) las columnas clave combinadas: 
    [timestamp, sensor_id, pm1, pm2.5, pm10, temp, humidity]
    """
    # TODO: Escribe el código para leer y concatenar los CSVs.
    # Sugerencia: Usa glob.glob junto con pd.concat y extrae el sensor_id del nombre del archivo.
    pass

def estandarizar_y_remuestrear(df: pd.DataFrame) -> pd.DataFrame:
    """
    Paso 2: Estandarización Temporal y Remuestreo (Resample)
    Los sensores suelen reportar cada 30 min, pero hay desfases.
    Fija todas las marcas de tiempo a formato datetime único y haz un Resample a intervalos 
    fijos (ej. cada 1 hora) promediando los valores. Así alinearás temporalmente las series.
    """
    # TODO: 
    # 1. Asegurar formato datetime (pd.to_datetime).
    # 2. Agrupar por sensor_id y aplicar .resample('1H').mean() para crear intervalos fijos de 1h.
    pass

def control_de_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """
    Paso 3: Limpieza Crítica de Sensores de Bajo Coste (Aeternum Innovations)
    - Valores Atípicos (Outliers): Filtrar picos imposibles o errores de lectura 
      (ej. PM2.5 > 500 que duran un solo registro).
    - Compensación por Humedad: Las partículas de agua se confunden con PM. 
      Si la humedad > 85-90%, considera aplicar una fórmula o flaggear esos datos.
    - Gaps (Huecos): Identifica periodos de inactividad de los sensores para no sesgar las medias.
    """
    # TODO: 
    # 1. Elimina o marca registros donde PM2.5 > 500
    # 2. Gestiona la humedad muy alta (ej. df.loc[df['Humidity'] > 85, 'PM2.5'] = ...)
    # 3. Elimina sensores o tramos si exceden un % de Nulos o Gaps continuados.
    pass

def asociar_coordenadas(df_lecturas: pd.DataFrame, ruta_coordenadas: str) -> pd.DataFrame:
    """
    Paso 4: Asociación Geoespacial (Metadatos)
    El archivo auxiliar contiene latitud, longitud y nombre del sitio. Vital para el WP espacial.
    """
    # TODO: Lee el CSV de CoordsSensores y haz un merge (join) con df_lecturas por 'sensor_id'.
    pass

def ejecutar_pipeline_ingesta(ruta_entrada: str, ruta_salida: str, ruta_coords: str):
    """
    Motor principal que ejecuta todo el flujo.
    """
    print("Iniciando ingesta de datos de sensores...")
    
    # TODO: Ve descomentando estas líneas a medida que vayas implementando las funciones
    
    # df = cargar_y_unificar_csvs(ruta_entrada)
    # df = estandarizar_y_remuestrear(df)
    # df = control_de_calidad(df)
    # df_final = asociar_coordenadas(df, ruta_coords)
    
    # df_final.to_csv(ruta_salida, index=False)
    # print(f"Pipeline finalizado con éxito. Datos guardados en {ruta_salida}")
    
    pass

if __name__ == "__main__":
    RUTA_ENTRADA = "../data/raw/DatosCompletos"
    RUTA_COORDENADAS = "../data/raw/CoordsSensores.csv"
    RUTA_SALIDA = "../data/processed/sensors_cleaned.csv"
    
    ejecutar_pipeline_ingesta(RUTA_ENTRADA, RUTA_SALIDA, RUTA_COORDENADAS)
