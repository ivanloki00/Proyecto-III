"""
WP1.1: Ingesta y Limpieza de Sensores (Issue #16)

Asignados: ivanloki00, Juanjocepe05
Dificultad: 5/10

Descripción:
Transformar los datos brutos de los 40 sensores de Liverpool en un dataset limpio, 
estandarizado y listo para el análisis temporal y el modelado espacial.
Se integran estrategias avanzadas de remuestreo horario y control de calidad físico.

Uso:
    Ejecutar desde la carpeta src/:
        python ingesta_sensores.py
    
    O importar desde el notebook central:
        from src.ingesta_sensores import ejecutar_pipeline_ingesta
        df = ejecutar_pipeline_ingesta(...)
"""

import pandas as pd
import numpy as np
import os
import glob
import warnings

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# ---------------------------------------------------------------------------
# CONSTANTES DE CONFIGURACIÓN
# ---------------------------------------------------------------------------
# Umbral físico máximo razonable para PM (µg/m³). Valores por encima son errores.
PM_MAX_THRESHOLD = 500.0
# Umbral mínimo: los valores negativos o centinela (ej. -1.4e31) son errores de sensor.
PM_MIN_THRESHOLD = 0.0
# Humedad por encima de la cual los PM se inflan artificialmente (partículas de agua).
HUMIDITY_HIGH_THRESHOLD = 85.0
# Porcentaje máximo de NaNs permitidos para un sensor antes de descartarlo.
MAX_NAN_RATIO = 0.50  # 50%
# Intervalo de remuestreo temporal.
RESAMPLE_FREQ = "1h"


def cargar_y_unificar_csvs(ruta_datos_brutos: str) -> pd.DataFrame:
    """
    Paso 1: Carga todos los CSVs de sensores y los unifica en un solo DataFrame tidy.
    Extrae el sensor_id del nombre del archivo (tercer segmento separado por '_').
    
    Resultado: DataFrame con columnas:
      [sensor_id, datetime, Temperature, Humidity, PM1.0, PM2.5, PM10]
    """
    archivos = glob.glob(os.path.join(ruta_datos_brutos, "*.csv"))
    
    if not archivos:
        raise FileNotFoundError(f"No se encontraron CSVs en {ruta_datos_brutos}")
    
    print(f"  -> Encontrados {len(archivos)} archivos CSV.")
    
    lista_df = []
    errores = []
    
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo, low_memory=False)
            
            # Extraer sensor_id del nombre: data_aeternum_<SENSOR_ID>_<fechas>.csv
            nombre = os.path.basename(archivo)
            partes = nombre.split("_")
            sensor_id = partes[2]  # Tercer segmento
            
            df["sensor_id"] = sensor_id
            lista_df.append(df)
        except Exception as e:
            errores.append((archivo, str(e)))
    
    if errores:
        print(f"  [!] {len(errores)} archivos con errores de lectura:")
        for path, err in errores[:5]:
            print(f"     - {os.path.basename(path)}: {err}")
    
    df_total = pd.concat(lista_df, ignore_index=True)
    print(f"  -> DataFrame unificado: {df_total.shape[0]:,} registros de {df_total['sensor_id'].nunique()} sensores.")
    
    return df_total


def estandarizar_y_remuestrear(df: pd.DataFrame) -> pd.DataFrame:
    """
    Paso 2: Estandarización Temporal y Remuestreo.
    - Convierte 'Date & Time' a datetime.
    - Ordena cronológicamente por sensor.
    - Remuestrea a intervalos fijos de 1 hora promediando valores.
    """
    # Convertir a datetime
    df["datetime"] = pd.to_datetime(df["Date & Time"], errors="coerce")
    df = df.drop(columns=["Date & Time"])
    
    # Eliminar filas sin fecha válida
    n_antes = len(df)
    df = df.dropna(subset=["datetime"])
    n_perdidos = n_antes - len(df)
    if n_perdidos > 0:
        print(f"  [!] Eliminadas {n_perdidos:,} filas con fecha invalida.")
    
    # Convertir columnas de medición a numérico (fuerza errores de texto a NaN)
    cols_medicion = ["Temperature", "Humidity", "PM1.0", "PM2.5", "PM10"]
    for col in cols_medicion:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Ordenar
    df = df.sort_values(["sensor_id", "datetime"]).reset_index(drop=True)
    
    # Remuestrear a intervalos fijos de 1 hora por sensor
    print(f"  -> Remuestreando a intervalos de {RESAMPLE_FREQ}...")
    resampled_dfs = []
    
    for sensor_id, grupo in df.groupby("sensor_id"):
        grupo = grupo.set_index("datetime")
        grupo_resampled = grupo[cols_medicion].resample(RESAMPLE_FREQ).mean()
        grupo_resampled["sensor_id"] = sensor_id
        resampled_dfs.append(grupo_resampled)
    
    df_resampled = pd.concat(resampled_dfs).reset_index()
    
    print(f"  -> Post-resample: {df_resampled.shape[0]:,} registros horarios.")
    return df_resampled


def control_de_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """
    Paso 3: Limpieza Crítica de Sensores de Bajo Coste (Aeternum Innovations).
    
    1. Valores centinela: Detecta y elimina valores absurdos (ej. -1.4e31).
    2. Outliers físicos: Marca como NaN los PM fuera del rango [0, 500] µg/m³.
    3. Flag de humedad alta: Marca registros donde Humidity > 85% (PM posiblemente inflado).
    4. Gaps: Descarta sensores con más del 50% de NaNs en PM2.5.
    5. Interpolación: Rellena huecos pequeños con interpolación lineal por sensor.
    """
    cols_pm = ["PM1.0", "PM2.5", "PM10"]
    
    # --- 1. Valores centinela y outliers físicos ---
    for col in cols_pm:
        n_invalidos = ((df[col] < PM_MIN_THRESHOLD) | (df[col] > PM_MAX_THRESHOLD)).sum()
        df.loc[(df[col] < PM_MIN_THRESHOLD) | (df[col] > PM_MAX_THRESHOLD), col] = np.nan
        if n_invalidos > 0:
            print(f"  -> {col}: {n_invalidos:,} valores fuera de rango [{PM_MIN_THRESHOLD}, {PM_MAX_THRESHOLD}] -> NaN")
    
    # --- 2. Flag de humedad alta ---
    df["high_humidity_flag"] = df["Humidity"] > HUMIDITY_HIGH_THRESHOLD
    n_humid = df["high_humidity_flag"].sum()
    print(f"  -> {n_humid:,} registros con humedad > {HUMIDITY_HIGH_THRESHOLD}% (flaggeados).")
    
    # --- 3. Descartar sensores con demasiados huecos ---
    sensores_antes = df["sensor_id"].nunique()
    nan_ratio = df.groupby("sensor_id")["PM2.5"].apply(lambda x: x.isna().mean())
    sensores_malos = nan_ratio[nan_ratio > MAX_NAN_RATIO].index.tolist()
    
    if sensores_malos:
        print(f"  [!] Descartando {len(sensores_malos)} sensores con > {MAX_NAN_RATIO*100:.0f}% NaNs en PM2.5:")
        for s in sensores_malos:
            print(f"     - {s} ({nan_ratio[s]*100:.1f}% NaN)")
        df = df[~df["sensor_id"].isin(sensores_malos)]
    
    print(f"  -> Sensores activos: {df['sensor_id'].nunique()} (de {sensores_antes} originales).")
    
    # --- 4. Interpolación lineal por sensor ---
    cols_interp = ["Temperature", "Humidity"] + cols_pm
    for col in cols_interp:
        df[col] = df.groupby("sensor_id")[col].transform(
            lambda x: x.interpolate(method="linear", limit=6)  # max 6h de gap
        )
    
    # Estadísticas finales de NaN
    total_nans = df[cols_pm].isna().sum()
    print(f"  -> NaNs restantes post-interpolacion:")
    for col in cols_pm:
        print(f"     - {col}: {total_nans[col]:,}")
    
    return df


def asociar_coordenadas(df_lecturas: pd.DataFrame, ruta_coordenadas: str) -> pd.DataFrame:
    """
    Paso 4: Asociación Geoespacial.
    Vincula cada lectura de sensor con lat/lon/label usando CoordsSensores.csv.
    
    NOTA: El CSV original tiene las columnas como 'lon' y 'lat',
    pero al inspeccionar los valores observamos que 'lon' contiene latitudes (~53.x)
    y 'lat' contiene longitudes (~-2.x). Los renombramos correctamente.
    """
    df_coords = pd.read_csv(ruta_coordenadas)
    df_coords["sensor_id"] = df_coords["sensor_id"].astype(str)
    
    # Renombrar columnas: el CSV base tiene lon=latitud, lat=longitud (están cruzadas) 
    df_coords = df_coords.rename(columns={"lon": "latitude", "lat": "longitude"})
    
    # Seleccionar solo las columnas que nos interesan
    df_coords = df_coords[["sensor_id", "latitude", "longitude", "label"]]
    
    # Merge
    df_lecturas["sensor_id"] = df_lecturas["sensor_id"].astype(str)
    df_final = df_lecturas.merge(df_coords, on="sensor_id", how="left")
    
    sin_coords = df_final["latitude"].isna().sum()
    if sin_coords > 0:
        print(f"  [!] {sin_coords:,} registros sin coordenadas asociadas.")
    
    # Redondear valores numéricos para reducir peso del CSV
    for col in ["Temperature", "Humidity"]:
        df_final[col] = df_final[col].round(2)
    for col in ["PM1.0", "PM2.5", "PM10"]:
        df_final[col] = df_final[col].round(4)
    
    return df_final


def ejecutar_pipeline_ingesta(
    ruta_entrada: str, 
    ruta_salida: str, 
    ruta_coords: str
) -> pd.DataFrame:
    """
    Motor principal: ejecuta todo el flujo de ingesta y devuelve el DataFrame final.
    """
    print("=" * 60)
    print(">> PIPELINE DE INGESTA - SENSORES LIVERPOOL")
    print("=" * 60)
    
    # Paso 1: Cargar y unificar
    print("\n[1] Paso 1: Cargando y unificando CSVs...")
    df = cargar_y_unificar_csvs(ruta_entrada)
    
    # Paso 2: Estandarizar tiempo y remuestrear
    print("\n[2] Paso 2: Estandarizacion temporal y remuestreo a 1h...")
    df = estandarizar_y_remuestrear(df)
    
    # Paso 3: Control de calidad
    print("\n[3] Paso 3: Control de calidad y limpieza...")
    df = control_de_calidad(df)
    
    # Paso 4: Asociar coordenadas
    print("\n[4] Paso 4: Asociacion geoespacial...")
    df_final = asociar_coordenadas(df, ruta_coords)
    
    # Guardar resultado
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    df_final.to_csv(ruta_salida, index=False)
    
    print("\n" + "=" * 60)
    print(f"[OK] Pipeline finalizado con exito!")
    print(f"   -> Registros finales: {df_final.shape[0]:,}")
    print(f"   -> Sensores activos:  {df_final['sensor_id'].nunique()}")
    print(f"   -> Rango temporal:    {df_final['datetime'].min()} -> {df_final['datetime'].max()}")
    print(f"   -> Guardado en:       {ruta_salida}")
    print("=" * 60)
    
    return df_final


if __name__ == "__main__":
    RUTA_ENTRADA = "../data/raw/DatosCompletos"
    RUTA_COORDENADAS = "../data/raw/CoordsSensores.csv"
    RUTA_SALIDA = "../data/processed/sensors_cleaned.csv"
    
    ejecutar_pipeline_ingesta(RUTA_ENTRADA, RUTA_SALIDA, RUTA_COORDENADAS)
