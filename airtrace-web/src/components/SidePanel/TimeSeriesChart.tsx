import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ReferenceArea, ResponsiveContainer,
} from "recharts";
import type { MonthlyRow } from "@/types/lsoa";
import { WHO_PM25, UK_2040, gradeOf, GRADE_BINS } from "@/lib/scale";

interface Props {
  rows: MonthlyRow[];
  fromYM?: string;
  toYM?: string;
}

export function TimeSeriesChart({ rows, fromYM, toYM }: Props) {
  const lastHistIdx = rows.reduce((last, r, i) => (r.type === "historical" ? i : last), -1);

  const data = rows.map((r, i) => ({
    ym: r.year_month,
    pm25Hist: r.type === "historical" ? r["PM2.5_pred"] : null,
    // Bridge: include the last historical value in the forecast series so the
    // dashed line visually connects from the last real point to the forecast.
    pm25Fc: (i === lastHistIdx || r.type === "forecast") ? r["PM2.5_pred"] : null,
    band: [r.ci_lower, r.ci_upper] as [number, number],
    isForecast: r.type === "forecast",
  }));

  const yearTicks = Array.from(
    new Set(data.map((d) => d.ym).filter((ym) => ym.endsWith("-01"))),
  );

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="ym"
            ticks={yearTicks}
            tickFormatter={(v: string) => v.slice(0, 4)}
            stroke="#64748b"
            fontSize={10}
          />
          <YAxis stroke="#64748b" fontSize={10} domain={[0, "auto"]} />
          <Tooltip content={<TSTooltip />} />

          {/* Selected window highlight */}
          {fromYM && toYM && (
            <ReferenceArea x1={fromYM} x2={toYM} fill="#60a5fa" fillOpacity={0.07} />
          )}

          <Area
            type="monotone" dataKey="band" stroke="none" fill="#60a5fa" fillOpacity={0.18} isAnimationActive={false}
          />
          <ReferenceLine y={WHO_PM25} stroke="#10b981" strokeDasharray="4 3" />
          <ReferenceLine y={UK_2040} stroke="#f59e0b" strokeDasharray="4 3" />

          {/* Historical line — solid blue, no dots */}
          <Line
            type="monotone" dataKey="pm25Hist" stroke="#60a5fa" strokeWidth={2}
            dot={false} isAnimationActive={false} connectNulls={false}
          />
          {/* Forecast line — dashed rose, connects from last historical point */}
          <Line
            type="monotone" dataKey="pm25Fc" stroke="#f43f5e" strokeWidth={2}
            strokeDasharray="6 3" dot={false} isAnimationActive={false} connectNulls={true}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

interface TooltipPayloadEntry {
  payload: {
    ym: string;
    pm25Hist: number | null;
    pm25Fc: number | null;
    band: [number, number];
    isForecast: boolean;
  };
}
function TSTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadEntry[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const pm25 = p.pm25Hist ?? p.pm25Fc ?? 0;
  const grade = gradeOf(pm25);
  const color = GRADE_BINS.find((b) => b.grade === grade)!.color;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-100 shadow-lg">
      <div className="font-mono text-slate-400">{p.ym}{p.isForecast ? " · forecast" : ""}</div>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
        <span className="font-semibold">{pm25.toFixed(2)} µg/m³</span>
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5">
        CI 90 %: {p.band[0].toFixed(2)} – {p.band[1].toFixed(2)}
      </div>
    </div>
  );
}
