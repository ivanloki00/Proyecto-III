"""
ejecutar_todo.py — Runner completo del pipeline LUR / ST-LUR
=============================================================
Ejecuta, en orden, todos los scripts del repo para dejar datos, features,
modelos y visualizaciones al día en el entorno local.

Uso básico:
    python ejecutar_todo.py                 # ejecuta todo (descargas = opcionales)
    python ejecutar_todo.py --skip-downloads  # salta fase 0 (descargas/OSM)
    python ejecutar_todo.py --from 2          # empieza en la fase 2
    python ejecutar_todo.py --only 3          # solo ejecuta la fase 3
    python ejecutar_todo.py --list            # lista todas las fases y pasos

Convenciones:
  - Cada paso se marca como obligatorio u opcional. Los opcionales no detienen
    el pipeline si fallan (ideal para descargas externas).
  - Se mantiene el mismo intérprete que invoca este script (sys.executable),
    por lo que respeta el venv activo.
  - Salida en tiempo real; al final se imprime un resumen OK/FAIL.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# UTF-8 en consolas Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ejecutar_todo")

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

# Colores ANSI (se desactivan si no hay TTY)
_USE_COLOR = sys.stdout.isatty()
def c(text: str, color: str) -> str:
    if not _USE_COLOR:
        return text
    codes = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
             "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m"}
    return f"{codes.get(color, '')}{text}{codes['reset']}"


# ── DEFINICIÓN DEL PIPELINE ──────────────────────────────────────────────────
@dataclass
class Step:
    label: str
    script: Path
    optional: bool = False


@dataclass
class Stage:
    num: int
    name: str
    steps: list[Step] = field(default_factory=list)


STAGES: list[Stage] = [
    Stage(0, "Extracción de capas externas (OSM + descargas)", [
        Step("OSM layers (streets, landuse, buildings)", ROOT / "src/data/extract_osm_features.py", optional=True),
        Step("DEFRA AURN reference stations",             ROOT / "src/data/download_aurn.py",       optional=True),
        Step("Meteorología Open-Meteo",                   ROOT / "src/data/download_meteo.py",      optional=True),
        Step("Elevación (DEM)",                           ROOT / "src/data/download_elevation.py",  optional=True),
        Step("Población (Census LSOA)",                   ROOT / "src/data/download_population.py", optional=True),
    ]),
    Stage(1, "Construcción de paneles de datos", [
        Step("Panel histórico mensual 2021-2025",   ROOT / "src/data/build_full_panel.py",        optional=True),
        Step("Integración de externos locales",     ROOT / "src/data/integrate_external_data.py", optional=True),
        Step("Procesado sensores (panel mensual)",  ROOT / "src/data/process_sensors_1.py",       optional=False),
    ]),
    Stage(2, "Features espaciales y de tráfico", [
        Step("Sensor snapping a calles",            ROOT / "src/features/sensor_road_matching.py",     optional=False),
        Step("Integración tráfico AADF",            ROOT / "src/features/integrate_aadf.py",           optional=False),
        Step("Traffic-Weighted Exposure",           ROOT / "src/features/traffic_weighted_exposure.py", optional=True),
        Step("Feature engineering LUR",             ROOT / "src/features/feature_engineering.py",      optional=False),
    ]),
    Stage(3, "Modelos LUR (espaciales)", [
        Step("Feature selection report",            ROOT / "src/models/feature_selection_report.py", optional=True),
        Step("LUR principal (+ElasticNet/SpatialCV/Bootstrap)", ROOT / "src/models/lur_model.py", optional=False),
        Step("Validación LOOCV",                    ROOT / "src/models/task5_loocv_validation.py",   optional=False),
        Step("Modelo LUR a nivel LSOA",             ROOT / "src/models/lur_lsoa_model.py",           optional=True),
    ]),
    Stage(4, "Modelos ST-LUR (espaciotemporales)", [
        Step("Reentrenamiento ST-LUR (panel histórico)", ROOT / "src/models/stlur_retrain.py",  optional=True),
        Step("Forecast ST-LUR",                          ROOT / "src/models/stlur_forecast.py", optional=True),
    ]),
    Stage(5, "Diagnóstico y visualización", [
        Step("Diagnósticos y entregables (task 7)", ROOT / "src/models/task7_diagnostics_deliverables.py", optional=True),
        Step("Mapa predictivo con intervalos",      ROOT / "src/visualization/predict_map.py",             optional=False),
        Step("Mapa urbano (plotearmapa)",           ROOT / "src/visualization/plotearmapa.py",             optional=True),
    ]),
]


# ── EJECUCIÓN ────────────────────────────────────────────────────────────────
def run_step(step: Step) -> tuple[bool, float]:
    """Ejecuta un paso. Devuelve (ok, elapsed_sec)."""
    t0 = time.time()
    if not step.script.exists():
        log.warning(f"  [{'opt' if step.optional else 'obl'}] Script no encontrado: {step.script.relative_to(ROOT)}")
        return (True if step.optional else False, 0.0)

    print()
    print(c("─" * 72, "cyan"))
    print(c(f"  ▶ {step.label}", "bold"))
    print(f"    {step.script.relative_to(ROOT)}  {'(opcional)' if step.optional else ''}")
    print(c("─" * 72, "cyan"))

    rc = subprocess.run([PYTHON, str(step.script)], cwd=str(ROOT)).returncode
    elapsed = time.time() - t0

    if rc == 0:
        print(c(f"  ✓ OK  ({elapsed:.1f}s)", "green"))
        return True, elapsed
    if step.optional:
        print(c(f"  ⚠ FALLO opcional (rc={rc}, {elapsed:.1f}s) — continuando", "yellow"))
        return True, elapsed
    print(c(f"  ✗ FALLO obligatorio (rc={rc}, {elapsed:.1f}s)", "red"))
    return False, elapsed


def run_stage(stage: Stage, stop_on_error: bool) -> list[tuple[Step, bool, float]]:
    print()
    print(c("═" * 72, "bold"))
    print(c(f"  FASE {stage.num} — {stage.name}", "bold"))
    print(c("═" * 72, "bold"))
    results: list[tuple[Step, bool, float]] = []
    for step in stage.steps:
        ok, elapsed = run_step(step)
        results.append((step, ok, elapsed))
        if not ok and stop_on_error:
            log.error(f"Pipeline detenido en la fase {stage.num}: {step.label}")
            break
    return results


def print_summary(all_results: list[tuple[int, Step, bool, float]]):
    print()
    print(c("═" * 72, "bold"))
    print(c("  RESUMEN", "bold"))
    print(c("═" * 72, "bold"))
    total_t = sum(r[3] for r in all_results)
    n_ok = sum(1 for r in all_results if r[2])
    n_fail = len(all_results) - n_ok
    for stage_num, step, ok, elapsed in all_results:
        mark = c("✓", "green") if ok else c("✗", "red")
        opt = " (opt)" if step.optional else ""
        print(f"  F{stage_num}  {mark}  {step.label:<55s}{opt:<7s} {elapsed:6.1f}s")
    print(c("─" * 72, "cyan"))
    color = "green" if n_fail == 0 else "red"
    print(c(f"  Total: {n_ok} OK / {n_fail} FAIL   ·   {total_t/60:.1f} min", color))
    print()


def list_stages():
    print(c("Pipeline completo:", "bold"))
    for stage in STAGES:
        print(c(f"\n  Fase {stage.num} — {stage.name}", "cyan"))
        for step in stage.steps:
            tag = "opt" if step.optional else "obl"
            print(f"    [{tag}] {step.label}   ({step.script.relative_to(ROOT)})")
    print()


# ── CLI ──────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Ejecutar el pipeline completo del proyecto LUR Liverpool.")
    p.add_argument("--from", dest="from_stage", type=int, default=0,
                   help="Fase inicial (por defecto 0 = desde el principio).")
    p.add_argument("--to", dest="to_stage", type=int, default=max(s.num for s in STAGES),
                   help="Fase final inclusive.")
    p.add_argument("--only", dest="only_stage", type=int, default=None,
                   help="Ejecuta únicamente la fase indicada.")
    p.add_argument("--skip-downloads", action="store_true",
                   help="Salta la fase 0 (descargas externas + OSM).")
    p.add_argument("--continue-on-error", action="store_true",
                   help="Continúa aunque falle un paso obligatorio.")
    p.add_argument("--list", action="store_true",
                   help="Lista las fases y pasos y sale.")
    return p.parse_args()


def main():
    args = parse_args()

    if args.list:
        list_stages()
        return 0

    if args.only_stage is not None:
        selected = [s for s in STAGES if s.num == args.only_stage]
    else:
        lo, hi = args.from_stage, args.to_stage
        if args.skip_downloads:
            lo = max(lo, 1)
        selected = [s for s in STAGES if lo <= s.num <= hi]

    if not selected:
        log.error("No hay fases seleccionadas con los filtros dados.")
        return 2

    print(c("\n" + "═" * 72, "bold"))
    print(c("  EJECUTAR TODO — PIPELINE LUR LIVERPOOL", "bold"))
    print(c(f"  Fases: {[s.num for s in selected]}   ·   Python: {PYTHON}", "cyan"))
    print(c("═" * 72 + "\n", "bold"))

    stop_on_error = not args.continue_on_error
    all_results: list[tuple[int, Step, bool, float]] = []
    t_pipe = time.time()

    for stage in selected:
        results = run_stage(stage, stop_on_error)
        all_results.extend((stage.num, s, ok, e) for s, ok, e in results)

        # Si falló un obligatorio y no continuamos, cortamos todo el pipeline.
        if stop_on_error and any(not ok for _, ok, _ in results):
            break

    log.info(f"Pipeline terminado en {(time.time() - t_pipe)/60:.1f} min")
    print_summary(all_results)

    # Código de salida: 0 si todo OK, 1 si algún obligatorio falló
    return 0 if all(ok for _, _, ok, _ in all_results) else 1


if __name__ == "__main__":
    sys.exit(main())
