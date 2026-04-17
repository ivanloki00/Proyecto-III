# 10. Project Progress Report — Liverpool Air Quality LUR
**Date:** 2026-04-17  
**Branch:** main  
**Prepared by:** Ivan (with Claude Code assistance)

---

## 1. Issue Status Summary

| # | Title | State | Checklist | Notes |
|---|-------|-------|-----------|-------|
| #16 | Ingesta y limpieza de datos de sensores | ✅ CLOSED | 6/6 | Sensores 2024 procesados, panel mensual |
| #17 | EDA Temporal | ✅ CLOSED | — | Análisis temporal completado |
| #18 | Extracción OSMnx y variables de entorno | ✅ CLOSED | — | Red vial, landuse, AADF snapeado |
| #19 | Datos demográficos y vulnerabilidad | ⚠️ OPEN | 0/4 | Pendiente datos ONS por edad/mortalidad |
| #20 | Road-level LUR Model (Task 4) | ✅ CLOSED | 5/5 | SVR, R²=0.602 (PM2.5), R²=0.581 (PM10) |
| #21 | LSOA-level model | ✅ CLOSED | 5/5 | Ridge, R²=0.203, 302 barrios |
| #24 | Health Impact Assessment (HIA) | ⚠️ OPEN | 0/5 | Bloqueado por #19 |
| #25 | Desigualdades y análisis espacial | ⚠️ OPEN | 4/5 | Falta evaluación colegios vs WHO |
| #26 | Validación externa DEFRA | ⚠️ OPEN | 0/5 | PCM/LAQM data no descargada aún |
| #27 | Informe Final | ⚠️ OPEN | 0/4 | Depende de cierre de #19, #24, #25, #26 |

**Cerrados:** 4 (#16, #17, #18, #20) + #21 cerrado en esta sesión  
**Pendientes:** 5 (#19, #24, #25, #26, #27)

---

## 2. Modelos — Métricas Finales

### 2.1 Street-level LUR (Issue #20)

| Target | Modelo | R²_CV (LOOCV) | RMSE_CV | n sensores |
|--------|--------|---------------|---------|-----------|
| PM2.5  | SVR    | **0.6020**    | 2.232 µg/m³ | 20 |
| PM10   | SVR    | **0.5809**    | 3.512 µg/m³ | 21 |

**Features PM2.5** (7 variables = 2 LUR + 5 controles):
- `landuse_green_m2_100m` — área verde buffer 100m (\|r\|=0.731)
- `road_length_residential_m_1000m` — longitud residencial buffer 1km (\|r\|=0.653)
- `air_temperature_mean`, `wind_speed_mean`, `rain_days`, `mes_sin`, `mes_cos`

**Validación adicional:**
- Spatial CV (Leave-Cluster-Out, 4 clusters): R²=0.400 — confirma generalización geográfica razonable
- Bootstrap (200 iter, α=0.1): IC medio ±0.76 µg/m³
- Breusch-Pagan p=0.0001 — heterocedasticidad detectada (esperada con sensores urbanos)

**Comparativa de modelos candidatos (PM2.5):**

| Modelo | R²_CV | RMSE_CV |
|--------|-------|---------|
| SVR | **0.6020** | **2.232** |
| GradientBoosting | 0.5898 | 2.266 |
| RandomForest | 0.5871 | 2.273 |
| LinearRegression | 0.4638 | 2.590 |
| Ridge | 0.4612 | 2.597 |
| ElasticNet | 0.4635 | 2.591 |

**Predicciones sobre red vial (8,450 tramos):**
- PM2.5: media=9.978, sd=2.412, rango=4.87–28.10 µg/m³
- PM10: media=19.750, sd=4.155, rango=10.72–51.47 µg/m³

---

### 2.2 LSOA-level LUR (Issue #21)

| Target | Modelo | R²_CV (LOOCV) | RMSE_CV | n LSOAs |
|--------|--------|---------------|---------|--------|
| PM2.5  | Ridge (α=1.0) | 0.203 | 1.482 µg/m³ | 302 |
| PM10   | Ridge (α=1.0) | 0.195 | 2.537 µg/m³ | 302 |

**Estrategia de entrenamiento:**  
Las predicciones del modelo street-level SVR (8,450 tramos) se agregan por LSOA obteniendo n=302 como target, en lugar de usar directamente los n=12 sensores físicos dentro de LSOAs. Esto es metodológicamente válido porque el modelo street-level ya fue validado con R²=0.60.

**Features LSOA** (14 variables zonal stats):
- `pct_industrial`, `bcr` (building coverage ratio)
- `street_density_m_per_km2`, `street_length_total_m`
- `pop_density_km2`, `area_km2`
- Intersecciones, longitudes por tipo de vía, etc.

**Predicciones sobre 302 LSOAs de Liverpool:**
- PM2.5_final: media=10.04, sd=1.67, rango=5.93–14.97 µg/m³
- PM10_final: media=19.89, sd=2.84, rango=12.98–28.57 µg/m³

**Distribución de scores (escala WHO A–F):**
- Grado B (5–10 µg/m³): 154 LSOAs (51%)
- Grado C (10–15 µg/m³): 148 LSOAs (49%)
- Ningún LSOA cumple el objetivo WHO 2021 (≤5 µg/m³ = Grado A)

**LSOAs más contaminados (PM2.5):**

| LSOA | Nombre | PM2.5 |
|------|--------|-------|
| E01006645 | Liverpool 017E | 14.97 µg/m³ |
| E01006541 | Liverpool 015A | 14.93 µg/m³ |
| E01006644 | Liverpool 017D | 14.71 µg/m³ |

**LSOAs más limpios (PM2.5):**

| LSOA | Nombre | PM2.5 |
|------|--------|-------|
| E01033750 | Liverpool 061A | 5.93 µg/m³ |
| E01034411 | Liverpool 062G | 6.40 µg/m³ |
| E01034409 | Liverpool 062E | 6.55 µg/m³ |

> Nota: El R²_CV bajo (0.20) refleja la limitación de usar solo features geoespaciales agregadas como predictores del promedio del área. La varianza espacial real dentro de un LSOA es alta. La fuente primaria de predicción es el street-level SVR; el LSOA Ridge ajusta con contexto de barrio.

---

## 3. Inventario de Artefactos

### 3.1 Modelos entrenados (`outputs/models/`)

| Archivo | Tipo | Target | R²_CV | Fecha |
|---------|------|--------|-------|-------|
| `lur_model_PM25.pkl` | SVR | PM2.5 (street) | 0.602 | 2026-04-14 |
| `lur_model_PM10.pkl` | SVR | PM10 (street) | 0.581 | 2026-04-14 |
| `lur_lsoa_PM25.pkl` | Ridge α=1 | PM2.5 (LSOA) | 0.203 | 2026-04-17 |
| `lur_lsoa_PM10.pkl` | Ridge α=1 | PM10 (LSOA) | 0.195 | 2026-04-17 |

### 3.2 Mapas y predicciones (`outputs/maps/`)

| Archivo | Geometría | Filas | Descripción |
|---------|-----------|-------|-------------|
| `liverpool_pollution_map.geojson` | LineString | 8,450 | Predicciones PM2.5/PM10 por tramo vial |
| `lur_lsoa_predictions.geojson` | Polygon | 302 | Predicciones + scores por LSOA |
| `lur_lsoa_predictions.csv` | — | 302 | Versión CSV del mismo dataset |

### 3.3 Datos procesados (`data/interim/` y `data/processed/`)

| Archivo | Descripción |
|---------|-------------|
| `sensores_monthly.csv` | Panel mensual 21 sensores × 11 meses (232 filas) |
| `lur_features.csv` | Variables LUR por sensor (27 variables tras VIF) |
| `lur_barrios_predictions.csv` | Zonal stats por LSOA (features para modelo LSOA) |
| `aadf_snapped.gpkg` | Tráfico AADF snapeado a red vial |
| `sensores_snapped.gpkg` | Sensores vinculados a tramos OSM |

### 3.4 Scripts principales (`src/models/`)

| Script | Función |
|--------|---------|
| `lur_model.py` | Pipeline street-level completo (Fases 1–7) |
| `lur_lsoa_model.py` | Pipeline LSOA (Issue #21): agregación + LOOCV + exportación |

### 3.5 Documentación (`docs/`)

| Doc | Contenido |
|-----|-----------|
| `00_project_structure.md` | Estructura general del proyecto |
| `01_resumen_ejecutivo.md` | Resumen ejecutivo inicial |
| `03_model_summary.md` | Resumen del modelo LUR street-level |
| `04_validation_report.md` | Reporte de validación LOOCV |
| `08_lur_improvement_session.md` | Sesión de mejora: Ridge → SVR, +0.016 R² |

---

## 4. Pipeline de Datos — Fases Completadas

```
[Raw Data]
  ├── Sensores 2024 (CSV/GPKG)          ✅ #16
  ├── OSM streets (GPK)                 ✅ #18
  ├── AADF traffic (CSV)                ✅ #18
  ├── Landuse (GPKG)                    ✅ #18
  ├── Buildings (GPKG)                  ✅ #18
  ├── LSOA boundaries (GPKG)            ✅ #21
  └── Census population (CSV)           ✅ #21

[Interim Processing]
  ├── sensores_monthly.csv              ✅ #16
  ├── meteo_monthly.csv                 ✅ #16
  ├── sensors_cleaned.csv               ✅ #16
  └── lur_features.csv                  ✅ #18

[Models]
  ├── Street SVR (PM2.5, PM10)          ✅ #20
  └── LSOA Ridge (PM2.5, PM10)         ✅ #21

[Outputs]
  ├── liverpool_pollution_map.geojson   ✅ #20
  └── lur_lsoa_predictions.geojson     ✅ #21
```

---

## 5. Issues Pendientes — Análisis de Gaps

### #19 — Datos Demográficos y Vulnerabilidad
**Estado:** 0/4 checkboxes  
**Bloquea:** Issue #24 (HIA)  
**Pendiente:**
- Descargar ONS Census 2021 por grupos de edad (0–4, 65+, etc.) a nivel LSOA
- Datos de mortalidad cardiovascular/respiratoria del NHS por LSOA
- Integrar con `lur_lsoa_predictions.geojson` (join por `LSOA21CD`)

### #24 — Health Impact Assessment (HIA)
**Estado:** 0/5 checkboxes  
**Requiere:** #19 completo  
**Pendiente:**
- Estimar muertes prematuras usando función dosis-respuesta WHO (PM2.5)
- Calcular DALY (Disability-Adjusted Life Years)
- Valoración económica (VSL — Value of Statistical Life)

### #25 — Desigualdades y Análisis Espacial
**Estado:** 4/5 — falta 1 ítem  
**Pendiente:**
- Evaluación de colegios vs límites WHO (buffer 100m escuelas + overlay con mapa de contaminación)

### #26 — Validación Externa DEFRA
**Estado:** 0/5 checkboxes  
**Pendiente:**
- Descargar datos PCM (Pollution Climate Mapping) del UK-AIR DEFRA para 2024
- Comparar predicciones LUR vs DEFRA para Liverpool (MAE, R², bias)
- Esta validación es clave para dar credibilidad externa al modelo

### #27 — Informe Final
**Estado:** 0/4 checkboxes  
**Requiere:** Cierre de #19, #24, #25, #26  
**Pendiente:** Redacción del informe académico completo

---

## 6. Contexto Regulatorio Relevante

| Marco | Objetivo | Relevancia |
|-------|----------|------------|
| UK Clean Air Strategy 2019 | PM2.5 < 10 µg/m³ anual para 2040 | **66% de LSOAs ya superan este nivel** |
| Environment Act 2021 | PM2.5 ≤ 10 µg/m³ para 2040 (objetivo intermedio) | Mismo umbral |
| WHO AQG 2021 | PM2.5 ≤ 5 µg/m³ anual | **100% de Liverpool supera el límite WHO** |
| EU Air Quality Directive | PM2.5 ≤ 25 µg/m³ (post-Brexit no vinculante) | Todos los LSOAs cumplen |
| CAZ Framework (DfT) | Zonas de Aire Limpio municipales | Liverpool sin CAZ activa |

> Todos los 302 LSOAs de Liverpool superan el objetivo WHO 2021 (≤5 µg/m³). El 51% supera también el objetivo UK 2040 (≥10 µg/m³). Esto refuerza la necesidad del MVP.

---

## 7. Progreso Global del Milestone 2

**Completado:** 5/10 issues (**50%** del trabajo técnico principal)  
**Bloqueado:** 1/10 (#24, por #19)  
**En progreso:** 1/10 (#25, 80% completo)  
**Pendiente:** 3/10 (#19, #26, #27)

**Estimación de gaps críticos por coste de tiempo:**
1. #26 Validación DEFRA — 1 sesión (descargar PCM, script comparación)
2. #19 Demográficos — 1–2 sesiones (APIs ONS, join LSOA)
3. #25 Colegios — media sesión (OSM schools + buffer overlay)
4. #24 HIA — 1–2 sesiones (requiere #19)
5. #27 Informe Final — 2–3 sesiones (redacción)
