---
name: Project State — LUR Feature Engineering
description: Pipeline state covering AADF integration and multi-scale spatial join feature engineering
type: project
---

## AADF Data Source
- File: `data/raw/aadf_liverpool.csv` — DfT national dataset, LA code 161 (Liverpool)
- 4965 rows total (multi-year time series), 407 unique count points
- Years: 2000–2024. Most recent year per point used (deduplicated in `prepare_aadf`)
- Column for traffic volume: `all_motor_vehicles`
- Coordinates available: `easting`/`northing` (EPSG:27700) AND `latitude`/`longitude`
- 2024 data: 188 points (160 Estimated, 28 Counted)

## Extraction Script
- `src/analysis/integrate_aadf.py` — Fase 3 integration
- Reads `data/raw/streets_liverpool.gpkg` (8450 streets, EPSG:27700)
- Spatial join max_distance: **100 m** (corrected from 500 m on 2026-04-10)
- Output: `data/interim/streets_with_traffic.gpkg`

## Coverage Reality (post-100m fix)
- Direct match (<100 m): **1675/8450 = 19.8%** of streets
- Imputed via hierarchy: **6775/8450 = 80.2%**
- The 85% direct-coverage criterion is NOT achievable with 100m threshold + 407 count points for 8450 streets — this is a dataset density limitation, not a script bug.
- Fallback logic: measured → highway-type median → global median

## Coverage by Highway Category (with 100m threshold)
| highway_norm | medido | imputado | total | pct_medido |
|---|---|---|---|---|
| motorway | 6 | 3 | 9 | 66.7% |
| primary | 294 | 192 | 486 | 60.5% |
| secondary | 89 | 248 | 337 | 26.4% |
| residential | 1286 | 6332 | 7618 | 16.9% |

## Validation Results (last run 2026-04-10)
- 0 NaN in `aadf_imputed` — PASS
- 0 negative values — PASS
- Monotonicity: motorway(11993) > primary(8779) > residential(6200) — PASS
- Script executes without errors — PASS

## Feature Engineering — Task 1 (Spatial Join Multi-escala)
- Script: `src/analysis/feature_engineering.py`
- Output: `data/interim/lur_features.csv`
- Shape: 80 rows × 26 columns (20 sensors × 4 buffers: 50/100/250/500m), 0 NaN
- CRS: EPSG:27700 throughout (sensors, streets, buildings, landuse)
- New variables added 2026-04-12:
  - `intersections_count`: unique road nodes (endpoints of clipped segments) within buffer
  - `dist_centre_m`: Euclidean distance to Liverpool centre (335000, 390000) in EPSG:27700
- Zero road rows at 50m buffer: 8 sensors — valid (sensors >50m from any road segment)
- `dist_industrial_m` zeros (16 rows): valid — sensor inside industrial polygon, distance=0
- Python executable: `/c/Users/Ivan/AppData/Local/Python/bin/python3.exe` (Python 3.14.3)

## Known Issues / Design Notes
- `secondary` median (9645) > `primary` median (8779) — this is real data, not a bug.
  Liverpool's secondary roads near the port carry more traffic than some primary routes.
- With 100m join, most residential streets rely on imputation — this is expected and correct.
  **Why:** 100m filter was corrected from 500m; the original 500m was geometrically assigning
  traffic from different roads, inflating direct-match coverage to a misleading 90.7%.
