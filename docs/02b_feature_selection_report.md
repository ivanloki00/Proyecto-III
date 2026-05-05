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
| aadf_total_sum | -0.163 | -0.085 | 0.085 | 0.285 | 500m | 0.284 | 0.224 |
| aadf_total_mean | -0.268 | 0.016 | -0.278 | -0.007 | 250m | 0.278 | 0.235 |
| aadf_total_max | -0.215 | 0.111 | -0.061 | -0.099 | 50m | 0.215 | 0.362 |
| road_length_total_m | -0.141 | 0.051 | 0.286 | 0.471 | 500m | 0.471 | 0.036 |
| road_length_motorway_m | — | — | — | — | N/A | — | — |
| road_length_primary_m | -0.082 | -0.056 | -0.205 | -0.306 | 500m | 0.306 | 0.190 |
| road_length_secondary_m | -0.098 | -0.084 | -0.126 | -0.133 | 500m | 0.133 | 0.577 |
| road_length_residential_m | -0.031 | 0.137 | 0.387 | 0.555 | 500m | 0.555 | 0.011 |
| road_density_m_per_m2 | -0.141 | 0.051 | 0.286 | 0.471 | 500m | 0.471 | 0.036 |
| building_area_m2 | 0.113 | 0.100 | 0.059 | 0.098 | 50m | 0.113 | 0.636 |
| building_coverage_ratio | 0.113 | 0.100 | 0.059 | 0.098 | 50m | 0.113 | 0.636 |
| landuse_industrial_m2 | -0.369 | -0.392 | -0.397 | -0.391 | 250m | 0.397 | 0.084 |
| landuse_industrial_ratio | -0.369 | -0.392 | -0.397 | -0.391 | 250m | 0.397 | 0.084 |
| landuse_residential_m2 | 0.253 | 0.298 | 0.294 | 0.322 | 500m | 0.322 | 0.167 |
| landuse_residential_ratio | 0.253 | 0.298 | 0.294 | 0.322 | 500m | 0.322 | 0.167 |
| landuse_commercial_m2 | -0.075 | -0.073 | -0.153 | -0.215 | 500m | 0.215 | 0.363 |
| landuse_commercial_ratio | -0.075 | -0.073 | -0.153 | -0.215 | 500m | 0.215 | 0.363 |
| landuse_green_m2 | 0.518 | 0.737 | 0.538 | 0.436 | 100m | 0.737 | 0.000 |
| landuse_green_ratio | 0.518 | 0.737 | 0.538 | 0.436 | 100m | 0.737 | 0.000 |
| dist_industrial_m | 0.558 | 0.558 | 0.558 | 0.558 | 50m | 0.558 | 0.011 |
| intersections_count | -0.085 | 0.099 | 0.294 | 0.340 | 500m | 0.340 | 0.143 |
| dist_centre_m | 0.051 | 0.051 | 0.051 | 0.051 | 50m | 0.051 | 0.832 |

## Paso 2 — Filtro p-value univariante

Candidatas iniciales (tras selección de escala): **21**

### Retenidas p < 0.10 (8 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `road_length_total_m_500m` | 0.4712 | 0.0360 |
| `road_length_residential_m_500m` | 0.5550 | 0.0111 |
| `road_density_m_per_m2_500m` | 0.4712 | 0.0360 |
| `landuse_industrial_m2_250m` | 0.3965 | 0.0835 |
| `landuse_industrial_ratio_250m` | 0.3965 | 0.0835 |
| `landuse_green_m2_100m` | 0.7366 | 0.0002 |
| `landuse_green_ratio_100m` | 0.7366 | 0.0002 |
| `dist_industrial_m_50m` | 0.5578 | 0.0106 |

### Zona gris p ∈ [0.10, 0.15) — añadidas solo en escenario relajado (1 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `intersections_count_500m` | 0.3397 | 0.1428 |

### Eliminadas p ≥ 0.15 (12 variables)

| Variable (mejor buffer) | |r| | p-value | Razón |
|---|---|---|---|
| `aadf_total_sum_500m` | 0.2845 | 0.2241 | p ≥ 0.15 |
| `aadf_total_mean_250m` | 0.2779 | 0.2355 | p ≥ 0.15 |
| `aadf_total_max_50m` | 0.2153 | 0.3621 | p ≥ 0.15 |
| `road_length_primary_m_500m` | 0.3057 | 0.1899 | p ≥ 0.15 |
| `road_length_secondary_m_500m` | 0.1328 | 0.5767 | p ≥ 0.15 |
| `building_area_m2_50m` | 0.1126 | 0.6364 | p ≥ 0.15 |
| `building_coverage_ratio_50m` | 0.1126 | 0.6364 | p ≥ 0.15 |
| `landuse_residential_m2_500m` | 0.3216 | 0.1668 | p ≥ 0.15 |
| `landuse_residential_ratio_500m` | 0.3216 | 0.1668 | p ≥ 0.15 |
| `landuse_commercial_m2_500m` | 0.2148 | 0.3632 | p ≥ 0.15 |
| `landuse_commercial_ratio_500m` | 0.2148 | 0.3632 | p ≥ 0.15 |
| `dist_centre_m_50m` | 0.0507 | 0.8319 | p ≥ 0.15 |

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
| `road_length_residential_m_500m` | 1.929 | 0.5550 | 0.0111 |
| `landuse_industrial_ratio_250m` | 1.071 | 0.3965 | 0.0835 |
| `landuse_green_ratio_100m` | 1.530 | 0.7366 | 0.0002 |
| `dist_industrial_m_50m` | 2.241 | 0.5578 | 0.0106 |

### Escenario p < 0.15

Variables pre-VIF: **9** → Variables finales: **4**

**Eliminaciones por VIF:**

| Variable eliminada | VIF |
|---|---|
| `road_length_total_m_500m` | inf |
| `landuse_industrial_m2_250m` | inf |
| `landuse_green_m2_100m` | inf |
| `road_density_m_per_m2_500m` | 66.33 |
| `intersections_count_500m` | 13.31 |

**Variables finales y sus VIF:**

| Variable | VIF | |r| con target | p-value |
|---|---|---|---|
| `road_length_residential_m_500m` | 1.929 | 0.5550 | 0.0111 |
| `landuse_industrial_ratio_250m` | 1.071 | 0.3965 | 0.0835 |
| `landuse_green_ratio_100m` | 1.530 | 0.7366 | 0.0002 |
| `dist_industrial_m_50m` | 2.241 | 0.5578 | 0.0106 |

---

# Target: PM10

## Paso 1 — Correlaciones (Pearson r) por variable × buffer

| Variable | 50m | 100m | 250m | 500m | Best buf | Best |r| | p-value |
|---|---|---|---|---|---|---|---|
| aadf_total_sum | -0.154 | -0.070 | -0.006 | 0.238 | 500m | 0.238 | 0.313 |
| aadf_total_mean | -0.237 | 0.001 | -0.343 | 0.013 | 250m | 0.343 | 0.139 |
| aadf_total_max | -0.185 | 0.085 | -0.126 | -0.075 | 50m | 0.185 | 0.435 |
| road_length_total_m | -0.099 | 0.104 | 0.232 | 0.412 | 500m | 0.412 | 0.071 |
| road_length_motorway_m | — | — | — | — | N/A | — | — |
| road_length_primary_m | -0.061 | -0.030 | -0.253 | -0.327 | 500m | 0.327 | 0.160 |
| road_length_secondary_m | -0.109 | -0.098 | -0.197 | -0.188 | 250m | 0.198 | 0.404 |
| road_length_residential_m | 0.027 | 0.189 | 0.368 | 0.512 | 500m | 0.512 | 0.021 |
| road_density_m_per_m2 | -0.099 | 0.104 | 0.232 | 0.412 | 500m | 0.412 | 0.071 |
| building_area_m2 | 0.088 | 0.040 | -0.025 | 0.015 | 50m | 0.088 | 0.711 |
| building_coverage_ratio | 0.088 | 0.040 | -0.025 | 0.015 | 50m | 0.088 | 0.711 |
| landuse_industrial_m2 | -0.358 | -0.353 | -0.338 | -0.331 | 50m | 0.358 | 0.121 |
| landuse_industrial_ratio | -0.358 | -0.353 | -0.338 | -0.331 | 50m | 0.358 | 0.121 |
| landuse_residential_m2 | 0.285 | 0.321 | 0.277 | 0.293 | 100m | 0.321 | 0.168 |
| landuse_residential_ratio | 0.285 | 0.321 | 0.277 | 0.293 | 100m | 0.321 | 0.168 |
| landuse_commercial_m2 | -0.096 | -0.063 | -0.137 | -0.227 | 500m | 0.227 | 0.337 |
| landuse_commercial_ratio | -0.096 | -0.063 | -0.137 | -0.227 | 500m | 0.227 | 0.337 |
| landuse_green_m2 | 0.512 | 0.719 | 0.531 | 0.406 | 100m | 0.719 | 0.000 |
| landuse_green_ratio | 0.512 | 0.719 | 0.531 | 0.406 | 100m | 0.719 | 0.000 |
| dist_industrial_m | 0.549 | 0.549 | 0.549 | 0.549 | 50m | 0.549 | 0.012 |
| intersections_count | -0.029 | 0.151 | 0.262 | 0.298 | 500m | 0.298 | 0.203 |
| dist_centre_m | 0.121 | 0.121 | 0.121 | 0.121 | 50m | 0.121 | 0.612 |

## Paso 2 — Filtro p-value univariante

Candidatas iniciales (tras selección de escala): **21**

### Retenidas p < 0.10 (6 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `road_length_total_m_500m` | 0.4122 | 0.0709 |
| `road_length_residential_m_500m` | 0.5119 | 0.0210 |
| `road_density_m_per_m2_500m` | 0.4122 | 0.0709 |
| `landuse_green_m2_100m` | 0.7190 | 0.0004 |
| `landuse_green_ratio_100m` | 0.7190 | 0.0004 |
| `dist_industrial_m_50m` | 0.5487 | 0.0122 |

### Zona gris p ∈ [0.10, 0.15) — añadidas solo en escenario relajado (3 variables)

| Variable (mejor buffer) | |r| | p-value |
|---|---|---|
| `aadf_total_mean_250m` | 0.3428 | 0.1389 |
| `landuse_industrial_m2_50m` | 0.3584 | 0.1207 |
| `landuse_industrial_ratio_50m` | 0.3584 | 0.1207 |

### Eliminadas p ≥ 0.15 (12 variables)

| Variable (mejor buffer) | |r| | p-value | Razón |
|---|---|---|---|
| `aadf_total_sum_500m` | 0.2377 | 0.3129 | p ≥ 0.15 |
| `aadf_total_max_50m` | 0.1850 | 0.4348 | p ≥ 0.15 |
| `road_length_primary_m_500m` | 0.3267 | 0.1597 | p ≥ 0.15 |
| `road_length_secondary_m_250m` | 0.1975 | 0.4039 | p ≥ 0.15 |
| `building_area_m2_50m` | 0.0884 | 0.7110 | p ≥ 0.15 |
| `building_coverage_ratio_50m` | 0.0884 | 0.7110 | p ≥ 0.15 |
| `landuse_residential_m2_100m` | 0.3207 | 0.1680 | p ≥ 0.15 |
| `landuse_residential_ratio_100m` | 0.3207 | 0.1680 | p ≥ 0.15 |
| `landuse_commercial_m2_500m` | 0.2265 | 0.3369 | p ≥ 0.15 |
| `landuse_commercial_ratio_500m` | 0.2265 | 0.3369 | p ≥ 0.15 |
| `intersections_count_500m` | 0.2976 | 0.2026 | p ≥ 0.15 |
| `dist_centre_m_50m` | 0.1209 | 0.6117 | p ≥ 0.15 |

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
| `road_length_residential_m_500m` | 1.808 | 0.5119 | 0.0210 |
| `landuse_green_ratio_100m` | 1.528 | 0.7190 | 0.0004 |
| `dist_industrial_m_50m` | 2.185 | 0.5487 | 0.0122 |

### Escenario p < 0.15

Variables pre-VIF: **9** → Variables finales: **5**

**Eliminaciones por VIF:**

| Variable eliminada | VIF |
|---|---|
| `road_length_total_m_500m` | inf |
| `landuse_industrial_m2_50m` | inf |
| `landuse_green_m2_100m` | inf |
| `road_density_m_per_m2_500m` | 38.09 |

**Variables finales y sus VIF:**

| Variable | VIF | |r| con target | p-value |
|---|---|---|---|
| `aadf_total_mean_250m` | 3.511 | 0.3428 | 0.1389 |
| `road_length_residential_m_500m` | 2.831 | 0.5119 | 0.0210 |
| `landuse_industrial_ratio_50m` | 1.777 | 0.3584 | 0.1207 |
| `landuse_green_ratio_100m` | 1.554 | 0.7190 | 0.0004 |
| `dist_industrial_m_50m` | 2.272 | 0.5487 | 0.0122 |

---

# Análisis transversal

## ¿Variables con |r| > 0.5 eliminadas por VIF?

**PM2.5** — eliminadas por VIF con |r| ≥ 0.5:

| Variable | |r| | p-value | Motivo |
|---|---|---|---|
| `landuse_green_m2_100m` | 0.7366 | 0.0002 | Multicolinealidad (VIF > 5) |

**PM10** — eliminadas por VIF con |r| ≥ 0.5:

| Variable | |r| | p-value | Motivo |
|---|---|---|---|
| `landuse_green_m2_100m` | 0.7190 | 0.0004 | Multicolinealidad (VIF > 5) |

## ¿Es 0.10 demasiado restrictivo para n=20?

Con n=20 observaciones, la potencia estadística es baja. Un test t bilateral al nivel α=0.10 para correlación requiere |r| ≥ 0.38 para alcanzar p<0.10 (aproximación: t = r·√(n-2)/√(1-r²), rechazo si |t| > t₀.₀₅,₁₈ ≈ 1.73). El umbral p<0.10 ya supone una concesión respecto al estándar α=0.05.

**Recomendación:** Mantener p<0.10 como umbral primario. Usar p<0.15 únicamente como escenario de sensibilidad y reportar ambos resultados. Si el número de variables finales p<0.10 cae por debajo de 2, activar el escenario relajado.

## Resumen ejecutivo

| Target | Escenario | Variables pre-VIF | Variables finales |
|---|---|---|---|
| PM2.5 | p<0.10 | 8 | 4 (`road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |
| PM2.5 | p<0.15 | 9 | 4 (`road_length_residential_m_500m`, `landuse_industrial_ratio_250m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |
| PM10 | p<0.10 | 6 | 3 (`road_length_residential_m_500m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |
| PM10 | p<0.15 | 9 | 5 (`aadf_total_mean_250m`, `road_length_residential_m_500m`, `landuse_industrial_ratio_50m`, `landuse_green_ratio_100m`, `dist_industrial_m_50m`) |

---
_Generado automáticamente por `src/analysis/feature_selection_report.py`_