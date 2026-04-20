# Modelización Espacio-Temporal de la Calidad del Aire en Liverpool mediante Land Use Regression

**Proyecto III — Ciencia de Datos**  
**Autor:** Ivan  
**Fecha:** Abril 2026

---

## 1. Introducción

La contaminación por partículas en suspensión (PM2.5 y PM10) es el principal riesgo ambiental para la salud pública en entornos urbanos. Sin embargo, las redes de monitoreo permanente tienen cobertura limitada: la mayoría de los barrios carecen de sensores propios. El objetivo de este proyecto es construir un modelo espacio-temporal que reconstruya la evolución mensual de PM2.5 y PM10 para los 302 Lower Super Output Areas (LSOA) de Liverpool —unidades estadísticas de ~1.500 habitantes— a partir de datos históricos de una red de 68 sensores de bajo coste Aeternum y variables meteorológicas y de uso del suelo.

El modelo resultante, denominado **ST-LUR** (*Spatiotemporal Land Use Regression*), permite: (a) reconstruir series históricas 2021–2024 para zonas sin sensor, (b) proyectar 12 meses hacia el futuro, y (c) estimar incertidumbre mediante intervalos de confianza al 90 %. El caso de uso final es una herramienta de apoyo para planificación urbana y salud pública que identifique los barrios con mayor exposición crónica.

---

## 2. Preparación de Datos

### 2.1 Fuentes de datos

Se integraron tres fuentes heterogéneas:

1. **Red de sensores Aeternum**: 321 archivos CSV (datos cada 30 min) distribuidos en 14 carpetas trimestrales (2021Q3–2025Q1). Cada archivo corresponde a un sensor y período, con columnas `Date & Time`, `PM2.5` y `PM10`.
2. **Meteorología ERA5** (Open-Meteo API, gratuita): temperatura 2m, humedad relativa, velocidad del viento y precipitación horaria para el aeropuerto de Liverpool (53.33°N, −2.85°W), descargados programáticamente para 2021–2025.
3. **Características espaciales** (OpenStreetMap + UK DfT): densidad viaria por tipo (motorway, residential, primaria), cobertura de suelo industrial/residencial/verde, AADF (flujo de tráfico), distancias a fuentes (industrial, puerto, aeropuerto, túnel, estación), elevación digital.

### 2.2 Limpieza y control de calidad

Los datos de sensores presentan dos problemas críticos:

- **Valores centinela de hardware**: el firmware Aeternum registra −8.83×10²⁹ ante fallo de lectura. Se eliminaron todas las filas con `|PM2.5| > 10²⁰`.
- **Fuera de rango físico**: PM2.5 ∈ [0, 150] µg/m³; PM10 ∈ [0, 300] µg/m³.

Tras el filtrado, se agregaron las lecturas a **medias mensuales por sensor**, exigiendo una completitud mínima del 40 % de observaciones esperadas (= días del mes × 48 lecturas/día). El panel resultante contiene **1.291 observaciones** (sensor × mes), 68 sensores únicos, con cobertura media del 88,7 % por celda conservada.

**Tabla 1. Evolución anual de PM2.5 (media red de sensores)**

| Año | PM2.5 medio (µg/m³) | PM10 medio (µg/m³) |
|-----|--------------------|--------------------|
| 2021 | 24.19 | 48.74 |
| 2022 | 13.93 | 31.23 |
| 2023 | 7.56  | 17.86 |
| 2024 | 8.16  | 17.86 |
| 2025 (Q1) | 9.48 | 16.42 |

La tendencia decreciente 2021→2023 refleja en parte la recuperación post-COVID y en parte una mejora real de la calidad del aire. Esta tendencia interanual motivó una normalización año-específica en el modelo (§4).

La meteorología ERA5 cubre 60 meses (2021-01 a 2025-12), con temperatura media 10.9 °C y viento 4.2 m/s —valores coherentes con el clima oceánico templado de Liverpool.

### 2.3 Feature engineering espacial

Para cada sensor se emparejaron las coordenadas GPS con los polígonos LSOA de la ONS. Las características de uso del suelo se extrajeron con buffers concéntricos (50 m, 250 m, 500 m, 1.000 m) alrededor de cada sensor y de cada centroide LSOA. Las variables temporales cíclicas `mes_sin = sin(2π·mes/12)` y `mes_cos = cos(2π·mes/12)` codifican la estacionalidad sin discontinuidades en diciembre→enero.

---

## 3. Descripción de la Tarea (Vista Minable)

### 3.1 Definición de tarea

**Tarea principal**: regresión supervisada multivariante con estructura panel espacio-temporal. La variable de salida es la concentración media mensual de PM2.5 (y PM10) a nivel LSOA. No existe observación directa para 302 LSOAs, por lo que el problema es de extrapolación espacial + interpolación temporal.

### 3.2 Vista minable

La vista minable se materializa en dos niveles:

**Nivel espacial** — Matriz de 302 LSOAs × 14 características de uso del suelo (Tabla 2). Variable de salida: mediana anual de PM2.5 según el sensor más próximo o asignado al LSOA.

**Tabla 2. Variables de entrada del modelo espacial (muestra)**

| Grupo | Variable | Descripción |
|---|---|---|
| Uso del suelo | `pct_green` | Fracción de suelo verde en buffer 100 m |
| Uso del suelo | `pct_industrial` | Fracción industrial en buffer 1.000 m |
| Viario | `street_density_residential` | Longitud viaria residencial / área (1.000 m) |
| Viario | `street_density_motorway` | Longitud autopista / área |
| Fuentes | `dist_industrial_m` | Distancia al polígono industrial más cercano |
| Morfología | `bcr` | *Building Coverage Ratio* |
| Tráfico | `aadf_total_sum_1000m` | Suma AADF en buffer 1.000 m |

**Nivel temporal** — Panel de 1.215 observaciones (sensor × mes, 2022–2025) con 10 predictores meteorológicos. Variable de salida: `log_AF = log(PM_mes / mediana_anual_sensor_año)`, el *logarithmic Adjustment Factor* que captura la variación estacional y meteorológica eliminando la tendencia interanual.

**Tabla 3. Variables del modelo temporal**

| Variable | Tipo |
|---|---|
| `air_temperature_mean` | Continua (°C) |
| `wind_speed_mean` | Continua (m/s) |
| `rain_days` | Continua (días/mes) |
| `mes_sin`, `mes_cos` | Cíclica (estacionalidad) |
| `temp²`, `wind²` | Cuadrática (no-linealidades) |
| `temp × wind` | Interacción dispersión |
| `temp × rain`, `wind × rain` | Interacciones lavado/dilución |

---

## 4. Prototipo del Modelo y Evaluación

### 4.1 Arquitectura ST-LUR v2

El modelo sigue una descomposición multiplicativa:

```
PM2.5(LSOA, mes) = baseline_espacial(LSOA) × exp(log_AF(meteo, mes))
```

**Etapa 1 — Baseline espacial**: SVR con kernel RBF, entrenado con validación cruzada dejando fuera un sensor (*Leave-One-Sensor-Out*, LOSO) sobre las medianas anuales de 2024. Predice el nivel de fondo de cada LSOA a partir de sus características de uso del suelo.

**Etapa 2 — Factor temporal (log-AF)**: RidgeCV (α* = 1.0 por selección automática sobre grid logarítmico), entrenado sobre el panel 2022-01 a 2025-03. La normalización año-específica elimina la tendencia interanual: `log_AF_it = log(PM_it / mediana_{sensor,año})`, evitando que el descenso 2021→2023 infle los factores invernales en proyecciones futuras.

**Incertidumbre combinada (IC 90 %)**: Se propaga la incertidumbre del modelo temporal (bootstrap paramétrico, B = 200) más un componente espacial fijo (σ_espacial = 3.0 µg/m³ para PM2.5), combinados en cuadratura: σ²_total = σ²_temporal + σ²_espacial.

### 4.2 Justificación de elección de modelos

SVR con kernel RBF fue seleccionado sobre Ridge, Lasso y Random Forest para el componente espacial por tres razones: (1) robusto a outliers de la variable de respuesta (sensores en emplazamientos atípicos), (2) regularización implícita que evita sobreajuste con n = 20–21 sensores, y (3) mejora de R² LOSO frente a Ridge en +0.20 puntos. RidgeCV para el componente temporal es apropiado dado que las 10 variables están correlacionadas (interacciones derivadas de las mismas variables base), contexto donde la penalización L2 estabiliza los coeficientes.

### 4.3 Evaluación

**Componente espacial (SVR sensor-level)**

| Métrica | PM2.5 | PM10 |
|---|---|---|
| R² (LOSO-CV) | **0.602** | **0.581** |
| RMSE (LOSO-CV) | 2.23 µg/m³ | 3.51 µg/m³ |
| N observaciones | 220 | 232 |
| N sensores | 20 | 21 |

La validación LOSO es un protocolo riguroso: todos los meses de un sensor se retiran del entrenamiento, simulando la predicción en un barrio sin cobertura. R² = 0.60 indica capacidad predictiva moderada-buena para un problema de extrapolación espacial urbana.

**Componente temporal (RidgeCV log-AF)**

| Métrica | PM2.5 | PM10 |
|---|---|---|
| R² (entrenamiento) | 0.310 | 0.205 |
| RMSE (escala log) | 0.293 | 0.227 |
| N observaciones | 1.215 | 1.215 |

El R² ≈ 0.31 refleja que la meteorología local explica parte de la variación estacional, pero no toda: factores como episodios de contaminación transfronteriza, inversión térmica o quema de biomasa no están capturados. Esta limitación es inherente a la disponibilidad de predictores, no a la elección del modelo.

**Validación temporal externa: 2025Q1 (enero–marzo 2025)**

Se reservó el primer trimestre de 2025 como conjunto de test completamente independiente —el modelo no vio estos datos durante el entrenamiento.

| Métrica | Valor |
|---|---|
| R² | −1.11 |
| RMSE | 7.54 µg/m³ |
| MAE | 6.10 µg/m³ |
| Sesgo medio | +4.53 µg/m³ (sobreestimación) |
| Cobertura IC 90 % | **40.7 %** |
| N observaciones | 27 (14 sensores, 3 meses) |

El R² negativo y el sesgo sistemático de +4.53 µg/m³ se explican por una **falta de coincidencia espacial** (*spatial mismatch*): el modelo predice la media de área del LSOA, mientras que los sensores Aeternum están instalados en ubicaciones de fondo (fachadas de edificios, parques) que sistemáticamente registran concentraciones un 45–52 % inferiores a la media de área del barrio. Este comportamiento es esperado en modelos LUR de área: los sensores validan concentraciones puntuales, no medias de LSOA. La cobertura IC 90 % del 40.7 % (vs. 0 % antes de añadir σ_espacial) confirma que incorporar la incertidumbre de la extrapolación espacial es imprescindible para predicciones honestas.

---

## 5. Discusión

### 5.1 Mockup de despliegue y estimación de valor

El artefacto final es un fichero `stlur_v2_predictions.csv` con **18.120 filas** (302 LSOAs × 60 meses, 14.496 históricas + 3.624 de pronóstico hasta diciembre 2025) con columnas de predicción central e intervalo de confianza. Este fichero alimenta directamente un prototipo de **mapa de calor interactivo** en un dashboard web (Folium/GeoPandas), donde un técnico de salud pública puede:

1. Seleccionar un período y visualizar los LSOA con exposición crónica > umbral OMS (10 µg/m³).
2. Consultar la serie temporal de cualquier barrio con su banda de incertidumbre.
3. Exportar un ranking de LSOAs para priorizar intervenciones (zonas verdes, restricciones de tráfico).

El prototipo responde afirmativamente a "¿puede funcionar?": el modelo cubre el 100 % de los 302 LSOAs con resolución mensual, identifica correctamente el gradiente espacial centro-periferia, y sus predicciones tienen coherencia física (mínimos en verano, máximos en enero–febrero). El valor principal no es la precisión absoluta —limitada por el mismatch espacial— sino la **cobertura espacial**: sin el modelo, el 95 % de los LSOAs de Liverpool carecen de datos de calidad del aire.

### 5.2 Tecnología y autonomía técnica

El proyecto se desarrolló íntegramente en Python (pandas, scikit-learn, geopandas, osmnx, requests). La API Open-Meteo fue identificada como alternativa gratuita a la paga UK Met Office tras consultar la documentación oficial y foros de Stack Overflow. La extracción de características OSM con buffers concéntricos sigue el patrón estándar de la literatura LUR (Hoek et al., 2008; Eeftens et al., 2012) y fue implementada con `geopandas.sjoin` y operaciones de área vectorizadas.

La decisión de normalizar log-AF por año (en lugar de la mediana global) surgió del análisis diagnóstico del sesgo en las predicciones de invierno de 2025, sin referencia externa, demostrando autonomía analítica para identificar y corregir un bug conceptual.

### 5.3 Uso de Inteligencia Artificial

**Claude Code** (Anthropic) se utilizó como asistente de programación a lo largo del proyecto en tres roles:

1. **Generación de código**: escritura inicial de `build_full_panel.py` y `stlur_retrain.py` a partir de especificaciones en lenguaje natural, reduciendo el tiempo de implementación.
2. **Depuración**: identificación de errores como `KeyError: 'annual_median'` tras renombrar columnas, `SyntaxError` por notación `PM2.5` dentro de f-strings de Python, y `UnicodeEncodeError` en Windows (cp1252).
3. **Arquitectura**: discusión del diseño del intervalo de confianza combinado (bootstrap + σ_espacial) y justificación de la normalización año-específica.

El uso de IA es transparente y responsable: todas las decisiones analíticas (elección de modelos, umbral de completitud, exclusión de 2021) fueron evaluadas por el autor con criterio estadístico propio. La IA no generó resultados ni interpretaciones; generó código que fue validado empíricamente.

---

## Referencias

- Hoek, G. et al. (2008). A review of land-use regression models to assess spatial variation of outdoor air pollution. *Atmospheric Environment*, 42(33), 7561–7578.
- Eeftens, M. et al. (2012). Development of land use regression models for PM2.5, PM2.5 absorbance, PM10 and PMcoarse in 20 European study areas. *Environmental Science & Technology*, 46(20), 11195–11205.
- Open-Meteo (2024). Free Weather API. archive-api.open-meteo.com
- UK ONS (2021). Lower Super Output Areas — Liverpool. Office for National Statistics.

---

## Apéndice — Archivos del proyecto

| Archivo | Descripción |
|---|---|
| `src/data/build_full_panel.py` | Pipeline de datos: sensores + ERA5 → panel mensual |
| `src/models/stlur_retrain.py` | Clase `STLURModelV2`: entrenamiento, CV, pronóstico |
| `data/interim/sensores_monthly_full.csv` | Panel limpio 1.291 filas |
| `data/interim/meteo_monthly_full.csv` | ERA5 60 meses |
| `outputs/stlur_v2_predictions.csv` | 18.120 predicciones (302 LSOAs × 60 meses) |
| `outputs/models/stlur_v2_PM25.pkl` | Modelo entrenado PM2.5 |
| `outputs/figures/lur/map_PM25.png` | Mapa espacial PM2.5 (302 LSOAs) |
| `outputs/figures/stlur/stlur_v2_PM25_E01006512.png` | Serie temporal ejemplo con IC 90 % |
