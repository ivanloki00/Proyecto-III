# AirTrace — Guía de Procedimiento por Tareas y Agentes (Web App)

**Versión:** 2.0  
**Fecha:** 2026-04-17  
**Referencia técnica:** `TECHNICAL_SPEC.md` v0.2.0  
**Enfoque:** Web app de visualización pública. Sin API comercial. Sin backend propio.

---

## Cómo leer este documento

Cada tarea tiene:
- **Agente** — quién la ejecuta
- **Input** — qué debe existir antes
- **Output** — qué produce
- **Criterio de aceptación** — condición binaria y verificable
- **Instrucción literal** — el prompt exacto a dar a Claude Code cuando aplica

Las fases son secuenciales. Dentro de cada fase, las tareas marcadas con `//paralelo` pueden ejecutarse en paralelo.

---

## Mapa de Agentes

| Símbolo | Agente | Cuándo usarlo |
|---------|--------|---------------|
| 👤 | **Humano** | Cuentas, tokens, decisiones de negocio, pruebas manuales en browser |
| 🤖 | **Claude Code — general** | Escribir código, crear archivos, ejecutar scripts |
| 🔍 | **Claude Code — Explore** | Entender código existente antes de modificarlo |
| 📐 | **Claude Code — Plan** | Diseño de arquitectura antes de implementar |

---

## Fase 0 — Datos: Generar GeoJSONs Mensuales

**Por qué primero:** El slider de meses es el feature central. Sin los 12 GeoJSONs, la app es solo un mapa estático.  
**Duración estimada:** 2–4 horas  
**Agente:** 🤖 Claude Code — general

---

### Tarea 0.1 — Crear `scripts/generate_monthly_geojsons.py`

**Input:** `outputs/models/lur_model_PM25.pkl`, `lur_model_PM10.pkl`, `outputs/maps/liverpool_pollution_map.geojson`, `data/interim/sensores_monthly.csv`  
**Output:** `outputs/maps/monthly/streets_2024_01.geojson` … `streets_2024_12.geojson` + `monthly_stats.json`

**Instrucción para Claude Code:**

> Lee estos archivos antes de escribir nada:
> - `src/models/lur_model.py` (líneas donde construye X para el modelo y carga los pkl)
> - `outputs/maps/liverpool_pollution_map.geojson` (inspecciona las columnas de properties)
> - `data/interim/sensores_monthly.csv` (columnas y rango de meses)
>
> Luego crea `scripts/generate_monthly_geojsons.py` que haga lo siguiente:
>
> 1. Carga `lur_model_PM25.pkl` y `lur_model_PM10.pkl` con pickle
> 2. Carga el GeoJSON anual con geopandas
> 3. Para cada mes en `sensores_monthly.csv` (2024-01 a 2024-12):
>    - Calcula la media mensual de `air_temperature_mean`, `wind_speed_mean`, `rain_days` agrupando todos los sensores de ese mes
>    - Calcula `mes_sin = np.sin(2 * np.pi * mes_num / 12)` y `mes_cos = np.cos(2 * np.pi * mes_num / 12)` donde `mes_num` es 1–12
>    - Construye un DataFrame con las features espaciales del GeoJSON (`landuse_green_m2_100m`, `road_length_residential_m_1000m`) más los controles meteo del mes
>    - Predice con los dos modelos
>    - Crea un GeoJSON ligero: solo `geometry`, `name`, `highway`, `pm25_pred` (redondeado a 2 decimales), `pm10_pred`, `score` (calculado como en el modelo: A si <5, B si <10, C si <15, D si <20, E si <25, F si >=25)
>    - Exporta a `outputs/maps/monthly/streets_2024_{mm:02d}.geojson`
> 4. Genera `outputs/maps/monthly/monthly_stats.json` con estructura:
>    ```
>    { "2024-01": { "pm25_mean": X, "pm10_mean": X, "temp_mean": X, "wind_mean": X,
>                   "by_highway": {"primary": X, "secondary": X, "residential": X} }, ... }
>    ```
> 5. Usa `logging` para indicar progreso por mes
> 6. Usa `pathlib.Path` para todos los paths
>
> El problema clave: las features espaciales del GeoJSON (`landuse_green_m2_100m`, `road_length_residential_m_1000m`) existen a nivel de sensor, no de tramo. Cada tramo fue asignado a un sensor via join espacial. Revisa cómo lur_model.py hace ese join y replica la lógica para obtener las features espaciales por tramo.

**Criterio de aceptación:**
```bash
python scripts/generate_monthly_geojsons.py
ls outputs/maps/monthly/
# → streets_2024_01.geojson ... streets_2024_12.geojson + monthly_stats.json

python -c "
import json
with open('outputs/maps/monthly/streets_2024_07.geojson') as f:
    gj = json.load(f)
print(len(gj['features']), 'features')
print(gj['features'][0]['properties'])
"
# → 8450 features, properties con pm25_pred < pm25_pred de enero (verano más limpio)
```

**Bloquea:** 0.2

---

### Tarea 0.2 — Verificar variación estacional

**Agente:** 🤖 Claude Code — general

**Instrucción para Claude Code:**

> Ejecuta este script de verificación y reporta los resultados:
> ```python
> import json, statistics
> meses = {}
> for mm in range(1, 13):
>     with open(f'outputs/maps/monthly/streets_2024_{mm:02d}.geojson') as f:
>         gj = json.load(f)
>     vals = [f['properties']['pm25_pred'] for f in gj['features']]
>     meses[f'2024-{mm:02d}'] = round(statistics.mean(vals), 3)
> for k,v in sorted(meses.items()):
>     print(f'{k}: {v} µg/m³')
> ```
> Verifica que enero/diciembre tienen PM2.5 > agosto/septiembre (patrón estacional esperado en UK).

**Criterio de aceptación:** PM2.5 medio de enero > PM2.5 medio de julio en al menos 1.5 µg/m³  
**Bloquea:** Fase 1

---

### Tarea 0.3 — Crear `public/events.json` //paralelo con 0.1

**Agente:** 🤖 Claude Code — general  
**Input:** TECHNICAL_SPEC.md §5.4 (estructura y eventos ya definidos)

**Instrucción para Claude Code:**

> Crea el archivo `webapp/public/events.json` con exactamente el contenido de la sección 5.4 del TECHNICAL_SPEC.md. No añadas ni quites eventos — el contenido está definido ahí literalmente.

**Criterio de aceptación:** `python -m json.tool webapp/public/events.json` no da error  
**Bloquea:** Tarea 4.4

---

## Fase 1 — Cuentas y Setup

**Duración estimada:** 1–2 horas  
**Agente:** 👤 Humano

| # | Tarea | Cómo | Produce | Bloquea |
|---|-------|------|---------|---------|
| 1.1 | Crear bucket público en Supabase | Supabase → Storage → New bucket → nombre `airtrace-data` → Public ON | URL base del bucket | 1.2 |
| 1.2 | Subir GeoJSONs al bucket | Script `upload_to_supabase_storage.py` (Tarea 1.3) | 14 archivos públicos | Fase 2 |
| 1.3 | Crear cuenta Vercel | vercel.com → Import GitHub repo → `webapp/` como root directory | URL de staging automática | Fase 5 |
| 1.4 | Obtener token Mapbox | account.mapbox.com → Tokens → scope `styles:read` + `tiles:read` | Token `pk.eyJ1...` | Fase 2 |
| 1.5 | Anotar URL del bucket | Dashboard Supabase → Storage → airtrace-data → cualquier archivo → Copy URL → tomar solo la parte base | String tipo `https://xxx.supabase.co/storage/v1/object/public/airtrace-data` | Fase 2 |

---

### Tarea 1.3 — Crear script de subida //paralelo con Tarea 1.1

**Agente:** 🤖 Claude Code — general

**Instrucción para Claude Code:**

> Crea `scripts/upload_to_supabase_storage.py`. El script debe:
> 1. Leer `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` de variables de entorno (service key, no anon key, para poder escribir al bucket)
> 2. Subir todos los archivos de `outputs/maps/monthly/` al bucket `airtrace-data` usando la Supabase Storage REST API (POST `{SUPABASE_URL}/storage/v1/object/airtrace-data/{filename}` con header `Authorization: Bearer {SERVICE_KEY}`)
> 3. Subir también `outputs/maps/liverpool_pollution_map.geojson` como `streets_annual.geojson`
> 4. Subir `outputs/maps/lur_lsoa_predictions.geojson` como `lsoa_predictions.geojson`
> 5. Usar `requests` para las llamadas HTTP
> 6. Logging del progreso con tamaño de cada archivo
> 7. Verificar que la URL pública de cada archivo devuelve 200 tras la subida

**Criterio de aceptación:**
```bash
SUPABASE_URL="https://xxx.supabase.co" SUPABASE_SERVICE_KEY="eyJ..." \
    python scripts/upload_to_supabase_storage.py
# → Log muestra 14 archivos subidos con 200 OK
```

---

## Fase 2 — Inicializar el Proyecto Next.js

**Duración estimada:** 1–2 horas  
**Pre-condición:** Token Mapbox disponible; URL del bucket anotada  
**Agente:** 🤖 Claude Code — general

---

### Tarea 2.1 — Scaffold del proyecto

**Instrucción para Claude Code:**

> Ejecuta en la raíz del repo:
> ```bash
> npx create-next-app@14 webapp --typescript --tailwind --app --no-src-dir --import-alias="@/*" --no-git
> ```
> Cuando pregunte, responde: TypeScript Yes, ESLint Yes, Tailwind Yes, App Router Yes.
>
> Luego entra al directorio e instala dependencias adicionales:
> ```bash
> cd webapp
> npm install mapbox-gl recharts @radix-ui/react-slider
> npm install -D @types/mapbox-gl
> ```
>
> Verifica que `npm run dev` levanta sin errores en localhost:3000.

**Criterio de aceptación:** `npm run build` en `webapp/` completa sin errores TypeScript  
**Bloquea:** 2.2, 2.3

---

### Tarea 2.2 — Crear `lib/colorScale.ts` y `lib/scoring.ts` y `lib/dataLoader.ts`

**Agente:** 🤖 Claude Code — general

**Instrucción para Claude Code:**

> Crea los tres archivos de utilidades en `webapp/lib/`:
>
> **`colorScale.ts`** — exporta `PM25_STOPS: [number, string][]` con los 6 pares valor/color del TECHNICAL_SPEC §6.6, y una función `pm25ToColor(val: number): string` que interpola linealmente entre stops.
>
> **`scoring.ts`** — exporta `pm25ToScore(val: number): "A"|"B"|"C"|"D"|"E"|"F"` y `SCORE_LABELS: Record<string, {label: string, color: string, bg: string}>` con el nombre en inglés y los colores Tailwind para cada score (A=green, B=lime, C=yellow, D=orange, E=red, F=purple).
>
> **`dataLoader.ts`** — exporta las tres funciones del TECHNICAL_SPEC §8 (`loadAnnualStreets`, `loadMonthlyStreets`, `loadMonthlyStats`). La variable `NEXT_PUBLIC_DATA_BASE_URL` se lee de `process.env`. Añade manejo de error: si el fetch falla, lanza un Error con mensaje descriptivo.

**Criterio de aceptación:** `npx tsc --noEmit` en `webapp/` no da errores en estos archivos  
**Bloquea:** Fase 3

---

## Fase 3 — Componentes del Mapa

**Duración estimada:** 2–3 días  
**Pre-condición:** Fase 2 completa; GeoJSONs subidos a Supabase Storage  
**Agente:** 🤖 Claude Code — general

---

### Tarea 3.1 — `components/ScoreBadge.tsx`

El componente más pequeño, sin dependencias. Empezar por aquí para validar el sistema de estilos.

**Instrucción para Claude Code:**

> Crea `webapp/components/ScoreBadge.tsx`. Props: `{ score: string; size?: "sm" | "lg" }`.
> Renderiza un badge cuadrado/redondeado con la letra del score (A–F) en el color correspondiente de `SCORE_LABELS` de `lib/scoring.ts`. Size "lg" = 48×48px con texto xl, "sm" = 24×24px con texto sm. Usa clases Tailwind; no CSS inline.

**Criterio de aceptación:** Renderiza correctamente en el Storybook o en una página de prueba con todos los valores A–F  

---

### Tarea 3.2 — `components/InfoCard.tsx`

**Instrucción para Claude Code:**

> Crea `webapp/components/InfoCard.tsx`. Recibe props:
> ```typescript
> type Props = {
>   feature: {
>     name: string | null
>     highway: string
>     pm25_pred: number
>     pm10_pred: number
>   } | null
>   onClose: () => void
> }
> ```
> Si `feature` es null, no renderiza nada. Si tiene valor, muestra un card flotante (posición fija, esquina inferior izquierda) con:
> - Nombre de la calle (o "Unnamed road" si null) + tipo de vía
> - `ScoreBadge` (size lg) para PM2.5
> - Barra de progreso visual para PM2.5 (0–30 µg/m³) con los colores de la paleta
> - Valores numéricos PM2.5 y PM10 con unidades
> - Dos líneas de referencia: "WHO 2021: 5 µg/m³ (×N)" y "UK 2040: 10 µg/m³ (×N)" donde N = pm25_pred / umbral redondeado a 1 decimal
> - Botón × para cerrar

**Criterio de aceptación:** Con `pm25_pred: 14.2`, el card muestra score "C", "×2.8 del límite WHO", "×1.4 del objetivo UK"

---

### Tarea 3.3 — `components/MapView.tsx`

El componente más complejo. Requiere `'use client'` (DOM API).

**Instrucción para Claude Code:**

> Crea `webapp/components/MapView.tsx` con `'use client'` al inicio.
>
> El componente recibe `{ selectedMonth: string | null, activeLayer: "streets" | "lsoa", onFeatureClick: (f: any) => void }`.
>
> Usa `useEffect` para inicializar el mapa Mapbox GL JS una sola vez (con `map.current` como ref para evitar re-inicializaciones). El token Mapbox viene de `process.env.NEXT_PUBLIC_MAPBOX_TOKEN`.
>
> **Configuración inicial del mapa:**
> - center: [-2.9816, 53.4084] (Liverpool)
> - zoom: 12
> - style: "mapbox://styles/mapbox/dark-v11"
>
> **Al cargar el mapa (evento `load`):**
> - Llamar `loadAnnualStreets()` de `lib/dataLoader.ts`
> - Añadir source `streets` de tipo `geojson` con los datos cargados
> - Añadir layer `streets-line` de tipo `line` con paint:
>   ```json
>   {
>     "line-color": ["interpolate", ["linear"], ["get", "pm25_pred"],
>       0, "#00c864", 5, "#c8e632", 10, "#ffc800",
>       15, "#ff8200", 20, "#e63232", 25, "#960096"],
>     "line-width": ["interpolate", ["linear"], ["zoom"], 10, 1, 14, 3],
>     "line-opacity": 0.9
>   }
>   ```
> - Añadir source `lsoa` con `loadAnnualLsoa()` (que debes crear en dataLoader.ts) — en layer `lsoa-fill` de tipo `fill`, inicialmente con `layout: { visibility: "none" }`
>
> **Al cambiar `selectedMonth`:**
> - Si null: volver a `streets_annual.geojson`
> - Si "2024-MM": llamar `loadMonthlyStreets(selectedMonth)`, actualizar los datos del source con `map.current.getSource('streets').setData(data)`
>
> **Al cambiar `activeLayer`:**
> - "streets": `setLayoutProperty('streets-line', 'visibility', 'visible')` + ocultar lsoa
> - "lsoa": ocultar streets + mostrar lsoa
>
> **Click en feature:**
> - `map.on('click', 'streets-line', (e) => onFeatureClick(e.features[0].properties))`
> - `map.on('click', 'lsoa-fill', (e) => onFeatureClick(e.features[0].properties))`
> - Cursor: pointer al hacer hover sobre cualquier layer interactivo
>
> El div del mapa debe ocupar 100% del width y height del contenedor padre.

**Criterio de aceptación:**
- [ ] El mapa carga con tramos de Liverpool coloreados
- [ ] Click en un tramo llama `onFeatureClick` con las properties del tramo
- [ ] Cambiar `selectedMonth` a "2024-07" actualiza la capa sin reinicializar el mapa

---

### Tarea 3.4 — `components/EventsLayer.tsx`

**Instrucción para Claude Code:**

> Crea `webapp/components/EventsLayer.tsx` con `'use client'`.
>
> Props: `{ map: mapboxgl.Map | null, selectedMonth: string | null }`.
>
> Al montar (cuando `map` no es null):
> 1. Fetch `/events.json` (público en `public/`)
> 2. Para cada evento en `events.json`:
>    - Si `event.month` es null (evento de contexto histórico como COVID): mostrar siempre
>    - Si `event.month` coincide con `selectedMonth`: mostrar el marker
>    - En otro caso: no mostrar
> 3. Crear un `mapboxgl.Marker` con HTML personalizado según `event.type`:
>    - seasonal: emoji 🎆 sobre fondo dark
>    - climate: 🌡️
>    - policy: 📋
>    - traffic: 🚦
> 4. Al hacer click en el marker: abrir `mapboxgl.Popup` con título, fecha formateada, y descripción del evento
>
> Al cambiar `selectedMonth`: eliminar todos los markers existentes y recrear según las nuevas condiciones de visibilidad.
>
> El componente no renderiza HTML propio (los markers van directamente al mapa). Devuelve `null`.

**Criterio de aceptación:**
- En mes "2024-11" se ve el marker de Bonfire Night en el mapa
- En mes "2024-08" se ve el marker de la ola de calor
- El evento COVID se ve siempre (month: null)
- Click en marker abre popup con descripción

---

## Fase 4 — Panel Lateral y Slider

**Duración estimada:** 1–2 días  
**Agente:** 🤖 Claude Code — general

---

### Tarea 4.1 — `components/MonthSlider.tsx`

**Instrucción para Claude Code:**

> Crea `webapp/components/MonthSlider.tsx`.
>
> Props: `{ value: string | null, onChange: (month: string | null) => void, stats: Record<string, any> | null }`.
>
> Renderiza:
> 1. Una fila de 13 botones: "Anual" + "Ene" "Feb" "Mar" "Abr" "May" "Jun" "Jul" "Ago" "Sep" "Oct" "Nov" "Dic"
> 2. El botón activo tiene fondo con el color de la paleta según el `pm25_mean` del mes en `stats`
> 3. Debajo del botón activo: temperatura media y velocidad de viento del mes (de `stats[selectedMonth]`)
> 4. Al hacer click: llama `onChange("2024-01")` ... `onChange("2024-12")` o `onChange(null)` para "Anual"
> 5. Un tooltip al hover sobre cada mes que muestra "PM2.5: X µg/m³"
>
> Usa `@radix-ui/react-slider` si el diseño de botones resulta difícil, o directamente botones HTML con Tailwind.

**Criterio de aceptación:** Al seleccionar "Jul", el botón se marca como activo y se emite `onChange("2024-07")`

---

### Tarea 4.2 — `components/TimeseriesChart.tsx`

**Instrucción para Claude Code:**

> Crea `webapp/components/TimeseriesChart.tsx`.
>
> Props: `{ stats: Record<string, any> | null, selectedMonth: string | null }`.
>
> Usa Recharts `LineChart` + `ResponsiveContainer`. El gráfico muestra:
> - Datos: array de 12 puntos `{ month: "Ene", pm25: X, pm10: X }` extraídos de `stats`
> - Línea PM2.5 (color `#3b82f6`, azul)
> - Línea PM10 (color `#f97316`, naranja) en eje Y secundario o escalado (PM10 suele ser el doble de PM2.5)
> - ReferenceLine horizontal en y=5 (WHO 2021, color rojo, etiqueta "WHO")
> - ReferenceLine horizontal en y=10 (UK 2040, color naranja, etiqueta "UK 2040")
> - Al hacer click en un punto del gráfico: llama un callback `onMonthSelect(month)` para sincronizar con el slider
> - El punto del mes seleccionado en `selectedMonth` se resalta con un dot más grande
> - Tooltip con los valores de ese mes
> - Eje Y etiquetado con "µg/m³"
>
> Si `stats` es null, muestra un skeleton loader (3 líneas grises pulsantes).

**Criterio de aceptación:** El gráfico renderiza con 12 puntos. El mes de enero tiene valor mayor que julio.

---

### Tarea 4.3 — `components/SidePanel.tsx`

**Instrucción para Claude Code:**

> Crea `webapp/components/SidePanel.tsx`.
>
> Props:
> ```typescript
> type Props = {
>   stats: Record<string, any> | null
>   selectedMonth: string | null
>   activeLayer: "streets" | "lsoa"
>   onMonthChange: (m: string | null) => void
>   onLayerChange: (l: "streets" | "lsoa") => void
> }
> ```
>
> Layout (panel fijo en el lado derecho del viewport, 320px de ancho):
>
> 1. **Header**: Logo "AirTrace" + "Liverpool 2024" en subtítulo
> 2. **Toggle de capa**: dos botones "Calles" / "Barrios (LSOA)" con estilo tab
> 3. **MonthSlider** (componente Tarea 4.1)
> 4. **TimeseriesChart** (componente Tarea 4.2)
> 5. **Estadísticas del mes seleccionado** (o anuales si null):
>    - PM2.5 medio ciudad: valor + ScoreBadge
>    - PM10 medio ciudad: valor
>    - Desglose por tipo de vía: tabla pequeña primary/secondary/residential
> 6. **Footer**: "Datos: SVR LUR Model, R²=0.602 · 8.450 tramos · 21 sensores IoT · 2024"
>
> El panel tiene fondo `bg-gray-900/95 backdrop-blur` para que el mapa se vea detrás.

**Criterio de aceptación:** El panel se renderiza sin desbordarse. El toggle de capa llama `onLayerChange`. El slider llama `onMonthChange`.

---

### Tarea 4.4 — `app/page.tsx` — Integración final

**Instrucción para Claude Code:**

> Crea `webapp/app/page.tsx`. Este es el componente raíz que integra todo.
>
> Estado global (useState):
> ```typescript
> const [selectedMonth, setSelectedMonth] = useState<string | null>(null)
> const [activeLayer, setActiveLayer] = useState<"streets" | "lsoa">("streets")
> const [selectedFeature, setSelectedFeature] = useState<any | null>(null)
> const [stats, setStats] = useState<any | null>(null)
> const [mapInstance, setMapInstance] = useState<mapboxgl.Map | null>(null)
> ```
>
> Al montar: fetch de `loadMonthlyStats()` → guardar en `stats`.
>
> Layout (CSS Grid o Flexbox):
> ```
> ┌────────────────────────────────────┬────────────┐
> │                                    │            │
> │         MapView (flex-1)           │ SidePanel  │
> │                                    │ (320px)    │
> │                                    │            │
> └────────────────────────────────────┴────────────┘
> ```
> El MapView y SidePanel ocupan 100vh.
>
> - `MapView` recibe `selectedMonth`, `activeLayer`, `onFeatureClick`, `onMapReady` (callback para guardar la instancia del mapa)
> - `EventsLayer` recibe `map={mapInstance}` y `selectedMonth`
> - `SidePanel` recibe todos los callbacks y el estado
> - `InfoCard` se renderiza sobre el mapa (posición absoluta) cuando `selectedFeature !== null`
>
> El componente debe tener `'use client'` porque usa useState.

**Criterio de aceptación:**
- [ ] `npm run build` en `webapp/` completa sin errores
- [ ] `npm run dev` muestra la app en localhost:3000
- [ ] El mapa carga con Liverpool y los tramos coloreados
- [ ] El panel lateral es visible y muestra el gráfico de línea
- [ ] El slider de meses funciona y cambia el mapa

---

## Fase 5 — Deploy a Vercel

**Duración estimada:** 1–2 horas  
**Pre-condición:** `npm run build` pasa localmente; archivos en Supabase Storage  
**Agente:** 👤 Humano + 🤖 Claude Code — general

---

### Tarea 5.1 — Configurar variables de entorno en Vercel

**Agente:** 👤 Humano  
En el dashboard de Vercel → Settings → Environment Variables:

```
NEXT_PUBLIC_MAPBOX_TOKEN       = pk.eyJ1...
NEXT_PUBLIC_DATA_BASE_URL      = https://xxx.supabase.co/storage/v1/object/public/airtrace-data
```

---

### Tarea 5.2 — Crear `webapp/vercel.json`

**Instrucción para Claude Code:**

> Crea `webapp/vercel.json`:
> ```json
> {
>   "buildCommand": "npm run build",
>   "outputDirectory": ".next",
>   "framework": "nextjs"
> }
> ```
> Y en `vercel.json` de la raíz del repo (si no existe, créalo):
> ```json
> { "rewrites": [{ "source": "/(.*)", "destination": "/webapp/$1" }] }
> ```
> Alternativamente, configura Vercel para que use `webapp/` como root directory desde el dashboard (Settings → General → Root Directory → `webapp`). Eso es más limpio que reescrituras. Indica cuál de las dos opciones elegiste y por qué.

---

### Tarea 5.3 — Deploy y smoke test

**Instrucción para Claude Code:**

> ```bash
> cd webapp
> vercel --prod
> ```
> Anota la URL de producción. Luego verifica:
> ```bash
> # La app carga
> curl -I https://airtrace.vercel.app
> # → HTTP 200
>
> # Los datos del bucket son accesibles
> curl -I "https://xxx.supabase.co/storage/v1/object/public/airtrace-data/streets_annual.geojson"
> # → HTTP 200 con Content-Type: application/geo+json
> ```

**Criterio de aceptación:**
- La app carga en el browser sin errores de consola
- El mapa muestra Liverpool con tramos coloreados
- El slider de meses funciona y los colores cambian

---

## Fase 6 — Validación Manual en Browser

**Duración estimada:** 30–60 minutos  
**Agente:** 👤 Humano

```
CHECKLIST COMPLETO
──────────────────
Mapa base
  [ ] Tramos coloreados en toda la red viaria de Liverpool
  [ ] Zoom in/out funciona sin degradar colores
  [ ] Click en tramo → InfoCard con nombre, score, PM2.5, PM10
  [ ] InfoCard cierra con ×

Slider de meses
  [ ] "Anual" seleccionado por defecto
  [ ] Seleccionar "Ene" → mapa más rojo (invierno)
  [ ] Seleccionar "Jul" → mapa más verde (verano)
  [ ] Diferencia visual clara entre enero y julio

Gráfico EDA
  [ ] 12 puntos visibles (Ene–Dic)
  [ ] Líneas WHO y UK 2040 son visibles
  [ ] Enero tiene valor mayor que julio
  [ ] Click en punto → sincroniza con slider del mapa

Eventos canónicos
  [ ] En mes "Nov" → marker Bonfire Night visible en el mapa
  [ ] En mes "Ago" → marker ola de calor visible
  [ ] Evento COVID visible en todos los meses (es contexto histórico)
  [ ] Click en marker → popup con título y descripción

Vista LSOA
  [ ] Toggle "Barrios (LSOA)" → capa coroplética visible
  [ ] Click en LSOA → InfoCard con nombre del barrio y PM2.5 medio
  [ ] Toggle "Calles" → vuelve a la vista de tramos

Móvil (DevTools emulación iPhone 12, 390px)
  [ ] Panel lateral se colapsa o adapta (no bloquea el mapa)
  [ ] Touch funciona para click en tramos
```

---

## Fase 7 — Post-deploy: Features v1.1 (Brainstorm pendiente)

Estas features están definidas en `Analisis.md §12` pero no son necesarias para el primer deploy.

| Feature | Tarea | Agente | Pre-condición |
|---------|-------|--------|---------------|
| Comparativa de LSOAs (selección múltiple) | Añadir multi-select en vista LSOA + panel comparativo | 🤖 general | Fase 6 completa |
| Buscador por dirección (Nominatim) | Componente `SearchBar.tsx` + geocoding | 🤖 general | Fase 6 completa |
| Noticias en tiempo real (RSS Liverpool Echo) | Fetch RSS de noticias relacionadas con aire/tráfico, parsear y mostrar como eventos dinámicos | 📐 Plan primero | API RSS accesible |
| Exportar área como informe PDF | Selección de zona en el mapa → PDF con estadísticas | 📐 Plan primero | Fase 6 completa |

---

## Resumen de Dependencias

```
Fase 0 (datos)
  ├── 0.1 generate_monthly_geojsons.py
  │     └── 0.2 verificar estacionalidad ──┐
  └── 0.3 events.json (paralelo)           │
                                           ▼
Fase 1 (cuentas)                    Fase 2 (scaffold)
  ├── 1.1 bucket Supabase                  │
  ├── 1.3 upload script ──────────────────┐│
  ├── 1.2 subir archivos ←────────────────┘│
  └── 1.4 token Mapbox ──────────────────┘│
                                          ▼
                               Fase 3 (componentes mapa)
                                 3.1 ScoreBadge
                                 3.2 InfoCard
                                 3.3 MapView ────────────┐
                                 3.4 EventsLayer ────────┐│
                                                         ││
                               Fase 4 (panel)            ││
                                 4.1 MonthSlider          ││
                                 4.2 TimeseriesChart      ││
                                 4.3 SidePanel ───────────┤│
                                 4.4 page.tsx ←───────────┘│
                                                           │
                               Fase 5 (deploy)            │
                                 5.1 env vars             │
                                 5.2 vercel.json ←────────┘
                                 5.3 deploy + smoke test
                                          │
                               Fase 6 (validación manual)
```

---

## Duración Total Estimada

| Fase | Duración |
|------|----------|
| 0 — Datos mensuales | 3–4 h |
| 1 — Cuentas | 1–2 h |
| 2 — Scaffold | 1–2 h |
| 3 — Componentes mapa | 1–2 días |
| 4 — Panel lateral | 1 día |
| 5 — Deploy | 1–2 h |
| 6 — Validación | 30 min |
| **Total** | **~4–5 días** |

---

_Versión 2.0 · Reemplaza PROCEDIMIENTO_MVP v1.0 (arquitectura API comercial)_  
_Referencia técnica: `mvp/TECHNICAL_SPEC.md` v0.2.0_
