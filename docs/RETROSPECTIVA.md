# Análisis Retrospectivo: Proyecto III — Liverpool Air Quality (ST-LUR)

**Fecha:** Mayo 2026  
**Autor:** Ivan  

---

## Resumen ejecutivo

El proyecto fue un éxito técnico medido: se entregó un modelo ST-LUR funcional (SVR R²=0.602 PM2.5, R²=0.581 PM10), un pipeline geodata completo y una webapp de visualización. Lo que sigue es una lectura honesta de los fallos cometidos, lo que se aprendió de cada uno, y qué cambiaría en un proyecto futuro similar.

---

## 1. Errores encontrados y soluciones tomadas

### 1.1 "El Desfase Transatlántico" — Columnas lat/lon invertidas

| | Detalle |
|---|---|
| **Error** | Las columnas `lat` y `lon` del CSV de sensores estaban intercambiadas. Al proyectar a EPSG:27700, los sensores desaparecieron del mapa de Liverpool. |
| **Síntoma** | 0 intersecciones en todos los spatial joins posteriores. |
| **Diagnóstico** | Revisión de los rangos estadísticos de las columnas: `lat` contenía valores ~−3.0 (longitud británica) y `lon` contenía ~53.3 (latitud del norte de Inglaterra). |
| **Solución** | `gpd.points_from_xy(resumen['lat'], resumen['lon'])` — override explícito del orden. |
| **Tiempo perdido estimado** | Alto. Todo el pipeline downstream fallaba silenciosamente. |

> **Aprendizaje**: Antes de cualquier pipeline espacial, verificar los rangos de coordenadas con 3 líneas: `print(df[['lat','lon']].describe())`. Un valor de latitud en el hemisferio norte debe estar entre 50–60 para UK. Si no, para todo.

---

### 1.2 "La Ilusión de Slough" — Código de autoridad local incorrecto (DfT AADF)

| | Detalle |
|---|---|
| **Error** | El ID de municipio por defecto (`112`) en la documentación oficial de DfT correspondía a Slough, no a Liverpool. |
| **Síntoma** | Spatial join devolvió 0 tramos de carretera con tráfico. El script no lanzó ningún error. |
| **Diagnóstico** | Inspección directa del CSV descargado: los nombres de calles no eran de Liverpool. |
| **Solución** | Búsqueda en la tabla de referencia DfT → código correcto `161`. Resultado: 7,661 tramos (90.7% de cobertura). |
| **Tiempo perdido estimado** | Medio-alto. El join silencioso fue el principal riesgo. |

> **Aprendizaje**: Los joins espaciales con 0 resultados son casi siempre un error de datos, no de código. Añadir siempre `assert len(result) > 0, "Join vacío — revisar IDs de referencia"` como guardia.

---

### 1.3 "Variables Olvidadas en Cadenas Cíclicas" — KeyError en predicción masiva

| | Detalle |
|---|---|
| **Error** | El script `predict_map.py` generaba el array de features para 8,450 tramos pero omitía `landuse_industrial_ratio_250m`, que solo necesitaba el modelo PM10. |
| **Síntoma** | `KeyError` al 12% del proceso. |
| **Solución** | Parar ejecución, reescribir el bloque generativo, reiniciar. |
| **Causa raíz** | El modelo PM2.5 se desarrolló primero y el loop de features fue copiado para PM10 sin revisar las features diferenciales. |

> **Aprendizaje**: Al entrenar modelos separados para targets distintos (PM2.5 vs PM10), guardar la lista de features de cada modelo en el `.pkl` o en un JSON de metadatos. Así el script de predicción carga `model.feature_names_in_` en vez de hardcodear columnas.

---

### 1.4 APIs externas deprecadas (DEFRA + ONS)

| | Detalle |
|---|---|
| **Error** | Los endpoints automatizados para datos ONS (HTTP 400) y DEFRA AURN (HTTP 404) fallaron. |
| **Impacto** | Los datos de densidad de población y la estación de referencia AURN no pudieron integrarse automáticamente. |
| **Solución** | Descarga manual + script `integrate_external_data.py` con parser custom del formato ONS no estándar. |

> **Aprendizaje**: Las APIs gubernamentales tienen alta tasa de deprecación. Para datos externos críticos, diseñar siempre el pipeline con un `if file_exists: load else: skip_with_warning`. No bloquear el pipeline entero por datos opcionales.

---

### 1.5 Sobreajuste geográfico con buffer 1000m + GradientBoosting

| | Detalle |
|---|---|
| **Error** | Al añadir buffer 1000m en la iteración de mejora, GradientBoosting pasó de R²=0.586 a R²=0.497 (PM2.5) y a R²=0.305 (PM10). |
| **Causa** | El buffer 1000m introduce colinealidad severa y amplía el espacio de features relativo a n=20 sensores, provocando sobreajuste geográfico medible en Spatial CV (R²=−14). |
| **Solución** | SVR con kernel RBF ganó la selección por ser regularizado implícitamente y robusto a outliers espaciales. |

> **Aprendizaje**: Con n pequeño (< 25 observaciones espaciales), más features no es mejor. La regla de oro: `n_features < n/3` como máximo en modelos no regularizados. SVR y Ridge deben ser el default para datasets espaciales pequeños, no ensemble methods.

---

### 1.6 Mismatch espacial en validación temporal (2025Q1)

| | Detalle |
|---|---|
| **Error** | La validación temporal externa dio R²=−1.11, RMSE=7.54, cobertura IC 90% del 40.7%. |
| **Causa** | El modelo predice la *media de área LSOA*, pero los sensores Aeternum están en ubicaciones de fondo (fachadas, parques) que registran concentraciones un 45–52% inferiores. No es un fallo del modelo; es un mismatch de concepto. |
| **Solución** | Documentar el mismatch como limitación inherente y añadir σ_espacial=3.0 µg/m³ en cuadratura para ampliar los IC. |

> **Aprendizaje**: Definir desde el inicio qué es lo que el modelo predice (media de área vs. punto de medición). Si los sensores de validación no representan lo mismo que el target del modelo, la métrica de validación es engañosa por diseño.

---

### 1.7 Errores de implementación menores (Python)

| Error | Causa | Solución |
|---|---|---|
| `KeyError: 'annual_median'` | Columna renombrada en un refactor intermedio | Estandarizar nombres de columnas en un dict de constantes al inicio del script |
| `SyntaxError` en f-strings con `PM2.5` | El punto en `PM2.5` rompía la sintaxis | Usar `PM25` como nombre de variable interno siempre |
| `UnicodeEncodeError` (Windows, cp1252) | Carácteres no-ASCII en outputs | `open(file, encoding='utf-8')` explícito en todos los `write` |
| `ModuleNotFoundError` en `lur_model.py` | `scikit-learn`, `statsmodels` no instalados en el entorno base | Añadir `requirements.txt` al inicio del proyecto |

---

## 2. Errores de proceso (no técnicos)

### 2.1 Issues de GitHub no reflejaban el trabajo real

El repo tenía 5 issues abiertas al 50% del Milestone 2 cuando el trabajo técnico sustancial (#19, #24, #26) quedó sin ejecutar. El informe final se escribió con esos issues pendientes.

**Causa**: Los issues se crearon antes de conocer bien la viabilidad de los datos externos. #19 (demografía por edad) y #24 (HIA) requerían datos NHS que no eran accesibles en la práctica.

> **Aprendizaje**: En la fase de planificación, distinguir entre issues *aspiracionales* e issues *viables* con los datos disponibles. Un issue sin fuente de datos confirmada debería ser un "spike" primero, no un issue de desarrollo completo.

---

### 2.2 El pipeline no era reproducible de un solo comando al final

El orden correcto de ejecución final fue:
```
process_sensors_1.py → integrate_external_data.py → sensor_road_matching.py
→ integrate_aadf.py → feature_engineering.py → traffic_weighted_exposure.py
→ lur_model.py
```

Pero `run_and_compare.py` (el script orquestador) no incluía `integrate_external_data.py`. Alguien nuevo no podría reproducir el resultado final sin leer la documentación de la sesión de mejora.

> **Aprendizaje**: Mantener un único punto de entrada ejecutable (`make all` o `run_pipeline.py`) que sea la verdad del pipeline. Actualizarlo en el mismo commit que se añade un paso nuevo.

---

### 2.3 Documentación en cascada, no incremental

Se generaron 10 documentos `docs/0X_*.md` a lo largo del proyecto, varios superponiéndose en contenido. Al final, un lector nuevo no sabía cuál era el documento "vivo" y cuál era historia.

> **Aprendizaje**: Un solo `REPORT.md` actualizado incrementalmente + un `CHANGELOG.md` de decisiones técnicas. No crear un nuevo `.md` por cada sesión de trabajo.

---

## 3. Lo que funcionó bien (para repetir)

| Práctica | Por qué funcionó |
|---|---|
| Leave-One-Sensor-Out como protocolo de CV | Más honesto que K-fold para datos espaciales con n pequeño. Simuló exactamente el caso de uso real. |
| Filtro VIF iterativo antes de entrenar | Evitó colinealidad sin hiperparámetros. Simple y efectivo con n=20. |
| Separar modelo espacial (SVR) de modelo temporal (RidgeCV) | La descomposición multiplicativa `baseline × exp(log_AF)` fue arquitecturalmente correcta y facilitó depurar cada componente por separado. |
| Normalización log-AF por año específico | Detectado y corregido un bug conceptual (la tendencia 2021→2023 inflaba los factores invernales). Demostró autonomía analítica real. |
| Fallback jerárquico en imputación AADF | El 90.7% de cobertura directa + imputación por medianas de jerarquía vial fue robusto y no introdujo ruido. |

---

## 4. Qué cambiaríamos en el próximo proyecto

### Prioridad alta

1. **Validar fuentes de datos externas antes de planificar features** — Confirmar que APIs gubernamentales devuelven datos antes de crear issues que dependen de ellas.

2. **Schema de columnas como constantes globales** — Un diccionario `COLS = {"lat": "latitude_wgs84", ...}` en un archivo `config.py` compartido. Los KeyErrors por renombrado desaparecerían.

3. **Script orquestador actualizado como parte del pipeline, no como afterthought** — Cada vez que se añade un paso, el pipeline completo debe ejecutarse de principio a fin y documentarse el tiempo que tarda.

4. **Verificación de coordenadas como primer assert de cualquier pipeline espacial** — 3 líneas que comprueban que lat ∈ [49, 61] y lon ∈ [−8, 2] para UK. Si no, stop.

### Prioridad media

5. **Guardar `feature_names_in_` junto a cada modelo pkl** — Evita el error de "variables olvidadas" en scripts de predicción.

6. **Un solo documento vivo de decisiones, no uno por sesión** — Facilita onboarding y no genera confusión sobre qué versión es la actual.

7. **Separar issues viables de aspiracionales desde el inicio** — Usar labels `data-confirmed` vs `data-pending` para gestionar expectativas del Milestone.

### Prioridad baja

8. **Añadir `requirements.txt` en el commit inicial** — Evita el `ModuleNotFoundError` al ejecutar en un entorno limpio.

9. **Codificar nombres de target como `PM25`/`PM10` internamente** — Nunca `PM2.5` dentro de strings de Python.

---

## 5. Métrica de progreso real

| Fase | Estado | R² final |
|---|---|---|
| Ingesta y limpieza de sensores | Completo | — |
| EDA temporal | Completo | — |
| OSM + AADF extraction | Completo | — |
| Street-level LUR (SVR) | Completo | 0.602 / 0.581 |
| LSOA-level aggregation | Completo | 0.203 / 0.195 |
| ST-LUR temporal component | Completo | 0.310 / 0.205 |
| Webapp AirTrace | Completo | — |
| HIA / demografía NHS | No realizado | — |
| Validación externa DEFRA | No realizado | — |

Los 2 issues no completados (#19 HIA y #26 DEFRA) eran dependientes de datos que resultaron inaccesibles, no de capacidad técnica. La decisión correcta habría sido detectarlo en la fase de planificación y no incluirlos en el scope comprometido.

---

> El proyecto demostró que es posible construir un pipeline geodata completo en Python puro con datos públicos, y que los errores más costosos no fueron de código sino de supuestos sobre datos externos. Esa es la lección más transferible.
