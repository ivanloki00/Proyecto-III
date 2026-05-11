import type { LoadedData } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { TimeSeriesChart } from "@/components/SidePanel/TimeSeriesChart";
import { FilterPanel } from "@/components/Controls/FilterPanel";
import { DownloadRanking } from "@/components/Export/DownloadRanking";
import { WHO_PM25, WHO_PM10, binsForPollutant, gradeForPollutant } from "@/lib/scale";
import type { Pollutant } from "@/types/lsoa";
import { useMemo } from "react";
import type { ReactNode } from "react";

interface Props { data: LoadedData; }

export function SidePanel({ data }: Props) {
  const viewMode = useAppStore((s) => s.viewMode);
  const pollutant = useAppStore((s) => s.pollutant);
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const selectedLsoa = useAppStore((s) => s.selectedLsoa);
  const setSelected = useAppStore((s) => s.setSelected);

  const totalRows = useMemo(
    () => Array.from(data.series.values()).reduce((acc, list) => acc + list.length, 0),
    [data.series],
  );

  return (
    <aside className="w-[420px] h-full overflow-y-auto bg-slate-950 border-l border-white/[0.06] p-5 text-sm sidebar-scroll">
      <header className="mb-5 pb-4 border-b border-white/[0.07]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-500/25">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>
            </svg>
          </div>
          <div>
            <h1 className="text-[15px] font-semibold text-white tracking-tight leading-tight">AirTrace</h1>
            <p className="text-slate-500 text-[11px] mt-0.5">Liverpool · {pollutant} air quality</p>
          </div>
        </div>
      </header>

      {viewMode === "streets" ? (
        <StreetsPanel data={data} totalRows={totalRows} />
      ) : viewMode === "sensors" ? (
        <SensorsPanel data={data} toYM={toYM} />
      ) : (
        <LsoaPanel
          data={data}
          fromYM={fromYM}
          toYM={toYM}
          selectedLsoa={selectedLsoa}
          pollutant={pollutant}
          onCloseDetail={() => setSelected(null)}
        />
      )}
    </aside>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h2 className="flex items-center gap-2 text-[11px] font-semibold text-slate-400 uppercase tracking-widest mb-2.5">
      {children}
    </h2>
  );
}

function StreetsPanel({ data, totalRows }: { data: LoadedData; totalRows: number }) {
  const nLsoas = data.lsoaGeo.features.length;
  const nStreets = data.streetsGeo.features.length;
  const nMonths = data.months.length;
  return (
    <>
      <section className="mb-5">
        <SectionLabel>Streets View</SectionLabel>
        <p className="text-slate-400 text-xs leading-relaxed">
          Click any segment to see its grade. Annual values from the LUR model
          (R² = 0.60 on PM2.5 under LOOCV).
        </p>
        <p className="text-slate-600 text-xs mt-2">
          Switch to <span className="text-slate-400">Neighbourhoods</span> to use the date slider,
          time-series chart and ranking export.
        </p>
      </section>
      <section className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-3.5">
        <SectionLabel>Data loaded</SectionLabel>
        <dl className="grid grid-cols-2 gap-y-2 text-xs text-slate-500">
          <dt>Streets</dt><dd className="text-slate-100 font-medium tabular-nums">{nStreets.toLocaleString()}</dd>
          <dt>LSOAs</dt><dd className="text-slate-100 font-medium tabular-nums">{nLsoas}</dd>
          <dt>Months</dt><dd className="text-slate-100 font-medium tabular-nums">{nMonths}</dd>
          <dt>Series rows</dt><dd className="text-slate-100 font-medium tabular-nums">{totalRows.toLocaleString()}</dd>
        </dl>
      </section>
    </>
  );
}

function LsoaPanel({
  data, fromYM, toYM, selectedLsoa, pollutant, onCloseDetail,
}: {
  data: LoadedData;
  fromYM: string;
  toYM: string;
  selectedLsoa: string | null;
  pollutant: Pollutant;
  onCloseDetail: () => void;
}) {
  const predField = pollutant === "PM10" ? "PM10_pred" : "PM2.5_pred";
  const whoLimit  = pollutant === "PM10" ? WHO_PM10 : WHO_PM25;

  const wardName = selectedLsoa ? (data.wardLookup[selectedLsoa] ?? null) : null;
  const detail = useMemo(() => {
    if (!selectedLsoa) return null;
    const rows = data.series.get(selectedLsoa);
    if (!rows) return null;
    const feature = data.lsoaGeo.features.find((f) => f.properties.LSOA21CD === selectedLsoa);
    if (!feature) return null;

    let sum = 0, n = 0;
    for (const r of rows) {
      if (r.year_month >= fromYM && r.year_month <= toYM) {
        const v = r[predField];
        if (v !== undefined) { sum += v; n += 1; }
      }
    }
    const windowMean = n > 0 ? sum / n : NaN;
    const forecast = rows.find((r) => r.type === "forecast") ?? null;
    return { rows, properties: feature.properties, windowMean, nMonths: n, forecast };
  }, [selectedLsoa, data, fromYM, toYM, predField]);

  if (!detail) {
    return (
      <>
        <section className="mb-5 rounded-xl border border-white/[0.07] bg-white/[0.03] p-3.5 text-xs">
          <p className="font-semibold text-slate-200 mb-1.5">No area selected</p>
          <p className="text-slate-500 leading-relaxed">Click any polygon on the map to see its monthly trajectory, 90 % CI band and forecast.</p>
        </section>
        <FilterPanel data={data} pollutant={pollutant} />
        <DownloadRanking data={data} />
      </>
    );
  }

  const bins  = binsForPollutant(pollutant);
  const grade = gradeForPollutant(detail.windowMean, pollutant);
  const color = bins.find((b) => b.grade === grade)!.color;
  const ratio = (detail.windowMean / whoLimit).toFixed(1);

  const fcValue = detail.forecast ? (detail.forecast[predField] ?? detail.forecast["PM2.5_pred"]) : null;
  const fcGrade = fcValue !== null ? gradeForPollutant(fcValue, pollutant) : null;
  const fcColor = fcGrade ? bins.find((b) => b.grade === fcGrade)!.color : null;

  return (
    <>
      <section className="mb-5 rounded-xl border border-white/[0.08] bg-white/[0.04] p-4 relative">
        <button
          onClick={onCloseDetail}
          className="absolute top-3 right-3 w-6 h-6 rounded-lg flex items-center justify-center text-slate-500 hover:text-white hover:bg-white/10 text-sm leading-none transition-all duration-150"
          aria-label="Close detail"
        >×</button>
        {wardName && (
          <div className="text-[15px] font-semibold text-white leading-tight pr-8">{wardName}</div>
        )}
        <div className={`font-mono pr-8 ${wardName ? "text-[11px] text-slate-500 mt-0.5" : "text-[15px] font-semibold text-white leading-tight"}`}>
          {detail.properties.LSOA21NM}
        </div>
        <div className="flex items-start gap-4 mt-3.5">
          {/* Datum-style grade — letter as primary, colour as hairline */}
          <div className="flex flex-col items-center flex-shrink-0 pt-0.5">
            <span className="font-mono font-medium leading-none" style={{ fontSize: 30, color: '#F2F2F2', letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{grade}</span>
            <div className="w-5 h-[2px] rounded-sm mt-2" style={{ background: color }} />
          </div>
          <div>
            <div className="text-xl font-semibold text-white tabular-nums">{detail.windowMean.toFixed(2)} <span className="text-sm text-slate-400 font-normal">µg/m³</span></div>
            <div className="text-[11px] text-slate-500 mt-0.5">mean {pollutant} · {fromYM} → {toYM} · ×{ratio} WHO</div>
          </div>
        </div>
      </section>

      <section className="mb-5">
        <SectionLabel>Monthly trajectory</SectionLabel>
        <TimeSeriesChart rows={detail.rows} fromYM={fromYM} toYM={toYM} pollutant={pollutant} />
        <div className="flex gap-3 text-[10px] text-slate-600 mt-1.5">
          <span><span className="inline-block w-2 h-2 bg-blue-400 rounded-sm mr-1 align-middle" />Monthly {pollutant}</span>
          <span><span className="inline-block w-3 h-2 bg-blue-400/30 rounded-sm mr-1 align-middle" />CI 90 %</span>
          <span><span className="inline-block w-4 border-t-2 border-dashed border-rose-500 mr-1 align-middle" />Forecast</span>
        </div>
      </section>

      {detail.forecast && fcColor && fcValue !== null && (
        <section className="mb-5 rounded-xl border border-rose-500/25 bg-rose-500/[0.07] p-3.5">
          <div className="text-[11px] text-rose-300 font-semibold uppercase tracking-wider mb-2">Forecast {pollutant} · {detail.forecast.year_month}</div>
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center flex-shrink-0">
              <span className="font-mono font-medium leading-none" style={{ fontSize: 24, color: '#F2F2F2', letterSpacing: '-0.02em' }}>{fcGrade}</span>
              <div className="w-4 h-[2px] rounded-sm mt-1.5" style={{ background: fcColor ?? undefined }} />
            </div>
            <div>
              <div className="text-white font-semibold tabular-nums">
                {fcValue.toFixed(2)} <span className="text-xs text-slate-400 font-normal">µg/m³</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                CI 90 %: {detail.forecast.ci_lower.toFixed(2)} – {detail.forecast.ci_upper.toFixed(2)}
              </div>
            </div>
          </div>
        </section>
      )}

      <FilterPanel data={data} />
      <DownloadRanking data={data} />
    </>
  );
}

function SensorsPanel({ data, toYM }: { data: LoadedData; toYM: string }) {
  const timelineKeys = useMemo(() => Object.keys(data.sensorTimeline).sort(), [data.sensorTimeline]);
  const effectiveMonth = (toYM in data.sensorTimeline) ? toYM : (timelineKeys[timelineKeys.length - 1] ?? toYM);
  const activeIds = new Set(data.sensorTimeline[effectiveMonth] ?? []);
  const sensors = data.sensorsGeo.features;

  const litFinal = sensors.filter((s) => activeIds.has(s.properties.device_id) && s.properties.is_final);
  const litOther = sensors.filter((s) => activeIds.has(s.properties.device_id) && !s.properties.is_final);
  const dark     = sensors.filter((s) => !activeIds.has(s.properties.device_id));

  // Sparkline: active sensors per month across the full timeline
  const sparkBars = useMemo(() => {
    const counts = timelineKeys.map((m) => (data.sensorTimeline[m] ?? []).length);
    const max = Math.max(...counts, 1);
    return counts.map((c, i) => ({ count: c, pct: c / max, isNow: timelineKeys[i] === effectiveMonth }));
  }, [timelineKeys, data.sensorTimeline, effectiveMonth]);

  const totalMonths = Object.keys(data.sensorTimeline).length;
  const monthsWithData = Object.values(data.sensorTimeline).filter((ids) => ids.length > 0).length;

  // Node tile config
  const nodes = [
    { label: 'Active · final',    count: litFinal.length, sub: 'Kept for the LUR model',       color: '#10B981', border: 'rgba(16,185,129,0.22)', bg: 'rgba(16,185,129,0.05)', pulse: true },
    { label: 'Active · excluded', count: litOther.length, sub: 'Coverage / quality issues',     color: '#F97316', border: 'rgba(249,115,22,0.18)',  bg: 'rgba(249,115,22,0.04)', pulse: false },
    { label: 'Offline',           count: dark.length,     sub: 'No transmission this month',    color: '#64748B', border: 'rgba(255,255,255,0.06)', bg: 'rgba(10,18,11,0.55)',   pulse: false },
  ];

  return (
    <>
      <section className="mb-4">
        <SectionLabel>Sensor Network</SectionLabel>
        <p className="text-slate-500 text-[11px] leading-relaxed">
          Move the slider to see which sensors were transmitting each month.
        </p>
      </section>

      {/* Node tiles with pulse animation */}
      <section className="mb-4" style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 14, padding: 20 }}>
        <div className="grid grid-cols-3 gap-2.5 mb-4">
          {nodes.map((n) => (
            <div key={n.label} style={{ position: 'relative', padding: '14px 14px 12px', background: n.bg, border: `1px solid ${n.border}`, borderRadius: 10, overflow: 'hidden' }}>
              <div className="flex items-center gap-2 mb-2.5">
                <span
                  className={n.pulse ? 'pulse-dot' : ''}
                  style={{ width: 8, height: 8, borderRadius: '50%', background: n.color, flexShrink: 0 }}
                />
                <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-slate-500">{n.label}</span>
              </div>
              <div className="font-semibold leading-none tabular-nums" style={{ fontSize: 30, color: '#F2F2F2', letterSpacing: '-0.02em' }}>{n.count}</div>
              <div className="mt-1 text-[11px] leading-snug" style={{ color: '#64748b' }}>{n.sub}</div>
            </div>
          ))}
        </div>

        {/* Coverage sparkline */}
        <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 10, padding: '12px 14px' }}>
          <div className="flex justify-between items-baseline mb-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-slate-500">Active sensors · {totalMonths} months</span>
            <span className="font-mono text-[11px] text-slate-400"><strong className="text-slate-100 font-medium">{effectiveMonth}</strong></span>
          </div>
          <div className="flex items-end gap-[2px]" style={{ height: 32 }}>
            {sparkBars.map((b, i) => (
              <div
                key={i}
                style={{
                  flex: 1,
                  height: b.count === 0 ? 2 : Math.max(2, b.pct * 32),
                  background: b.isNow ? '#10B981' : b.count === 0 ? 'rgba(100,116,139,0.25)' : 'rgba(16,185,129,0.35)',
                  borderRadius: '1px 1px 0 0',
                  minHeight: 2,
                }}
              />
            ))}
          </div>
          <div className="flex justify-between mt-1.5 font-mono text-[9px] tracking-[0.04em] text-slate-600">
            <span>{timelineKeys[0]}</span>
            <span>{timelineKeys[Math.floor(timelineKeys.length / 2)]}</span>
            <span>{timelineKeys[timelineKeys.length - 1]}</span>
          </div>
        </div>
      </section>

      {litFinal.length > 0 && (
        <section className="mb-4">
          <SectionLabel>Final online · {effectiveMonth}</SectionLabel>
          <ul className="space-y-1">
            {litFinal.map((s) => (
              <li key={s.properties.device_id} className="text-xs text-slate-300 flex items-center gap-2">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                {s.properties.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      {litOther.length > 0 && (
        <section className="mb-4">
          <SectionLabel>Excluded online · {effectiveMonth}</SectionLabel>
          <ul className="space-y-1">
            {litOther.map((s) => (
              <li key={s.properties.device_id} className="text-xs text-slate-500 flex items-center gap-2">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0" />
                {s.properties.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-2 pt-3 text-[10px] text-slate-700" style={{ borderTop: '1px dashed rgba(255,255,255,0.06)' }}>
        Dataset spans {monthsWithData} months with data across {totalMonths} calendar months.
      </div>
    </>
  );
}
