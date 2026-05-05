# Story 1.4: Loading Overlay y Spinner Global

Status: done

## Story

As a user,
I want to see a loading indicator while the map data is being fetched,
So that I know the app is working and not frozen.

## Acceptance Criteria

1. **Given** la app iniciando carga, **When** `isLoading === true` en el store Zustand, **Then** se muestra un overlay semitransparente con un spinner animado y el texto "Cargando mapa de Liverpool..." centrado sobre el área del mapa
2. **Given** el overlay visible, **When** `isLoading` cambia a `false`, **Then** el overlay desaparece con una animación fade-out (150 ms)
3. **Given** el overlay visible, **When** se revisa con un lector de pantalla, **Then** existe un elemento `role="status"` con `aria-live="polite"` que anuncia el estado de carga
4. **Given** el overlay visible, **When** el usuario intenta hacer Tab, **Then** el foco no puede entrar al overlay (inert o pointer-events-none)

## Tasks / Subtasks

- [x] Task 1 — Crear `src/components/LoadingOverlay.tsx` (AC: 1, 2, 3, 4)
  - [x] Componente que lee `isLoading` directamente de `useAppStore` (NO prop-drilling)
  - [x] Overlay: `absolute inset-0 z-50 flex items-center justify-center bg-background/80`
  - [x] Spinner SVG animado con `animate-spin` (Tailwind) — círculo de 40px
  - [x] Texto: "Cargando mapa de Liverpool..." con `text-text-muted text-sm mt-3`
  - [x] Fade-out: `transition-opacity duration-150` + `opacity-0 pointer-events-none` cuando `!isLoading`
  - [x] `role="status"` + `aria-live="polite"` en el contenedor del mensaje (AC: 3)
  - [x] `pointer-events-none` cuando `!isLoading`, `aria-hidden={!isLoading}` (AC: 4)

- [x] Task 2 — Montar `LoadingOverlay` en el área del mapa en `App.tsx` (AC: 1)
  - [x] `<LoadingOverlay />` dentro del `<main>` (que ya tiene `relative` de Story 1.3)

- [x] Task 3 — Inicializar `isLoading = true` en el store para demostrar el overlay (AC: 1, 2)
  - [x] `useEffect` en App.tsx: `setIsLoading(true)` al montar, `setIsLoading(false)` tras 2s
  - [x] Comentario `// TODO Story 2.1: reemplazar con carga real de Mapbox`

- [x] Task 4 — Verificar compilación (AC: 1–4)
  - [x] `npx tsc --noEmit` ✅ sin errores
  - [x] `npm run build` ✅ 284ms sin errores

### Review Findings

- [x] [Review][Defer] `pointer-events-none` no bloquea foco keyboard si se añaden elementos interactivos al overlay en el futuro [src/components/LoadingOverlay.tsx] — deferred, sin focusable children actualmente; usar `inert` attribute si se añade un botón cancelar

## Dev Notes

### Estructura del Componente

```tsx
// src/components/LoadingOverlay.tsx
import useAppStore from '../store/useAppStore'

export default function LoadingOverlay() {
  const isLoading = useAppStore(s => s.isLoading)

  return (
    <div
      className={[
        'absolute inset-0 z-50 flex flex-col items-center justify-center',
        'bg-background/80 transition-opacity duration-150',
        isLoading ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
      ].join(' ')}
      aria-hidden={!isLoading}
    >
      {/* Spinner SVG */}
      <svg
        className="animate-spin h-10 w-10 text-accent"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12" cy="12" r="10"
          stroke="currentColor" strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>

      {/* Texto accesible */}
      <p
        className="text-text-muted text-sm mt-3"
        role="status"
        aria-live="polite"
      >
        {isLoading ? 'Cargando mapa de Liverpool...' : ''}
      </p>
    </div>
  )
}
```

### Montaje en App.tsx

```tsx
// En el <main> de App.tsx — añadir LoadingOverlay junto al placeholder
<main className="flex-1 relative bg-background min-h-0 flex items-center justify-center" role="main">
  <LoadingOverlay />
  <p className="text-text-muted text-sm">Mapa — Story 2.1</p>
</main>
```

### Simulación Temporal en App.tsx

```tsx
// Al inicio de App() — TEMPORAL, Story 2.1 lo reemplazará
const setIsLoading = useAppStore(s => s.setIsLoading)

useEffect(() => {
  setIsLoading(true)
  const t = setTimeout(() => setIsLoading(false), 2000)
  return () => clearTimeout(t)
}, [setIsLoading])
```

### Token `text-accent` para el Spinner

El color del spinner usa `text-accent` = `#3b82f6` (blue-500), definido en `@theme` en `index.css`. Consistente con el focus ring de los botones.

### `bg-background/80` — Fondo Semitransparente

Tailwind v4 soporta la sintaxis `color/opacity`. `bg-background/80` = `#0f1117` con 80% opacidad. El usuario sigue viendo el contenido debajo (cuando haya mapa real), lo que evita la pantalla en blanco.

### Fade-out — Diseño Elegante sin `unmount`

En lugar de unmount abrupto con `{isLoading && <LoadingOverlay />}`, el componente permanece en el DOM pero con `opacity-0 pointer-events-none` cuando no está cargando. Esto:
1. Permite la animación CSS `transition-opacity duration-150`
2. Evita parpadeos al re-montar
3. El `aria-hidden={!isLoading}` oculta el contenido a lectores de pantalla cuando no está activo

### Dependencia de Story 1.3

El `<main>` ya tiene `relative` desde Story 1.3 — crítico para que `absolute inset-0` del overlay funcione correctamente. No cambiar esa clase.

### Contexto de Stories Siguientes

- **Story 2.1**: eliminará el `setTimeout` simulacro y llamará `setIsLoading(true)` al iniciar fetch de Mapbox y `setIsLoading(false)` cuando `map.on('load')` se dispare
- **Story 1.4 NO implementa** el spinner inline del slider thumb (16px) — eso es Story 3.2 (`MonthSlider`)

### Referencias

- FR-06: spinner + texto "Cargando mapa de Liverpool..." durante carga inicial
- UX Spec → Loading States: "Carga inicial: spinner centrado"
- AR-02: `isLoading` centralizado en `useAppStore`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `tsc --noEmit` ✅ sin salida
- `npm run build` ✅ 284ms

### Completion Notes List

- ✅ `LoadingOverlay` lee `isLoading` del store via selector — sin prop-drilling
- ✅ `bg-background/80` fade con `transition-opacity duration-150`
- ✅ `aria-hidden`, `role="status"`, `aria-live="polite"` — WCAG compliant
- ✅ `pointer-events-none` cuando oculto — foco pasa al mapa correctamente
- ✅ Simulación 2s en App.tsx con `// TODO Story 2.1` para reemplazo futuro

### File List

- `src/components/LoadingOverlay.tsx` (creado)
- `src/App.tsx` (modificado — import + useEffect simulación + LoadingOverlay montado)
