/**
 * AirTrace shared types — single source of truth for every component.
 *
 * Field names match the real files exactly:
 *   - public/data/streets.geojson  (slim copy of outputs/maps/liverpool_pollution_map.geojson)
 *   - public/data/lsoa.geojson     (copy of outputs/maps/lur_lsoa_predictions.geojson)
 *   - public/data/timeseries.csv   (copy of outputs/stlur_v2_predictions.csv)
 */

import type {
  Feature,
  FeatureCollection,
  LineString,
  MultiLineString,
  Point,
  Polygon,
  MultiPolygon,
} from "geojson";

/* -------------------------------------------------------------------------- */
/* A–F regulatory scale                                                       */
/* -------------------------------------------------------------------------- */

export type Grade = "A" | "B" | "C" | "D" | "E" | "F";

export interface GradeBin {
  grade: Grade;
  min: number;
  max: number;
  color: `#${string}`;
  label: string;
}

/* -------------------------------------------------------------------------- */
/* LSOA polygon properties                                                    */
/* -------------------------------------------------------------------------- */

export interface LsoaProperties {
  LSOA21CD: string;
  LSOA21NM: string;
  "PM2.5_final": number;
  score_pm25: Grade;
  pct_green: number;
  pop_density_km2: number;
  population: number;
}

export type LsoaFeature = Feature<Polygon | MultiPolygon, LsoaProperties>;
export type LsoaFeatureCollection = FeatureCollection<Polygon | MultiPolygon, LsoaProperties>;

/* -------------------------------------------------------------------------- */
/* Street segment properties                                                  */
/* -------------------------------------------------------------------------- */

export type SensorStatus = "active" | "candidate";

export interface SensorProperties {
  name: string;
  device_id: string;
  status: SensorStatus;
  date_from?: string;
  date_to?: string;
}

export type SensorFeature = Feature<Point, SensorProperties>;
export type SensorFeatureCollection = FeatureCollection<Point, SensorProperties>;

export type HighwayClass = "residential" | "primary" | "secondary" | "motorway";

export interface StreetProperties {
  name: string | null;
  highway: HighwayClass;
  pm25: number;
  pm10: number;
}

export type StreetFeature = Feature<LineString | MultiLineString, StreetProperties>;
export type StreetFeatureCollection = FeatureCollection<LineString | MultiLineString, StreetProperties>;

/* -------------------------------------------------------------------------- */
/* Monthly time-series row                                                    */
/* -------------------------------------------------------------------------- */

export type RowType = "historical" | "forecast";

export interface MonthlyRow {
  year_month: string;
  date: string;
  "PM2.5_pred": number;
  ci_lower: number;
  ci_upper: number;
  temporal_factor: number;
  spatial_baseline: number;
  lsoa_id: string;
  lsoa_name: string;
  type: RowType;
}

/* -------------------------------------------------------------------------- */
/* Aggregations                                                               */
/* -------------------------------------------------------------------------- */

export interface LoadedData {
  lsoaGeo: LsoaFeatureCollection;
  streetsGeo: StreetFeatureCollection;
  sensorsGeo: SensorFeatureCollection;
  series: Map<string, MonthlyRow[]>;
  months: string[];
  wardLookup: Record<string, string>;
  sensorTimeline: Record<string, string[]>;
}

export interface ChronicExposure {
  LSOA21CD: string;
  LSOA21NM: string;
  meanPM25: number;
  nMonths: number;
  grade: Grade;
}

export interface RankingRow {
  rank: number;
  LSOA21CD: string;
  LSOA21NM: string;
  mean_pm25: number;
  n_months: number;
  ratio_vs_who: number;
  ratio_vs_uk2040: number;
  score: Grade;
  pct_green: number;
  pop_density_km2: number;
  population: number;
}

/* -------------------------------------------------------------------------- */
/* Zustand store                                                              */
/* -------------------------------------------------------------------------- */

export type ViewMode = "streets" | "lsoa" | "sensors";

export interface AppState {
  viewMode: ViewMode;
  fromYM: string;
  toYM: string;
  selectedLsoa: string | null;
  showOverlay: boolean;
  greenCoverMax: number | null;
  popDensityMin: number | null;
  /** Auto-play through the date range. */
  playing: boolean;

  setViewMode: (m: ViewMode) => void;
  setPlaying: (v: boolean) => void;
  togglePlay: () => void;
  setRange: (from: string, to: string) => void;
  setSelected: (id: string | null) => void;
  toggleOverlay: () => void;
  setGreenCoverMax: (v: number | null) => void;
  setPopDensityMin: (v: number | null) => void;
}
