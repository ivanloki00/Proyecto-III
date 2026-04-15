"""
Task 5 — Validación Cruzada LOOCV completa
============================================
Ridge Regression (modelo ganador Task 4) para PM2.5 y PM10.

Produce:
  outputs/loocv_results.csv
  outputs/validation_report.md
  outputs/figures/loocv_obs_vs_pred.png

Variables ganadoras (Task 4):
  PM2.5 : road_length_residential_m_500m, landuse_industrial_ratio_250m,
           landuse_green_ratio_100m, dist_industrial_m_50m
  PM10  : road_length_residential_m_500m, landuse_green_ratio_100m,
           dist_industrial_m_50m, landuse_industrial_ratio_50m
"""

# ── CONFIG ───────────────────────────────────────────────────────────────────
from pathlib import Path
import logging
import warnings
import pickle

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import RidgeCV
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_squared_error

import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from scipy.stats import shapiro, norm
from scipy.spatial.distance import squareform, pdist

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

ROOT        = Path(__file__).resolve().parents[2]
DATA_INT    = ROOT / "data" / "interim"
OUT_DIR  = ROOT / "data" / "processed" / "LUR"              # CSVs de resultados
FIG_DIR  = ROOT / "outputs" / "figures" / "lur"  # imágenes
DOCS_DIR = ROOT / "docs"                          # reportes markdown
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_CSV = DATA_INT / "lur_features.csv"
SENSORS_GPKG = DATA_INT / "sensores_snapped.gpkg"

RIDGE_ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0]

# Variables ganadoras Task 4 — formato: {var_base}_{buffer}m
WINNER_FEATURES = {
    "PM2.5": [
        "road_length_residential_m_500m",
        "landuse_industrial_ratio_250m",
        "landuse_green_ratio_100m",
        "dist_industrial_m_50m",
    ],
    "PM10": [
        "road_length_residential_m_500m",
        "landuse_green_ratio_100m",
        "dist_industrial_m_50m",
        "landuse_industrial_ratio_50m",
    ],
}

# Variable → nombre base en CSV y buffer
def _parse_feature(feat: str):
    """'road_length_residential_m_500m' → (base, buffer_int)."""
    # buffer suffix always like _<N>m at the end
    parts = feat.rsplit("_", 2)
    # e.g. ['road_length_residential_m', '500', 'm'] but last part is 'm'
    # so feat ends with e.g. '_500m'
    # split on last '_' twice: first gives 'm', second gives buffer number
    no_m = feat[:-1]          # strip trailing 'm'
    idx  = no_m.rfind("_")
    buf  = int(no_m[idx+1:])  # buffer radius as int
    base = feat[:idx]         # base variable name as in CSV (without _<N>m suffix)
    # The base variable in the CSV has an '_m' ending for dist_industrial_m
    # so base = 'dist_industrial_m' → look for column 'dist_industrial_m'
    return base, buf


# ── UTILIDADES ───────────────────────────────────────────────────────────────

def build_design_matrix(df_all: pd.DataFrame, target: str) -> pd.DataFrame:
    """
    Pivota el CSV long (sensor × buffer) al vector de features ganadores para `target`.
    Devuelve DataFrame indexado por sensor_id con columnas = features + target.
    """
    feature_list = WINNER_FEATURES[target]
    sensors = df_all["sensor_id"].unique()
    rows = []
    for sid in sensors:
        rec = {"sensor_id": sid}
        # target value is same across buffers
        sid_rows = df_all[df_all["sensor_id"] == sid]
        rec[target] = sid_rows[target].iloc[0]
        for feat in feature_list:
            base, buf = _parse_feature(feat)
            buf_row = sid_rows[sid_rows["buffer_m"] == buf]
            if buf_row.empty or base not in buf_row.columns:
                log.warning(f"  Falta {feat} para sensor {sid}")
                rec[feat] = np.nan
            else:
                rec[feat] = buf_row[base].iloc[0]
        rows.append(rec)
    result = pd.DataFrame(rows).set_index("sensor_id")
    result = result.replace([np.inf, -np.inf], np.nan)
    # CORRECCIÓN A3: distancias NaN → centinela, no 0
    dist_cols = [c for c in result.columns if c.startswith("dist_")]
    for dc in dist_cols:
        max_val = result[dc].max()
        fill_val = max_val * 1.5 if (pd.notna(max_val) and max_val > 0) else 9999.0
        result[dc] = result[dc].fillna(fill_val)
    result = result.fillna(0)
    return result


def run_loocv(X: np.ndarray, y: np.ndarray) -> dict:
    """LOOCV con RidgeCV. Devuelve predicciones por fold y métricas agregadas."""
    loo    = LeaveOneOut()
    y_pred = np.zeros(len(y), dtype=float)

    for train_idx, test_idx in loo.split(X):
        m = RidgeCV(alphas=RIDGE_ALPHAS, cv=None)
        m.fit(X[train_idx], y[train_idx])
        y_pred[test_idx] = m.predict(X[test_idx])

    residuals = y - y_pred
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
    mae  = float(np.mean(np.abs(residuals)))
    r2   = float(r2_score(y, y_pred))
    # MAPE — guard against zero observations
    mape_vals = np.abs(residuals / np.where(y == 0, np.nan, y))
    mape = float(np.nanmean(mape_vals)) * 100

    return {
        "y_pred":     y_pred,
        "residuals":  residuals,
        "r2":         r2,
        "rmse":       rmse,
        "mae":        mae,
        "mape":       mape,
    }


def full_sample_ridge(X: np.ndarray, y: np.ndarray) -> tuple:
    """Ajusta Ridge sobre todos los datos; devuelve (model, residuals)."""
    m = RidgeCV(alphas=RIDGE_ALPHAS, cv=None)
    m.fit(X, y)
    residuals = y - m.predict(X)
    log.info(f"  Ridge alpha elegido (full sample): {m.alpha_}")
    return m, residuals


def run_breusch_pagan(X: np.ndarray, y: np.ndarray, residuals: np.ndarray) -> dict:
    """Breusch-Pagan sobre residuos del modelo full-sample."""
    X_const = sm.add_constant(X)
    _, bp_p, _, _ = het_breuschpagan(residuals, X_const)
    verdict = "Homocedasticidad OK (p > 0.05)" if bp_p > 0.05 else "Heterocedasticidad detectada (p <= 0.05)"
    log.info(f"  Breusch-Pagan p={bp_p:.4f} — {verdict}")
    return {"stat": None, "p_value": float(bp_p), "verdict": verdict}


def run_shapiro(residuals: np.ndarray) -> dict:
    """Shapiro-Wilk test de normalidad sobre residuos."""
    stat, p = shapiro(residuals)
    verdict = "Residuos normales (p > 0.05)" if p > 0.05 else "Residuos no normales (p <= 0.05)"
    log.info(f"  Shapiro-Wilk W={stat:.4f}, p={p:.4f} — {verdict}")
    return {"stat": float(stat), "p_value": float(p), "verdict": verdict}


def run_durbin_watson(residuals: np.ndarray) -> float:
    """Durbin-Watson statistic (informativo)."""
    diffs = np.diff(residuals)
    dw = float(np.sum(diffs**2) / np.sum(residuals**2))
    log.info(f"  Durbin-Watson = {dw:.4f} (2 = sin autocorrelación temporal)")
    return dw


def run_morans_i(residuals: np.ndarray, coords: np.ndarray) -> dict:
    """Moran's I global (inverse-distance weights)."""
    n = len(residuals)
    if n < 4:
        return {"I": np.nan, "p_value": np.nan, "verdict": "n insuficiente"}

    dist_matrix = squareform(pdist(coords))
    np.fill_diagonal(dist_matrix, np.inf)
    W = 1.0 / dist_matrix
    W_sum = W.sum()

    z = residuals - residuals.mean()
    numerator   = n * np.sum(W * np.outer(z, z))
    denominator = W_sum * np.sum(z**2)
    I = float(numerator / denominator) if denominator != 0 else np.nan

    E_I = -1.0 / (n - 1)
    S1  = 0.5 * np.sum((W + W.T)**2)
    S2  = np.sum((W.sum(axis=1) + W.sum(axis=0))**2)
    S0  = W_sum
    b2  = (n * np.sum(z**4)) / (np.sum(z**2)**2)

    var_I = (
        n * ((n**2 - 3*n + 3)*S1 - n*S2 + 3*S0**2)
        - b2 * (n*(n-1)*S1 - 2*n*S2 + 6*S0**2)
    ) / ((n-1)*(n-2)*(n-3)*S0**2) - E_I**2

    z_score = (I - E_I) / np.sqrt(var_I) if var_I > 0 else np.nan
    p_value = float(2 * (1 - norm.cdf(abs(z_score)))) if not np.isnan(z_score) else np.nan

    verdict = (
        "Sin autocorrelación espacial (p > 0.05)"
        if (not np.isnan(p_value) and p_value > 0.05)
        else "Autocorrelación espacial detectada (p <= 0.05)"
    )
    log.info(f"  Moran's I={I:.4f}, E[I]={E_I:.4f}, z={z_score:.3f}, p={p_value:.4f} — {verdict}")
    return {"I": float(I), "E_I": float(E_I), "z": float(z_score), "p_value": float(p_value), "verdict": verdict}


def identify_outliers(sensor_ids, residuals: np.ndarray, rmse: float) -> pd.DataFrame:
    """Sensores con |residuo| > 2×RMSE."""
    threshold = 2.0 * rmse
    mask = np.abs(residuals) > threshold
    out_df = pd.DataFrame({
        "sensor_id": sensor_ids,
        "residual":  residuals,
        "abs_residual": np.abs(residuals),
    })
    outliers = out_df[mask].sort_values("abs_residual", ascending=False).copy()
    log.info(f"  Outliers (|residuo| > 2×RMSE={threshold:.3f}): {len(outliers)} sensores → {outliers['sensor_id'].tolist()}")
    return outliers


# ── VISUALIZACIÓN ─────────────────────────────────────────────────────────────

def plot_loocv(y_true_25, y_pred_25, resid_25, sensors_25,
               y_true_10, y_pred_10, resid_10, sensors_10,
               r2_25, rmse_25, r2_10, rmse_10):
    """4-panel figure: obs vs pred + residuos para ambos targets."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle("LOOCV — Ridge Regression | Liverpool Air Quality LUR", fontsize=14, fontweight="bold")

    def _scatter_pred(ax, y_true, y_pred, r2, rmse, title, color):
        mn = min(y_true.min(), y_pred.min()) * 0.95
        mx = max(y_true.max(), y_pred.max()) * 1.05
        ax.scatter(y_true, y_pred, c=color, edgecolors="k", s=60, zorder=3)
        ax.plot([mn, mx], [mn, mx], "r--", lw=1.5, label="1:1")
        ax.set_xlabel("Observado (µg/m³)")
        ax.set_ylabel("Predicho LOOCV (µg/m³)")
        ax.set_title(f"{title}\nR²_CV={r2:.3f}  RMSE={rmse:.2f} µg/m³")
        ax.legend(fontsize=9)

    def _scatter_resid(ax, y_pred, resid, rmse, title, color):
        ax.scatter(y_pred, resid, c=color, edgecolors="k", s=60, zorder=3)
        ax.axhline(0, color="gray", ls="--", lw=1)
        ax.axhline( 2*rmse, color="red", ls=":", lw=1, label=f"±2×RMSE={2*rmse:.2f}")
        ax.axhline(-2*rmse, color="red", ls=":", lw=1)
        ax.set_xlabel("Predicho LOOCV (µg/m³)")
        ax.set_ylabel("Residuo (µg/m³)")
        ax.set_title(f"Residuos — {title}")
        ax.legend(fontsize=9)

    _scatter_pred(axes[0, 0], y_true_25, y_pred_25, r2_25, rmse_25, "PM2.5", "steelblue")
    _scatter_resid(axes[0, 1], y_pred_25, resid_25, rmse_25, "PM2.5", "steelblue")
    _scatter_pred(axes[1, 0], y_true_10, y_pred_10, r2_10, rmse_10, "PM10",  "coral")
    _scatter_resid(axes[1, 1], y_pred_10, resid_10, rmse_10, "PM10",  "coral")

    plt.tight_layout()
    out_path = FIG_DIR / "loocv_obs_vs_pred.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"  Figura guardada → {out_path}")
    return out_path


# ── RESULTADOS ────────────────────────────────────────────────────────────────

def save_loocv_csv(sensors, results_25, results_10):
    """Guarda outputs/loocv_results.csv."""
    df = pd.DataFrame({
        "sensor_id":       sensors,
        "observed_pm25":   results_25["y_obs"],
        "predicted_pm25":  results_25["y_pred"],
        "residual_pm25":   results_25["residuals"],
        "observed_pm10":   results_10["y_obs"],
        "predicted_pm10":  results_10["y_pred"],
        "residual_pm10":   results_10["residuals"],
    })
    path = OUT_DIR / "loocv_results.csv"
    df.to_csv(path, index=False, float_format="%.4f")
    log.info(f"  LOOCV CSV guardado → {path}")
    return df


def _classify(r2: float) -> str:
    if r2 > 0.6:
        return "ROBUSTO (R² > 0.6)"
    elif r2 >= 0.4:
        return "ACEPTABLE CON LIMITACIONES (0.4 ≤ R² ≤ 0.6)"
    else:
        return "REQUIERE MAS DATOS (R² < 0.4)"


def save_validation_report(
    r2_25, rmse_25, mae_25, mape_25,
    r2_10, rmse_10, mae_10, mape_10,
    bp_25, bp_10,
    moran_25, moran_10,
    sw_25, sw_10,
    dw_25, dw_10,
    outliers_25, outliers_10,
    n_sensors: int,
):
    """Escribe outputs/validation_report.md."""
    path = DOCS_DIR / "04_validation_report.md"

    def _fmt_outliers(df, target_label):
        if df.empty:
            return f"Ninguno identificado para {target_label}.\n"
        lines = []
        for _, row in df.iterrows():
            lines.append(
                f"- `{row['sensor_id']}`: residuo = {row['residual']:+.3f} µg/m³"
            )
        return "\n".join(lines) + "\n"

    content = f"""# Validation Report — Task 5 LOOCV
**Proyecto:** PROYIII Liverpool Air Quality LUR
**Fecha:** 2026-04-10
**Modelo:** Ridge Regression (ganador Task 4)
**Protocolo:** Leave-One-Out Cross-Validation (LOOCV), n = {n_sensors} folds

---

## 1. Metricas LOOCV

| Metrica | PM2.5 | PM10 |
|---------|-------|------|
| R² (LOOCV) | {r2_25:.4f} | {r2_10:.4f} |
| RMSE (µg/m³) | {rmse_25:.4f} | {rmse_10:.4f} |
| MAE (µg/m³) | {mae_25:.4f} | {mae_10:.4f} |
| MAPE (%) | {mape_25:.2f} | {mape_10:.2f} |

**Clasificacion:**
- PM2.5: {_classify(r2_25)}
- PM10:  {_classify(r2_10)}

---

## 2. Sensores Outlier (|residuo| > 2 x RMSE)

**PM2.5** (umbral = {2*rmse_25:.3f} µg/m³):
{_fmt_outliers(outliers_25, "PM2.5")}
**PM10** (umbral = {2*rmse_10:.3f} µg/m³):
{_fmt_outliers(outliers_10, "PM10")}

Posibles explicaciones para outliers:
- Microentorno atipico no capturado por las 4 variables (e.g., fuente puntual cercana).
- Efecto de levantamiento de polvo o actividad industrial episodica.
- Errores de medicion del sensor individual (drift, calibracion deficiente).
- Efecto de borde: sensor en limite entre zonas con caracteristicas muy distintas.

---

## 3. Diagnosticos Estadisticos (modelo full-sample)

### 3.1 Breusch-Pagan (homocedasticidad)

| Target | p-value | Interpretacion |
|--------|---------|----------------|
| PM2.5 | {bp_25['p_value']:.4f} | {bp_25['verdict']} |
| PM10  | {bp_10['p_value']:.4f} | {bp_10['verdict']} |

### 3.2 Shapiro-Wilk (normalidad de residuos)

| Target | W | p-value | Interpretacion |
|--------|---|---------|----------------|
| PM2.5 | {sw_25['stat']:.4f} | {sw_25['p_value']:.4f} | {sw_25['verdict']} |
| PM10  | {sw_10['stat']:.4f} | {sw_10['p_value']:.4f} | {sw_10['verdict']} |

### 3.3 Moran's I (autocorrelacion espacial)

| Target | I | E[I] | z | p-value | Interpretacion |
|--------|---|------|---|---------|----------------|
| PM2.5 | {moran_25['I']:.4f} | {moran_25['E_I']:.4f} | {moran_25['z']:.3f} | {moran_25['p_value']:.4f} | {moran_25['verdict']} |
| PM10  | {moran_10['I']:.4f} | {moran_10['E_I']:.4f} | {moran_10['z']:.3f} | {moran_10['p_value']:.4f} | {moran_10['verdict']} |

### 3.4 Durbin-Watson (informativo, orden por sensor_id)

| Target | DW |
|--------|----|
| PM2.5 | {dw_25:.4f} |
| PM10  | {dw_10:.4f} |

> DW ~ 2.0 indica sin autocorrelacion serial. Rango aceptable: 1.5–2.5.

---

## 4. Interpretacion Global

**Rendimiento del modelo:**
- PM2.5 Ridge LOOCV: R²={r2_25:.3f}, RMSE={rmse_25:.2f} µg/m³, MAE={mae_25:.2f} µg/m³.
- PM10  Ridge LOOCV: R²={r2_10:.3f}, RMSE={rmse_10:.2f} µg/m³, MAE={mae_10:.2f} µg/m³.

**Supuestos del modelo:**
- Homocedasticidad: {"PM2.5 OK" if bp_25['p_value'] > 0.05 else "PM2.5 FALLA"} / {"PM10 OK" if bp_10['p_value'] > 0.05 else "PM10 FALLA"}.
  {"> Si alguno falla, los intervalos de confianza de Ridge son anticonservadores." if (bp_25['p_value'] <= 0.05 or bp_10['p_value'] <= 0.05) else ""}
- Normalidad residuos: {"PM2.5 OK" if sw_25['p_value'] > 0.05 else "PM2.5 FALLA"} / {"PM10 OK" if sw_10['p_value'] > 0.05 else "PM10 FALLA"}.
- Autocorrelacion espacial: {"PM2.5 OK" if moran_25['p_value'] > 0.05 else "PM2.5 PROBLEMA"} / {"PM10 OK" if moran_10['p_value'] > 0.05 else "PM10 PROBLEMA"}.

---

## 5. Recomendacion: aptitud para extrapolacion

### PM2.5
{_classify(r2_25)}
{"- R² > 0.6: el modelo puede usarse para extrapolacion espacial con cautela. Se recomienda reportar incertidumbre (intervalo de prediccion) en zonas sin sensores." if r2_25 > 0.6 else "- R² entre 0.4-0.6: aceptable para descripcion espacial relativa (alta/baja contaminacion), pero NO para predicciones absolutas en zonas sin validar." if r2_25 >= 0.4 else "- R² < 0.4: el modelo no tiene capacidad predictiva suficiente. Se requieren mas sensores o variables adicionales antes de extrapolacion."}

### PM10
{_classify(r2_10)}
{"- R² > 0.6: el modelo puede usarse para extrapolacion espacial con cautela. Se recomienda reportar incertidumbre (intervalo de prediccion) en zonas sin sensores." if r2_10 > 0.6 else "- R² entre 0.4-0.6: aceptable para descripcion espacial relativa (alta/baja contaminacion), pero NO para predicciones absolutas en zonas sin validar." if r2_10 >= 0.4 else "- R² < 0.4: el modelo no tiene capacidad predictiva suficiente. Se requieren mas sensores o variables adicionales antes de extrapolacion."}

**Limitaciones clave:**
- n=20 sensores es un tamaño muestral pequeno. LOOCV con n pequeno tiende a ser optimista en varianza.
- Las 4 variables seleccionadas no capturan fuentes episodicas (trafico pesado puntual, viento).
- Extrapolacion confiable se limita a zonas con perfil de uso de suelo similar a los sensores.

---

## 6. Artefactos producidos

| Archivo | Descripcion |
|---------|-------------|
| `outputs/loocv_results.csv` | Predicciones LOOCV por sensor (ambos targets) |
| `outputs/validation_report.md` | Este reporte |
| `outputs/figures/loocv_obs_vs_pred.png` | Graficos obs vs pred + residuos |
"""

    path.write_text(content, encoding="utf-8")
    log.info(f"  Reporte guardado → {path}")
    return path


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Task 5: LOOCV Validation — Ridge Regression ===")

    # 1. Cargar datos
    df_all       = pd.read_csv(FEATURES_CSV)
    sensors_gdf  = gpd.read_file(SENSORS_GPKG)

    # Construir array de coordenadas alineado con sensor_id
    # sensores_snapped puede tener columna sensor_id o no
    if "sensor_id" in sensors_gdf.columns:
        coords_df = sensors_gdf.set_index("sensor_id")[["geometry"]]
    else:
        # Usar orden natural
        coords_df = sensors_gdf[["geometry"]].copy()
        coords_df.index = sensors_gdf.index

    # 2. Matrices de diseño por target
    log.info("  Construyendo matrices de diseño ...")
    dm_25 = build_design_matrix(df_all, "PM2.5")
    dm_10 = build_design_matrix(df_all, "PM10")

    # Ordenar sensores igual que coordenadas
    # Ambas matrices tienen sensor_id como index
    sensor_ids = dm_25.index.tolist()
    log.info(f"  n sensores: {len(sensor_ids)}")

    feats_25 = WINNER_FEATURES["PM2.5"]
    feats_10 = WINNER_FEATURES["PM10"]

    X_25 = dm_25[feats_25].values
    y_25 = dm_25["PM2.5"].values

    X_10 = dm_10[feats_10].values
    y_10 = dm_10["PM10"].values

    # 3. LOOCV
    log.info("  Ejecutando LOOCV PM2.5 ...")
    res_25 = run_loocv(X_25, y_25)
    res_25["y_obs"] = y_25
    log.info(f"  PM2.5 LOOCV → R²={res_25['r2']:.4f}, RMSE={res_25['rmse']:.4f}, "
             f"MAE={res_25['mae']:.4f}, MAPE={res_25['mape']:.2f}%")

    log.info("  Ejecutando LOOCV PM10 ...")
    res_10 = run_loocv(X_10, y_10)
    res_10["y_obs"] = y_10
    log.info(f"  PM10  LOOCV → R²={res_10['r2']:.4f}, RMSE={res_10['rmse']:.4f}, "
             f"MAE={res_10['mae']:.4f}, MAPE={res_10['mape']:.2f}%")

    # 4. Residuos LOOCV para diagnósticos
    # CORRECCIÓN A1: los tests estadísticos se aplican sobre residuos LOOCV,
    # no sobre residuos full-sample. El full-sample ve todos los datos al ajustar,
    # por lo que sus residuos están sesgados a la baja y los tests son anticonservadores.
    log.info("  Usando residuos LOOCV para diagnósticos estadísticos ...")
    full_resid_25 = res_25["residuals"]
    full_resid_10 = res_10["residuals"]

    # Ajuste full-sample solo para loggear el alpha elegido por RidgeCV
    log.info("  Ajustando Ridge full-sample (solo para info de alpha) ...")
    _, _ = full_sample_ridge(X_25, y_25)
    _, _ = full_sample_ridge(X_10, y_10)

    # Coordenadas alineadas con sensor_ids
    if "sensor_id" in sensors_gdf.columns:
        coords_ordered = (
            sensors_gdf.set_index("sensor_id")
            .reindex(sensor_ids)
            [["geometry"]]
        )
        coords = np.column_stack([
            coords_ordered.geometry.x.values,
            coords_ordered.geometry.y.values,
        ])
    else:
        coords = np.column_stack([
            sensors_gdf.geometry.x.values[:len(sensor_ids)],
            sensors_gdf.geometry.y.values[:len(sensor_ids)],
        ])

    # 5. Tests estadísticos
    log.info("  Tests estadísticos sobre residuos full-sample ...")
    bp_25    = run_breusch_pagan(X_25, y_25, full_resid_25)
    bp_10    = run_breusch_pagan(X_10, y_10, full_resid_10)

    sw_25    = run_shapiro(full_resid_25)
    sw_10    = run_shapiro(full_resid_10)

    moran_25 = run_morans_i(full_resid_25, coords)
    moran_10 = run_morans_i(full_resid_10, coords)

    dw_25    = run_durbin_watson(full_resid_25)
    dw_10    = run_durbin_watson(full_resid_10)

    # 6. Outliers LOOCV
    log.info("  Identificando outliers LOOCV ...")
    outliers_25 = identify_outliers(sensor_ids, res_25["residuals"], res_25["rmse"])
    outliers_10 = identify_outliers(sensor_ids, res_10["residuals"], res_10["rmse"])

    # 7. Guardar CSV
    csv_path = save_loocv_csv(sensor_ids, res_25, res_10)

    # 8. Figura
    fig_path = plot_loocv(
        y_25, res_25["y_pred"], res_25["residuals"], sensor_ids,
        y_10, res_10["y_pred"], res_10["residuals"], sensor_ids,
        res_25["r2"], res_25["rmse"],
        res_10["r2"], res_10["rmse"],
    )

    # 9. Reporte
    report_path = save_validation_report(
        res_25["r2"], res_25["rmse"], res_25["mae"], res_25["mape"],
        res_10["r2"], res_10["rmse"], res_10["mae"], res_10["mape"],
        bp_25, bp_10,
        moran_25, moran_10,
        sw_25, sw_10,
        dw_25, dw_10,
        outliers_25, outliers_10,
        n_sensors=len(sensor_ids),
    )

    # 10. Resumen final
    log.info("\n" + "="*60)
    log.info("  RESUMEN TASK 5")
    log.info("="*60)
    log.info(f"  PM2.5: R²={res_25['r2']:.4f} | RMSE={res_25['rmse']:.3f} | MAE={res_25['mae']:.3f} | MAPE={res_25['mape']:.2f}%")
    log.info(f"  PM10:  R²={res_10['r2']:.4f} | RMSE={res_10['rmse']:.3f} | MAE={res_10['mae']:.3f} | MAPE={res_10['mape']:.2f}%")
    log.info(f"  Outliers PM2.5: {outliers_25['sensor_id'].tolist()}")
    log.info(f"  Outliers PM10:  {outliers_10['sensor_id'].tolist()}")
    log.info(f"  BP PM2.5 p={bp_25['p_value']:.4f} | BP PM10 p={bp_10['p_value']:.4f}")
    log.info(f"  Moran PM2.5 p={moran_25['p_value']:.4f} | Moran PM10 p={moran_10['p_value']:.4f}")
    log.info(f"  SW PM2.5 p={sw_25['p_value']:.4f} | SW PM10 p={sw_10['p_value']:.4f}")
    log.info(f"  Artefactos: {csv_path} | {report_path} | {fig_path}")

    return {
        "metrics": {
            "PM2.5": {"r2": res_25["r2"], "rmse": res_25["rmse"], "mae": res_25["mae"], "mape": res_25["mape"]},
            "PM10":  {"r2": res_10["r2"], "rmse": res_10["rmse"], "mae": res_10["mae"], "mape": res_10["mape"]},
        },
        "outliers": {
            "PM2.5": outliers_25["sensor_id"].tolist(),
            "PM10":  outliers_10["sensor_id"].tolist(),
        },
        "stats": {
            "BP":    {"PM2.5": bp_25, "PM10": bp_10},
            "SW":    {"PM2.5": sw_25, "PM10": sw_10},
            "Moran": {"PM2.5": moran_25, "PM10": moran_10},
            "DW":    {"PM2.5": dw_25, "PM10": dw_10},
        },
    }


if __name__ == "__main__":
    main()
