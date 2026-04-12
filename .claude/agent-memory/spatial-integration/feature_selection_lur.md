---
name: Feature Selection LUR Results
description: Variables finales seleccionadas para modelos LUR PM2.5 y PM10 tras buffer selection, filtro p-value y filtro VIF. Completado 2026-04-10.
type: project
---

Task 3 completada. Script: `src/analysis/feature_selection_report.py`. Informe: `outputs/feature_selection_report.md`.

**Why:** n=20 sensores en Liverpool; selección de variables crítica para evitar sobreajuste en LUR.

**How to apply:** Usar estas variables como punto de partida para entrenar los modelos en Task 4. No re-ejecutar la selección sin causa justificada.

## Configuración usada
- Buffers evaluados: 50, 100, 250, 500 m
- p-value threshold primario: 0.10 | relajado: 0.15
- VIF threshold: 5.0
- Criterio buffer: max |Pearson r| con target

## Variables finales — escenario primario p<0.10 + VIF<=5

### PM2.5 (4 variables)
| Variable | Buffer | |r| | p-value | VIF |
|---|---|---|---|---|
| road_length_residential_m | 500m | 0.557 | 0.011 | 1.93 |
| landuse_industrial_ratio | 250m | 0.392 | 0.087 | 1.07 |
| landuse_green_ratio | 100m | 0.731 | 0.0002 | 1.53 |
| dist_industrial_m | 50m | 0.550 | 0.012 | 2.24 |

### PM10 (3 variables — escenario p<0.10)
| Variable | Buffer | |r| | p-value | VIF |
|---|---|---|---|---|
| road_length_residential_m | 500m | 0.514 | 0.020 | 1.81 |
| landuse_green_ratio | 100m | 0.722 | 0.0003 | 1.53 |
| dist_industrial_m | 50m | 0.553 | 0.011 | 2.19 |

### PM10 (4 variables — escenario p<0.15, recomendado)
Añade: landuse_industrial_ratio @ 50m (|r|=0.356, p=0.123, VIF=1.03)

## Variables eliminadas por VIF (multicolinealidad severa)
- road_length_total_m_500m: VIF=inf (colineal con road_length_residential + road_density)
- landuse_green_m2_100m: VIF=inf (colineal perfecta con landuse_green_ratio_100m — misma variable en m2 vs ratio)
- road_density_m_per_m2_500m: VIF=17-20 (derivada directa de road_length_total)
- landuse_industrial_m2_250m: VIF=inf (colineal con landuse_industrial_ratio)

## Variable notable perdida por VIF
landuse_green_m2_100m tiene |r|=0.731 (PM2.5) y 0.722 (PM10) pero VIF=inf.
Causa: es perfectamente colineal con landuse_green_ratio a escala 100m.
Solucion: retener landuse_green_ratio_100m (VIF=1.53) que captura la misma señal normalizada.

## Recomendacion sobre p-value threshold
- p<0.10 es adecuado para n=20; requiere |r|>=~0.38
- PM10 con p<0.10 solo retiene 3 variables (umbral minimo cumplido)
- Usar p<0.15 para PM10 para añadir landuse_industrial_ratio y tener modelo mas robusto
- road_length_motorway_m: std=0 en todos los buffers (no hay autopistas en el area de los sensores) — excluida automáticamente
