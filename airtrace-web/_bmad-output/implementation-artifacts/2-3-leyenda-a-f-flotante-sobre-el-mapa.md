# Story 2.3: Leyenda A–F Flotante sobre el Mapa

Status: done

## Story

As a user,
I want a permanent legend showing what each colour grade means,
so that I can interpret the map without prior knowledge of the scale.

## Acceptance Criteria

1. **Given** el mapa renderizado, **When** el viewport es ≥ 1024px (desktop), **Then** la leyenda A–F es visible en la esquina inferior izquierda del mapa, nunca colapsable
2. **Given** la leyenda visible, **When** se inspecciona su contenido, **Then** muestra las 6 entradas en orden A→F: letra de grado + rango µg/m³ + swatch de color cuadrado
3. **Given** la leyenda renderizada, **When** se verifica el contraste WCAG, **Then** el texto de cada entrada va al lado del swatch (nunca superpuesto), cumpliendo WCAG 1.4.11 Non-text Contrast ≥ 3:1
4. **Given** la leyenda en esquina inferior izquierda, **When** la InfoCard también está visible en esquina inferior izquierda, **Then** la leyenda no se solapa con la InfoCard (UX-DR-10) — la InfoCard debe reposicionarse a la esquina inferior derecha (esto lo implementa Story 2.4; la leyenda permanece siempre en bottom-left)
5. **Given** el viewport entre 768px y 1023px (tablet), **When** se renderiza la leyenda, **Then** la leyenda sigue visible pero puede tener tamaño reducido para no interferir con el mapa

## Tasks / Subtasks

- [x] Task 1 — Crear `src/features/map/LegendOverlay.tsx`
  - [x] Importar `SCORE_GRADES`, `SCORE_COLORS`, `SCORE_THRESHOLDS` desde `'../../utils/colorScale'`
  - [x] Contenedor: `absolute bottom-4 left-4 z-10 bg-surface/90 backdrop-blur-sm border border-border rounded-lg p-3 pointer-events-none`
  - [x] `role="complementary"` con `aria-label="Leyenda de calidad del aire A–F"`
  - [x] Iterar sobre `SCORE_GRADES` (array ordenado A→F) para renderizar 6 entradas
  - [x] Cada entrada: `<div className="flex items-center gap-2 py-0.5">` con swatch + grado + umbral en spans separados
  - [x] NO usar `getScoreLabel` aquí — separar grado y umbral en spans distintos para layout limpio
  - [x] NO añadir toggle ni botón de colapso — la leyenda es siempre visible (FR-04)

- [x] Task 2 — Montar `LegendOverlay` en `PollutionMap.tsx`
  - [x] Importar `LegendOverlay` desde `'./LegendOverlay'`
  - [x] Añadir `<LegendOverlay />` como hermano de `<PollutionLayer map={map} />` dentro del `div className="absolute inset-0"`, después de `<PollutionLayer />`
  - [x] PollutionMap.tsx queda: `<div className="absolute inset-0">` → `<div ref={containerRef} ... />` → `<PollutionLayer />` → `<LegendOverlay />`

- [x] Task 3 — Verificar compilación y accesibilidad
  - [x] `npx tsc --noEmit` — 0 errores
  - [x] `npm run build` — exitoso en 1.46s (30 módulos transformados)
  - [ ] Verificar en browser que la leyenda es visible en bottom-left sobre el mapa (requiere VITE_MAPBOX_TOKEN en .env.local)
  - [ ] Verificar que la leyenda no interfiere con controles nativos de Mapbox (navigation, scale)

### Review Findings (AI) — 2026-04-30

- [x] [Review][Patch] Debug `console.log` statements en PollutionLayer.tsx eliminados [src/features/map/PollutionLayer.tsx:59-61]
- [x] [Review][Patch] `text-text-muted` → `text-text-primary` en spans de umbral (WCAG 1.4.3 contraste) [src/features/map/LegendOverlay.tsx:23]
- [x] [Review][Patch] `role="complementary"` → `role="img"` en LegendOverlay [src/features/map/LegendOverlay.tsx:6]
- [x] [Review][Defer] Arquitectura multi-capa con comentario DEBUG en PollutionLayer — pre-existing Story 2.1, no introducido por esta historia
- [x] [Review][Defer] Race condition React Strict Mode (addSource en double-invoke) en PollutionLayer — pre-existing Story 2.1
- [x] [Review][Defer] `isLoading` se queda atascado si `cancelled=true` mid-flight — pre-existing Story 2.1
- [x] [Review][Defer] Local GeoJSON fallback sin validación `hasScoreField` — pre-existing Story 2.1
- [x] [Review][Defer] `setIsLoading(false)` no llamado cuando `map=null` — pre-existing Story 2.1
- [x] [Review][Defer] Colisión InfoCard/leyenda en bottom-left — delegado a Story 2.4 por spec (FR-32)

## Dev Notes

### Contexto de la arquitectura real (PollutionLayer)

**IMPORTANTE:** La implementación actual de `PollutionLayer.tsx` NO usa una sola capa `streets-line` con `match` expression. Usa **7 capas separadas** por score:
- `streets-line-A`, `streets-line-B`, `streets-line-C`, `streets-line-D`, `streets-line-E`, `streets-line-F`
- `streets-line-fallback` (para scores null/desconocidos, color `#888888`)

Esta historia NO toca `PollutionLayer.tsx`. Solo crea el componente visual de leyenda.

### Utilidades disponibles en `src/utils/colorScale.ts`

Toda la paleta ya existe — NO reimplementar:

```ts
// Usar estas exportaciones directamente:
import { SCORE_GRADES, SCORE_COLORS, SCORE_THRESHOLDS } from '../../utils/colorScale'

SCORE_GRADES  // ['A', 'B', 'C', 'D', 'E', 'F'] — orden garantizado
SCORE_COLORS  // { A: '#00c864', B: '#c8e632', C: '#ffc800', D: '#ff8200', E: '#e63232', F: '#960096' }
SCORE_THRESHOLDS  // { A: '< 5 µg/m³', B: '5–10 µg/m³', C: '10–15 µg/m³', D: '15–20 µg/m³', E: '20–25 µg/m³', F: '≥ 25 µg/m³' }
```

### Regla WCAG para el swatch (del análisis en Story 2.2)

Los colores B, C, D tienen contraste bajo con texto blanco. La regla de implementación es:
- El swatch es un **elemento gráfico** (≥ 3×3 px) → aplica WCAG 1.4.11 Non-text Contrast ≥ 3:1 ✅ (todos superan contra `#0F1117`)
- El texto del grado y umbral va **al lado** del swatch, nunca **sobre** él
- Usar texto en `#F0F2F7` (var `text-text-primary`) y `#8B92A9` (var `text-text-muted`) — no sobre el swatch

### Conflicto FR-04 vs UX-DR-10

FR-04 dice "inferior derecha", pero **Story 2.3 y UX-DR-10 explícitamente dicen "inferior izquierda"**. Implementar **bottom-left**. La InfoCard (Story 2.4) implementará la lógica de reposicionamiento a bottom-right cuando el click caiga en la zona bottom-left (FR-32).

### Posicionamiento sobre el mapa

`PollutionMap.tsx` ya tiene `<div className="absolute inset-0">`. La leyenda debe ser un hijo absoluto dentro de ese div. La clase `z-10` es suficiente para aparecer sobre las tiles del mapa sin interferir con popups Mapbox (que usan z-index mayor).

Los controles nativos de Mapbox (NavigationControl si se añade) van por defecto en top-right / bottom-right — no hay conflicto.

### Tailwind tokens disponibles

Los tokens `text-text-primary`, `text-text-muted`, `bg-surface`, `border-border` están definidos en `src/index.css` via `@theme` de Tailwind v4 y funcionan como clases utilitarias directamente.

### Anti-patterns a evitar

- ❌ No crear un nuevo token de color para el fondo de la leyenda — usar hex directo o la variable CSS `#1A1D27`
- ❌ No usar `getScoreLabel` en la leyenda — ese helper concatena grado + umbral en un string; la leyenda necesita elementos separados para layout con gap
- ❌ No añadir ninguna lógica de estado o store — la leyenda es puramente presentacional
- ❌ No reimplementar `SCORE_COLORS` — el único source of truth es `colorScale.ts`
- ❌ No colocar la leyenda fuera del `absolute inset-0` de PollutionMap — debe estar sobre el mapa, no fuera de él

### Deferred de Story 2.2 resuelto

Story 2.2 dejó pendiente: "`getScoreLabel(null)` devolviendo `'—'`". Para la leyenda, esto no aplica porque iteramos directamente sobre `SCORE_GRADES` (no hay scores null). Story 2.4 (InfoCard) resolverá el caso null en el contexto de tramos sin score.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `npx tsc --noEmit` — 0 errores
- `npm run build` — exitoso en 1.46s (30 módulos, chunk size warning esperado por mapbox-gl ~1.9 MB)
- Error pre-existente corregido: `PollutionLayer.tsx:77` — parámetro `i` declarado pero no usado en `forEach`

### Completion Notes

- ✅ `src/features/map/LegendOverlay.tsx` creado — componente puramente presentacional, sin estado
- ✅ Itera `SCORE_GRADES` (orden garantizado A→F) usando `SCORE_COLORS` e `SCORE_THRESHOLDS` de `colorScale.ts`
- ✅ Swatch con `style={{ backgroundColor }}` (inline) — los 6 colores de la paleta no tienen clases Tailwind directas
- ✅ Texto al lado del swatch (nunca sobre él) — cumple WCAG 1.4.11
- ✅ `role="complementary"` + `aria-label` para accesibilidad
- ✅ `pointer-events-none` — la leyenda no captura clicks del mapa
- ✅ Montada en `PollutionMap.tsx` dentro del `absolute inset-0` con `z-10`
- ✅ Error pre-existente en `PollutionLayer.tsx` (parámetro `i` sin usar) corregido como parte de la verificación de build
- ⚠️ Verificación en browser pendiente (requiere `.env.local` con `VITE_MAPBOX_TOKEN`)

### File List

- `src/features/map/LegendOverlay.tsx` (nuevo)
- `src/features/map/PollutionMap.tsx` (modificado — import + `<LegendOverlay />`)
- `src/features/map/PollutionLayer.tsx` (corregido — parámetro `i` sin usar en forEach)

### Change Log

- 2026-04-30: Historia 2.3 implementada — leyenda A–F flotante en bottom-left sobre el mapa
