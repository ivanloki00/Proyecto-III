# Comparison Report — Mejoras LUR
**Fecha:** 2026-04-13 22:19

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
| R² LOOCV | 0.43940693483348003 | 0.41957636102082707 | -0.0198 |
| R² Spatial CV | N/A | 0.376047208818733 | nuevo |
| RMSE µg/m³ | 2.6672816628624076 | 2.6949984233716893 | +0.0277 |
| BP p-value¹ | 1.867012571694701e-06 | 1.773163148537888e-06 | — |
| Moran's I p | 0.8616594485737417 | 0.8882808607776103 | — |

**Variables ANTES:** `road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

**Variables DESPUÉS:** `road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

### PM10

| Métrica | ANTES | DESPUÉS | Δ |
|---------|-------|---------|---|
| Modelo | ElasticNet | ElasticNet | — |
| Nº variables | 6 | 6 | +0 |
| R² LOOCV | 0.4140354989969719 | 0.43507919473065326 | +0.0210 |
| R² Spatial CV | N/A | 0.416549084041803 | nuevo |
| RMSE µg/m³ | 4.246829806609737 | 4.160606941622733 | -0.0862 |
| BP p-value¹ | 3.687644335388659e-05 | 1.2062767019821884e-05 | — |
| Moran's I p | 0.7885708559080236 | 0.8388674636199076 | — |

**Variables ANTES:** `road_length_residential_m_500m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

**Variables DESPUÉS:** `road_length_residential_m_500m`, `landuse_green_ratio_100m`, `dist_industrial_m`, `air_temperature_mean`, `wind_speed_mean`, `rain_days`

---

¹ BP = Breusch-Pagan. ANTES: calculado sobre residuos full-sample (sesgado). 
DESPUÉS: calculado sobre residuos LOOCV (correcto, más conservador).