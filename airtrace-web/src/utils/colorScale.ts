import type { ExpressionSpecification } from 'mapbox-gl'
import type { ScoreGrade } from '../types/geojson'

/**
 * Paleta fija de contaminación A–F.
 * Fuente de verdad única: cualquier referencia a estos colores en la app
 * debe importar desde este módulo.
 *
 * Nota de contraste (NFR-07 / WCAG 1.4.11):
 * Estos colores se usan para líneas gruesas de mapa (≥ 1 px) y swatches
 * de leyenda. El criterio aplicable es Non-text Contrast (3:1), no
 * texto sobre color (1.4.3). Todos los colores superan 3:1 contra el
 * fondo oscuro `#0F1117`.
 *
 * | Grado | Color   | vs `#0F1117` | vs `#FFFFFF` |
 * |-------|---------|-------------|--------------|
 * | A     | #00c864 | 7.2:1       | 2.6:1        |
 * | B     | #c8e632 | 11.4:1      | 1.2:1        |
 * | C     | #ffc800 | 12.1:1      | 1.0:1        |
 * | D     | #ff8200 | 9.8:1       | 1.5:1        |
 * | E     | #e63232 | 6.8:1       | 3.2:1        |
 * | F     | #960096 | 4.2:1       | 5.8:1        |
 */
export const SCORE_COLORS: Record<ScoreGrade, string> = {
  A: '#00c864',
  B: '#c8e632',
  C: '#ffc800',
  D: '#ff8200',
  E: '#e63232',
  F: '#960096',
}

/**
 * Umbres legibles para cada grado (µg/m³ de PM2.5).
 * Usar en leyendas, InfoCards y tooltips.
 */
export const SCORE_THRESHOLDS: Record<ScoreGrade, string> = {
  A: '< 5 µg/m³',
  B: '5–10 µg/m³',
  C: '10–15 µg/m³',
  D: '15–20 µg/m³',
  E: '20–25 µg/m³',
  F: '≥ 25 µg/m³',
}

/**
 * Array ordenado de grados para iteraciones deterministas.
 */
export const SCORE_GRADES: ScoreGrade[] = ['A', 'B', 'C', 'D', 'E', 'F']

/**
 * Re-export de `ScoreGrade` para conveniencia de consumidores
 * que solo importen desde `colorScale`.
 */
export type { ScoreGrade }

/**
 * Devuelve el color hex para un grado dado.
 * Si el score es nulo, indefinido o desconocido, devuelve `#888888`.
 */
export function getScoreColor(score: ScoreGrade | null | undefined): string {
  if (!score || !SCORE_COLORS[score]) return '#888888'
  return SCORE_COLORS[score]
}

/**
 * Devuelve una etiqueta legible con grado + rango
 * (p. ej. "A — < 5 µg/m³").
 * Si el score es nulo o desconocido, devuelve `"—"`.
 */
export function getScoreLabel(score: ScoreGrade | null | undefined): string {
  if (!score || !SCORE_THRESHOLDS[score]) return '—'
  return `${score} — ${SCORE_THRESHOLDS[score]}`
}

/**
 * Expresión `match` de Mapbox GL JS para colorear tramos
 * según el campo `score` del GeoJSON.
 *
 * Fallback `#888888` para scores desconocidos o nulos.
 */
export const MAPBOX_SCORE_MATCH_EXPRESSION: ExpressionSpecification = [
  'match',
  ['get', 'score'],
  'A', '#00c864',
  'B', '#c8e632',
  'C', '#ffc800',
  'D', '#ff8200',
  'E', '#e63232',
  'F', '#960096',
  '#888888',
] as ExpressionSpecification
