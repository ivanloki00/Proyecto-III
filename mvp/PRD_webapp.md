# AirTrace — Product Requirements Document (Web App)

**Para:** Equipo de desarrollo  
**De:** Business Owner  
**Fecha:** 2026-04-17  
**Versión:** 1.0

---

## Contexto para el equipo

Hemos construido un modelo científico que predice los niveles de PM2.5 y PM10 (partículas contaminantes) en cada calle de Liverpool. Tenemos:

- **8.450 tramos de calle** con predicciones anuales (media 2024)
- **21 sensores IoT** reales desplegados por la ciudad — son los datos de entrenamiento del modelo
- **12 meses** de datos mensuales (enero–diciembre 2024) que permiten ver estacionalidad
- **302 barrios** (LSOAs — zonas censales UK) con predicciones agregadas
- Modelo validado: R² = 0.60 (PM2.5), R² = 0.58 (PM10)

El producto es una **web app pública** para mostrar estos resultados. No hay login. No hay API comercial. El objetivo de esta primera versión es tener algo que enseñarle a Liverpool City Council en una reunión.

**Los datos muestran algo concreto:** ninguna calle de Liverpool cumple el límite de la OMS (5 µg/m³). El 49% de los barrios supera incluso el objetivo UK para 2040 (10 µg/m³). Eso tiene implicaciones de política pública.

---

## Principios de diseño

1. **Los datos son el protagonista.** La UI existe para que los datos hablen, no al revés.
2. **Un no-técnico tiene que entenderlo en 30 segundos.** El score A–F es la interfaz primaria; los números exactos son secundarios.
3. **Cada número tiene contexto.** PM2.5 = 12.4 µg/m³ dice poco. "PM2.5 = 12.4 µg/m³ — 2.5 veces el límite de la OMS" dice mucho.
4. **El mapa es el centro.** Todo lo demás (panel, slider, popups) sirve al mapa.

---

## Feature 1 — Mapa de Contaminación Base

### Qué queremos

El mapa muestra Liverpool con cada calle coloreada según su nivel de PM2.5. A primera vista, sin hacer nada, el usuario ve qué zonas son más limpias y cuáles son más contaminadas.

### Por qué importa

Cuando le enseñemos esto al Council, la primera pregunta será: *"¿dónde están las calles más contaminadas?"*. La respuesta tiene que ser visual e inmediata. No un Excel. No una tabla. El mapa.

### Comportamiento detallado

**Carga inicial:**
- El mapa arranca centrado en Liverpool, zoom 12, estilo oscuro (dark-v11 de Mapbox)
- En los primeros 3 segundos se cargan los 8.450 tramos coloreados
- Mientras carga: spinner + texto "Cargando mapa de Liverpool..."

**Escala de color (fija, no negociable):**

| Score | Rango PM2.5 | Color | Referencia |
|-------|-------------|-------|------------|
| A | < 5 µg/m³ | Verde `#00c864` | Cumple OMS |
| B | 5–10 µg/m³ | Amarillo-verde `#c8e632` | Cumple UK 2040 |
| C | 10–15 µg/m³ | Amarillo `#ffc800` | Supera UK 2040 |
| D | 15–20 µg/m³ | Naranja `#ff8200` | Zona preocupante |
| E | 20–25 µg/m³ | Rojo `#e63232` | Zona crítica |
| F | ≥ 25 µg/m³ | Morado `#960096` | Zona de acción urgente |

> **Nota para el equipo:** En los datos anuales de 2024, **ningún tramo de Liverpool tiene score A**. Los scores observados son B (calles periféricas en zonas verdes) y C/D en el centro y vías principales. Algunos tramos con tráfico intenso alcanzan E/F. Esto es lo que queremos que sea visible.

**Grosor de línea:** fino en zoom out (1–2px), más grueso al hacer zoom in (3–4px). Así el mapa no es un borrón de colores a nivel ciudad.

**Mapa base:** estilo oscuro para que los colores de la capa de contaminación resalten. No usar estilo claro — los colores se pierden.

**Leyenda fija:** esquina inferior derecha, siempre visible, no colapsable. Muestra los 6 scores con su color y rango.

```
┌─────────────────────┐
│ Calidad del aire     │
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
│                                                         │         │
│          [MAPA DE LIVERPOOL — fondo oscuro]             │ PANEL   │
│                                                         │ LATERAL │
│    Tramos coloreados:                                   │         │
│    Centro/vías principales → naranja/rojo               │ (ver    │
│    Zonas residenciales → amarillo                       │ Feature │
│    Zonas verdes/periféricas → amarillo-verde            │  3)     │
│                                                         │         │
│                                        [Leyenda A–F]   │         │
└─────────────────────────────────────────────────────────┴──────────┘
```

### Criterio de aceptación

- [ ] El mapa carga en < 3 segundos en una conexión normal (cable/WiFi)
- [ ] Los 8.450 tramos son visibles en zoom 12 (nivel ciudad completa)
- [ ] La escala de color es correcta: el centro de Liverpool es más oscuro (más contaminado) que las zonas periféricas
- [ ] La leyenda es visible en todos los tamaños de pantalla

---

## Feature 2 — Slider de Meses (Estacionalidad)

### Qué queremos

Un slider o selector de meses que permite ver cómo cambia la contaminación mes a mes a lo largo de 2024. El mapa se actualiza al seleccionar un mes distinto.

### Por qué importa

Los datos anuales dicen *cuánto* hay de contaminación. Los datos mensuales dicen *por qué*. En UK, el PM2.5 es un 25–30% mayor en invierno (calefacción + inversión térmica + menos viento) que en verano. Eso es información accionable: si el Council necesita justificar una intervención, puede apuntar a los meses de invierno como prioridad.

Además, esto es lo que diferencia nuestro producto de un mapa estático. Cualquiera puede hacer un mapa. El slider convierte el mapa en una herramienta de análisis temporal.

### Datos disponibles

Los 12 GeoJSONs mensuales se generan corriendo el modelo SVR con los datos meteorológicos reales de cada mes (temperatura, viento, lluvia) mientras las variables espaciales (land use, roads) se mantienen constantes. Esto captura la variación estacional con datos reales.

Variación esperada (referencia para validar que el slider funciona):

| Mes | PM2.5 medio estimado | Razón |
|-----|---------------------|-------|
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

- "Anual" es la posición por defecto y muestra la media de 2024
- Al seleccionar un mes: el mapa se actualiza con los datos de ese mes
- La transición del mapa debe ser suave (fade de < 500ms), no un parpadeo brusco

**Feedback visual mientras carga el mes:**
- El slider muestra un indicador de carga en el mes seleccionado mientras el GeoJSON se descarga
- El mapa no desaparece — se mantiene el estado anterior hasta que el nuevo está listo

**Información contextual del mes activo:**
Debajo del slider, una línea de texto con los datos meteorológicos de ese mes:
```
Julio 2024  ·  Temp. media: 18.3°C  ·  Viento: 4.2 m/s  ·  Días de lluvia: 8
```
Estos datos vienen del `monthly_stats.json`.

**Indicador de estacionalidad:**
El fondo o borde de cada botón de mes se colorea sutilmente según el PM2.5 medio de ese mes (usando la misma paleta de la leyenda). Así el usuario ve de un vistazo que enero/diciembre son "más naranjas" y julio/agosto "más verdes".

### Wireframe del slider

```
┌──────────────────────────────────────────────────────────────────────┐
│  ANUAL  ENE  FEB  MAR  ABR  MAY  JUN  JUL  AGO  SEP  OCT  NOV  DIC  │
│         [■]  [■]  [□]  [□]  [□]  [□]  [□]  [□]  [□]  [□]  [■]  [■] │
│          ↑ color de fondo = PM2.5 del mes                             │
│                                                                       │
│  Enero 2024  ·  Temp: 6.2°C  ·  Viento: 5.1 m/s  ·  Lluvia: 14 días │
└──────────────────────────────────────────────────────────────────────┘
```

### Criterio de aceptación

- [ ] El mapa en enero muestra colores visiblemente más oscuros (más contaminación) que en julio
- [ ] La transición entre meses tarda < 1 segundo en conexión normal
- [ ] Los datos meteorológicos del mes se muestran correctamente bajo el slider
- [ ] "Anual" como posición por defecto carga el GeoJSON de media anual, no el de enero

---

## Feature 3 — Panel EDA (Gráficos de Tendencia)

### Qué queremos

Un panel lateral con gráficos que complementan el mapa. No solo "dónde" está la contaminación, sino "cómo evoluciona" y "quién contribuye más".

### Por qué importa

En una reunión con el Council, el mapa es lo primero que ven. Pero el analista de datos del Council va a querer gráficos que pueda copiar a su presentación de PowerPoint. Sin gráficos, somos un mapa bonito. Con gráficos, somos una herramienta de análisis.

Los gráficos también responden preguntas que el mapa no puede: ¿cuál es el peor mes del año? ¿Las calles primarias están mucho peor que las residenciales? ¿Qué zona de la ciudad tiene la mayor variación estacional?

### Componentes del panel

#### 3A — Gráfico de tendencia mensual (principal)

**Título:** "PM2.5 y PM10 — Evolución mensual 2024"

Gráfico de línea con:
- Eje X: meses (Ene–Dic)
- Eje Y izquierdo: PM2.5 (µg/m³), rango 0–20
- Eje Y derecho: PM10 (µg/m³), rango 0–35 — misma escala proporcional para que ambas líneas sean comparables visualmente
- Línea azul: PM2.5 medio de toda Liverpool ese mes
- Línea naranja: PM10 medio
- Línea roja punteada horizontal: 5 µg/m³ (límite OMS) — etiquetada "OMS"
- Línea naranja punteada horizontal: 10 µg/m³ (objetivo UK 2040) — etiquetada "UK 2040"
- Área sombreada entre la línea PM2.5 y el límite OMS (siempre por encima — todo Liverpool supera la OMS)
- **Sincronización con el mapa:** cuando el usuario selecciona un mes en el slider, ese punto del gráfico se resalta con un círculo más grande y un tooltip. Y al revés: hacer click en un punto del gráfico mueve el slider del mapa a ese mes.

**Insight clave que debe ser obvio:** la línea PM2.5 nunca baja por debajo de la línea roja de la OMS — ni en el mes más limpio (julio). Esto es lo que queremos que el Council vea.

#### 3B — Distribución por tipo de vía

**Título:** "PM2.5 medio por tipo de calle — Mes seleccionado"

Gráfico de barras horizontal con 4 categorías:
- `primary` — vías principales (Scotland Road, Queens Drive...)
- `secondary` — vías secundarias
- `residential` — calles residenciales
- `other` — resto

Cada barra:
- Coloreada con el color de la paleta según su valor
- Muestra el valor numérico al final de la barra
- Se actualiza cuando cambia el mes seleccionado

**Por qué este gráfico:** permite demostrar que vivir en una calle residencial no implica menos contaminación que vivir en una vía principal. En Liverpool, la diferencia es de ~2–3 µg/m³ — suficiente para pasar de score C a score B, pero ambas están por encima de la OMS.

```
primary      ████████████████████ 15.2 µg/m³  [D]
secondary    ████████████████░░░  13.1 µg/m³  [C]
residential  █████████████░░░░░░  11.3 µg/m³  [C]
other        ███████████░░░░░░░░  10.1 µg/m³  [C]
                                  ↑ referencia OMS
```

#### 3C — Top 5 tramos más contaminados

**Título:** "Calles más contaminadas · Mes seleccionado"

Lista simple de 5 filas:
```
1. Scotland Road           [D]  16.8 µg/m³
2. Queens Drive            [D]  16.2 µg/m³
3. Edge Lane               [C]  15.9 µg/m³
4. Vauxhall Road           [C]  15.4 µg/m³
5. Commercial Road         [C]  14.9 µg/m³
```

Click en cualquiera de ellas: el mapa vuela a esa calle y la resalta.

#### 3D — Contador de calles por encima de umbrales

Tres números grandes, siempre visibles en la parte superior del panel:

```
┌──────────┬──────────┬──────────┐
│  8.450   │  8.450   │  4.161   │
│  tramos  │ > OMS    │ > UK2040 │
│  totales │ (100%)   │  (49%)   │
└──────────┴──────────┴──────────┘
```

Estos números se actualizan con el mes seleccionado. En julio el "% > OMS" puede bajar — eso es interesante.

### Diseño del panel

Panel fijo lateral derecho, 320px de ancho, fondo semitransparente oscuro. Scroll interno si el contenido no cabe. No colapsa — siempre visible en desktop. En móvil se convierte en un drawer desde abajo.

```
┌──────────────────────────────┐
│ AirTrace   Liverpool 2024    │
│ [Calles ▼] [Barrios]        │
├──────────────────────────────┤
│ 8.450   8.450   4.161        │
│ tramos  >OMS   >UK2040      │
├──────────────────────────────┤
│                              │
│  [Gráfico tendencia mensual] │
│   PM2.5 ── PM10 ──          │
│   ── OMS  ── UK2040         │
│                              │
├──────────────────────────────┤
│ Por tipo de calle            │
│ primary    ████ 15.2 [D]    │
│ secondary  ███  13.1 [C]    │
│ residential██   11.3 [C]    │
├──────────────────────────────┤
│ Top 5 calles                 │
│ 1. Scotland Rd  16.8 [D]    │
│ 2. Queens Drive 16.2 [D]    │
│ ...                          │
├──────────────────────────────┤
│ Datos: SVR LUR · R²=0.60    │
│ 21 sensores IoT · 2024      │
└──────────────────────────────┘
```

### Criterio de aceptación

- [ ] El gráfico de tendencia muestra 12 puntos, uno por mes
- [ ] Las líneas de referencia OMS (5) y UK2040 (10) son visibles y etiquetadas
- [ ] Hacer click en un mes del gráfico mueve el slider del mapa a ese mes
- [ ] El gráfico de barras se actualiza al cambiar de mes
- [ ] El top 5 muestra valores consistentes con los datos del GeoJSON del mes activo
- [ ] Los contadores del header muestran 8.450 tramos totales y 100% > OMS

---

## Feature 4 — Eventos Canónicos

### Qué queremos

Marcadores contextuales en el mapa y en el timeline que explican los picos o valles de contaminación. Cuando el usuario ve que noviembre es el peor mes, hay un popup que le explica por qué: Bonfire Night.

### Por qué importa

Los datos sin contexto son ruido. Los datos con contexto son inteligencia. Cuando el Council pregunta "¿por qué en agosto hay menos contaminación?", la respuesta tiene que estar en el producto, no en la cabeza del vendedor.

Además, los eventos dan vida al mapa. Un mapa estático es académico. Un mapa que dice "este mes hay fuegos artificiales" es algo que la gente entiende y recuerda.

### Lista de eventos (con justificación científica)

| ID | Fecha | Mes | Título | Tipo | Impacto en datos |
|----|-------|-----|--------|------|-----------------|
| `bonfire_night` | 5 Nov 2024 | 2024-11 | Bonfire Night | seasonal | Pico de PM2.5 y PM10 de 1–3 días. Los sensores de Liverpool registran aumentos de hasta 3× la media diaria. Noviembre suele ser el mes con el PM2.5 más alto del año. |
| `heatwave_aug` | 12 Ago 2024 | 2024-08 | Ola de calor | climate | Temperaturas > 28°C aceleran la dispersión atmosférica. Agosto es el mes más limpio de 2024. Paradoja: el calor mejora la calidad del aire en PM2.5 aunque empeora el ozono troposférico (no medido aquí). |
| `heating_jan` | 15 Ene 2024 | 2024-01 | Temporada de calefacción | seasonal | Inicio del invierno. Combinación de calefacción doméstica + inversión térmica + viento < 3 m/s = concentración máxima de PM2.5. Enero es históricamente el mes más contaminado en ciudades del norte de UK. |
| `easter_traffic` | 29 Mar 2024 | 2024-03 | Semana Santa — Reducción de tráfico | traffic | El fin de semana de Pascua reduce el tráfico laboral ~40% en Liverpool. Los sensores en vías principales muestran caída de PM2.5. Pequeño experimento natural de qué ocurre si se reduce el tráfico. |
| `caz_eval` | 15 Mar 2024 | 2024-03 | Liverpool CAZ — Evaluación activa | policy | Liverpool City Council inicia evaluación formal de Clean Air Zone (CAZ). Los datos de este período son los primeros disponibles durante el proceso oficial de evaluación. AirTrace es la única fuente con resolución de tramo de calle para este proceso. |
| `covid_context` | 23 Mar 2020 | *contexto* | Confinamiento COVID-19 (referencia) | policy | Durante el confinamiento de 2020, el NO2 en Liverpool cayó ~45% y el PM2.5 ~15%. Sirve como experimento natural que demuestra el impacto del tráfico. No tenemos datos de 2020, pero este contexto explica por qué el tráfico importa. |

### Comportamiento detallado

**En el mapa:**
- Cada evento con `lat/lng` (todos excepto COVID que es global) se muestra como un marker
- Icono según tipo: 🎆 seasonal · 🌡️ climate · 📋 policy · 🚦 traffic
- El marker solo aparece si el mes del evento coincide con el mes seleccionado en el slider
- El evento COVID aparece siempre (es contexto histórico, no tiene mes)
- Click en marker → popup con: título, fecha, explicación en lenguaje natural, impacto en el dato

**En el gráfico de tendencia (panel EDA):**
- En el eje X del gráfico, debajo del mes correspondiente, aparece un pequeño icono del tipo de evento
- Hover sobre el icono → tooltip con título y descripción corta
- Esto conecta visualmente "el pico de noviembre" con "Bonfire Night"

**Popup del evento — diseño:**
```
┌──────────────────────────────────────────┐
│ 🎆 Bonfire Night                  × │
│ 5 de noviembre 2024                       │
├──────────────────────────────────────────┤
│ Los fuegos artificiales del 5 de          │
│ noviembre generan picos de PM2.5 y PM10   │
│ de corta duración. Los sensores de        │
│ Liverpool registran aumentos de hasta     │
│ 3× la media diaria.                       │
│                                           │
│ Noviembre es el mes con mayor             │
│ contaminación media de 2024.              │
└──────────────────────────────────────────┘
```

### Criterio de aceptación

- [ ] En el mes de noviembre: el marker de Bonfire Night es visible en el mapa
- [ ] En el mes de agosto: el marker de la ola de calor es visible, el de Bonfire Night no
- [ ] El evento COVID es visible en todos los meses
- [ ] El popup tiene título, fecha, y descripción comprensible para un no-técnico
- [ ] En el gráfico de tendencia, noviembre tiene un icono 🎆 bajo el punto de datos

---

## Feature 5 — Vista LSOA (Barrios)

### Qué queremos

Un toggle que cambia la vista del mapa de tramos de calle a barrios (LSOAs — zonas censales UK). En vez de 8.450 líneas, el usuario ve 302 polígonos coloreados por el nivel medio de PM2.5 del barrio.

### Por qué importa

Los tramos de calle son precisos pero difíciles de interpretar a nivel de ciudad. Un concejal necesita saber: "¿qué barrios tienen mayor problema?". La vista LSOA responde esa pregunta.

Además, las LSOAs son la unidad de datos del ONS (Census UK) y del NHS. Cuando queramos cruzar la contaminación con datos de salud o deprivación social (que es el próximo paso del proyecto científico), la unidad de comparación es el LSOA. La vista ya debe estar lista.

Los datos ya existen: el archivo `lur_lsoa_predictions.geojson` tiene 302 LSOAs con PM2.5, PM10 y score A–F.

### Datos disponibles (resumen para el equipo)

- **302 LSOAs** con PM2.5_final (media anual 2024)
- PM2.5 rango: 5.93 µg/m³ (Liverpool 061A, zona sur) a 14.97 µg/m³ (Liverpool 017E, Vauxhall)
- Score distribution: 154 LSOAs con B (51%), 148 con C (49%)
- **Ningún LSOA tiene score A** (ninguno por debajo de 5 µg/m³)

Los LSOAs con peor score son todos del norte/centro de Liverpool (zonas industriales y portuarias históricas). Las zonas con mejor score son el sur y las áreas periféricas con más vegetación.

### Comportamiento detallado

**Toggle:**
```
[ Calles (8.450) ]  [ Barrios — LSOA (302) ]
       ↑
  activo por defecto
```

Al activar "Barrios":
- La capa de tramos de calle se oculta
- Se muestra la capa de polígonos LSOA con fill-color según PM2.5_final
- Misma escala de color que las calles (A–F)
- Los bordes de los LSOAs son visibles (línea blanca fina) para poder distinguir barrios contiguos

Al volver a "Calles":
- La capa LSOA se oculta
- La capa de tramos reaparece

**Opacidad:** los polígonos LSOA tienen fill-opacity = 0.7 para que el mapa base sea visible debajo.

**Etiquetas opcionales:** en zoom ≥ 13, mostrar el nombre del LSOA (p. ej. "Liverpool 017E") directamente en el mapa. En zoom < 13, no mostrar etiquetas (demasiado texto).

**El slider de meses en vista LSOA:** la vista LSOA es solo anual (no hay GeoJSONs mensuales por LSOA en esta versión). Si el usuario está en vista LSOA y mueve el slider, el slider debe mostrarse deshabilitado con un tooltip: "La vista por barrios usa datos anuales (2024). Cambia a vista por calles para explorar la estacionalidad."

### Wireframe vista LSOA

```
┌─────────────────────────────────────────────────────────┬──────────┐
│                                                         │ PANEL    │
│   [MAPA — polígonos LSOA coloreados]                    │          │
│                                                         │ Toggle:  │
│   Liverpool 017E (Vauxhall)                             │ [Calles] │
│   ████████████ C — 14.97 µg/m³                         │ [Barrios]│
│                                                         │ ←activo  │
│   Liverpool 061A (sur)                                  │          │
│   ████ B — 5.93 µg/m³                                  │ Gráficos │
│                                                         │ (anuales)│
│                                        [Leyenda A–F]   │          │
└─────────────────────────────────────────────────────────┴──────────┘
```

### Criterio de aceptación

- [ ] El toggle cambia entre las dos capas sin reload de página
- [ ] Los 302 polígonos LSOA son visibles en zoom 11–12
- [ ] El LSOA Liverpool 017E (el más contaminado) tiene score C y color amarillo
- [ ] El LSOA Liverpool 061A (el más limpio) tiene score B y color amarillo-verde
- [ ] El slider se deshabilita en vista LSOA con el tooltip explicativo
- [ ] Click en un LSOA abre InfoCard con nombre del barrio, PM2.5_final, score, y posición en el ranking (ej: "#1 de 302 barrios")

---

## Feature 6 — Tooltips de Calle (InfoCard)

### Qué queremos

Al hacer click en cualquier tramo de calle (o barrio en vista LSOA), aparece una card con los datos de ese tramo. No un tooltip básico de Mapbox — una card bien diseñada con contexto.

### Por qué importa

El mapa sin tooltips es una imagen. Con tooltips, es una herramienta de consulta. Un analista del Council puede buscar una calle específica, hacer click, y tener los datos para su informe. Un periodista puede hacer lo mismo para su artículo.

La card también es la única parte de la UI donde mostramos los números crudos (PM2.5 = 14.2 µg/m³) con contexto regulatorio explícito. En el resto de la app usamos colores y scores. Aquí usamos números.

### Comportamiento detallado

**Cuándo aparece:**
- Click en cualquier tramo de calle (capa `streets-line`) → card para tramo
- Click en cualquier polígono LSOA (capa `lsoa-fill`) → card para barrio
- Click en fondo del mapa (sin feature) → la card desaparece

**Posición:** flotante sobre el mapa, esquina inferior izquierda. No sigue al cursor — está fija en esa esquina para no tapar el mapa. Si el usuario hace click en el área inferior izquierda del mapa, la card se mueve a la esquina inferior derecha.

**Card para tramo de calle:**

```
┌───────────────────────────────────────┐
│  Scotland Road                    ×   │
│  Vía principal (primary)              │
│                                       │
│         [ D ]  15.8 µg/m³           │
│         PM2.5 anual · Enero 2024      │
│                                       │
│  ████████████████░░░░░  (barra 0-30) │
│                                       │
│  🔴 OMS 2021:    5 µg/m³   × 3.2    │
│  🟠 UK 2040:    10 µg/m³   × 1.6    │
│  ⚪ UK actual:  20 µg/m³   ✓ cumple  │
│                                       │
│  PM10: 29.4 µg/m³                    │
└───────────────────────────────────────┘
```

El "×" del score: cuántas veces supera el límite de la OMS. Es el dato que más impacta en una presentación.

**Card para LSOA:**

```
┌───────────────────────────────────────┐
│  Liverpool 017E — Vauxhall        ×   │
│  Barrio (LSOA)                        │
│                                       │
│         [ C ]  14.97 µg/m³          │
│         PM2.5 medio anual 2024        │
│                                       │
│  ████████████████░░░░░  (barra 0-20) │
│                                       │
│  🔴 OMS 2021:    5 µg/m³   × 3.0    │
│  🟠 UK 2040:    10 µg/m³   × 1.5    │
│                                       │
│  PM10 medio: 27.2 µg/m³             │
│  Posición: #1 de 302 barrios         │
│  (el más contaminado de Liverpool)    │
└───────────────────────────────────────┘
```

**Si el nombre del tramo es null** (muchas calles pequeñas no tienen nombre en OSM): mostrar "Calle sin nombre" + el tipo de vía.

**Animación:** la card aparece con un fade-in de 150ms. No hay animación al cerrar (la × es instantánea).

**El mes afecta los datos:** si el slider está en julio, la card muestra "PM2.5 · Julio 2024" con los datos de julio. Si está en "Anual", muestra "PM2.5 anual 2024". Los valores cambiarán visiblemente entre meses (en julio, Scotland Road puede bajar de D a C).

### Criterio de aceptación

- [ ] Click en Scotland Road (una vía primary del centro) muestra la card con score D o C
- [ ] La card muestra "× N.N del límite OMS" con el multiplicador correcto
- [ ] Click en el fondo del mapa cierra la card
- [ ] La card se actualiza cuando cambia el mes en el slider (sin cerrar y volver a abrir)
- [ ] En vista LSOA, click en Liverpool 017E muestra "#1 de 302 barrios"
- [ ] Tramos sin nombre muestran "Calle sin nombre" en lugar de null o undefined

---

## Layout global y responsive

### Desktop (≥ 1024px)

```
┌───────────────────────────────────────────────┬───────────────┐
│                                               │               │
│  MAPA (flex: 1, full height)                  │  PANEL LATERAL│
│                                               │  (320px fixed)│
│  ┌─────────────────────────────────────────┐  │               │
│  │ MonthSlider (posición fija, top)        │  │               │
│  └─────────────────────────────────────────┘  │               │
│                                               │               │
│  [Markers de eventos]                         │               │
│  [InfoCard — bottom left]                     │               │
│                           [Leyenda — bot right│               │
└───────────────────────────────────────────────┴───────────────┘
```

### Tablet (768px–1023px)

El panel lateral se convierte en un drawer que se abre desde el botón "Datos" en la barra inferior. El slider de meses sigue visible arriba del mapa.

### Móvil (< 768px)

- El mapa ocupa el 100% de la pantalla
- La leyenda se minimiza a un icono
- El slider y el panel son drawers desde abajo
- Los tooltips de tramo se abren como sheet modal (no como card flotante)

---

## Qué NO construir en esta versión

Para que el equipo no pierda tiempo en features que no están en scope:

- ❌ Login / autenticación
- ❌ API keys o rate limiting
- ❌ Búsqueda por dirección (es v1.1)
- ❌ Datos en tiempo real
- ❌ Otras ciudades
- ❌ Comparativa entre LSOAs seleccionados (es v1.1)
- ❌ Exportar PDF o informe (es v1.1)
- ❌ Modo oscuro/claro toggle — solo modo oscuro

---

## Datos de referencia para el equipo

Estos números deben usarse para verificar que la implementación es correcta:

| Dato | Valor | Fuente |
|------|-------|--------|
| Tramos totales | 8.450 | `liverpool_pollution_map.geojson` |
| PM2.5 mínimo (anual) | 4.87 µg/m³ | Misma fuente |
| PM2.5 máximo (anual) | 28.10 µg/m³ | Misma fuente |
| PM2.5 medio Liverpool | 9.98 µg/m³ | Misma fuente |
| LSOAs totales | 302 | `lur_lsoa_predictions.geojson` |
| LSOA más contaminado | Liverpool 017E, 14.97 µg/m³ | Misma fuente |
| LSOA más limpio | Liverpool 061A, 5.93 µg/m³ | Misma fuente |
| LSOAs con score B | 154 (51%) | Misma fuente |
| LSOAs con score C | 148 (49%) | Misma fuente |
| LSOAs con score A | 0 (0%) | Dato clave para comunicación |
| Modelo | SVR | `outputs/models/lur_model_PM25.pkl` |
| R² PM2.5 (LOOCV) | 0.602 | `docs/08_lur_improvement_session.md` |
| R² PM10 (LOOCV) | 0.581 | Misma fuente |

---

## Preguntas frecuentes del equipo

**¿Por qué no hay score A en ningún LSOA?**
Porque el límite A (< 5 µg/m³) es el objetivo OMS 2021, que ninguna ciudad urbana del norte de UK cumple actualmente. El LSOA más limpio tiene 5.93 µg/m³ — muy cerca pero sin llegar. Esto es un hecho científico, no un bug.

**¿El modelo es 100% preciso?**
No. R² = 0.60 significa que el modelo explica el 60% de la varianza en los datos. Los intervalos de confianza son ±0.76 µg/m³ en la media. Hay que comunicar esto en el footer de la app — no para debilitar el producto, sino para ser científicamente honestos.

**¿Los datos del slider son predicciones o medidas reales?**
Son predicciones del modelo SVR usando los datos meteorológicos reales de cada mes de 2024. Las variables espaciales (land use, roads) son constantes — lo que cambia mes a mes es la temperatura, el viento y la lluvia. Es un modelo calibrado con datos reales, no una simulación.

**¿Por qué usar Supabase Storage en vez de incluir los archivos en el repo?**
Los archivos GeoJSON mensuales son ~6–8 MB cada uno × 12 meses + el anual = ~100 MB de archivos. Eso no va en un repo de Git. Supabase Storage es gratuito hasta 1 GB y sirve los archivos desde CDN — mejor latencia que desde el repo.

---

_PRD v1.0 · 2026-04-17 · Para preguntas técnicas: referirse a `mvp/TECHNICAL_SPEC.md` v0.2.0 y `mvp/PROCEDIMIENTO_MVP.md` v2.0_
