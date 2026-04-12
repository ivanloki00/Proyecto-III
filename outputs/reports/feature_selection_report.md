# Feature Selection Report — LUR Liverpool Air Quality

**Fecha:** 2026-04-10  |  **n sensores:** 20  |  **Buffers evaluados:** 50, 100, 250, 500 m

---

## Contexto metodológico

- **n=20** — tamaño muestral pequeño; umbral p<0.10 es moderado (no conservador) para regresión univariante.
- Selección de escala: para cada variable base se elige el buffer que maximiza |r| con el target.
- Filtro p-value: OLS univariante sobre la variable en su mejor escala.
- Filtro VIF: eliminación iterativa del predictor con VIF más alto hasta que todos queden ≤ 5.0.

---

# Target: PM2.5

## Paso 1 — Correlaciones (Pearson r) por variable × buffer

| Variable | 50m | 100m | 250m | 500m | Best buf | Best |r| | p-value |
|---|---|---|---|---|---|---|---|
| aadf_total_sum | -0.162 | -0.078 | 0.092 | 0.295 | 500m | 0.295 | 0.207 |
| aadf_total_mean | -0.259 | 0.022 | -0.266 | -0.001 | 250m | 0.266 | 0.257 |
| aadf_total_max | -0.207 | 0.115 | -0.054 | -0.098 | 50m | 0.207 | 0.382 |
| road_length_total_m | -0.137 | 0.058 | 0.288 | 0.474 | 500m | 0.474 | 0.035 |
| road_length_motorway_m | — | — | — | — | N/A | — | — |
| road_length_primary_m | -0.080 | -0.050 | -0.199 | -0.304 | 500m | 0.304 | 0.192 |
| road_length_secondary_m | -0.099 | -0.086 | -0.127 | -0.130 | 500m | 0.130 | 0.584 |
| road_length_residential_m | -0.025 | 0.143 | 0.387 | 0.557 | 500m | 0.557 | 0.011 |
| road_density_m_per_m2 | -0.137 | 0.058 | 0.288 | 0.474 | 500m | 0.474 | 0.035 |
| building_area_m2 | 0.120 | 0.112 | 0.071 | 0.107 | 50m | 0.120 | 0.615 |
| building_coverage_ratio | 0.120 | 0.112 | 0.071 | 0.107 | 50m | 0.120 | 0.615 |
| landuse_industrial_m2 | -0.366 | -0.389 | -0.392 | -0.386 | 250m | 0.392 | 0.087 |
| landuse_industrial_ratio | -0.366 | -0.389 | -0.392 | -0.386 | 250m | 0.392 | 0.087 |
| landuse_residential_m2 | 0.259 | 0.304 | 0.296 | 0.322 | 500m | 0.322 | 0.166 |
| landuse_residential_ratio | 0.259 | 0.304 | 0.296 | 0.322 | 500m | 0.322 | 0.166 |
| landuse_commercial_m2 | -0.071 | -0.067 | -0.144 | -0.215 | 500m | 0.215 | 0.363 |
| landuse_commercial_ratio | -0.071 | -0.067 | -0.144 | -0.215 | 500m | 0.215 | 0.363 |
| landuse_green_m2 | 0.513 | 0.731 | 0.535 | 0.431 | 100m | 0.731 | 0.000 |
| landuse_green_ratio | 0.513 | 0.731 | 0.535 | 0.431 | 100m | 0.731 | 0.000 |
| dist_industrial_m | 0.550 | 0.550 | 0.550 | 0.550 | 50m | 0.550 | 0.012 |
| intersections_count | -0.080 | 0.108 | 0.299 | 0.347 | 500m | 0.346 | 0.134 |
| dist_centre_m | 0.050 | 0.050 | 0.050 | 0.050 | 50m | 0.050 | 0.834 |

## Paso 2 — Filtro p-value univariante

Candidatas iniciales (tras selección de escala): **21**

### Retenidas p < 0.10 (8 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `road_length_total_m_500m` | 0.4740 | 0.0347 |
| `road_length_residential_m_500m` | 0.5570 | 0.0107 |
| `road_density_m_per_m2_500m` | 0.4740 | 0.0347 |
| `landuse_industrial_m2_250m` | 0.3924 | 0.0870 |
| `landuse_industrial_ratio_250m` | 0.3924 | 0.0870 |
| `landuse_green_m2_100m` | 0.7314 | 0.0002 |
| `landuse_green_ratio_100m` | 0.7314 | 0.0002 |
| `dist_industrial_m_50m` | 0.5496 | 0.0121 |

### Zona gris p ∈ [0.10, 0.15) — añadidas solo en escenario relajado (1 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `intersections_count_500m` | 0.3465 | 0.1344 |

### Eliminadas p ≥ 0.15 (12 variables)

| Variable (mejor buffer) | |r| | p-value | Razón |
|---|---|---|---|
| `aadf_total_sum_500m` | 0.2949 | 0.2068 | p ≥ 0.15 |
| `aadf_total_mean_250m` | 0.2660 | 0.2570 | p ≥ 0.15 |
| `aadf_total_max_50m` | 0.2067 | 0.3819 | p ≥ 0.15 |
| `road_length_primary_m_500m` | 0.3043 | 0.1921 | p ≥ 0.15 |
| `road_length_secondary_m_500m` | 0.1303 | 0.5839 | p ≥ 0.15 |
| `building_area_m2_50m` | 0.1199 | 0.6145 | p ≥ 0.15 |
| `building_coverage_ratio_50m` | 0.1199 | 0.6145 | p ≥ 0.15 |
| `landuse_residential_m2_500m` | 0.3223 | 0.1657 | p ≥ 0.15 |
| `landuse_residential_ratio_500m` | 0.3223 | 0.1657 | p ≥ 0.15 |
| `landuse_commercial_m2_500m` | 0.2150 | 0.3627 | p ≥ 0.15 |
| `landuse_commercial_ratio_500m` | 0.2150 | 0.3627 | p ≥ 0.15 |
| `dist_centre_m_50m` | 0.0501 | 0.8339 | p ≥ 0.15 |

## Paso 3 — Filtro VIF (umbral = 5.0)

### Escenario p < 0.10

Variables pre-VIF: **8** → Variables finales: **4**

**Eliminaciones por VIF:**

| Variable eliminada | VIF |
|---|---|
| `road_length_total_m_500m` | inf |
| `landuse_industrial_m2_250m` | inf |
| `landuse_green_m2_100m` | inf |
| `road_density_m_per_m2_500m` | 19.11 |

**Variables finales y sus VIF:**

| Variable | VIF | |r| con target | p-value |
|---|---|---|---|
| `road_length_residential_m_500m` | 1.930 | 0.5570 | 0.0107 |
| `landuse_industrial_ratio_250m` | 1.071 | 0.3924 | 0.0870 |
| `landuse_green_ratio_100m` | 1.530 | 0.7314 | 0.0002 |
| `dist_industrial_m_50m` | 2.241 | 0.5496 | 0.0121 |

### Escenario p < 0.15

Variables pre-VIF: **9** → Variables finales: **4**

**Eliminaciones por VIF:**

| Variable eliminada | VIF |
|---|---|
| `road_length_total_m_500m` | inf |
| `landuse_industrial_m2_250m` | inf |
| `landuse_green_m2_100m` | inf |
| `road_density_m_per_m2_500m` | 65.86 |
| `intersections_count_500m` | 13.26 |

**Variables finales y sus VIF:**

| Variable | VIF | |r| con target | p-value |
|---|---|---|---|
| `road_length_residential_m_500m` | 1.930 | 0.5570 | 0.0107 |
| `landuse_industrial_ratio_250m` | 1.071 | 0.3924 | 0.0870 |
| `landuse_green_ratio_100m` | 1.530 | 0.7314 | 0.0002 |
| `dist_industrial_m_50m` | 2.241 | 0.5496 | 0.0121 |

---

# Target: PM10

## Paso 1 — Correlaciones (Pearson r) por variable × buffer

| Variable | 50m | 100m | 250m | 500m | Best buf | Best |r| | p-value |
|---|---|---|---|---|---|---|---|
| aadf_total_sum | -0.150 | -0.065 | -0.000 | 0.243 | 500m | 0.243 | 0.302 |
| aadf_total_mean | -0.232 | 0.008 | -0.332 | 0.021 | 250m | 0.332 | 0.152 |
| aadf_total_max | -0.181 | 0.090 | -0.119 | -0.070 | 50m | 0.181 | 0.444 |
| road_length_total_m | -0.098 | 0.103 | 0.234 | 0.416 | 500m | 0.416 | 0.068 |
| road_length_motorway_m | — | — | — | — | N/A | — | — |
| road_length_primary_m | -0.056 | -0.026 | -0.249 | -0.322 | 500m | 0.322 | 0.166 |
| road_length_secondary_m | -0.110 | -0.100 | -0.199 | -0.192 | 250m | 0.199 | 0.401 |
| road_length_residential_m | 0.024 | 0.185 | 0.367 | 0.514 | 500m | 0.514 | 0.020 |
| road_density_m_per_m2 | -0.098 | 0.103 | 0.234 | 0.416 | 500m | 0.416 | 0.068 |
| building_area_m2 | 0.090 | 0.045 | -0.017 | 0.020 | 50m | 0.089 | 0.707 |
| building_coverage_ratio | 0.090 | 0.045 | -0.017 | 0.020 | 50m | 0.089 | 0.707 |
| landuse_industrial_m2 | -0.356 | -0.351 | -0.335 | -0.329 | 50m | 0.356 | 0.123 |
| landuse_industrial_ratio | -0.356 | -0.351 | -0.335 | -0.329 | 50m | 0.356 | 0.123 |
| landuse_residential_m2 | 0.282 | 0.319 | 0.277 | 0.294 | 100m | 0.319 | 0.171 |
| landuse_residential_ratio | 0.282 | 0.319 | 0.277 | 0.294 | 100m | 0.319 | 0.171 |
| landuse_commercial_m2 | -0.098 | -0.073 | -0.147 | -0.230 | 500m | 0.230 | 0.330 |
| landuse_commercial_ratio | -0.098 | -0.073 | -0.147 | -0.230 | 500m | 0.230 | 0.330 |
| landuse_green_m2 | 0.514 | 0.722 | 0.533 | 0.407 | 100m | 0.722 | 0.000 |
| landuse_green_ratio | 0.514 | 0.722 | 0.533 | 0.407 | 100m | 0.722 | 0.000 |
| dist_industrial_m | 0.553 | 0.553 | 0.553 | 0.553 | 50m | 0.553 | 0.011 |
| intersections_count | -0.030 | 0.148 | 0.262 | 0.299 | 500m | 0.299 | 0.200 |
| dist_centre_m | 0.104 | 0.104 | 0.104 | 0.104 | 50m | 0.104 | 0.663 |

## Paso 2 — Filtro p-value univariante

Candidatas iniciales (tras selección de escala): **21**

### Retenidas p < 0.10 (6 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `road_length_total_m_500m` | 0.4156 | 0.0684 |
| `road_length_residential_m_500m` | 0.5139 | 0.0204 |
| `road_density_m_per_m2_500m` | 0.4156 | 0.0684 |
| `landuse_green_m2_100m` | 0.7216 | 0.0003 |
| `landuse_green_ratio_100m` | 0.7216 | 0.0003 |
| `dist_industrial_m_50m` | 0.5533 | 0.0114 |

### Zona gris p ∈ [0.10, 0.15) — añadidas solo en escenario relajado (2 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `landuse_industrial_m2_50m` | 0.3559 | 0.1235 |
| `landuse_industrial_ratio_50m` | 0.3559 | 0.1235 |

### Eliminadas p ≥ 0.15 (13 variables)

| Variable (mejor buffer) | |r| | p-value | Razón |
|---|---|---|---|
| `aadf_total_sum_500m` | 0.2430 | 0.3019 | p ≥ 0.15 |
| `aadf_total_mean_250m` | 0.3321 | 0.1525 | p ≥ 0.15 |
| `aadf_total_max_50m` | 0.1814 | 0.4440 | p ≥ 0.15 |
| `road_length_primary_m_500m` | 0.3221 | 0.1660 | p ≥ 0.15 |
| `road_length_secondary_m_250m` | 0.1987 | 0.4010 | p ≥ 0.15 |
| `building_area_m2_50m` | 0.0895 | 0.7074 | p ≥ 0.15 |
| `building_coverage_ratio_50m` | 0.0895 | 0.7074 | p ≥ 0.15 |
| `landuse_residential_m2_100m` | 0.3189 | 0.1705 | p ≥ 0.15 |
| `landuse_residential_ratio_100m` | 0.3189 | 0.1705 | p ≥ 0.15 |
| `landuse_commercial_m2_500m` | 0.2299 | 0.3295 | p ≥ 0.15 |
| `landuse_commercial_ratio_500m` | 0.2299 | 0.3295 | p ≥ 0.15 |
| `intersections_count_500m` | 0.2992 | 0.2000 | p ≥ 0.15 |
| `dist_centre_m_50m` | 0.1040 | 0.6626 | p ≥ 0.15 |

## Paso 3 — Filtro VIF (umbral = 5.0)

### Escenario p < 0.10

Variables pre-VIF: **6** → Variables finales: **3**

**Eliminaciones por VIF:**

| Variable eliminada | VIF |
|---|---|
| `road_length_total_m_500m` | inf |
| `landuse_green_m2_100m` | inf |
| `road_density_m_per_m2_500m` | 17.17 |

**Variables finales y sus VIF:**

| Variable | VIF | |r| con target | p-value |
|---|---|---|---|
| `road_length_residential_m_500m` | 1.808 | 0.5139 | 0.0204 |
| `landuse_green_ratio_100m` | 1.528 | 0.7216 | 0.0003 |
| `dist_industrial_m_50m` | 2.186 | 0.5533 | 0.0114 |

### Escenario p < 0.15

Variables pre-VIF: **8** → Variables finales: **4**

**Eliminaciones por VIF:**

| Variable eliminada | VIF |
|---|---|
| `road_length_total_m_500m` | inf |
| `landuse_industrial_m2_50m` | inf |
| `landuse_green_m2_100m` | inf |
| `road_density_m_per_m2_500m` | 20.01 |

**Variables finales y sus VIF:**

| Variable | VIF | |r| con target | p-value |
|---|---|---|---|
| `road_length_residential_m_500m` | 1.861 | 0.5139 | 0.0204 |
| `landuse_industrial_ratio_50m` | 1.032 | 0.3559 | 0.1235 |
| `landuse_green_ratio_100m` | 1.530 | 0.7216 | 0.0003 |
| `dist_industrial_m_50m` | 2.217 | 0.5533 | 0.0114 |

---

# Análisis transversal

## ¿Variables con |r| > 0.5 eliminadas por VIF?

**PM2.5** — eliminadas por VIF con |r| ≥ 0.5:

| Variable | |r| | p-value | Motivo |
|---|---|---|---|
| `landuse_green_m2_100m` | 0.7314 | 0.0002 | Multicolinealidad (VIF > 5) |

**PM10** — eliminadas por VIF con |r| ≥ 0.5:

| Variable | |r| | p-value | Motivo |
|---|---|---|---|
| `landuse_green_m2_100m` | 0.7216 | 0.0003 | Multicolinealidad (VIF > 5) |

## ¿Es 0.10 demasiado restrictivo para n=20?

Con n=20 observaciones, la potencia estadística es baja. Un test t bilateral al nivel α=0.10 para correlación requiere |r| ≥ 0.38 para alcanzar p<0.10 (aproximación: t = r·√(n-2)/√(1-r²), rechazo si |t| > t₀.₀₅,₁₈ ≈ 1.73). El umbral p<0.10 ya supone una concesión respecto al estándar α=0.05.

**Recomendación:** Mantener p<0.10 como umbral primario. Usar p<0.15 únicamente como escenario de sensibilidad y reportar ambos resultados. Si el número de variables finales p<0.10 cae por debajo de 2, activar el escenario relajado.

## Resumen ejecutivo

| Target | Escenario | Variables pre-VIF | Variables finales |
|---|---|---|---|
| PM2.5 | p<0.10 | 8 | 4 (`road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |
| PM2.5 | p<0.15 | 9 | 4 (`road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |
| PM10 | p<0.10 | 6 | 3 (`road_length_residential_m_500m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |
| PM10 | p<0.15 | 8 | 4 (`road_length_residential_m_500m`, `landuse_industrial_ratio_50m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |

---
_Generado automáticamente por `src/analysis/feature_selection_report.py`_