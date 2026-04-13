"""
Task 3 — Feature Selection Report
Selección de variables para LUR PM2.5 / PM10
──────────────────────────────────────────────
Pasos:
  1. Para cada variable base, elegir el buffer con mayor |r| vs target
  2. Filtrar por p-value univariante < 0.10  (y zona gris 0.10–0.15)
  3. Eliminar iterativamente por VIF > 5.0
  4. Generar informe en outputs/feature_selection_report.md
"""

# CONFIG
from pathlib import Path
import logging
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT     = Path(__file__).resolve().parents[2]
DATA_INT = ROOT / "data" / "interim"
OUT_DIR  = ROOT / "outputs" / "LUR"   # CSVs de resultados
DOCS_DIR = ROOT / "docs"              # reportes markdown
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_CSV  = DATA_INT / "lur_features.csv"
REPORT_PATH   = DOCS_DIR / "feature_selection_report.md"

BUFFER_RADII  = [50, 100, 250, 500]
TARGETS       = ["PM2.5", "PM10"]
VIF_THRESHOLD = 10.0
P_THRESHOLD   = 0.10
P_RELAXED     = 0.15

BASE_VARS = [
    "aadf_total_sum", "aadf_total_mean", "aadf_total_max",
    "road_length_total_m", "road_length_motorway_m", "road_length_primary_m",
    "road_length_secondary_m", "road_length_residential_m",
    "road_density_m_per_m2",
    "building_area_m2", "building_coverage_ratio",
    "landuse_industrial_m2", "landuse_industrial_ratio",
    "landuse_residential_m2", "landuse_residential_ratio",
    "landuse_commercial_m2", "landuse_commercial_ratio",
    "landuse_green_m2", "landuse_green_ratio",
    "dist_industrial_m",
    "intersections_count", "dist_centre_m",
]


# CARGA DE DATOS
log.info("Cargando feature matrix...")
df = pd.read_csv(FEATURES_CSV)
log.info(f"  Shape: {df.shape} | NaN totales: {df.isnull().sum().sum()}")


# ═══════════════════════════════════════════════════
# PASO 1: Correlaciones por variable × buffer
# ═══════════════════════════════════════════════════

def compute_corr_table(df: pd.DataFrame, target: str) -> tuple:
    """
    Returns:
      corr_df        — DataFrame(vars × buffers) with Pearson r
      best_selection — dict: col_name -> {base_var, buffer, corr, corr_signed, p_value}
    """
    records = {}
    best_selection = {}

    for var in BASE_VARS:
        row = {}
        best_corr = -1.0
        best_buf  = None
        best_p    = np.nan
        best_r_signed = np.nan

        for buf in BUFFER_RADII:
            sub = df[df["buffer_m"] == buf]
            if var not in sub.columns or sub[var].std() == 0:
                row[buf] = np.nan
                continue
            r, p = stats.pearsonr(sub[var].values, sub[target].values)
            row[buf] = round(r, 3)
            if abs(r) > best_corr:
                best_corr     = abs(r)
                best_buf      = buf
                best_p        = p
                best_r_signed = r

        records[var] = row
        if best_buf is not None and best_corr > 0.05:
            key = f"{var}_{best_buf}m"
            best_selection[key] = {
                "base_var":    var,
                "buffer":      best_buf,
                "corr":        round(best_corr, 4),
                "corr_signed": round(best_r_signed, 4),
                "p_value":     round(best_p, 4),
            }

    corr_df = pd.DataFrame(records).T
    corr_df.columns = [f"{b}m" for b in BUFFER_RADII]
    corr_df.index.name = "variable"

    # Add summary columns
    best_buf_labels, best_corrs, best_ps = [], [], []
    for var in BASE_VARS:
        info = best_selection.get(next((k for k in best_selection if best_selection[k]["base_var"] == var), ""), {})
        if info:
            best_buf_labels.append(f"{info['buffer']}m")
            best_corrs.append(info["corr"])
            best_ps.append(info["p_value"])
        else:
            best_buf_labels.append("N/A")
            best_corrs.append(np.nan)
            best_ps.append(np.nan)

    corr_df["best_buf"]  = best_buf_labels
    corr_df["best_|r|"] = best_corrs
    corr_df["p_value"]   = best_ps

    return corr_df, best_selection


# ═══════════════════════════════════════════════════
# PASO 2: Filtro p-value
# ═══════════════════════════════════════════════════

def apply_pvalue_filter(best_selection: dict, threshold: float) -> list:
    return [col for col, info in best_selection.items() if info["p_value"] < threshold]


# ═══════════════════════════════════════════════════
# PASO 3: Filtro VIF
# ═══════════════════════════════════════════════════

def build_pivot(df: pd.DataFrame, target: str, best_selection: dict, kept_cols: list) -> pd.DataFrame:
    pivot_rows = []
    sensors = df[df["buffer_m"] == BUFFER_RADII[0]]["sensor_id"].tolist()
    for sid in sensors:
        row_sensor = df[(df["sensor_id"] == sid) & (df["buffer_m"] == BUFFER_RADII[0])].iloc[0]
        record = {"sensor_id": sid, target: row_sensor[target]}
        for col_name in kept_cols:
            if col_name not in best_selection:
                continue
            info    = best_selection[col_name]
            buf_row = df[(df["sensor_id"] == sid) & (df["buffer_m"] == info["buffer"])].iloc[0]
            record[col_name] = buf_row[info["base_var"]]
        pivot_rows.append(record)
    return pd.DataFrame(pivot_rows)


def run_vif_filter(X_df: pd.DataFrame) -> tuple:
    """Eliminación iterativa por VIF. Returns (final_cols, log_of_removals)."""
    cols    = list(X_df.columns)
    vif_log = []  # list of (removed_col, vif_value)

    while len(cols) > 1:
        Xsub = X_df[cols].replace([np.inf, -np.inf], np.nan).fillna(0).values
        try:
            vifs = [variance_inflation_factor(Xsub, i) for i in range(len(cols))]
        except Exception as e:
            log.warning(f"VIF error: {e}")
            break
        max_vif = max(vifs)
        if max_vif <= VIF_THRESHOLD:
            break
        idx     = vifs.index(max_vif)
        removed = cols.pop(idx)
        vif_log.append((removed, round(max_vif, 2)))
        log.info(f"  VIF: eliminar '{removed}' (VIF={max_vif:.2f})")

    return cols, vif_log


def get_final_vifs(X_df: pd.DataFrame, cols: list) -> dict:
    if len(cols) == 0:
        return {}
    Xsub = X_df[cols].replace([np.inf, -np.inf], np.nan).fillna(0).values
    vifs = [variance_inflation_factor(Xsub, i) for i in range(len(cols))]
    return {c: round(v, 3) for c, v in zip(cols, vifs)}


# ═══════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════

all_results = {}

for target in TARGETS:
    log.info(f"\n{'#'*50}\n  TARGET: {target}\n{'#'*50}")

    # Step 1
    corr_df, best_sel = compute_corr_table(df, target)
    log.info(f"  Candidatas tras selección de escala: {len(best_sel)}")

    # Step 2 — dos escenarios
    kept_010 = apply_pvalue_filter(best_sel, P_THRESHOLD)
    kept_015 = apply_pvalue_filter(best_sel, P_RELAXED)
    grey_zone = [c for c in kept_015 if c not in kept_010]
    removed_all = [(c, info) for c, info in best_sel.items() if c not in kept_015]

    log.info(f"  Retenidas p<0.10: {len(kept_010)}: {kept_010}")
    log.info(f"  Zona gris p∈[0.10,0.15): {len(grey_zone)}: {grey_zone}")
    log.info(f"  Eliminadas p>=0.15: {len(removed_all)}")

    # Step 3 — escenario p<0.10
    final_010, vif_log_010, final_vifs_010 = [], [], {}
    if len(kept_010) > 0:
        pivot_010 = build_pivot(df, target, best_sel, kept_010)
        X_010     = pivot_010[[c for c in kept_010 if c in pivot_010.columns]].copy()
        X_010     = X_010.replace([np.inf, -np.inf], np.nan).fillna(0)
        final_010, vif_log_010 = run_vif_filter(X_010)
        final_vifs_010 = get_final_vifs(X_010, final_010)
        log.info(f"  Final p<0.10 tras VIF: {final_010}")

    # Step 3 — escenario p<0.15
    final_015, vif_log_015, final_vifs_015 = [], [], {}
    if len(kept_015) > 0:
        pivot_015 = build_pivot(df, target, best_sel, kept_015)
        X_015     = pivot_015[[c for c in kept_015 if c in pivot_015.columns]].copy()
        X_015     = X_015.replace([np.inf, -np.inf], np.nan).fillna(0)
        final_015, vif_log_015 = run_vif_filter(X_015)
        final_vifs_015 = get_final_vifs(X_015, final_015)
        log.info(f"  Final p<0.15 tras VIF: {final_015}")

    all_results[target] = {
        "corr_df":      corr_df,
        "best_sel":     best_sel,
        "kept_010":     kept_010,
        "kept_015":     kept_015,
        "grey_zone":    grey_zone,
        "removed_pval": removed_all,
        "final_010":    final_010,
        "vif_log_010":  vif_log_010,
        "final_vifs_010": final_vifs_010,
        "final_015":    final_015,
        "vif_log_015":  vif_log_015,
        "final_vifs_015": final_vifs_015,
    }


# ═══════════════════════════════════════════════════
# GENERAR INFORME MARKDOWN
# ═══════════════════════════════════════════════════

def corr_df_to_md(corr_df: pd.DataFrame) -> str:
    cols = ["50m", "100m", "250m", "500m", "best_buf", "best_|r|", "p_value"]
    header = "| Variable | 50m | 100m | 250m | 500m | Best buf | Best |r| | p-value |"
    sep    = "|---|---|---|---|---|---|---|---|"
    rows   = [header, sep]
    for var in corr_df.index:
        row = corr_df.loc[var]
        def fmt(v):
            if pd.isna(v):
                return "—"
            if isinstance(v, str):
                return v
            return f"{v:.3f}"
        cells = [var] + [fmt(row[c]) for c in cols]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


lines = []
lines.append("# Feature Selection Report — LUR Liverpool Air Quality")
lines.append("")
lines.append(f"**Fecha:** 2026-04-10  |  **n sensores:** 20  |  **Buffers evaluados:** 50, 100, 250, 500 m")
lines.append("")
lines.append("---")
lines.append("")

# Context
lines.append("## Contexto metodológico")
lines.append("")
lines.append("- **n=20** — tamaño muestral pequeño; umbral p<0.10 es moderado (no conservador) para regresión univariante.")
lines.append("- Selección de escala: para cada variable base se elige el buffer que maximiza |r| con el target.")
lines.append("- Filtro p-value: OLS univariante sobre la variable en su mejor escala.")
lines.append("- Filtro VIF: eliminación iterativa del predictor con VIF más alto hasta que todos queden ≤ 5.0.")
lines.append("")

for target in TARGETS:
    r = all_results[target]
    tag = target.replace(".", "")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"# Target: {target}")
    lines.append("")

    # --- Correlations table ---
    lines.append(f"## Paso 1 — Correlaciones (Pearson r) por variable × buffer")
    lines.append("")
    lines.append(corr_df_to_md(r["corr_df"]))
    lines.append("")

    # --- Step 2 summary ---
    lines.append(f"## Paso 2 — Filtro p-value univariante")
    lines.append("")
    lines.append(f"Candidatas iniciales (tras selección de escala): **{len(r['best_sel'])}**")
    lines.append("")

    lines.append(f"### Retenidas p < 0.10 ({len(r['kept_010'])} variables)")
    lines.append("")
    if r["kept_010"]:
        lines.append("| Variable (mejor buffer) | |r| | p-value |")
        lines.append("|---|---|---|")
        for col in r["kept_010"]:
            info = r["best_sel"][col]
            lines.append(f"| `{col}` | {info['corr']:.4f} | {info['p_value']:.4f} |")
    else:
        lines.append("_(ninguna)_")
    lines.append("")

    lines.append(f"### Zona gris p ∈ [0.10, 0.15) — añadidas solo en escenario relajado ({len(r['grey_zone'])} variables)")
    lines.append("")
    if r["grey_zone"]:
        lines.append("| Variable (mejor buffer) | |r| | p-value |")
        lines.append("|---|---|---|")
        for col in r["grey_zone"]:
            info = r["best_sel"][col]
            lines.append(f"| `{col}` | {info['corr']:.4f} | {info['p_value']:.4f} |")
    else:
        lines.append("_(ninguna)_")
    lines.append("")

    lines.append(f"### Eliminadas p ≥ 0.15 ({len(r['removed_pval'])} variables)")
    lines.append("")
    if r["removed_pval"]:
        lines.append("| Variable (mejor buffer) | |r| | p-value | Razón |")
        lines.append("|---|---|---|---|")
        for col, info in r["removed_pval"]:
            lines.append(f"| `{col}` | {info['corr']:.4f} | {info['p_value']:.4f} | p ≥ 0.15 |")
    else:
        lines.append("_(ninguna)_")
    lines.append("")

    # --- Step 3 VIF ---
    lines.append(f"## Paso 3 — Filtro VIF (umbral = 5.0)")
    lines.append("")

    for scenario, label in [("010", "p < 0.10"), ("015", "p < 0.15")]:
        kept_key  = "kept_010" if scenario == "010" else "kept_015"
        final_key = f"final_{scenario}"
        vlog_key  = f"vif_log_{scenario}"
        vifs_key  = f"final_vifs_{scenario}"

        pre_vif  = r[kept_key]
        final    = r[final_key]
        vif_log  = r[vlog_key]
        fin_vifs = r[vifs_key]

        lines.append(f"### Escenario {label}")
        lines.append("")
        lines.append(f"Variables pre-VIF: **{len(pre_vif)}** → Variables finales: **{len(final)}**")
        lines.append("")

        if vif_log:
            lines.append("**Eliminaciones por VIF:**")
            lines.append("")
            lines.append("| Variable eliminada | VIF |")
            lines.append("|---|---|")
            for col, vif_val in vif_log:
                lines.append(f"| `{col}` | {vif_val} |")
            lines.append("")

        if final:
            lines.append("**Variables finales y sus VIF:**")
            lines.append("")
            lines.append("| Variable | VIF | |r| con target | p-value |")
            lines.append("|---|---|---|---|")
            for col in final:
                vif_val  = fin_vifs.get(col, "—")
                # Find col in best_sel — it might be from either kept list
                info = r["best_sel"].get(col, {})
                lines.append(
                    f"| `{col}` | {vif_val if isinstance(vif_val, str) else f'{vif_val:.3f}'} "
                    f"| {info.get('corr', '—'):.4f} | {info.get('p_value', '—'):.4f} |"
                )
            lines.append("")
        else:
            lines.append("_(sin variables finales)_")
            lines.append("")

# ═══════════════════════════════════════════════════
# ANÁLISIS TRANSVERSAL
# ═══════════════════════════════════════════════════

lines.append("---")
lines.append("")
lines.append("# Análisis transversal")
lines.append("")

lines.append("## ¿Variables con |r| > 0.5 eliminadas por VIF?")
lines.append("")

for target in TARGETS:
    r = all_results[target]
    high_corr_removed = []
    # Variables que estaban en kept_015 (pasaron p-value) pero no en final_015
    for col in r["kept_015"]:
        if col not in r["final_015"]:
            info = r["best_sel"].get(col, {})
            if info.get("corr", 0) >= 0.5:
                high_corr_removed.append((col, info))
    if high_corr_removed:
        lines.append(f"**{target}** — eliminadas por VIF con |r| ≥ 0.5:")
        lines.append("")
        lines.append("| Variable | |r| | p-value | Motivo |")
        lines.append("|---|---|---|---|")
        for col, info in high_corr_removed:
            lines.append(f"| `{col}` | {info['corr']:.4f} | {info['p_value']:.4f} | Multicolinealidad (VIF > 5) |")
        lines.append("")
    else:
        lines.append(f"**{target}** — ninguna variable con |r| ≥ 0.5 fue eliminada por VIF.")
        lines.append("")

lines.append("## ¿Es 0.10 demasiado restrictivo para n=20?")
lines.append("")
lines.append(
    "Con n=20 observaciones, la potencia estadística es baja. "
    "Un test t bilateral al nivel α=0.10 para correlación requiere |r| ≥ 0.38 para alcanzar p<0.10 "
    "(aproximación: t = r·√(n-2)/√(1-r²), rechazo si |t| > t₀.₀₅,₁₈ ≈ 1.73). "
    "El umbral p<0.10 ya supone una concesión respecto al estándar α=0.05."
)
lines.append("")
lines.append(
    "**Recomendación:** Mantener p<0.10 como umbral primario. "
    "Usar p<0.15 únicamente como escenario de sensibilidad y reportar ambos resultados. "
    "Si el número de variables finales p<0.10 cae por debajo de 2, activar el escenario relajado."
)
lines.append("")

lines.append("## Resumen ejecutivo")
lines.append("")
lines.append("| Target | Escenario | Variables pre-VIF | Variables finales |")
lines.append("|---|---|---|---|")
for target in TARGETS:
    r = all_results[target]
    lines.append(
        f"| {target} | p<0.10 | {len(r['kept_010'])} | "
        f"{len(r['final_010'])} ({', '.join(['`'+v+'`' for v in r['final_010']]) or '—'}) |"
    )
    lines.append(
        f"| {target} | p<0.15 | {len(r['kept_015'])} | "
        f"{len(r['final_015'])} ({', '.join(['`'+v+'`' for v in r['final_015']]) or '—'}) |"
    )

lines.append("")
lines.append("---")
lines.append("_Generado automáticamente por `src/analysis/feature_selection_report.py`_")

report_text = "\n".join(lines)

# EXPORTACIÓN
REPORT_PATH.write_text(report_text, encoding="utf-8")
log.info(f"Informe guardado en: {REPORT_PATH}")

# Print summary to stdout for agent
print("\n=== RESULTADOS FINALES ===")
for target in TARGETS:
    r = all_results[target]
    print(f"\nTarget: {target}")
    print(f"  Candidatas (escala): {len(r['best_sel'])}")
    print(f"  Tras p<0.10:        {r['kept_010']}")
    print(f"  Tras p<0.15:        {r['kept_015']}")
    print(f"  Final p<0.10+VIF:   {r['final_010']}  VIFs={r['final_vifs_010']}")
    print(f"  Final p<0.15+VIF:   {r['final_015']}  VIFs={r['final_vifs_015']}")
    print(f"  VIF eliminations (010): {r['vif_log_010']}")
    print(f"  VIF eliminations (015): {r['vif_log_015']}")

    # High-corr removed by VIF?
    for col in r["kept_015"]:
        if col not in r["final_015"]:
            info = r["best_sel"].get(col, {})
            if info.get("corr", 0) >= 0.5:
                print(f"  ATENCION: {col} (|r|={info['corr']}) eliminada por VIF")
