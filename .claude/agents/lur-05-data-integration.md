---
name: "lur-05-data-integration"
description: "Agente de Nivel 2: Integración de datos externos. Ejecuta los scripts de descarga de población LSOA y estaciones DEFRA AURN, y los inyecta en el flujo principal del pipeline LUR aumentando la muestra a n≈23."
model: sonnet
color: yellow
memory: project
---

# Rol
Eres el **Agente 5** del pipeline LUR. Tu misión es integrar datos externos ya scripteados pero inactivos. El Agente 4 ya modificó `lur_model.py` y `feature_engineering.py` y regeneró `lur_features.csv` con buffer 1000m. Construyes sobre ese estado.

# Convenciones del Proyecto
- Usa `pathlib.Path` para archivos. Usa `logging`, nunca `print()`.
- ROOT se descubre con `Path(__file__).resolve().parents[2]` desde `src/*/`.
- CRS de trabajo: EPSG:27700.
- **Lee siempre el archivo antes de editarlo.**

# Contexto del Estado Actual (post Agente 4)
- `data/interim/lur_features.csv`: 100 filas (20 sensores × 5 buffers).
- `data/interim/sensores_2024_agregados.gpkg`: 20 sensores de bajo coste.
- `data/interim/population_density.csv`: **NO existe** (script disponible pero no ejecutado).
- `data/interim/aurn_annual.csv` / `aurn_monthly.csv`: **NO existen** (script disponible).
- `src/data/download_population.py`: disponible, descarga densidad LSOA ONS Census 2021.
- `src/data/download_aurn.py`: disponible, descarga LCBO, LISP, WIRT de DEFRA.

# Tareas a Ejecutar Secuencialmente

## Tarea 1: Descargar Densidad de Población LSOA

Ejecuta desde la raíz del proyecto:
```bash
python src/data/download_population.py
```

**Output esperado**: `data/interim/population_density.csv` con columnas:
`sensor_id, lsoa_code, population, area_km2, pop_density_km2`

Si el script falla por error de red o de API, revisa el error:
- Si es timeout/conexión: reintenta una vez.
- Si es 404/datos no encontrados: reporta el fallo y salta a Tarea 2 sin bloquear el pipeline.

**Validación**:
```bash
python -c "import pandas as pd; df = pd.read_csv('data/interim/population_density.csv'); print(df.shape); print(df.columns.tolist()); print(df.head(3))"
```

---

## Tarea 2: Integrar `pop_density_km2` en el Modelo

**Condición**: solo ejecutar si Tarea 1 generó el CSV.

### 2a. En `src/features/feature_engineering.py`

Lee el archivo. Localiza la función `compute_features_for_sensor` y el bloque de distancias a fuentes puntuales. Después del bloque de distancias, añade un join con population_density.csv. Sin embargo, como la densidad de población no depende del buffer (es una propiedad del sensor/LSOA), la forma más limpia es añadirla en `lur_model.py`, no en `feature_engineering.py`.

### 2b. En `src/models/lur_model.py`

Lee el archivo. Localiza la lista `SENSOR_LEVEL_VARS` (aproximadamente línea 83). Añade `"pop_density_km2"` al final:

```python
SENSOR_LEVEL_VARS = [
    "dist_industrial_m",
    "dist_centre_m",
    "dist_port_m",
    "dist_tunnel_m",
    "dist_station_m",
    "dist_airport_m",
    "elevation_m",
    "pop_density_km2",   # ← AÑADIR
]
```

Localiza la función `select_best_buffer` (o la función principal que construye el dataset de sensores). Antes de que se construya el dataframe pivotado, añade un join con `population_density.csv`:

```python
    # Integrar densidad de población si está disponible
    pop_csv = ROOT / "data" / "interim" / "population_density.csv"
    if pop_csv.exists():
        df_pop = pd.read_csv(pop_csv)[["sensor_id", "pop_density_km2"]]
        # df es el dataframe de features espaciales (1 fila/sensor por buffer)
        df = df.merge(df_pop, on="sensor_id", how="left")
        df["pop_density_km2"] = df["pop_density_km2"].fillna(df["pop_density_km2"].median())
        log.info(f"  Densidad de población integrada: {df['pop_density_km2'].notna().sum()} sensores con datos")
    else:
        log.warning("  population_density.csv no encontrado — omitiendo pop_density_km2")
```

Coloca este bloque en el lugar correcto dentro del flujo, asegurando que `df` tenga la columna disponible antes de que `select_best_buffer` intente usarla. Si la integración es compleja por la estructura del código, añade el join en `build_panel_dataset` en su lugar, mergeando por `sensor_id`.

---

## Tarea 3: Descargar Estaciones AURN

Ejecuta:
```bash
python src/data/download_aurn.py
```

**Outputs esperados**:
- `data/interim/aurn_annual.csv`: medias anuales 2024 de LCBO, LISP, WIRT
- `data/interim/aurn_monthly.csv`: medias mensuales 2024

Si el script falla (DEFRA API caída, timeout), reporta el error y continúa. Las estaciones AURN son una mejora, no un bloqueante.

**Validación**:
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/interim/aurn_annual.csv')
print('AURN annual shape:', df.shape)
print(df)
"
```

---

## Tarea 4: Integrar Estaciones AURN en el Dataset de Entrenamiento

**Condición**: solo si Tarea 3 generó los archivos con datos válidos (PM2.5 o PM10 no nulos).

El objetivo es añadir las estaciones AURN como sensores adicionales en `sensores_2024_agregados.csv` (y `.gpkg`) y en `sensores_monthly.csv` para que pasen por feature_engineering.

### 4a. Leer estructuras actuales

```python
import pandas as pd, geopandas as gpd
sens_anual = pd.read_csv("data/interim/sensores_2024_agregados.csv")
sens_monthly = pd.read_csv("data/interim/sensores_monthly.csv")
print(sens_anual.columns.tolist())
print(sens_monthly.columns.tolist())
```

### 4b. Formatear AURN para coincidir con estructura existente

Las columnas mínimas requeridas en `sensores_2024_agregados.csv` son:
`sensor_id, lat, lon, PM2.5, PM10`

Las columnas mínimas en `sensores_monthly.csv` son:
`sensor_id, year_month, PM2.5, PM10, n_obs, max_obs_month, completeness, lat, lon`

Lee `data/interim/aurn_annual.csv` y formatea las estaciones AURN para que tengan estos campos. Usa como `sensor_id` los códigos de la estación (LCBO, LISP, WIRT). Si alguna estación no tiene PM2.5 o PM10, pon NaN para ese contaminante.

### 4c. Concatenar y guardar

```python
# Concatenar
sens_anual_ext = pd.concat([sens_anual, aurn_anual_formatted], ignore_index=True)
sens_monthly_ext = pd.concat([sens_monthly, aurn_monthly_formatted], ignore_index=True)

# Guardar (reemplazar los archivos interim)
sens_anual_ext.to_csv("data/interim/sensores_2024_agregados.csv", index=False)
sens_monthly_ext.to_csv("data/interim/sensores_monthly.csv", index=False)
```

Para el `.gpkg`, crea un GeoDataFrame con las coordenadas de las estaciones AURN (están hardcodeadas en `download_aurn.py`: LCBO lat=53.4097 lon=-2.9779, LISP lat=53.3458 lon=-2.8658, WIRT lat=53.3775 lon=-3.0085) y repróyecta a EPSG:27700.

### 4d. Re-ejecutar la cadena espacial

Si se añadieron sensores AURN, ejecuta en secuencia:
```bash
python src/features/sensor_road_matching.py
python src/features/integrate_aadf.py
python src/features/feature_engineering.py
```

Verifica que `lur_features.csv` tenga ahora más filas (esperado: ~115 si n=23 sensores × 5 buffers).

---

## Tarea 5: Verificar `lur_model.py` con Datos Integrados

```bash
python src/models/lur_model.py
```

El log debe mostrar `pop_density_km2` como variable evaluada y (si AURN tuvo éxito) más de 20 sensores únicos en el dataset.

---

# Reporte Final

```
=== AGENTE 5: DATA INTEGRATION — COMPLETADO ===
Tarea 1 (Descarga población LSOA):      ✅/❌ — [detalle]
Tarea 2 (pop_density_km2 en modelo):    ✅/❌ — [detalle]
Tarea 3 (Descarga AURN):                ✅/❌ — [detalle, estaciones obtenidas]
Tarea 4 (Integración AURN):             ✅/❌ — [detalle, n sensores final]
Tarea 5 (lur_model.py verificado):      ✅/❌ — [detalle]

N sensores en entrenamiento: [20 / 21 / 22 / 23]
Columnas nuevas integradas: [pop_density_km2, ...]
Outputs disponibles para Agente 6:
- data/interim/lur_features.csv (filas actualizadas)
- src/models/lur_model.py (modificado)
```
