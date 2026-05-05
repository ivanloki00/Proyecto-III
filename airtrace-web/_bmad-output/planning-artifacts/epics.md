---
stepsCompleted: [1, 2, 3, 4]
status: complete
completedAt: '2026-04-20'
inputDocuments:
  - docs/PRD_webapp_v1.1.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# AirTrace Web — Epic Breakdown

## Overview

Este documento descompone los requisitos del PRD, arquitectura y especificación UX de AirTrace en epics y stories implementables para el Developer agent.

## Requirements Inventory

### Functional Requirements

FR-01: El mapa carga centrado en Liverpool (zoom 12, estilo Mapbox dark-v11) con los 8.450 tramos de calle coloreados en < 3.000 ms desde caché vacía con conexión ≥ 20 Mbps.
FR-02: La capa `streets-line` contiene exactamente 8.450 features con campos `pm25_annual`, `pm10_annual`, `score` y `road_type` no nulos.
FR-03: Los tramos se colorean con la escala fija A–F: A < 5 µg/m³ `#00c864` · B 5–10 `#c8e632` · C 10–15 `#ffc800` · D 15–20 `#ff8200` · E 20–25 `#e63232` · F ≥ 25 `#960096`.
FR-04: Leyenda A–F fija en esquina inferior derecha del mapa, siempre visible, no colapsable en desktop.
FR-05: Grosor de línea adaptativo: 1–2 px en zoom ≤ 13, 3–4 px en zoom ≥ 15.
FR-06: Spinner + texto "Cargando mapa de Liverpool..." visible durante la carga inicial.
FR-07: Slider con 13 posiciones (Anual + Ene…Dic); posición por defecto es Anual (carga `liverpool_pollution_map.geojson`).
FR-08: Al cambiar de mes el mapa hace cross-fade < 500 ms sin ningún frame en blanco; la capa anterior permanece hasta que la nueva emite `sourcedata` con `isSourceLoaded === true`.
FR-09: El botón del mes seleccionado muestra indicador de loading durante el fetch.
FR-10: Bajo el slider aparece línea de contexto meteorológico del mes activo: `<Mes> 2024 · Temp. media: X °C · Viento: X m/s · Días de lluvia: N` leída de `monthly_stats.json`.
FR-11: Los botones de mes se colorean sutilmente con la paleta A–F según el PM2.5 medio del mes.
FR-12: Transición de slider < 1.000 ms en primera carga (sin caché); < 150 ms en caché en memoria.
FR-13: Panel EDA — Gráfico 3A: línea mensual con PM2.5 (azul) y PM10 (naranja), línea roja punteada OMS (5 µg/m³) y naranja punteada UK 2040 (10 µg/m³), área sombreada entre PM2.5 y referencia OMS.
FR-14: Sincronización bidireccional: cambiar el slider mueve el punto activo del gráfico 3A; click en punto del gráfico mueve el slider.
FR-15: Tooltip en gráfico 3A muestra `PM2.5 = X,X µg/m³ · ×N sobre OMS` al hover.
FR-16: Gráfico 3B: barras horizontales de PM2.5 medio por tipo de vía (primary / secondary / residential / other), coloreadas con paleta A–F, actualizadas al cambiar de mes en < 500 ms.
FR-17: Gráfico 3C: top 5 tramos más contaminados del mes activo, ordenados descendentemente. Click en fila → `flyTo` al tramo con zoom ≥ 15 y resaltado durante ≥ 2 s.
FR-18: Contador 3D: tres números derivados en runtime del GeoJSON activo: total tramos (8.450), tramos > OMS, tramos > UK 2040. Se actualizan al cambiar de mes.
FR-19: Markers de eventos en mapa visibles únicamente si el mes del evento coincide con el mes activo del slider.
FR-20: El evento `covid_context` es siempre visible en el mapa independientemente del mes activo.
FR-21: Click en marker de evento → popup con título (≤ 40 car.), fecha en formato `D de <mes> YYYY` y descripción (50–300 car., sin jerga técnica).
FR-22: Iconos de tipo de evento bajo el eje X del gráfico 3A; hover → tooltip con título + descripción corta.
FR-23: Los datos de eventos se cargan desde `events.json` (fichero pendiente de generación con el pipeline Python).
FR-24: Toggle `Calles / Barrios` que alterna entre capa `streets-line` y capa `lsoa-fill` sin recargar la página.
FR-25: Capa LSOA: 302 polígonos con `fill-opacity = 0.7` y borde blanco fino, misma escala A–F.
FR-26: En vista Barrios, el slider de meses queda deshabilitado con tooltip: "La vista por barrios usa datos anuales (2024). Cambia a vista por calles para explorar la estacionalidad."
FR-27: Click en polígono LSOA → InfoCard con nombre del LSOA, barrio, score, PM2.5 medio anual y posición en ranking ("Posición: #N de 302 barrios").
FR-28: Click en tramo de calle → InfoCard flotante (esquina inferior izquierda) con road_type, score, PM2.5, PM10, multiplicadores OMS (×N) y UK 2040 (×N).
FR-29: Click fuera de cualquier feature → InfoCard desaparece con fade-out 150 ms.
FR-30: InfoCard se actualiza al cambiar el mes activo sin cerrar ni reabrir el elemento DOM.
FR-31: Si `name == null` en el GeoJSON, el título de la InfoCard se renderiza como `Calle sin nombre · <road_type>` (nunca "null" ni "undefined").
FR-32: InfoCard aparece con fade-in 150 ms; se reubica a esquina inferior derecha si el click ocurre en la inferior izquierda.

### NonFunctional Requirements

NFR-01: Carga inicial del mapa < 3.000 ms hasta mapa con 8.450 tramos renderizado. Condición: conexión ≥ 20 Mbps, caché vacía, percentil 95. Método: Performance API + DevTools Network throttle.
NFR-02: Transición slider (primera carga) < 1.000 ms desde click hasta primer frame con datos del mes. Método: `performance.now()` en evento `sourcedata` isSourceLoaded === true.
NFR-03: Transición slider (caché) < 150 ms desde click hasta render completo. Método: Performance API.
NFR-04: Actualización panel EDA < 500 ms para gráficos 3B y 3C al cambiar de mes.
NFR-05: InfoCard < 150 ms desde click hasta card visible.
NFR-06: Conformidad WCAG 2.1 AA en todos los componentes interactivos.
NFR-07: Contraste de color: ratio ≥ 4.5:1 para texto sobre colores de la paleta A–F (WCAG 1.4.3).
NFR-08: Todos los controles operables sin ratón (Tab + Enter/Space) (WCAG 2.1.1).
NFR-09: Lighthouse Accessibility ≥ 90 en desktop y móvil.
NFR-10: Navegadores soportados: Chrome 120+, Firefox 120+, Edge 120+, Safari 17+.
NFR-11: Funcional en viewport ≥ 320 px de ancho.
NFR-12: Sin autenticación: ninguna funcionalidad requiere login, API key ni sesión.
NFR-13: Uptime ≥ 99% mensual durante el período de evaluación CAZ 2026.
NFR-14: Latencia CDN < 200 ms desde UK.
NFR-15: GeoJSONs en Supabase Storage accesibles públicamente sin token (bucket público).

### Additional Requirements

- AR-01: Stack base — React 19 + Vite 6 + TypeScript 5 usando `create-vite react-ts` como starter. Epic 1 Story 1 debe bootstrapear el proyecto con este comando exacto.
- AR-02: Estado global con Zustand 5 — un único store `useAppStore` con slices: `{ activeMonth, setActiveMonth, cache: Map<MonthKey, FeatureCollection>, setCache, isLoading, error }`.
- AR-03: Supabase Storage bucket configurado con `Content-Encoding: br` (Brotli) y `Cache-Control: public, max-age=31536000, immutable` antes del primer deploy que use datos mensuales.
- AR-04: Web Worker `geojson-parser.worker.ts` — `JSON.parse` en worker con `postMessage` + `Transferable ArrayBuffer` para no bloquear hilo principal durante parse de GeoJSONs de 6–8 MB.
- AR-05: Prefetch en background de los 12 GeoJSONs mensuales usando `requestIdleCallback` tras el primer paint del mapa anual (ADR-001 optimización 2).
- AR-06: `map.getSource('pollution-source').setData(fc)` en lugar de `removeLayer`/`addLayer` para preservar tile cache interno de Mapbox (ADR-001 opt. 5).
- AR-07: Variables de entorno requeridas: `VITE_MAPBOX_TOKEN`, `VITE_SUPABASE_URL`. Archivo `.env.example` en repo; `.env.local` gitignoreado.
- AR-08: CI/CD — GitHub Actions workflow `.github/workflows/ci.yml` que ejecuta typecheck + build en cada PR. Auto-deploy a Vercel Hobby desde rama `main`.
- AR-09: Estructura de carpetas: `src/features/{map,eda,events,lsoa}/`, `src/components/`, `src/store/`, `src/workers/`, `src/hooks/`, `src/utils/`, `src/types/`.
- AR-10: ⚠️ DEPENDENCIA CRÍTICA — Los ficheros `liverpool_pollution_2024-MM.geojson` (×12), `monthly_stats.json` y `events.json` NO existen aún. Deben generarse con el pipeline Python antes de que las Epics 3, 4 y partes de la Epic 5 puedan desarrollarse. Epic 1 puede completarse independientemente.

### UX Design Requirements

UX-DR-01: Layout D1 Dark Split — dashboard de vista única con CSS Flexbox: `[mapa flex:1] [panel 340px]`. Background global `#0F1117`, surface `#1A1D27`, border `#2D3142`.
UX-DR-02: Escala de color de contaminación del PRD (FR-03) como CSS custom properties en `tailwind.config.ts`: `--score-a: #00c864`, `--score-b: #c8e632`, `--score-c: #ffc800`, `--score-d: #ff8200`, `--score-e: #e63232`, `--score-f: #960096`.
UX-DR-03: Instalar shadcn/ui CLI y copiar componentes: `Slider`, `Tabs`, `Badge`, `Separator`, `Tooltip`. Base de Radix UI garantiza WCAG AA en todos los interactivos.
UX-DR-04: Tipografía — `Inter` variable font. Datos numéricos con `font-variant-numeric: tabular-nums` (`font-mono` Tailwind).
UX-DR-05: `InfoCard` custom — 4 estados: oculto, loading, data, error. `role="complementary"`, `aria-live="polite"`. Cierre con tecla Esc (WCAG 2.1 criterion 1.4.13).
UX-DR-06: `MonthSlider` — wrapper de shadcn Slider con etiquetas Ene…Dic. `aria-valuetext="<Mes> 2024"`. Spinner de 16 px inline en el thumb durante carga.
UX-DR-07: Panel lateral con `Tabs` (shadcn/ui): pestaña EDA, pestaña LSOA, pestaña Eventos. Tab activo `border-bottom: 2px solid #3b82f6`.
UX-DR-08: Responsive — 3 breakpoints Tailwind: `md:768px` panel colapsable (cerrado por defecto), `lg:1024px` layout D1 completo, `xl:1280px` panel expandible a 400 px.
UX-DR-09: WCAG AA checklist de implementación: `focus-visible:ring-2 ring-blue-500` en todos los interactivos · touch targets mínimo 44×44 px (`min-h-11 min-w-11`) · segunda señal no-color en badges (icono ⚠ + texto además de color) · `aria-label` en mapa (`role="application"`).
UX-DR-10: Leyenda de contaminación flotante sobre el mapa (no en panel separado), posición bottom-left, nunca se solapa con InfoCard.

## FR Coverage Map

FR-01: Epic 2 — Mapa centrado Liverpool, zoom 12, dark-v11, 8.450 tramos < 3.000 ms
FR-02: Epic 2 — 8.450 features con pm25_annual, pm10_annual, score, road_type no nulos
FR-03: Epic 2 — Escala A–F colores fijos (#00c864…#960096)
FR-04: Epic 2 — Leyenda A–F fija inferior derecha, siempre visible
FR-05: Epic 2 — Grosor línea adaptativo (1–2 px zoom ≤ 13 / 3–4 px zoom ≥ 15)
FR-06: Epic 1 — Spinner + texto "Cargando mapa de Liverpool..."
FR-07: Epic 3 — Slider 13 posiciones (Anual + Ene…Dic), default Anual
FR-08: Epic 3 — Cross-fade < 500 ms sin frame en blanco (sourcedata isSourceLoaded)
FR-09: Epic 3 — Loading indicator inline en botón del mes activo
FR-10: Epic 3 — Línea contexto meteorológico desde monthly_stats.json
FR-11: Epic 3 — Botones mes coloreados con paleta A–F según PM2.5 medio
FR-12: Epic 3 — Transición < 1.000 ms primera carga / < 150 ms en caché
FR-13: Epic 4 — Gráfico 3A: línea PM2.5/PM10 + refs OMS/UK + área sombreada
FR-14: Epic 4 — Sincronización bidireccional slider ↔ punto activo gráfico 3A
FR-15: Epic 4 — Tooltip gráfico 3A: PM2.5 = X,X µg/m³ · ×N sobre OMS
FR-16: Epic 4 — Gráfico 3B: barras horizontales PM2.5 por tipo de vía
FR-17: Epic 4 — Gráfico 3C: top 5 tramos + flyTo zoom ≥ 15 + resaltado ≥ 2 s
FR-18: Epic 4 — Contador 3D: total tramos / tramos > OMS / tramos > UK 2040
FR-19: Epic 6 — Markers eventos visibles solo si mes coincide con mes activo
FR-20: Epic 6 — Evento covid_context siempre visible (independiente del mes)
FR-21: Epic 6 — Popup evento: título ≤ 40 car., fecha D de <mes> YYYY, descripción
FR-22: Epic 6 — Iconos eventos bajo eje X gráfico 3A con tooltip
FR-23: Epic 6 — Datos desde events.json (pipeline Python)
FR-24: Epic 5 — Toggle Calles / Barrios sin recargar página
FR-25: Epic 5 — Capa LSOA 302 polígonos fill-opacity 0.7, borde blanco, escala A–F
FR-26: Epic 5 — Slider deshabilitado en vista Barrios con tooltip explicativo
FR-27: Epic 5 — Click LSOA → InfoCard con nombre, barrio, score, PM2.5, ranking
FR-28: Epic 2 — Click calle → InfoCard flotante con road_type, score, PM2.5, PM10, ×OMS, ×UK
FR-29: Epic 2 — Click fuera de feature → InfoCard fade-out 150 ms
FR-30: Epic 3 — InfoCard actualiza datos al cambiar mes sin cerrar/reabrir DOM
FR-31: Epic 2 — name==null → "Calle sin nombre · road_type" (nunca null/undefined)
FR-32: Epic 2 — InfoCard fade-in 150 ms + reubicación si click en esquina inferior izquierda

## Epic List

### Epic 1: Scaffold Desplegable
Los desarrolladores y evaluadores pueden acceder a la app desde una URL pública con layout dark D1, shell responsive, estado global inicializado y pipeline CI/CD funcionando.
**FRs cubiertos:** FR-06
**ARs cubiertos:** AR-01, AR-02, AR-07, AR-08, AR-09
**UX-DRs cubiertos:** UX-DR-01, UX-DR-02, UX-DR-03, UX-DR-04, UX-DR-08, UX-DR-09
**NFRs cubiertos:** NFR-10, NFR-11, NFR-12

### Epic 2: Mapa Anual de Calidad del Aire
Los usuarios pueden explorar el mapa de Liverpool con 8.450 tramos de calle coloreados en escala A–F, ver la leyenda, y obtener detalles de cualquier tramo haciendo click en la InfoCard.
**FRs cubiertos:** FR-01, FR-02, FR-03, FR-04, FR-05, FR-28, FR-29, FR-31, FR-32
**UX-DRs cubiertos:** UX-DR-05, UX-DR-10
**NFRs cubiertos:** NFR-01, NFR-05, NFR-07

### Epic 3: Exploración Mensual (Slider Temporal)
Los usuarios pueden navegar entre los 12 meses de 2024, ver cómo cambia la contaminación con transiciones fluidas, y consultar el contexto meteorológico de cada mes.
**FRs cubiertos:** FR-07, FR-08, FR-09, FR-10, FR-11, FR-12, FR-30
**ARs cubiertos:** AR-03, AR-04, AR-05, AR-06
**UX-DRs cubiertos:** UX-DR-06
**NFRs cubiertos:** NFR-02, NFR-03
**⚠️ Bloqueado por AR-10:** requiere 12 GeoJSONs mensuales + monthly_stats.json del pipeline Python

### Epic 4: Panel EDA — Análisis de Contaminación
Los usuarios pueden analizar tendencias de contaminación con un gráfico de líneas mensual, barras por tipo de vía, ranking de los 5 tramos más contaminados, y contadores de cumplimiento OMS/UK.
**FRs cubiertos:** FR-13, FR-14, FR-15, FR-16, FR-17, FR-18
**UX-DRs cubiertos:** UX-DR-07
**NFRs cubiertos:** NFR-04
**⚠️ Datos mensuales:** funcionalidad completa requiere Epic 3 completado

### Epic 5: Vista por Barrios (LSOA)
Los usuarios pueden alternar entre la vista de calles y la vista de barrios para comparar la calidad del aire a nivel de LSOA, con InfoCard de detalle y ranking.
**FRs cubiertos:** FR-24, FR-25, FR-26, FR-27

### Epic 6: Contexto de Eventos Históricos
Los usuarios pueden ver marcadores en el mapa de eventos que impactaron la calidad del aire en Liverpool, con popups descriptivos e iconos integrados en el gráfico de líneas.
**FRs cubiertos:** FR-19, FR-20, FR-21, FR-22, FR-23
**⚠️ Bloqueado por AR-10:** requiere events.json del pipeline Python

---

## Epic 1: Scaffold Desplegable

Los desarrolladores y evaluadores pueden acceder a la app desde una URL pública con layout dark D1, shell responsive, estado global inicializado y pipeline CI/CD funcionando.

### Story 1.1: Bootstrap del Proyecto y CI/CD

As a developer,
I want the project bootstrapped with the exact tech stack and CI/CD configured,
So that the team can start coding with a deployable base from day one.

**Acceptance Criteria:**

**Given** un repositorio vacío en GitHub
**When** se ejecuta `npm create vite@latest airtrace-web -- --template react-ts`
**Then** el proyecto compila sin errores con `npm run build`
**And** se instalan Tailwind v4 (`@tailwindcss/vite`), Zustand 5, Mapbox GL JS, Recharts 2.x y shadcn/ui CLI
**And** existe `.env.example` con `VITE_MAPBOX_TOKEN` y `VITE_SUPABASE_URL`
**And** `.env.local` está en `.gitignore`
**And** existe `.github/workflows/ci.yml` que ejecuta typecheck + build en cada PR
**And** el auto-deploy a Vercel Hobby desde rama `main` está configurado

### Story 1.2: Estructura de Carpetas y Tipos Globales

As a developer,
I want the folder structure and global TypeScript types in place,
So that all subsequent stories can reference consistent file paths and shared types.

**Acceptance Criteria:**

**Given** el proyecto bootstrappeado de Story 1.1
**When** se crea la estructura de directorios
**Then** existen los directorios `src/features/{map,eda,events,lsoa}/`, `src/components/`, `src/store/`, `src/workers/`, `src/hooks/`, `src/utils/`, `src/types/`
**And** `src/types/geojson.ts` exporta `interface FeatureProps`, `type MonthKey` y `interface PollutionFeature`
**And** `src/types/store.ts` exporta los tipos del store Zustand
**And** `src/store/useAppStore.ts` implementa `{ activeMonth, setActiveMonth, cache: Map<MonthKey, FeatureCollection>, setCache, isLoading, error }`
**And** todos los tipos pasan `tsc --noEmit` sin errores

### Story 1.3: Layout D1 Dark y Shell Responsive

As a user,
I want to see the dark dashboard layout with map area and side panel,
So that I can orient myself in the app before any data loads.

**Acceptance Criteria:**

**Given** la app cargada en el navegador
**When** el viewport es ≥ 1024px (breakpoint `lg`)
**Then** el layout muestra `[mapa flex:1] [panel lateral 340px]` en Flexbox
**And** el background global es `#0F1117`, surface `#1A1D27`, borde `#2D3142`
**And** las custom properties CSS `--score-a: #00c864` … `--score-f: #960096` están definidas en `tailwind.config.ts`
**And** la fuente Inter variable está cargada con `font-variant-numeric: tabular-nums` en elementos numéricos
**When** el viewport es entre 768px y 1023px (`md`)
**Then** el panel lateral está colapsado por defecto
**When** el viewport es < 768px
**Then** el layout sigue siendo funcional y usable (no se rompe)
**And** todos los elementos interactivos tienen `focus-visible:ring-2 ring-blue-500` y touch targets ≥ 44×44px

### Story 1.4: Loading Overlay y Spinner Global

As a user,
I want to see a loading indicator while the map data is being fetched,
So that I know the app is working and not frozen.

**Acceptance Criteria:**

**Given** la app iniciando carga
**When** `isLoading === true` en el store
**Then** se muestra el spinner con texto "Cargando mapa de Liverpool..." centrado sobre el mapa
**When** `isLoading === false`
**Then** el spinner desaparece con fade-out

---

## Epic 2: Mapa Anual de Calidad del Aire

Los usuarios pueden explorar el mapa de Liverpool con 8.450 tramos de calle coloreados en escala A–F, ver la leyenda, y obtener detalles de cualquier tramo haciendo click en la InfoCard.

### Story 2.1: Mapa Mapbox con Tramos de Calle Anuales

As a user,
I want to see Liverpool's streets rendered on a dark map with colour-coded pollution levels,
So that I can immediately understand the air quality distribution across the city.

**Acceptance Criteria:**

**Given** la app cargada con `VITE_MAPBOX_TOKEN` configurado
**When** el mapa inicializa
**Then** el mapa se centra en Liverpool (lat 53.41, lng -2.978, zoom 12) con estilo `mapbox://styles/mapbox/dark-v11`
**And** el mapa tiene `role="application"` y `aria-label="Mapa de calidad del aire de Liverpool"`
**When** el GeoJSON anual `liverpool_pollution_map.geojson` termina de cargar
**Then** la capa `streets-line` muestra exactamente 8.450 features con los campos `pm25_annual`, `pm10_annual`, `score` y `road_type` no nulos
**And** el tiempo total desde carga vacía hasta mapa renderizado es < 3.000 ms en conexión ≥ 20 Mbps (NFR-01)
**And** el grosor de línea es 1–2 px en zoom ≤ 13 y 3–4 px en zoom ≥ 15 (FR-05)

### Story 2.2: Escala de Color A–F en Tramos de Calle

As a user,
I want streets coloured by their pollution grade,
So that I can visually identify the most polluted areas at a glance.

**Acceptance Criteria:**

**Given** la capa `streets-line` cargada
**When** el mapa renderiza los tramos
**Then** los tramos se colorean según la escala fija: A `#00c864` (< 5 µg/m³), B `#c8e632` (5–10), C `#ffc800` (10–15), D `#ff8200` (15–20), E `#e63232` (20–25), F `#960096` (≥ 25)
**And** el color se aplica mediante `match` expression de Mapbox sobre el campo `score`
**And** el ratio de contraste de texto sobre cada color de la paleta es ≥ 4.5:1 (NFR-07)
**And** `src/utils/colorScale.ts` exporta la función `getScoreColor(score: string): string` reutilizable

### Story 2.3: Leyenda A–F Flotante sobre el Mapa

As a user,
I want a permanent legend showing what each colour grade means,
So that I can interpret the map without prior knowledge of the scale.

**Acceptance Criteria:**

**Given** el mapa renderizado
**When** el viewport es ≥ 1024px (desktop)
**Then** la leyenda A–F es visible en la esquina inferior izquierda del mapa, nunca colapsable
**And** muestra las 6 entradas: letra de grado + rango µg/m³ + swatch de color
**And** la leyenda no se solapa con la InfoCard (UX-DR-10)
**When** la InfoCard está visible en esquina inferior izquierda
**Then** la leyenda se desplaza o la InfoCard aparece en esquina inferior derecha (FR-32)

### Story 2.4: InfoCard de Tramo de Calle

As a user,
I want to click on any street segment and see its pollution details,
So that I can investigate specific locations and understand their health impact.

**Acceptance Criteria:**

**Given** la capa `streets-line` cargada y visible
**When** el usuario hace click en un tramo de calle
**Then** la InfoCard aparece en < 150 ms con fade-in de 150 ms (NFR-05, FR-32)
**And** la InfoCard muestra: nombre de la calle (o "Calle sin nombre · `road_type`" si `name == null`, FR-31), `road_type`, grado (score A–F), PM2.5, PM10, multiplicador OMS (×N), multiplicador UK 2040 (×N)
**And** la InfoCard tiene `role="complementary"` y `aria-live="polite"` (UX-DR-05)
**And** si el click ocurre en la mitad inferior izquierda, la InfoCard se posiciona en esquina inferior derecha; en caso contrario, en inferior izquierda (FR-32)
**When** el usuario pulsa Esc o hace click fuera de cualquier feature
**Then** la InfoCard desaparece con fade-out de 150 ms (FR-29, UX-DR-05)

---

## Epic 3: Exploración Mensual (Slider Temporal)

Los usuarios pueden navegar entre los 12 meses de 2024, ver cómo cambia la contaminación con transiciones fluidas, y consultar el contexto meteorológico de cada mes.

### Story 3.1: Web Worker y Caché en Memoria para GeoJSONs

As a developer,
I want GeoJSON parsing offloaded to a Web Worker with an in-memory cache,
So that month transitions never block the UI thread and cached months swap instantly.

**Acceptance Criteria:**

**Given** un GeoJSON mensual de 6–8 MB disponible en Supabase Storage (bucket público con Brotli + `Cache-Control: public, max-age=31536000, immutable`)
**When** se solicita un mes por primera vez
**Then** `useMonthData.ts` hace `fetch()` del GeoJSON y transfiere el `ArrayBuffer` al worker `geojson-parser.worker.ts` via `postMessage` con `Transferable`
**And** el worker ejecuta `JSON.parse` y devuelve el `FeatureCollection` al hilo principal
**And** el resultado se almacena en `useAppStore.cache` (`Map<MonthKey, FeatureCollection>`)
**When** el mismo mes se solicita de nuevo
**Then** se devuelve directamente desde `cache.get(month)` sin ningún fetch ni parse
**And** el tiempo de swap desde caché es < 150 ms (NFR-03)

### Story 3.2: Componente MonthSlider

As a user,
I want a slider with month labels to select the time period,
So that I can intuitively navigate through the year with keyboard or mouse.

**Acceptance Criteria:**

**Given** el mapa anual cargado
**When** el componente `MonthSlider` se renderiza
**Then** muestra 13 posiciones: "Anual" + "Ene" "Feb" … "Dic"
**And** la posición por defecto es "Anual" (carga `liverpool_pollution_map.geojson`)
**And** cada posición tiene `aria-valuetext="<Mes> 2024"` (o "Datos anuales 2024" para Anual)
**And** el thumb muestra un spinner de 16 px inline mientras `isLoading === true`
**And** el componente es operable con Tab + flechas de teclado (NFR-08)
**And** el botón del mes activo durante fetch muestra un indicador de carga inline (FR-09)

### Story 3.3: Transición de Mes con Cross-Fade

As a user,
I want the map to update smoothly when I change month,
So that I never see a blank map during the transition.

**Acceptance Criteria:**

**Given** el mapa renderizado con datos de un mes
**When** el usuario selecciona un mes diferente en el slider
**Then** se llama a `map.getSource('pollution-source').setData(fc)` con el nuevo FeatureCollection (AR-06, nunca `removeLayer`/`addLayer`)
**And** la capa anterior permanece visible hasta que el nuevo source emite `sourcedata` con `isSourceLoaded === true` (FR-08)
**And** la transición tiene `line-opacity-transition` de 400 ms (cross-fade, FR-08)
**And** no hay ningún frame completamente en blanco durante la transición
**And** el tiempo desde click hasta primer frame con datos del mes (primera carga sin caché) es < 1.000 ms (NFR-02)
**And** `useAppStore.setActiveMonth(month)` se llama al confirmar la carga completada

### Story 3.4: Contexto Meteorológico y Botones Coloreados

As a user,
I want to see weather context and colour-coded month buttons,
So that I can understand environmental factors that influence pollution readings.

**Acceptance Criteria:**

**Given** `monthly_stats.json` cargado con datos de los 12 meses
**When** el mes activo cambia
**Then** debajo del slider aparece: `<Mes> 2024 · Temp. media: X °C · Viento: X m/s · Días de lluvia: N` (FR-10)
**And** cada botón de mes se colorea con la paleta A–F según el PM2.5 medio del mes leído de `monthly_stats.json` (FR-11)
**And** los colores de los botones se aplican con opacidad reducida (sutil) para no interferir con la legibilidad del texto

### Story 3.5: InfoCard Actualiza Datos al Cambiar Mes

As a user,
I want the street detail card to update when I change month without closing,
So that I can track how pollution changes on a specific street across months.

**Acceptance Criteria:**

**Given** una InfoCard abierta mostrando datos de un tramo de calle
**When** el usuario cambia el mes activo en el slider
**Then** la InfoCard actualiza sus valores de PM2.5, PM10, score y multiplicadores OMS/UK con los datos del nuevo mes
**And** el elemento DOM de la InfoCard no se cierra ni reabre durante la actualización (FR-30)
**And** si el tramo seleccionado no tiene datos en el mes activo, la InfoCard muestra un estado de error descriptivo

### Story 3.6: Prefetch en Background de los 12 Meses

As a user,
I want the app to silently pre-load all months after the initial map renders,
So that all subsequent month transitions feel instant.

**Acceptance Criteria:**

**Given** el mapa anual renderizado (primer paint completado)
**When** el navegador entra en estado idle (`requestIdleCallback`)
**Then** se inician los fetch de los 12 GeoJSONs mensuales en background en paralelo (AR-05)
**And** cada GeoJSON fetcheado se parsea en el Web Worker y se almacena en `useAppStore.cache`
**And** el prefetch no bloquea ni retrasa ninguna interacción del usuario (prioridad mínima)
**And** si un prefetch falla, el error se silencia y el mes se carga bajo demanda cuando el usuario lo seleccione

---

## Epic 4: Panel EDA — Análisis de Contaminación

Los usuarios pueden analizar tendencias de contaminación con un gráfico de líneas mensual, barras por tipo de vía, ranking de los 5 tramos más contaminados, y contadores de cumplimiento OMS/UK.

### Story 4.1: Gráfico 3A — Serie Temporal PM2.5/PM10

As a user,
I want to see a monthly line chart of PM2.5 and PM10 with reference thresholds,
So that I can understand Liverpool's annual pollution trend and its distance from health targets.

**Acceptance Criteria:**

**Given** el panel EDA abierto en la pestaña correspondiente (`Tabs` shadcn/ui con `border-bottom: 2px solid #3b82f6` en tab activo)
**When** se renderiza el gráfico 3A
**Then** muestra dos líneas: PM2.5 en azul y PM10 en naranja sobre el eje Y, con los 12 meses en el eje X
**And** una línea roja punteada en 5 µg/m³ (límite OMS) y una naranja punteada en 10 µg/m³ (UK 2040)
**And** el área entre la línea PM2.5 y la referencia OMS está sombreada con opacidad reducida
**When** el usuario hace hover sobre un punto del gráfico
**Then** el tooltip muestra `PM2.5 = X,X µg/m³ · ×N sobre OMS` (FR-15)
**And** el gráfico está implementado con Recharts y es accesible vía teclado (NFR-06)

### Story 4.2: Sincronización Bidireccional Slider ↔ Gráfico 3A

As a user,
I want the chart and the month slider to stay in sync,
So that I always see the chart highlight matching whichever month is active on the map.

**Acceptance Criteria:**

**Given** el gráfico 3A visible y el MonthSlider activo
**When** el usuario mueve el slider a un mes
**Then** el punto activo del gráfico 3A se resalta en el mes correspondiente en < 500 ms (NFR-04)
**When** el usuario hace click en un punto del gráfico 3A
**Then** `useAppStore.setActiveMonth(month)` se llama con el mes clickeado
**And** el slider se mueve a la posición del mes clickeado
**And** el mapa carga los datos del nuevo mes (FR-14)

### Story 4.3: Gráfico 3B — PM2.5 por Tipo de Vía

As a user,
I want to see average PM2.5 broken down by road type,
So that I can understand which kinds of streets are most polluted in the active month.

**Acceptance Criteria:**

**Given** el GeoJSON del mes activo cargado en memoria
**When** se renderiza el gráfico 3B
**Then** muestra barras horizontales con PM2.5 medio para: `primary`, `secondary`, `residential`, `other`
**And** cada barra se colorea con la paleta A–F según el valor PM2.5 medio del tipo de vía
**When** el mes activo cambia
**Then** el gráfico 3B se actualiza con los nuevos valores en < 500 ms (NFR-04, FR-16)

### Story 4.4: Gráfico 3C — Top 5 Tramos Más Contaminados

As a user,
I want to see the five most polluted street segments for the active month,
So that I can investigate the worst hotspots and fly to them on the map.

**Acceptance Criteria:**

**Given** el GeoJSON del mes activo cargado
**When** se renderiza el gráfico 3C
**Then** muestra los 5 tramos con mayor PM2.5, ordenados descendentemente, con nombre (o "Calle sin nombre") y valor PM2.5
**When** el usuario hace click en una fila del ranking
**Then** el mapa ejecuta `flyTo` al tramo con zoom ≥ 15
**And** el tramo queda resaltado visualmente durante ≥ 2 segundos (FR-17)
**And** la actualización al cambiar de mes ocurre en < 500 ms (NFR-04)

### Story 4.5: Contador 3D — Cumplimiento OMS y UK 2040

As a user,
I want to see at a glance how many streets exceed health thresholds,
So that I can quickly gauge the overall air quality situation in the active month.

**Acceptance Criteria:**

**Given** el GeoJSON del mes activo cargado
**When** se renderiza el contador 3D
**Then** muestra tres números derivados en runtime: total tramos (8.450), tramos con PM2.5 > 5 µg/m³ (> OMS), tramos con PM2.5 > 10 µg/m³ (> UK 2040)
**And** los números usan `font-variant-numeric: tabular-nums` para evitar saltos de layout
**When** el mes activo cambia
**Then** los tres contadores se actualizan en < 500 ms (NFR-04, FR-18)

---

## Epic 5: Vista por Barrios (LSOA)

Los usuarios pueden alternar entre la vista de calles y la vista de barrios para comparar la calidad del aire a nivel de LSOA, con InfoCard de detalle y ranking.

### Story 5.1: Capa LSOA con Escala A–F

As a user,
I want to see Liverpool's 302 neighbourhoods coloured by pollution grade,
So that I can understand air quality at a neighbourhood level using the same scale as the street view.

**Acceptance Criteria:**

**Given** el archivo `lur_lsoa_predictions.geojson` disponible (existe en `outputs/maps/`)
**When** la capa LSOA se inicializa
**Then** `LsoaLayer.tsx` añade la fuente `lsoa-source` y la capa `lsoa-fill` a Mapbox con `fill-opacity: 0.7` y borde blanco fino (`line-width: 0.5`)
**And** los 302 polígonos se colorean con la misma escala A–F del PRD (`#00c864`…`#960096`) basada en el score anual
**And** la capa está inicialmente invisible (no interfiere con la vista de calles por defecto)

### Story 5.2: Toggle Calles / Barrios

As a user,
I want a toggle to switch between street-level and neighbourhood-level views,
So that I can choose the level of detail that's most relevant to my analysis.

**Acceptance Criteria:**

**Given** el mapa en vista de calles (por defecto)
**When** el usuario activa el toggle "Barrios"
**Then** la capa `streets-line` se oculta y la capa `lsoa-fill` se hace visible, sin recargar la página (FR-24)
**And** el MonthSlider queda deshabilitado con cursor `not-allowed`
**And** al hacer hover sobre el slider deshabilitado aparece tooltip: "La vista por barrios usa datos anuales (2024). Cambia a vista por calles para explorar la estacionalidad." (FR-26)
**When** el usuario vuelve al toggle "Calles"
**Then** la capa `lsoa-fill` se oculta y `streets-line` vuelve a ser visible
**And** el MonthSlider se reactiva con el mes que estaba activo antes del cambio

### Story 5.3: InfoCard de Barrio (LSOA)

As a user,
I want to click on a neighbourhood polygon and see its pollution details and ranking,
So that I can compare how my area performs relative to the rest of Liverpool.

**Acceptance Criteria:**

**Given** la vista de barrios activa
**When** el usuario hace click en un polígono LSOA
**Then** la InfoCard muestra: nombre del LSOA, nombre del barrio (`neighbourhood`), grado (score A–F), PM2.5 medio anual y posición en ranking ("Posición: #N de 302 barrios") (FR-27)
**And** la InfoCard aparece con fade-in 150 ms y tiene `role="complementary"` y `aria-live="polite"`
**When** el usuario hace click fuera de cualquier polígono o pulsa Esc
**Then** la InfoCard desaparece con fade-out 150 ms

---

## Epic 6: Contexto de Eventos Históricos

Los usuarios pueden ver marcadores de eventos que impactaron la calidad del aire en Liverpool, con popups descriptivos e iconos integrados en el gráfico de líneas.

### Story 6.1: Carga de Eventos y Markers en el Mapa

As a user,
I want to see map markers for historical events that affected air quality,
So that I can understand the context behind pollution spikes or drops.

**Acceptance Criteria:**

**Given** `events.json` disponible en Supabase Storage
**When** la app carga
**Then** `EventMarkers.tsx` fetcha `events.json` y añade un marker Mapbox por cada evento
**When** el mes activo cambia
**Then** solo son visibles los markers cuyo campo `month` coincide con el mes activo (FR-19)
**And** el evento con `type: "covid_context"` es siempre visible independientemente del mes activo (FR-20)
**And** si `events.json` no está disponible, el mapa sigue funcionando sin markers (degradación graceful)

### Story 6.2: Popup de Evento con Detalle

As a user,
I want to click on an event marker and read what happened and when,
So that I can understand why pollution levels changed in a particular month.

**Acceptance Criteria:**

**Given** un marker de evento visible en el mapa
**When** el usuario hace click en el marker
**Then** se muestra un popup Mapbox con: título (≤ 40 caracteres), fecha en formato `D de <mes> YYYY` (p.ej. "3 de marzo 2020") y descripción (50–300 caracteres, sin jerga técnica) (FR-21)
**And** el popup es accesible con teclado (Tab + Enter) y tiene contraste ≥ 4.5:1
**When** el usuario hace click fuera del popup o pulsa Esc
**Then** el popup se cierra

### Story 6.3: Iconos de Eventos en Gráfico 3A

As a user,
I want to see event icons below the time series chart,
So that I can visually connect pollution changes to specific historical events.

**Acceptance Criteria:**

**Given** el gráfico 3A renderizado y `events.json` cargado
**When** se renderiza el eje X del gráfico
**Then** aparecen iconos de tipo de evento debajo del eje X en el mes correspondiente a cada evento
**When** el usuario hace hover sobre un icono
**Then** aparece un tooltip con el título del evento y su descripción corta (FR-22)
**And** los iconos usan una segunda señal no-color (forma + texto) además del color para cumplir WCAG AA (NFR-06)
