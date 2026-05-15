import { useMemo } from "react";
import type { LoadedData, Pollutant } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { buildRanking } from "@/lib/exposure";
import { GRADE_BINS, GRADE_BINS_PM10 } from "@/lib/scale";

interface Props { data: LoadedData; pollutant?: Pollutant; }

export function FilterPanel({ data, pollutant = "PM2.5" }: Props) {
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const popDensityMin = useAppStore((s) => s.popDensityMin);
  const setPopDensityMin = useAppStore((s) => s.setPopDensityMin);

  const bins = pollutant === "PM10" ? GRADE_BINS_PM10 : GRADE_BINS;

  const ranking = useMemo(
    () =>
      buildRanking(data.lsoaGeo.features, data.series, fromYM, toYM, {
        popDensityMin,
      }, pollutant),
    [data, fromYM, toYM, popDensityMin, pollutant],
  );

  return (
    <section className="mb-4">
      <h2 className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-2.5">Ranking filters</h2>
      <div className="space-y-3">
        <FilterRow
          label="Min pop density (km⁻²)"
          value={popDensityMin}
          min={0} max={20000} step={500} unit=""
          help="IMD proxy until real IMD data is wired in (see CONTRACTS §6.4)."
          onChange={setPopDensityMin}
        />
      </div>

      <div className="mt-3 rounded-xl border border-white/[0.07] bg-white/[0.03] p-3">
        <div className="flex justify-between items-baseline mb-1">
          <span className="text-[11px] text-slate-400">Top-10 preview</span>
          <span className="text-[11px] font-mono text-slate-500">{ranking.length} / {data.lsoaGeo.features.length}</span>
        </div>
        <table className="w-full text-[11px]">
          <tbody>
            {ranking.slice(0, 10).map((r) => {
              const color = bins.find((b) => b.grade === r.score)?.color ?? "#666";
              return (
                <tr key={r.LSOA21CD} className="border-t border-white/[0.05]">
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
  realMin, realMax,
}: {
  label: string;
  value: number | null;
  min: number; max: number; step: number; unit: string;
  help: string;
  onChange: (v: number | null) => void;
  /** If set, the visual slider range [min,max] is remapped to [realMin,realMax] before storing. */
  realMin?: number;
  realMax?: number;
}) {
  const rMin = realMin ?? min;
  const rMax = realMax ?? max;

  // Convert between visual position (0-max) and real stored value (rMin-rMax)
  const toReal    = (vis: number)  => rMin + (vis - min) / (max - min) * (rMax - rMin);
  const toDisplay = (real: number) => Math.round(min + (real - rMin) / (rMax - rMin) * (max - min));

  const enabled = value !== null;
  // Visual position for slider and fill bar
  const displayValue = enabled ? toDisplay(value) : min;
  const pct = enabled ? (displayValue / (max - min)) * 100 : 0;

  const toggle = () => onChange(enabled ? null : toReal(Math.round((min + max) / 2)));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Header row: toggle switch + label + value badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif' }}>
          {/* Custom pill switch */}
          <span
            onClick={toggle}
            style={{
              position: 'relative', display: 'inline-block',
              width: 30, height: 18, borderRadius: 999, flexShrink: 0, cursor: 'pointer',
              background: enabled ? 'rgba(16,185,129,0.45)' : 'rgba(255,255,255,0.10)',
              border: enabled ? '1px solid rgba(16,185,129,0.65)' : '1px solid rgba(255,255,255,0.10)',
              transition: 'background 150ms, border-color 150ms',
            }}
          >
            <span style={{
              position: 'absolute', top: 1, left: 1,
              width: 14, height: 14, borderRadius: '50%',
              background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
              transform: enabled ? 'translateX(12px)' : 'translateX(0)',
              transition: 'transform 150ms',
            }} />
          </span>
          <span style={{ fontSize: 13, color: enabled ? '#F1F5F9' : '#64748b', fontWeight: 500, transition: 'color 150ms' }}>
            {label}
          </span>
        </label>
        {/* Value badge — shows visual (fake) value */}
        <span style={{
          fontFamily: 'var(--font-mono, monospace)', fontSize: 12, fontWeight: 500,
          padding: '2px 8px', borderRadius: 6,
          color: enabled ? '#F1F5F9' : '#475569',
          background: enabled ? 'rgba(16,185,129,0.10)' : 'rgba(255,255,255,0.03)',
          border: enabled ? '1px solid rgba(16,185,129,0.25)' : '1px solid rgba(255,255,255,0.07)',
          transition: 'all 150ms',
        }}>
          {enabled ? `${displayValue}${unit}` : 'off'}
        </span>
      </div>

      {/* Slider track with gradient fill */}
      <div style={{ position: 'relative', opacity: enabled ? 1 : 0.35, transition: 'opacity 150ms' }}>
        {/* Track background */}
        <div style={{ height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.08)' }}>
          {/* Gradient fill */}
          <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: `${pct}%`, background: 'linear-gradient(90deg, #10B981, #34D399)', borderRadius: 999, transition: 'width 120ms ease-out' }} />
        </div>
        {/* Thumb */}
        {enabled && (
          <div style={{ position: 'absolute', top: '50%', left: `${pct}%`, transform: 'translate(-50%, -50%)', width: 16, height: 16, borderRadius: '50%', background: '#F8FAFC', border: '2px solid #10B981', boxShadow: '0 1px 4px rgba(0,0,0,0.4)', pointerEvents: 'none', transition: 'left 120ms ease-out' }} />
        )}
        {/* Functional invisible input — operates in visual range, converts to real on change */}
        <input
          type="range" min={min} max={max} step={step}
          value={displayValue}
          disabled={!enabled}
          onChange={(e) => onChange(toReal(Number(e.target.value)))}
          style={{ position: 'absolute', inset: 0, width: '100%', opacity: 0, cursor: enabled ? 'pointer' : 'not-allowed', height: 6 }}
          aria-label={label}
        />
      </div>

      <p style={{ fontSize: 12, color: enabled ? '#64748b' : '#334155', lineHeight: 1.5, margin: 0, fontFamily: 'Inter, system-ui, sans-serif' }}>{help}</p>
    </div>
  );
}
