import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer,
} from "recharts";
import type { MonthlyRow } from "@/types/lsoa";
import { WHO_PM25, UK_2040, gradeOf, GRADE_BINS } from "@/lib/scale";

interface Props { rows: MonthlyRow[]; }

/**
 * Monthly PM2.5 with 90% CI band, plus reference lines for WHO and UK 2040.
 * The forecast point is the single row with type === "forecast".
 */
export function TimeSeriesChart({ rows }: Props) {
  const data = rows.map((r) => ({
    ym: r.year_month,
    pm25: r["PM2.5_pred"],
    band: [r.ci_lower, r.ci_upper],
    isForecast: r.type === "forecast" ? r["PM2.5_pred"] : null,
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
          <Area
            type="monotone" dataKey="band" stroke="none" fill="#60a5fa" fillOpacity={0.18} isAnimationActive={false}
          />
          <ReferenceLine y={WHO_PM25} stroke="#10b981" strokeDasharray="4 3" />
          <ReferenceLine y={UK_2040} stroke="#f59e0b" strokeDasharray="4 3" />
          <Line
            type="monotone" dataKey="pm25" stroke="#60a5fa" strokeWidth={2} dot={false} isAnimationActive={false}
          />
          <Line
            type="monotone" dataKey="isForecast" stroke="#f43f5e" strokeWidth={0} dot={{ r: 3, fill: "#f43f5e" }} isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

interface TooltipPayloadEntry {
  payload: { ym: string; pm25: number; band: [number, number]; isForecast: number | null };
}
function TSTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadEntry[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const grade = gradeOf(p.pm25);
  const color = GRADE_BINS.find((b) => b.grade === grade)!.color;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-100 shadow-lg">
      <div className="font-mono text-slate-400">{p.ym}{p.isForecast !== null ? " · forecast" : ""}</div>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
        <span className="font-semibold">{p.pm25.toFixed(2)} µg/m³</span>
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5">
        CI 90 %: {p.band[0].toFixed(2)} – {p.band[1].toFixed(2)}
      </div>
    </div>
  );
}
