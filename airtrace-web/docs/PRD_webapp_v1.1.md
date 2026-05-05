---
workflowType: prd
workflow: edit
classification:
  domain: govtech
  projectType: web_app
  complexity: high
inputDocuments:
  - outputs/maps/liverpool_pollution_map.geojson
  - outputs/maps/lur_lsoa_predictions.geojson
  - docs/08_lur_improvement_session.md
  - docs/04_validation_report.md
stepsCompleted:
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
lastEdited: '2026-04-20'
editHistory:
  - date: '2026-04-20'
    changes: >
      Añadidas secciones Criterios de Éxito, Flujos de Usuario y Requisitos No Funcionales.
      Declarados WCAG 2.1 AA y browser matrix en Layout global.
      Notas técnicas de Feature 2 movidas a ADR-001-geojson-delivery.md.
      Frontmatter BMAD añadido con clasificación govtech/web_app.
---

# AirTrace — Product Requirements Document (Web App)

**Para:** Equipo de desarrollo
**De:** Business Owner
**Fecha:** 2026-04-17
**Versión:** 1.2 (mejoras estructurales BMAD — 2026-04-20)

---

## Propuesta de valor B2G

**Usuario primario:** Planificador urbano del Liverpool City Council (LCC) y analista de salud pública del NHS Cheshire & Merseyside ICB.

**Caso de uso de referencia:** Insumo técnico a la **evaluación formal de la Clean Air Zone (CAZ) de Liverpool**, iniciada en marzo 2024 y con ventana decisional abierta en 2026. AirTrace es, a la fecha, la única fuente con resolución **calle a calle (n = 8.450 tramos)** disponible durante el proceso oficial.

**Unidad de valor:** Extender los 21 puntos de sensor físico IoT a una superficie modelada y validada estadísticamente (SVR, R² = 0.60 en PM2.5 y R² = 0.58 en PM10 bajo LOOCV), con agregación nativa a **302 LSOAs** — la unidad administrativa estándar del ONS y del NHS, lo que habilita cruces posteriores con datos de deprivación social (IMD) y epidemiología respiratoria.

**Por qué mensual y no tiempo real:** los ciclos de política pública —evaluación CAZ, planes locales de calidad del aire, inversiones en zonas de bajas emisiones— se miden en trimestres. La variación estacional (invierno ~+30% vs verano) es precisamente el rango accionable para priorizar intervenciones. Un dashboard en tiempo real sería ruido operativo sin decisión asociada.

---

## Contexto para el equipo

Hemos construido un modelo científico (regresión LUR con Support Vector Regression) que predice los niveles de PM2.5 y PM10 en cada tramo de calle de Liverpool. Activos disponibles:

- **8.450 tramos de calle** con predicción anual (media 2024) y predicción por mes.
- **21 sensores IoT** reales desplegados en la ciudad — conjunto de entrenamiento y validación del modelo.
- **12 meses** de predicciones mensuales (enero–diciembre 2024) que capturan la estacionalidad real vía meteorología observada.
- **302 barrios (LSOAs)** con predicción agregada anual.
- **Modelo validado:** R² = 0.602 en PM2.5, R² = 0.581 en PM10, LOOCV sobre 21 estaciones. Intervalo de confianza ±0,76 µg/m³ en la media. Esto sitúa al modelo en el rango alto de la literatura LUR (aceptada entre 0,5 y 0,7).

El producto es una **web app pública sin autenticación** y sin API comercial en esta versión. Objetivo inmediato: material demostrable en la próxima reunión con el Liverpool City Council.

**Mensaje de política pública que los datos permiten defender:** prácticamente ninguna calle de Liverpool cumple el límite OMS 2021 (5 µg/m³), y el **49% de las LSOAs supera incluso el objetivo UK 2040** (10 µg/m³). Esto tiene implicaciones directas sobre la priorización de intervenciones CAZ y sobre la asignación geográfica de recursos sanitarios.

---

## Principios de diseño

1. **Los datos son el protagonista.** La UI existe para que los datos hablen, no al revés.
2. **Un no-técnico tiene que entenderlo en 30 segundos.** El score A–F es la interfaz primaria; los valores exactos en µg/m³ son secundarios.
3. **Cada número tiene contexto regulatorio.** "PM2.5 = 12,4 µg/m³" dice poco. "PM2.5 = 12,4 µg/m³ — ×2,5 sobre OMS" dice mucho. El multiplicador ×N sobre OMS es la métrica narrativa primaria y debe aparecer en InfoCard y en el tooltip del gráfico de tendencia.
4. **El mapa es el centro.** Panel, slider y popups sirven al mapa.

---

## Criterios de Éxito

El producto cumple su objetivo cuando se verifican todas las siguientes condiciones:

| ID | Criterio | Métrica | Método de verificación |
|----|----------|---------|------------------------|
| CE-01 | Carga inicial del mapa | < 3.000 ms con 8.450 tramos visibles, conexión ≥ 20 Mbps, caché vacía, percentil 95 | Performance API en browser + prueba manual con Network throttle |
| CE-02 | Transición de slider (mes nuevo) | < 1.000 ms desde click hasta primer frame con datos del mes | `performance.now()` en evento `sourcedata` de Mapbox GL |
| CE-03 | Adopción en política pública | Los datos de AirTrace son citados o referenciados en ≥ 1 documento oficial del Liverpool City Council o NHS durante el proceso de evaluación CAZ 2026 | Confirmación directa con el contacto en LCC tras la reunión de presentación |
| CE-04 | Integridad de datos | 100% de los 8.450 tramos y 302 LSOAs tienen valores `pm25` y `pm10` no nulos en la carga inicial | Test automatizado sobre GeoJSON: `assert features.filter(f => f.pm25 == null).length === 0` |
| CE-05 | Accesibilidad | La app cumple WCAG 2.1 AA en todos los componentes interactivos | Auditoría con axe DevTools o Lighthouse Accessibility ≥ 90 |

> **Nota:** CE-03 es el criterio de impacto de negocio. CE-01, CE-02 y CE-04 son los criterios de calidad técnica verificables antes de la reunión.

---

## Flujos de Usuario

### FU-01 — Planificador Urbano (Liverpool City Council)

**Perfil:** Técnico de política ambiental del LCC responsable de preparar insumos para la evaluación CAZ.  
**Objetivo:** Obtener evidencia georreferenciada a nivel de calle para justificar una intervención en un corredor específico.

1. Abre la app → el mapa anual de Liverpool carga en < 3 s con todos los tramos coloreados.
2. Identifica visualmente los corredores naranja/rojo en el centro → confirma que Scotland Road y Queens Drive son zonas D.
3. Activa el slider en **Enero** → observa que los valores empeoran en invierno, confirmando el patrón estacional.
4. Hace click en Scotland Road → la InfoCard muestra `PM2.5 = 15,8 µg/m³ · ×3,2 sobre OMS` → copia el multiplicador para su informe.
5. Cambia a vista **Barrios (LSOA)** → identifica Liverpool 017E (Vauxhall) como el LSOA #1 con 14,97 µg/m³.
6. **Resultado:** tiene evidencia a nivel calle (tramo) y barrio (LSOA) para el informe técnico de la evaluación CAZ.

### FU-02 — Analista de Salud Pública (NHS Cheshire & Merseyside ICB)

**Perfil:** Analista del ICB que prioriza intervenciones de salud respiratoria por área geográfica.  
**Objetivo:** Identificar qué barrios tienen mayor exposición acumulada y cuándo es peor para planificar campañas.

1. Abre la app → activa directamente la vista **Barrios (LSOA)**.
2. Identifica los LSOAs con score C en el norte y centro (Vauxhall, Scotland, Kirkdale).
3. Consulta el **gráfico de tendencia mensual** (panel EDA 3A) → el pico de noviembre confirma que Bonfire Night es un evento crítico.
4. Lee el contador 3D: *"≥ 8.400 tramos > OMS (99%) · 4.161 > UK 2040 (49%)"* → extrae el 49% para su memo de gestión.
5. Abre la InfoCard de Liverpool 017E → toma el multiplicador `×3,0 sobre OMS` como argumento para priorización presupuestaria.
6. **Resultado:** lista de barrios prioritarios con evidencia de exposición estacional para el plan de salud respiratoria 2026–2027.

---

## Feature 1 — Mapa de Contaminación Base

### Qué queremos

Liverpool con cada tramo coloreado por su nivel de PM2.5 anual. A primera vista, sin interacción, el usuario distingue zonas limpias de zonas contaminadas.

### Por qué importa

En la reunión con el Council, la primera pregunta será *"¿dónde están las calles más contaminadas?"*. La respuesta debe ser visual, inmediata y defendible. No un Excel. No una tabla. El mapa.

### Comportamiento detallado

**Carga inicial:**
- Mapa centrado en Liverpool, zoom 12, estilo Mapbox `dark-v11`.
- Los 8.450 tramos coloreados deben quedar visibles en los primeros 3 segundos.
- Mientras carga: spinner + texto *"Cargando mapa de Liverpool..."*.

**Escala de color (fija, no negociable):**

| Score | Rango PM2.5 | Color | Referencia regulatoria |
|-------|-------------|-------|------------------------|
| A | < 5 µg/m³ | Verde `#00c864` | Cumple OMS 2021 |
| B | 5–10 µg/m³ | Amarillo-verde `#c8e632` | Cumple UK 2040 |
| C | 10–15 µg/m³ | Amarillo `#ffc800` | Supera UK 2040 |
| D | 15–20 µg/m³ | Naranja `#ff8200` | Zona preocupante |
| E | 20–25 µg/m³ | Rojo `#e63232` | Zona crítica |
| F | ≥ 25 µg/m³ | Morado `#960096` | Acción urgente |

> **Nota para el equipo:** En datos anuales 2024, el PM2.5 mínimo observado es 4,87 µg/m³ y el máximo 28,10 µg/m³. La distribución práctica vive entre B (periféricas), C/D (centro y vías primarias) y algunos picos E/F en corredores de tráfico intenso. Los scores A son residuales (< 1% del total). Este patrón es exactamente el que queremos que sea visible.

**Grosor de línea:** fino en zoom out (1–2 px), grueso en zoom in (3–4 px). Evita que el mapa se lea como un borrón a nivel ciudad.

**Mapa base:** estilo oscuro obligatorio. El estilo claro diluye la paleta de contaminación.

**Leyenda fija:** esquina inferior derecha, siempre visible, no colapsable. Muestra los 6 scores con su color y rango.

```
┌─────────────────────┐
│ Calidad del aire    │
│ ● A  < 5 µg/m³      │
│ ● B  5–10           │
│ ● C  10–15          │
│ ● D  15–20          │
│ ● E  20–25          │
│ ● F  ≥ 25           │
│ PM2.5 anual 2024    │
└─────────────────────┘
```

### Wireframe del estado inicial

```
┌─────────────────────────────────────────────────────────┬──────────┐
│                                                         │          │
│          [MAPA DE LIVERPOOL — fondo oscuro]             │ PANEL    │
│                                                         │ LATERAL  │
│    Tramos coloreados:                                   │          │
│    Centro/vías principales → naranja/rojo               │ (ver     │
│    Zonas residenciales → amarillo                       │ Feature  │
│    Zonas verdes/periféricas → amarillo-verde            │  3)      │
│                                                         │          │
│                                        [Leyenda A–F]    │          │
└─────────────────────────────────────────────────────────┴──────────┘
```

### Criterios de aceptación (BDD)

- **Given** una conexión WiFi o cable estándar (≥ 20 Mbps) y caché vacía, **When** el usuario abre la app por primera vez, **Then** el mapa con los 8.450 tramos coloreados debe estar completamente renderizado en menos de 3.000 ms desde la respuesta del HTML inicial.
- **Given** el mapa en estado inicial (zoom 12, centrado en Liverpool), **When** la carga ha finalizado, **Then** la capa `streets-line` contiene 8.450 features exactas con los campos `pm25_annual`, `pm10_annual`, `score` y `road_type` no nulos.
- **Given** el mapa cargado con datos anuales 2024, **When** se inspeccionan zonas del centro (ej. Ranelagh Street, Scotland Road) frente a zonas periféricas (ej. Childwall, Allerton), **Then** los tramos del centro presentan predominantemente scores C–D–E y los periféricos scores B, reflejando el gradiente real del dataset.
- **Given** cualquier viewport soportado (desktop ≥ 1024 px, tablet 768–1023 px o móvil < 768 px), **When** el mapa está renderizado, **Then** la leyenda A–F es visible sin necesidad de scroll (en móvil, accesible mediante icono expandible en la esquina inferior derecha).

---

## Feature 2 — Slider de Meses (Estacionalidad)

### Qué queremos

Un selector de meses que permite ver cómo varía la contaminación a lo largo de 2024. El mapa se actualiza en cada cambio.

### Por qué importa

Los datos anuales dicen *cuánto* hay de contaminación; los mensuales dicen *por qué*. En UK el PM2.5 es un 25–30% mayor en invierno (calefacción + inversión térmica + menos viento) que en verano. Esa estacionalidad es accionable: permite al Council justificar intervenciones concentradas en los meses de mayor exposición.

Además, el slider es lo que diferencia AirTrace de un mapa estático. Cualquiera publica un choropleth. El slider convierte el mapa en una herramienta de análisis temporal.

### Datos disponibles

Los 12 GeoJSONs mensuales se generan corriendo el modelo SVR con la meteorología real observada cada mes (temperatura, viento, lluvia), manteniendo constantes las variables espaciales (land use, roads). Esto captura variación estacional con datos reales, no con simulación.

Variación esperada (referencia para validar el slider):

| Mes | PM2.5 medio estimado | Razón |
|-----|----------------------|-------|
| Enero | ~12–13 µg/m³ | Invierno: calefacción + inversión térmica |
| Abril | ~10–11 µg/m³ | Primavera: transición |
| Julio | ~8–9 µg/m³ | Verano: viento + dispersión |
| Noviembre | ~13–14 µg/m³ | Otoño tardío + Bonfire Night |
| Diciembre | ~12–13 µg/m³ | Inicio de temporada de calefacción |

### Comportamiento detallado

**Posiciones del slider:**

```
[ Anual ] [ Ene ] [ Feb ] [ Mar ] [ Abr ] [ May ] [ Jun ] [ Jul ] [ Ago ] [ Sep ] [ Oct ] [ Nov ] [ Dic ]
    ↑
  default
```

- `Anual` es la posición por defecto; muestra la media de 2024 desde `liverpool_pollution_map.geojson`.
- Al seleccionar un mes, el mapa se actualiza con el GeoJSON mensual correspondiente.
- La transición debe ser un fade de < 500 ms, nunca un parpadeo brusco.

**Feedback visual durante la carga:**
- El botón del mes seleccionado muestra un indicador de loading mientras se resuelve el fetch.
- El mapa **no se blanquea**: la capa anterior permanece hasta que la nueva está lista en el `source`.

**Contexto meteorológico del mes activo:**
Bajo el slider, una línea con la meteorología observada de ese mes, leída de `monthly_stats.json`:

```
Julio 2024  ·  Temp. media: 18,3 °C  ·  Viento: 4,2 m/s  ·  Días de lluvia: 8
```

**Indicador de estacionalidad en el propio slider:**
El fondo o borde de cada botón de mes se colorea sutilmente según el PM2.5 medio de ese mes usando la paleta de la leyenda. Así enero/diciembre se ven "más naranjas" y julio/agosto "más verdes", incluso antes de hacer click.

### Wireframe del slider

```
┌──────────────────────────────────────────────────────────────────────┐
│  ANUAL  ENE  FEB  MAR  ABR  MAY  JUN  JUL  AGO  SEP  OCT  NOV  DIC   │
│         [■]  [■]  [□]  [□]  [□]  [□]  [□]  [□]  [□]  [□]  [■]  [■]   │
│          ↑ color de fondo = PM2.5 medio del mes                      │
│                                                                      │
│  Enero 2024  ·  Temp: 6,2 °C  ·  Viento: 5,1 m/s  ·  Lluvia: 14 días │
└──────────────────────────────────────────────────────────────────────┘
```

### Arquitectura de entrega de GeoJSONs mensuales

El criterio `< 1 s` requiere una estrategia específica de entrega. Las decisiones técnicas (compresión Brotli, prefetch en background, caché en memoria, parse en Web Worker, cross-fade controlado) están documentadas en:

> **→ `docs/ADR-001-geojson-delivery.md`** — Architecture Decision Record: entrega de GeoJSONs mensuales

Las optimizaciones del ADR son **requisito para este sprint**; implementarlas en conjunto es lo que hace alcanzable el criterio de 1 s.

### Criterios de aceptación (BDD)

- **Given** un usuario con el mapa anual cargado y caché vacía del navegador, **When** selecciona por primera vez el mes de enero, **Then** el mapa refleja los nuevos datos en menos de **1.000 ms** desde el `click` hasta el primer frame con la nueva capa visible.
- **Given** un mes previamente cargado y presente en la caché en memoria, **When** el usuario vuelve a seleccionarlo, **Then** la transición se completa en menos de **150 ms**.
- **Given** el slider en `Anual` y luego el usuario selecciona `Jul`, **When** ambas capas se han renderizado, **Then** el PM2.5 medio expuesto en el panel 3D es al menos **2 µg/m³ inferior** al de enero, validando la estacionalidad.
- **Given** el slider en cualquier mes, **When** la transición finaliza, **Then** aparece bajo el slider una línea con formato `<Mes> 2024 · Temp. media: X,X °C · Viento: X,X m/s · Días de lluvia: N`, con valores exactos provenientes de `monthly_stats.json`.
- **Given** el primer arranque de la app (cold load), **When** el mapa termina de cargar, **Then** la posición del slider es `Anual` y el `source` activo apunta a `liverpool_pollution_map.geojson` (nunca a `liverpool_pollution_2024-01.geojson`).
- **Given** el slider interactuado en cualquier dirección, **When** se inspecciona visualmente la transición, **Then** el mapa **no presenta ningún frame en blanco**: la capa anterior persiste hasta que la nueva emite `sourcedata` con `isSourceLoaded === true`.

---

## Feature 3 — Panel EDA (Gráficos de Tendencia)

### Qué queremos

Un panel lateral con gráficos que complementan el mapa. Más allá del *dónde*, el panel responde al *cómo evoluciona* y al *quién contribuye más*.

### Por qué importa

En una reunión con el Council, el mapa es el primer gancho. Pero el analista de datos del Council querrá gráficos que pueda copiar a su PowerPoint. Sin gráficos, somos un mapa bonito; con gráficos, somos una herramienta de análisis.

Los gráficos responden preguntas que el mapa no puede resolver por sí solo: ¿cuál es el peor mes? ¿las vías primarias están realmente mucho peor que las residenciales? ¿qué zona de la ciudad muestra mayor variación estacional?

### Componentes del panel

#### 3A — Gráfico de tendencia mensual (principal)

**Título:** "PM2.5 y PM10 — Evolución mensual 2024"

Gráfico de línea con:
- Eje X: meses (Ene–Dic).
- Eje Y izquierdo: PM2.5 (µg/m³), rango 0–20.
- Eje Y derecho: PM10 (µg/m³), rango 0–35 — escala proporcional equivalente para que ambas líneas sean comparables visualmente.
- Línea azul: PM2.5 medio de Liverpool ese mes.
- Línea naranja: PM10 medio.
- Línea roja punteada horizontal: 5 µg/m³ (OMS 2021) — etiquetada `OMS`.
- Línea naranja punteada horizontal: 10 µg/m³ (UK 2040) — etiquetada `UK 2040`.
- Área sombreada entre la línea PM2.5 y la referencia OMS (siempre por encima — todo Liverpool supera OMS).
- **Sincronización bidireccional con el mapa:** al cambiar el mes en el slider, el punto correspondiente del gráfico se resalta con un círculo mayor y un tooltip que expone el multiplicador `× N sobre OMS`. Click en un punto del gráfico mueve el slider al mes correspondiente.

**Insight clave que debe ser obvio:** la línea PM2.5 nunca baja por debajo de la línea roja OMS — ni siquiera en julio, el mes más limpio. Ese es el hecho que el Council debe ver.

#### 3B — Distribución por tipo de vía

**Título:** "PM2.5 medio por tipo de calle — Mes seleccionado"

Gráfico de barras horizontal con 4 categorías:
- `primary` — vías principales (Scotland Road, Queens Drive...).
- `secondary` — vías secundarias.
- `residential` — calles residenciales.
- `other` — resto.

Cada barra:
- Coloreada con la paleta según su valor.
- Con valor numérico al final.
- Se actualiza al cambiar el mes seleccionado.

**Por qué este gráfico:** demuestra que vivir en una calle residencial no implica menos contaminación que vivir en una vía principal. En Liverpool la diferencia es ~2–3 µg/m³, suficiente para pasar de score C a B, pero ambas siguen por encima de OMS.

```
primary      ████████████████████ 15,2 µg/m³  [D]
secondary    ████████████████░░░  13,1 µg/m³  [C]
residential  █████████████░░░░░░  11,3 µg/m³  [C]
other        ███████████░░░░░░░░  10,1 µg/m³  [C]
                                  ↑ referencia OMS
```

#### 3C — Top 5 tramos más contaminados

**Título:** "Calles más contaminadas · Mes seleccionado"

Lista simple de 5 filas:

```
1. Scotland Road           [D]  16,8 µg/m³
2. Queens Drive            [D]  16,2 µg/m³
3. Edge Lane               [C]  15,9 µg/m³
4. Vauxhall Road           [C]  15,4 µg/m³
5. Commercial Road         [C]  14,9 µg/m³
```

Click en cualquiera: el mapa hace `flyTo` al tramo y lo resalta.

#### 3D — Contador de calles por encima de umbrales

Tres números grandes, siempre visibles en la parte superior del panel. Los valores se **derivan del GeoJSON del mes activo en runtime** (no se hardcodean):

```
┌──────────┬──────────┬──────────┐
│  8.450   │ ≥ 8.400  │  4.161   │
│  tramos  │ > OMS    │ > UK2040 │
│  totales │ (~99%)   │  (49%)   │
└──────────┴──────────┴──────────┘
```

Se actualizan al cambiar de mes. En julio el porcentaje `> OMS` puede bajar ligeramente — ese movimiento es, en sí mismo, un dato interesante.

### Diseño del panel

Panel fijo lateral derecho, 320 px, fondo semitransparente oscuro. Scroll interno si el contenido no cabe. No colapsa en desktop; en móvil se convierte en drawer inferior.

```
┌──────────────────────────────┐
│ AirTrace   Liverpool 2024    │
│ [Calles ▼] [Barrios]         │
├──────────────────────────────┤
│ 8.450   ≥8.400  4.161        │
│ tramos   >OMS   >UK2040      │
├──────────────────────────────┤
│                              │
│  [Gráfico tendencia mensual] │
│   PM2.5 ── PM10 ──           │
│   ── OMS  ── UK2040          │
│                              │
├──────────────────────────────┤
│ Por tipo de calle            │
│ primary    ████ 15,2 [D]     │
│ secondary  ███  13,1 [C]     │
│ residential██   11,3 [C]     │
├──────────────────────────────┤
│ Top 5 calles                 │
│ 1. Scotland Rd  16,8 [D]     │
│ 2. Queens Drive 16,2 [D]     │
│ ...                          │
├──────────────────────────────┤
│ Datos: SVR LUR · R²=0,60     │
│ 21 sensores IoT · 2024       │
└──────────────────────────────┘
```

### Criterios de aceptación (BDD)

- **Given** el panel EDA en estado inicial, **When** el gráfico 3A se renderiza, **Then** el eje X muestra exactamente 12 puntos etiquetados `Ene` a `Dic` y dos series (PM2.5, PM10) con valores no nulos en los 12 puntos.
- **Given** el gráfico 3A renderizado, **When** se inspecciona el lienzo, **Then** existe una línea horizontal roja punteada en `y = 5` etiquetada `OMS` y una línea naranja punteada en `y = 10` etiquetada `UK 2040`.
- **Given** el gráfico 3A renderizado y el slider en `Anual`, **When** el usuario hace `click` sobre el punto de datos correspondiente a septiembre, **Then** el slider se desplaza a `Sep` y el mapa carga `liverpool_pollution_2024-09.geojson` con la misma sincronización bidireccional exigida.
- **Given** el gráfico 3A en cualquier estado, **When** el usuario hace `hover` sobre un punto, **Then** el tooltip muestra `PM2.5 = X,X µg/m³ · ×N sobre OMS` y la misma métrica para PM10.
- **Given** el gráfico 3B mostrando datos anuales, **When** el usuario selecciona `Jul` en el slider, **Then** las cuatro barras (`primary`, `secondary`, `residential`, `other`) se actualizan a los valores de julio en menos de 500 ms y cada barra aplica el color de la paleta A–F correspondiente a su valor.
- **Given** un mes seleccionado, **When** el panel 3C se renderiza, **Then** las 5 filas corresponden exactamente a los 5 tramos con mayor `pm25` en el GeoJSON de ese mes, ordenados descendentemente y con su nombre, score y valor numérico.
- **Given** el panel 3C con 5 filas renderizadas, **When** el usuario hace `click` en la fila 1, **Then** el mapa ejecuta `flyTo` a las coordenadas de ese tramo con zoom ≥ 15 y lo resalta durante al menos 2 s.
- **Given** el panel 3D en cualquier mes seleccionado, **When** se leen los tres contadores, **Then** `tramos_totales = 8.450`, `tramos_over_oms` es el recuento real del GeoJSON del mes activo, y `tramos_over_uk2040` es igualmente derivado en runtime (no hardcodeado).

---

## Feature 4 — Eventos Canónicos

### Qué queremos

Marcadores contextuales en el mapa y en el timeline que explican picos o valles de contaminación. Cuando el usuario ve que noviembre es el peor mes, un popup le dice por qué: Bonfire Night.

### Por qué importa

Los datos sin contexto son ruido; los datos con contexto son inteligencia. Cuando el Council pregunte "¿por qué en agosto hay menos contaminación?", la respuesta debe estar **dentro del producto**, no en la cabeza del vendedor.

Los eventos también humanizan el mapa. Un mapa estático es académico; un mapa que dice "esta semana hubo fuegos artificiales" es algo que la gente entiende y recuerda.

### Lista de eventos (con justificación científica)

| ID | Fecha | Mes | Título | Tipo | Impacto en datos |
|----|-------|-----|--------|------|------------------|
| `bonfire_night` | 5 Nov 2024 | 2024-11 | Bonfire Night | seasonal | Pico de PM2.5 y PM10 de 1–3 días. Sensores de Liverpool registran aumentos de hasta ×3 la media diaria. Noviembre es el mes con PM2.5 más alto del año. |
| `heatwave_aug` | 12 Ago 2024 | 2024-08 | Ola de calor | climate | Temperaturas > 28 °C aceleran la dispersión atmosférica. Agosto es el mes más limpio de 2024. Paradoja: el calor mejora la calidad del aire en PM2.5 aunque empeora el ozono troposférico (fuera de scope). |
| `heating_jan` | 15 Ene 2024 | 2024-01 | Temporada de calefacción | seasonal | Inicio del invierno. Combinación de calefacción doméstica + inversión térmica + viento < 3 m/s = concentración máxima de PM2.5. Enero es históricamente uno de los meses más contaminados en ciudades del norte de UK. |
| `easter_traffic` | 29 Mar 2024 | 2024-03 | Semana Santa — Reducción de tráfico | traffic | El fin de semana de Pascua reduce el tráfico laboral ~40% en Liverpool. Los sensores en vías primarias registran caída de PM2.5. Experimento natural que ilustra el impacto del tráfico. |
| `caz_eval` | 15 Mar 2024 | 2024-03 | Liverpool CAZ — Evaluación activa | policy | Liverpool City Council inicia evaluación formal de Clean Air Zone. Los datos de este período son los primeros disponibles durante el proceso oficial de evaluación. AirTrace es la única fuente con resolución de tramo de calle para este proceso. |
| `covid_context` | 23 Mar 2020 | *contexto* | Confinamiento COVID-19 (referencia) | policy | Durante el confinamiento de 2020 el NO₂ en Liverpool cayó ~45% y el PM2.5 ~15%. Sirve como experimento natural que demuestra el impacto del tráfico. No tenemos datos de 2020, pero este contexto explica por qué el tráfico importa. |

### Comportamiento detallado

**En el mapa:**
- Cada evento con `lat/lng` (todos excepto COVID) se muestra como marker.
- Icono según tipo: 🎆 seasonal · 🌡️ climate · 📋 policy · 🚦 traffic.
- El marker aparece únicamente si el mes del evento coincide con el mes seleccionado en el slider.
- El evento COVID aparece siempre (contexto histórico sin mes asignado).
- Click en marker → popup con título, fecha, explicación en lenguaje natural e impacto en los datos.

**En el gráfico 3A (panel EDA):**
- Bajo el eje X, bajo el mes correspondiente, aparece el icono del tipo de evento.
- Hover sobre el icono → tooltip con título y descripción corta.
- Conecta visualmente "el pico de noviembre" con "Bonfire Night".

**Diseño del popup:**

```
┌──────────────────────────────────────────┐
│ 🎆 Bonfire Night                    ×    │
│ 5 de noviembre 2024                      │
├──────────────────────────────────────────┤
│ Los fuegos artificiales del 5 de         │
│ noviembre generan picos de PM2.5 y PM10  │
│ de corta duración. Los sensores de       │
│ Liverpool registran aumentos de hasta    │
│ ×3 la media diaria.                      │
│                                          │
│ Noviembre es el mes con mayor            │
│ contaminación media de 2024.             │
└──────────────────────────────────────────┘
```

### Criterios de aceptación (BDD)

- **Given** el slider en `Nov`, **When** el mapa ha terminado de renderizar, **Then** el marker con `id = bonfire_night` es visible en la capa `events` en las coordenadas registradas en el `events.json`.
- **Given** el slider en `Ago`, **When** el mapa ha terminado de renderizar, **Then** el marker `heatwave_aug` es visible y el marker `bonfire_night` **no** está presente en la capa `events`.
- **Given** el slider en cualquier posición (incluido `Anual`), **When** el mapa está renderizado, **Then** el marker del evento `covid_context` es visible.
- **Given** un marker de evento visible en el mapa, **When** el usuario hace `click` sobre él, **Then** aparece un popup con los campos no vacíos: `título` (≤ 40 caracteres), `fecha` en formato `D de <mes> YYYY` y `descripción` entre 50 y 300 caracteres sin jerga técnica.
- **Given** el gráfico 3A renderizado, **When** se inspecciona el eje X, **Then** bajo `Nov` aparece el icono `🎆`, bajo `Ago` el icono `🌡️`, bajo `Ene` el icono `🔥/📋` del evento `heating_jan` y bajo `Mar` dos iconos (`🚦` de `easter_traffic` y `📋` de `caz_eval`); un hover sobre cualquier icono muestra tooltip con título + descripción corta.

---

## Feature 5 — Vista LSOA (Barrios)

### Qué queremos

Un toggle que conmuta entre tramos de calle y barrios (LSOAs — zonas censales UK). En lugar de 8.450 líneas, el usuario ve 302 polígonos coloreados por el PM2.5 medio del barrio.

### Por qué importa

Los tramos son precisos pero difíciles de interpretar a nivel ciudad. Un concejal necesita saber *"¿qué barrios tienen mayor problema?"*. La vista LSOA responde esa pregunta.

Las LSOAs son, además, la unidad de datos del ONS (Census UK) y del NHS. Cuando crucemos contaminación con datos de salud o deprivación social (el próximo paso científico del proyecto), la unidad de comparación es el LSOA. La vista ya debe estar lista.

Los datos existen: `lur_lsoa_predictions.geojson` tiene 302 LSOAs con PM2.5, PM10 y score A–F.

### Datos disponibles (resumen para el equipo)

- **302 LSOAs** con `pm25_final` (media anual 2024).
- Rango PM2.5: **5,93 µg/m³** (Liverpool 061A, zona sur) a **14,97 µg/m³** (Liverpool 017E, Vauxhall).
- Distribución de score: 154 LSOAs con B (51%), 148 con C (49%).
- **Ningún LSOA tiene score A** (ninguno por debajo de 5 µg/m³ a nivel de media de barrio).

Los LSOAs con peor score están todos en el norte y centro de Liverpool (zonas industriales y portuarias históricas). Las mejores están en el sur y áreas periféricas con más cobertura vegetal.

### Comportamiento detallado

**Toggle:**

```
[ Calles (8.450) ]  [ Barrios — LSOA (302) ]
       ↑
  activo por defecto
```

Al activar `Barrios`:
- La capa `streets-line` se oculta.
- Se muestra la capa de polígonos LSOA con `fill-color` según `pm25_final`.
- Misma escala A–F que las calles.
- Los bordes de los LSOAs son visibles (línea blanca fina) para distinguir barrios contiguos.

Al volver a `Calles`:
- La capa LSOA se oculta.
- La capa `streets-line` reaparece.

**Opacidad:** polígonos LSOA con `fill-opacity = 0.7` para que el basemap sea visible debajo.

**Etiquetas opcionales:** en zoom ≥ 13 se muestra el nombre del LSOA (p. ej. `Liverpool 017E`) en el propio mapa. En zoom < 13, no se muestran (demasiado texto).

**Comportamiento del slider en vista LSOA:** la vista LSOA es sólo anual (no existen GeoJSONs mensuales por LSOA en esta versión). Si el usuario está en vista LSOA e intenta mover el slider, los controles se presentan deshabilitados con tooltip: *"La vista por barrios usa datos anuales (2024). Cambia a vista por calles para explorar la estacionalidad."*

### Wireframe vista LSOA

```
┌─────────────────────────────────────────────────────────┬──────────┐
│                                                         │ PANEL    │
│   [MAPA — polígonos LSOA coloreados]                    │          │
│                                                         │ Toggle:  │
│   Liverpool 017E (Vauxhall)                             │ [Calles] │
│   ████████████ C — 14,97 µg/m³                          │ [Barrios]│
│                                                         │ ←activo  │
│   Liverpool 061A (sur)                                  │          │
│   ████ B — 5,93 µg/m³                                   │ Gráficos │
│                                                         │ (anuales)│
│                                        [Leyenda A–F]    │          │
└─────────────────────────────────────────────────────────┴──────────┘
```

### Criterios de aceptación (BDD)

- **Given** la vista `Calles` activa, **When** el usuario pulsa el toggle `Barrios`, **Then** la capa `streets-line` pasa a `visibility: none` y la capa `lsoa-fill` pasa a `visibility: visible`, sin recargar la URL ni la página.
- **Given** la vista `Barrios` activa en zoom 11 o 12, **When** el mapa se renderiza, **Then** los 302 polígonos son visibles con `fill-opacity = 0,7` y los bordes se dibujan con línea blanca fina.
- **Given** la vista `Barrios` activa, **When** se inspecciona el polígono `Liverpool 017E`, **Then** su score es `C` y su `fill-color` es `#ffc800` (amarillo), correspondiente al rango 10–15 µg/m³.
- **Given** la vista `Barrios` activa, **When** se inspecciona el polígono `Liverpool 061A`, **Then** su score es `B` y su `fill-color` es `#c8e632` (amarillo-verde).
- **Given** la vista `Barrios` activa, **When** el usuario intenta interactuar con el slider de meses, **Then** los controles aparecen con `opacity` reducida y, al hover, se muestra el tooltip literal: *"La vista por barrios usa datos anuales (2024). Cambia a vista por calles para explorar la estacionalidad."*
- **Given** la vista `Barrios` activa, **When** el usuario hace `click` en `Liverpool 017E`, **Then** la InfoCard muestra nombre `Liverpool 017E — Vauxhall`, PM2.5 = `14,97 µg/m³`, score `C` y la línea `Posición: #1 de 302 barrios`.

---

## Feature 6 — Tooltips de Calle (InfoCard)

### Qué queremos

Al hacer click en cualquier tramo (o barrio en vista LSOA) aparece una card con los datos de ese objeto. No un tooltip básico de Mapbox — una card diseñada con contexto regulatorio explícito.

### Por qué importa

El mapa sin tooltips es una imagen. Con tooltips es una herramienta de consulta. Un analista del Council puede buscar una calle específica, hacer click, y llevarse los datos a su informe. Un periodista puede hacer lo mismo para un artículo.

La card es, además, la única parte de la UI donde mostramos los números crudos (PM2.5 = 14,2 µg/m³) con contexto regulatorio explícito. En el resto de la app usamos colores y scores; aquí usamos números.

### Comportamiento detallado

**Cuándo aparece:**
- Click en cualquier tramo de calle (capa `streets-line`) → card para tramo.
- Click en cualquier polígono LSOA (capa `lsoa-fill`) → card para barrio.
- Click en fondo del mapa (sin feature) → la card desaparece.

**Posición:** flotante sobre el mapa, esquina inferior izquierda. No sigue al cursor — fija en esa esquina para no tapar el resto del mapa. Si el click ocurre en la esquina inferior izquierda, la card se reubica a la inferior derecha para evitar solaparse con la feature seleccionada.

**Card para tramo de calle:**

```
┌───────────────────────────────────────┐
│  Scotland Road                    ×   │
│  Vía principal (primary)              │
│                                       │
│         [ D ]  15,8 µg/m³             │
│         PM2.5 · Enero 2024            │
│                                       │
│  ████████████████░░░░░  (barra 0–30)  │
│                                       │
│  🔴 OMS 2021:    5 µg/m³   × 3,2      │
│  🟠 UK 2040:    10 µg/m³   × 1,6      │
│  ⚪ UK actual:  20 µg/m³   ✓ cumple    │
│                                       │
│  PM10: 29,4 µg/m³                     │
└───────────────────────────────────────┘
```

El `×N` del score es cuántas veces se supera el límite OMS. Es el dato que más impacta en una presentación.

**Card para LSOA:**

```
┌───────────────────────────────────────┐
│  Liverpool 017E — Vauxhall        ×   │
│  Barrio (LSOA)                        │
│                                       │
│         [ C ]  14,97 µg/m³            │
│         PM2.5 medio anual 2024        │
│                                       │
│  ████████████████░░░░░  (barra 0–20)  │
│                                       │
│  🔴 OMS 2021:    5 µg/m³   × 3,0      │
│  🟠 UK 2040:    10 µg/m³   × 1,5      │
│                                       │
│  PM10 medio: 27,2 µg/m³               │
│  Posición: #1 de 302 barrios          │
│  (el más contaminado de Liverpool)    │
└───────────────────────────────────────┘
```

**Si el nombre del tramo es null** (muchas calles pequeñas no tienen nombre en OSM): mostrar `Calle sin nombre · <tipo_via>`.

**Animación:** fade-in de 150 ms al abrir. Cierre instantáneo.

**El mes afecta los datos:** si el slider está en julio, la card muestra `PM2.5 · Julio 2024` con los valores de julio. Si está en `Anual`, muestra `PM2.5 anual 2024`. Los valores cambian visiblemente entre meses (en julio, Scotland Road puede bajar de D a C).

### Criterios de aceptación (BDD)

- **Given** el mapa en vista `Calles` con datos anuales, **When** el usuario hace `click` sobre cualquier tramo de Scotland Road, **Then** la InfoCard aparece en menos de 150 ms con `road_type = primary`, score `D` o `C` y PM2.5 en el rango 10–20 µg/m³.
- **Given** una InfoCard abierta para un tramo con PM2.5 = 14,97 µg/m³, **When** se inspecciona la fila `OMS 2021`, **Then** muestra `5 µg/m³` y `× 3,0` (resultado de `14,97 / 5` redondeado a un decimal).
- **Given** una InfoCard abierta, **When** el usuario hace `click` en una zona del mapa sin features (agua, parque, área vacía), **Then** la InfoCard desaparece aplicando fade-out de 150 ms.
- **Given** una InfoCard abierta con datos anuales de Scotland Road, **When** el usuario mueve el slider a `Jul`, **Then** el contenido de la card se actualiza en menos de 500 ms mostrando los valores de julio **sin cerrar ni re-abrir** la card (el elemento DOM persiste).
- **Given** la vista `Barrios` activa, **When** el usuario hace `click` en el polígono `Liverpool 017E`, **Then** la card muestra exactamente la línea `Posición: #1 de 302 barrios`.
- **Given** un tramo cuyo campo `name == null` en el GeoJSON, **When** el usuario hace `click` y se abre la InfoCard, **Then** el título se renderiza como `Calle sin nombre · <road_type>` y no aparecen nunca las cadenas `null` ni `undefined`.

---

## Layout global y responsive

### Desktop (≥ 1024 px)

```
┌───────────────────────────────────────────────┬────────────────┐
│                                               │                │
│  MAPA (flex: 1, full height)                  │ PANEL LATERAL  │
│                                               │ (320 px fixed) │
│  ┌─────────────────────────────────────────┐  │                │
│  │ MonthSlider (posición fija, top)        │  │                │
│  └─────────────────────────────────────────┘  │                │
│                                               │                │
│  [Markers de eventos]                         │                │
│  [InfoCard — bottom left]                     │                │
│                           [Leyenda — bot right]                │
└───────────────────────────────────────────────┴────────────────┘
```

### Tablet (768–1023 px)

El panel lateral se convierte en drawer accesible desde el botón `Datos` en la barra inferior. El slider de meses permanece visible encima del mapa.

### Móvil (< 768 px)

- El mapa ocupa el 100% de la pantalla.
- La leyenda se minimiza a un icono.
- Slider y panel son drawers desde abajo.
- Los tooltips de tramo se abren como sheet modal (no como card flotante).

### Accesibilidad y compatibilidad de navegadores

**Nivel de accesibilidad objetivo:** WCAG 2.1 AA — requerido para contratos B2G con el Liverpool City Council y el NHS.

**Verificaciones obligatorias antes de la presentación al Council:**
- Contraste de la paleta A–F: ratio mínimo 4.5:1 para cualquier texto renderizado sobre los colores de score.
- Todos los controles interactivos (slider, toggle Calles/Barrios, InfoCard, markers de eventos) operables mediante teclado (Tab + Enter/Space).
- Iconos de eventos y leyenda con texto alternativo accesible.
- Auditoría con Lighthouse Accessibility o axe DevTools — puntuación objetivo ≥ 90.

**Navegadores soportados:**

| Navegador | Versión mínima |
|-----------|----------------|
| Chrome | 120+ |
| Firefox | 120+ |
| Edge | 120+ |
| Safari | 17+ |

> IE y navegadores con más de 2 años sin soporte mainstream están fuera de scope.

---

## Qué NO construir en esta versión

Para que el equipo no disperse esfuerzo en lo que está fuera de scope:

- ❌ Login / autenticación
- ❌ API keys o rate limiting
- ❌ Búsqueda por dirección (v1.1)
- ❌ Datos en tiempo real
- ❌ Otras ciudades
- ❌ Comparativa entre LSOAs seleccionados (v1.1)
- ❌ Exportar PDF o informe (v1.1)
- ❌ Modo oscuro/claro toggle — solo modo oscuro

---

## Requisitos No Funcionales

### Performance

| ID | NFR | Criterio | Condición de medición | Método |
|----|-----|----------|-----------------------|--------|
| NFR-01 | Carga inicial del mapa | < 3.000 ms hasta mapa con 8.450 tramos renderizado | Conexión ≥ 20 Mbps, caché vacía, percentil 95 | Performance API + DevTools Network throttle |
| NFR-02 | Transición slider — primera carga | < 1.000 ms desde click hasta primer frame con datos del mes | Primera selección de un mes, sin caché en memoria | `performance.now()` en evento `sourcedata` con `isSourceLoaded === true` |
| NFR-03 | Transición slider — caché | < 150 ms desde click hasta render completo | Mes previamente cargado en caché de memoria | Performance API |
| NFR-04 | Actualización del panel EDA | < 500 ms para actualización de gráficos 3B y 3C | Cualquier cambio de mes activo | Observación visual + DevTools |
| NFR-05 | InfoCard | < 150 ms desde click hasta card visible | Cualquier tramo o polígono LSOA | Performance API |

### Accesibilidad

| ID | NFR | Criterio | Estándar de referencia |
|----|-----|----------|------------------------|
| NFR-06 | Conformidad WCAG | Nivel AA en todos los componentes interactivos | WCAG 2.1 W3C |
| NFR-07 | Contraste de color | Ratio ≥ 4.5:1 para texto sobre colores de la paleta A–F | WCAG 1.4.3 |
| NFR-08 | Navegación por teclado | Todos los controles operables sin ratón (Tab + Enter/Space) | WCAG 2.1.1 |
| NFR-09 | Puntuación de auditoría | Lighthouse Accessibility ≥ 90 en desktop y móvil | Google Lighthouse |

### Compatibilidad

| ID | NFR | Criterio |
|----|-----|----------|
| NFR-10 | Navegadores | Chrome 120+, Firefox 120+, Edge 120+, Safari 17+ |
| NFR-11 | Resolución mínima | Funcional en viewport ≥ 320 px de ancho |
| NFR-12 | Sin autenticación | Ninguna funcionalidad requiere login, API key ni sesión en esta versión |

### Disponibilidad y hosting

| ID | NFR | Criterio | Notas |
|----|-----|----------|-------|
| NFR-13 | Uptime | ≥ 99% mensual durante el período de evaluación CAZ 2026 | Medido por monitor externo (UptimeRobot o similar) |
| NFR-14 | Latencia de red | Tiempo de respuesta del CDN < 200 ms desde UK | Supabase Storage + CDN (Vercel/Netlify) |
| NFR-15 | Datos sin autenticación | Los GeoJSONs en Supabase Storage accesibles públicamente sin token | Bucket configurado como `public` |

---

## Datos de referencia para el equipo

Estos números son la fuente de verdad para los tests automatizados y para la verificación manual:

| Dato | Valor | Fuente |
|------|-------|--------|
| Tramos totales | 8.450 | `liverpool_pollution_map.geojson` |
| PM2.5 mínimo (anual) | 4,87 µg/m³ | Misma fuente |
| PM2.5 máximo (anual) | 28,10 µg/m³ | Misma fuente |
| PM2.5 medio Liverpool | 9,98 µg/m³ | Misma fuente |
| LSOAs totales | 302 | `lur_lsoa_predictions.geojson` |
| LSOA más contaminado | Liverpool 017E, 14,97 µg/m³ | Misma fuente |
| LSOA más limpio | Liverpool 061A, 5,93 µg/m³ | Misma fuente |
| LSOAs con score B | 154 (51%) | Misma fuente |
| LSOAs con score C | 148 (49%) | Misma fuente |
| LSOAs con score A | 0 (0%) | Dato clave para comunicación B2G |
| Modelo | SVR (LUR) | `outputs/models/lur_model_PM25.pkl` |
| R² PM2.5 (LOOCV) | 0,602 | `docs/08_lur_improvement_session.md` |
| R² PM10 (LOOCV) | 0,581 | Misma fuente |

---

## Preguntas frecuentes del equipo

**¿Por qué no hay score A en ningún LSOA?**
Porque el umbral A (< 5 µg/m³) es el objetivo OMS 2021, que ninguna ciudad urbana del norte de UK cumple actualmente. El LSOA más limpio tiene 5,93 µg/m³ — muy cerca pero sin llegar. Es un hecho científico, no un bug. A nivel de tramo individual sí hay algún caso marginal (mínimo 4,87 µg/m³), por eso los contadores del panel 3D se calculan en runtime sobre el GeoJSON.

**¿El modelo es 100% preciso?**
No. R² = 0,60 significa que el modelo explica el 60% de la varianza observada en los 21 sensores. Los intervalos de confianza son ±0,76 µg/m³ en la media. Este valor se comunica en el footer de la app; está en el rango alto de la literatura LUR aceptada (R² entre 0,5 y 0,7 es el estándar internacional). No para debilitar el producto, sino para ser científicamente honestos.

**¿Los datos del slider son predicciones o medidas reales?**
Son **predicciones del modelo SVR alimentadas con la meteorología real observada** de cada mes de 2024. Las variables espaciales (land use, roads) son constantes; lo que cambia mes a mes es temperatura, viento y lluvia. Es un modelo calibrado con datos reales, no una simulación sintética.

**¿Por qué Supabase Storage en vez de incluir los GeoJSONs en el repo?**
Los 12 mensuales pesan ~6–8 MB cada uno + el anual ≈ 100 MB totales. Eso no va en un repo Git. Supabase Storage es gratuito hasta 1 GB, sirve con CDN y soporta compresión Brotli/Gzip. Con compresión, cada archivo viaja a ~500–800 KB por la red (ver Feature 2 · Notas técnicas). Mejor latencia y menor coste que servir desde el repo.

---

_PRD v1.1 · 2026-04-17 · Refinado bajo metodología BMAD. Para especificación técnica: `mvp/TECHNICAL_SPEC.md` v0.2.0 y `mvp/PROCEDIMIENTO_MVP.md` v2.0._
