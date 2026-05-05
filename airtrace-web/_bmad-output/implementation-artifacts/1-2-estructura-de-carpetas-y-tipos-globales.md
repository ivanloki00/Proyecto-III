# Story 1.2: Estructura de Carpetas y Tipos Globales

Status: done

## Story

As a developer,
I want the folder structure and global TypeScript types in place,
So that all subsequent stories can reference consistent file paths and shared types.

## Acceptance Criteria

1. **Given** el proyecto bootstrappeado de Story 1.1, **When** se crea la estructura de directorios, **Then** existen los directorios `src/features/{map,eda,events,lsoa}/`, `src/components/`, `src/store/`, `src/workers/`, `src/hooks/`, `src/utils/`, `src/types/`
2. **Given** la estructura creada, **When** se inspecciona `src/types/geojson.ts`, **Then** exporta `interface FeatureProps`, `type MonthKey` y `interface PollutionFeature`
3. **Given** la estructura creada, **When** se inspecciona `src/types/store.ts`, **Then** exporta los tipos del store Zustand (`AppState`, `StoreActions`)
4. **Given** la estructura creada, **When** se inspecciona `src/store/useAppStore.ts`, **Then** implementa `{ activeMonth, setActiveMonth, cache: Map<MonthKey, FeatureCollection>, setCache, isLoading, setIsLoading, error, setError }` con Zustand 5
5. **Given** todos los archivos creados, **When** se ejecuta `npx tsc --noEmit`, **Then** compila sin errores de tipo

## Tasks / Subtasks

- [x] Task 1 — Crear estructura de directorios con `.gitkeep` (AC: 1)
  - [x] Crear `src/features/map/.gitkeep`
  - [x] Crear `src/features/eda/.gitkeep`
  - [x] Crear `src/features/events/.gitkeep`
  - [x] Crear `src/features/lsoa/.gitkeep`
  - [x] Crear `src/components/.gitkeep`
  - [x] Crear `src/workers/.gitkeep`
  - [x] Crear `src/hooks/.gitkeep`
  - [x] Crear `src/utils/.gitkeep`
  - [x] Crear `src/types/.gitkeep` (la carpeta existirá por los archivos .ts — el .gitkeep no es necesario pero los archivos .ts la crearán)

- [x] Task 2 — Crear `src/types/geojson.ts` (AC: 2)
  - [x] Definir `type MonthKey = 'annual' | '2024-01' | '2024-02' | ... | '2024-12'`
  - [x] Definir `interface FeatureProps` con campos: `name: string | null`, `road_type: string`, `score: string`, `pm25_annual: number`, `pm10_annual: number`
  - [x] Definir `interface PollutionFeature extends GeoJSON.Feature<GeoJSON.Geometry, FeatureProps>`
  - [x] Exportar todos los tipos nombrados

- [x] Task 3 — Crear `src/types/store.ts` (AC: 3)
  - [x] Importar `FeatureCollection` desde `geojson`
  - [x] Importar `MonthKey` desde `./geojson`
  - [x] Definir `interface AppState` con todos los campos del store
  - [x] Definir `interface StoreActions` con todos los setters
  - [x] Exportar ambas interfaces

- [x] Task 4 — Crear `src/store/useAppStore.ts` (AC: 4)
  - [x] Importar `create` de `zustand` (Zustand 5)
  - [x] Implementar store con `create<AppState & StoreActions>()((set) => ({ ... }))` — sintaxis curried obligatoria en Zustand 5 para TS
  - [x] `activeMonth: MonthKey` inicializado a `'annual'`
  - [x] `setActiveMonth(month: MonthKey)` — `set({ activeMonth: month })`
  - [x] `cache: Map<MonthKey, FeatureCollection>` inicializado a `new Map()`
  - [x] `setCache(key: MonthKey, data: FeatureCollection)` — actualización INMUTABLE: crear nuevo `Map` con spread `new Map(state.cache).set(key, data)`
  - [x] `isLoading: boolean` inicializado a `false`
  - [x] `setIsLoading(loading: boolean)` — `set({ isLoading: loading })`
  - [x] `error: string | null` inicializado a `null`
  - [x] `setError(error: string | null)` — `set({ error })`

- [x] Task 5 — Verificar compilación TypeScript (AC: 5)
  - [x] Ejecutar `npx tsc --noEmit` sin errores
  - [x] Ejecutar `npm run build` sin errores

## Dev Notes

### ⚠️ Zustand 5 — Sintaxis Curried Obligatoria

Zustand 5 requiere la forma curried para inferencia correcta de TypeScript:

```ts
// ✅ CORRECTO (Zustand 5)
import { create } from 'zustand'

const useAppStore = create<AppState & StoreActions>()((set) => ({
  activeMonth: 'annual',
  // ...
}))

// ❌ INCORRECTO (Zustand 4 legacy — no usar)
const useAppStore = create<AppState>((set) => ({ ... }))
```

### Tipos GeoJSON — Importar desde `geojson`

El package `geojson` (tipado TypeScript) ya está disponible como dependencia transitiva de `@types/mapbox-gl`. NO instalar nada nuevo.

```ts
// src/types/geojson.ts
import type { Feature, FeatureCollection, Geometry } from 'geojson'

export type MonthKey = 'annual' | '2024-01' | '2024-02' | '2024-03' | '2024-04' |
  '2024-05' | '2024-06' | '2024-07' | '2024-08' | '2024-09' | '2024-10' |
  '2024-11' | '2024-12'

export interface FeatureProps {
  name: string | null      // puede ser null — FR-31: renderizar como "Calle sin nombre · road_type"
  road_type: string        // 'primary' | 'secondary' | 'residential' | 'other'
  score: string            // 'A' | 'B' | 'C' | 'D' | 'E' | 'F'
  pm25_annual: number
  pm10_annual: number
}

export interface PollutionFeature extends Feature<Geometry, FeatureProps> {}
```

### Tipos del Store — `src/types/store.ts`

```ts
import type { FeatureCollection } from 'geojson'
import type { MonthKey } from './geojson'

export interface AppState {
  activeMonth: MonthKey
  cache: Map<MonthKey, FeatureCollection>
  isLoading: boolean
  error: string | null
}

export interface StoreActions {
  setActiveMonth: (month: MonthKey) => void
  setCache: (key: MonthKey, data: FeatureCollection) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}
```

### Store Zustand — Actualización Inmutable del Cache

El `Map` de JavaScript es mutable. Para que Zustand detecte el cambio de estado, el setter debe crear un NUEVO `Map`:

```ts
setCache: (key, data) => set((state) => ({
  cache: new Map(state.cache).set(key, data)
})),
```

NO hacer: `state.cache.set(key, data); set({ cache: state.cache })` — Zustand no detectará el cambio.

### Directorios Vacíos — `.gitkeep`

Git no rastrea directorios vacíos. Crear un archivo `.gitkeep` vacío en cada directorio sin archivos `.ts`:
- `src/features/map/.gitkeep`
- `src/features/eda/.gitkeep`
- `src/features/events/.gitkeep`
- `src/features/lsoa/.gitkeep`
- `src/components/.gitkeep`
- `src/workers/.gitkeep`
- `src/hooks/.gitkeep`
- `src/utils/.gitkeep`

`src/types/` y `src/store/` NO necesitan `.gitkeep` porque tendrán archivos `.ts`.

### `src/assets/` Ya Existe

El directorio `src/assets/` ya fue creado por Vite scaffold (Story 1.1). NO recrear ni modificar.

### Convenciones de Nomenclatura (de Architecture.md)

| Elemento | Convención |
|----------|-----------|
| Interfaces TypeScript | `interface FeatureProps` (PascalCase) |
| Type aliases simples | `type MonthKey` (PascalCase) |
| Archivos de tipos | `camelCase.ts` — `geojson.ts`, `store.ts` |
| Store | `useAppStore.ts` (prefijo `use`) |

### Tests — Esta Story No Requiere Tests Unitarios

La story solo crea tipos TypeScript y el store. La verificación es `tsc --noEmit` + `npm run build`. No se añaden tests de componentes — eso es responsabilidad de historias con UI.

### Contexto de Stories Siguientes

- **Story 1.3** usará `useAppStore` para leer `isLoading` (spinner global)
- **Story 2.1** usará `useAppStore` para `setCache` y `activeMonth`
- **Story 4.2** añadirá `activeSegment` al store (identificado en architecture gap analysis — no implementar aquí)

### Referencias

- AR-02: [architecture.md#State Management Patterns] — store único `useAppStore`
- AR-09: [architecture.md#Project Structure] — estructura de carpetas obligatoria
- [architecture.md#Implementation Patterns] — naming conventions
- [epics.md#Story 1.2] — ACs originales

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Directorios creados con `mkdir -p` + `.gitkeep` para tracking en git
- `src/store/` creado explícitamente antes de escribir `useAppStore.ts`
- `npx tsc --noEmit` ✅ sin salida (cero errores)
- `npm run build` ✅ 272ms, sin errores

### Completion Notes List

- ✅ 8 directorios de features/components/workers/hooks/utils creados con `.gitkeep`
- ✅ `src/types/geojson.ts` — `MonthKey` (13 valores), `FeatureProps`, `PollutionFeature`
- ✅ `src/types/store.ts` — `AppState`, `StoreActions` con tipos completos
- ✅ `src/store/useAppStore.ts` — Zustand 5 curried, inicialización `'annual'`, `Map` inmutable
- ✅ `tsc --noEmit` + `npm run build` sin errores

### File List

- `src/features/map/.gitkeep` (creado)
- `src/features/eda/.gitkeep` (creado)
- `src/features/events/.gitkeep` (creado)
- `src/features/lsoa/.gitkeep` (creado)
- `src/components/.gitkeep` (creado)
- `src/workers/.gitkeep` (creado)
- `src/hooks/.gitkeep` (creado)
- `src/utils/.gitkeep` (creado)
- `src/types/geojson.ts` (creado)
- `src/types/store.ts` (creado)
- `src/store/useAppStore.ts` (creado)

### Review Findings

- [x] [Review][Patch] `score: string` sin narrowing — usar `'A' | 'B' | 'C' | 'D' | 'E' | 'F'` [src/types/geojson.ts] — FIXED: tipo `ScoreGrade`
- [x] [Review][Patch] `road_type: string` sin narrowing — usar `'primary' | 'secondary' | 'residential' | 'other'` [src/types/geojson.ts] — FIXED: tipo `RoadType`
- [x] [Review][Defer] Campo mensual no definido en `FeatureProps` (`pm25_annual` vs futuro `pm25_monthly`) [src/types/geojson.ts] — deferred, AR-10 bloquea datos mensuales; resolver cuando el pipeline Python genere los GeoJSONs mensuales
- [x] [Review][Defer] `useAppStore` default export vs named export [src/store/useAppStore.ts] — deferred, pre-existing; sin importaciones rotas aún; cambiar a `export const` cuando se establezca la primera importación externa
