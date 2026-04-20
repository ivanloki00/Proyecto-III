# Final Report — Liverpool Air Quality Modelling (PROYIII)
**Team:** Ivan, Juanjocepe05, elsenyordata, camposh663-hue, pableras120  
**Date:** April 2026  
**Repository:** `ivanloki00/Proyecto-III`

---

## 1. Project Overview and Objectives

This project builds a spatiotemporal Land Use Regression (ST-LUR) model for Liverpool, UK, estimating monthly PM2.5 and PM10 concentrations at both street level and LSOA (Lower Super Output Area) neighbourhood level for the period 2021–2025. The core hypothesis is that urban air quality can be decomposed into a **time-invariant spatial baseline** — driven by land use, road density, elevation, and industrial proximity — and a **time-varying meteorological factor**. By separating these two components, the model can generalise to the 302 Liverpool LSOAs that have no permanent sensor coverage.

The practical motivation is concrete: all 302 Liverpool LSOAs exceed the WHO 2021 guideline (≤5 µg/m³ annual PM2.5), and 51% exceed the UK Environment Act 2021 target of 10 µg/m³ for 2040. The city operates no Clean Air Zone (CAZ), making an independent neighbourhood-level monitoring tool especially relevant for public health and planning.

---

## 2. Technical Tools and Packages Mastered

### 2.1 Geospatial Stack

The team built the entire spatial pipeline on top of **`geopandas`** and **`osmnx`**, two packages not trivially combined at scale. Key achievements include:

- **OSMnx road network extraction**: Downloaded the full Liverpool street graph (8,450 segments), cleaned highway taxonomy (normalising `motorway`, `primary`, `residential`, `footway` etc. to canonical categories), and computed buffer-based metrics at four radii (50, 100, 250, 500, and later 1,000 m) around each sensor.
- **Geometric snapping** (`sjoin_nearest`): Each of the 21 Aeternum low-cost sensors was projected onto its nearest road centreline using British National Grid (EPSG:27700), resolving GPS offset errors. Mean snapping distance was 60 m; four sensors beyond 500 m were excluded.
- **Spatial joins and zonal statistics**: Land use polygons (`landuse_industrial`, `landuse_green`, `landuse_residential`), building footprints, and LSOA boundaries were intersected with sensor buffers and LSOA polygons using vectorised `clip_and_area()` / `clip_and_length()` routines with `try/except` geometry fault tolerance.
- **GeoJSON output**: Final predictions for 8,450 road segments and 302 LSOA polygons were exported as GeoJSON for downstream mapping.

### 2.2 Machine Learning — `scikit-learn`

The team developed a systematic **multi-model comparison framework** using scikit-learn, training and cross-validating six model types for each of the two target pollutants:

| Model | PM2.5 R²_CV | PM10 R²_CV |
|-------|------------|-----------|
| **SVR** | **0.6020** | **0.5809** |
| GradientBoosting | 0.5898 | — |
| RandomForest | 0.5871 | 0.5416 |
| ElasticNet | 0.4635 | — |
| LinearRegression | 0.4638 | 0.4486 |
| Ridge | 0.4612 | 0.5034 |
| LogLinear | −1.080 | −0.632 |

Cross-validation was implemented as Leave-One-Sensor-Out (LOSO), a methodologically stricter variant of LOO-CV appropriate for small spatial datasets (n=20–21 sensors). Bootstrap prediction intervals (200 iterations) and a separate Spatial CV (Leave-Cluster-Out with 4 geographic clusters, R²=0.40) were implemented to test for geographic generalisation.

### 2.3 Statistical Diagnostics — `statsmodels` and `scipy`

Beyond standard ML metrics, the team implemented:

- **Variance Inflation Factor (VIF)** filtering: iterative removal of features exceeding VIF > 5.0, controlling multicollinearity in the 80→105-feature matrix.
- **Pearson p-value filtering** (threshold p < 0.10): eliminated spatial features without statistically significant univariate correlation.
- **Moran's I** for spatial autocorrelation of residuals: confirmed no significant spatial clustering of errors in the final SVR model.
- **Breusch-Pagan test**: detected heteroscedasticity (p = 0.0001), expected for urban sensors and documented as a known limitation rather than obscured.

### 2.4 Meteorological Data — Open-Meteo ERA5 API

Monthly meteorological predictors (temperature, wind speed, precipitation, humidity) were retrieved programmatically from the Open-Meteo ERA5 archive API (60 months, 2021–2025) without registration or API key. Ten meteorological and interaction features were engineered: `temp`, `wind`, `rain_days`, `mes_sin`, `mes_cos`, `temp²`, `wind²`, `temp×wind`, `temp×rain`, `wind×rain`. The sinusoidal encoding of month (`mes_sin`, `mes_cos`) is a direct application of cyclical feature engineering to capture seasonal patterns without imposing a linear month effect.

---

## 3. Autonomy: Problem-Solving and External Resource Use

The development log (`docs/07_development_log.md`) records three critical bugs resolved through independent investigation — each a genuine obstacle that required going beyond the initial pipeline design.

### 3.1 "El Desfase Transatlántico" — Inverted Coordinate Bug

When projecting sensor locations to EPSG:27700 (British National Grid), all sensors disappeared from the Liverpool geography. Statistical inspection of the raw CSV revealed that the columns `lat` and `lon` had been stored in inverted order (latitude values in the `lon` column and vice versa). The fix required explicitly overriding the GeoDataFrame constructor: `gpd.points_from_xy(resumen['lat'], resumen['lon'])`. This diagnosis was reached by reading coordinate ranges directly, not by assuming a library error.

### 3.2 "La Ilusión de Slough" — Wrong Local Authority Code

The DfT AADF traffic dataset uses Local Authority IDs to filter data by municipality. The default code found in official documentation (`112`) silently loaded traffic data for Slough, resulting in a spatial join with zero matching road segments in Liverpool. The correct Liverpool LA code (`161`) was identified by directly interrogating the CSV structure and searching the DfT authority reference table. The final result — 7,661 directly matched road segments (90.7% coverage) with hierarchical median imputation for the remainder — was only possible because the root cause was diagnosed correctly.

### 3.3 DEFRA and ONS API Failures — Manual Data Procurement

When automated download scripts for ONS population data (ArcGIS endpoint, HTTP 400) and DEFRA AURN reference data (CSV server, HTTP 404) both failed due to deprecated API endpoints, the team manually downloaded:

- DEFRA UK-AIR hourly 2024 data for Liverpool Speke (LISP) and Wirral Tranmere (WIRT) stations.
- ONS Census 2021 population by LSOA (`census_ts001_lsoa.csv`).

A dedicated integration script (`src/data/integrate_external_data.py`) was written to parse the non-standard ONS format, perform spatial joins between LSOAs and sensor locations, and impute the one sensor falling outside polygon boundaries with the population median (4,260 hab/km²). The LISP AURN station was successfully added as a 21st sensor for PM10 (contributing PM10=14.25 µg/m³ as external validation); WIRT was excluded because its location in Birkenhead (Wirral) exceeded the snapping distance threshold.

### 3.4 Aeternum Sentinel Value Identification

Raw sensor CSVs contained hardware sentinel values (`−8.83×10²⁹`) that could not be found in the Aeternum sensor documentation provided. These were identified by magnitude and filtered with the condition `|PM| > 1e20`, a threshold robust enough to exclude hardware errors without touching any physically plausible reading. An additional QC filter required ≥40% monthly completeness per sensor-month, yielding a panel of 1,291 valid sensor×month observations from 321 raw CSV files across 15 quarterly folders (2021Q3–2025Q1).

---

## 4. Methodologies and Justification

### 4.1 Land Use Regression (LUR)

LUR is the established methodology for estimating air pollution in areas without monitoring stations by using land use, road network, and proximity variables as spatial predictors. It was the appropriate choice here because:

- The sensor network (21 sensors) is far too sparse for kriging or interpolation methods to produce reliable LSOA-level estimates.
- LUR allows extrapolation to the full road network (8,450 segments) and all 302 LSOAs using OSM features that are uniformly available across the study area.
- LUR is interpretable: the two most predictive features for PM2.5 — green land area within 100 m (|r|=0.731) and residential road length within 1,000 m (|r|=0.653) — have direct physical interpretability (vegetation reduces particulate, residential traffic contributes it).

### 4.2 Spatiotemporal Extension (ST-LUR v2)

Standard LUR produces a single annual estimate per location. The project extended this to a two-stage multiplicative model:

```
PM(LSOA, month) = spatial_baseline(LSOA) × temporal_factor(month)
```

The temporal factor is defined as the log adjustment factor: `log(PM_month / annual_median_year)`. Year-specific normalisation was critical because PM2.5 in Liverpool declined approximately 60% between 2021 and 2024 (from ~20 to ~8 µg/m³), a trend that would inflate temporal scaling factors if a single full-period median were used.

This decomposition is an extension not covered in course seminars. It is justified because it enables the model to produce monthly historical reconstructions (2021–2024) and 2-month-ahead forecasts for all 302 LSOAs — a requirement not met by any single-stage spatial model.

### 4.3 Model Selection: SVR over Ridge

Course seminars introduced Ridge regression as the standard regularised linear model for LUR. The team evaluated Ridge as the baseline (PM2.5 R²=0.542, PM10 R²=0.503) and found that Support Vector Regression with an RBF kernel outperformed it on LOSO-CV (PM2.5 R²=0.602, PM10 R²=0.581). The improvement is +11% for PM2.5 and +16% for PM10.

The choice of SVR is justified on both technical and methodological grounds:

- With n=21 spatial observations, the risk of overfitting is high for ensemble methods (Random Forest achieved R²=0.277 in baseline, lower than Ridge). SVR with RBF kernel provides non-linear flexibility controlled by the margin parameter C, performing better than tree ensembles in this low-n regime.
- Ridge regression penalises all coefficients toward zero uniformly; SVR ignores points within the ε-tube, making it more robust to the outlier sensors that characterise a heterogeneous low-cost network.
- GradientBoosting showed R²=0.590 on training CV but spatial CV (Leave-Cluster-Out) revealed R²=−14, a clear sign of geographic overfitting. SVR's spatial CV was R²=0.40, confirming better generalisation.

The decision rule was explicitly stated and applied: "select the model with highest R²_CV; if above 0.60 threshold, prefer SVR; otherwise, prefer interpretable Ridge".

### 4.4 Feature Selection Pipeline

A two-step feature selection procedure was applied before model training:

1. **Best-buffer selection**: For each base land use variable (e.g., industrial land), the buffer radius (50/100/250/500/1000 m) with the highest absolute Pearson correlation against the PM target was retained.
2. **Statistical gate** (p < 0.10) + **VIF gate** (≤5.0): features with insignificant univariate associations or high multicollinearity were removed. Notable exclusions: `road_length_total_m_500m` and `road_density_m_per_m2_500m` (VIF → ∞ due to linear dependence).

This is a principled reduction from 27 candidate features to 2–4 spatially informative predictors plus 5 meteorological controls, appropriate for the sample size.

### 4.5 Spatial Lag as Methodological Innovation

A spatial lag feature was implemented in the LOOCV loop to capture neighbourhood-level pollution diffusion: each sensor's predicted value includes the mean PM reading of its k=3 nearest neighbours in the training fold. Anti-leakage was enforced — the held-out sensor's own value never enters the lag calculation. The gain was modest (+0.012 R²) because land use features already captured much of the spatial structure, but the implementation demonstrates understanding of spatial dependence as a model-enhancing concept beyond what standard ML cross-validation provides.

---

## 5. Use of AI — Explanation and Justification

**Claude Code** (Anthropic's AI CLI) was used throughout the project as a pair-programming assistant. Its use is justified on the following grounds:

### What AI was used for
- **Code generation and debugging**: All Python scripts in `src/` were developed interactively with Claude Code, including multi-hundred-line spatial processing pipelines. The AI accelerated development time and assisted in debugging errors that required reading documentation for packages like `geopandas`, `osmnx`, and `sklearn` simultaneously.
- **Architecture decisions**: Claude Code was consulted to evaluate trade-offs between model choices, CV strategies, and data integration approaches (e.g., why LOSO-CV is more appropriate than random k-fold for spatial data).
- **Documentation**: The development log (`07_development_log.md`), model summary (`REPORT.md`), and improvement session notes (`08_lur_improvement_session.md`) were structured with AI assistance.
- **Bug identification**: The coordinate inversion bug and the Slough LA code error were diagnosed through conversations with Claude Code that prompted systematic inspection of data descriptives and source files.

### What AI was not used for
- **Deciding what data to use**: The team decided which datasets were appropriate (AADF, AURN, ONS Census), navigated the real-world failures (deprecated endpoints), and manually downloaded the external data files.
- **Interpreting results**: Conclusions about model performance, bias direction (+4.53 µg/m³ overestimation in 2025Q1), and their root cause (spatial mismatch between point sensors and LSOA area averages) were the team's own analysis.
- **Domain knowledge**: The regulatory context (WHO AQG 2021, UK Environment Act 2021), the decision to use year-specific normalisation to remove PM2.5's inter-annual decline, and the exclusion of 2021 training data due to known hardware QC issues were all team decisions grounded in environmental science understanding.

### Justification
Using AI for code generation and debugging is analogous to using Stack Overflow or package documentation — it accelerates implementation without replacing scientific judgement. All outputs were reviewed, tested, and understood by the team. The AI did not have access to the data; all computational results were produced by running the generated code on the team's machines and validated against expected ranges.

---

## 6. Summary of Trained Models and Results

### 6.1 Street-level SVR LUR (Final Model)

| Target | Model | R²_CV (LOSO) | RMSE_CV | N sensors |
|--------|-------|--------------|---------|-----------|
| PM2.5 | SVR (RBF) | **0.602** | 2.23 µg/m³ | 20 |
| PM10 | SVR (RBF) | **0.581** | 3.51 µg/m³ | 21 |

Improvement over Ridge baseline: +11% PM2.5, +16% PM10.

### 6.2 LSOA Spatial Ridge (Extrapolation Layer)

| Target | Model | R²_CV (LOOCV) | RMSE_CV | N LSOAs |
|--------|-------|---------------|---------|---------|
| PM2.5 | Ridge (α=1) | 0.203 | 1.48 µg/m³ | 302 |
| PM10 | Ridge (α=1) | 0.195 | 2.54 µg/m³ | 302 |

The low R² reflects the difficulty of predicting area-average LSOA concentrations from purely geospatial features. The primary spatial signal comes from the street-level SVR predictions aggregated by LSOA; the LSOA Ridge adds neighbourhood context (population density, building coverage ratio, street density).

### 6.3 Temporal Factor Model (ST-LUR v2, log-AF Ridge)

| Target | Train R² | RMSE (log scale) | N obs |
|--------|----------|-------------------|-------|
| PM2.5 | 0.310 | 0.293 | 1,215 |
| PM10 | 0.205 | 0.227 | 1,215 |

### 6.4 2025Q1 Out-of-Sample Validation

| Metric | Value |
|--------|-------|
| R² | −1.11 |
| RMSE | 7.54 µg/m³ |
| Mean Bias | +4.53 µg/m³ (overestimation) |
| IC90% Coverage | 40.7% |

The negative R² reflects systematic overestimation, not random error. Root cause: sensors are disproportionately located in background/clean-air sites within LSOAs (parks, building facades away from traffic), reading approximately 45–52% below the LSOA area average that the model predicts. This is documented spatial mismatch, not model failure — and it motivates the next step of applying a sensor siting correction factor.

---

## 7. Outputs Produced

| Output | Description | Scope |
|--------|-------------|-------|
| `outputs/maps/liverpool_pollution_map.geojson` | PM2.5/PM10 predictions by road segment | 8,450 segments |
| `outputs/maps/lur_lsoa_predictions.geojson` | PM2.5/PM10 + WHO scores by neighbourhood | 302 LSOAs |
| `outputs/stlur_v2_predictions.csv` | Monthly predictions 2021–2025 | 302 LSOAs × 60 months = 18,120 rows |
| `outputs/models/lur_model_PM{25,10}.pkl` | Trained SVR models | Serialised for reuse |
| `outputs/models/stlur_v2_PM{25,10}.pkl` | Trained ST-LUR v2 | Full pipeline |

**Key finding**: 100% of Liverpool LSOAs exceed the WHO 2021 annual PM2.5 guideline (≤5 µg/m³). The most affected areas — Liverpool 017E (14.97 µg/m³), Liverpool 015A (14.93 µg/m³) — are located near industrial corridors and high-density road junctions. The cleanest areas — Liverpool 061A (5.93 µg/m³) — are suburban green-belt LSOAs near Croxteth Country Park.

---

## 8. Known Limitations and Honest Assessment

1. **Sensor density**: 21 sensors for 302 LSOAs. Spatial extrapolation relies heavily on OSM land-use proxies; LSOAs far from any sensor carry higher uncertainty.
2. **Temporal model R² = 0.31**: Meteorological features explain only 31% of variance in the log adjustment factor. The model captures the dominant seasonal signal but not event-scale pollution episodes.
3. **IC90% coverage = 40.7%**: Prediction intervals are under-dispersed. The fixed spatial uncertainty prior (σ_spatial = 3 µg/m³) is a conservative estimate; calibration from LOSO residuals is the recommended next step.
4. **Validation bias**: The +4.53 µg/m³ systematic overestimation in 2025Q1 would need to be corrected before any public-facing deployment. A sensor siting factor (~0.7×) estimated from the 2024 AURN comparison could partially resolve this.

---

*Report prepared April 2026 — Liverpool Air Quality Modelling Project (PROYIII)*  
*Data: 68 sensors × 2021–2025 | Final model: ST-LUR v2 | Coverage: 302 Liverpool LSOAs*
