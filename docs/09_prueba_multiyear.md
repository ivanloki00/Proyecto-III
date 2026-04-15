# PruebaN — Experimento Multi-año (Abril 2026)

## Objetivo

Evaluar si ampliar el dataset de entrenamiento del modelo LUR de 2024 únicamente (20 sensores) a la cobertura completa 2021-2025 (28 sensores) mejora el poder predictivo.

---

## Configuración del Experimento

| Parámetro | Pipeline actual | PruebaN |
|---|---|---|
| Años de datos | 2024 | 2021–2025 |
| Sensores totales | 20 | 28 |
| Sensores snapped (<500m carretera) | 21 (con LISP AURN) | 24 |
| Filas panel mensual | ~220 | 1.031 |
| Completitud mínima requerida | ≥75% mensual | ≥50% mensual |
| Meses válidos mínimos | ≥6 meses en 2024 | ≥6 meses en cualquier año |

**Cobertura temporal de los 28 sensores en `sensors_definitivo.csv`:**

| sensor_id | Inicio | Fin | Años |
|---|---|---|---|
| f008d1ccc0c4 | Mar 2021 | Abr 2025 | 4.03 |
| f008d1cb9af0 | Oct 2021 | Abr 2025 | 3.44 |
| f008d1cbdea4 | Oct 2021 | Abr 2025 | 3.44 |
| f008d1cbce64 | Oct 2021 | Abr 2025 | 3.44 |
| f008d1cc02a4 | Oct 2021 | Abr 2025 | 3.44 |
| ... (23 más) | | | 2.2–3.4 |

---

## Estructura Creada (eliminada)

```
PruebaN/
├── src/
│   ├── 01_process_multiyear.py       — agrega sensors_definitivo.csv a mensual/anual, todos los años
│   ├── 02_sensor_road_matching.py    — snap 28 sensores a carreteras
│   ├── 03_integrate_aadf.py          — integración AADF para nuevos sensores
│   ├── 04_feature_engineering.py     — features multi-escala (buffers [50,100,250,500,1000]m)
│   ├── 05_traffic_weighted_exposure.py — TWE para 24 sensores
│   └── 06_lur_model.py               — modelo LUR idéntico al principal
├── run_pipeline.py                   — orquestador secuencial con verificación de outputs
├── data/
│   ├── interim/                      — aggregados, snapped, lur_features_multiyear.csv
│   └── processed/LUR/               — model_comparison.csv, loocv_results.csv
└── outputs/
    ├── models/                       — lur_model_PM25.pkl, lur_model_PM10.pkl
    └── figures/lur/                  — diagnostics_PM25.png, diagnostics_PM10.png
```

**Convención de rutas en los scripts:**
```python
PRUEBA_ROOT = Path(__file__).resolve().parents[1]   # PruebaN/
MAIN_ROOT   = Path(__file__).resolve().parents[2]   # PROYIII/
DATA_RAW    = MAIN_ROOT / "data" / "raw"            # datos crudos compartidos (solo lectura)
DATA_INT    = PRUEBA_ROOT / "data" / "interim"
```

---

## Resultados

### Pipeline ejecutado con éxito

- `01_process_multiyear.py`: 1.037.393 registros horarios procesados → 1.031 filas panel mensual (28 sensores, media 36.8 meses válidos/sensor)
- `02_sensor_road_matching.py`: 24/28 sensores snapped (4 excluidos por estar a >500m de cualquier tramo — principalmente sensores periféricos)
- `04_feature_engineering.py`: `lur_features_multiyear.csv` → 120 filas (24 sensores × 5 buffers)
- `06_lur_model.py`: ejecutado sin errores

### Métricas obtenidas

| Target | Mejor modelo | R²_CV | RMSE_CV |
|---|---|---|---|
| PM2.5 | LogLinear | 0.315 | — |
| PM10 | SVR | 0.203 | — |

### Comparativa vs. pipeline actual

| Métrica | Pipeline actual | PruebaN | Delta |
|---|---|---|---|
| Sensores espaciales | 21 | 24 | +3 |
| Filas panel | ~220 | 1.031 | +4.7× |
| **PM2.5 R²** | **0.602** | 0.315 | −0.287 |
| **PM10 R²** | **0.581** | 0.203 | −0.378 |

---

## Diagnóstico: Por Qué Baja el R²

El resultado **no es un bug** — es el comportamiento esperado de un LUR cuando se usa variación temporal inter-anual.

### Causa raíz

El modelo LUR usa **features espaciales estáticas** (AADF de 2023, land-use OSM, edificios) que no cambian con el tiempo. Al ampliar de 1 año a 5 años aparece variación inter-anual del PM que las features espaciales no pueden explicar:

- Los niveles de PM en 2021-2022 fueron diferentes a los de 2024 por razones no espaciales: recuperación post-COVID, condiciones meteorológicas multianuales, cambios en emisiones
- El modelo intenta explicar "¿por qué este sensor tiene más PM que aquel?" pero ahora también enfrenta "¿por qué 2022 tuvo más PM que 2024?" — y para eso no tiene variables

### Variables seleccionadas en PruebaN (PM2.5)

`aadf_total_mean_50m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `elevation_m` + controles meteo

Son covariables razonables, pero la señal espacial se diluye con la variación temporal añadida.

---

## Soluciones Propuestas (no implementadas)

### Opción A — Efectos fijos por año (más sencilla)

Añadir dummies de año (`year_2022`, `year_2023`, `year_2024`) como variables forzadas en el panel, igual que `mes_sin`/`mes_cos`. Absorben la variación de nivel inter-anual sin tocar las features espaciales.

```python
# En build_panel_dataset():
df_panel["year_num"] = pd.to_datetime(df_panel["year_month"]).dt.year
for yr in [2022, 2023, 2024, 2025]:
    df_panel[f"year_{yr}"] = (df_panel["year_num"] == yr).astype(int)
```

### Opción B — Normalización por año (más robusta para LUR puro)

Calcular el Z-score de PM dentro de cada año antes de entrenar. El modelo aprende el patrón espacial relativo dentro de cada año, no los niveles absolutos. Más apropiado para LUR metodológicamente correcto.

```python
# Por año: PM_norm = (PM - mean_año) / std_año
df_panel["PM_norm"] = df_panel.groupby("year")["PM2.5"].transform(
    lambda x: (x - x.mean()) / x.std()
)
```

### Opción C — Leave-One-Year-Out CV

En vez de Leave-One-Sensor-Out, usar Leave-One-Year-Out: entrenar en 4 años, predecir el 5º. Evalúa la generalización temporal además de la espacial.

---

## Decisión

Experimento descartado. La carpeta `PruebaN/` fue eliminada. Se conserva este registro para referencia futura.

**Razón del descarte**: El enfoque multi-año sin controlar la variación inter-anual produce modelos con R² muy inferior al pipeline actual. Para aprovechar los 28 sensores con datos históricos, se requiere implementar previamente efectos fijos por año (Opción A) o normalización anual (Opción B).

---

## Archivos del Pipeline Original NO modificados

El experimento PruebaN fue completamente aislado en su propia carpeta. Los siguientes archivos del pipeline principal **no fueron modificados**:

- `src/models/lur_model.py`
- `src/features/feature_engineering.py`
- `data/interim/lur_features.csv`
- `data/interim/sensores_2024_agregados.csv`
- `outputs/models/lur_model_PM25.pkl`
- `outputs/models/lur_model_PM10.pkl`
