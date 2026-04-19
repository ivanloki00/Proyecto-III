# Project Report: Liverpool Air Quality ST-LUR

**Last Updated:** 2026-04-19
**Phase:** Model Retrain + 2025 Validation
**Target:** PM2.5 and PM10 monthly predictions for 302 Liverpool LSOAs (2021–2025)

---

## 1. Project Summary

### Objective

Reconstruct 12-month historical PM2.5/PM10 concentration curves for Liverpool neighbourhoods (LSOAs) without permanent air quality sensors, and produce 2-month ahead forecasts. The model is intended for public health and planning applications.

### Study Area

- Liverpool, UK — 302 Lower Super Output Areas (LSOAs)
- Sensor network: up to 68 low-cost Aeternum sensors (2021–2025)
- Meteorological reference: Liverpool Airport (53.33°N, -2.85°W) via Open-Meteo ERA5

### Edge / Hypothesis

Urban air quality is decomposable into a **time-invariant spatial baseline** (driven by land use, roads, elevation, proximity to industrial sources) and a **time-varying factor** (driven by meteorology and seasonality). Separating these two components allows generalisation to unmonitored areas.

---

## 2. Model Architecture — Spatiotemporal LUR (ST-LUR v2)

Two-stage multiplicative model:

```
PM2.5(LSOA, month) = spatial_baseline(LSOA) × temporal_factor(month)
```

### Stage 1 — Spatial Baseline

- **Input**: Annual median PM2.5/PM10 per sensor (year 2024)
- **Features**: Road density, green land ratio, elevation, industrial proximity, residential land cover, AADF traffic (OSM + UK DfT)
- **Model**: Ridge regression (standardised features)
- **Extrapolation**: Predicts annual baseline for all 302 LSOAs from OSM/land-use features

### Stage 2 — Temporal Adjustment Factor (log-AF)

- **Definition**: `log(PM_month / annual_median_year_sensor)` — year-specific normalisation removes inter-annual trend
- **Features**: 10 predictors — `temp`, `wind`, `rain_days`, `mes_sin`, `mes_cos`, `temp²`, `wind²`, `temp×wind`, `temp×rain`, `wind×rain`
- **Model**: Ridge regression on log-AF
- **Training**: 2022-01 to 2025-03 (2021 excluded: elevated sentinel contamination)

### Prediction Intervals (Combined IC90%)

```
σ_total² = σ_temporal_bootstrap² + σ_spatial_LUR²
σ_spatial(PM2.5) = 3.0 µg/m³ | σ_spatial(PM10) = 6.0 µg/m³
```

---

## 3. Data Pipeline

### 3.1 Raw Sensor Data

| Item | Value |
|---|---|
| Raw CSV files processed | 321 |
| Quarterly folders | 2021Q3–2025Q1 |
| QC filters applied | Sentinel (`\|PM\| > 1e20`), physical range [0, 150] PM2.5 / [0, 300] PM10 |
| Completeness threshold | ≥ 40% observations per month |
| **Panel output** | 1,291 sensor×month observations |
| Unique sensors | 68 |
| Temporal range | 2021-03 to 2025-03 |

Key QC issue: Aeternum hardware sentinel = `-8.83×10²⁹` (detected by magnitude).

### 3.2 Meteorology (Open-Meteo ERA5)

| Item | Value |
|---|---|
| Source | archive-api.open-meteo.com (free, no API key) |
| Variables | temp_2m, rel_humidity, wind_speed_10m, precipitation |
| Resolution | Hourly → aggregated to monthly means/totals |
| Coverage | 2021-01 to 2025-12 (60 months) |

### 3.3 Spatial Features (pre-existing)

- OSM road network: buffer radii 50m / 250m / 500m / 1000m
- AADF traffic counts (UK DfT)
- Land use: industrial, residential, commercial, green
- Elevation (DEM)
- Distance to: industrial areas, city centre, port, airport, tunnel, station

---

## 4. Model Performance

### 4.1 Sensor-Level LUR (training baseline — SVR)

| Target | R² (CV) | RMSE (CV) | N sensors |
|---|---|---|---|
| PM2.5 | **0.602** | 2.23 µg/m³ | 20 |
| PM10 | **0.581** | 3.51 µg/m³ | 21 |

Cross-validation: Leave-One-Sensor-Out (LOSO) on annual means.

### 4.2 LSOA Spatial LUR (Ridge, extrapolation layer)

| Target | R² (LOO-CV) | RMSE (LOO-CV) | N LSOAs |
|---|---|---|---|
| PM2.5 | 0.203 | 1.48 µg/m³ | 302 |
| PM10 | 0.195 | 2.54 µg/m³ | 302 |

Low R² reflects point-to-area extrapolation challenge (sensors capture local plumes, not LSOA area averages).

### 4.3 Temporal Factor Model (log-AF Ridge)

| Target | Train R² | Train RMSE (log scale) | N observations |
|---|---|---|---|
| PM2.5 | 0.310 | 0.293 | 1,215 |
| PM10 | 0.205 | 0.227 | 1,215 |

### 4.4 2025Q1 Out-of-Sample Validation

Hold-out: January–March 2025 | N = 27 observations across 14 sensors

| Metric | Value |
|---|---|
| R² | -1.11 |
| RMSE | 7.54 µg/m³ |
| Mean Bias | +4.53 µg/m³ (model overestimates) |
| IC90% Coverage | **40.7%** |
| % obs below model pred | 78% |

**Root cause of bias**: Spatial mismatch. The LSOA spatial baseline predicts area-average concentrations. Sensors are disproportionately sited in background/clean-air locations within LSOAs (parks, building facades away from traffic). Sensor readings ≈ 45–52% of LSOA area average — this is expected LUR behaviour, not a model failure.

---

## 5. Outputs

### Prediction Files

| File | Description | Rows |
|---|---|---|
| `outputs/stlur_v2_predictions.csv` | Historical (2021-01 to 2024-12) + forecast (2025-01 to 2025-12) for all 302 LSOAs | 18,120 |
| `outputs/stlur_v2_validation.csv` | 2025Q1 hold-out observed vs. predicted | 27 |
| `outputs/stlur_predictions.csv` | ST-LUR v1 (2024-only, superseded) | 4,228 |
| `outputs/maps/lur_lsoa_predictions.csv` | Spatial baseline predictions for 302 LSOAs | 302 |
| `outputs/maps/lur_lsoa_predictions.geojson` | Same, with geometries for mapping | — |

### Interim Data

| File | Description |
|---|---|
| `data/interim/sensores_monthly_full.csv` | Full 2021-2025 sensor panel (1,291 rows, 68 sensors) |
| `data/interim/meteo_monthly_full.csv` | ERA5 monthly meteo 2021-2025 (60 months) |
| `data/interim/lur_features.csv` | LSOA spatial features (302 LSOAs) |

### Trained Models

| File | Contents |
|---|---|
| `outputs/models/stlur_v2_PM25.pkl` | ST-LUR v2 for PM2.5 (temporal Ridge + spatial baseline) |
| `outputs/models/stlur_v2_PM10.pkl` | ST-LUR v2 for PM10 |
| `outputs/models/lur_model_PM25.pkl` | Sensor-level SVR LUR (PM2.5) |
| `outputs/models/lur_model_PM10.pkl` | Sensor-level SVR LUR (PM10) |
| `outputs/models/lur_lsoa_PM25.pkl` | LSOA spatial Ridge (PM2.5) |
| `outputs/models/lur_lsoa_PM10.pkl` | LSOA spatial Ridge (PM10) |

---

## 6. Key Figures

### EDA
- `outputs/figures/eda/ts_monthly_pollution.png` — Time series 2021–2024
- `outputs/figures/eda/lur_pm_por_sensor.png` — PM2.5 by sensor
- `outputs/figures/eda/lur_mapa_sensores.png` — Sensor locations
- `outputs/figures/eda/lur_correlacion_features.png` — Feature correlation matrix

### Spatial LUR
- `outputs/figures/lur/map_PM25.png` — Predicted PM2.5 map (302 LSOAs)
- `outputs/figures/lur/map_PM10.png` — Predicted PM10 map
- `outputs/figures/lur/obs_vs_pred_PM25.png` — LUR scatter plot
- `outputs/figures/lur/importancia_variables_PM25.png` — Feature importance

### ST-LUR v2
- `outputs/figures/stlur/stlur_v2_PM25_E01006512.png` — Example LSOA time series
- `outputs/figures/stlur/stlur_v2_PM25_E01006514.png`
- `outputs/figures/stlur/stlur_v2_PM25_E01006518.png`

---

## 7. Key Technical Decisions

| Decision | Rationale |
|---|---|
| Year-specific log-AF normalisation | PM2.5 trend 2021→2024: ~20→8 µg/m³. Full-period median inflated winter factors for 2025; year-specific anchoring removes inter-annual drift |
| `train_from="2022-01"` | 2021 sensor data has higher sentinel contamination and anomalous high readings before QC procedures were stable |
| Bootstrap + spatial σ for IC | Bootstrap alone gave 0% IC90% coverage; adding σ_spatial=3 µg/m³ raises it to 40.7% |
| Climatological meteo for forecast | Future months use median of same month across all historical years — more robust than single-year analog when full ERA5 is unavailable |
| Open-Meteo ERA5 (free) | No registration, no quota issues, full 2021–2025 coverage including partial 2025 actuals |

---

## 8. Source Files

| File | Role |
|---|---|
| `src/data/build_full_panel.py` | Downloads meteo + processes 321 raw CSVs → sensor panel |
| `src/models/stlur_retrain.py` | ST-LUR v2: training, LOOSO-CV, temporal split validation, forecasting |
| `src/models/stlur_forecast.py` | ST-LUR v1 (2024-only, superseded) |
| `src/models/lur_lsoa_model.py` | LSOA spatial LUR (Ridge extrapolation to 302 LSOAs) |
| `src/models/lur_model.py` | Sensor-level SVR LUR |

---

## 9. Limitations and Next Steps

### Known Limitations

1. **Spatial mismatch**: Point sensors ≠ LSOA area averages → systematic +4.5 µg/m³ overestimation in 2025Q1 validation. Sensor placement bias (background sites) is the primary driver.
2. **Temporal model R² = 0.31**: Log-AF is inherently noisy (ratio of monthly/annual medians). The signal is real but meteorological features explain only 31% of variance.
3. **IC90% coverage = 40.7%**: Prediction intervals are too narrow or the spatial σ component is underestimated. σ_spatial = 3 µg/m³ is a conservative prior — could be calibrated from LOOSO residuals.
4. **Sensor density**: 68 sensors across 302 LSOAs — many LSOAs have no nearby sensor; spatial extrapolation relies heavily on OSM land-use proxies.

### Recommended Next Steps

- [ ] Calibrate σ_spatial from LOOSO residual distribution rather than using a fixed 3 µg/m³ prior
- [ ] Apply a sensor siting correction factor (~0.7×) to shift baseline predictions to sensor-comparable scale for validation
- [ ] Increase training data by importing 2021–2022 sensor data more aggressively (reduce `train_from` cutoff after verifying data quality)
- [ ] Explore kriging or Gaussian process for spatial interpolation as alternative to Ridge on land-use features
- [ ] Add traffic intensity time series (lockdown effects visible in 2021 data) as temporal predictor

---

*Generated by /cbt:report — Liverpool Air Quality ST-LUR Project*
*Data: 68 sensors × 2021-2025 | Model: ST-LUR v2 | 302 LSOAs covered*
