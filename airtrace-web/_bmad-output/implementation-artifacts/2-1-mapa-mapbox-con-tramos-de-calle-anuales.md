# Story 2.1: Mapa Mapbox con Tramos de Calle Anuales

Status: done

## Story

As a user,
I want to see Liverpool's streets rendered on a dark map with colour-coded pollution levels,
So that I can immediately understand the air quality distribution across the city.

## Acceptance Criteria

1. **Given** la app cargada con `VITE_MAPBOX_TOKEN` configurado, **When** el mapa inicializa, **Then** el mapa se centra en Liverpool (`center: [-2.978, 53.41]`, `zoom: 12`) con estilo `mapbox://styles/mapbox/dark-v11`
2. **Given** el mapa inicializado, **When** se revisa el DOM, **Then** el contenedor del mapa tiene `role="application"` y `aria-label="Mapa de calidad del aire de Liverpool"`
3. **Given** `VITE_SUPABASE_URL` configurado, **When** el GeoJSON anual `liverpool_pollution_map.geojson` termina de cargar, **Then** la fuente `pollution-source` y la capa `streets-line` están añadidas al mapa con los 8.450 features
4. **Given** la capa `streets-line` cargada, **When** se inspecciona cualquier feature, **Then** los campos `pm25_annual`, `pm10_annual`, `score` y `road_type` no son nulos
5. **Given** la capa renderizada, **When** el zoom es ≤ 13, **Then** el grosor de línea es 1–2 px; **When** el zoom es ≥ 15, **Then** el grosor de línea es 3–4 px (interpolación Mapbox)
6. **Given** la app iniciando carga, **When** el fetch del GeoJSON está en progreso, **Then** el `LoadingOverlay` existente está visible (`isLoading === true`); **When** `map.on('load')` se dispara y el GeoJSON está añadido, **Then** `isLoading` se pone a `false`
7. **Given** `VITE_MAPBOX_TOKEN` presente, **When** el mapa carga desde caché vacía en conexión ≥ 20 Mbps, **Then** el tiempo hasta mapa renderizado es < 3.000 ms (NFR-01)

## Tasks / Subtasks

- [x] Task 1 — Eliminar simulación temporal en `App.tsx` (AC: 6)
  - [x] Eliminar el `useEffect` con `setTimeout` de 2s marcado `// TODO Story 2.1`
  - [x] Eliminar el import de `useEffect` si no queda ningún otro uso
  - [x] Eliminar el placeholder `<p className="text-text-muted text-sm">Mapa — Story 2.1</p>`
  - [x] Mantener el `<LoadingOverlay />` montado — seguirá leyendo `isLoading` del store

- [x] Task 2 — Crear `src/utils/colorScale.ts` (AC: 3, 4)
  - [x] Exportar `SCORE_COLORS: Record<ScoreGrade, string>` con los 6 valores fijos del PRD
  - [x] Exportar `getScoreColor(score: ScoreGrade): string` reutilizable
  - [x] Exportar `MAPBOX_SCORE_MATCH_EXPRESSION` para usar en paint de Mapbox (array `['match', ['get', 'score'], 'A', '#00c864', ...]`)
  - [x] Los colores DEBEN ser exactamente: A `#00c864` · B `#c8e632` · C `#ffc800` · D `#ff8200` · E `#e63232` · F `#960096`
  - [x] Importar `ScoreGrade` desde `'../types/geojson'`

- [x] Task 3 — Crear `src/hooks/useMapbox.ts` (AC: 1, 2, 6)
  - [x] Hook que acepta `containerRef: React.RefObject<HTMLDivElement>` y retorna `{ map: mapboxgl.Map | null }`
  - [x] Inicializar `new mapboxgl.Map({ container, style, center: [-2.978, 53.41], zoom: 12 })` en `useEffect`
  - [x] Leer token desde `import.meta.env.VITE_MAPBOX_TOKEN` y asignarlo a `mapboxgl.accessToken` antes de new Map
  - [x] Retornar `map` via `useState<mapboxgl.Map | null>` (elegido sobre useRef para trigger reactivo)
  - [x] Cleanup: `map.remove()` en el return del useEffect
  - [x] NO gestionar isLoading aquí — lo maneja `PollutionLayer`

- [x] Task 4 — Crear `src/features/map/PollutionLayer.tsx` (AC: 3, 4, 5, 6)
  - [x] Componente que recibe `map: MapboxMap | null` como prop
  - [x] Cuando `map !== null`, registrar `map.on('load', callback)` en `useEffect`; guard `map.loaded()` para race condition
  - [x] En el callback `load`:
    - [x] Llamar `setIsLoading(true)` del store ANTES del fetch
    - [x] fetch con fallback: Supabase URL si VITE_SUPABASE_URL está definido, `/data/liverpool_pollution_map.geojson` si no
    - [x] Al resolver: añadir fuente `pollution-source` y capa `streets-line`
    - [x] Paint de color: `MAPBOX_SCORE_MATCH_EXPRESSION` cast a `ExpressionSpecification`
    - [x] Paint de grosor: interpolación `['interpolate', ['linear'], ['zoom'], 13, 1.5, 15, 3.5]`
    - [x] Tras añadir la capa: `setIsLoading(false)` y `setCache('annual', fc)`
    - [x] Error handling: catch → `setError(err.message)`, `setIsLoading(false)` en finally
  - [x] Leer `setIsLoading`, `setCache`, `setError` del store via `useAppStore` (sin prop-drilling)
  - [x] Cleanup: `removeLayer('streets-line')` + `removeSource('pollution-source')` con guards

- [x] Task 5 — Crear `src/features/map/PollutionMap.tsx` (AC: 1, 2)
  - [x] Componente contenedor: `<div ref={containerRef} className="absolute inset-0" role="application" aria-label="Mapa de calidad del aire de Liverpool" />`
  - [x] Usar `useMapbox(containerRef)` para obtener `map`
  - [x] Renderizar `<PollutionLayer map={map} />` (retorna null, solo efectos)
  - [x] El `<div>` del mapa usa `absolute inset-0` — rellena el `<main relative>` completamente
  - [x] Import `mapbox-gl/dist/mapbox-gl.css` aquí para co-localizar la dependencia CSS

- [x] Task 6 — Integrar `PollutionMap` en `App.tsx` (AC: 1, 2, 6)
  - [x] Importar y montar `<PollutionMap />` dentro del `<main>` (reemplaza el placeholder)
  - [x] Main conserva `flex-1 relative bg-background min-h-0` — eliminadas las clases de centrado del placeholder
  - [x] `<LoadingOverlay />` montado como hermano ANTES de `<PollutionMap />` (z-50 cubre el mapa)

- [x] Task 7 — Verificar compilación y tipos (AC: 1–7)
  - [x] `npx tsc --noEmit` ✅ sin errores
  - [x] `npm run build` ✅ 786ms — build exitoso (warning chunk size esperado, mapbox-gl ~1.9MB)
  - [ ] Verificar en browser que el mapa carga y los tramos son visibles (requiere .env.local con VITE_MAPBOX_TOKEN)

## Dev Notes

### Estructura de Archivos a Crear

```
src/
  utils/
    colorScale.ts               ← NUEVO
  hooks/
    useMapbox.ts                ← NUEVO
  features/
    map/
      PollutionMap.tsx          ← NUEVO (contenedor)
      PollutionLayer.tsx        ← NUEVO (datos + capas)
```

**Archivos a modificar:**
- `src/App.tsx` — eliminar useEffect de simulación, montar PollutionMap

**NO tocar:**
- `src/components/LoadingOverlay.tsx` — ya funciona correctamente
- `src/store/useAppStore.ts` — ya tiene `isLoading`, `setCache`, `setError`
- `src/types/geojson.ts` — ya tiene `ScoreGrade`, `FeatureProps`

### Variables de Entorno Requeridas

```bash
# .env.local (gitignoreado, crear localmente)
VITE_MAPBOX_TOKEN=pk.eyJ1IjoiXXX...
VITE_SUPABASE_URL=https://xxxx.supabase.co
```

La URL del GeoJSON se construye como:
```
${VITE_SUPABASE_URL}/storage/v1/object/public/geojson/liverpool_pollution_map.geojson
```

Si Supabase no está configurado aún, usar la ruta local del GeoJSON disponible en el repo:
```
../outputs/maps/liverpool_pollution_map.geojson
```
Para desarrollo local, colocar el GeoJSON en `public/data/liverpool_pollution_map.geojson` y hacer fetch a `/data/liverpool_pollution_map.geojson`.

### Mapbox GL JS v3 — API Relevante

La versión instalada es `mapbox-gl ^3.22.0`. En v3 no hay cambios breaking respecto a v2 para este caso de uso. Puntos clave:

```ts
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'  // CRÍTICO — sin esto el mapa no renderiza

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN

const map = new mapboxgl.Map({
  container: containerRef.current!,
  style: 'mapbox://styles/mapbox/dark-v11',
  center: [-2.978, 53.41],  // [lng, lat]
  zoom: 12,
})
```

**Eventos importantes:**
- `map.on('load', cb)` — se dispara cuando el estilo base está listo; añadir fuentes y capas aquí
- `map.on('error', cb)` — capturar errores de tiles

**CSS requerido:** Importar en `PollutionMap.tsx` o en `main.tsx`:
```ts
import 'mapbox-gl/dist/mapbox-gl.css'
```

### Expresión Mapbox para Grosor de Línea

```ts
'line-width': [
  'interpolate', ['linear'], ['zoom'],
  13, 1.5,   // zoom 13 → 1.5px
  15, 3.5,   // zoom 15 → 3.5px
]
```

### Expresión Mapbox para Color (desde colorScale.ts)

```ts
// src/utils/colorScale.ts
export const MAPBOX_SCORE_MATCH_EXPRESSION = [
  'match', ['get', 'score'],
  'A', '#00c864',
  'B', '#c8e632',
  'C', '#ffc800',
  'D', '#ff8200',
  'E', '#e63232',
  'F', '#960096',
  '#888888'  // fallback para score desconocido
] as const
```

### Flujo de isLoading

```
App.tsx mount
  └─ PollutionMap renderiza → useMapbox inicializa Map
       └─ PollutionLayer registra map.on('load')
            └─ 'load' dispara → setIsLoading(true) → fetch GeoJSON
                 └─ fetch resuelve → addSource + addLayer → setIsLoading(false)
```

**IMPORTANTE:** Story 1.4 dejó un `setTimeout` en App.tsx que llama `setIsLoading(true/false)`. Esta historia ELIMINA ese timeout. La gestión de `isLoading` pasa completamente a `PollutionLayer`.

### Patrón useMapbox (ciclo de vida crítico)

```ts
// src/hooks/useMapbox.ts
import { useRef, useEffect } from 'react'
import mapboxgl from 'mapbox-gl'

export function useMapbox(containerRef: React.RefObject<HTMLDivElement>) {
  const mapRef = useRef<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN

    mapRef.current = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [-2.978, 53.41],
      zoom: 12,
    })

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [containerRef])

  return { map: mapRef.current }
}
```

**Problema conocido con React 19 StrictMode:** En desarrollo, StrictMode monta/desmonta dos veces. El guard `if (!containerRef.current || mapRef.current) return` previene doble inicialización. El `return () => { mapRef.current?.remove() }` evita memory leaks.

### PollutionLayer — Patrón de Efectos

```ts
// src/features/map/PollutionLayer.tsx
useEffect(() => {
  if (!map) return

  const onLoad = async () => {
    setIsLoading(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/storage/v1/object/public/geojson/liverpool_pollution_map.geojson`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const fc = await res.json() as FeatureCollection

      map.addSource('pollution-source', { type: 'geojson', data: fc })
      map.addLayer({
        id: 'streets-line',
        type: 'line',
        source: 'pollution-source',
        paint: {
          'line-color': MAPBOX_SCORE_MATCH_EXPRESSION,
          'line-width': ['interpolate', ['linear'], ['zoom'], 13, 1.5, 15, 3.5],
          'line-opacity': 1,
        },
      })

      setCache('annual', fc)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar el mapa')
    } finally {
      setIsLoading(false)
    }
  }

  map.on('load', onLoad)

  return () => {
    // cleanup si el mapa sigue montado
    if (map.getLayer('streets-line')) map.removeLayer('streets-line')
    if (map.getSource('pollution-source')) map.removeSource('pollution-source')
  }
}, [map, setIsLoading, setCache, setError])
```

### Deferred Work Relevante de Epic 1

Del archivo `_bmad-output/implementation-artifacts/deferred-work.md`:

- **`pm25_annual`/`pm10_annual`**: Estos son los nombres de campo del GeoJSON anual — correctos para esta historia. Cuando llegue Epic 3 y los GeoJSONs mensuales del pipeline Python, confirmar si usan los mismos nombres.
- **Favicon 404**: No es bloqueante para esta historia. Ignorar el aviso en consola.

### GeoJSON Local de Fallback para Desarrollo

Si no hay `.env.local` configurado, el mapa fallará silenciosamente. Para desarrollo sin Supabase:

1. Copiar `liverpool_pollution_map.geojson` desde `../outputs/maps/` a `public/data/`
2. Hacer fetch a `/data/liverpool_pollution_map.geojson`

Alternativamente, exponer la URL como variable con fallback:
```ts
const BASE = import.meta.env.VITE_SUPABASE_URL ?? ''
const GEOJSON_URL = BASE
  ? `${BASE}/storage/v1/object/public/geojson/liverpool_pollution_map.geojson`
  : '/data/liverpool_pollution_map.geojson'
```

### Project Structure Notes

**Alineación con arquitectura:**
- `PollutionMap.tsx` y `PollutionLayer.tsx` van en `src/features/map/` — exactamente como especifica `architecture.md` sección "Project Structure & Boundaries"
- `useMapbox.ts` en `src/hooks/` — convención camelCase con `use`
- `colorScale.ts` en `src/utils/` — helpers puros, sin estado
- Layer ID `streets-line` y source ID `pollution-source` en kebab-case — convención Mapbox de `architecture.md`

**Naming seguido:**
- Componentes: PascalCase `.tsx` → `PollutionMap.tsx`, `PollutionLayer.tsx`
- Hooks: camelCase con `use` → `useMapbox.ts`
- Utils: camelCase → `colorScale.ts`

### Referencias

- FR-01: mapa centrado Liverpool, zoom 12, dark-v11, < 3.000 ms [Source: epics.md#Story 2.1]
- FR-02: 8.450 features con campos no nulos [Source: epics.md#Story 2.1]
- FR-05: grosor adaptativo zoom ≤ 13 / ≥ 15 [Source: epics.md#Story 2.1]
- AR-02: estado centralizado `useAppStore` [Source: architecture.md#State Management Patterns]
- AR-07: variables de entorno `VITE_MAPBOX_TOKEN`, `VITE_SUPABASE_URL` [Source: architecture.md#Variables de Entorno]
- AR-09: estructura de carpetas `src/features/map/` [Source: architecture.md#Project Structure]
- NFR-01: carga inicial < 3.000 ms [Source: epics.md#NonFunctional Requirements]
- Story 1.4 dev notes: `// TODO Story 2.1: reemplazar con carga real de Mapbox` [Source: 1-4-loading-overlay-y-spinner-global.md]
- Deferred: nombres de campo pm25_annual/pm10_annual [Source: deferred-work.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `npx tsc --noEmit` ✅ sin salida (0 errores)
- `npm run build` ✅ 786ms — 29 módulos transformados
- Error corregido: TS6133 en PollutionLayer — `import type mapboxgl` reemplazado por `import type { Map as MapboxMap, ExpressionSpecification }`

### Completion Notes List

- ✅ `colorScale.ts` — SCORE_COLORS, getScoreColor, MAPBOX_SCORE_MATCH_EXPRESSION con los 6 colores exactos del PRD
- ✅ `useMapbox.ts` — usa `useState` (no useRef) para trigger reactivo cuando el mapa está listo; cleanup con `map.remove()`
- ✅ `PollutionLayer.tsx` — guard `map.loaded()` previene race condition; fallback URL para desarrollo sin Supabase; finally en catch garantiza setIsLoading(false)
- ✅ `PollutionMap.tsx` — `absolute inset-0` llena el `<main relative>`; mapbox-gl CSS importado aquí
- ✅ `App.tsx` — mock setTimeout eliminado; `useEffect` eliminado; import `useEffect` e `useAppStore` eliminados; PollutionMap montado
- ✅ Sin tests — no hay framework de tests configurado (anotado en architecture.md como aceptable para demo universitario)
- ⚠️ Verificación visual en browser requiere `.env.local` con `VITE_MAPBOX_TOKEN` y `VITE_SUPABASE_URL` (o GeoJSON en `public/data/`)

### File List

- `src/utils/colorScale.ts` (creado)
- `src/hooks/useMapbox.ts` (creado)
- `src/features/map/PollutionLayer.tsx` (creado)
- `src/features/map/PollutionMap.tsx` (creado)
- `src/App.tsx` (modificado — eliminado mock, integrado PollutionMap)

### Review Findings

_Review 1 — 2026-04-28: Blind Hunter + Edge Case Hunter + Acceptance Auditor + Playwright. Bug crítico de CSS corregido. Código actualizado resolvió la mayoría de items abiertos._
_Review 2 — 2026-04-29: Blind Hunter + Edge Case Hunter + Acceptance Auditor._

- [x] [Review][Decision] AC-6 — ¿`isLoading` desde mount o solo desde fetch? → **RESUELTO: desde mount**. Inicializar `isLoading: true` en el store para que el spinner cubra toda la carga (basemap + GeoJSON). Se convierte en patch (ver siguiente ítem).
- [x] [Review][Patch] **AC-6 — `isLoading` no cubre la carga del basemap** [`src/store/useAppStore.ts`] — CORREGIDO: `isLoading` inicializado a `true` en el store. Spinner visible desde mount.
- [x] [Review][Patch] **`setIsLoading(true)` llamado antes del guard `cancelled`** [`src/features/map/PollutionLayer.tsx:43`] — CORREGIDO: `if (cancelled) return` movido a primera línea de `onLoad`.
- [x] [Review][Patch] **`removeLayer`/`removeSource` sin guard contra mapa destruido** [`src/features/map/PollutionLayer.tsx:78-85`] — CORREGIDO: cleanup envuelto en `try/catch`.
- [x] [Review][Patch] CSS conflict: contenedor del mapa con altura 0 → mapa invisible [`src/features/map/PollutionMap.tsx`] — CORREGIDO (Review 1)
- [x] [Review][Patch] Token Mapbox sin validación → CORREGIDO (`if (!token) { console.error; return }`)
- [x] [Review][Patch] Race condition `map.loaded()` vs `map.on('load')` → CORREGIDO
- [x] [Review][Patch] `addSource`/`addLayer` en mapa ya destruido → CORREGIDO (guard `if (cancelled) return` antes de `addSource`)
- [x] [Review][Patch] Error de red Supabase no cae al fallback local → CORREGIDO (`fetchGeoJSON()` con try/catch)
- [x] [Review][Patch] Fallback Supabase→local silencioso → CORREGIDO (`console.warn` en ambas rutas de error)
- [x] [Review][Patch] `setIsLoading(false)` en `finally` tras `cancelled = true` → CORREGIDO (`if (!cancelled) setIsLoading(false)`)
- [x] [Review][Patch] `MAPBOX_SCORE_MATCH_EXPRESSION` con doble cast → CORREGIDO (tipado directo como `ExpressionSpecification`)
- [x] [Review][Defer] Validación runtime de shape `FeatureCollection` (zod) — diferido, mejora robustez post-MVP
- [x] [Review][Defer] Manejo de `score` null en match expression — diferido, depende del pipeline
- [x] [Review][Defer] Sin assertion `features.length === 8450` (AC-3) — diferido, concierne a tests E2E
- [x] [Review][Defer] `aria-controls` ausente en botón hamburguesa — diferido, pre-existente de Story 1.3
- [x] [Review][Defer] `mapboxgl.accessToken` asignado en hook en lugar de `main.tsx` — diferido, sin impacto en MVP single-map
- [x] [Review][Defer] Colores duplicados en `SCORE_COLORS` y `MAPBOX_SCORE_MATCH_EXPRESSION` — diferido, DRY concern sin impacto funcional
- [x] [Review][Defer] `☰` sin `aria-hidden` en botón hamburguesa — diferido, accesibilidad post-MVP
- [x] [Review][Defer] Logs `console.warn/error` en producción — diferido, aceptable para demo universitario

