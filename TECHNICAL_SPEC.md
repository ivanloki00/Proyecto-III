# AirTrace — Technical Specification (MVP)

**Producto:** AirTrace — Liverpool Air Quality Intelligence Platform  
**Versión:** 0.1.0-MVP  
**Fecha:** 2026-04-17  
**Autor:** Cesar Vizoso  
**Estado:** Especificación lista para implementación

---

## 1. Contexto y Base Técnica

El pipeline científico del Milestone 1 produjo el activo central del producto:

| Artefacto | Ruta en repo | Descripción |
|---|---|---|
| `liverpool_pollution_map.geojson` | `outputs/maps/` | 8.450 tramos viarios con `pm25_pred` y `pm10_pred` |
| `lur_model_PM25.pkl` | `outputs/models/` | SVR, R²=0.6020 LOOCV (sesión mejora Abril 2026) |
| `lur_model_PM10.pkl` | `outputs/models/` | SVR, R²=0.5809 LOOCV (sesión mejora Abril 2026) |
| Pipeline 9 scripts | `src/` | Reproducible: datos → features → modelos → mapa |

### Métricas del modelo (referencia)

| Métrica | PM2.5 | PM10 |
|---|---|---|
| R² LOOCV | **0.6020** | **0.5809** |
| RMSE LOOCV (µg/m³) | **2.232** | **3.512** |
| MAE (µg/m³) | N/D | N/D |
| Outliers (>2×RMSE) | 0 | 0 |
| Sensores base | 20 (LISP excluido: sin PM2.5) | 21 |
| Tramos predichos | 8.450 | 8.450 |

> **Nota:** El modelo Ridge original (baseline Task 4) tenía R²=0.5858/PM2.5 y R²=0.5034/PM10.
> La sesión de mejora de Abril 2026 (doc `08_lur_improvement_session.md`) añadió spatial lag,
> estacionalidad cíclica, buffer 1000m y sensor LISP, mejorando a SVR como modelo ganador.

### Variables predictoras del modelo

**PM2.5** (2 LUR + 5 controles): `landuse_green_m2_100m`, `road_length_residential_m_1000m` + `air_temperature_mean`, `wind_speed_mean`, `rain_days`, `mes_sin`, `mes_cos`

**PM10**: variables seleccionadas por LOOCV SVR — ver `docs/08_lur_improvement_session.md` para detalle completo

---

## 2. Propuesta de Valor del MVP

> **"Cualquier dirección de Liverpool. Su nivel de contaminación PM2.5/PM10. En menos de 200 ms."**

El MVP no requiere más ciencia. Requiere envolver el GeoJSON existente en una interfaz comercializable con tres componentes:

1. **API REST** — endpoint de consulta por coordenada o dirección postal
2. **Dashboard web** — mapa interactivo de la red viaria coloreado por contaminación
3. **Datos en Supabase PostGIS** — backend espacial para consultas eficientes

---

## 3. Arquitectura del Sistema

```
┌────────────────────────────────────────────────────────────────────┐
│                        VERCEL (Edge Network)                       │
│                                                                    │
│  ┌─────────────────────┐     ┌───────────────────────────────┐    │
│  │   Frontend (Next.js) │     │  API Routes (Python Serverless│    │
│  │                     │     │  via @vercel/python)           │    │
│  │  /app               │────▶│                               │    │
│  │  └─ page.tsx        │     │  /api/predict    GET          │    │
│  │  /components        │     │  /api/streets    GET          │    │
│  │     └─ AirMap.tsx   │     │  /api/health     GET          │    │
│  └─────────────────────┘     └──────────────┬────────────────┘    │
│                                             │                      │
└─────────────────────────────────────────────┼──────────────────────┘
                                              │ SQL (PostGIS)
                                              ▼
                              ┌───────────────────────────┐
                              │     Supabase (PostgreSQL)  │
                              │                           │
                              │  tabla: streets           │
                              │  tipo: geometry (LINESTRING│
                              │  cols: pm25_pred, pm10_pred│
                              │        highway, name, ...  │
                              │                           │
                              │  índice: GIST(geometry)   │
                              └───────────────────────────┘
```

### Flujo de una consulta típica

```
Usuario introduce dirección  →  Geocodificación (Nominatim/Mapbox)
→  GET /api/predict?lat=53.4&lng=-2.98&radius=200
→  Vercel Serverless Function  →  Supabase PostGIS ST_DWithin query
→  JSON respuesta  →  Renderizado en mapa + score A–F
```

---

## 4. Estructura de Directorios del Proyecto MVP

```
Proyecto-III/
├── TECHNICAL_SPEC.md          ← este documento
├── CLAUDE.md
├── vercel.json                ← configuración despliegue
├── requirements.txt           ← deps Python para Vercel
│
├── api/                       ← Vercel Python Serverless Functions
│   ├── predict.py             ← GET /api/predict
│   ├── streets.py             ← GET /api/streets (bbox)
│   └── health.py              ← GET /api/health
│
├── app/                       ← Next.js frontend (App Router)
│   ├── layout.tsx
│   ├── page.tsx               ← landing + mapa principal
│   └── globals.css
│
├── components/
│   ├── AirMap.tsx             ← mapa Mapbox GL JS / Deck.gl
│   ├── SearchBar.tsx          ← input dirección + geocoding
│   └── PollutionScore.tsx     ← widget score A–F
│
├── lib/
│   ├── supabase.ts            ← cliente Supabase (TypeScript)
│   └── scoring.ts             ← lógica escala A–F
│
├── scripts/
│   └── load_geojson_to_supabase.py  ← script one-time de carga
│
├── src/                       ← pipeline científico existente (sin cambios)
├── data/
├── outputs/
└── docs/
```

---

## 5. API Specification

### Base URL

```
Production:  https://airtrace.vercel.app/api
Staging:     https://airtrace-git-main-<user>.vercel.app/api
Local:       http://localhost:3000/api
```

---

### `GET /api/predict`

Devuelve las predicciones de contaminación para los tramos viarios dentro de un radio dado.

**Parámetros**

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `lat` | float | Sí | Latitud WGS84 (ej: 53.4084) |
| `lng` | float | Sí | Longitud WGS84 (ej: -2.9916) |
| `radius` | int | No | Radio en metros, default=200, max=1000 |
| `format` | string | No | `json` (default) o `geojson` |

**Ejemplo de request**

```
GET /api/predict?lat=53.4084&lng=-2.9916&radius=200
```

**Respuesta 200 (format=json)**

```json
{
  "query": {
    "lat": 53.4084,
    "lng": -2.9916,
    "radius_m": 200,
    "timestamp_utc": "2026-04-17T10:30:00Z"
  },
  "summary": {
    "pm25_mean": 12.4,
    "pm25_max": 15.2,
    "pm10_mean": 24.1,
    "pm10_max": 30.8,
    "score": "C",
    "streets_found": 7
  },
  "streets": [
    {
      "id": "way/123456",
      "name": "Mather Avenue",
      "highway": "secondary",
      "pm25_pred": 12.27,
      "pm10_pred": 23.81,
      "distance_m": 43.2
    }
  ]
}
```

**Respuesta 200 (format=geojson)** — GeoJSON FeatureCollection estándar, compatible con Mapbox/Deck.gl.

**Errores**

| Código | Motivo |
|---|---|
| 400 | Parámetros `lat`/`lng` ausentes o fuera de rango |
| 422 | `radius` > 1000 m |
| 404 | Sin tramos en el radio especificado |
| 500 | Error interno / BD no disponible |

---

### `GET /api/streets`

Devuelve todos los tramos dentro de un bounding box. Usado por el mapa para carga progresiva.

**Parámetros**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `minlng` | float | Longitud mínima del bbox |
| `minlat` | float | Latitud mínima del bbox |
| `maxlng` | float | Longitud máxima del bbox |
| `maxlat` | float | Latitud máxima del bbox |
| `limit` | int | Máx. tramos (default=500, max=2000) |

**Respuesta** — GeoJSON FeatureCollection con propiedades `pm25_pred`, `pm10_pred`, `score`.

---

### `GET /api/health`

```json
{
  "status": "ok",
  "db_connected": true,
  "streets_count": 8450,
  "model_version": "svr-v2-20260414",
  "timestamp_utc": "2026-04-17T10:30:00Z"
}
```

---

## 6. Esquema de Base de Datos (Supabase PostGIS)

### Tabla `streets`

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE streets (
    id            BIGSERIAL PRIMARY KEY,
    osm_id        TEXT,
    name          TEXT,
    highway       TEXT,
    -- Predicciones LUR
    pm25_pred     DOUBLE PRECISION NOT NULL,
    pm10_pred     DOUBLE PRECISION NOT NULL,
    pm25_score    CHAR(1) GENERATED ALWAYS AS (
                      CASE
                          WHEN pm25_pred < 5   THEN 'A'
                          WHEN pm25_pred < 10  THEN 'B'
                          WHEN pm25_pred < 15  THEN 'C'
                          WHEN pm25_pred < 20  THEN 'D'
                          WHEN pm25_pred < 25  THEN 'E'
                          ELSE 'F'
                      END
                  ) STORED,
    -- Tráfico
    aadf_imputed  DOUBLE PRECISION,
    aadf_source   TEXT,
    -- Geometría
    geom          GEOMETRY(LINESTRING, 4326) NOT NULL,
    -- Metadatos
    loaded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Índice espacial (crítico para ST_DWithin)
CREATE INDEX idx_streets_geom ON streets USING GIST(geom);

-- Índice para filtros por score
CREATE INDEX idx_streets_pm25_score ON streets(pm25_score);
CREATE INDEX idx_streets_highway ON streets(highway);
```

### Escala de Score (A–F)

| Score | PM2.5 (µg/m³) | Referencia |
|---|---|---|
| A | < 5 | Muy buena calidad |
| B | 5–10 | Buena (objetivo UK 2040) |
| C | 10–15 | Moderada |
| D | 15–20 | Pobre |
| E | 20–25 | Muy pobre |
| F | ≥ 25 | Peligrosa |

> Basado en WHO Air Quality Guidelines (2021): PM2.5 anual ≤ 5 µg/m³.

---

## 7. Script de Carga a Supabase

`scripts/load_geojson_to_supabase.py`

```python
"""
Script one-time: carga liverpool_pollution_map.geojson en Supabase PostGIS.
Ejecutar una sola vez (o cuando haya nuevo GeoJSON del pipeline).

Uso:
    SUPABASE_DB_URL=postgresql://... python scripts/load_geojson_to_supabase.py
"""
from pathlib import Path
import geopandas as gpd
from sqlalchemy import create_engine
import os

GEOJSON_PATH = Path("outputs/maps/liverpool_pollution_map.geojson")

def main():
    db_url = os.environ["SUPABASE_DB_URL"]
    engine = create_engine(db_url)

    gdf = gpd.read_file(GEOJSON_PATH)
    # Seleccionar solo columnas necesarias
    cols = ["name", "highway", "pm25_pred", "pm10_pred",
            "aadf_imputed", "aadf_source", "geometry"]
    gdf = gdf[[c for c in cols if c in gdf.columns]]
    gdf = gdf.set_crs(4326, allow_override=True)

    gdf.to_postgis("streets", engine, if_exists="replace",
                   index=False, chunksize=500)
    print(f"Cargados {len(gdf)} tramos en Supabase.")

if __name__ == "__main__":
    main()
```

---

## 8. Implementación de la API (Vercel Python)

### `api/predict.py`

```python
"""
GET /api/predict — Devuelve predicciones de contaminación por coordenada.
Vercel Python Serverless Function.
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json, os
import psycopg2

DB_URL = os.environ["SUPABASE_DB_URL"]

SCORE_THRESHOLDS = [5, 10, 15, 20, 25]
SCORE_LABELS     = ["A", "B", "C", "D", "E", "F"]

def pm25_to_score(val: float) -> str:
    for threshold, label in zip(SCORE_THRESHOLDS, SCORE_LABELS):
        if val < threshold:
            return label
    return "F"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)

        # Validación
        try:
            lat    = float(params["lat"][0])
            lng    = float(params["lng"][0])
            radius = min(int(params.get("radius", [200])[0]), 1000)
        except (KeyError, ValueError):
            self._respond(400, {"error": "lat and lng are required"})
            return

        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            self._respond(400, {"error": "Coordinates out of range"})
            return

        # Consulta PostGIS
        sql = """
            SELECT name, highway, pm25_pred, pm10_pred,
                   ST_Distance(geom::geography,
                       ST_MakePoint(%s,%s)::geography) AS distance_m
            FROM streets
            WHERE ST_DWithin(
                geom::geography,
                ST_MakePoint(%s, %s)::geography,
                %s
            )
            ORDER BY distance_m
            LIMIT 50;
        """
        try:
            conn   = psycopg2.connect(DB_URL)
            cur    = conn.cursor()
            cur.execute(sql, (lng, lat, lng, lat, radius))
            rows   = cur.fetchall()
            cur.close(); conn.close()
        except Exception as e:
            self._respond(500, {"error": str(e)})
            return

        if not rows:
            self._respond(404, {"error": "No streets found in radius"})
            return

        streets = [
            {
                "name":       r[0],
                "highway":    r[1],
                "pm25_pred":  round(r[2], 2),
                "pm10_pred":  round(r[3], 2),
                "distance_m": round(r[4], 1),
            }
            for r in rows
        ]

        pm25_vals = [s["pm25_pred"] for s in streets]
        body = {
            "query":   {"lat": lat, "lng": lng, "radius_m": radius},
            "summary": {
                "pm25_mean":     round(sum(pm25_vals)/len(pm25_vals), 2),
                "pm25_max":      round(max(pm25_vals), 2),
                "score":         pm25_to_score(sum(pm25_vals)/len(pm25_vals)),
                "streets_found": len(streets),
            },
            "streets": streets,
        }
        self._respond(200, body)

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
```

---

## 9. Configuración de Vercel

### `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/*.py",
      "use": "@vercel/python"
    },
    {
      "src": "app/**",
      "use": "@vercel/next"
    }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/$1.py" },
    { "src": "/(.*)",     "dest": "/app/$1" }
  ],
  "env": {
    "SUPABASE_DB_URL": "@supabase_db_url",
    "NEXT_PUBLIC_MAPBOX_TOKEN": "@mapbox_token"
  }
}
```

### `requirements.txt` (Python API)

```
psycopg2-binary==2.9.9
```

> Las funciones serverless de Vercel tienen un límite de 50 MB por bundle.
> Se usa `psycopg2-binary` (sin numpy/geopandas) porque las predicciones
> **ya están en la BD** — no se necesita cargar los `.pkl` en tiempo de consulta.

### `package.json` (Next.js frontend)

```json
{
  "name": "airtrace",
  "version": "0.1.0",
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "mapbox-gl": "^3.4.0",
    "@supabase/supabase-js": "^2.43.0"
  }
}
```

---

## 10. Estrategia de Repositorio y Control de Archivos

### Decisión: repo único (monorepo)

No se crea un repositorio separado para la app. El repo `Proyecto-III` ya existente sirve como base para el despliegue en Vercel. Vercel solo lee los directorios `api/` y `app/` — el resto del repo (pipeline científico, datos, modelos) es invisible para el proceso de build.

```
Proyecto-III/          ← repo existente, conectado a Vercel
├── api/               ← Vercel despliega esto
├── app/               ← Vercel despliega esto
├── vercel.json        ← Vercel lee esto
├── .vercelignore      ← Vercel ignora todo lo demás
│
├── src/               ╮
├── data/              │  Invisible para Vercel.
├── outputs/           │  Solo se usa en local para el pipeline.
├── notebooks/         │  Los datos van a Supabase, no a Vercel.
└── docs/              ╯
```

### Por qué no hay "migración de datos"

Los archivos de datos no se mueven a ningún sitio. El único paso de transferencia es ejecutar `scripts/load_geojson_to_supabase.py` una sola vez, que lee el GeoJSON local y lo inserta en Supabase. A partir de ese momento:

- **Vercel** sirve el código (API + frontend) — no almacena datos
- **Supabase** almacena los 8.450 tramos con sus predicciones — no hay archivos grandes en el repo desplegado
- **Local** sigue siendo el entorno donde corre el pipeline científico

### Separación de responsabilidades por entorno

| Entorno | Responsabilidad | Qué contiene |
|---|---|---|
| Local (tu máquina) | Pipeline científico + reentrenamiento | `src/`, `data/`, `outputs/`, `.pkl`, `.gpkg`, `.geojson` |
| Supabase | Almacenamiento de predicciones en producción | Tabla `streets` (PostGIS) |
| Vercel | Servir la API y el frontend | `api/`, `app/`, `components/`, `lib/` |
| GitHub | Control de versiones del código | Todo excepto lo ignorado por `.gitignore` |

### `.vercelignore`

Archivo en la raíz del repo que impide que Vercel suba archivos innecesarios durante el build. Sin este archivo, Vercel intentaría procesar los 85 MB de archivos geoespaciales trackeados en git.

```
# Datos científicos — van a Supabase, no a Vercel
data/
outputs/
notebooks/
src/
docs/
mvp/

# Scripts del pipeline (solo uso local)
scripts/load_geojson_to_supabase.py
run_and_compare.py

# Binarios y datos geoespaciales
__pycache__/
*.pyc
*.pkl
*.gpkg
*.geojson
*.zip
```

> **Nota sobre archivos grandes en git:** `buildings_liverpool.gpkg` (61 MB) y
> `liverpool_pollution_map.geojson` (24 MB) están actualmente trackeados en git.
> El `.vercelignore` resuelve el problema para el despliegue. Si en el futuro se
> quiere limpiar el historial, usar `git filter-repo` o mover estos archivos a
> `.gitignore` y hacer un commit de limpieza.

### Flujo de trabajo por tipo de cambio

**Cuando cambia el código de la API o el frontend:**
```bash
git add api/ app/ components/ lib/
git commit -m "feat: ..."
git push          # Vercel hace autodeploy automáticamente desde GitHub
```

**Cuando el pipeline produce un nuevo mapa:**
```bash
# 1. Correr el pipeline localmente (scripts 1-9)
python run_and_compare.py

# 2. Cargar el nuevo GeoJSON a Supabase
SUPABASE_DB_URL="..." python scripts/load_geojson_to_supabase.py

# 3. No se necesita redeploy — la API ya consulta la BD en tiempo real
curl https://airtrace.vercel.app/api/health  # verificar streets_count
```

**Cuando hay cambios en ambos (código + datos):**
```bash
# Primero cargar datos
python scripts/load_geojson_to_supabase.py

# Luego hacer push del código
git push
```

---

## 11. Variables de Entorno

| Variable | Entorno | Descripción |
|---|---|---|
| `SUPABASE_DB_URL` | Server-side | PostgreSQL connection string de Supabase |
| `SUPABASE_ANON_KEY` | Client-side | Clave pública Supabase para queries desde frontend |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Client-side | Token Mapbox GL JS para renderizado de mapas |
| `NEXT_PUBLIC_API_BASE` | Client-side | URL base de la API (auto en Vercel) |

**Configuración en Vercel:**

```bash
vercel env add SUPABASE_DB_URL          # añadir como Secret
vercel env add SUPABASE_ANON_KEY
vercel env add NEXT_PUBLIC_MAPBOX_TOKEN
```

---

## 12. Despliegue Step-by-Step

### Prerrequisitos

- Cuenta Vercel (tier free válido para MVP)
- Cuenta Supabase (tier free: 500 MB, suficiente para GeoJSON ~80 MB en PostGIS)
- Token Mapbox (tier free: 50.000 tile loads/mes)
- Python ≥ 3.10 con geopandas instalado (solo para el script de carga)

### Pasos

```bash
# 1. Instalar Vercel CLI
npm i -g vercel

# 2. Inicializar proyecto
cd Proyecto-III
vercel init

# 3. Crear proyecto en Supabase y obtener DB URL
#    Dashboard Supabase → Project Settings → Database → Connection string (URI)

# 4. Cargar GeoJSON a Supabase (una sola vez)
SUPABASE_DB_URL="postgresql://postgres:<pwd>@<host>:5432/postgres" \
    python scripts/load_geojson_to_supabase.py

# 5. Configurar variables de entorno en Vercel
vercel env add SUPABASE_DB_URL
vercel env add NEXT_PUBLIC_MAPBOX_TOKEN

# 6. Deploy a staging
vercel

# 7. Verificar endpoint
curl "https://<slug>.vercel.app/api/health"

# 8. Deploy a producción
vercel --prod
```

---

## 13. Frontend — Componentes Clave

### `components/AirMap.tsx`

Mapa Mapbox GL JS con capa GeoJSON coloreada por `pm25_pred`.

```typescript
// Paleta de color: blanco (limpio) → naranja → rojo (contaminado)
const PM25_COLOR_SCALE = [
  [0,   [0,   200, 100]],   // A: verde
  [5,   [200, 230,  50]],   // B: amarillo-verde
  [10,  [255, 200,   0]],   // C: amarillo
  [15,  [255, 130,   0]],   // D: naranja
  [20,  [230,  50,  50]],   // E: rojo
  [25,  [150,   0, 150]],   // F: morado
];

// Capa Mapbox
map.addLayer({
  id:     "streets-pollution",
  type:   "line",
  source: "streets",
  paint:  {
    "line-color": [
      "interpolate", ["linear"], ["get", "pm25_pred"],
      0, "rgb(0,200,100)",
      5, "rgb(200,230,50)",
      10, "rgb(255,200,0)",
      15, "rgb(255,130,0)",
      20, "rgb(230,50,50)",
      25, "rgb(150,0,150)"
    ],
    "line-width": 2,
    "line-opacity": 0.85,
  }
});
```

---

## 14. Actualización del Mapa (Pipeline → Supabase)

Cuando el pipeline produce un nuevo `liverpool_pollution_map.geojson`:

```bash
# Re-cargar en Supabase (tabla se reemplaza)
SUPABASE_DB_URL="..." python scripts/load_geojson_to_supabase.py

# No se requiere redeploy en Vercel — la API consulta la BD en tiempo real
```

Para automatizar con el scheduler de Claude:

```
Tarea: airtraceapi:refresh-map
Cron: 0 3 1 * *  (primer día de cada mes, 3am)
Pasos:
  1. Ejecutar pipeline src/ (scripts 1-9)
  2. Verificar que outputs/maps/liverpool_pollution_map.geojson existe
  3. Ejecutar scripts/load_geojson_to_supabase.py
  4. Verificar /api/health → streets_count > 8000
```

---

## 15. KPIs y Criterios de Aceptación del MVP

| KPI | Target | Cómo medirlo |
|---|---|---|
| Latencia `/api/predict` | < 200 ms (p95) | Vercel Analytics / Supabase Logs |
| Cobertura geográfica | 8.450 tramos (0 NaN) | `SELECT COUNT(*) FROM streets` |
| Disponibilidad | ≥ 99.5% | Vercel uptime monitor |
| Precisión PM2.5 | R² ≥ 0.60 en reentrenamiento | LOOCV automatizado |
| Primer cliente B2G | 1 piloto pagado | CRM |
| API keys activas | ≥ 5 (mes 6) | Supabase dashboard |

---

## 16. Limitaciones del MVP (para comunicar a clientes)

1. **n=20 sensores**: los modelos están validados con Leave-One-Out Cross-Validation pero el tamaño muestral implica intervalos de confianza amplios.
2. **Predicciones anuales**: el mapa refleja niveles medios anuales (datos 2024). No apto para predicciones horarias o estacionales sin datos adicionales.
3. **Cobertura AADF 19.8%**: la variable de tráfico fue eliminada del modelo final por falta de significación estadística. La influencia del tráfico está capturada indirectamente por `road_length_residential_m`.
4. **Radio de ciudad único**: el modelo actual es específico a Liverpool. Extensión a Manchester/Birmingham requiere reentrenamiento con datos locales.
5. **Fuentes episódicas**: eventos puntuales (obras, incendios, tráfico puntual) no están capturados por el modelo estático.

---

## 17. Roadmap Post-MVP

| Versión | Entregable | Habilitador técnico |
|---|---|---|
| MVP (mes 1–4) | API + dashboard Liverpool | Pipeline actual + Vercel + Supabase |
| v1.1 | Score A–F por código postal (LSOA) | Notebook `3.2_LUR_Barrios_LSOA.ipynb` |
| v1.2 | Validación vs estaciones DEFRA AURN | `src/data/download_aurn.py` |
| v1.3 | Health Impact Assessment integrado | Issue #24 |
| v2.0 | Segunda ciudad (Manchester) | Pipeline reproducible |
| v2.1 | Streaming en tiempo real | Apache Kafka o Supabase Realtime |

---

*Documento generado el 2026-04-17. Última actualización de métricas: 2026-04-17. Versión de referencia del modelo: SVR LUR v2, entrenado sobre datos 2024 con 21 sensores (PM10) / 20 sensores (PM2.5), tras sesión de mejora Abril 2026 — ver `docs/08_lur_improvement_session.md`.*
