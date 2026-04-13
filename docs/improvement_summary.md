# Resumen de Mejoras — LUR Liverpool

## Cambios aplicados
- VIF threshold: 5 → 10 (permite retener más variables con colinealidad moderada)
- Nuevas features: `elevation_m` (elevación del sensor), `traffic_weighted_exposure` (exposición ponderada por distancia al tráfico)
- Nuevos modelos candidatos: LogRidge, SVR (junto con Linear, Ridge, ElasticNet, RandomForest, GradientBoosting, LogLinear)
- Dataset de entrenamiento: cross-sectional n=20 → panel mensual n=220 (20 sensores × 11 meses) con controles meteorológicos

## Comparativa de resultados

> Nota: el baseline fue entrenado con Ridge sobre datos cross-seccionales (n=20 sensores).
> El nuevo modelo usa SVR sobre panel mensual (n=220 = 20 sensores × 11 meses).
> Las métricas RMSE no son directamente comparables por la diferencia de escala temporal.
> La comparación de R² LOOCV es válida en ambos casos.

| Target | Métrica | Antes (Ridge n=20) | Después (SVR n=220) | Δ |
|--------|---------|-------|---------|---|
| PM2.5 | R² LOOCV | 0.5858 | 0.5964 | +0.0106 |
| PM2.5 | RMSE (µg/m³) | 1.84 | 2.247 | +0.407 (escala panel) |
| PM10 | R² LOOCV | 0.4159 | 0.6723 | +0.2564 |
| PM10 | RMSE (µg/m³) | 3.93 | 3.169 | -0.761 (escala panel) |

## Modelo ganador por target
- PM2.5: SVR (R²=0.596, RMSE=2.247 µg/m³)
- PM10:  SVR (R²=0.672, RMSE=3.169 µg/m³)

## Diagnósticos (modelo lur_model.py, panel n=220)

### Heterocedasticidad (Breusch-Pagan)
- Heterocedasticidad PM2.5: FALLA (p=0.0000)
- Heterocedasticidad PM10: FALLA (p=0.0003)

### Autocorrelación espacial (Moran's I)
- Moran PM2.5: OK (I=-0.0903, p=0.5374 — sin autocorrelación espacial)
- Moran PM10: OK (I=-0.0327, p=0.7410 — sin autocorrelación espacial)

## Variables finales seleccionadas

### PM2.5 (5 variables LUR + 3 controles meteo)
- `road_length_residential_m_500m` — longitud viaria residencial en buffer 500m
- `landuse_industrial_ratio_250m` — proporción industrial en buffer 250m
- `landuse_green_ratio_100m` — proporción verde en buffer 100m
- `dist_industrial_m` — distancia a zona industrial más cercana
- `elevation_m` — elevación del sensor (nueva feature)

### PM10 (4 variables LUR + 3 controles meteo)
- `road_length_residential_m_500m` — longitud viaria residencial en buffer 500m
- `landuse_green_ratio_100m` — proporción verde en buffer 100m
- `dist_industrial_m` — distancia a zona industrial más cercana
- `elevation_m` — elevación del sensor (nueva feature)

## Observaciones
- `elevation_m` tiene la correlación univariada más alta con ambos targets (|r|=0.808 para PM2.5, |r|=0.763 para PM10), siendo la feature más importante añadida.
- `traffic_weighted_exposure` fue candidata (|r|=0.18-0.19) pero no pasó el filtro p-value <0.10.
- El mayor salto de rendimiento es para PM10: R² pasa de 0.4159 (REQUIERE MÁS DATOS) a 0.6723 (ROBUSTO), principalmente por la combinación de `elevation_m` + panel mensual con controles meteorológicos.
- La heterocedasticidad detectada en ambos targets implica que los intervalos de confianza de los modelos son anticonservadores; se recomienda usar errores estándar robustos (HC3) en análisis inferenciales.
- Spatial CV (Leave-Cluster-Out, 4 clusters): PM2.5 R²=0.483, PM10 R²=0.534 — el gap respecto a LOOCV (~0.11-0.14) indica cierta dependencia espacial no capturada, esperable con n=20 sensores.
