"""
Task 7 — Gráficos de Diagnóstico y Entregables Finales
PROYIII Liverpool Air Quality LUR
Fecha: 2026-04-10
"""

# CONFIG
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import scipy.stats as stats
import geopandas as gpd
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ROOT discovery
def find_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "outputs").exists() and (p / "data").exists():
            return p
    raise RuntimeError("No se encontró el directorio ROOT del proyecto.")

ROOT = find_root()
FIGURES_DIR = ROOT / "outputs" / "LUR" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR = ROOT / "outputs" / "LUR"

# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

TARGETS = ["PM2.5", "PM10"]
TARGET_KEYS = {"PM2.5": "PM25", "PM10": "PM10"}

STYLE = {
    "PM2.5": {"color": "#D94F3D", "cmap": "Reds"},
    "PM10":  {"color": "#3D6FD9", "cmap": "Blues"},
}

# Etiquetas en español para los ejes
XLABEL_OBS  = "Observado (µg/m³)"
XLABEL_PRED = "Predicho (µg/m³)"
XLABEL_RES  = "Residuo (µg/m³)"
YLABEL_RES  = "Residuo (µg/m³)"

def save_fig(fig: plt.Figure, path: Path, dpi: int = 150) -> None:
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    log.info("Guardado: %s", path)


def load_loocv() -> pd.DataFrame:
    p = OUTPUTS_DIR / "loocv_results.csv"
    df = pd.read_csv(p)
    log.info("LOOCV cargado: %d filas, columnas=%s", len(df), list(df.columns))
    return df


def load_model(target_key: str) -> dict:
    p = OUTPUTS_DIR / f"lur_model_{target_key}.pkl"
    m = joblib.load(p)
    log.info("Modelo cargado: %s (features=%s)", target_key, m["features"])
    return m


def load_features_wide() -> pd.DataFrame:
    """Construye tabla wide de features para cada sensor, por buffer elegido."""
    feat_long = pd.read_csv(ROOT / "data/interim/lur_features.csv")
    # Buffer seleccionado por variable: basado en feature_selection_report
    # PM2.5 → road_length_residential_m_500m, landuse_industrial_ratio_250m,
    #           landuse_green_ratio_100m, dist_industrial_m_50m
    # PM10  → road_length_residential_m_500m, landuse_green_ratio_100m, dist_industrial_m_50m
    # Variables requeridas con su buffer
    needed = {
        "road_length_residential_m_500m": ("road_length_residential_m", 500),
        "landuse_industrial_ratio_250m":  ("landuse_industrial_ratio",  250),
        "landuse_green_ratio_100m":       ("landuse_green_ratio",       100),
        "dist_industrial_m_50m":          ("dist_industrial_m",          50),
    }
    sensors = feat_long["sensor_id"].unique()
    rows = []
    for sid in sensors:
        row = {"sensor_id": sid}
        sub = feat_long[feat_long["sensor_id"] == sid]
        pm25 = sub["PM2.5"].iloc[0]
        pm10 = sub["PM10"].iloc[0]
        row["PM2.5"] = pm25
        row["PM10"]  = pm10
        for col_name, (base_col, buf) in needed.items():
            vals = sub[sub["buffer_m"] == buf][base_col]
            row[col_name] = vals.iloc[0] if len(vals) > 0 else np.nan
        rows.append(row)
    wide = pd.DataFrame(rows)
    log.info("Features wide: %s", wide.shape)
    return wide


def normalize_coefs(features: list, coef: np.ndarray, X: pd.DataFrame) -> pd.DataFrame:
    """Coeficientes Ridge normalizados (β * std_X / std_y para comparación)."""
    stds = X[features].std()
    norm = np.abs(coef * stds.values)
    df = pd.DataFrame({"variable": features, "importancia": norm})
    df = df.sort_values("importancia", ascending=True).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# TAREA 1: Gráficos de diagnóstico individuales
# ─────────────────────────────────────────────────────────────────────────────

def plot_obs_vs_pred(loocv: pd.DataFrame, target: str, target_key: str) -> Path:
    """Dispersión Observado vs Predicho con línea 1:1 y R²."""
    obs  = loocv[f"observed_{target_key.lower()}"]
    pred = loocv[f"predicted_{target_key.lower()}"]
    r2   = 1 - np.sum((obs - pred) ** 2) / np.sum((obs - obs.mean()) ** 2)

    fig, ax = plt.subplots(figsize=(5.5, 5))
    color = STYLE[target]["color"]
    ax.scatter(obs, pred, color=color, alpha=0.75, edgecolors="white",
               linewidths=0.5, s=60, zorder=3)

    lims = [min(obs.min(), pred.min()) * 0.95, max(obs.max(), pred.max()) * 1.05]
    ax.plot(lims, lims, "k--", linewidth=1.2, label="Línea 1:1", zorder=2)
    ax.set_xlim(lims); ax.set_ylim(lims)

    ax.set_xlabel(XLABEL_OBS, fontsize=11)
    ax.set_ylabel(XLABEL_PRED, fontsize=11)
    ax.set_title(f"{target} — Observado vs Predicho (LOOCV)\nR²={r2:.3f}", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    out = FIGURES_DIR / f"obs_vs_pred_{target_key}.png"
    save_fig(fig, out)
    return out


def plot_residuos_vs_pred(loocv: pd.DataFrame, target: str, target_key: str) -> Path:
    """Residuos vs Predicho."""
    pred = loocv[f"predicted_{target_key.lower()}"]
    res  = loocv[f"residual_{target_key.lower()}"]

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    color = STYLE[target]["color"]
    ax.scatter(pred, res, color=color, alpha=0.75, edgecolors="white",
               linewidths=0.5, s=60, zorder=3)
    ax.axhline(0, color="black", linewidth=1.2, linestyle="--")
    ax.set_xlabel(XLABEL_PRED, fontsize=11)
    ax.set_ylabel(YLABEL_RES, fontsize=11)
    ax.set_title(f"{target} — Residuos vs Predicho (LOOCV)", fontsize=12)
    ax.grid(True, alpha=0.3)

    out = FIGURES_DIR / f"residuos_vs_pred_{target_key}.png"
    save_fig(fig, out)
    return out


def plot_histograma_residuos(loocv: pd.DataFrame, target: str, target_key: str) -> Path:
    """Histograma de residuos con curva de densidad normal."""
    res = loocv[f"residual_{target_key.lower()}"]

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    color = STYLE[target]["color"]
    ax.hist(res, bins=8, color=color, alpha=0.7, edgecolor="white",
            density=True, label="Residuos")

    x = np.linspace(res.min() - 1, res.max() + 1, 200)
    ax.plot(x, stats.norm.pdf(x, res.mean(), res.std()),
            "k-", linewidth=1.5, label="Normal ajustada")
    ax.set_xlabel(XLABEL_RES, fontsize=11)
    ax.set_ylabel("Densidad", fontsize=11)
    ax.set_title(f"{target} — Histograma de Residuos (LOOCV)", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    out = FIGURES_DIR / f"hist_residuos_{target_key}.png"
    save_fig(fig, out)
    return out


def plot_qq_residuos(loocv: pd.DataFrame, target: str, target_key: str) -> Path:
    """Q-Q plot de residuos vs distribución normal."""
    res = loocv[f"residual_{target_key.lower()}"]

    fig, ax = plt.subplots(figsize=(5, 5))
    (quantiles, values), (slope, intercept, r) = stats.probplot(res, dist="norm")
    color = STYLE[target]["color"]
    ax.scatter(quantiles, values, color=color, alpha=0.75,
               edgecolors="white", linewidths=0.5, s=60, zorder=3)
    x_line = np.array([quantiles.min(), quantiles.max()])
    ax.plot(x_line, slope * x_line + intercept,
            "k--", linewidth=1.2, label=f"R={r:.3f}")
    ax.set_xlabel("Cuantiles teóricos (Normal)", fontsize=11)
    ax.set_ylabel("Cuantiles muestrales", fontsize=11)
    ax.set_title(f"{target} — Q-Q Plot de Residuos (LOOCV)", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    out = FIGURES_DIR / f"qq_residuos_{target_key}.png"
    save_fig(fig, out)
    return out


def plot_importancia_variables(model_dict: dict, wide: pd.DataFrame,
                                target: str, target_key: str) -> Path:
    """Barras horizontales: importancia normalizada (|coef| * std_X)."""
    features = model_dict["features"]
    coef     = model_dict["model"].coef_
    y_vals   = wide[target]
    imp_df   = normalize_coefs(features, coef, wide)

    # Etiquetas más legibles
    label_map = {
        "road_length_residential_m_500m": "Long. vías residenciales\n(buffer 500m)",
        "landuse_industrial_ratio_250m":  "Proporción suelo industrial\n(buffer 250m)",
        "landuse_green_ratio_100m":       "Proporción espacios verdes\n(buffer 100m)",
        "dist_industrial_m_50m":          "Distancia a zona industrial\n(buffer 50m)",
    }
    imp_df["label"] = imp_df["variable"].map(label_map).fillna(imp_df["variable"])

    fig, ax = plt.subplots(figsize=(7, max(3.5, len(imp_df) * 0.9 + 0.5)))
    color = STYLE[target]["color"]
    bars = ax.barh(imp_df["label"], imp_df["importancia"],
                   color=color, alpha=0.8, edgecolor="white")
    ax.set_xlabel("|Coeficiente Ridge| × Desv. Est. de la variable", fontsize=10)
    ax.set_title(f"{target} — Importancia Normalizada de Variables\n(proxy Ridge)", fontsize=12)
    ax.grid(True, axis="x", alpha=0.3)

    # Valores en las barras
    for bar, val in zip(bars, imp_df["importancia"]):
        ax.text(bar.get_width() + imp_df["importancia"].max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", fontsize=9)

    plt.tight_layout()
    out = FIGURES_DIR / f"importancia_variables_{target_key}.png"
    save_fig(fig, out)
    return out


def plot_mapa_residuos(loocv: pd.DataFrame, target: str, target_key: str) -> Path:
    """Mapa de residuos espaciales usando coordenadas de sensores_snapped."""
    snapped_path = ROOT / "data/interim/sensores_snapped.gpkg"
    snapped = gpd.read_file(snapped_path).to_crs("EPSG:4326")

    # Unir con residuos
    res_col = f"residual_{target_key.lower()}"
    df_res = loocv[["sensor_id", res_col]].copy()
    gdf = snapped.merge(df_res, on="sensor_id", how="inner")

    if gdf.empty:
        log.warning("No se pudo unir residuos con sensores para %s", target)
        return None

    fig, ax = plt.subplots(figsize=(8, 7))

    # Obtener geometría de la red vial para contexto visual mínimo
    try:
        streets_gdf = gpd.read_file(ROOT / "data/interim/streets_with_traffic.gpkg").to_crs("EPSG:4326")
        streets_gdf.plot(ax=ax, color="#cccccc", linewidth=0.4, alpha=0.5, zorder=1)
    except Exception as e:
        log.warning("No se pudo cargar streets_with_traffic.gpkg: %s", e)

    vmax = max(abs(gdf[res_col].min()), abs(gdf[res_col].max()))
    sc = ax.scatter(
        gdf.geometry.x, gdf.geometry.y,
        c=gdf[res_col], cmap="RdBu_r",
        vmin=-vmax, vmax=vmax,
        s=120, edgecolors="black", linewidths=0.5, zorder=3
    )
    cbar = fig.colorbar(sc, ax=ax, shrink=0.7, label="Residuo (µg/m³)")
    ax.set_title(f"{target} — Mapa de Residuos Espaciales (LOOCV)", fontsize=12)
    ax.set_xlabel("Longitud", fontsize=10)
    ax.set_ylabel("Latitud", fontsize=10)
    ax.grid(True, alpha=0.2)

    out = FIGURES_DIR / f"mapa_residuos_{target_key}.png"
    save_fig(fig, out)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# TAREA 2: Mapas de polución (verificar si ya existen y son recientes)
# ─────────────────────────────────────────────────────────────────────────────

def check_maps_exist() -> bool:
    """Retorna True si ambos mapas existen y pesan > 100 KB (se consideran válidos)."""
    for t in ["PM25", "PM10"]:
        p = OUTPUTS_DIR / f"map_{t}.png"
        if not p.exists() or p.stat().st_size < 100_000:
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# TAREA 3: Resumen ejecutivo
# ─────────────────────────────────────────────────────────────────────────────

SUMMARY_TEMPLATE = """# Resumen Ejecutivo — Modelo LUR Liverpool Air Quality
**Proyecto:** PROYIII — Predicción de Contaminación Atmosférica en Liverpool
**Fecha:** 2026-04-10
**Protocolo de validación:** Leave-One-Out Cross-Validation (LOOCV), n = 20 sensores
**Modelo ganador:** Ridge Regression (RidgeCV, α seleccionado por CV)

---

## 1. Variables Finales por Modelo

### PM2.5 — 4 predictores (escenario p < 0.10, VIF ≤ 5)

| Variable | Buffer | |r| | p-valor | VIF |
|---|---|---|---|---|
| `road_length_residential_m` | 500 m | 0.557 | 0.011 | 1.93 |
| `landuse_industrial_ratio`  | 250 m | 0.392 | 0.087 | 1.07 |
| `landuse_green_ratio`       | 100 m | 0.731 | 0.0002 | 1.53 |
| `dist_industrial_m`         |  50 m | 0.550 | 0.012 | 2.24 |

### PM10 — 3 predictores (escenario p < 0.10, VIF ≤ 5)

| Variable | Buffer | |r| | p-valor | VIF |
|---|---|---|---|---|
| `road_length_residential_m` | 500 m | 0.514 | 0.020 | 1.81 |
| `landuse_green_ratio`       | 100 m | 0.722 | 0.0003 | 1.53 |
| `dist_industrial_m`         |  50 m | 0.553 | 0.011 | 2.19 |

---

## 2. Métricas LOOCV

| Métrica | PM2.5 | PM10 |
|---|---|---|
| R² (LOOCV) | **0.5858** | **0.4159** |
| RMSE (µg/m³) | 1.839 | 3.933 |
| MAE (µg/m³) | 1.510 | 3.215 |
| MAPE (%) | 21.05 | 20.49 |
| Outliers (|res| > 2×RMSE) | 0 | 0 |

> Nota: el modelo PM10 almacenado tiene R²=0.5034 (full-sample CV durante selección de modelo),
> mientras que el LOOCV estricto sobre las 4 variables finales reporta R²=0.4159.
> Se usa el LOOCV estricto como métrica de validación definitiva.

---

## 3. Tests Estadísticos de Supuestos (residuos full-sample)

| Test | PM2.5 | PM10 | Resultado |
|---|---|---|---|
| Breusch-Pagan (homocedasticidad) | p = 0.185 | p = 0.535 | OK — no se rechaza homocedasticidad |
| Shapiro-Wilk (normalidad residuos) | p = 0.840 | p = 0.919 | OK — residuos normales |
| Moran's I (autocorr. espacial) | p = 0.667 | p = 0.310 | OK — sin estructura espacial residual |
| Durbin-Watson (autocorr. serial) | 2.647 | 2.194 | Aceptable (rango 1.5–2.5; PM2.5 marginal) |

---

## 4. Comparación de Modelos (selección Task 4)

| Target | Modelo | R² (CV) | RMSE (µg/m³) |
|---|---|---|---|
| PM2.5 | **Ridge** ← ganador | **0.5858** | **1.839** |
| PM2.5 | LinearRegression | 0.5079 | 2.005 |
| PM2.5 | RandomForest | 0.2769 | 2.430 |
| PM2.5 | GradientBoosting | 0.2662 | 2.448 |
| PM10 | **Ridge** ← ganador | **0.5034** | **3.626** |
| PM10 | LinearRegression | 0.4486 | 3.821 |
| PM10 | RandomForest | 0.3809 | 4.049 |
| PM10 | GradientBoosting | 0.2616 | 4.422 |

---

## 5. Clasificación de Robustez

| Contaminante | R² LOOCV | Clasificación |
|---|---|---|
| PM2.5 | 0.5858 | **Aceptable con limitaciones** (0.4 ≤ R² < 0.6) |
| PM10  | 0.4159 | **Aceptable con limitaciones** (0.4 ≤ R² < 0.6) |

Ambos modelos son apropiados para describir patrones espaciales relativos
(zonas de alta/baja contaminación), pero **no** para predicciones absolutas
en ubicaciones sin validar.

---

## 6. Limitaciones del Modelo

- **n = 20 sensores:** tamaño muestral pequeño. LOOCV con n pequeño tiene
  tendencia a ser optimista en varianza; los intervalos de confianza de R²
  son amplios.
- **Cobertura AADF = 19.8%:** solo el 19.8% de los tramos viarios dispone de
  datos de tráfico AADF, lo que reduce la capacidad explicativa del tráfico
  como predictor. La variable AADF fue eliminada por p > 0.10 en ambos modelos.
- **Ausencia de variables meteorológicas:** viento, temperatura y humedad
  modulan la concentración de PM pero no están disponibles a nivel de sensor.
- **Extrapolación temporal:** el modelo se entrenó sobre medias anuales 2024.
  No es directamente aplicable a predicciones horarias o estacionales.
- **Fuentes episódicas no capturadas:** quemas, tráfico pesado puntual,
  polvo de construcción no están representados por las 4 variables seleccionadas.
- **Durbin-Watson PM2.5 = 2.647:** ligeramente fuera del rango 1.5–2.5,
  sugiere posible correlación serial negativa (no espacial, dado Moran's I OK).
  Se considera marginal dado el orden arbitrario de los sensores.

---

## 7. Artefactos Producidos

### Modelos serializados
| Archivo | Contenido |
|---|---|
| `outputs/lur_model_PM25.pkl` | Modelo Ridge PM2.5 (RidgeCV, α=0.01) |
| `outputs/lur_model_PM10.pkl` | Modelo Ridge PM10 (RidgeCV, α=0.01) |

### Predicciones y mapas
| Archivo | Contenido |
|---|---|
| `outputs/loocv_results.csv` | Predicciones LOOCV por sensor (ambos targets) |
| `outputs/liverpool_pollution_map.geojson` | 8 450 tramos viarios con PM2.5 y PM10 predichos |
| `outputs/map_PM25.png` | Mapa de polución PM2.5 (colormap Inferno) |
| `outputs/map_PM10.png` | Mapa de polución PM10 (colormap Inferno) |

### Gráficos de diagnóstico (`outputs/figures/`)
| Archivo | Descripción |
|---|---|
| `obs_vs_pred_PM25.png` | Dispersión obs vs pred PM2.5 (LOOCV) |
| `obs_vs_pred_PM10.png` | Dispersión obs vs pred PM10 (LOOCV) |
| `residuos_vs_pred_PM25.png` | Residuos vs predicho PM2.5 |
| `residuos_vs_pred_PM10.png` | Residuos vs predicho PM10 |
| `hist_residuos_PM25.png` | Histograma de residuos PM2.5 |
| `hist_residuos_PM10.png` | Histograma de residuos PM10 |
| `qq_residuos_PM25.png` | Q-Q plot residuos PM2.5 |
| `qq_residuos_PM10.png` | Q-Q plot residuos PM10 |
| `importancia_variables_PM25.png` | Importancia normalizada PM2.5 |
| `importancia_variables_PM10.png` | Importancia normalizada PM10 |
| `mapa_residuos_PM25.png` | Mapa espacial de residuos PM2.5 |
| `mapa_residuos_PM10.png` | Mapa espacial de residuos PM10 |

### Reportes
| Archivo | Contenido |
|---|---|
| `outputs/feature_selection_report.md` | Selección de variables (correlaciones, VIF) |
| `outputs/validation_report.md` | Reporte LOOCV + tests estadísticos |
| `outputs/model_comparison.csv` | Comparación de 4 modelos × 2 targets |
| `outputs/model_summary.md` | Este resumen ejecutivo |

---
_Generado automáticamente por `src/analysis/task7_diagnostics_deliverables.py`_
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Task 7 — Gráficos de Diagnóstico y Entregables Finales ===")
    log.info("ROOT: %s", ROOT)

    produced = []

    # ── Cargar datos ──────────────────────────────────────────────────────────
    loocv = load_loocv()
    wide  = load_features_wide()

    # ── Tarea 1: Gráficos de diagnóstico ─────────────────────────────────────
    for target, target_key in TARGET_KEYS.items():
        model_dict = load_model(target_key)
        log.info("--- Diagnósticos %s ---", target)

        # a. Observado vs Predicho
        p = plot_obs_vs_pred(loocv, target, target_key)
        produced.append((p, f"Dispersión obs vs pred {target} (LOOCV, R²)"))

        # b. Residuos vs Predicho
        p = plot_residuos_vs_pred(loocv, target, target_key)
        produced.append((p, f"Residuos vs predicho {target}"))

        # c. Histograma de residuos
        p = plot_histograma_residuos(loocv, target, target_key)
        produced.append((p, f"Histograma de residuos {target}"))

        # d. Q-Q plot
        p = plot_qq_residuos(loocv, target, target_key)
        produced.append((p, f"Q-Q plot residuos {target}"))

        # e. Importancia de variables
        p = plot_importancia_variables(model_dict, wide, target, target_key)
        produced.append((p, f"Importancia normalizada de variables {target}"))

        # f. Mapa de residuos espaciales
        p = plot_mapa_residuos(loocv, target, target_key)
        if p:
            produced.append((p, f"Mapa espacial de residuos {target}"))

    # ── Tarea 2: Mapas de polución ────────────────────────────────────────────
    if check_maps_exist():
        log.info("Mapas de polución ya existen y son válidos — omitiendo regeneración.")
        for t in ["PM25", "PM10"]:
            p = OUTPUTS_DIR / f"map_{t}.png"
            produced.append((p, f"Mapa de polución {t} (preexistente, válido)"))
    else:
        log.warning("Mapas de polución no encontrados o insuficientes — ejecutar plotearmapa.py manualmente.")

    # ── Tarea 3: Resumen ejecutivo ────────────────────────────────────────────
    summary_path = OUTPUTS_DIR / "model_summary.md"
    summary_path.write_text(SUMMARY_TEMPLATE, encoding="utf-8")
    log.info("Guardado: %s", summary_path)
    produced.append((summary_path, "Resumen ejecutivo del modelo LUR"))

    # ── Verificación de archivos ──────────────────────────────────────────────
    log.info("=== Verificación de archivos producidos ===")
    all_ok = True
    for path, desc in produced:
        path = Path(path)
        exists = path.exists()
        size   = path.stat().st_size if exists else 0
        status = "OK" if exists and size > 0 else "FALLO"
        if status == "FALLO":
            all_ok = False
        log.info("[%s] %s — %s (%d bytes)", status, desc, path.name, size)

    if all_ok:
        log.info("=== Task 7 completada sin errores ===")
    else:
        log.error("=== Task 7 completada con errores — revisar archivos marcados FALLO ===")
        sys.exit(1)

    return produced


if __name__ == "__main__":
    main()
