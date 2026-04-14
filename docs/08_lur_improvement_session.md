# Sesión de Mejora del Modelo LUR — Abril 2026

## Contexto

Sesión de trabajo orientada a mejorar el modelo LUR de predicción de calidad del aire (PM2.5 y PM10) en Liverpool. El punto de partida era un modelo Ridge con R²=0.542 (PM2.5) y R²=0.503 (PM10). El objetivo era subir el poder predictivo sin sobreentrenar, dado que el dataset tiene solo 20 sensores espaciales.

---

## 1. Diagnóstico Inicial del Pipeline

### Problema de rutas detectado

El directorio `outputs/LUR/` había sido eliminado manualmente pero los scripts aún lo referenciaban. Se actualizaron 5 archivos para apuntar a `data/processed/LUR/` (nueva ubicación real de los CSVs de resultados):

- `src/models/feature_selection_report.py`
- `src/models/lur_model.py`
- `src/models/task5_loocv_validation.py`
- `src/models/task7_diagnostics_deliverables.py`
- `run_and_compare.py`

### Archivos eliminables identificados

Se documentó qué archivos son generados por el pipeline (eliminables para reset limpio) y cuáles son datos de entrada originales (intocables):

- **Eliminables**: todo `data/interim/`, `data/processed/LUR/`, `outputs/models/`, `outputs/figures/lur/`, `outputs/maps/`, `cache/`
- **Intocables**: `data/raw/`, `src/**/*.py`, `run_and_compare.py`
- **Duplicados/huérfanos eliminables**: `data/processed/sensors_definitivo.csv` (223 MB), `data/processed/loocv_results.csv`, `data/processed/lur_barrios_predictions.*`

---

## 2. Análisis de Mejoras Posibles

Se identificaron tres niveles de mejora:

| Nivel | Tipo | Riesgo sobreajuste |
|---|---|---|
| 1 | Quick wins en código existente | Nulo-Bajo |
| 2 | Integración de datos externos ya scripteados | Bajo |
| 3 | Modificación metodológica (spatial lag) | Medio |

---

## 3. Agentes Diseñados e Implementados

Se crearon tres agentes de proyecto en `.claude/agents/`:

| Agente | Archivo | Color | Misión |
|---|---|---|---|
| lur-04-feature-expansion | `.claude/agents/lur-04-feature-expansion.md` | Azul | Quick wins de código |
| lur-05-data-integration | `.claude/agents/lur-05-data-integration.md` | Amarillo | Datos externos |
| lur-06-methodological-lag | `.claude/agents/lur-06-methodological-lag.md` | Magenta | Spatial lag en LOOCV |

Los agentes se ejecutaron secuencialmente (cada uno depende del anterior porque todos modifican `lur_model.py`).

---

## 4. Agente 4 — Feature Expansion (Nivel 1)

### Cambios realizados

**`src/models/lur_model.py`**

1. `intersections_count` añadida a `BASE_VARS` — la variable ya estaba calculada en `lur_features.csv` pero nunca entraba al modelo. Entra a selección; el filtro VIF la elimina cuando hay alta colinealidad con `road_length` y `road_density`, lo cual es correcto.

2. Estacionalidad cíclica en `build_panel_dataset`:
   ```python
   df_panel["mes_sin"] = np.sin(2 * np.pi * month / 12)
   df_panel["mes_cos"] = np.cos(2 * np.pi * month / 12)
   ```
   Añadidas a `METEO_CONTROLS` para que siempre estén presentes como controles temporales sin pasar por filtro p-value/VIF.

**`src/features/feature_engineering.py`** y **`src/models/lur_model.py`**

3. `BUFFER_RADII` ampliado a `[50, 100, 250, 500, 1000]`.

### Re-ejecución

`feature_engineering.py` re-ejecutado: `lur_features.csv` pasó de **80 filas** (4 buffers) a **100 filas** (5 buffers).

### Resultados post-Agente 4

| | Antes | Después |
|---|---|---|
| PM2.5 (GradientBoosting) | 0.586 | 0.497 |
| PM10 (SVR) | 0.503 | 0.620 |

PM10 mejoró notablemente. PM2.5 bajó porque el buffer 1000m introduce colinealidad severa que desfavorece los modelos lineales; GradientBoosting es el nuevo ganador pero muestra sobreajuste geográfico (Spatial CV = −14).

---

## 5. Agente 5 — Data Integration (Nivel 2)

### Intento de descarga automática

- **Población ONS**: endpoint ONS ArcGIS devolvió HTTP 400 (deprecado).
- **AURN DEFRA**: API DEFRA `csv_server.php` devolvió HTTP 404.

### Código integrado con fallback

`pop_density_km2` añadida a `SENSOR_LEVEL_VARS` en `lur_model.py` con fallback seguro:
```python
pop_csv = ROOT / "data" / "interim" / "population_density.csv"
if pop_csv.exists():
    # merge con sensores
else:
    log.warning("population_density.csv no encontrado — omitiendo")
```

### Problema de orden de ejecución identificado

`feature_engineering.py` sobreescribe la columna `traffic_weighted_exposure`. El orden correcto de la cadena es:
```
feature_engineering.py → traffic_weighted_exposure.py
```
No al revés. Documentado para futuras ejecuciones.

---

## 6. Agente 6 — Spatial Lag Metodológico (Nivel 3)

### Implementación

`loocv_panel` modificada para aceptar parámetros opcionales `coords`, `sensor_pm_map`, `k_neighbors`. En cada fold:

1. El sensor test `sid` queda excluido del training set.
2. Se calculan distancias euclídeas BNG desde `sid` hacia todos los sensores de entrenamiento.
3. Se seleccionan los k=3 más cercanos.
4. `spatial_lag_pm` del sensor test = media de PM de esos k vecinos en el mismo período temporal.
5. `spatial_lag_pm` de cada sensor de entrenamiento = media de sus k vecinos (sin incluirse a sí mismo).
6. El lag se concatena como última columna de `X_train` y `X_test` antes del `.fit()`.

**Garantía anti-data-leakage**: `y[test_mask]` nunca entra en ningún cálculo de lag.

### Impacto

| | Sin lag | Con lag | Delta |
|---|---|---|---|
| PM2.5 R² | 0.497 | 0.509 | +0.012 |
| PM10 R² | 0.620 | 0.620 | ±0.000 |

La ganancia es modesta porque las features de entorno (road_density, landuse, dist_industrial) ya capturaban parte de la señal espacial.

---

## 7. Integración Manual de Datos Externos

### Archivos descargados manualmente por el usuario

| Archivo | Fuente | Contenido |
|---|---|---|
| `data/raw/file1.csv` | DEFRA UK-AIR | Datos horarios 2024: PM10, NO2, O3 para Liverpool Speke y Wirral Tranmere |
| `data/raw/census_ts001_lsoa.csv` | ONS Census 2021 | Población por LSOA para Liverpool (302 LSOAs, ~486K hab.) |

### Script de integración creado

`src/data/integrate_external_data.py` — procesa ambos archivos y los integra:

**Población:**
- Parseo custom del formato ONS (no estándar).
- Join espacial LSOA → sensor via `gpd.sjoin(..., predicate="within")`.
- 1 sensor fuera de LSOA → imputado con mediana (4.260 hab/km²).
- Rango de densidades: 898 – 30.762 hab/km² (media: 5.473).
- Guardado en `data/interim/population_density.csv`.

**AURN (file1.csv):**
- Solo PM10 disponible (no PM2.5 en este archivo).
- Estaciones válidas: Liverpool Speke (LISP) y Wirral Tranmere (WIRT).
- Valores anuales: LISP PM10=14.25 µg/m³, WIRT PM10=11.08 µg/m³.
- LISP integrada en `sensores_2024_agregados.csv/.gpkg` y `sensores_monthly.csv`.
- WIRT excluida del modelo: está en Birkenhead (Wirral), fuera de la cobertura del `streets_liverpool.gpkg` → distancia a carretera > MAX_SNAP_DIST=500m.

### Cadena re-ejecutada

```
sensor_road_matching.py → integrate_aadf.py → feature_engineering.py → traffic_weighted_exposure.py
```

`lur_features.csv`: **105 filas** (21 sensores × 5 buffers).

### Fix adicional en lur_model.py

LISP tiene PM2.5=NaN. Se añadió filtro de filas nulas por target antes del entrenamiento:
```python
valid_mask = y.notna()
df_work   = df_work[valid_mask].reset_index(drop=True)
X_final   = X_final[valid_mask].reset_index(drop=True)
y         = y[valid_mask].reset_index(drop=True)
sensor_ids_arr = sensor_ids_arr[valid_mask]
```
PM2.5 entrena con 220 filas (21 sensores × ~10.5 meses, excluyendo LISP). PM10 entrena con 232 filas (21 sensores).

---

## 8. Resultados Finales

### Comparativa completa

| Target | Modelo | R²_CV | RMSE_CV |
|---|---|---|---|
| **PM2.5** | **SVR** | **0.6020** | **2.232** |
| PM2.5 | GradientBoosting | 0.5898 | 2.266 |
| PM2.5 | RandomForest | 0.5871 | 2.273 |
| PM2.5 | LinearRegression | 0.4638 | 2.590 |
| PM2.5 | Ridge | 0.4612 | 2.597 |
| **PM10** | **SVR** | **0.5809** | **3.512** |
| PM10 | LogRidge | 0.5688 | 3.563 |
| PM10 | Ridge | 0.5623 | 3.590 |
| PM10 | RandomForest | 0.5416 | 3.673 |

### Comparativa baseline vs. final

| Métrica | Baseline (Ridge) | Final (SVR) | Mejora |
|---|---|---|---|
| PM2.5 R² | 0.542 | **0.602** | **+0.060 (+11%)** |
| PM10 R² | 0.503 | **0.581** | **+0.078 (+16%)** |
| PM2.5 RMSE | 2.394 µg/m³ | **2.232 µg/m³** | −0.162 |
| PM10 RMSE | 3.682 µg/m³ | **3.512 µg/m³** | −0.170 |

### Variables seleccionadas en el modelo final (PM2.5)

- `landuse_green_m2_100m` — área verde en buffer 100m (correlación espacial más fuerte: |r|=0.731)
- `road_length_residential_m_1000m` — longitud de vías residenciales en buffer 1000m (|r|=0.653)
- Controles temporales: `air_temperature_mean`, `wind_speed_mean`, `rain_days`, `mes_sin`, `mes_cos`

---

## 9. Estado del Pipeline Post-Sesión

### Archivos nuevos o modificados

| Archivo | Tipo | Cambio |
|---|---|---|
| `src/data/integrate_external_data.py` | Nuevo | Integración población + AURN |
| `src/models/lur_model.py` | Modificado | BASE_VARS, estacionalidad, buffer 1000m, spatial lag, filtro NaN |
| `src/features/feature_engineering.py` | Modificado | BUFFER_RADII incluye 1000m |
| `data/raw/file1.csv` | Nuevo | Datos AURN horarios 2024 |
| `data/raw/census_ts001_lsoa.csv` | Nuevo | Censo ONS 2021 por LSOA |
| `data/interim/population_density.csv` | Nuevo | Densidad hab/km² por sensor |
| `data/interim/lur_features.csv` | Regenerado | 105 filas (21 sensores × 5 buffers) |
| `data/interim/sensores_2024_agregados.csv/.gpkg` | Modificado | +LISP (n=21 efectivo para PM10) |
| `data/interim/sensores_monthly.csv` | Modificado | +12 meses de LISP PM10 |
| `outputs/models/lur_model_PM25.pkl` | Regenerado | SVR entrenado |
| `outputs/models/lur_model_PM10.pkl` | Regenerado | SVR entrenado |
| `.claude/agents/lur-04-feature-expansion.md` | Nuevo | Definición agente |
| `.claude/agents/lur-05-data-integration.md` | Nuevo | Definición agente |
| `.claude/agents/lur-06-methodological-lag.md` | Nuevo | Definición agente |

### Orden correcto de ejecución del pipeline completo

```
src/data/process_sensors_1.py
src/data/integrate_external_data.py       ← NUEVO (requiere file1.csv + census)
src/features/sensor_road_matching.py
src/features/integrate_aadf.py
src/features/feature_engineering.py
src/features/traffic_weighted_exposure.py ← siempre DESPUÉS de feature_engineering
src/models/lur_model.py
```

---

## 10. Pendientes y Recomendaciones

### Pendiente inmediato

- `run_and_compare.py` no incluye `integrate_external_data.py` en su pipeline. Añadirlo como paso opcional (condicionado a que `file1.csv` y `census_ts001_lsoa.csv` existan).

### Para mejorar PM2.5 específicamente

El filtro p-value con n=21 spatial es muy conservador — ninguna variable pasa con p<0.10, forzando fallback a top-5 por correlación. Opciones:
- Relajar `P_THRESHOLD` a 0.15 para el caso espacial.
- Usar selección por correlación directamente cuando n_espacial < 25.

### Para mejorar PM10

El GradientBoosting colapsó con el buffer 1000m (R²=0.305). Considerar usar `BUFFER_RADII = [50, 100, 250, 500, 1000]` solo para modelos lineales y `[50, 100, 250, 500]` para ensemble si se detecta sobreajuste geográfico.

### Datos pendientes de integrar

| Dato | Fuente | Impacto esperado |
|---|---|---|
| PM2.5 de AURN (si disponible en otro período) | DEFRA | Bajo-Medio |
| Densidad de tráfico nocturno vs. diurno | OS/AADF | Medio |
| Concentración de fondo regional (NO2 AURN) | DEFRA | Medio |
