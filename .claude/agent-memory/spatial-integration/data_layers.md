---
name: Data Layers and File Paths
description: Rutas, CRS y caracteristicas de las capas de datos espaciales y tabulares del proyecto PROYIII
type: reference
---

**Why:** Referencia rápida para no tener que redescubrir rutas y CRS en cada sesión.

**How to apply:** Usar estas rutas al leer o exportar datos. Verificar existencia antes de asumir que están actualizadas.

## Feature Matrix (entrada para modelos)
- Path: `data/interim/lur_features.csv`
- Shape: 80 filas x 26 columnas (20 sensores x 4 buffers)
- Columnas: sensor_id, buffer_m, [20 variables OSM/AADF], PM2.5, PM10
- NaN: 0
- Nota: road_length_motorway_m = 0 en todos los registros (sin autopistas en area sensores)

## Sensores Snapped
- Path: `data/interim/sensores_snapped.gpkg`
- n: 20 sensores
- Uso: coordenadas para Moran's I

## OSM Features Raw
- `data/raw/streets_liverpool.gpkg`
- `data/raw/landuse_liverpool.gpkg`
- `data/raw/buildings_liverpool.gpkg`

## Outputs Modelo
- `outputs/lur_model_PM25.pkl` — modelo entrenado PM2.5
- `outputs/lur_model_PM10.pkl` — modelo entrenado PM10
- `outputs/feature_selection_report.md` — informe Task 3 (generado 2026-04-10)
- `outputs/diagnostics_PM25.png`, `outputs/diagnostics_PM10.png`

## Python executable en este entorno
- Usar `py` (no `python` ni `python3`) — apunta a Python 3.14 en Windows
- Path: `C:\Users\Ivan\AppData\Local\Python\pythoncore-3.14-64\python.exe`
