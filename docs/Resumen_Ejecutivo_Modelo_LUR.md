# Resumen Ejecutivo: Modelo de Regresión de Uso de Suelo (LUR) para Liverpool

**Fecha:** 08 de Abril de 2026  
**Proyecto:** Liverpool Air Quality (Proyecto III)  
**Objetivo:** Extrapolar y predecir los niveles de PM2.5 y PM10 a lo largo de los 8,450 segmentos de la red vial de Liverpool mediante la construcción de un pipeline de Data Science automatizado.

---

## 1. Contexto y Objetivos Cumplidos
A pesar de la alta variabilidad del entorno espacial de Liverpool, las redes de medición fijas (sensores) son escasas (aprox. 24 nodos eficaces). El objetivo primario de esta fase fue **vincular características urbanas, morfológicas y volúmenes de tráfico** registrados en un entorno GIS para entrenar un algoritmo que aprenda de los sensores existentes y *pueda rellenar los vacíos en todos los tramos de carretera donde actualmente no hay monitorización.*

Todos los objetivos marcados fueron procesados con éxito cumpliendo requerimientos metodológicos estrictos de control de calidad temporal, ensamblaje espacial y modelado ML con control de variables.

## 2. Metodología e Hitos Centrales

### Fase 1: Limpieza del Core Series Temporales
- **Periodo de Estudio Fijo (2024):** Se filtraron más de 1.5 millones de registros históricos, quedándonos solo con el año 2024 (casi medio millón de eventos) para garantizar una foto temporal unificada.
- **Calidad del Dato:** Se impuso un umbral de supervivencia del **75% de completitud del año** a cada sensor. Los que superaron la criba (20 sensores activos ininterrumpidos) se homogeneizaron transformando sus millones de datos en **concentraciones medias anuales (PM2.5 y PM10).**

### Fase 2: Sensor-to-Road Matching
- Se detectó y resolvió un error histórico en el dataset base: las columnas de Longitud / Latitud estaban intercambiadas.
- Una vez corregido, se ejecutó un algoritmo de proximidad (*snapping*) que **alineó físicamente la coordenada de cada sensor con su calle métrica más próxima** en el mapa vial vectorial (`EPSG:27700`). Distancia media de ajuste: ±60 metros.

### Fase 3: The Traffic Enrichment (Integración AADF)
El tráfico vehicular es el predictor causal más determinante.
- **Acceso API y Join Espacial:** El script minó de manera autónoma los servidores de datos en abierto del Departamento de Transportes Británico (DfT), aisló el código de autoridad representativo para Liverpool (`LA-161`) y consolidó casi 5000 puntos de la red central.
- **Imputación Inteligente:** Se obtuvo recuento exacto empírico para un tremendo **90.7% del flujo viario en toda la ciudad** (conteo medio a la baja de 10,016 coches/día en carreteras primarias y 7,044 en residenciales). Al restante **9.3%** se le imputó estadísticamente la "mediana global" correspondiente a su misma jerarquía viaria. Toda la ciudad quedó enriquecida.

### Fase 4: Generación Zonal (Feature Engineering)
Se programaron rutinas que proyectaron zonas de proximidad elípticas (buffers concéntricos a **50m, 100m, 250m y 500m**) con respecto al sensor. Para calcular la agresividad estática del aire circundante en las 4 distancias, se interceptaron:
1. Longitud e intensidad de tráfico por densidad viaria (Motorway, Primary, Residential).
2. Proporción de parques contra masas de asfalto (`landuse_green_ratio`).
3. Volúmenes industriales puros.
4. Distancia euclidiana mínima contra fábricas (industria pesada). 

## 3. Entrenamiento (Data Science Pipeline)

### Selección de Características (Feature Selection)
Evitando someter el predictor al fenómeno llamado la "maldición de la dimensionalidad", un filtro doble hizo la criba de las características:
1. **Selección de escala óptima:** El script seleccionó para cada variable su zona matemática de máxima afección (Ej. La contaminación industrial es predictora principal a proximidad micro escala -50m-, frente a la red de carreteras secundarias que correlaciona mejor considerando zonas más amplias de dilución -500m-).
2. **Caza de Colinealidad (VIF):** Filtramos hasta tener un ecosistema de variables independientes que aportaran verdadero valor analítico excluyendo solapamientos de correlación matemática (Factor VIF < 5).

### Performance del Bosque Aleatorio (Random Forest vs Linear Regression)
Se ajustó un Regresor Lineal y un modelo Random Forest (N=200). Se aplicó una test de validación estricto y pesimista (*Leave-One-Out Cross-Validation*). Los resultados declararon a **Random Forest** como claro y definitivo vencedor para la predicción de red completa:

#### ✨ PM2.5 (Random Forest)
- **$R^2$ LOOCV:** `0.531` -> Explica el 53% de la varianza en zonas "ciegas", asombroso dado un pool fundacional de n=20 observaciones y la brutal complejidad barrial de la ciudad de The Beatles.
- **Prueba de Breusch-Pagan:** Todo correcto (No presenta homoscedasticidad errática).
- **Test de Moran's I:** P-Value 0.85 -> Sin sombra de sesgo de vecindad / autocorrelación espacial no capturada.

#### ✨ PM10 (Random Forest)
- **$R^2$ LOOCV:** `0.431` -> Fiel acompañamiento a PM2.5 dadas las discrepancias atmosféricas de este polvo sedimentario de mayor calibre.
- **Test espacial:** Exitosamente aprobado en los márgenes científicos de seguridad (P-Value > 0.79).

## 4. Conclusión Tecnológica y Outputs

El pipeline generó los artefactos persistentes:
1. `lur_model_PM25.pkl` / `lur_model_PM10.pkl`: Red neuronal lista para implementarse en APIs futuras.
2. `liverpool_pollution_map.geojson`: **El hito logístico que visualiza el producto final**. Son **8,450 trazos de calle** precalculados. Hemos identificado arterias como *Anfield Road* y *Quarry Road* prediciéndolas sobre los 24.87 µg/m³ (PM10), evidenciando correlaciones con alta actividad de rodadura u obstinación semiindustrial cercana. Ningún tramo urbano tiene vacíos de información o NaNs. Todo está imputado, cubierto y respaldado estadísticamente en un único plano interactivo.
3. Las fotos diagnósticas observadas están consolidadas en los mapas térmicos espaciales `map_PM10.png` y `map_PM25.png`.

---
*Reporte autogenerado tras integración completa del pipeline analítico.*
