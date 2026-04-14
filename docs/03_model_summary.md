# Resumen Ejecutivo — Modelo LUR Liverpool Air Quality
**Proyecto:** PROYIII — Predicción de Contaminación Atmosférica en Liverpool
**Fecha:** 2026-04-10
**Protocolo de validación:** Leave-One-Out Cross-Validation (LOOCV), n = 20 sensores
**Modelo ganador:** Ridge Regression (RidgeCV, α seleccionado por CV)

---

## 1. Variables Finales por Modelo

### PM2.5 — 4 predictores (escenario p < 0.10, VIF ≤ 5)

| Variable | Buffer | |r| | p-valor | VIF |
|---|---|---|---|---|
| `road_length_residential_m` | 500 m | 0.557 | 0.011 | 1.93 |
| `landuse_industrial_ratio`  | 250 m | 0.392 | 0.087 | 1.07 |
| `landuse_green_ratio`       | 100 m | 0.731 | 0.0002 | 1.53 |
| `dist_industrial_m`         |  50 m | 0.550 | 0.012 | 2.24 |

### PM10 — 3 predictores (escenario p < 0.10, VIF ≤ 5)

| Variable | Buffer | |r| | p-valor | VIF |
|---|---|---|---|---|
| `road_length_residential_m` | 500 m | 0.514 | 0.020 | 1.81 |
| `landuse_green_ratio`       | 100 m | 0.722 | 0.0003 | 1.53 |
| `dist_industrial_m`         |  50 m | 0.553 | 0.011 | 2.19 |

---

## 2. Métricas LOOCV

| Métrica | PM2.5 | PM10 |
|---|---|---|
| R² (LOOCV) | **0.5858** | **0.4159** |
| RMSE (µg/m³) | 1.839 | 3.933 |
| MAE (µg/m³) | 1.510 | 3.215 |
| MAPE (%) | 21.05 | 20.49 |
| Outliers (|res| > 2×RMSE) | 0 | 0 |

> Nota: el modelo PM10 almacenado tiene R²=0.5034 (full-sample CV durante selección de modelo),
> mientras que el LOOCV estricto sobre las 4 variables finales reporta R²=0.4159.
> Se usa el LOOCV estricto como métrica de validación definitiva.

---

## 3. Tests Estadísticos de Supuestos (residuos full-sample)

| Test | PM2.5 | PM10 | Resultado |
|---|---|---|---|
| Breusch-Pagan (homocedasticidad) | p = 0.185 | p = 0.535 | OK — no se rechaza homocedasticidad |
| Shapiro-Wilk (normalidad residuos) | p = 0.840 | p = 0.919 | OK — residuos normales |
| Moran's I (autocorr. espacial) | p = 0.667 | p = 0.310 | OK — sin estructura espacial residual |
| Durbin-Watson (autocorr. serial) | 2.647 | 2.194 | Aceptable (rango 1.5–2.5; PM2.5 marginal) |

---

## 4. Comparación de Modelos (selección Task 4)

| Target | Modelo | R² (CV) | RMSE (µg/m³) |
|---|---|---|---|
| PM2.5 | **Ridge** ← ganador | **0.5858** | **1.839** |
| PM2.5 | LinearRegression | 0.5079 | 2.005 |
| PM2.5 | RandomForest | 0.2769 | 2.430 |
| PM2.5 | GradientBoosting | 0.2662 | 2.448 |
| PM10 | **Ridge** ← ganador | **0.5034** | **3.626** |
| PM10 | LinearRegression | 0.4486 | 3.821 |
| PM10 | RandomForest | 0.3809 | 4.049 |
| PM10 | GradientBoosting | 0.2616 | 4.422 |

---

## 5. Clasificación de Robustez

| Contaminante | R² LOOCV | Clasificación |
|---|---|---|
| PM2.5 | 0.5858 | **Aceptable con limitaciones** (0.4 ≤ R² < 0.6) |
| PM10  | 0.4159 | **Aceptable con limitaciones** (0.4 ≤ R² < 0.6) |

Ambos modelos son apropiados para describir patrones espaciales relativos
(zonas de alta/baja contaminación), pero **no** para predicciones absolutas
en ubicaciones sin validar.

---

## 6. Limitaciones del Modelo

- **n = 20 sensores:** tamaño muestral pequeño. LOOCV con n pequeño tiene
  tendencia a ser optimista en varianza; los intervalos de confianza de R²
  son amplios.
- **Cobertura AADF = 19.8%:** solo el 19.8% de los tramos viarios dispone de
  datos de tráfico AADF, lo que reduce la capacidad explicativa del tráfico
  como predictor. La variable AADF fue eliminada por p > 0.10 en ambos modelos.
- **Ausencia de variables meteorológicas:** viento, temperatura y humedad
  modulan la concentración de PM pero no están disponibles a nivel de sensor.
- **Extrapolación temporal:** el modelo se entrenó sobre medias anuales 2024.
  No es directamente aplicable a predicciones horarias o estacionales.
- **Fuentes episódicas no capturadas:** quemas, tráfico pesado puntual,
  polvo de construcción no están representados por las 4 variables seleccionadas.
- **Durbin-Watson PM2.5 = 2.647:** ligeramente fuera del rango 1.5–2.5,
  sugiere posible correlación serial negativa (no espacial, dado Moran's I OK).
  Se considera marginal dado el orden arbitrario de los sensores.

---

## 7. Artefactos Producidos

### Modelos serializados
| Archivo | Contenido |
|---|---|
| `outputs/lur_model_PM25.pkl` | Modelo Ridge PM2.5 (RidgeCV, α=0.01) |
| `outputs/lur_model_PM10.pkl` | Modelo Ridge PM10 (RidgeCV, α=0.01) |

### Predicciones y mapas
| Archivo | Contenido |
|---|---|
| `outputs/loocv_results.csv` | Predicciones LOOCV por sensor (ambos targets) |
| `outputs/liverpool_pollution_map.geojson` | 8 450 tramos viarios con PM2.5 y PM10 predichos |
| `outputs/map_PM25.png` | Mapa de polución PM2.5 (colormap Inferno) |
| `outputs/map_PM10.png` | Mapa de polución PM10 (colormap Inferno) |

### Gráficos de diagnóstico (`outputs/figures/`)
| Archivo | Descripción |
|---|---|
| `obs_vs_pred_PM25.png` | Dispersión obs vs pred PM2.5 (LOOCV) |
| `obs_vs_pred_PM10.png` | Dispersión obs vs pred PM10 (LOOCV) |
| `residuos_vs_pred_PM25.png` | Residuos vs predicho PM2.5 |
| `residuos_vs_pred_PM10.png` | Residuos vs predicho PM10 |
| `hist_residuos_PM25.png` | Histograma de residuos PM2.5 |
| `hist_residuos_PM10.png` | Histograma de residuos PM10 |
| `qq_residuos_PM25.png` | Q-Q plot residuos PM2.5 |
| `qq_residuos_PM10.png` | Q-Q plot residuos PM10 |
| `importancia_variables_PM25.png` | Importancia normalizada PM2.5 |
| `importancia_variables_PM10.png` | Importancia normalizada PM10 |
| `mapa_residuos_PM25.png` | Mapa espacial de residuos PM2.5 |
| `mapa_residuos_PM10.png` | Mapa espacial de residuos PM10 |

### Reportes
| Archivo | Contenido |
|---|---|
| `outputs/feature_selection_report.md` | Selección de variables (correlaciones, VIF) |
| `outputs/validation_report.md` | Reporte LOOCV + tests estadísticos |
| `outputs/model_comparison.csv` | Comparación de 4 modelos × 2 targets |
| `outputs/model_summary.md` | Este resumen ejecutivo |

---
_Generado automáticamente por `src/analysis/task7_diagnostics_deliverables.py`_
