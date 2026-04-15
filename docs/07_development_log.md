# Historial Detallado del Desarrollo: Modelo LUR (Liverpool)

Este documento es una bitácora técnica de muy bajo nivel destinada al equipo de desarrollo y Data Science. Su propósito es documentar **cada paso, script, función generada, error sufrido y solución implementada** durante la construcción del modelo de Regresión de Uso de Suelo (LUR) para estimar PM2.5 y PM10 en Liverpool (Año de referencia: 2024).

---

## 1. Fase de Planificación Inicial
El proyecto comenzó con la revisión del repositorio y la re-creación del `implementation_plan.md`. Se integraron nuevas directivas arquitectónicas forzadas:
* Usar promedios para 2024 con un umbral estricto del 75% de completitud temporal (descartar sensores inconsistentes).
* Homogeneizar ventanas analíticas (*buffers*) a escalas de 50m, 100m, 250m y 500m.
* Entrenar modelos separados y aplicar pruebas robustas residuales (Moran's I para autocorrelación espacial, Breusch-Pagan para Heterocedasticidad).

---

## 2. Fase de Extracción, Filtrado y Agregación (`process_sensors_1.py`)
**Objetivo:** Extraer del crudo gigantesco (`sensors_definitivo.csv`) solo la métrica validada anual para el 2024.

* **Lógica:** Se aplicó la función que calculaba si un sensor poseía más de 13,176 mediciones (75% del límite bisiesto de mediciones cada 30 min). 24 de 28 sensores sobrevivieron esta criba. Las mediciones se colapsaron en la media anual usando Pandas.
* 🚨 **Error Crítico: "El Desfase Transatlántico" (Coordenadas Invertidas)**
  * **Problema:** Al proyectar el `GeoDataFrame` inicial de los sensores al sistema métrico EPSG:27700 (British National Grid), los sensores desaparecieron de la geografía del mapeo y los posteriores análisis interceptaban 0 elementos.
  * **Diagnóstico:** Se ejecutó un escrutinio de los descriptores estadísticos que desveló que nuestro CSV contenía la Latitud salvada bajo la columna `lon` (53º Norte) y la Longitud británica almacenada bajo la columna `lat` (-3.00º). 
  * **Solución:** Se parchó explícitamente la lectura geométrica: `gpd.points_from_xy(resumen['lat'], resumen['lon'])` devolviendo las entidades físicas a Liverpool.

---

## 3. Fase de Alineación Espacial (`sensor_road_matching.py`)
**Objetivo:** Eliminar el ruido "GNSS" empujando las coordenadas de cada sensor estrictamente sobre la línea central del segmento vial correspondiente ('Snapping').

* **Funciones Generadas:**
    * `load_data()`: Lectura segura de GPKGs manejando CRS asimétricos.
    * `snap_sensors_to_roads(sensors, streets)`: Proyecta (vía `sjoin_nearest`) y calcula el desajuste por geometría.
* **Resultado:** 20 sensores urbanos emparejaron perfectamente (distancia media real: 60 m). Los otros 4 ubicados a más de 500m se desecharon del modelo intra-urbano por no representar flujo rodado válido.

---

## 4. Fase de Integración de Tráfico (`integrate_aadf.py`)
**Objetivo:** Imputar a la red viaria métricas reales del Censo Nacional de Tráfico DfT (Departament for Transport).

* **Funciones Generadas:**
    * `download_aadf()`: Scraper transaccional.
    * `prepare_aadf(df)`
    * `join_aadf_to_streets(streets, aadf)`
    * `impute_aadf_by_hierarchy(streets_joined)`
* 🚨 **Error Crítico: "La Ilusión de Slough" (Equívoco de Local Authority ID)**
  * **Problema:** El spatial join daba como resultado "0 tramos de carretera abastecidos". El motor había insertado el ID por defecto `112` extraído de la documentación oficial.
  * **Diagnóstico:** Se interrumpió el proceso vía scripts para investigar el CSV. Resultó que los datos correspondían a la comarca de **Slough** y no a Liverpool.
  * **Solución:** Una búsqueda forzada en internet por parte de la IA recuperó el código correcto y actual (`161`) para el municipio geográfico de Liverpool.
* **Resultado Estelar:** Se sobrepasaron las expectativas y el dataset oficial abarcó **7,661 tramos directos (90.7% del mapa).** El resto inferior fue imputado mediante medianas probabilísticas usando un *Fallback algorítmico jerárquico*.

---

## 5. Fase de Generación de Variables LUR (`feature_engineering.py`)
**Objetivo:** Programar el cálculo iterativo del contexto geográfico dinámico para pre-alimentar el entrenamiento (Buffers).

* **Funciones Generadas:**
    * `normalize_highway()` / `assign_highway_cat()`: Limpiadores de la taxonomía OpenStreetMap.
    * `clip_and_area()` / `clip_and_length()`: Funcionalidades nucleares tolerantes a fallos (`try/except`) para cruces de geometrías.
    * `compute_features_for_sensor(row, streets, buildings, landuse, radius)`: Calculadora vectorizada masiva de las más de 20 variables de intensidad urbanística para un determinado radio.
    * `compute_all_features()`: Orquestador iterativo de radios (50 a 500m) vs sensores (N=20).
* **Resultado:** Matriz densa de **80 filas (4 repeticiones x 20 sensores) x 24 columnas.** Todo fluido sin errores espaciales tras los parches previos.

---

## 6. Modelado y Diagnósticos Estadísticos (`lur_model.py`)
**Objetivo:** Realizar la quimioterapia matemática al Feature Engineering (Feature Selection) y entrenar el modelo ideal simultáneo PM2.5/PM10 con validación.

* 🚨 **Error de Dependencias Nulas:** El primer lanzamiento escupió un `ModuleNotFoundError`. Las cajas de modelado matemático carecían de dependencias ML. Se tuvo que usar pip para inyectar `scikit-learn`, `statsmodels` y `scipy`.
* **Funciones Generadas:**
    * `select_best_buffer(df, target)`: Comprime los resultados escogiendo para la misma variable base (ej. *industria*) únicamente aquella envolvente 2D donde la correlación de Pearson respecto a la concentración PM sea asintóticamente superior.
    * `filter_by_pvalue(X,y)`: Eliminación de insignificancia (<0.10).
    * `filter_by_vif(X)`: Podador iterativo de Multicolinealidad (expulsa variables redundantes superando VIF > 5.0).
    * `loocv(...)`: Probador validador cruzado con método pesimista de N pliegues unitarios (Leave-One-Out).
    * `morans_i()`: Matemática pesada de estadística espacial que prueba la existencia de autocorrelación/contagio de error latente.
    * `plot_diagnostics(...)`: Ensamblador gráfico de regresiones empíricas mediante subplots modulares (`GridSpec`).
* **Resultado:** Random Forest venció la contienda con $R^2$-CV prometedores (hasta 0.53 en micropartículas finas) pasando excepcionalmente bien los tests de estrés espacial.

---

## 7. Fase de Extrapolación Espacial Masiva (`predict_map.py`)
**Objetivo:** Exprimir las matemáticas LUR para invadir y colorear la red urbana en su totalidad (8,450 segmentos).

* **Funciones Generadas (Adaptación escalable):** Re-implementación directa in-file de los cortadores espaciales para atacar polígonos sobre line-strings directamente para no usar librerías complejas.
* 🚨 **Error Estructural: "Variables Olvidadas en Cadenas Cíclicas"**
  * **Problema:** El Random Forest PM10 exigía 4 columnas para pensar (ej. `landuse_industrial_ratio_250m`). El loop programado generativo del script precalentaba tan sólo las 3 basales que compartía genéticamente el PM2.5. El modelo falló por ausencia (KeyError subyacente).
  * **Solución:** Interrumpí de urgencia asíncrona la ejecución el script al 12% del proceso, re-reescribí vía sustitución multi-bloque los inyectores que forjaban el array de memoria `ind_ratio_250_m` y se reinició.
* **Resultado:** Geometrías calculadas. Ningún NaN en el producto final (Cero fallos lógicos predictivos). Mínimo PM2.5 ≈ 5.2, Máximo en nodos tipo Anfield Rd ≈ 13.4.

---

## 8. Fase de Ensamblaje Visual (`plotearmapa.py`)
**Objetivo:** Empaquetar la validación y crear entregables impactantes para stakeholders. 
* Se programó un lienzo Matplotlib en modo asíncrono-headless para tragar el archivo pesado `.geojson` y exprimir paletas cartográficas (Inferno CMAP) silenciando ejes y optimizando la renderización vectorial en dos archivos de alto contraste (PNG's disponibles en `outputs`).

---
Este ha sido el histórico de acciones. Cada código se encajó iterativamente superando las imperfecciones de los paquetes origen y las suposiciones geométricas. El pipeline actualmente es repetible, aséptico al nivel de calle (Road-Matched) e inferencialmente resiliente.
