# AirTrace — Technical Specification (Web App)

**Producto:** AirTrace — Liverpool Air Quality Dashboard  
**Versión:** 0.2.0-webapp  
**Fecha:** 2026-04-17  
**Enfoque:** Web app de visualización pública. Sin API comercial, sin auth. Datos claros, interactivos y con contexto.

---

## 1. Contexto y Datos Disponibles

### Artefactos del pipeline científico

| Artefacto | Ruta | Descripción |
|-----------|------|-------------|
| `liverpool_pollution_map.geojson` | `outputs/maps/` | 8.450 tramos con `pm25_pred`, `pm10_pred` (media anual 2024) |
| `lur_lsoa_predictions.geojson` | `outputs/maps/` | 302 LSOAs con `PM2.5_final`, `PM10_final`, `score_pm25` |
| `sensores_monthly.csv` | `data/interim/` | Panel mensual 2024: 21 sensores × 12 meses (PM2.5, PM10, meteo) |

### Cobertura temporal real

| Dataset | Período disponible | Uso en la app |
|---------|-------------------|---------------|
| Predicciones LUR streets | Media anual 2024 | Mapa base principal |
| Datos sensor mensuales | Ene–Dic 2024 | Gráficos EDA de evolución mensual |
| Predicciones mensuales (a generar) | Ene–Dic 2024 × 8.450 tramos | Slider de meses en el mapa |
| LSOA aggregations | Media anual 2024 | Capa coroplética de barrios |

> **Sobre la "evolución":** Solo hay datos completos de 2024. La evolución temporal se
> muestra como **variación mensual dentro de 2024**, lo cual es científicamente válido:
> PM2.5 es ~30% mayor en invierno (calefacción + inversión térmica) que en verano.

---

## 2. Propuesta de la Web App

> **"El estado del aire en Liverpool. Por calle, por mes, con contexto."**

### Qué muestra la app

1. **Mapa de contaminación** — 8.450 tramos de calle coloreados por PM2.5/PM10
2. **Slider de meses** — Enero a Diciembre 2024, el mapa cambia con la estacionalidad real
3. **Panel EDA** — Gráficos de tendencia mensual, distribución por tipo de vía, comparativa de zonas
4. **Eventos canónicos** — Popups en el mapa y el timeline: Bonfire Night, ola de calor, festivos, noticias locales
5. **Vista LSOA** — Toggle para ver barrios en lugar de calles (escala A–F)
6. **Tooltips de calle** — Click en cualquier tramo: nombre, score, PM2.5/PM10, tipo de vía

### Lo que NO incluye (fuera de scope)

- No requiere login ni API key
- No hay backend propio — solo frontend + Supabase Storage
- No hay datos en tiempo real (predicciones estáticas 2024)
- No hay otras ciudades

---

## 3. Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                   VERCEL (Static + CDN)                  │
│                                                          │
│   Next.js 14 App Router                                 │
│   ┌────────────────┐  ┌────────────────────────────┐    │
│   │  MapView       │  │  SidePanel                 │    │
│   │  - Mapbox GL   │  │  - MonthSlider             │    │
│   │  - StreetsLayer│  │  - TimeseriesChart         │    │
│   │  - LsoaLayer   │  │  - TopPollutedList         │    │
│   │  - EventsLayer │  │  - InfoCard (click)        │    │
│   └────────────────┘  └────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────┘
                                │ fetch (no auth needed)
                                ▼
          ┌───────────────────────────────────────┐
          │         Supabase Storage               │
          │  (bucket público "airtrace-data")      │
          │                                       │
          │  streets_annual.geojson    (24 MB)    │
          │  streets_2024_01.geojson   (~24 MB)   │
          │  streets_2024_02.geojson              │
          │  ...                                  │
          │  streets_2024_12.geojson              │
          │  lsoa_predictions.geojson  (2 MB)     │
          │  monthly_stats.json        (<100 KB)  │
          │  events.json               (<10 KB)   │
          └───────────────────────────────────────┘
```

**Por qué Storage y no PostGIS:** Para una web app pública sin auth, un bucket con archivos públicos
es más simple, más rápido (CDN), y no requiere configurar RLS. Los archivos GeoJSON se cargan
una vez por sesión en el cliente; Mapbox hace el rendering localmente.

**Optimización de tamaño:** Los GeoJSONs mensuales se pueden simplificar eliminando columnas
innecesarias (solo `geometry`, `pm25_pred`, `pm10_pred`, `highway`, `name`), reduciéndolos a ~6–8 MB.

---

## 4. Estructura de Directorios

```
Proyecto-III/
├── mvp/
│   ├── TECHNICAL_SPEC.md       ← este documento
│   ├── Analisis.md
│   └── PROCEDIMIENTO_MVP.md
│
├── webapp/                     ← app completa aquí
│   ├── package.json
│   ├── next.config.js
│   ├── vercel.json
│   │
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx            ← página principal (layout map + panel)
│   │   └── globals.css
│   │
│   ├── components/
│   │   ├── MapView.tsx         ← mapa Mapbox + capas
│   │   ├── StreetsLayer.tsx     ← capa de tramos coloreados
│   │   ├── LsoaLayer.tsx       ← capa coroplética de barrios
│   │   ├── EventsLayer.tsx     ← markers de eventos canónicos
│   │   ├── MonthSlider.tsx     ← slider Ene–Dic 2024
│   │   ├── SidePanel.tsx       ← panel lateral con gráficos
│   │   ├── TimeseriesChart.tsx ← gráfico PM2.5 mensual
│   │   ├── InfoCard.tsx        ← popup al hacer click en tramo
│   │   └── ScoreBadge.tsx      ← badge A–F con color
│   │
│   ├── lib/
│   │   ├── colorScale.ts       ← paleta PM2.5 → color RGB
│   │   ├── scoring.ts          ← PM2.5 → score A–F
│   │   └── dataLoader.ts       ← fetch de GeoJSONs por mes
│   │
│   └── public/
│       └── events.json         ← eventos canónicos (estático)
│
├── scripts/
│   ├── generate_monthly_geojsons.py  ← genera 12 GeoJSONs mensuales
│   └── upload_to_supabase_storage.py ← sube archivos al bucket público
│
├── src/               ← pipeline científico (sin cambios)
├── outputs/
└── data/
```

---

## 5. Datos — Especificación Completa

### 5.1 GeoJSON anual (`streets_annual.geojson`)

El archivo existente `outputs/maps/liverpool_pollution_map.geojson` optimizado:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "LineString", "coordinates": [...] },
      "properties": {
        "name": "Mather Avenue",
        "highway": "secondary",
        "pm25_pred": 12.27,
        "pm10_pred": 23.81,
        "score": "C"
      }
    }
  ]
}
```

### 5.2 GeoJSONs mensuales (`streets_2024_MM.geojson`)

El pipeline calcula predicciones usando las medias mensuales de meteo como controles.
Las variables espaciales (land use, roads) no cambian mes a mes.
Solo varían: `air_temperature_mean`, `wind_speed_mean`, `rain_days`, `mes_sin`, `mes_cos`.

**Script:** `scripts/generate_monthly_geojsons.py` — ejecuta el modelo SVR una vez por mes
con los valores meteo de ese mes, produce 12 GeoJSONs ligeros (~6 MB cada uno).

### 5.3 Estadísticas mensuales (`monthly_stats.json`)

```json
{
  "2024-01": {
    "pm25_mean_city": 12.8,
    "pm25_std": 2.1,
    "pm10_mean_city": 24.3,
    "by_highway": {
      "primary":     { "pm25": 14.2, "pm10": 27.1 },
      "secondary":   { "pm25": 13.1, "pm10": 25.0 },
      "residential": { "pm25": 11.3, "pm10": 21.8 }
    },
    "top5_streets": [
      { "name": "Scotland Road", "pm25": 18.4 }
    ]
  },
  "2024-02": { ... },
  ...
}
```

Generado por `scripts/generate_monthly_geojsons.py` como subproducto.

### 5.4 Eventos canónicos (`public/events.json`)

```json
{
  "events": [
    {
      "id": "bonfire_2024",
      "date": "2024-11-05",
      "month": "2024-11",
      "title": "Bonfire Night",
      "description": "Los fuegos artificiales y quemas del 5 de noviembre generan picos de PM2.5 y PM10 de corta duración. Los sensores de Liverpool registran aumentos de hasta 3× la media diaria.",
      "type": "seasonal",
      "impact": "high",
      "lat": 53.4084,
      "lng": -2.9916
    },
    {
      "id": "heatwave_aug_2024",
      "date": "2024-08-12",
      "month": "2024-08",
      "title": "Ola de calor — Agosto 2024",
      "description": "Las temperaturas por encima de 28°C favorecen la formación de ozono troposférico pero reducen PM2.5 primario al acelerar la dispersión atmosférica. Mes con menor PM2.5 del año.",
      "type": "climate",
      "impact": "low",
      "lat": 53.4084,
      "lng": -2.9916
    },
    {
      "id": "covid_lockdown_context",
      "date": "2020-03-23",
      "month": null,
      "title": "Contexto: Confinamiento COVID-19 (2020)",
      "description": "Durante el confinamiento de marzo-junio 2020, los niveles de NO2 en Liverpool cayeron un ~45% y el PM2.5 un ~15%. Este periodo sirve como experimento natural de referencia para estimar el impacto del tráfico en la contaminación urbana.",
      "type": "policy",
      "impact": "reference",
      "lat": 53.4084,
      "lng": -2.9916
    },
    {
      "id": "caz_evaluation_2024",
      "date": "2024-03-15",
      "month": "2024-03",
      "title": "Liverpool CAZ — Evaluación activa",
      "description": "El Liverpool City Council inicia la evaluación formal de una Clean Air Zone (CAZ) bajo el marco del Joint Air Quality Unit (JAQU). Los datos de AirTrace de este período son los primeros disponibles durante el proceso de evaluación.",
      "type": "policy",
      "impact": "medium",
      "lat": 53.4047,
      "lng": -2.9915
    },
    {
      "id": "winter_heating_jan_2024",
      "date": "2024-01-15",
      "month": "2024-01",
      "title": "Temporada de calefacción — Enero 2024",
      "description": "Los meses de invierno (enero, febrero, diciembre) muestran niveles de PM2.5 un 25-30% superiores a la media anual. La combinación de calefacción doméstica, inversión térmica y baja velocidad del viento concentra los contaminantes cerca del suelo.",
      "type": "seasonal",
      "impact": "high",
      "lat": 53.4084,
      "lng": -2.9916
    },
    {
      "id": "easter_traffic_2024",
      "date": "2024-03-29",
      "month": "2024-03",
      "title": "Semana Santa — Reducción de tráfico",
      "description": "El fin de semana de Pascua reduce el tráfico laboral en Liverpool un ~40%. Los sensores ubicados en vías principales (Scotland Road, Queens Drive) muestran las caídas más marcadas de PM2.5 del año.",
      "type": "traffic",
      "impact": "medium",
      "lat": 53.4320,
      "lng": -2.9610
    }
  ]
}
```

---

## 6. Componentes Frontend — Especificación

### 6.1 `MapView.tsx`

Mapa Mapbox GL JS full-screen. Gestiona el estado del mes seleccionado y qué capa mostrar (calles / LSOAs).

**Estado:**
```typescript
type MapState = {
  selectedMonth: string | null  // "2024-01" ... "2024-12" | null (anual)
  activeLayer: "streets" | "lsoa"
  selectedFeature: StreetFeature | LsoaFeature | null
}
```

**Comportamiento:**
- Carga inicial: `streets_annual.geojson` (media anual)
- Al cambiar mes: reemplaza source con `streets_2024_MM.geojson`
- Click en feature: abre `InfoCard` con los datos del tramo/LSOA
- Hover en feature: highlight temporal (outline blanco)

### 6.2 `MonthSlider.tsx`

```
[Anual] ──●─────────────────────── [Ene] [Feb] [Mar] ... [Dic]
                                    ↑ slider o tabs de meses
```

- 13 posiciones: "Anual" + 12 meses
- Al seleccionar mes: emite evento al `MapView` + actualiza `SidePanel`
- Muestra temperatura y velocidad de viento promedio del mes seleccionado (de `monthly_stats.json`)

### 6.3 `TimeseriesChart.tsx`

Gráfico de línea con PM2.5 y PM10 medio de la ciudad, enero–diciembre 2024.
- Eje X: meses
- Eje Y: µg/m³
- Línea PM2.5 (azul) + PM10 (naranja)
- Línea de referencia WHO (5 µg/m³, roja punteada)
- Línea de referencia UK 2040 (10 µg/m³, naranja punteada)
- Al hover sobre un mes: sincroniza con el slider del mapa

**Librería:** Recharts (< 45 kB gzipped)

### 6.4 `EventsLayer.tsx`

Markers en el mapa para cada evento canónico con `lat/lng` definidos.
- Icono según `type`: 🌡️ climate, 📋 policy, 🚦 traffic, 🎆 seasonal
- Click en marker: popup con título, descripción, fecha
- Si el evento tiene `month`, solo se muestra cuando ese mes está seleccionado en el slider

### 6.5 `InfoCard.tsx`

Card flotante que aparece al hacer click en un tramo o LSOA.

**Para tramo:**
```
┌─────────────────────────────────┐
│ Scotland Road          [ C ]    │
│ secondary road                  │
│ PM2.5: 14.2 µg/m³  ████████░░  │
│ PM10:  27.1 µg/m³  ████████░░  │
│ WHO límite: 5 µg/m³  ⚠ ×2.8    │
│ UK 2040 límite: 10  ⚠ ×1.4     │
└─────────────────────────────────┘
```

**Para LSOA:**
```
┌─────────────────────────────────┐
│ Liverpool 017E         [ C ]    │
│ Vauxhall                        │
│ PM2.5 medio: 14.97 µg/m³       │
│ Población: ~1.500 residentes    │
│ Posición: #1 de 302 barrios     │
└─────────────────────────────────┘
```

### 6.6 Paleta de color

```typescript
// lib/colorScale.ts
export const PM25_STOPS: [number, string][] = [
  [0,  "#00c864"],  // A: verde
  [5,  "#c8e632"],  // B: amarillo-verde
  [10, "#ffc800"],  // C: amarillo
  [15, "#ff8200"],  // D: naranja
  [20, "#e63232"],  // E: rojo
  [25, "#960096"],  // F: morado
]

export function pm25ToScore(val: number): "A"|"B"|"C"|"D"|"E"|"F" {
  if (val < 5)  return "A"
  if (val < 10) return "B"
  if (val < 15) return "C"
  if (val < 20) return "D"
  if (val < 25) return "E"
  return "F"
}
```

---

## 7. Script de Generación de GeoJSONs Mensuales

`scripts/generate_monthly_geojsons.py`

**Lógica:**
1. Cargar el modelo SVR entrenado (`outputs/models/lur_model_PM25.pkl`, `lur_model_PM10.pkl`)
2. Cargar las features espaciales del GeoJSON anual (land use, roads — constantes)
3. Para cada mes M en 2024:
   - Calcular media mensual de `air_temperature_mean`, `wind_speed_mean`, `rain_days` desde `sensores_monthly.csv`
   - Calcular `mes_sin = sin(2π × M / 12)`, `mes_cos = cos(2π × M / 12)`
   - Construir X con las features espaciales constantes + controles meteo del mes M
   - Predecir pm25 y pm10 con los modelos SVR
   - Generar GeoJSON ligero con solo geometry + pm25_pred + pm10_pred + highway + name + score
4. Exportar a `outputs/maps/monthly/streets_2024_MM.geojson`
5. Generar `outputs/maps/monthly/monthly_stats.json` con estadísticas agregadas

**Output esperado:**
- 12 archivos de ~6–8 MB cada uno (sin columnas innecesarias)
- 1 archivo `monthly_stats.json` de < 100 KB

---

## 8. Deploy — Configuración Vercel

### `webapp/vercel.json`

```json
{
  "version": 2,
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "env": {
    "NEXT_PUBLIC_MAPBOX_TOKEN": "@mapbox_token",
    "NEXT_PUBLIC_DATA_BASE_URL": "@data_base_url"
  }
}
```

### `webapp/package.json`

```json
{
  "name": "airtrace-webapp",
  "version": "0.2.0",
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "mapbox-gl": "^3.4.0",
    "recharts": "^2.12.0",
    "@radix-ui/react-slider": "^1.2.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "@types/mapbox-gl": "^3.1.0"
  }
}
```

### Variable de entorno `NEXT_PUBLIC_DATA_BASE_URL`

URL base del bucket público de Supabase Storage donde están los GeoJSONs.
Ejemplo: `https://<project>.supabase.co/storage/v1/object/public/airtrace-data`

```typescript
// lib/dataLoader.ts
const BASE = process.env.NEXT_PUBLIC_DATA_BASE_URL!

export async function loadAnnualStreets() {
  const res = await fetch(`${BASE}/streets_annual.geojson`)
  return res.json()
}

export async function loadMonthlyStreets(month: string) {
  // month = "2024-01", "2024-02", ...
  const mm = month.split("-")[1]
  const res = await fetch(`${BASE}/streets_2024_${mm}.geojson`)
  return res.json()
}

export async function loadMonthlyStats() {
  const res = await fetch(`${BASE}/monthly_stats.json`)
  return res.json()
}
```

---

## 9. KPIs de Aceptación

| KPI | Target | Cómo medir |
|-----|--------|-----------|
| Carga inicial del mapa | < 3 s (cable) | Chrome DevTools Network |
| Cambio de mes (slider) | < 1 s | time desde click hasta repaint del mapa |
| Sin errores en consola | 0 errores | DevTools Console |
| Funciona en móvil | Layout legible en 375px | Chrome emulación iPhone 12 |
| GeoJSON anual completo | 8.450 features | `map.querySourceFeatures('streets').length` |
| Todos los eventos visibles | 6 markers | Inspección visual |

---

## 10. Limitaciones a Comunicar en la App

Texto de footer / modal "Sobre los datos":

> Los datos de contaminación son **predicciones del modelo LUR** entrenado con 20–21 sensores IoT
> de la red Aeternum desplegada en Liverpool. Reflejan medias anuales de 2024 (o medias mensuales
> cuando se activa el slider). No representan mediciones en tiempo real. Precisión validada con
> R² = 0.602 (PM2.5) y R² = 0.581 (PM10) mediante Leave-One-Out Cross-Validation.
> Fuentes: OpenStreetMap, DfT AADF, MIDAS (UK Met Office), ONS Census 2021.

---

_Versión 0.2.0 · Reemplaza TECHNICAL_SPEC v0.1.0 (arquitectura API comercial, descartada en favor de web app pública)_
_Referencia científica: `docs/08_lur_improvement_session.md` · `docs/10_project_progress_report.md`_
