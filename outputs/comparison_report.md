# Comparison Report — Mejoras LUR
**Fecha:** 2026-04-13 18:55

## Scripts ejecutados

- ✓ `D1: DEFRA AURN`
- ✓ `C1: Meteorología`
- ✓ `C2: Elevación`
- ✓ `C4: Población`
- ✓ `B1: Sensores (panel mensual)`
- ✓ `Fase 2.5: Sensor snapping`
- ✓ `Fase 3: Tráfico AADF`
- ✓ `Fase 4: Feature engineering (+fuentes puntuales)`
- ✓ `Fase 5-7: Modelo LUR (+ElasticNet, SpatialCV, Bootstrap)`
- ✓ `Validación LOOCV (residuos corregidos)`
- ✗ `Fase 8: Mapa predictivo (+intervalos)`

## Métricas ANTES vs DESPUÉS

### PM2.5

| Métrica | ANTES | DESPUÉS | Δ |
|---------|-------|---------|---|
| Modelo | ElasticNet | ElasticNet | — |
| Nº variables | 7 | 7 | +0 |
| R² LOOCV | 0.43940693483348003 | 0.43940693483348003 | +0.0000 |
| R² Spatial CV | N/A | 0.3753008584916637 | nuevo |
| RMSE µg/m³ | 2.6672816628624076 | 2.6672816628624076 | +0.0000 |
| BP p-value¹ | 1.867012571694701e-06 | 1.867012571694701e-06 | — |
| Moran's I p | 0.8616594485737417 | 0.8616594485737417 | — |

**Variables ANTES:** `road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

**Variables DESPUÉS:** `road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

### PM10

| Métrica | ANTES | DESPUÉS | Δ |
|---------|-------|---------|---|
| Modelo | ElasticNet | ElasticNet | — |
| Nº variables | 6 | 6 | +0 |
| R² LOOCV | 0.4140354989969719 | 0.4140354989969719 | +0.0000 |
| R² Spatial CV | N/A | 0.4003176016221618 | nuevo |
| RMSE µg/m³ | 4.246829806609737 | 4.246829806609737 | +0.0000 |
| BP p-value¹ | 3.687644335388659e-05 | 3.687644335388659e-05 | — |
| Moran's I p | 0.7885708559080236 | 0.7885708559080236 | — |

**Variables ANTES:** `road_length_residential_m_500m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

**Variables DESPUÉS:** `road_length_residential_m_500m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

---

¹ BP = Breusch-Pagan. ANTES: calculado sobre residuos full-sample (sesgado). 
DESPUÉS: calculado sobre residuos LOOCV (correcto, más conservador).