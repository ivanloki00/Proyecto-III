import type { LsoaProperties, MonthlyRow, Pollutant, RankingRow } from "@/types/lsoa";
import { gradeOf, gradeOfPM10, WHO_PM25, UK_2040, WHO_PM10, UK_PM10 } from "@/lib/scale";

type PredField = "PM2.5_pred" | "PM10_pred";

function fieldFor(pollutant: Pollutant): PredField {
  return pollutant === "PM10" ? "PM10_pred" : "PM2.5_pred";
}

/** Mean of the given field over an inclusive [fromYM, toYM] window for one LSOA. */
function meanInWindow(
  rows: MonthlyRow[],
  fromYM: string,
  toYM: string,
  field: PredField = "PM2.5_pred",
): { mean: number; n: number } {
  let sum = 0, n = 0;
  for (const r of rows) {
    if (r.year_month >= fromYM && r.year_month <= toYM) {
      const v = r[field];
      if (v !== undefined && v !== null) { sum += v; n += 1; }
    }
  }
  return { mean: n > 0 ? sum / n : NaN, n };
}

/** Map<LSOA21CD, mean> over [fromYM, toYM] for the given pollutant. */
export function windowedMeans(
  series: Map<string, MonthlyRow[]>,
  fromYM: string,
  toYM: string,
  pollutant: Pollutant = "PM2.5",
): Map<string, number> {
  const field = fieldFor(pollutant);
  const out = new Map<string, number>();
  for (const [id, rows] of series) {
    const { mean } = meanInWindow(rows, fromYM, toYM, field);
    out.set(id, mean);
  }
  return out;
}

/** Count LSOAs whose windowed mean exceeds a threshold. */
export function countAbove(means: Map<string, number>, threshold: number): number {
  let n = 0;
  for (const v of means.values()) if (Number.isFinite(v) && v > threshold) n += 1;
  return n;
}

/**
 * Build the ranking rows for the current window + filters.
 * Sorted by mean pollutant value descending; rank assigned 1..N after filtering.
 */
export function buildRanking(
  features: Array<{ properties: LsoaProperties }>,
  series: Map<string, MonthlyRow[]>,
  fromYM: string,
  toYM: string,
  filters: { greenCoverMax: number | null; popDensityMin: number | null },
  pollutant: Pollutant = "PM2.5",
): RankingRow[] {
  const field = fieldFor(pollutant);
  const whoLimit = pollutant === "PM10" ? WHO_PM10 : WHO_PM25;
  const ukLimit  = pollutant === "PM10" ? UK_PM10  : UK_2040;
  const gradeFunc = pollutant === "PM10" ? gradeOfPM10 : gradeOf;

  const rows: Array<Omit<RankingRow, "rank">> = [];
  for (const f of features) {
    const p = f.properties;
    const rowsForLsoa = series.get(p.LSOA21CD);
    if (!rowsForLsoa) continue;
    const { mean, n } = meanInWindow(rowsForLsoa, fromYM, toYM, field);
    if (!Number.isFinite(mean)) continue;
    if (filters.greenCoverMax !== null && p.pct_green > filters.greenCoverMax) continue;
    if (filters.popDensityMin !== null && p.pop_density_km2 < filters.popDensityMin) continue;
    rows.push({
      LSOA21CD: p.LSOA21CD,
      LSOA21NM: p.LSOA21NM,
      mean_pm25: round2(mean),
      n_months: n,
      ratio_vs_who: round2(mean / whoLimit),
      ratio_vs_uk2040: round2(mean / ukLimit),
      score: gradeFunc(mean),
      pct_green: round2(p.pct_green),
      pop_density_km2: round2(p.pop_density_km2),
      population: p.population,
    });
  }
  rows.sort((a, b) => b.mean_pm25 - a.mean_pm25);
  return rows.map((r, i) => ({ rank: i + 1, ...r }));
}

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}

/**
 * Average `temporal_factor` over [fromYM, toYM]. Returns 1.0 if no rows.
 *
 * The factor is identical for all LSOAs within a given month (seasonal driver,
 * not spatial), so we just average over any one LSOA's series — pick the
 * first available iterator entry.
 */
export function windowedTemporalFactor(
  series: Map<string, MonthlyRow[]>,
  fromYM: string,
  toYM: string,
): number {
  const first = series.values().next();
  if (first.done) return 1;
  let sum = 0, n = 0;
  for (const r of first.value) {
    if (r.year_month >= fromYM && r.year_month <= toYM) {
      sum += r.temporal_factor;
      n += 1;
    }
  }
  return n > 0 ? sum / n : 1;
}
