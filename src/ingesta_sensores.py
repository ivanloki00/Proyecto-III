"""
WP1.1: Ingesta y Limpieza de Sensores (Issue #16)

Asignados: ivanloki00, Juanjocepe05
Dificultad: 5/10

Descripción:
Transformar los datos brutos de los 40 sensores de Liverpool en un dataset limpio, 
estandarizado y listo para el análisis temporal y el modelado espacial.
"""

import pandas as pd
import os
import glob

def cargar_y_unificar_csvs(ruta_datos_brutos: str) -> pd.DataFrame:
    """
    Paso 1 y 2: Descarga e Inspección / Unificación de Datos
    Carga todos los archivos CSV de la ruta indicada y unifícalos en un solo DataFrame.
    """
    # TODO: Escribe el código para leer y concatenar los CSVs.
    # Sugerencia: Usa glob.glob o os.listdir junto con pd.concat
    pass

def estandarizar_tiempo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Paso 3: Estandarización Temporal
    Convierte todas las marcas de tiempo a un formato datetime único y 
    asegúrate de que los intervalos de 30 minutos sean coherentes.
    """
    # TODO: Usa pd.to_datetime en la columna correspondiente.
    pass

def control_de_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """
    Paso 4: Control de Calidad
    - Identificar y tratar valores nulos (ej. interpolación u omitirlos si conviene).
    - Detectar y filtrar outliers (valores absurdos de sensores).
    - Gestionar posibles duplicados.
    """
    # TODO: Implementa la limpieza de nulos y atípicos
    pass

def asociar_coordenadas(df_lecturas: pd.DataFrame, ruta_coordenadas: str) -> pd.DataFrame:
    """
    Paso 5: Asociación Geoespacial
    Vincula cada lectura de sensor con sus coordenadas usando el archivo base.
    """
    # TODO: Lee el CSV de coordenadas y haz un merge (join) con df_lecturas por 'sensor_id'
    pass

def ejecutar_pipeline_ingesta(ruta_entrada: str, ruta_salida: str, ruta_coords: str):
    """
    Ejecuta todo el flujo: carga, estandariza, limpia, une coordenadas y guarda el CSV final.
    """
    print("Iniciando ingesta de datos de sensores...")
    
    # TODO: Descomenta estas líneas a medida que vayas implementando las funciones de arriba
    
    # df = cargar_y_unificar_csvs(ruta_entrada)
    # df = estandarizar_tiempo(df)
    # df = control_de_calidad(df)
    # df_final = asociar_coordenadas(df, ruta_coords)
    
    # df_final.to_csv(ruta_salida, index=False)
    # print(f"Pipeline finalizado con éxito. Datos guardados en {ruta_salida}")
    
    pass

if __name__ == "__main__":
    # Rutas relativas, asumiendo que ejecutaremos el script desde la carpeta raíz del proyecto
    RUTA_ENTRADA = "data/raw/DatosCompletos"
    RUTA_COORDENADAS = "data/raw/CoordsSensores.csv"
    RUTA_SALIDA = "data/processed/sensors_cleaned.csv"
    
    ejecutar_pipeline_ingesta(RUTA_ENTRADA, RUTA_SALIDA, RUTA_COORDENADAS)
