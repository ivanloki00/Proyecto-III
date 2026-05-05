---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: complete
documentsUsed:
  - docs/PRD_webapp_v1.1.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# Implementation Readiness Assessment Report

**Date:** 2026-04-20
**Project:** airtrace-web

## Document Inventory

| Documento | Ruta | Tamaño | Última Modificación | Estado |
|-----------|------|--------|---------------------|--------|
| PRD | `docs/PRD_webapp_v1.1.md` | 49 KB | 2026-04-20 00:08 | ✅ Encontrado |
| PRD Validation | `docs/PRD_validation_report.md` | 22 KB | 2026-04-19 23:58 | ✅ Referencia |
| Architecture | `_bmad-output/planning-artifacts/architecture.md` | 12 KB | 2026-04-20 00:27 | ✅ Encontrado |
| Epics & Stories | `_bmad-output/planning-artifacts/epics.md` | 35 KB | 2026-04-20 01:03 | ✅ Encontrado |
| UX Design | `_bmad-output/planning-artifacts/ux-design-specification.md` | 19 KB | 2026-04-20 00:45 | ✅ Encontrado |

---

## PRD Analysis

### Functional Requirements (32 total)

| ID | Texto |
|----|-------|
| FR-01 | Mapa centrado en Liverpool (zoom 12, estilo dark-v11), 8.450 tramos coloreados en < 3.000 ms con conexión ≥ 20 Mbps, caché vacía |
| FR-02 | Capa `streets-line` contiene exactamente 8.450 features con campos `pm25_annual`, `pm10_annual`, `score` y `road_type` no nulos |
| FR-03 | Tramos coloreados con escala fija A–F: A<5 `#00c864` · B 5–10 `#c8e632` · C 10–15 `#ffc800` · D 15–20 `#ff8200` · E 20–25 `#e63232` · F≥25 `#960096` |
| FR-04 | Leyenda A–F fija en esquina inferior derecha, siempre visible, no colapsable en desktop |
| FR-05 | Grosor de línea adaptativo: 1–2 px en zoom ≤ 13, 3–4 px en zoom ≥ 15 |
| FR-06 | Spinner + texto "Cargando mapa de Liverpool..." visible durante carga inicial |
| FR-07 | Slider con 13 posiciones (Anual + Ene…Dic); posición por defecto es Anual (carga `liverpool_pollution_map.geojson`) |
| FR-08 | Al cambiar de mes, cross-fade < 500 ms sin frame en blanco; capa anterior permanece hasta que la nueva emite `sourcedata` con `isSourceLoaded === true` |
| FR-09 | Botón del mes seleccionado muestra indicador de loading durante el fetch |
| FR-10 | Bajo el slider, línea de contexto meteorológico del mes activo leída de `monthly_stats.json`: `<Mes> 2024 · Temp. media: X °C · Viento: X m/s · Días de lluvia: N` |
| FR-11 | Botones de mes coloreados sutilmente con paleta A–F según PM2.5 medio del mes |
| FR-12 | Transición slider < 1.000 ms en primera carga; < 150 ms en caché en memoria |
| FR-13 | Gráfico 3A: línea mensual PM2.5 (azul) y PM10 (naranja), línea roja punteada OMS (5 µg/m³), línea naranja punteada UK 2040 (10 µg/m³), área sombreada entre PM2.5 y OMS |
| FR-14 | Sincronización bidireccional: slider mueve punto activo del gráfico 3A; click en punto del gráfico mueve el slider |
| FR-15 | Tooltip en gráfico 3A muestra `PM2.5 = X,X µg/m³ · ×N sobre OMS` al hover |
| FR-16 | Gráfico 3B: barras horizontales PM2.5 medio por tipo de vía (primary/secondary/residential/other), coloreadas A–F, actualizadas al cambiar mes en < 500 ms |
| FR-17 | Gráfico 3C: top 5 tramos más contaminados del mes activo, ordenados descendentemente. Click → `flyTo` al tramo con zoom ≥ 15 y resaltado ≥ 2 s |
| FR-18 | Contador 3D: tres números derivados en runtime del GeoJSON activo (total tramos, tramos > OMS, tramos > UK 2040). Se actualizan al cambiar de mes |
| FR-19 | Markers de eventos visibles únicamente si mes del evento coincide con mes activo del slider |
| FR-20 | Evento `covid_context` siempre visible en mapa independientemente del mes activo |
| FR-21 | Click en marker → popup con título (≤ 40 car.), fecha `D de <mes> YYYY`, descripción (50–300 car., sin jerga técnica) |
| FR-22 | Iconos de tipo de evento bajo eje X del gráfico 3A; hover → tooltip con título + descripción corta |
| FR-23 | Datos de eventos cargados desde `events.json` (fichero pendiente de generación con pipeline Python) |
| FR-24 | Toggle `Calles / Barrios` alterna entre capa `streets-line` y capa `lsoa-fill` sin recargar la página |
| FR-25 | Capa LSOA: 302 polígonos con `fill-opacity = 0.7` y borde blanco fino, misma escala A–F |
| FR-26 | En vista Barrios, slider de meses queda deshabilitado con tooltip: "La vista por barrios usa datos anuales (2024). Cambia a vista por calles para explorar la estacionalidad." |
| FR-27 | Click en polígono LSOA → InfoCard con nombre del LSOA, barrio, score, PM2.5 medio anual y posición en ranking ("Posición: #N de 302 barrios") |
| FR-28 | Click en tramo de calle → InfoCard flotante (esquina inferior izquierda) con road_type, score, PM2.5, PM10, ×OMS, ×UK 2040 |
| FR-29 | Click fuera de cualquier feature → InfoCard desaparece con fade-out 150 ms |
| FR-30 | InfoCard se actualiza al cambiar mes activo sin cerrar ni reabrir el elemento DOM |
| FR-31 | Si `name == null` en GeoJSON, título de InfoCard se renderiza como `Calle sin nombre · <road_type>` (nunca "null" ni "undefined") |
| FR-32 | InfoCard aparece con fade-in 150 ms; se reubica a esquina inferior derecha si el click ocurre en la inferior izquierda |

**Total FRs: 32**

### Non-Functional Requirements (15 total)

| ID | Categoría | Criterio |
|----|-----------|----------|
| NFR-01 | Performance | Carga inicial < 3.000 ms, 8.450 tramos renderizados, conexión ≥ 20 Mbps, caché vacía, p95 |
| NFR-02 | Performance | Transición slider primera carga < 1.000 ms desde click hasta primer frame |
| NFR-03 | Performance | Transición slider caché < 150 ms |
| NFR-04 | Performance | Actualización panel EDA < 500 ms para gráficos 3B y 3C |
| NFR-05 | Performance | InfoCard < 150 ms desde click hasta card visible |
| NFR-06 | Accesibilidad | Conformidad WCAG 2.1 AA en todos los componentes interactivos |
| NFR-07 | Accesibilidad | Contraste ≥ 4.5:1 para texto sobre colores paleta A–F (WCAG 1.4.3) |
| NFR-08 | Accesibilidad | Todos los controles operables sin ratón (Tab + Enter/Space) (WCAG 2.1.1) |
| NFR-09 | Accesibilidad | Lighthouse Accessibility ≥ 90 en desktop y móvil |
| NFR-10 | Compatibilidad | Chrome 120+, Firefox 120+, Edge 120+, Safari 17+ |
| NFR-11 | Compatibilidad | Funcional en viewport ≥ 320 px de ancho |
| NFR-12 | Seguridad | Sin autenticación: ninguna funcionalidad requiere login, API key ni sesión |
| NFR-13 | Disponibilidad | Uptime ≥ 99% mensual durante período evaluación CAZ 2026 |
| NFR-14 | Red | Latencia CDN < 200 ms desde UK |
| NFR-15 | Datos | GeoJSONs en Supabase Storage accesibles públicamente sin token (bucket público) |

**Total NFRs: 15**

### Additional Requirements

| ID | Descripción |
|----|-------------|
| AR-01 | Stack: React 19 + Vite 6 + TypeScript 5 con `create-vite react-ts` |
| AR-02 | Estado global Zustand 5 — store único `useAppStore` con slices definidos |
| AR-03 | Supabase Storage con `Content-Encoding: br` y `Cache-Control: public, max-age=31536000, immutable` |
| AR-04 | Web Worker `geojson-parser.worker.ts` para JSON.parse sin bloquear hilo principal |
| AR-05 | Prefetch en background de 12 GeoJSONs mensuales con `requestIdleCallback` tras primer paint |
| AR-06 | `map.getSource('pollution-source').setData(fc)` en lugar de removeLayer/addLayer |
| AR-07 | Variables de entorno: `VITE_MAPBOX_TOKEN`, `VITE_SUPABASE_URL`. `.env.example` en repo |
| AR-08 | CI/CD: GitHub Actions `.github/workflows/ci.yml` typecheck + build en cada PR. Auto-deploy Vercel |
| AR-09 | Estructura de carpetas: `src/features/{map,eda,events,lsoa}/`, etc. |
| AR-10 | ⚠️ CRÍTICO: GeoJSONs mensuales, `monthly_stats.json` y `events.json` NO existen aún — pipeline Python pendiente |

**UX Design Requirements (UX-DR-01 a UX-DR-10):** Layout D1 Dark Split, escala de color como CSS custom properties, shadcn/ui, tipografía Inter, InfoCard 4 estados, MonthSlider con aria, panel con Tabs, responsive 3 breakpoints, WCAG checklist, leyenda flotante sobre mapa.

### PRD Completeness Assessment

El PRD está **bien estructurado y completo** para su versión:
- ✅ 32 FRs numerados y trazables
- ✅ 15 NFRs con criterios medibles y métodos de verificación
- ✅ Criterios de aceptación BDD por cada Feature
- ✅ Wireframes textuales para todas las vistas
- ✅ Flujos de usuario definidos (FU-01, FU-02)
- ⚠️ AR-10 documenta explícitamente la dependencia crítica de datos externos (pipeline Python)

---

## Epic Coverage Validation

### Coverage Matrix — Functional Requirements (32 FRs)

| FR | Descripción resumida | Epic | Story | Estado |
|----|----------------------|------|-------|--------|
| FR-01 | Mapa centrado Liverpool, zoom 12, < 3.000 ms | Epic 2 | Story 2.1 | ✅ Cubierto |
| FR-02 | 8.450 features con campos no nulos | Epic 2 | Story 2.1 | ✅ Cubierto |
| FR-03 | Escala A–F colores fijos | Epic 2 | Story 2.2 | ✅ Cubierto |
| FR-04 | Leyenda A–F fija inferior derecha | Epic 2 | Story 2.3 | ✅ Cubierto |
| FR-05 | Grosor línea adaptativo por zoom | Epic 2 | Story 2.1 | ✅ Cubierto |
| FR-06 | Spinner "Cargando mapa de Liverpool..." | Epic 1 | Story 1.4 | ✅ Cubierto |
| FR-07 | Slider 13 posiciones, default Anual | Epic 3 | Story 3.2 | ✅ Cubierto |
| FR-08 | Cross-fade < 500 ms sin frame en blanco | Epic 3 | Story 3.3 | ✅ Cubierto |
| FR-09 | Loading indicator en botón de mes | Epic 3 | Story 3.2 | ✅ Cubierto |
| FR-10 | Contexto meteorológico desde monthly_stats.json | Epic 3 | Story 3.4 | ✅ Cubierto |
| FR-11 | Botones mes coloreados con paleta A–F | Epic 3 | Story 3.4 | ✅ Cubierto |
| FR-12 | Transición < 1.000 ms / < 150 ms caché | Epic 3 | Stories 3.1 + 3.3 | ✅ Cubierto |
| FR-13 | Gráfico 3A: líneas PM2.5/PM10 + refs OMS/UK + área | Epic 4 | Story 4.1 | ✅ Cubierto |
| FR-14 | Sincronización bidireccional slider ↔ gráfico 3A | Epic 4 | Story 4.2 | ✅ Cubierto |
| FR-15 | Tooltip gráfico 3A: PM2.5 = X,X · ×N sobre OMS | Epic 4 | Story 4.1 | ✅ Cubierto |
| FR-16 | Gráfico 3B: barras horizontales por tipo de vía | Epic 4 | Story 4.3 | ✅ Cubierto |
| FR-17 | Gráfico 3C: top 5 tramos + flyTo + resaltado ≥ 2 s | Epic 4 | Story 4.4 | ✅ Cubierto |
| FR-18 | Contador 3D derivado en runtime del GeoJSON activo | Epic 4 | Story 4.5 | ✅ Cubierto |
| FR-19 | Markers eventos visibles solo si mes coincide | Epic 6 | Story 6.1 | ✅ Cubierto |
| FR-20 | Evento covid_context siempre visible | Epic 6 | Story 6.1 | ✅ Cubierto |
| FR-21 | Popup evento: título, fecha, descripción | Epic 6 | Story 6.2 | ✅ Cubierto |
| FR-22 | Iconos eventos bajo eje X con tooltip | Epic 6 | Story 6.3 | ✅ Cubierto |
| FR-23 | Datos desde events.json (pipeline Python) | Epic 6 | Story 6.1 | ✅ Cubierto |
| FR-24 | Toggle Calles/Barrios sin recargar página | Epic 5 | Story 5.2 | ✅ Cubierto |
| FR-25 | Capa LSOA 302 polígonos fill-opacity 0.7 | Epic 5 | Story 5.1 | ✅ Cubierto |
| FR-26 | Slider deshabilitado en vista Barrios con tooltip | Epic 5 | Story 5.2 | ✅ Cubierto |
| FR-27 | Click LSOA → InfoCard con ranking | Epic 5 | Story 5.3 | ✅ Cubierto |
| FR-28 | Click calle → InfoCard con ×OMS, ×UK 2040 | Epic 2 | Story 2.4 | ✅ Cubierto |
| FR-29 | Click fuera → InfoCard fade-out 150 ms | Epic 2 | Story 2.4 | ✅ Cubierto |
| FR-30 | InfoCard actualiza datos sin cerrar DOM | Epic 3 | Story 3.5 | ✅ Cubierto |
| FR-31 | name==null → "Calle sin nombre · road_type" | Epic 2 | Story 2.4 | ✅ Cubierto |
| FR-32 | InfoCard fade-in 150 ms + reubicación | Epic 2 | Stories 2.3 + 2.4 | ✅ Cubierto |

### Coverage Matrix — Non-Functional Requirements (15 NFRs)

| NFR | Descripción | Epic/Story | Estado |
|-----|-------------|------------|--------|
| NFR-01 | Carga inicial < 3.000 ms | Epic 2 / Story 2.1 | ✅ Cubierto |
| NFR-02 | Transición slider primera carga < 1.000 ms | Epic 3 / Story 3.3 | ✅ Cubierto |
| NFR-03 | Transición slider caché < 150 ms | Epic 3 / Story 3.1 | ✅ Cubierto |
| NFR-04 | Actualización EDA < 500 ms | Epic 4 / Stories 4.2–4.5 | ✅ Cubierto |
| NFR-05 | InfoCard < 150 ms | Epic 2 / Story 2.4 | ✅ Cubierto |
| NFR-06 | WCAG 2.1 AA | Stories 4.1, 6.3, 3.2 | ✅ Cubierto (parcial) |
| NFR-07 | Contraste ≥ 4.5:1 | Epic 2 / Story 2.2 | ✅ Cubierto |
| NFR-08 | Navegación teclado Tab + Enter/Space | Epic 3 / Story 3.2 | ✅ Cubierto |
| NFR-09 | Lighthouse Accessibility ≥ 90 | No en ninguna story | ⚠️ GAP — sin story explícita |
| NFR-10 | Navegadores Chrome/Firefox/Edge/Safari | Epic 1 / Story 1.1 (implícito) | ✅ Cubierto |
| NFR-11 | Viewport ≥ 320 px | Epic 1 / Story 1.3 | ✅ Cubierto |
| NFR-12 | Sin autenticación | Epic 1 / Story 1.1 | ✅ Cubierto |
| NFR-13 | Uptime ≥ 99%, monitoreo externo | No en ninguna story | ⚠️ GAP — infraestructura no en stories |
| NFR-14 | Latencia CDN < 200 ms UK | Epic 3 / Story 3.1 (Supabase CDN) | ✅ Cubierto |
| NFR-15 | GeoJSONs públicos sin token | Epic 3 / Story 3.1 | ✅ Cubierto |

### Missing Requirements

#### ⚠️ NFR-09 — Lighthouse Accessibility ≥ 90
- **Descripción:** Ninguna story incluye la verificación de auditoría Lighthouse con puntuación ≥ 90 como criterio de aceptación explícito.
- **Impacto:** Requisito verificable antes de la presentación al Council. Sin story, no hay responsable claro de ejecutarlo ni umbrales de pass/fail.
- **Recomendación:** Añadir como acceptance criteria en Story 1.3 (Layout) o crear Story 1.5 "Auditoría de Accesibilidad" en Epic 1.

#### ⚠️ NFR-13 — Uptime ≥ 99%, monitoreo externo
- **Descripción:** No hay story que configure UptimeRobot ni ningún monitor de uptime externo.
- **Impacto:** Requisito de disponibilidad para el período de evaluación CAZ 2026. Sin monitoreo, no es verificable.
- **Recomendación:** Añadir como tarea de infraestructura en Story 1.1 (CI/CD) o crear Story 1.6 "Monitoreo de Disponibilidad". Bajo esfuerzo (UptimeRobot es gratuito).

### Coverage Statistics

- **Total PRD FRs:** 32
- **FRs cubiertos en epics:** 32 (100%)
- **Total NFRs:** 15
- **NFRs cubiertos:** 13 (87%) — 2 gaps identificados
- **ARs cubiertos:** 9/10 — AR-10 es dependencia externa (pipeline Python, documentado como ⚠️ CRÍTICO)

---

## UX Alignment Assessment

### UX Document Status

✅ Encontrado: `_bmad-output/planning-artifacts/ux-design-specification.md` (status: complete, 14 pasos completados)

### Alineación UX ↔ PRD

| Elemento | Estado | Detalle |
|----------|--------|---------|
| Layout D1 Dark Split (desktop ≥1024px) | ✅ Alineado | PRD Layout global coincide con UX D1 |
| Responsive 768/1024/1280px breakpoints | ✅ Alineado | Ambos documentos coinciden |
| Escala A–F en mapa y LSOA | ✅ Alineado | Ambos definen la misma escala (story 2.2 referencia colores PRD) |
| shadcn/ui: Slider, Tabs, Badge, Tooltip | ✅ Alineado | UX y epics (UX-DR-03) coinciden |
| Flujos de usuario FU-01 y FU-02 | ✅ Alineado | Journeys UX coinciden con flujos PRD |
| WCAG 2.1 AA | ✅ Alineado | Ambos requieren AA con mismos controles |
| **Color tokens UX ≠ colores PRD** | ⚠️ INCONSISTENCIA | UX Step 8 define `--pm-safe: #22C55E`, `--pm-low: #EAB308`, etc. (5 niveles) que NO coinciden con la escala A–F del PRD (`#00c864`…`#960096`, 6 niveles). La UX tiene dos sistemas de color en conflicto. |
| **Threshold del badge WHO** | ⚠️ INCONSISTENCIA | UX Steps 7 y 12 declaran "Badge ⚠ Over WHO limit cuando PM2.5 > **15** µg/m³" pero el límite OMS 2021 PM2.5 anual es **5** µg/m³ (confirmado en PRD). El badge se disparará para el 99% de los tramos si el umbral correcto es 5. |
| URL state sharing en FU-01 | ⚠️ FUERA DE SCOPE | UX Journey FU-01 menciona "comparte URL con estado" — no hay FR en PRD que cubra esto, y la arquitectura decidió "Sin router". |

### Alineación UX ↔ Arquitectura

| Elemento | Estado | Detalle |
|----------|--------|---------|
| Stack React 19 + Vite 6 + TS5 + Zustand | ✅ Alineado | |
| Componentes InfoCard, MonthSlider, EdaPanel | ✅ Alineado | Nombres consistentes |
| Flujo de datos Supabase → Worker → cache | ✅ Alineado | UX performance requirements cubiertos por ADR-001 |
| **EdaPanel: charts en arquitectura ≠ PRD** | ⚠️ INCONSISTENCIA | Arquitectura define `HistogramChart.tsx` y `ScatterChart.tsx` pero el PRD/UX define: 3A (time series), 3B (barras por road type), 3C (top 5 tabla), 3D (contadores). No hay histograma ni scatter en el PRD. |
| `activeSegment` no en store | ⚠️ GAP | Arquitectura identifica este gap — debe añadirse al implementar F6/Epic 2 |

### Warnings

1. **⚠️ CRÍTICO — Doble sistema de color**: La UX Spec (Step 8) define tokens `--pm-*` que no coinciden con la escala A–F del PRD. El desarrollador debe ignorar los tokens del Step 8 y usar exclusivamente `--score-a`…`--score-f` de UX-DR-02 / Story 2.2. Recomendación: corregir o eliminar la sección de design tokens en UX Step 8.

2. **⚠️ CRÍTICO — Umbral badge WHO incorrecto**: El badge "Over WHO limit" debe activarse a PM2.5 > 5 µg/m³ (límite OMS), no > 15 µg/m³. Recomendación: corregir en UX Spec Steps 7 y 12. Impacto en InfoCard (Story 2.4) y en el contador 3D.

3. **ℹ️ MENOR — HistogramChart/ScatterChart sin PRD backing**: Eliminar de la arquitectura o confirmar si son parte del EdaPanel no documentado en PRD. Puede causar confusión al desarrollar Epic 4.

---

## Epic Quality Review

### Best Practices Compliance por Epic

#### Epic 1: Scaffold Desplegable ✅ ACEPTABLE (proyecto greenfield)

| Criterio | Estado | Nota |
|----------|--------|------|
| User value | ⚠️ Parcial | "Scaffold" es terminología técnica; el valor para el usuario es "acceder a la app desde URL pública" — correcto en fondo |
| Independence | ✅ | No depende de otros epics |
| Story 1.1 — Bootstrap + CI/CD | ✅ | Estándar en greenfield; entrega URL desplegable |
| Story 1.2 — Estructura carpetas + tipos | 🟠 ISSUE | **No hay user value visible**. Crear `src/features/`, tipos TypeScript y store vacío no entrega nada al usuario. Es una historia técnica pura. El desarrollador termina 1.2 y el usuario no puede hacer nada nuevo. |
| Story 1.3 — Layout D1 Dark | ✅ | Usuario ve el layout completo |
| Story 1.4 — Loading Overlay | ✅ | Usuario ve el spinner |

**Recomendación Story 1.2:** Fusionar el setup de tipos y store en Story 1.1 (como requisito previo técnico) o redefinir la AC para incluir un resultado visible (ej. "el layout renderiza sin errores de TypeScript con la estructura de carpetas definida").

---

#### Epic 2: Mapa Anual de Calidad del Aire ✅ BIEN ESTRUCTURADO

| Criterio | Estado | Nota |
|----------|--------|------|
| User value | ✅ | Usuarios exploran mapa de Liverpool con tramos coloreados |
| Independence | ✅ | Requiere solo Epic 1 |
| Story 2.1 — Mapa básico | ✅ | Entrega mapa funcional con 8.450 tramos |
| Story 2.2 — Escala A–F | ✅ | Usuarios ven colores de contaminación |
| Story 2.3 — Leyenda | 🟠 FORWARD DEPENDENCY | AC incluye: "When la InfoCard está visible en esquina inferior izquierda / Then la leyenda se desplaza o la InfoCard aparece en inferior derecha" — esto requiere **Story 2.4 completada**. |
| Story 2.4 — InfoCard | ✅ | Completa y autocontenida |

**Recomendación Story 2.3:** Separar la AC del desplazamiento de leyenda (dependiente de InfoCard) en un sub-ticket o moverla a Story 2.4. La leyenda básica es independiente; su interacción con la InfoCard no lo es.

---

#### Epic 3: Exploración Mensual ⚠️ BLOQUEADO EXTERNAMENTE

| Criterio | Estado | Nota |
|----------|--------|------|
| User value | ✅ | Usuarios navegan por 12 meses de 2024 |
| Independence | ⚠️ | **Bloqueado por AR-10**: 12 GeoJSONs mensuales + `monthly_stats.json` NO existen. Epic completamente inoperable sin pipeline Python. |
| Story 3.1 — Web Worker + Caché | 🟡 TÉCNICA | "As a **developer**" — no hay user value visible. Es una historia de infraestructura. Aceptable para habilitar NFR-02/03, pero el PM debe ser consciente de que la historia pasa pero el usuario no ve nada nuevo. |
| Story 3.2 — MonthSlider | ✅ | Usuario ve el control; usa datos anuales existentes aunque los mensuales no existan |
| Story 3.3 — Cross-fade | ✅ | Comportamiento verificable cuando haya datos |
| Story 3.4 — Contexto meteorológico | ⚠️ | Depende de `monthly_stats.json` inexistente |
| Story 3.5 — InfoCard actualiza al cambiar mes | ✅ | Lógica bien definida |
| Story 3.6 — Prefetch en background | 🟡 TÉCNICA | "As a **developer**" — como 3.1. Infraestructura sin user value directo. |

**Nota:** La secuencia recomendada de implementación es: Story 3.2 (slider UI) → pipeline Python → Stories 3.1, 3.3, 3.4, 3.5, 3.6.

---

#### Epic 4: Panel EDA ⚠️ PARCIALMENTE BLOQUEADO

| Criterio | Estado | Nota |
|----------|--------|------|
| User value | ✅ | Usuarios analizan tendencias con 4 visualizaciones |
| Independence | 🟡 | Gráfico 3A con datos anuales funciona sin Epic 3; gráficos 3B, 3C, 3D actualizables por mes requieren Epic 3 completado |
| Stories 4.1–4.5 | ✅ | Bien estructuradas, ACs claras y testables |
| Story 4.2 — Sincronización bidireccional | ✅ | Bien definida con Zustand como intermediario |

---

#### Epic 5: Vista LSOA ✅ BIEN ESTRUCTURADO

| Criterio | Estado | Nota |
|----------|--------|------|
| User value | ✅ | Usuarios ven 302 barrios con datos anuales existentes |
| Independence | ✅ | `lur_lsoa_predictions.geojson` **ya existe** — epic implementable hoy |
| Stories 5.1–5.3 | ✅ | Bien estructuradas, ACs verificables |

---

#### Epic 6: Contexto de Eventos Históricos ⚠️ BLOQUEADO EXTERNAMENTE

| Criterio | Estado | Nota |
|----------|--------|------|
| User value | ✅ | Usuarios ven contexto histórico de picos de contaminación |
| Independence | ⚠️ | **Bloqueado por AR-10**: `events.json` NO existe. Epic 6 no puede iniciarse hasta que el pipeline Python genere el archivo. |
| Stories 6.1–6.3 | ✅ | Bien estructuradas, ACs verificables cuando datos existan |

---

### Dependency Analysis (Orden Recomendado de Implementación)

```
Epic 1 (independiente — puede empezar hoy)
  ↓
Epic 2 (requiere Epic 1 — puede empezar tras 1.1+1.3)
  ↓
Epic 5 (requiere Epic 2 — datos LSOA ya existen, no bloqueado)
  ↓
Epic 4 (parcial: gráfico 3A con datos anuales funciona; 3B/3C/3D esperan Epic 3)
  ↓ (en paralelo con pipeline Python)
Pipeline Python → genera GeoJSONs mensuales + monthly_stats.json + events.json
  ↓
Epic 3 (requiere datos mensuales del pipeline)
  ↓
Epic 4 completo (actualización mensual de gráficos)
  ↓
Epic 6 (requiere events.json del pipeline)
```

### Issues por Severidad

#### 🟠 MAJOR ISSUES (no bloquean implementación pero requieren acción antes del desarrollo)

1. **Story 2.3 — Forward dependency en AC**: La AC de posicionamiento de leyenda vs. InfoCard referencia comportamiento de Story 2.4. Debe separarse.
2. **Story 1.2 — Sin user value observable**: Considerar fusionar con Story 1.1 o añadir AC de verificación visual.
3. **UX color tokens en conflicto** (identificado en paso anterior): Doble sistema de color puede confundir al desarrollador de Epic 2.
4. **WHO badge threshold incorrecto en UX Spec** (identificado en paso anterior): Impacta directamente la implementación de Story 2.4.

#### 🟡 MINOR CONCERNS

1. **Stories "As a developer" en Epic 3** (3.1 y 3.6): Válidas funcionalmente pero el PM debe comunicar que estas historias no entregan user value directo.
2. **`activeSegment` no en store initial**: Documentado en architecture gap — debe añadirse antes de Story 2.4.
3. **HistogramChart/ScatterChart en arquitectura sin FR**: Componentes sin backing en PRD.

### Best Practices Compliance Summary

| Epic | User Value | Independence | Story Sizing | ACs Quality | Traceability |
|------|-----------|--------------|--------------|-------------|--------------|
| Epic 1 | ⚠️ | ✅ | 🟠 (1.2) | ✅ | ✅ |
| Epic 2 | ✅ | ✅ | ✅ | 🟠 (2.3 fwd dep) | ✅ |
| Epic 3 | ✅ | ⚠️ (AR-10) | 🟡 (3.1, 3.6 dev) | ✅ | ✅ |
| Epic 4 | ✅ | 🟡 (parcial) | ✅ | ✅ | ✅ |
| Epic 5 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Epic 6 | ✅ | ⚠️ (AR-10) | ✅ | ✅ | ✅ |

---

## Summary and Recommendations

### Overall Readiness Status

**🟡 LISTO CONDICIONALMENTE** — El proyecto puede iniciar implementación (Epics 1, 2, 5) hoy mismo. Hay 2 issues críticos en la documentación UX que deben corregirse antes de desarrollar Story 2.4. Los Epics 3 y 6 están bloqueados por la dependencia crítica del pipeline Python.

### Critical Issues Requiring Immediate Action

| # | Issue | Impacto | Acción requerida |
|---|-------|---------|-----------------|
| C1 | **UX Spec: doble sistema de color** — Step 8 define `--pm-*` tokens que contradicen la escala A–F del PRD | Desarrollador de Epic 2 usará colores incorrectos | Eliminar sección de design tokens en UX Step 8; usar solo `--score-a`…`--score-f` |
| C2 | **UX Spec: threshold WHO badge incorrecto (>15 en lugar de >5 µg/m³)** | La InfoCard mostrará el badge para el 99% de los tramos, no solo los que superan el límite OMS | Corregir en UX Spec Steps 7 y 12 antes de Story 2.4 |
| C3 | **Pipeline Python (AR-10) — bloqueante para Epics 3 y 6** | Sin GeoJSONs mensuales, monthly_stats.json y events.json no es posible completar ~50% del producto | Generar datos antes de iniciar Sprint 2; Epic 1+2+5 pueden avanzar en Sprint 1 |

### Recommended Next Steps

**Sprint 1 — Iniciar hoy (datos disponibles):**
1. Corregir UX Spec (issues C1 y C2) antes de desarrollar
2. Epic 1 completo (Stories 1.1 → 1.4) — scaffold + CI/CD + layout
3. Epic 2 completo (Stories 2.1 → 2.4) — mapa anual + InfoCard
4. Epic 5 completo (Stories 5.1 → 5.3) — vista LSOA (datos ya existen)
5. Epic 4 parcial (Story 4.1) — gráfico 3A con datos anuales

**Paralelo al Sprint 1 — Pipeline Python:**
6. Ejecutar pipeline Python para generar: 12 GeoJSONs mensuales, `monthly_stats.json`, `events.json`
7. Configurar Supabase Storage con Brotli y headers de caché (AR-03)

**Sprint 2 — Tras pipeline Python:**
8. Epic 3 completo (Stories 3.1 → 3.6) — slider mensual
9. Epic 4 completo (Stories 4.2 → 4.5) — gráficos mensuales
10. Epic 6 completo (Stories 6.1 → 6.3) — eventos históricos

**Antes de Sprint 2:**
11. Añadir `activeSegment` al store Zustand (gap identificado en arquitectura)
12. Aclarar HistogramChart/ScatterChart en arquitectura o eliminarlos
13. Añadir AC de Lighthouse ≥ 90 a Story 1.3 o crear Story 1.5 (NFR-09)
14. Añadir configuración de UptimeRobot a Story 1.1 (NFR-13)

### Final Note

Esta evaluación identificó **12 issues** en 4 categorías:
- 2 issues **críticos** en UX Spec (requieren corrección antes de Epic 2)
- 1 dependencia **crítica** externa (pipeline Python — bloqueante para Epics 3+6)
- 4 issues **major** (forward dependency en Story 2.3, user value en Story 1.2, NFR-09, NFR-13)
- 5 issues **menores** (componentes sin backing, stories técnicas, activeSegment gap)

**El proyecto está en condiciones de iniciar la implementación de Epics 1, 2 y 5 hoy.** La cobertura funcional es 100% (32/32 FRs trazados). Los issues identificados son correcciones de documentación y dependencias de datos, no deficiencias arquitecturales.

---

*Informe generado: 2026-04-20 | Proyecto: airtrace-web | Metodología: BMAD Implementation Readiness v6.3.0*
