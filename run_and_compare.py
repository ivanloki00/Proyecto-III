"""
run_and_compare.py — Ejecuta el pipeline mejorado y compara con el baseline
============================================================================
Uso:
    python run_and_compare.py

Qué hace:
  1. Guarda las métricas del modelo existente (BASELINE)
  2. Ejecuta las descargas externas opcionales (AURN, meteo, elevación)
  3. Re-ejecuta feature engineering + modelo + validación
  4. Imprime tabla de comparación ANTES vs DESPUÉS
  5. Escribe outputs/comparison_report.md
"""

import subprocess
import sys
import pickle
import json

# Forzar UTF-8 en stdout/stderr para evitar UnicodeEncodeError en terminales Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT    = Path(__file__).resolve().parent
OUT_DIR   = ROOT / "data" / "processed" / "LUR"   # CSVs de resultados
MODELS_DIR = ROOT / "outputs" / "models"  # modelos .pkl
DOCS_DIR   = ROOT / "docs"               # reportes markdown

PYTHON = sys.executable  # mismo intérprete que está ejecutando este script


# ── COLORES para terminal ─────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def colored(text, color):
    return f"{color}{text}{RESET}"

def delta_str(before, after, higher_better=True):
    """Devuelve string con delta y color: verde si mejora, rojo si empeora."""
    if before is None or after is None:
        return "N/A"
    try:
        d = after - before
        if d == 0:
            return f"±0.000"
        better = (d > 0) == higher_better
        sign   = "+" if d > 0 else ""
        color  = GREEN if better else RED
        return colored(f"{sign}{d:.4f}", color)
    except Exception:
        return "N/A"


# ── 1. CAPTURAR BASELINE ──────────────────────────────────────────────────────

def load_model_metrics(pkl_path: Path) -> dict:
    """Lee métricas de un pickle de modelo LUR."""
    if not pkl_path.exists():
        return {}
    with open(pkl_path, "rb") as f:
        m = pickle.load(f)
    return {
        "model_name":      m.get("model_name", "?"),
        "features":        m.get("features", []),
        "n_features":      len(m.get("features", [])),
        "r2_cv":           m.get("r2_cv"),
        "rmse_cv":         m.get("rmse_cv"),
        "bp_pvalue":       m.get("bp_pvalue"),
        "moran_I":         m.get("moran_I"),
        "moran_p":         m.get("moran_p"),
        "r2_spatial_cv":   m.get("r2_spatial_cv"),     # None si era modelo antiguo
        "rmse_spatial_cv": m.get("rmse_spatial_cv"),
        "n_obs":           m.get("n_obs", 20),         # 20 = anual legacy
        "is_panel":        m.get("is_panel", False),
    }


def capture_baseline():
    log.info("── Capturando métricas BASELINE ─────────────────────────────────")
    baseline = {}
    for tag, label in [("PM25","PM2.5"), ("PM10","PM10")]:
        pkl = MODELS_DIR / f"lur_model_{tag}.pkl"
        baseline[label] = load_model_metrics(pkl)
        if baseline[label]:
            log.info(f"  {label}: R²_CV={baseline[label]['r2_cv']:.4f}, "
                     f"RMSE={baseline[label]['rmse_cv']:.4f}, "
                     f"features={baseline[label]['features']}")
        else:
            log.warning(f"  {label}: modelo no encontrado en {pkl}")
    return baseline


# ── 2. EJECUTAR SCRIPTS ───────────────────────────────────────────────────────

def run(script_path: Path, label: str, optional: bool = False) -> bool:
    """Ejecuta un script Python y devuelve True si tuvo éxito."""
    if not script_path.exists():
        if not optional:
            log.error(f"  {label}: script no encontrado → {script_path}")
        return False

    log.info(f"\n{'='*60}")
    log.info(f"  EJECUTANDO: {label}")
    log.info(f"  Script: {script_path.relative_to(ROOT)}")
    log.info(f"{'='*60}")

    result = subprocess.run(
        [PYTHON, str(script_path)],
        cwd=str(ROOT),
        capture_output=False,   # mostrar output en tiempo real
    )

    if result.returncode == 0:
        log.info(f"  ✓ {label} completado")
        return True
    else:
        if optional:
            log.warning(f"  ⚠ {label} falló (opcional — continuando)")
        else:
            log.error(f"  ✗ {label} falló con código {result.returncode}")
        return False


# ── 3. COMPARACIÓN ────────────────────────────────────────────────────────────

def print_comparison(before: dict, after: dict):
    """Imprime tabla de comparación ANTES vs DESPUÉS."""
    print(f"\n{'='*70}")
    print(colored(f"  COMPARACIÓN ANTES vs DESPUÉS — {datetime.now().strftime('%Y-%m-%d %H:%M')}", BOLD))
    print(f"{'='*70}\n")

    headers = ["Métrica", "ANTES", "DESPUÉS", "Δ (mejora si +)"]
    col_w   = [35, 12, 12, 20]

    def row(cells):
        return "  " + "".join(str(c).ljust(w) for c, w in zip(cells, col_w))

    print(row(headers))
    print("  " + "-" * sum(col_w))

    for label in ["PM2.5", "PM10"]:
        b = before.get(label, {})
        a = after.get(label,  {})
        print(f"\n  ── {label} ──────────────────────────────────────────────")

        # Modelo seleccionado
        b_model = b.get("model_name", "?")
        a_model = a.get("model_name", "?")
        changed = a_model != b_model
        print(row(["Modelo",
                   b_model,
                   colored(a_model, GREEN) if changed else a_model,
                   colored("CAMBIÓ", YELLOW) if changed else "igual"]))

        # n observaciones
        b_n = b.get("n_obs", 20)
        a_n = a.get("n_obs", 20)
        panel_tag = colored("PANEL", GREEN) if a.get("is_panel") else "anual"
        print(row(["n observaciones",
                   str(b_n),
                   f"{a_n} ({panel_tag})",
                   colored(f"+{a_n - b_n}", GREEN) if a_n > b_n else "igual"]))

        # Nº features
        b_nf = b.get("n_features")
        a_nf = a.get("n_features")
        print(row(["Nº variables",
                   str(b_nf) if b_nf is not None else "?",
                   str(a_nf) if a_nf is not None else "?",
                   delta_str(b_nf, a_nf, higher_better=False)]))

        # Variables usadas
        b_feats = b.get("features", [])
        a_feats = a.get("features", [])
        new_feats = set(a_feats) - set(b_feats)
        removed_feats = set(b_feats) - set(a_feats)
        if new_feats:
            print(f"    {colored('Nuevas variables:', GREEN)} {', '.join(sorted(new_feats))}")
        if removed_feats:
            print(f"    {colored('Eliminadas:', RED)} {', '.join(sorted(removed_feats))}")

        # R² LOOCV (mayor = mejor)
        b_r2 = b.get("r2_cv")
        a_r2 = a.get("r2_cv")
        print(row(["R² LOOCV",
                   f"{b_r2:.4f}" if b_r2 else "?",
                   f"{a_r2:.4f}" if a_r2 else "?",
                   delta_str(b_r2, a_r2, higher_better=True)]))

        # R² Spatial CV (si existe en el nuevo modelo)
        a_r2s = a.get("r2_spatial_cv")
        if a_r2s is not None:
            gap = (a_r2 - a_r2s) if a_r2 else None
            gap_str = (colored(f"LOOCV es {gap:+.4f} más optimista", YELLOW if gap > 0.05 else GREEN)
                       if gap is not None else "?")
            print(row(["R² Spatial CV (nuevo)",
                       "N/A (no existía)",
                       f"{a_r2s:.4f}",
                       gap_str]))

        # RMSE (menor = mejor)
        b_rmse = b.get("rmse_cv")
        a_rmse = a.get("rmse_cv")
        print(row(["RMSE µg/m³",
                   f"{b_rmse:.4f}" if b_rmse else "?",
                   f"{a_rmse:.4f}" if a_rmse else "?",
                   delta_str(b_rmse, a_rmse, higher_better=False)]))

        # Breusch-Pagan (tests sobre residuos LOOCV ahora, vs full-sample antes)
        b_bp = b.get("bp_pvalue")
        a_bp = a.get("bp_pvalue")
        b_bp_src = "(full-sample)" if b.get("r2_spatial_cv") is None else "(LOOCV)"
        a_bp_src = "(LOOCV)"
        bp_ok_b = "OK" if b_bp and b_bp > 0.05 else "FALLA" if b_bp else "?"
        bp_ok_a = "OK" if a_bp and a_bp > 0.05 else "FALLA" if a_bp else "?"
        print(row([f"BP p-value",
                   f"{b_bp:.4f} {b_bp_src}" if b_bp else "?",
                   f"{a_bp:.4f} {a_bp_src}" if a_bp else "?",
                   colored(f"{bp_ok_a}", GREEN if bp_ok_a == "OK" else RED)]))

        # Moran's I p-value
        b_mp = b.get("moran_p")
        a_mp = a.get("moran_p")
        mo_ok_b = "OK" if b_mp and b_mp > 0.05 else "FALLA" if b_mp else "?"
        mo_ok_a = "OK" if a_mp and a_mp > 0.05 else "FALLA" if a_mp else "?"
        print(row(["Moran's I p-value",
                   f"{b_mp:.4f}" if b_mp else "?",
                   f"{a_mp:.4f}" if a_mp else "?",
                   colored(f"{mo_ok_a}", GREEN if mo_ok_a == "OK" else RED)]))

    print(f"\n{'='*70}\n")


def save_comparison_report(before: dict, after: dict, scripts_run: list):
    """Escribe outputs/comparison_report.md con la comparación."""
    path = DOCS_DIR / "05_comparison_report.md"
    lines = [
        f"# Comparison Report — Mejoras LUR",
        f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## Scripts ejecutados",
        "",
    ]
    for s, ok in scripts_run:
        lines.append(f"- {'✓' if ok else '✗'} `{s}`")
    lines += ["", "## Métricas ANTES vs DESPUÉS", ""]

    for label in ["PM2.5", "PM10"]:
        b = before.get(label, {})
        a = after.get(label, {})
        b_r2   = b.get("r2_cv");    a_r2   = a.get("r2_cv")
        b_rmse = b.get("rmse_cv"); a_rmse = a.get("rmse_cv")
        d_r2   = f"{a_r2 - b_r2:+.4f}"    if (a_r2   and b_r2)   else "N/A"
        d_rmse = f"{a_rmse - b_rmse:+.4f}" if (a_rmse and b_rmse) else "N/A"
        feats_b = "`, `".join(b.get("features", []))
        feats_a = "`, `".join(a.get("features", []))
        lines += [
            f"### {label}",
            "",
            "| Métrica | ANTES | DESPUÉS | Δ |",
            "|---------|-------|---------|---|",
            f"| Modelo | {b.get('model_name','?')} | {a.get('model_name','?')} | — |",
            f"| Nº variables | {b.get('n_features','?')} | {a.get('n_features','?')} | {(a.get('n_features',0) or 0) - (b.get('n_features',0) or 0):+d} |",
            f"| R² LOOCV | {b_r2} | {a_r2} | {d_r2} |",
            f"| R² Spatial CV | N/A | {a.get('r2_spatial_cv','N/A')} | nuevo |",
            f"| RMSE µg/m³ | {b_rmse} | {a_rmse} | {d_rmse} |",
            f"| BP p-value¹ | {b.get('bp_pvalue','?')} | {a.get('bp_pvalue','?')} | — |",
            f"| Moran's I p | {b.get('moran_p','?')} | {a.get('moran_p','?')} | — |",
            "",
            f"**Variables ANTES:** `{feats_b}`",
            "",
            f"**Variables DESPUÉS:** `{feats_a}`",
            "",
        ]

    lines += [
        "---",
        "",
        "¹ BP = Breusch-Pagan. ANTES: calculado sobre residuos full-sample (sesgado). ",
        "DESPUÉS: calculado sobre residuos LOOCV (correcto, más conservador).",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"\n  Reporte de comparación guardado → {path}")
    return path


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(colored("\n" + "═"*60, BOLD))
    print(colored("  LUR PIPELINE — EJECUCIÓN CON MEJORAS", BOLD))
    print(colored("═"*60 + "\n", BOLD))

    # 1. Baseline
    baseline = capture_baseline()

    scripts_run = []

    # 2. Descargas externas opcionales
    log.info("\n── Fase Opcional: Descargas externas ─────────────────────────")
    for script, label in [
        (ROOT / "src/data/download_aurn.py",       "D1: DEFRA AURN"),
        (ROOT / "src/data/download_meteo.py",      "C1: Meteorología"),
        (ROOT / "src/data/download_elevation.py",  "C2: Elevación"),
        (ROOT / "src/data/download_population.py", "C4: Población"),
    ]:
        ok = run(script, label, optional=True)
        scripts_run.append((label, ok))

    # 3. Pipeline principal
    log.info("\n── Pipeline Principal ─────────────────────────────────────────")
    pipeline = [
        (ROOT / "src/data/process_sensors_1.py",         "B1: Sensores (panel mensual)"),
        (ROOT / "src/features/sensor_road_matching.py",  "Fase 2.5: Sensor snapping"),
        (ROOT / "src/features/integrate_aadf.py",        "Fase 3: Tráfico AADF"),
        (ROOT / "src/features/feature_engineering.py",   "Fase 4: Feature engineering (+fuentes puntuales)"),
        (ROOT / "src/models/lur_model.py",                "Fase 5-7: Modelo LUR (+ElasticNet, SpatialCV, Bootstrap)"),
        (ROOT / "src/models/task5_loocv_validation.py",  "Validación LOOCV (residuos corregidos)"),
        (ROOT / "src/visualization/predict_map.py",      "Fase 8: Mapa predictivo (+intervalos)"),
    ]

    all_ok = True
    for script, label in pipeline:
        ok = run(script, label, optional=False)
        scripts_run.append((label, ok))
        if not ok:
            all_ok = False
            log.error(f"  Pipeline detenido en: {label}")
            log.error("  Comprueba el error arriba e intenta ejecutar ese script solo.")
            break

    if not all_ok:
        log.warning("\n  Pipeline incompleto — comparando con lo que hay disponible")

    # 4. Cargar nuevas métricas
    log.info("\n── Cargando métricas nuevas ───────────────────────────────────")
    after = capture_baseline()   # misma función, ahora lee los pickles actualizados

    # 5. Comparación
    print_comparison(baseline, after)

    # 6. Guardar reporte
    report_path = save_comparison_report(baseline, after, scripts_run)
    print("  Reporte guardado en: " + str(report_path) + "\n")


if __name__ == "__main__":
    main()
