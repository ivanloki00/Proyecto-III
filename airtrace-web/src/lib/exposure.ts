import type { LsoaProperties, MonthlyRow, RankingRow } from "@/types/lsoa";
import { gradeOf, WHO_PM25, UK_2040 } from "@/lib/scale";

/** Mean PM2.5_pred over an inclusive [fromYM, toYM] window for one LSOA. */
function meanInWindow(rows: MonthlyRow[], fromYM: string, toYM: string): { mean: number; n: number } {
  let sum = 0, n = 0;
  for (const r of rows) {
    if (r.year_month >= fromYM && r.year_month <= toYM) {
      sum += r["PM2.5_pred"];
      n += 1;
    }
  }
  return { mean: n > 0 ? sum / n : NaN, n };
}

/** Map<LSOA21CD, meanPM25> over [fromYM, toYM]. */
export function windowedMeans(
  series: Map<string, MonthlyRow[]>,
  fromYM: string,
  toYM: string,
): Map<string, number> {
  const out = new Map<string, number>();
  for (const [id, rows] of series) {
    const { mean } = meanInWindow(rows, fromYM, toYM);
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
 * Sorted by mean PM2.5 descending; rank assigned 1..N after filtering.
 */
export function buildRanking(
  features: Array<{ properties: LsoaProperties }>,
  series: Map<string, MonthlyRow[]>,
  fromYM: string,
  toYM: string,
  filters: { greenCoverMax: number | null; popDensityMin: number | null },
): RankingRow[] {
  const rows: Array<Omit<RankingRow, "rank">> = [];
  for (const f of features) {
    const p = f.properties;
    const rowsForLsoa = series.get(p.LSOA21CD);
    if (!rowsForLsoa) continue;
    const { mean, n } = meanInWindow(rowsForLsoa, fromYM, toYM);
    if (!Number.isFinite(mean)) continue;
    if (filters.greenCoverMax !== null && p.pct_green > filters.greenCoverMax) continue;
    if (filters.popDensityMin !== null && p.pop_density_km2 < filters.popDensityMin) continue;
    rows.push({
      LSOA21CD: p.LSOA21CD,
      LSOA21NM: p.LSOA21NM,
      mean_pm25: round2(mean),
      n_months: n,
      ratio_vs_who: round2(mean / WHO_PM25),
      ratio_vs_uk2040: round2(mean / UK_2040),
      score: gradeOf(mean),
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
