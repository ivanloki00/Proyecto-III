# Deferred Work

## Deferred from: code review of 2-3-leyenda-a-f-flotante-sobre-el-mapa (2026-04-30)

- **Arquitectura multi-capa DEBUG en PollutionLayer** — `PollutionLayer.tsx` usa 7 capas filtradas (`streets-line-A…F` + fallback) con comentario `// DEBUG: add multiple layers to test match` en vez de la capa única con `match` expression del plan original. Pre-existing de Story 2.1. Refactorizar hacia capa única con `MAPBOX_SCORE_MATCH_EXPRESSION` en un story de deuda técnica.
- **Race condition React Strict Mode en PollutionLayer** — En dev, Strict Mode ejecuta efectos dos veces; el segundo invoca `map.addSource('pollution-source')` que ya existe, lanzando error. Añadir guard `if (!map.getSource('pollution-source'))` al implementar Story 3.x o al refactorizar PollutionLayer.
- **`isLoading` atascado si `cancelled=true` mid-flight** — Si el componente desmonta mientras el fetch está en vuelo, `setIsLoading(false)` del `finally` no se ejecuta por el guard `!cancelled`. Añadir un `setIsLoading(false)` incondicional en el cleanup del efecto. Pre-existing Story 2.1.
- **Local GeoJSON fallback sin validación `hasScoreField`** — El path Supabase valida el campo `score`; el local no. Un fichero local corrupto llega a `addSource` silenciosamente. Pre-existing Story 2.1.
- **`setIsLoading(false)` no llamado cuando `map=null`** — Si el token Mapbox falta, el efecto retorna inmediatamente y `isLoading` puede quedar `true` indefinidamente. Pre-existing Story 2.1.
- **Colisión LegendOverlay/InfoCard en bottom-left** — La leyenda está fija en `bottom-4 left-4`; la InfoCard (Story 2.4) debe reposicionarse a bottom-right cuando el click ocurre en bottom-left (FR-32). Sin token o medida compartida para coordinación entre componentes. Resolver en Story 2.4.

## Deferred from: code review of 2-2-escala-de-color-a-f-en-tramos-de-calle (2026-04-29)

- **`getScoreLabel(null)` devuelve `'—'` — UX ambigua** — Cuando un tramo no tiene score clasificado, la leyenda o InfoCard mostraría `"—"` como grado. Preferible decidir un mensaje más descriptivo (`"Sin clasificar"`, `"N/D"`, etc.) al implementar Story 2.3 (leyenda) o Story 2.4 (InfoCard).
- **Sin tests para `getScoreColor(null)` y `getScoreLabel(undefined)`** — El fallback `#888888` y `'—'` no tienen cobertura automatizada. Sin framework de tests configurado (aceptado post-MVP en architecture.md).

## Deferred from: code review of 2-1-mapa-mapbox-con-tramos-de-calle-anuales (2026-04-29)

- **`mapboxgl.accessToken` asignado dentro del hook** — Asignarlo en `useMapbox` es una mutación global que puede interferir si se añaden múltiples instancias de mapa en el futuro. Mover a `main.tsx` o al entry point de la app. Sin impacto en arquitectura single-map del MVP.
- **Colores duplicados en `colorScale.ts`** — Los seis hex están hardcodeados dos veces: en `SCORE_COLORS` y en `MAPBOX_SCORE_MATCH_EXPRESSION`. Construir la expresión Mapbox derivándola de `SCORE_COLORS` para evitar drift al cambiar paleta.
- **`☰` sin `aria-hidden` en botón hamburguesa** — El carácter U+2630 en `App.tsx` puede ser anunciado por lectores de pantalla como "trigrama del cielo" aunque el botón ya tiene `aria-label`. Reemplazar con SVG o añadir `aria-hidden="true"` al carácter.
- **`console.warn`/`console.error` en producción** — Los mensajes de diagnóstico de `useMapbox` y `PollutionLayer` quedan activos en la build de producción. Eliminar o proteger con `import.meta.env.DEV` al madurar el proyecto.

## Deferred from: code review of 2-1-mapa-mapbox-con-tramos-de-calle-anuales (2026-04-28)

- **Validación runtime de shape `FeatureCollection`** — `fetchGeoJSON` castea `res.json()` directamente a `FeatureCollection` sin validación. Si el endpoint devuelve JSON malformado (ej. `{"error":"unauthorized"}`), `map.addSource` lo acepta y Mapbox falla silenciosamente. Añadir validación zod cuando se introduzca librería de schemas (probable Sprint 2).
- **Manejo de `score` null en match expression** — `MAPBOX_SCORE_MATCH_EXPRESSION` con `['get', 'score']` lanza un error de evaluación silencioso en el renderer GL si una feature trae `score: null`. Hoy `FeatureProps.score` está tipado como `ScoreGrade` (no-null), así que confiamos en el pipeline. Reabrir si Epic 3 introduce datos mensuales con calidad menor.
- **Assertion de `features.length === 8450` (AC-3)** — La AC menciona el conteo exacto pero no hay verificación runtime. Pertenece a la suite E2E de QA (Story `bmad-qa-generate-e2e-tests`).
- **`aria-controls` en botón hamburguesa de `App.tsx`** — Pre-existente de Story 1.3. Sin `aria-controls="<id-sidebar>"` el lector de pantalla no asocia el botón con el panel que despliega. Añadir cuando se trabaje accesibilidad transversalmente.

## Deferred from: code review of 1-3-layout-d1-dark-y-shell-responsive (2026-04-20)

- **favicon.svg faltante** — `index.html` referencia `/favicon.svg` pero no existe en `public/`. Genera 404 silencioso en consola del navegador. Crear un SVG mínimo del logo AirTrace en `public/favicon.svg` durante el sprint de pulido visual.

## Deferred from: code review of 1-2-estructura-de-carpetas-y-tipos-globales (2026-04-20)

- **Campo mensual en `FeatureProps`** — `pm25_annual`/`pm10_annual` son nombres de campo del GeoJSON anual. Cuando el pipeline Python genere los GeoJSONs mensuales (AR-10), confirmar si usan los mismos nombres o `pm25_monthly`/`pm10_monthly`. Actualizar `FeatureProps` y el tipo del store antes de implementar Epic 3.
- **`useAppStore` default export** — Actualmente `export default useAppStore`. Considerar cambiar a `export const useAppStore` (named export) cuando se establezca la primera importación externa, para consistencia con convenciones de hooks React.

## Deferred from: code review of 1-1-bootstrap-del-proyecto-y-ci-cd (2026-04-20)

- **Sin SPA rewrite en vercel.json** — `vercel.json` no tiene regla `rewrites` para servir `index.html` en todas las rutas. No hay React Router ahora, pero bloqueará routing cuando se añada. Añadir antes de implementar cualquier navegación client-side.
- **@types/node ^24.12.2 vs Node 20 en CI** — Los tipos de Node instalados son v24 pero el entorno CI usa Node 20. Inofensivo para SPA (no se usan APIs de Node en src/). Revisar al hacer upgrade de CI a Node 22+.
- **Dual-definition de design tokens** — Los tokens `score-a…score-f` están definidos tanto en `tailwind.config.ts` (theme.extend.colors) como en `src/index.css` (@theme). Intencional para compatibilidad con shadcn/ui CLI y plugins de editor en Tailwind v4. Consolidar en un solo lugar cuando Tailwind v4 tenga mejor soporte en tooling.
