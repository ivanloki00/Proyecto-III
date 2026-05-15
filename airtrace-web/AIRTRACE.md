# AirTrace — Documentación de la aplicación

AirTrace es una aplicación web de visualización de calidad del aire para Liverpool (2021-2025). Combina predicciones del modelo LUR (Land Use Regression), datos de sensores IoT y geometrías administrativas para permitir exploración espacial y temporal de PM2.5 y PM10.

---

## Estructura general de la interfaz

```
┌─────────────────────────────────────────────────────────┬──────────────┐
│                                                         │  Side Panel  │
│                     Mapa Mapbox                         │   (420 px)   │
│                                                         │              │
│  [Streets | Neighbourhoods | Sensors]  [PM2.5 | PM10]   │  Header      │
│                                                         │  ─────────── │
│                              [Overlay / Factor badge]   │  Contenido   │
│                                                         │  dinámico    │
│  ┌──────────────────────────────┐  ┌────────────────┐   │  según vista │
│  │  Slider de fechas (← →) ▶   │  │  Leyenda A-F   │   │              │
│  └──────────────────────────────┘  └────────────────┘   │              │
└─────────────────────────────────────────────────────────┴──────────────┘
```

---

## Pestañas de vista (toggle superior izquierdo)

Las tres vistas son mutuamente excluyentes. Cambiar de vista limpia el popup activo.

### Streets — Calles (8 450 segmentos)

Muestra cada segmento viario del municipio de Liverpool coloreado según su concentración de contaminante.

**Origen del dato:** predicciones anuales del modelo LUR (R² = 0.60 en PM2.5 bajo LOOCV), ajustadas en tiempo real por el **factor estacional** calculado sobre la ventana temporal activa.

**Factor estacional:** promedio del campo `temporal_factor` de todas las filas dentro de la ventana `[fromYM, toYM]`. Un factor > 1 indica meses de mayor concentración (invierno); < 1 indica meses más limpios.

**Interacción:** clic en un segmento abre un **popup** con:
- Nombre de la calle y tipo de vía (`highway`)
- Badge de grado A-F con color semántico
- Concentración escalada: `base × factor estacional` (µg/m³)
- Ratio respecto al límite WHO o UK LAQM
- Ventana temporal activa

El popup se actualiza automáticamente si el usuario mueve el slider mientras está abierto.

---

### Neighbourhoods — LSOA (302 zonas)

Muestra los 302 LSOAs (Lower Super Output Areas) de Liverpool coloreados por la **media aritmética** del contaminante seleccionado sobre la ventana temporal activa.

**Interacción:**
- **Clic en un polígono** → vuela al LSOA con `fitBounds` y abre el panel de detalle lateral.
- **Borde de selección** → contorno blanco grueso sobre el LSOA activo.
- **Botón overlay** (esquina superior derecha) → activa/desactiva un contorno blanco sobre todos los LSOAs que **superan el umbral UK** (10 µg/m³ PM2.5 o 40 µg/m³ PM10). El badge muestra `N / 302 (%)`.

**Cálculo de la media ventana:**
```
mean = Σ(pred[t]) / n   para t ∈ [fromYM, toYM]
```
donde `pred` es `PM2.5_pred` o `PM10_pred` según el selector de contaminante.

---

### Sensors — Red de sensores (68 dispositivos)

Muestra los 68 sensores IoT desplegados en Liverpool. El estado de cada sensor varía mes a mes según el dataset `sensorTimeline`.

| Color en mapa | Significado |
|---|---|
| Verde (emerald) | Activo ese mes **y** incluido en el modelo final (21 dispositivos) |
| Naranja | Activo ese mes pero **excluido** por calidad o cobertura insuficiente |
| Gris oscuro | Offline ese mes |

**Nota:** los meses del período de previsión (forecast) no tienen datos reales de sensores; la app muestra el último mes conocido del timeline.

**Clic en un sensor** abre un popup con:
- Nombre del dispositivo
- `device_id`
- Estado (Active / Historical)
- Rango de fechas operativo (`date_from → date_to`)

---

## Selector de contaminante (PM2.5 / PM10)

Disponible solo en vistas **Streets** y **Neighbourhoods**. Conmuta globalmente la capa de color del mapa, la leyenda A-F, los umbrales del gráfico, el cálculo de la media y el ranking.

---

## Control de fecha (slider inferior izquierdo)

Slider de doble manilla sobre el eje temporal completo del dataset (~60 meses: 2021-01 → 2025-12, incluyendo el mes de forecast).

| Control | Acción |
|---|---|
| Manilla izquierda | Define `fromYM` (inicio de ventana) |
| Manilla derecha | Define `toYM` (fin de ventana) |
| Botón ▶ / ⏸ | Anima `toYM` avanzando un mes cada 380 ms hasta el final |
| Cualquier arrastre | Pausa la animación automáticamente |

La barra de relleno verde refleja visualmente el rango activo. Las marcas inferiores indican los años del periodo (2021, 2022, 2023, 2024, 2025 · forecast).

---

## Panel lateral — contenido dinámico

El panel (420 px, derecha) cambia su contenido según la vista activa.

### Cabecera fija

Siempre visible: logotipo AirTrace (ícono de viento), nombre de la app y contaminante activo.

---

### Panel Streets

- Descripción del origen del dato (modelo LUR, R² = 0.60).
- Tarjeta de estadísticas del dataset cargado:

| Campo | Valor |
|---|---|
| Streets | 8 450 segmentos |
| LSOAs | 302 |
| Months | n° de meses en el dataset |
| Series rows | total de filas de predicción mensuales |

---

### Panel Neighbourhoods — sin selección

- Mensaje de orientación ("click any polygon…").
- **Filtros de ranking** (ver sección siguiente).
- **Botón de descarga CSV**.

### Panel Neighbourhoods — con LSOA seleccionado

**Tarjeta de detalle:**
- Nombre del ward y nombre del LSOA.
- Badge de grado (A-F) con sombra del color semántico.
- Concentración media en la ventana activa y ratio respecto al límite WHO.

**Gráfico de serie temporal:**
- Eje X: meses (ticks en enero de cada año).
- Línea azul sólida: valores históricos (`type = "historical"`).
- Línea rosa discontinua: valores de previsión (`type = "forecast"`), conectada desde el último punto histórico.
- Banda azul semitransparente: intervalo de confianza al 90 % (CI lower – CI upper).
- Área sombreada: ventana temporal activa seleccionada.
- Líneas de referencia:
  - Verde discontinua: límite WHO (5 µg/m³ PM2.5 / 15 µg/m³ PM10).
  - Ámbar discontinua (solo PM2.5): objetivo UK 2040 (10 µg/m³).
- Tooltip: grado, concentración y CI al pasar el ratón.

**Tarjeta de forecast** (si existe):
- Grado, concentración predicha e intervalo de confianza al 90 %.

Después del detalle aparecen los filtros y el botón de descarga.

---

### Panel Sensors

- Contador del mes efectivo mostrando:
  - Sensores activos finales (verde).
  - Sensores activos excluidos (naranja).
  - Sensores offline (gris).
- Leyenda de colores.
- Lista de sensores finales activos ese mes.
- Lista de sensores excluidos activos ese mes.
- Estadística del dataset (meses con datos / meses totales).

---

## Filtros de ranking (vista Neighbourhoods)

Dos filtros opcionales que restringen qué LSOAs aparecen en el ranking y en la descarga:

| Filtro | Descripción | Rango |
|---|---|---|
| **Max green-cover %** | Excluye LSOAs con cobertura vegetal superior al valor (prioriza zonas urbanas densas) | 0–50 % |
| **Min pop density (km⁻²)** | Excluye LSOAs por debajo de la densidad indicada | 0–20 000 km⁻² |

Ambos filtros son opcionales (checkbox off = sin restricción). El **Top-10 preview** muestra en tiempo real los 10 LSOAs con mayor concentración media que pasan los filtros activos, con rango, nombre, concentración y badge de grado.

---

## Descarga CSV

Genera un fichero `airtrace_ranking_<fromYM>_<toYM>.csv` con todos los LSOAs que pasan los filtros activos, ordenados por concentración media descendente.

**Columnas exportadas:**

| Columna | Descripción |
|---|---|
| `rank` | Posición en el ranking (1 = más contaminado) |
| `LSOA21CD` | Código oficial LSOA 2021 |
| `LSOA21NM` | Nombre del LSOA |
| `mean_pm25` | Media del contaminante en la ventana (µg/m³) |
| `n_months` | Nº de meses con dato en la ventana |
| `ratio_vs_who` | Ratio respecto al límite WHO |
| `ratio_vs_uk2040` | Ratio respecto al objetivo UK |
| `score` | Grado A-F |
| `pct_green` | Cobertura vegetal (%) |
| `pop_density_km2` | Densidad de población (hab/km²) |
| `population` | Población total del LSOA |

---

## Escala de grados A-F

### PM2.5

| Grado | Rango (µg/m³) | Color | Descripción |
|---|---|---|---|
| A | < 5 | Verde | Meets WHO 2021 |
| B | 5 – 10 | Amarillo-verde | Meets UK 2040 |
| C | 10 – 15 | Amarillo | Above UK 2040 |
| D | 15 – 20 | Naranja | Concerning |
| E | 20 – 25 | Rojo | Critical |
| F | ≥ 25 | Púrpura | Urgent action |

**Umbrales regulatorios:** WHO 2021 = 5 µg/m³ · UK 2040 = 10 µg/m³

### PM10

| Grado | Rango (µg/m³) | Color | Descripción |
|---|---|---|---|
| A | < 15 | Verde | Meets WHO 2021 |
| B | 15 – 30 | Amarillo-verde | Good |
| C | 30 – 45 | Amarillo | Above WHO daily |
| D | 45 – 60 | Naranja | Concerning |
| E | 60 – 75 | Rojo | Critical |
| F | ≥ 75 | Púrpura | Urgent action |

**Umbrales regulatorios:** WHO 2021 = 15 µg/m³ · UK LAQM = 40 µg/m³

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Framework | React 19 + TypeScript |
| Bundler | Vite |
| Estilos | Tailwind CSS v4 |
| Mapa | Mapbox GL JS (`dark-v11`) |
| Gráficos | Recharts (ComposedChart) |
| Estado global | Zustand |
| Exportación CSV | PapaParse + file-saver |
| Fuente | Inter (Google Fonts) |

---

## Datos cargados al inicio

Todos los datos se cargan una sola vez al arrancar la app mediante `loadAll()`:

| Dataset | Descripción |
|---|---|
| `lsoaGeo` | GeoJSON de 302 polígonos LSOA con propiedades (nombre, ward, pct_green, pop_density_km2, population) |
| `series` | Map LSOA → array de filas mensuales con `PM2.5_pred`, `PM10_pred`, `ci_lower`, `ci_upper`, `temporal_factor`, `type` (historical/forecast) |
| `streetsGeo` | GeoJSON de 8 450 segmentos viarios con `pm25`, `pm10`, `name`, `highway` |
| `sensorsGeo` | GeoJSON de 68 puntos sensor con `device_id`, `name`, `is_final`, `status`, `date_from`, `date_to` |
| `sensorTimeline` | Mapa `year_month → device_id[]` de sensores activos por mes |
| `wardLookup` | Mapa `LSOA21CD → ward_name` |
| `months` | Array ordenado de todos los meses disponibles (eje del slider) |
