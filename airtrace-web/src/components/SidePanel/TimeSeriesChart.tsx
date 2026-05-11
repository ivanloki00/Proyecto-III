import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ReferenceArea, ResponsiveContainer,
} from "recharts";
import type { MonthlyRow, Pollutant } from "@/types/lsoa";
import { WHO_PM25, UK_2040, WHO_PM10, gradeOf, gradeOfPM10, GRADE_BINS, GRADE_BINS_PM10 } from "@/lib/scale";

interface Props {
  rows: MonthlyRow[];
  fromYM?: string;
  toYM?: string;
  pollutant?: Pollutant;
}

export function TimeSeriesChart({ rows, fromYM, toYM, pollutant = "PM2.5" }: Props) {
  const lastHistIdx = rows.reduce((last, r, i) => (r.type === "historical" ? i : last), -1);
  const isPM10 = pollutant === "PM10";
  const hasPM10 = rows.some((r) => r["PM10_pred"] !== undefined && r["PM10_pred"] !== null);

  // Expand CI band visually so the margin around the prediction line is clearly readable.
  // The half-width is multiplied by CI_EXPAND; a minimum of 1 µg/m³ half-width is enforced.
  const CI_EXPAND = 3.5;

  const data = rows.map((r, i) => {
    const val = isPM10 && hasPM10 ? (r["PM10_pred"] ?? r["PM2.5_pred"]) : r["PM2.5_pred"];
    const mid    = (r.ci_lower + r.ci_upper) / 2;
    const halfW  = Math.max(1.0, ((r.ci_upper - r.ci_lower) / 2) * CI_EXPAND);
    return {
      ym: r.year_month,
      pmHist: r.type === "historical" ? val : null,
      pmFc: (i === lastHistIdx || r.type === "forecast") ? val : null,
      band: [Math.max(0, mid - halfW), mid + halfW] as [number, number],
      isForecast: r.type === "forecast",
      val,
    };
  });

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
          <Tooltip content={<TSTooltip pollutant={pollutant} />} />

          {/* Selected window highlight */}
          {fromYM && toYM && (
            <ReferenceArea x1={fromYM} x2={toYM} fill="#60a5fa" fillOpacity={0.07} />
          )}

          <Area
            type="monotone" dataKey="band"
            stroke="#60a5fa" strokeWidth={0.8} strokeOpacity={0.45}
            fill="#60a5fa" fillOpacity={0.38}
            isAnimationActive={false}
          />
          {isPM10 ? (
            <ReferenceLine y={WHO_PM10} stroke="#10b981" strokeDasharray="4 3"
              label={{ value: `WHO PM10 ${WHO_PM10} µg`, position: "insideTopRight", fill: "#10b981", fontSize: 9 }} />
          ) : (
            <>
              <ReferenceLine y={WHO_PM25} stroke="#10b981" strokeDasharray="4 3"
                label={{ value: `WHO ${WHO_PM25} µg`, position: "insideTopRight", fill: "#10b981", fontSize: 9 }} />
              <ReferenceLine y={UK_2040} stroke="#f59e0b" strokeDasharray="4 3"
                label={{ value: `UK 2040 · ${UK_2040} µg`, position: "insideTopRight", fill: "#f59e0b", fontSize: 9 }} />
            </>
          )}

          {/* Historical line — solid blue, no dots */}
          <Line
            type="monotone" dataKey="pmHist" stroke="#60a5fa" strokeWidth={2}
            dot={false} isAnimationActive={false} connectNulls={false}
          />
          {/* Forecast line — dashed rose, connects from last historical point */}
          <Line
            type="monotone" dataKey="pmFc" stroke="#f43f5e" strokeWidth={2}
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
    pmHist: number | null;
    pmFc: number | null;
    band: [number, number];
    isForecast: boolean;
    val: number;
  };
}
function TSTooltip({
  active, payload, pollutant = "PM2.5",
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  pollutant?: Pollutant;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const val = p.val ?? 0;
  const grade = pollutant === "PM10" ? gradeOfPM10(val) : gradeOf(val);
  const bins  = pollutant === "PM10" ? GRADE_BINS_PM10 : GRADE_BINS;
  const color = bins.find((b) => b.grade === grade)!.color;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded px-2 py-1.5 text-xs text-slate-100 shadow-lg">
      <div className="font-mono text-slate-400">{p.ym}{p.isForecast ? " · forecast" : ""}</div>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
        <span className="font-semibold">{val.toFixed(2)} µg/m³</span>
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5">
        CI 90 %: {p.band[0].toFixed(2)} – {p.band[1].toFixed(2)}
      </div>
    </div>
  );
}
