# AirTrace Web — Data & Component Contracts

> **Purpose.** Single source of truth for every sub-agent that builds part of `airtrace-web/`. Read this file *first*, then implement only the surface assigned to you. Do not re-derive shapes, scales, or thresholds — they are fixed here.

> **Scope.** MVP for a public fair demo. Runs entirely **local**. No auth, no backend API, no security hardening. Data is shipped as static assets in `public/data/`.

---

## 1. Stack (already installed in `node_modules/`)

| Concern | Library | Version | Notes |
|---|---|---|---|
| Bundler / dev server | `vite` | 8.0.9 | `npm run dev` on port 5173 |
| UI | `react` / `react-dom` | 19.2.5 | function components + hooks |
| Map | `mapbox-gl` | 3.22.0 | used directly (no `react-map-gl`) |
| Charts | `recharts` | 2.15.4 | line + area for CI band |
| State | `zustand` | 5.0.12 | one store, no providers |
| Styles | `tailwindcss` | 4.2.2 | Tailwind v4, CSS-first config |
| Types | `typescript` | 6.0.3 | strict mode |

**Deps still to install** (Phase 1 closing step):
```
npm i papaparse file-saver
npm i -D @types/papaparse @types/file-saver
```

`react-map-gl` is **not** used; we instantiate `mapboxgl.Map` ourselves in a `useEffect`.

---

## 2. Real data sources (do **not** invent fields)

All paths are relative to repository root.

### 2.0 Streets — `outputs/maps/liverpool_pollution_map.geojson` (slimmed → `public/data/streets.geojson`)

- 8 450 LineString features, one per OSM way segment
- Source file is 24 MB; we ship a 3.2 MB **slim** version with only the props the UI needs
- Range: PM2.5 4.87 – 28.10 µg/m³ — covers the **full A–F scale** (the LSOA aggregate flattens to B/C only)
- Distribution at A–F bins: A 0.0 % · B 56.1 % · C 40.1 % · D 3.4 % · E 0.4 % · F 0.0 %

**Slim properties (used as-is):**

| Field | Type | Notes |
|---|---|---|
| `name` | string \| null | OSM `name` (e.g. `"Mather Avenue"`) — for the click tooltip |
| `highway` | `"residential" \| "primary" \| "secondary" \| "motorway"` | display + future filter |
| `pm25` | number µg/m³ \| null | rounded 2 d.p. — drives colour |
| `pm10` | number µg/m³ \| null | informational |

The slim file is generated once by the script in `scripts/build_streets_geojson.py` (next paragraph). All segments without a `pm25` value are dropped.

### 2.1 LSOA polygons — `outputs/maps/lur_lsoa_predictions.geojson`

- 302 features (`FeatureCollection`)
- CRS: WGS84 (EPSG:4326)
- One feature per LSOA polygon
- Carries the **static** annual baseline + all geographic covariates

**Properties used by the webapp:**

| Field | Type | Used for |
|---|---|---|
| `LSOA21CD` | string (e.g. `"E01006512"`) | join key, CSV export |
| `LSOA21NM` | string (e.g. `"Liverpool 031A"`) | display name |
| `PM2.5_final` | number µg/m³ | static fallback only — **the live colour comes from the CSV mean over the slider window**, not from this field |
| `score_pm25` | `"A"…"F"` | not used by us at runtime — we recompute the score from the windowed mean |
| `pct_green` | number 0–100 | "low green-cover" filter |
| `pop_density_km2` | number | proxy for the IMD filter (see §6.4) |
| `population` | number | tooltip / export |

Any other property (street density, building counts, …) is ignored by the MVP.

### 2.2 Monthly time-series — `outputs/stlur_v2_predictions.csv`

- 18 121 rows = 302 LSOAs × ~60 months
- Date range: **2021-01 to 2025-12** inclusive (5 years monthly)

**Columns:**

| Column | Type | Notes |
|---|---|---|
| `year_month` | string `"YYYY-MM"` | unique per (lsoa, month) |
| `date` | ISO date `"YYYY-MM-01"` | start of month |
| `PM2.5_pred` | number µg/m³ | central prediction |
| `ci_lower` | number µg/m³ | 90 % CI lower bound |
| `ci_upper` | number µg/m³ | 90 % CI upper bound |
| `temporal_factor` | number | seasonal multiplier (informational) |
| `spatial_baseline` | number µg/m³ | annual mean for this LSOA |
| `lsoa_id` | string = `LSOA21CD` | join key |
| `lsoa_name` | string = `LSOA21NM` | redundant — display |
| `type` | `"historical"` \| `"forecast"` | the **last** month per LSOA is `forecast`; everything before is `historical` |

The "central forecast value for the next month with its CI bounds" required by use-case 2 is the single row where `type === "forecast"` for the clicked LSOA.

---

## 3. Public asset layout (Phase 1 closing step)

Copy the two source files into the Vite public folder so the browser can fetch them by URL:

```
airtrace-web/public/data/
├── streets.geojson     ← slimmed copy of outputs/maps/liverpool_pollution_map.geojson
├── lsoa.geojson        ← copy of outputs/maps/lur_lsoa_predictions.geojson
└── timeseries.csv      ← copy of outputs/stlur_v2_predictions.csv
```

Fetched as `/data/streets.geojson`, `/data/lsoa.geojson` and `/data/timeseries.csv` from the browser. No CORS, no API.

---

## 4. The fixed A–F regulatory scale

**Non-negotiable.** Defined in `PRD_webapp_v1.1.md` and frozen here. All sub-agents import from `@/lib/scale.ts`.

| Score | PM2.5 µg/m³ | Hex | Regulatory meaning |
|---|---|---|---|
| A | < 5     | `#00c864` | Meets WHO 2021 guideline |
| B | 5 – 10  | `#c8e632` | Meets UK 2040 target |
| C | 10 – 15 | `#ffc800` | Above UK 2040 target |
| D | 15 – 20 | `#ff8200` | Concerning |
| E | 20 – 25 | `#e63232` | Critical |
| F | ≥ 25    | `#960096` | Urgent action |

**Reference thresholds** (used for the binary overlay and the "×N over WHO" multiplier):

```ts
export const WHO_PM25 = 5;      // µg/m³  WHO 2021 guideline
export const UK_2040  = 10;     // µg/m³  UK 2040 target
```

Score function (one place only):

```ts
function gradeOf(pm25: number): "A"|"B"|"C"|"D"|"E"|"F" {
  if (pm25 < 5)  return "A";
  if (pm25 < 10) return "B";
  if (pm25 < 15) return "C";
  if (pm25 < 20) return "D";
  if (pm25 < 25) return "E";
  return "F";
}
```

---

## 5. Component contracts (3 use-cases × responsible agent)

### 5.0 View toggle — Streets ↔ Barrios (LSOAs)

The map has two mutually-exclusive layers and a top-bar toggle:

```
[ Calles (8 450) ]   [ Barrios — LSOA (302) ]
```

- Default: **Calles**.
- `viewMode` lives in the Zustand store (§6.1).
- When `viewMode === "streets"`: the LSOA fill/outline layers are hidden; the streets line layer is visible. The date-range slider, side-panel time-series, and ranking export are **disabled** (the streets dataset is annual only). A muted hint reads *"Switch to LSOA view to use the date slider, time-series and ranking."*
- When `viewMode === "lsoa"`: the streets layer is hidden; the LSOA fill + outline layers are visible. All 3 use-cases (5.1, 5.2, 5.3) are active.

**Streets layer paint (constant — does not depend on slider):**
- `type: "line"`, source = `streets`
- `line-color`: same A–F step expression as the LSOA layer, on `["get","pm25"]`
- `line-width`: `["interpolate", ["linear"], ["zoom"], 10, 0.6, 13, 1.6, 16, 3]` so the city-wide view stays readable but zooming in shows real road thickness
- `line-opacity`: 0.85

**Streets click tooltip (Mapbox Popup):**
- Title: `properties.name ?? "Unnamed road"` + `· {highway}`
- Big number: `pm25` µg/m³ + grade badge from §4
- Multiplier line: *"× N over WHO 5 µg/m³"*
- Closes on map background click.

### 5.1 Use-case 1 — Chronic-exposure map (`map-builder` agent)

**Owns:** `src/components/Map/ChronicMap.tsx`, `src/components/Controls/DateRangeSlider.tsx`, `src/lib/scale.ts`.

**Inputs:**
- `lsoa.geojson` — geometry only (properties.LSOA21CD as join key)
- `timeseries.csv` — parsed once at startup into `Map<LSOA21CD, MonthlyRow[]>`
- `[fromYM, toYM]` — slider state from the Zustand store, both `"YYYY-MM"`

**Behaviour:**
1. For each LSOA, compute `meanPM = average(PM2.5_pred for rows where fromYM ≤ year_month ≤ toYM)`.
2. Apply `gradeOf(meanPM)` → fill colour from §4.
3. **Binary overlay (toggleable):** outline LSOAs where `meanPM > UK_2040` in white, 1.5 px. Counter in legend reads e.g. *"148 / 302 above UK 2040 (49 %)"*.
4. **Click on polygon:** push `LSOA21CD` to `store.selectedLsoa`. Side panel listens.
5. Slider must be debounced 150 ms to avoid recomputing 302 means on every drag pixel.

**Acceptance:**
- Drag slider end-to-end: no UI freeze > 200 ms on a Liverpool-sized dataset.
- With window `2021-01 .. 2025-12`, the percentage above 10 µg/m³ is in the **45–48 %** band (computed: 46.4 % = 140 / 302). The PRD's 49 % refers to the annual 2024 slice; over the full 5-year window the share is slightly lower because cleaner years (2021–2022) drag the mean down.

### 5.2 Use-case 2 — LSOA time-series + CI band + forecast (`panel-builder` agent)

**Owns:** `src/components/SidePanel/SidePanel.tsx`, `src/components/SidePanel/TimeSeriesChart.tsx`.

**Inputs:**
- `store.selectedLsoa` — `LSOA21CD` or `null`
- The same parsed time-series map.

**Behaviour:**
1. When `selectedLsoa` is null, panel shows a "Click an LSOA" placeholder.
2. When set, render with Recharts:
   - X axis: `year_month` (60 ticks, sparse-labelled by year).
   - Solid line: `PM2.5_pred`.
   - Shaded area between `ci_lower` and `ci_upper`, 90 % CI, opacity 0.2, same hue as line.
   - Two horizontal reference lines: `y = 5` (WHO, dashed green) and `y = 10` (UK 2040, dashed orange).
3. **Forecast call-out box** below the chart: locate the row with `type === "forecast"` for this LSOA. Display:
   - Month label (e.g. *"Forecast for 2025-12"*).
   - Central value with 1 decimal.
   - 90 % CI as `[ci_lower – ci_upper]`.
   - Grade badge using `gradeOf(PM2.5_pred)`.
4. Header of the panel: LSOA name + code, mean over the *current slider window* (read from store), grade badge, multiplier vs WHO (`mean / 5` to 1 decimal).
5. Close button (`×`) clears `selectedLsoa`.

**Acceptance:**
- Clicking 5 different LSOAs in sequence shows the right LSOA name in the header each time.
- The forecast box never shows a `historical` row.
- CI band visibly widens for the forecast point (it does in the data — verify visually).

### 5.3 Use-case 3 — Intervention ranking export (`export-builder` agent, **Haiku**)

**Owns:** `src/components/Export/DownloadRanking.tsx`, `src/components/Controls/FilterPanel.tsx`.

**Inputs:**
- The same store `[fromYM, toYM]`.
- Filter values: `greenCoverMax: number | null`, `popDensityMin: number | null` (the IMD proxy — see §6.4).
- The 302 LSOA records joined with the windowed mean from §5.1.

**Behaviour:**
1. Filter panel UI:
   - Slider "Max green-cover %" (0–100, default off).
   - Slider "Min population density (km⁻²)" labelled *"Deprivation proxy — see About"* (default off). See §6.4.
2. Build the ranking: filter → sort by `meanPM25` descending → assign `rank` 1..N.
3. **Download button** uses PapaParse + FileSaver to emit `airtrace_ranking_{from}_{to}.csv` with header:

   ```
   rank,LSOA21CD,LSOA21NM,mean_pm25,n_months,ratio_vs_who,ratio_vs_uk2040,score,pct_green,pop_density_km2,population
   ```

   - `mean_pm25` rounded to 2 decimals.
   - `ratio_vs_who = mean_pm25 / 5`, `ratio_vs_uk2040 = mean_pm25 / 10`, both 2 decimals.
   - `score` from §4.
4. Live preview: small table inside `<FilterPanel>` showing the top 10 with `rank | LSOA | mean_pm25 | score`.

**Acceptance:**
- With no filters and window `2021-01 .. 2025-12`, exported CSV has **302 rows** + header.
- With `greenCoverMax = 5` (very urban, low green), exported CSV is a strict subset.
- File downloads on Chrome / Firefox / Safari (no server side).

---

## 6. Cross-cutting decisions

### 6.1 State (single Zustand store, no contexts)

```ts
// src/store/useAppStore.ts
interface AppState {
  fromYM: string;          // "YYYY-MM", default "2021-01"
  toYM: string;            // "YYYY-MM", default "2025-12"
  selectedLsoa: string | null;
  showOverlay: boolean;    // binary "above UK 2040" overlay
  greenCoverMax: number | null;
  popDensityMin: number | null;
  setRange: (from: string, to: string) => void;
  setSelected: (id: string | null) => void;
  // ...
}
```

### 6.2 Data loader (one place, called once)

```ts
// src/lib/data.ts
export async function loadAll(): Promise<{
  lsoaGeo: GeoJSON.FeatureCollection<Polygon, LsoaProperties>;
  series:  Map<string, MonthlyRow[]>;     // key = LSOA21CD
  months:  string[];                      // sorted unique year_month
}>;
```

Implementation: `fetch('/data/lsoa.geojson')` + `Papa.parse('/data/timeseries.csv', { download: true, header: true, dynamicTyping: true })`. Build the `Map` once; group rows by `lsoa_id`.

### 6.3 Path alias

`vite.config.ts` and `tsconfig.json` both define `@/* → src/*`. All sub-agents import via `@/...`.

### 6.4 IMD filter — known gap

The repo currently has **no IMD (Index of Multiple Deprivation) file** wired in. PRD references it as "next scientific step". For the MVP fair demo we substitute it with `pop_density_km2` as a *proxy* and label the control accordingly. Future work: drop a 302-row CSV `LSOA21CD,IMD_decile` into `public/data/imd.csv`; `loadAll` joins it onto the LSOA records; the slider switches from "pop density" to true IMD decile. **Sub-agents should not block on this.**

### 6.5 What we do **not** build in the MVP

- Authentication, telemetry, persistence beyond `localStorage` for slider state.
- Mobile-first layout — desktop ≥ 1024 px target only.
- The "Eventos canónicos" feature (PRD §4) — out of scope.
- Street-level monthly seasonality — the streets dataset is annual only; the slider is hidden in streets view.

### 6.6 Sub-agent dispatch rules (Phase 2)

- Each agent gets: this file's path, its assigned section number, the 1–2 file paths it owns. **No other repo context.**
- Agents output files only — no prose summaries.
- The `wirer` agent (Phase 3) reads only `App.tsx`, the store, and the three component public exports.
- The `qa-bot` (Phase 4) runs `vite build` + a single Playwright smoke that loads the page, waits for `#map canvas`, clicks one LSOA, and downloads a ranking CSV.

---

*End of contract. If something is missing here, stop and ask the user — do not improvise.*
