import { SCORE_GRADES, SCORE_COLORS, SCORE_THRESHOLDS } from '../../utils/colorScale'

export default function LegendOverlay() {
  return (
    <div
      className="absolute bottom-4 left-4 z-10 bg-surface/90 backdrop-blur-sm border border-border rounded-lg p-3 pointer-events-none"
      role="img"
      aria-label="Leyenda de calidad del aire A–F"
    >
      <p className="text-[10px] uppercase tracking-wide text-text-muted mb-2">
        Calidad del aire
      </p>
      {SCORE_GRADES.map((grade) => (
        <div key={grade} className="flex items-center gap-2 py-0.5">
          <span
            className="w-3 h-3 rounded-sm shrink-0"
            style={{ backgroundColor: SCORE_COLORS[grade] }}
            aria-hidden="true"
          />
          <span className="text-xs font-bold text-text-primary w-4 tabular-nums">
            {grade}
          </span>
          <span className="text-xs text-text-primary">{SCORE_THRESHOLDS[grade]}</span>
        </div>
      ))}
    </div>
  )
}
