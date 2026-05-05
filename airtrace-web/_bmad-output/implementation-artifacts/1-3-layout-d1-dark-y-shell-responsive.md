# Story 1.3: Layout D1 Dark y Shell Responsive

Status: done

## Story

As a user,
I want to see the dark dashboard layout with map area and side panel,
So that I can orient myself in the app before any data loads.

## Acceptance Criteria

1. **Given** la app cargada en el navegador, **When** el viewport es ≥ 1024px (`lg`), **Then** el layout muestra `[mapa flex:1] [panel lateral 340px]` en Flexbox horizontal
2. **Given** el viewport ≥ 1024px, **When** se inspeccionan los colores, **Then** background global es `#0F1117`, surface `#1A1D27`, borde `#2D3142`
3. **Given** el proyecto compilado, **When** se inspeccionan los tokens de color en `tailwind.config.ts`, **Then** existen `score-a … score-f` (ya presentes desde Story 1.1 — no recrcar)
4. **Given** el proyecto en browser, **When** se inspeccionan los estilos del body, **Then** la fuente Inter variable está cargada (Google Fonts CDN en `index.html`) y `.tabular-nums` aplica `font-variant-numeric: tabular-nums`
5. **Given** el viewport entre 768px y 1023px (`md`), **When** carga la página, **Then** el panel lateral está colapsado (oculto) por defecto
6. **Given** el viewport `md`, **When** el usuario hace click en el botón toggle del panel, **Then** el panel se muestra/oculta correctamente
7. **Given** el viewport < 768px, **When** carga la página, **Then** el layout es funcional (no overflow horizontal, mapa ocupa todo el ancho disponible)
8. **Given** todos los elementos interactivos (botón toggle panel), **When** se navega con teclado (Tab + Enter/Space), **Then** tienen `focus-visible:ring-2 ring-blue-500` visible y touch target mínimo 44×44px

## Tasks / Subtasks

- [x] Task 1 — Actualizar `index.html` (AC: 4)
  - [x] Cambiar `<title>vite-temp</title>` → `<title>AirTrace</title>`
  - [x] Añadir Inter variable font desde Google Fonts CDN antes del cierre de `</head>`

- [x] Task 2 — Crear `src/components/SidePanel.tsx` (AC: 1, 2, 5, 6)
  - [x] Componente que recibe `isOpen: boolean` y `onToggle: () => void` como props
  - [x] `w-[340px] shrink-0 bg-surface border-l border-border overflow-y-auto`
  - [x] Visible siempre en `lg:flex`, oculto por defecto en md/sm — controlado via prop `isOpen`
  - [x] `xl:w-[400px]` para viewports ≥ 1280px
  - [x] `aria-label="Panel de análisis"` en el `<aside>`
  - [x] Placeholder de contenido con `text-text-muted` (Stories 4+ añadirán el contenido real)

- [x] Task 3 — Actualizar `src/App.tsx` con el layout shell completo (AC: 1, 2, 5, 6, 7, 8)
  - [x] Importar `useState` de React
  - [x] Estado `isPanelOpen: boolean` inicializado a `false` (colapsado por defecto en md)
  - [x] Topbar con logo + botón toggle
  - [x] Botón toggle solo visible en `lg:hidden`, `min-h-11 min-w-11`, `focus-visible:ring-2`, `aria-label` dinámico, `aria-expanded`
  - [x] `<main role="main" className="flex-1 relative bg-background min-h-0">` con placeholder
  - [x] `<SidePanel isOpen={isPanelOpen} ...>` con panel siempre visible en lg+

- [x] Task 4 — Verificar todos los breakpoints y compilación (AC: 1–8)
  - [x] `npx tsc --noEmit` sin errores
  - [x] `npm run build` ✅ 301ms sin errores

## Dev Notes

### ⚠️ NO recrear tokens de color — ya existen

Los tokens `score-a…score-f` y `background`, `surface`, `border` ya están en `tailwind.config.ts` y `src/index.css` desde Story 1.1. **No tocar.** El AC 3 es una verificación, no una tarea de implementación.

### Inter Font — Google Fonts CDN (index.html)

```html
<!-- index.html — añadir en <head> antes de </head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900&display=swap" rel="stylesheet">
```

La fuente ya está referenciada en `src/index.css` como `--font-sans: "Inter", system-ui, sans-serif` y aplicada en `body { font-family: "Inter", system-ui, sans-serif }`. Solo falta cargarla.

### Layout Shell — Estructura exacta

```tsx
// src/App.tsx
import { useState } from 'react'
import SidePanel from './components/SidePanel'

function App() {
  const [isPanelOpen, setIsPanelOpen] = useState(false)

  return (
    <div className="flex flex-col min-h-screen bg-background text-text-primary">
      {/* Topbar */}
      <header className="h-12 shrink-0 flex items-center px-4 bg-surface border-b border-border">
        <span className="font-semibold text-text-primary">AirTrace</span>
        {/* Toggle solo visible en <lg */}
        <button
          className="ml-auto lg:hidden min-h-11 min-w-11 flex items-center justify-center
                     rounded text-text-muted hover:text-text-primary
                     focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
          onClick={() => setIsPanelOpen(o => !o)}
          aria-label={isPanelOpen ? 'Cerrar panel de análisis' : 'Abrir panel de análisis'}
          aria-expanded={isPanelOpen}
        >
          ☰
        </button>
      </header>

      {/* Body: mapa + panel */}
      <div className="flex flex-1 overflow-hidden">
        <main
          className="flex-1 relative bg-background min-h-0 flex items-center justify-center"
          role="main"
        >
          {/* Story 2.1 montará PollutionMap aquí */}
          <p className="text-text-muted text-sm">Mapa — Story 2.1</p>
        </main>

        <SidePanel isOpen={isPanelOpen} onToggle={() => setIsPanelOpen(o => !o)} />
      </div>
    </div>
  )
}

export default App
```

### SidePanel — Visibilidad por breakpoint

```tsx
// src/components/SidePanel.tsx
interface SidePanelProps {
  isOpen: boolean
  onToggle: () => void
}

export default function SidePanel({ isOpen }: SidePanelProps) {
  return (
    <aside
      className={[
        'w-[340px] xl:w-[400px] shrink-0',
        'bg-surface border-l border-border overflow-y-auto flex-col',
        // lg+: siempre visible como flex
        // <lg: visible solo si isOpen
        isOpen ? 'flex lg:flex' : 'hidden lg:flex',
      ].join(' ')}
      aria-label="Panel de análisis"
    >
      {/* Contenido añadido por Stories 4.x — placeholder por ahora */}
      <div className="p-4">
        <p className="text-text-muted text-sm">Panel lateral — Story 4.x</p>
      </div>
    </aside>
  )
}
```

### Patrón de Clases WCAG para Elementos Interactivos

Todos los botones y controles interactivos del proyecto deben usar este patrón:
```
focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none rounded
```
Y touch targets: `min-h-11 min-w-11` (= 44px con `1rem = 16px`).

### Tokens Tailwind en uso en esta story

| Token | Valor | Uso |
|-------|-------|-----|
| `bg-background` | `#0f1117` | fondo global, área del mapa |
| `bg-surface` | `#1a1d27` | topbar + panel lateral |
| `border-border` | `#2d3142` | separador topbar + borde panel |
| `text-text-primary` | `#f0f2f7` | texto principal |
| `text-text-muted` | `#8b92a9` | placeholders |
| `ring-blue-500` | `#3b82f6` | focus ring WCAG |

### `<main>` y `overflow-hidden`

El contenedor `flex flex-1 overflow-hidden` en el body es CRÍTICO para que el mapa Mapbox (Story 2.1) ocupe exactamente el espacio disponible sin causar scroll. `min-h-0` en el `<main>` evita que Flexbox ignore la restricción de altura. Sin esto, Mapbox no tendrá dimensiones correctas.

### Contexto de Stories Siguientes

- **Story 1.4**: leerá `isLoading` del store y montará el `LoadingOverlay` dentro del área del mapa (`<main>`)
- **Story 2.1**: reemplazará el placeholder del `<main>` con `<PollutionMap />`
- **Stories 4.x**: añadirán `<Tabs>` (shadcn/ui) dentro de `<SidePanel>` con paneles EDA/LSOA/Eventos

### shadcn/ui — NO inicializar en esta story

`npx shadcn@latest init` sigue pendiente de acción manual del usuario (requiere TTY interactivo). Esta story NO usa componentes shadcn — solo Tailwind nativo. Cuando el usuario ejecute `npx shadcn@latest init`, las historias futuras podrán importar `Tabs`, `Badge`, etc.

### Referencias

- UX-DR-01: layout D1 Dark Split `[mapa flex:1] [panel 340px]`
- UX-DR-03: responsive breakpoints md/lg/xl
- UX-DR-09: WCAG AA — focus-visible:ring-2, touch targets 44×44px
- NFR-06, NFR-08: WCAG 2.1 AA keyboard operability

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `tsc --noEmit` ✅ sin salida
- `npm run build` ✅ 301ms — index.html 0.72kB (incluye Inter font links)

### Completion Notes List

- ✅ `index.html` — título "AirTrace" + Inter variable font (Google Fonts CDN)
- ✅ `src/components/SidePanel.tsx` — panel 340px, colapsable md, aria-label
- ✅ `src/App.tsx` — layout D1: topbar + mapa flex:1 + SidePanel, toggle WCAG
- ✅ `overflow-hidden` + `min-h-0` en main para preparar Mapbox GL (Story 2.1)

### File List

- `index.html` (modificado — título + Inter font links)
- `src/App.tsx` (modificado — layout shell completo)
- `src/components/SidePanel.tsx` (creado)

### Review Findings

- [x] [Review][Patch] `onToggle` prop declarada en `SidePanelProps` pero nunca usada dentro del componente [src/components/SidePanel.tsx] — FIXED: eliminada de props e interfaz
- [x] [Review][Patch] Colores hardcodeados `text-[#f0f2f7]` y `text-[#8b92a9]` — usar tokens `text-text-primary` y `text-text-muted` [src/App.tsx, src/components/SidePanel.tsx] — FIXED
- [x] [Review][Patch] `lang="en"` en index.html — la app es en español, usar `lang="es"` [index.html] — FIXED
- [x] [Review][Defer] `favicon.svg` referenciado en index.html pero no existe en public/ — 404 silencioso en consola [index.html] — deferred, pre-existing desde scaffold Story 1.1; añadir favicon en sprint de pulido
