import { useMemo } from "react";
import type { LoadedData, Pollutant } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { buildRanking } from "@/lib/exposure";
import { GRADE_BINS, GRADE_BINS_PM10 } from "@/lib/scale";

interface Props { data: LoadedData; pollutant?: Pollutant; }

export function FilterPanel({ data, pollutant = "PM2.5" }: Props) {
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const greenCoverMax = useAppStore((s) => s.greenCoverMax);
  const popDensityMin = useAppStore((s) => s.popDensityMin);
  const setGreenCoverMax = useAppStore((s) => s.setGreenCoverMax);
  const setPopDensityMin = useAppStore((s) => s.setPopDensityMin);

  const bins = pollutant === "PM10" ? GRADE_BINS_PM10 : GRADE_BINS;

  const ranking = useMemo(
    () =>
      buildRanking(data.lsoaGeo.features, data.series, fromYM, toYM, {
        greenCoverMax, popDensityMin,
      }, pollutant),
    [data, fromYM, toYM, greenCoverMax, popDensityMin, pollutant],
  );

  return (
    <section className="mb-4">
      <h2 className="text-slate-300 font-medium mb-2">Ranking filters</h2>
      <div className="space-y-3">
        <FilterRow
          label="Max green-cover %"
          value={greenCoverMax}
          min={0} max={50} step={1} unit="%"
          help="Show only LSOAs with green-cover ≤ value (urban prioritisation)."
          onChange={setGreenCoverMax}
        />
        <FilterRow
          label="Min pop density (km⁻²)"
          value={popDensityMin}
          min={0} max={20000} step={500} unit=""
          help="IMD proxy until real IMD data is wired in (see CONTRACTS §6.4)."
          onChange={setPopDensityMin}
        />
      </div>

      <div className="mt-3 rounded-md border border-slate-700 bg-slate-800/40 p-2">
        <div className="flex justify-between items-baseline mb-1">
          <span className="text-[11px] text-slate-400">Top-10 preview</span>
          <span className="text-[11px] font-mono text-slate-500">{ranking.length} / {data.lsoaGeo.features.length}</span>
        </div>
        <table className="w-full text-[11px]">
          <tbody>
            {ranking.slice(0, 10).map((r) => {
              const color = bins.find((b) => b.grade === r.score)?.color ?? "#666";
              return (
                <tr key={r.LSOA21CD} className="border-t border-slate-800">
                  <td className="py-0.5 pr-2 text-slate-500 font-mono">{r.rank}</td>
                  <td className="py-0.5 pr-2 text-slate-200 truncate max-w-[140px]">{r.LSOA21NM}</td>
                  <td className="py-0.5 pr-2 text-white font-mono text-right">{r.mean_pm25.toFixed(2)}</td>
                  <td className="py-0.5 text-right">
                    <span className="inline-block w-4 h-4 rounded text-white font-bold text-[10px] leading-4" style={{ backgroundColor: color }}>{r.score}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FilterRow({
  label, value, min, max, step, unit, help, onChange,
}: {
  label: string;
  value: number | null;
  min: number; max: number; step: number; unit: string;
  help: string;
  onChange: (v: number | null) => void;
}) {
  const enabled = value !== null;
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <label className="flex items-center gap-2">
          <input
            type="checkbox" checked={enabled}
            onChange={(e) => onChange(e.target.checked ? Math.round((min + max) / 2 / step) * step : null)}
            className="accent-emerald-500"
          />
          <span className="text-slate-300">{label}</span>
        </label>
        <span className={`font-mono ${enabled ? "text-white" : "text-slate-600"}`}>
          {enabled ? `${value}${unit}` : "off"}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step}
        value={value ?? min}
        disabled={!enabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full mt-1 accent-emerald-500 disabled:opacity-30"
      />
      <p className="text-[10px] text-slate-500 mt-0.5">{help}</p>
    </div>
  );
}
