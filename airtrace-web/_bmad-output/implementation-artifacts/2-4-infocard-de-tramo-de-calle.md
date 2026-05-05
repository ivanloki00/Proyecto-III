# Story 2.4: InfoCard de Tramo de Calle

Status: ready-for-dev

## Story

As a user,
I want to click on any street segment and see its pollution details,
so that I can investigate specific locations and understand their health impact.

## Acceptance Criteria

1. **Given** la capa `streets-line` cargada y visible, **When** el usuario hace click en un tramo de calle, **Then** la InfoCard aparece en < 150 ms con fade-in de 150 ms (NFR-05, FR-32)
2. **Given** el click en un tramo, **When** la InfoCard se muestra, **Then** contiene: nombre de la calle (o `"Calle sin nombre · <road_type>"` si `name == null`, FR-31), `road_type`, grado de score (A–F con color), PM2.5 (µg/m³), PM10 (µg/m³), multiplicador OMS `×N.N` (pm25 / 5 µg/m³), multiplicador UK 2040 `×N.N` (pm25 / 10 µg/m³) (FR-28)
3. **Given** la InfoCard renderizada, **When** se inspecciona el DOM, **Then** tiene `role="complementary"` y `aria-live="polite"` (UX-DR-05)
4. **Given** el click en la mitad izquierda del mapa (x < anchura/2), **When** la InfoCard aparece, **Then** se posiciona en la esquina inferior derecha del mapa; en cualquier otro caso, en la esquina inferior izquierda — evitando siempre solaparse con LegendOverlay (FR-32, UX-DR-10)
5. **Given** la InfoCard visible, **When** el usuario pulsa Esc o hace click fuera de cualquier tramo de calle, **Then** la InfoCard desaparece con fade-out de 150 ms (FR-29, UX-DR-05)

---

## Tasks / Subtasks

- [ ] Task 1 — Extender el store con `activeSegment` e `infoCardCorner`
  - [ ] En `src/types/store.ts`: añadir a `AppState` los campos `activeSegment: FeatureProps | null` e `infoCardCorner: 'bottom-left' | 'bottom-right'`
  - [ ] En `src/types/store.ts`: añadir a `StoreActions` las acciones `setActiveSegment(f: FeatureProps | null): void` y `setInfoCardCorner(c: 'bottom-left' | 'bottom-right'): void`
  - [ ] En `src/store/useAppStore.ts`: inicializar `activeSegment: null` e `infoCardCorner: 'bottom-left'` e implementar sus setters
  - [ ] Verificar `npx tsc --noEmit` — 0 errores tras el cambio

- [ ] Task 2 — Añadir click handler en `PollutionMap.tsx`
  - [ ] Importar `useAppStore` y los setters `setActiveSegment`, `setInfoCardCorner`
  - [ ] Añadir un `useEffect([map])` que registre `map.on('click', handleClick)` a nivel de mapa (sin especificar capa)
  - [ ] Dentro del handler: usar `map.queryRenderedFeatures(e.point, { layers: existingLayers })` donde `existingLayers` filtra solo los IDs que existen con `map.getLayer(id)` (las 7 capas: A, B, C, D, E, F, fallback)
  - [ ] Si hay features → leer `features[0].properties as FeatureProps`, calcular `corner` y llamar `setInfoCardCorner` y `setActiveSegment`
  - [ ] Si no hay features → llamar `setActiveSegment(null)` para cerrar la InfoCard
  - [ ] Lógica de corner: si `e.point.x < map.getContainer().clientWidth / 2` → corner = `'bottom-right'`, si no → corner = `'bottom-left'`
  - [ ] Cursor: `map.on('sourcedata', () => { existingLayers.forEach(id => { map.on('mouseenter', id, setCursorPointer); map.on('mouseleave', id, resetCursor) }) })` para poner `cursor: pointer` al hacer hover sobre tramos
  - [ ] Cleanup: `map.off` para todos los listeners registrados en el `return` del useEffect

- [ ] Task 3 — Crear `src/components/InfoCard.tsx`
  - [ ] Estado: leer `activeSegment` e `infoCardCorner` desde `useAppStore`
  - [ ] Calcular `positionClass`: `infoCardCorner === 'bottom-right' ? 'bottom-4 right-4' : 'bottom-4 left-40'` (left-40 = 10rem para no solapar la leyenda de ~110px de ancho)
  - [ ] Animación: usar clase CSS con `transition-opacity duration-150` y mostrar/ocultar con `opacity-0` / `opacity-100` según `activeSegment !== null`; mantener en DOM (no condicional) para que el fade-out funcione correctamente
  - [ ] `role="complementary"` y `aria-live="polite"` en el elemento raíz
  - [ ] Nombre de calle: si `activeSegment.name == null` → `"Calle sin nombre · ${activeSegment.road_type}"`, si no → `activeSegment.name`
  - [ ] Score badge: mostrar el grado con el color correspondiente de `getScoreColor(activeSegment.score)` y el umbral de `SCORE_THRESHOLDS[activeSegment.score]`
  - [ ] Multiplicador OMS: `(activeSegment.pm25_annual / 5).toFixed(1)` con prefijo `×`
  - [ ] Multiplicador UK 2040: `(activeSegment.pm25_annual / 10).toFixed(1)` con prefijo `×`
  - [ ] Badge ⚠ Over WHO limit (rojo) si `activeSegment.pm25_annual > 15` (UX consistency pattern)
  - [ ] Hook Esc: `useEffect` con `document.addEventListener('keydown', ...)` que llame `setActiveSegment(null)` si `e.key === 'Escape'`
  - [ ] `aria-label` en el botón de cierre (X): `"Cerrar panel de información"`
  - [ ] Botón cierre con `focus-visible:ring-2 focus-visible:ring-blue-500` (WCAG 2.4.7)

- [ ] Task 4 — Montar InfoCard en `PollutionMap.tsx`
  - [ ] Importar `InfoCard` desde `'../../components/InfoCard'`
  - [ ] Añadir `<InfoCard />` dentro del `div className="absolute inset-0"`, después de `<LegendOverlay />`
  - [ ] No pasar props — InfoCard lee del store directamente

- [ ] Task 5 — Verificar compilación, tipado y regressions
  - [ ] `npx tsc --noEmit` — 0 errores
  - [ ] `npm run build` — exitoso sin errores (el chunk warning de mapbox-gl ~1.9 MB es esperado y aceptable)
  - [ ] Verificar que las historias anteriores (2.1, 2.2, 2.3) no están rotas: `LegendOverlay` sigue en bottom-left, `PollutionLayer` sigue renderizando las 7 capas sin cambios

---

## Dev Notes

### Arquitectura real de capas en PollutionLayer (CRÍTICO — no asumir una capa única)

`PollutionLayer.tsx` NO usa una sola capa `streets-line` con `match` expression. Usa **7 capas separadas** filtradas por score:

```
streets-line-A    (filter: score === 'A', color: #00c864)
streets-line-B    (filter: score === 'B', color: #c8e632)
streets-line-C    (filter: score === 'C', color: #ffc800)
streets-line-D    (filter: score === 'D', color: #ff8200)
streets-line-E    (filter: score === 'E', color: #e63232)
streets-line-F    (filter: score === 'F', color: #960096)
streets-line-fallback  (filter: score NOT in A-F, color: #888888)
```

El click handler DEBE consultar estas 7 IDs. Si alguna no existe aún (porque el GeoJSON no ha terminado de cargar), `map.getLayer(id)` devuelve undefined — filtrar los IDs existentes antes de `queryRenderedFeatures`.

### FeatureProps disponibles en el click (desde `src/types/geojson.ts`)

```ts
export interface FeatureProps {
  name: string | null      // nombre de la calle; puede ser null → usar "Calle sin nombre · <road_type>"
  road_type: RoadType      // 'primary' | 'secondary' | 'residential' | 'other'
  score: ScoreGrade        // 'A' | 'B' | 'C' | 'D' | 'E' | 'F'
  pm25_annual: number      // µg/m³ — usar para multiplicadores OMS y UK 2040
  pm10_annual: number      // µg/m³ — mostrar directamente en InfoCard
}
```

Mapbox serializa las properties de GeoJSON como strings/numbers primitivos. `name` puede ser `null` (JS) o la string `"null"` dependiendo del GeoJSON. Defensivamente: `const nombre = props.name && props.name !== 'null' ? props.name : null`.

### Cambios necesarios al store (gap arquitectural identificado en architecture.md)

Architecture validation identificó: `"activeSegment" no declarado en store — Añadir al implementar F6 [InfoCard]`. Esta historia lo implementa. Añadir a `AppState`:

```ts
// src/types/store.ts
activeSegment: FeatureProps | null
infoCardCorner: 'bottom-left' | 'bottom-right'
```

Y a `StoreActions`:
```ts
setActiveSegment: (f: FeatureProps | null) => void
setInfoCardCorner: (c: 'bottom-left' | 'bottom-right') => void
```

Importar `FeatureProps` desde `'./geojson'` en `store.ts`.

### Click handler — patrón correcto con queryRenderedFeatures

El patrón recomendado es un único handler a nivel de mapa (no layer-specific), que internamente consulta features:

```tsx
// En PollutionMap.tsx — dentro de useEffect([map, setActiveSegment, setInfoCardCorner])
const LAYER_IDS = [
  'streets-line-A', 'streets-line-B', 'streets-line-C',
  'streets-line-D', 'streets-line-E', 'streets-line-F',
  'streets-line-fallback',
]

const handleClick = (e: MapMouseEvent & { features?: MapboxGeoJSONFeature[] }) => {
  const existingLayers = LAYER_IDS.filter(id => map.getLayer(id))
  if (existingLayers.length === 0) return

  const features = map.queryRenderedFeatures(e.point, { layers: existingLayers })

  if (features.length > 0) {
    const props = features[0].properties as FeatureProps
    const isLeftHalf = e.point.x < map.getContainer().clientWidth / 2
    setInfoCardCorner(isLeftHalf ? 'bottom-right' : 'bottom-left')
    setActiveSegment(props)
  } else {
    setActiveSegment(null)
  }
}

map.on('click', handleClick)
```

Para el cursor pointer al hover: adjuntar con `map.on('sourcedata', attachCursorHandlers)` donde `attachCursorHandlers` verifica que la fuente esté cargada y adjunta mouseenter/mouseleave para las capas existentes.

### Posicionamiento InfoCard — regla de no-colisión con LegendOverlay

LegendOverlay está **siempre** en `bottom-4 left-4` con ancho de ~110px. Para evitar solapamiento:

| Click en... | InfoCard aparece en... | Clase CSS |
|-------------|------------------------|-----------|
| Mitad izquierda (x < width/2) | Esquina inferior DERECHA | `bottom-4 right-4` |
| Mitad derecha (x ≥ width/2) | Esquina inferior IZQUIERDA | `bottom-4 left-40` |

`left-40` (10rem = 160px) garantiza que InfoCard empieza a la derecha de la leyenda (~110px). No usar `left-4` cuando InfoCard va a bottom-left.

### InfoCard — animación fade-in/out 150ms

Mantener InfoCard siempre en el DOM (no usar renderizado condicional) para que el fade-out funcione:

```tsx
<div
  role="complementary"
  aria-live="polite"
  className={`absolute z-20 w-[280px] bg-surface border border-border rounded-lg shadow-lg p-4
              transition-opacity duration-150
              ${activeSegment ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}
              ${positionClass}`}
  aria-hidden={!activeSegment}
>
```

`pointer-events-none` cuando invisible para no bloquear clicks al mapa. `aria-hidden` cuando no visible para screen readers.

### Cálculo de multiplicadores OMS y UK 2040

```ts
const omsMultiplier = (props.pm25_annual / 5).toFixed(1)   // límite OMS: 5 µg/m³ (FR-13)
const ukMultiplier  = (props.pm25_annual / 10).toFixed(1)  // límite UK 2040: 10 µg/m³ (FR-13)
// Display: "×2.3 sobre OMS" / "×1.1 sobre UK 2040"
```

Badge de alerta (solo si PM2.5 > 15 µg/m³ — umbral OMS interim IT-3):
```tsx
{props.pm25_annual > 15 && (
  <span className="flex items-center gap-1 text-xs text-red-400 font-medium">
    <span>⚠</span><span>Over WHO limit</span>
  </span>
)}
```

### Utilidades disponibles en colorScale.ts (NO reimplementar)

```ts
import { getScoreColor, SCORE_THRESHOLDS } from '../utils/colorScale'

getScoreColor(score)        // '#00c864' etc — para el swatch de color del score
SCORE_THRESHOLDS[score]     // '< 5 µg/m³' etc — para el subtítulo del score
```

### Tailwind tokens disponibles (definidos en src/index.css vía @theme Tailwind v4)

```
bg-surface          → #1A1D27 (fondo de la InfoCard)
border-border       → #2D3142 (borde de la InfoCard)
text-text-primary   → #F0F2F7 (texto principal)
text-text-muted     → #8B92A9 (texto secundario — road_type, labels)
bg-background       → #0F1117 (fondo global)
```

No usar colores hex directos para estos tokens — usar las clases.

### Anti-patterns a evitar

- ❌ NO usar `map.on('click', 'streets-line', handler)` — esa capa no existe; solo existen `streets-line-A` … `streets-line-fallback`
- ❌ NO usar `innerHTML` ni `popup.setHTML()` de Mapbox para la InfoCard — es un componente React
- ❌ NO reimplementar `getScoreColor` o la paleta de colores — importar desde `colorScale.ts`
- ❌ NO usar `display: none` para ocultar la InfoCard — usar `opacity-0 pointer-events-none` para que el fade-out funcione
- ❌ NO hacer `setActiveSegment` en PollutionLayer — la lógica de click pertenece a PollutionMap o un hook en hooks/
- ❌ NO olvidar el cleanup de `map.off` en el return del useEffect — genera memory leaks
- ❌ NO mostrar `"null"` o `"undefined"` como nombre de calle — siempre validar `name` defensivamente

### Archivos a crear / modificar

| Archivo | Acción |
|---------|--------|
| `src/types/store.ts` | Modificar — añadir `activeSegment` e `infoCardCorner` a AppState y StoreActions |
| `src/store/useAppStore.ts` | Modificar — inicializar y implementar los nuevos setters |
| `src/components/InfoCard.tsx` | Crear nuevo |
| `src/features/map/PollutionMap.tsx` | Modificar — añadir useEffect de click + montar `<InfoCard />` |

No modificar `PollutionLayer.tsx` — ya está completo.

### Deferred de historias anteriores relevantes para esta historia

- Story 2.2 deferred: `getScoreLabel(null)` devuelve `'—'` — en InfoCard usar `name` directamente (no `getScoreLabel`), y manejar `score === null` con `getScoreColor(null)` que ya devuelve `'#888888'`
- Story 2.3 deferred: "Colisión InfoCard/leyenda en bottom-left" — resuelto en esta historia con `left-40` cuando InfoCard va a esquina inferior izquierda

### Referencia de FRs cubiertos

- FR-28: Click en tramo → InfoCard con road_type, score, PM2.5, PM10, ×OMS, ×UK 2040
- FR-29: Click fuera de feature → InfoCard fade-out 150 ms
- FR-31: `name == null` → `"Calle sin nombre · <road_type>"`
- FR-32: InfoCard fade-in 150 ms + reubicación si click en mitad izquierda del mapa

---

## Dev Agent Record

### Agent Model Used

(a completar por el agente)

### Debug Log References

- `npx tsc --noEmit` — esperado: 0 errores
- `npm run build` — esperado: exitoso (chunk warning mapbox-gl ~1.9 MB es pre-existente y aceptable)

### Completion Notes

(a completar por el agente)

### File List

(a completar por el agente)

### Change Log

- 2026-05-05: Historia 2.4 creada — InfoCard de tramo de calle con posicionamiento dinámico, fade-in/out y extensión del store
