import Papa from "papaparse";
import type {
  LoadedData,
  LsoaFeatureCollection,
  MonthlyRow,
  SensorFeatureCollection,
  StreetFeatureCollection,
} from "@/types/lsoa";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseStorageBase = `${SUPABASE_URL}/storage/v1/object/public/geojson/`;

/**
 * Loads all static assets from Supabase Storage (bucket: geojson) and
 * indexes them so the rest of the app never has to touch raw I/O again.
 *
 * Called once on app mount.
 */
export async function loadAll(): Promise<LoadedData> {
  const [lsoaGeo, streetsGeo, sensorsGeo, parsed, wardLookup, sensorTimeline] = await Promise.all([
    fetchLsoaGeojson(),
    fetchStreetsGeojson(),
    fetchSensorsGeojson(),
    fetchTimeseries(),
    fetchWardLookup(),
    fetchSensorTimeline(),
  ]);
  const series = groupByLsoa(parsed);
  const months = uniqueSorted(parsed.map((r) => r.year_month));
  return { lsoaGeo, streetsGeo, sensorsGeo, series, months, wardLookup, sensorTimeline };
}

async function fetchLsoaGeojson(): Promise<LsoaFeatureCollection> {
  const res = await fetch(`${supabaseStorageBase}lsoa.geojson`);
  if (!res.ok) throw new Error(`lsoa.geojson HTTP ${res.status}`);
  return (await res.json()) as LsoaFeatureCollection;
}

async function fetchStreetsGeojson(): Promise<StreetFeatureCollection> {
  const res = await fetch(`${supabaseStorageBase}streets.geojson`);
  if (!res.ok) throw new Error(`streets.geojson HTTP ${res.status}`);
  return (await res.json()) as StreetFeatureCollection;
}

async function fetchSensorsGeojson(): Promise<SensorFeatureCollection> {
  const res = await fetch(`${supabaseStorageBase}sensors.geojson`);
  if (!res.ok) throw new Error(`sensors.geojson HTTP ${res.status}`);
  const fc = (await res.json()) as SensorFeatureCollection;
  // Drop malformed records (missing device_id or placeholder name).
  fc.features = fc.features.filter(
    (f) => f.properties.device_id?.trim() && f.properties.name?.trim() && f.properties.name !== "Unknown",
  );
  // Some features were exported with [lat, lng] instead of [lng, lat].
  // Liverpool longitude ≈ -3, so any feature whose first coordinate is > 0 is swapped.
  for (const feat of fc.features) {
    const [a, b] = feat.geometry.coordinates as [number, number];
    if (a > 0) feat.geometry.coordinates = [b, a];
  }
  return fc;
}

async function fetchSensorTimeline(): Promise<Record<string, string[]>> {
  const res = await fetch(`${supabaseStorageBase}sensor_timeline.json`);
  if (!res.ok) return {};
  return (await res.json()) as Record<string, string[]>;
}

async function fetchWardLookup(): Promise<Record<string, string>> {
  const res = await fetch(`${supabaseStorageBase}lsoa_ward_lookup.json`);
  if (!res.ok) return {};
  return (await res.json()) as Record<string, string>;
}

function fetchTimeseries(): Promise<MonthlyRow[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<MonthlyRow>(`${supabaseStorageBase}timeseries.csv`, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (result) => {
        const rows = result.data.filter((r) => r && r.lsoa_id && r.year_month);
        resolve(rows);
      },
      error: (err) => reject(err),
    });
  });
}

function groupByLsoa(rows: MonthlyRow[]): Map<string, MonthlyRow[]> {
  const out = new Map<string, MonthlyRow[]>();
  for (const r of rows) {
    const list = out.get(r.lsoa_id);
    if (list) list.push(r);
    else out.set(r.lsoa_id, [r]);
  }
  for (const list of out.values()) {
    list.sort((a, b) => a.year_month.localeCompare(b.year_month));
  }
  return out;
}

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values)).sort();
}

/**
 * Mean of PM2.5_pred over an inclusive [fromYM, toYM] window.
 * Returns NaN if no rows fall inside.
 */
export function windowedMean(
  rows: MonthlyRow[],
  fromYM: string,
  toYM: string,
): { mean: number; nMonths: number } {
  let sum = 0;
  let n = 0;
  for (const r of rows) {
    if (r.year_month >= fromYM && r.year_month <= toYM) {
      sum += r["PM2.5_pred"];
      n += 1;
    }
  }
  return { mean: n > 0 ? sum / n : NaN, nMonths: n };
}
