# Estructura del Proyecto — PROYIII Liverpool Air Quality

> Referencia para cualquier IA o desarrollador que trabaje en este proyecto.
> Describe qué hay en cada carpeta, qué scripts generan qué archivos, y dónde añadir cosas nuevas.

---

## Árbol general

```
PROYIII/
├── data/
│   ├── raw/           ← datos originales sin modificar (nunca se sobrescriben a mano)
│   ├── interim/       ← datos procesados intermedios (generados por scripts)
│   └── processed/     ← datasets finales listos para modelar
│
├── src/
│   ├── data/          ← scripts de descarga y limpieza de datos externos
│   ├── features/      ← scripts de ingeniería de features espaciales
│   ├── models/        ← scripts de entrenamiento, validación y diagnóstico
│   └── visualization/ ← scripts de mapas y visualizaciones
│
├── outputs/
│   ├── figures/
│   │   ├── eda/       ← gráficos exploratorios (boxplots, heatmaps, series temporales)
│   │   └── lur/       ← gráficos del modelo LUR (diagnósticos, residuos, importancia)
│   ├── logs/
│   │   └── lur/       ← logs de ejecución del pipeline LUR
│   ├── maps/          ← GeoJSONs para visualización en navegador/GIS
│   ├── models/        ← modelos entrenados serializados (.pkl)
│   └── LUR/           ← resultados numéricos del modelo LUR (CSV)
│
├── docs/              ← reportes markdown generados automáticamente + documentación
├── notebooks/         ← Jupyter notebooks de exploración
├── run_and_compare.py ← orquestador principal del pipeline LUR
├── CLAUDE.md          ← instrucciones para IA (estilo de código, convenciones)
└── README.md
```

---

## `data/` — Datos

### `data/raw/` — Datos brutos
Archivos descargados directamente de fuentes externas. **No modificar manualmente.**

| Archivo | Origen | Script que lo genera |
|---------|--------|----------------------|
| `aadf_liverpool.csv` | DfT (Department for Transport) | `src/data/download_aurn.py` |
| `buildings_liverpool.gpkg` | OpenStreetMap | `src/data/extract_osm_features.py` |
| `landuse_liverpool.gpkg` | OpenStreetMap | `src/data/extract_osm_features.py` |
| `streets_liverpool.gpkg` | OpenStreetMap | `src/data/extract_osm_features.py` |
| `lsoa_liverpool.gpkg` | ONS / UK Census | `src/data/download_population.py` |
| `CoordsSensores.csv` | Proyecto manual | — |
| `sensores/` | Purple Air / IoT raw | — |
| `midas_liverpool/` | MIDAS Met Office | `src/data/download_meteo.py` |

### `data/interim/` — Datos intermedios procesados
Generados por scripts del pipeline. Se pueden regenerar ejecutando los scripts en orden.

| Archivo | Qué contiene | Script que lo genera |
|---------|-------------|----------------------|
| `sensores_snapped.gpkg` | Sensores ajustados a la red viaria (CRS: EPSG:27700) | `src/features/sensor_road_matching.py` |
| `streets_with_traffic.gpkg` | Red viaria con AADF imputado (8450 tramos) | `src/features/integrate_aadf.py` |
| `lur_features.csv` | Matrix de features LUR (20 sensores × 4 buffers = 80 filas) | `src/features/feature_engineering.py` + `src/features/traffic_weighted_exposure.py` |
| `sensores_monthly.csv` | Lecturas mensuales de PM2.5 y PM10 por sensor (panel) | `src/data/process_sensors_1.py` |
| `meteo_monthly.csv` | Temperatura, viento y días de lluvia mensuales | `src/data/download_meteo.py` |
| `sensor_elevation.csv` | Elevación en metros por sensor | `src/data/download_elevation.py` |
| `aadf_snapped.gpkg` | AADF asignado a tramos viarios | `src/features/integrate_aadf.py` |
| `sensores_2024_agregados.csv/.gpkg` | Agregados anuales 2024 por sensor | `src/data/process_sensors_1.py` |

### `data/processed/` — Datos finales
Resultados listos para análisis o entrega.

| Archivo | Qué contiene |
|---------|-------------|
| `loocv_results.csv` | Predicciones LOOCV por sensor |
| `model_comparison.csv` | Comparativa de modelos (R², RMSE) |
| `sensors_cleaned.csv` | Sensores limpios con coordenadas validadas |
| `lur_barrios_predictions.csv/.geojson` | Predicciones a nivel LSOA (notebook 3.2) |

---

## `src/` — Código fuente

### `src/data/` — Descarga y limpieza
| Script | Qué hace | Output |
|--------|----------|--------|
| `process_sensors_1.py` | Limpia lecturas de sensores IoT, agrega por mes/año | `data/interim/sensores_monthly.csv`, `sensores_2024_agregados.*` |
| `extract_osm_features.py` | Descarga OSM: calles, edificios, usos del suelo | `data/raw/*.gpkg` |
| `download_aurn.py` | Descarga datos de calidad del aire AURN (DEFRA) | `data/raw/aadf_liverpool.csv` |
| `download_meteo.py` | Descarga datos meteorológicos MIDAS | `data/interim/meteo_monthly.csv` |
| `download_elevation.py` | Obtiene elevación para cada sensor | `data/interim/sensor_elevation.csv` |
| `download_population.py` | Descarga datos de población por LSOA | `data/raw/lsoa_liverpool.gpkg` |

### `src/features/` — Ingeniería de features
| Script | Qué hace | Output |
|--------|----------|--------|
| `sensor_road_matching.py` | Snap de sensores a la red viaria más cercana | `data/interim/sensores_snapped.gpkg` |
| `integrate_aadf.py` | Asigna tráfico AADF a cada tramo viario | `data/interim/streets_with_traffic.gpkg` |
| `feature_engineering.py` | Calcula features de uso del suelo, tráfico, edificios en 4 radios de buffer (50/100/250/500 m). Añade `elevation_m` | `data/interim/lur_features.csv` |
| `traffic_weighted_exposure.py` | Calcula exposición al tráfico ponderada por distancia: `TWE = Σ(AADF / dist²)`. Añade columna `traffic_weighted_exposure` | Actualiza `data/interim/lur_features.csv` |

### `src/models/` — Modelos
| Script | Qué hace | Output |
|--------|----------|--------|
| `feature_selection_report.py` | Selección de variables por correlación máxima + VIF<10 | `docs/02b_feature_selection_report.md` |
| `lur_model.py` | **Pipeline principal**: selección de escala, entrenamiento (Ridge, ElasticNet, LogRidge, SVR, RF, GB), LOOCV, diagnósticos | `outputs/models/lur_model_PM*.pkl`, `outputs/LUR/model_comparison.csv`, `outputs/figures/lur/diagnostics_*.png` |
| `task5_loocv_validation.py` | Validación LOOCV independiente con tests estadísticos (Breusch-Pagan, Shapiro-Wilk, Moran's I) | `outputs/LUR/loocv_results.csv`, `docs/04_validation_report.md`, `outputs/figures/lur/loocv_obs_vs_pred.png` |
| `task7_diagnostics_deliverables.py` | Diagnósticos visuales completos: obs vs pred, residuos, importancia de variables, mapas de residuos | `outputs/figures/lur/*.png`, `docs/03_model_summary.md` |

### `src/visualization/` — Visualización
| Script | Qué hace | Output |
|--------|----------|--------|
| `predict_map.py` | Predice PM2.5/PM10 en los 8450 tramos viarios de Liverpool | `outputs/maps/liverpool_pollution_map.geojson` |
| `plotearmapa.py` | Renderiza mapas de polución como PNG | `outputs/figures/lur/map_PM*.png` |

---

## `outputs/` — Resultados

### `outputs/models/` — Modelos entrenados
| Archivo | Qué contiene |
|---------|-------------|
| `lur_model_PM25.pkl` | Modelo ganador para PM2.5 (serializado con pickle) |
| `lur_model_PM10.pkl` | Modelo ganador para PM10 (serializado con pickle) |

> Para añadir un nuevo modelo: guárdalo aquí con el patrón `lur_model_{CONTAMINANTE}.pkl`.

### `outputs/LUR/` — Resultados numéricos LUR
| Archivo | Qué contiene |
|---------|-------------|
| `loocv_results.csv` | Predicciones LOOCV por sensor y target |
| `model_comparison.csv` | R² y RMSE de todos los modelos candidatos |

> Para añadir resultados de un nuevo experimento: crea un subdirectorio `outputs/LUR/{nombre_experimento}/`.

### `outputs/figures/` — Imágenes
```
outputs/figures/
├── eda/     ← gráficos EDA (generados por notebooks o scripts exploratorios)
└── lur/     ← gráficos del modelo LUR (generados por src/models/)
```

> Para añadir figuras de un nuevo modelo (ej. kriging): crear `outputs/figures/kriging/`.

### `outputs/maps/` — Mapas geoespaciales
| Archivo | Qué contiene |
|---------|-------------|
| `liverpool_pollution_map.geojson` | 8450 tramos viarios con PM2.5 y PM10 predichos (WGS84) |

> Para añadir un nuevo mapa: guardar aquí en formato GeoJSON o GPKG.

### `outputs/logs/` — Logs de ejecución
```
outputs/logs/
└── lur/     ← logs del pipeline LUR (extract_osm_features.log, etc.)
```

---

## `docs/` — Documentación y reportes

Reportes markdown generados automáticamente por los scripts de modelado, más documentación manual del proyecto.

| Archivo | Generado por | Qué contiene |
|---------|-------------|-------------|
| `00_project_structure.md` | Este archivo | Guía de estructura del proyecto |
| `01_resumen_ejecutivo.md` | Manual | Resumen ejecutivo para presentación |
| `02_pipeline_analysis.md` | Manual | Análisis técnico del pipeline completo |
| `02b_feature_selection_report.md` | `feature_selection_report.py` | Correlaciones y filtros VIF por variable |
| `03_model_summary.md` | `task7_diagnostics_deliverables.py` | Resumen del modelo ganador (features, R²) |
| `04_validation_report.md` | `task5_loocv_validation.py` | Métricas LOOCV + tests estadísticos |
| `05_comparison_report.md` | `run_and_compare.py` | Comparativa antes/después de mejoras |
| `06_improvement_summary.md` | Manual / pipeline agent | Resumen de mejoras aplicadas |
| `07_development_log.md` | Manual | Bitácora técnica detallada del desarrollo |

> Para añadir documentación de un nuevo módulo: crear `docs/{nombre_modulo}.md`.

---

## Variables path en el código

Todos los scripts usan este patrón para resolver rutas:

```python
ROOT     = Path(__file__).resolve().parents[N]  # raíz del proyecto
DATA_INT = ROOT / "data" / "interim"
DATA_RAW = ROOT / "data" / "raw"

# Outputs
OUT_DIR    = ROOT / "outputs" / "LUR"           # CSVs de resultados
MODELS_DIR = ROOT / "outputs" / "models"        # modelos .pkl
FIG_DIR    = ROOT / "outputs" / "figures" / "lur"  # imágenes LUR
DOCS_DIR   = ROOT / "docs"                      # reportes markdown
```

`N` depende de la profundidad del script:
- Scripts en `src/models/` o `src/features/`: `parents[2]`
- Scripts en la raíz (`run_and_compare.py`): `Path(__file__).resolve().parent`

---

## Orden de ejecución del pipeline

```
1. src/data/process_sensors_1.py          → sensores mensuales
2. src/data/extract_osm_features.py       → capas OSM
3. src/features/sensor_road_matching.py   → snap sensores a red viaria
4. src/features/integrate_aadf.py         → tráfico AADF en tramos
5. src/features/feature_engineering.py   → matrix de features (con elevation_m)
6. src/features/traffic_weighted_exposure.py → TWE feature
7. src/models/lur_model.py                → entrenamiento + diagnósticos
8. src/models/task5_loocv_validation.py  → validación LOOCV
9. src/visualization/predict_map.py       → mapa predictivo GeoJSON
```

O ejecutar todo desde la raíz con:
```bash
python run_and_compare.py
```
