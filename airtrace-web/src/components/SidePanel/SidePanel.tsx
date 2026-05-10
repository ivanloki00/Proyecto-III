import type { LoadedData } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { TimeSeriesChart } from "@/components/SidePanel/TimeSeriesChart";
import { FilterPanel } from "@/components/Controls/FilterPanel";
import { DownloadRanking } from "@/components/Export/DownloadRanking";
import { WHO_PM25, WHO_PM10, binsForPollutant, gradeForPollutant } from "@/lib/scale";
import type { Pollutant } from "@/types/lsoa";
import { useMemo } from "react";

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
    <aside className="w-[420px] h-full overflow-y-auto bg-slate-900 border-l border-slate-800 p-5 text-sm">
      <header className="mb-5">
        <h1 className="text-xl font-semibold text-white">AirTrace</h1>
        <p className="text-slate-400 text-xs mt-1">Liverpool · {pollutant} air quality</p>
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

function StreetsPanel({ data, totalRows }: { data: LoadedData; totalRows: number }) {
  const nLsoas = data.lsoaGeo.features.length;
  const nStreets = data.streetsGeo.features.length;
  const nMonths = data.months.length;
  return (
    <>
      <section className="mb-5">
        <h2 className="text-slate-300 font-medium mb-2">Streets View</h2>
        <p className="text-slate-400 text-xs">
          Click any segment to see its grade. The annual values come from the LUR model
          predictions (R² = 0.60 on PM2.5 under LOOCV).
        </p>
        <p className="text-slate-500 text-xs mt-2">
          Switch to <span className="text-slate-300">Neighbourhoods</span> to use the date slider,
          time-series chart and ranking export.
        </p>
      </section>
      <section>
        <h2 className="text-slate-300 font-medium mb-2">Data loaded</h2>
        <dl className="grid grid-cols-2 gap-y-1 text-slate-400">
          <dt>Streets</dt><dd className="text-white">{nStreets.toLocaleString()}</dd>
          <dt>LSOAs</dt><dd className="text-white">{nLsoas}</dd>
          <dt>Months</dt><dd className="text-white">{nMonths}</dd>
          <dt>Series rows</dt><dd className="text-white">{totalRows.toLocaleString()}</dd>
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
        <section className="mb-5 rounded-md border border-slate-700 bg-slate-800/40 p-3 text-xs text-slate-300">
          <p className="font-medium mb-1">No area selected</p>
          <p className="text-slate-400">Click any polygon on the map to see its monthly trajectory, 90 % CI band and forecast.</p>
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
      <section className="mb-5 rounded-md border border-slate-700 bg-slate-800/60 p-3 relative">
        <button
          onClick={onCloseDetail}
          className="absolute top-2 right-2 text-slate-500 hover:text-white text-lg leading-none"
          aria-label="Close detail"
        >×</button>
        {wardName && (
          <div className="text-lg font-semibold text-white leading-tight pr-6">{wardName}</div>
        )}
        <div className={`font-mono pr-6 ${wardName ? "text-[11px] text-slate-500 mt-0.5" : "text-base font-semibold text-white leading-tight"}`}>
          {detail.properties.LSOA21NM}
        </div>
        <div className="flex items-center gap-3 mt-3">
          <span
            className="inline-block w-9 h-9 rounded-md text-center leading-9 font-bold text-white"
            style={{ backgroundColor: color }}
          >{grade}</span>
          <div>
            <div className="text-xl font-semibold text-white">{detail.windowMean.toFixed(2)} <span className="text-sm text-slate-400">µg/m³</span></div>
            <div className="text-[11px] text-slate-400">mean {pollutant} over {fromYM} → {toYM} · × {ratio} above WHO</div>
          </div>
        </div>
      </section>

      <section className="mb-5">
        <h2 className="text-slate-300 font-medium mb-2">Monthly trajectory</h2>
        <TimeSeriesChart rows={detail.rows} fromYM={fromYM} toYM={toYM} pollutant={pollutant} />
        <div className="flex gap-3 text-[10px] text-slate-500 mt-1">
          <span><span className="inline-block w-2 h-2 bg-blue-400 rounded-sm mr-1 align-middle" />Monthly {pollutant}</span>
          <span><span className="inline-block w-3 h-2 bg-blue-400/30 rounded-sm mr-1 align-middle" />CI 90 %</span>
          <span><span className="inline-block w-4 border-t-2 border-dashed border-rose-500 mr-1 align-middle" />Forecast</span>
        </div>
      </section>

      {detail.forecast && fcColor && fcValue !== null && (
        <section className="mb-5 rounded-md border border-rose-500/30 bg-rose-500/10 p-3">
          <div className="text-xs text-rose-200 font-medium mb-1">Forecast {pollutant} for {detail.forecast.year_month}</div>
          <div className="flex items-center gap-3">
            <span className="inline-block w-7 h-7 rounded-md text-center leading-7 font-bold text-white text-sm" style={{ backgroundColor: fcColor }}>
              {fcGrade}
            </span>
            <div>
              <div className="text-white font-semibold">
                {fcValue.toFixed(2)} <span className="text-xs text-slate-400">µg/m³</span>
              </div>
              <div className="text-[11px] text-slate-400">
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

  const totalMonths = Object.keys(data.sensorTimeline).length;
  const monthsWithData = Object.values(data.sensorTimeline).filter((ids) => ids.length > 0).length;

  return (
    <>
      <section className="mb-4">
        <h2 className="text-slate-300 font-medium mb-1">Sensor Network</h2>
        <p className="text-slate-500 text-[11px]">
          Move the slider to see which sensors were transmitting each month.
        </p>
      </section>

      {/* Live snapshot for toYM */}
      <section className="mb-4 rounded-md border border-slate-700 bg-slate-800/50 p-3">
        <div className="text-[11px] text-slate-400 mb-2 font-mono">
          {effectiveMonth}{effectiveMonth !== toYM ? <span className="text-slate-600 ml-1">(forecast → latest data)</span> : null}
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-xl font-bold text-emerald-400">{litFinal.length}</div>
            <div className="text-[10px] text-emerald-300 leading-tight mt-0.5">active<br/>final</div>
          </div>
          <div>
            <div className="text-xl font-bold text-orange-400">{litOther.length}</div>
            <div className="text-[10px] text-orange-300 leading-tight mt-0.5">active<br/>excluded</div>
          </div>
          <div>
            <div className="text-xl font-bold text-slate-500">{dark.length}</div>
            <div className="text-[10px] text-slate-500 leading-tight mt-0.5">offline<br/>&nbsp;</div>
          </div>
        </div>
      </section>

      {/* Legend */}
      <section className="mb-4 text-[11px] text-slate-400 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full bg-emerald-400 flex-shrink-0" />
          <span>Active &amp; kept for LUR model <span className="text-emerald-300 font-medium">(21 final)</span></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full bg-orange-400 flex-shrink-0" />
          <span>Active but excluded (coverage / quality issues)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 rounded-full bg-slate-600 flex-shrink-0" />
          <span>Offline this month</span>
        </div>
      </section>

      {/* Active sensors list for this month */}
      {litFinal.length > 0 && (
        <section className="mb-4">
          <h3 className="text-slate-400 text-[11px] font-medium mb-1.5">
            Final sensors online in {toYM}
          </h3>
          <ul className="space-y-0.5">
            {litFinal.map((s) => (
              <li key={s.properties.device_id} className="text-xs text-slate-200 flex items-center gap-1.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                {s.properties.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      {litOther.length > 0 && (
        <section className="mb-4">
          <h3 className="text-slate-400 text-[11px] font-medium mb-1.5">
            Excluded sensors online in {toYM}
          </h3>
          <ul className="space-y-0.5">
            {litOther.map((s) => (
              <li key={s.properties.device_id} className="text-xs text-slate-400 flex items-center gap-1.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0" />
                {s.properties.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-2 pt-3 border-t border-slate-800 text-[10px] text-slate-600">
        Dataset spans {monthsWithData} months across {totalMonths} calendar months.
      </div>
    </>
  );
}
