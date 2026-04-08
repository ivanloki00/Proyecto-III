"""
Fases 5-7: Feature Selection, Model Training, Validation & Diagnostics
──────────────────────────────────────────────────────────────────────────
1. Selección de escala óptima por variable (máx correlación)
2. Filtrado por p-value y VIF
3. Entrenamiento separado PM2.5 / PM10 (Lineal + Random Forest)
4. LOOCV
5. Diagnóstico: residuos, Breusch-Pagan, Moran I
6. Exportar modelos .pkl
7. Gráficos de diagnóstico
"""

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
from matplotlib.gridspec import GridSpec

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_squared_error
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor

from scipy.spatial.distance import squareform, pdist

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DATA_INT  = ROOT / "data" / "interim"
OUT_DIR   = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)

FEATURES_CSV = DATA_INT / "lur_features.csv"
SENSORS_GPKG = DATA_INT / "sensores_snapped.gpkg"

BUFFER_RADII   = [50, 100, 250, 500]
TARGETS        = ["PM2.5", "PM10"]
VIF_THRESHOLD  = 5.0
P_THRESHOLD    = 0.10   # relajado un poco dado n=20

# Variables base (sin prefijo de buffer)
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
]


# ═══════════════════════════════════════════════════
# 1. Selección de escala óptima por variable
# ═══════════════════════════════════════════════════

def select_best_buffer(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """
    Para cada variable, elige el buffer con la mayor |correlación| con target.
    Devuelve un DataFrame de 20 filas (1 por sensor) con las mejores variables.
    """
    log.info(f"  Seleccionando escala óptima para {target} ...")

    best_records = {}   # var_name -> (best_buffer, corr, series)

    for var in BASE_VARS:
        best_corr = -1
        best_buf  = None
        for buf in BUFFER_RADII:
            sub = df[df["buffer_m"] == buf]
            if var not in sub.columns or sub[var].std() == 0:
                continue
            corr = abs(sub[[var, target]].corr().iloc[0, 1])
            if not np.isnan(corr) and corr > best_corr:
                best_corr = corr
                best_buf  = buf
        if best_buf is not None and best_corr > 0.05:
            best_records[f"{var}_{best_buf}m"] = {
                "buffer": best_buf,
                "base_var": var,
                "corr": best_corr,
            }

    log.info(f"  Variables retenidas tras selección de escala: {len(best_records)}")

    # Construir tabla pivotada: sensor × mejor variable
    pivot_rows = []
    for _, row_sensor in df[df["buffer_m"] == BUFFER_RADII[0]].iterrows():
        sid = row_sensor["sensor_id"]
        record = {"sensor_id": sid, target: row_sensor[target]}
        for col_name, info in best_records.items():
            buf_row = df[(df["sensor_id"] == sid) & (df["buffer_m"] == info["buffer"])].iloc[0]
            record[col_name] = buf_row[info["base_var"]]
        pivot_rows.append(record)

    result = pd.DataFrame(pivot_rows)

    # Log correlaciones
    corr_summary = {k: round(v["corr"], 3) for k, v in best_records.items()}
    log.info(f"  Correlaciones: {corr_summary}")
    return result


# ═══════════════════════════════════════════════════
# 2. Filtrado por p-value y VIF
# ═══════════════════════════════════════════════════

def filter_by_pvalue(X: pd.DataFrame, y: pd.Series) -> list:
    """OLS univariado: retener variables con p < P_THRESHOLD."""
    kept = []
    for col in X.columns:
        x_const = sm.add_constant(X[[col]])
        try:
            model = sm.OLS(y, x_const).fit()
            p = model.pvalues.iloc[1]
            if p < P_THRESHOLD:
                kept.append(col)
        except Exception:
            pass
    log.info(f"  Variables tras filtro p-value (<{P_THRESHOLD}): {len(kept)} → {kept}")
    return kept


def filter_by_vif(X: pd.DataFrame) -> list:
    """Eliminación iterativa de la variable con VIF más alto."""
    cols = list(X.columns)
    while len(cols) > 1:
        X_sub = X[cols].values
        try:
            vifs = [variance_inflation_factor(X_sub, i) for i in range(len(cols))]
        except Exception:
            break
        max_vif = max(vifs)
        if max_vif <= VIF_THRESHOLD:
            break
        idx = vifs.index(max_vif)
        removed = cols.pop(idx)
        log.info(f"    VIF: eliminar '{removed}' (VIF={max_vif:.1f})")
    log.info(f"  Variables finales tras VIF: {len(cols)} → {cols}")
    return cols


# ═══════════════════════════════════════════════════
# 3. LOOCV
# ═══════════════════════════════════════════════════

def loocv(model_class, X: np.ndarray, y: np.ndarray, **kwargs) -> dict:
    loo = LeaveOneOut()
    y_pred = np.zeros_like(y, dtype=float)

    for train_idx, test_idx in loo.split(X):
        m = model_class(**kwargs)
        m.fit(X[train_idx], y[train_idx])
        y_pred[test_idx] = m.predict(X[test_idx])

    r2   = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return {"r2_cv": r2, "rmse_cv": rmse, "y_pred": y_pred}


# ═══════════════════════════════════════════════════
# 4. Diagnósticos
# ═══════════════════════════════════════════════════

def diagnostics_ols(X: pd.DataFrame, y: pd.Series, model_name: str, target: str):
    """Ajuste OLS completo + Breusch-Pagan + Resumen."""
    X_const = sm.add_constant(X)
    ols = sm.OLS(y, X_const).fit()
    log.info(f"\n{'='*60}\n  OLS Summary: {model_name} → {target}\n{'='*60}")
    log.info(ols.summary().as_text())

    # Breusch-Pagan
    resid = ols.resid
    _, bp_pval, _, _ = het_breuschpagan(resid, X_const)
    log.info(f"  Breusch-Pagan p-value: {bp_pval:.4f} ({'Heterocedasticidad detectada' if bp_pval < 0.05 else 'Homocedasticidad OK'})")
    return ols, resid, bp_pval


def morans_i(residuals: np.ndarray, coords: np.ndarray) -> dict:
    """Cálculo del índice de Moran I global para autocorrelación espacial."""
    n = len(residuals)
    if n < 4:
        return {"I": np.nan, "p_value": np.nan}

    # Matriz de pesos espaciales (inversa de la distancia)
    dist_matrix = squareform(pdist(coords))
    np.fill_diagonal(dist_matrix, np.inf)
    W = 1.0 / dist_matrix
    W_sum = W.sum()

    z = residuals - residuals.mean()
    numerator = n * np.sum(W * np.outer(z, z))
    denominator = W_sum * np.sum(z**2)
    I = numerator / denominator if denominator != 0 else np.nan

    # Expected value and variance under randomization
    E_I = -1.0 / (n - 1)
    # Simplified z-test
    S1 = 0.5 * np.sum((W + W.T)**2)
    S2 = np.sum((W.sum(axis=1) + W.sum(axis=0))**2)
    S0 = W_sum
    b2 = (n * np.sum(z**4)) / (np.sum(z**2)**2)

    var_I = (n * ((n**2 - 3*n + 3)*S1 - n*S2 + 3*S0**2) -
             b2 * (n*(n-1)*S1 - 2*n*S2 + 6*S0**2)) / ((n-1)*(n-2)*(n-3)*S0**2) - E_I**2

    z_score = (I - E_I) / np.sqrt(var_I) if var_I > 0 else np.nan
    from scipy.stats import norm
    p_value = 2 * (1 - norm.cdf(abs(z_score)))

    log.info(f"  Moran's I = {I:.4f}, E[I] = {E_I:.4f}, z = {z_score:.3f}, p = {p_value:.4f}")
    return {"I": I, "E_I": E_I, "z": z_score, "p_value": p_value}


# ═══════════════════════════════════════════════════
# 5. Visualización
# ═══════════════════════════════════════════════════

def plot_diagnostics(y_true, y_pred_lr, y_pred_rf, residuals_lr,
                     target, r2_lr, r2_rf, rmse_lr, rmse_rf):

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(f"Diagnósticos LUR — {target}", fontsize=16, fontweight="bold")
    gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3)

    # 1. Obs vs Pred – Linear
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(y_true, y_pred_lr, c="steelblue", edgecolors="k", s=60)
    mn, mx = min(y_true.min(), y_pred_lr.min()), max(y_true.max(), y_pred_lr.max())
    ax1.plot([mn, mx], [mn, mx], "r--", lw=1.5)
    ax1.set_xlabel("Observado"); ax1.set_ylabel("Predicho")
    ax1.set_title(f"Lineal (R²_CV={r2_lr:.3f}, RMSE={rmse_lr:.2f})")

    # 2. Obs vs Pred – RF
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(y_true, y_pred_rf, c="forestgreen", edgecolors="k", s=60)
    ax2.plot([mn, mx], [mn, mx], "r--", lw=1.5)
    ax2.set_xlabel("Observado"); ax2.set_ylabel("Predicho")
    ax2.set_title(f"Random Forest (R²_CV={r2_rf:.3f}, RMSE={rmse_rf:.2f})")

    # 3. Residuos vs Predichos (Lineal)
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.scatter(y_pred_lr, residuals_lr, c="coral", edgecolors="k", s=60)
    ax3.axhline(0, color="gray", ls="--")
    ax3.set_xlabel("Predicho (Lineal)"); ax3.set_ylabel("Residuo")
    ax3.set_title("Residuos vs Predichos")

    # 4. Histograma de residuos
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.hist(residuals_lr, bins=8, color="mediumpurple", edgecolor="k", alpha=0.8)
    ax4.set_xlabel("Residuo"); ax4.set_ylabel("Frecuencia")
    ax4.set_title("Distribución de Residuos (Lineal)")

    # 5. Q-Q plot
    ax5 = fig.add_subplot(gs[1, 1])
    sm.qqplot(residuals_lr, line="45", ax=ax5, markerfacecolor="teal", markeredgecolor="k", markersize=6)
    ax5.set_title("Q-Q Plot de Residuos")

    # 6. Texto resumen
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")
    summary_text = (
        f"━━━ Resumen {target} ━━━\n\n"
        f"Lineal LOOCV:\n"
        f"  R² = {r2_lr:.4f}\n"
        f"  RMSE = {rmse_lr:.3f}\n\n"
        f"Random Forest LOOCV:\n"
        f"  R² = {r2_rf:.4f}\n"
        f"  RMSE = {rmse_rf:.3f}\n"
    )
    ax6.text(0.1, 0.5, summary_text, fontsize=12, fontfamily="monospace",
             verticalalignment="center", transform=ax6.transAxes,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow"))

    out_path = OUT_DIR / f"diagnostics_{target.replace('.','')}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"  Gráfico guardado → {out_path}")


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    log.info("=== FASES 5-7: Feature Selection, Modelling & Diagnostics ===")

    df_all = pd.read_csv(FEATURES_CSV)

    # Coordenadas de sensores (para Moran's I)
    sensors_gdf = gpd.read_file(SENSORS_GPKG)
    coords = np.column_stack([sensors_gdf.geometry.x, sensors_gdf.geometry.y])

    results = {}

    for target in TARGETS:
        log.info(f"\n{'#'*60}\n  TARGET: {target}\n{'#'*60}")

        # ── 5.1  Selección de escala ──
        df_best = select_best_buffer(df_all, target)

        feature_cols = [c for c in df_best.columns if c not in ["sensor_id", "PM2.5", "PM10"]]
        X_all = df_best[feature_cols].copy()
        y = df_best[target].copy()

        # Reemplazar NaN/Inf
        X_all = X_all.replace([np.inf, -np.inf], np.nan).fillna(0)

        # ── 5.2  Filtro p-value ──
        kept_pval = filter_by_pvalue(X_all, y)
        if len(kept_pval) == 0:
            log.warning(f"  Ninguna variable significativa para {target}. Usando top 5 por |correlación|.")
            corrs = X_all.corrwith(y).abs().sort_values(ascending=False)
            kept_pval = corrs.head(5).index.tolist()

        X_sel = X_all[kept_pval]

        # ── 5.3  Filtro VIF ──
        final_vars = filter_by_vif(X_sel)
        if len(final_vars) == 0:
            final_vars = kept_pval[:1]
        X_final = X_sel[final_vars]

        log.info(f"  Variables finales para {target}: {final_vars}")

        # ── 6.  Entrenamiento ──
        X_np = X_final.values
        y_np = y.values

        # Linear Regression LOOCV
        lr_res = loocv(LinearRegression, X_np, y_np)
        log.info(f"  Lineal LOOCV: R²={lr_res['r2_cv']:.4f}, RMSE={lr_res['rmse_cv']:.3f}")

        # Random Forest LOOCV
        rf_res = loocv(RandomForestRegressor, X_np, y_np,
                       n_estimators=200, max_features="sqrt", random_state=42)
        log.info(f"  Random Forest LOOCV: R²={rf_res['r2_cv']:.4f}, RMSE={rf_res['rmse_cv']:.3f}")

        # ── 7.  Diagnóstico OLS ──
        ols_model, residuals, bp_pval = diagnostics_ols(X_final, y, "Lineal", target)

        # Moran's I
        moran = morans_i(residuals.values, coords)

        # ── Gráficos ──
        plot_diagnostics(
            y_np, lr_res["y_pred"], rf_res["y_pred"], residuals.values,
            target, lr_res["r2_cv"], rf_res["r2_cv"],
            lr_res["rmse_cv"], rf_res["rmse_cv"]
        )

        # ── Modelo ganador ──
        # Criterio: mayor R²-CV; si ambos > 0.6, preferir lineal por interpretabilidad
        if lr_res["r2_cv"] >= 0.6 and lr_res["r2_cv"] >= rf_res["r2_cv"] * 0.9:
            best_name = "LinearRegression"
            best_model = LinearRegression().fit(X_np, y_np)
        else:
            best_name = "RandomForest"
            best_model = RandomForestRegressor(n_estimators=200, max_features="sqrt", random_state=42).fit(X_np, y_np)

        log.info(f"  ★ Modelo elegido para {target}: {best_name}")

        # Guardar modelo
        model_info = {
            "model": best_model,
            "model_name": best_name,
            "features": final_vars,
            "target": target,
            "r2_cv": max(lr_res["r2_cv"], rf_res["r2_cv"]),
            "rmse_cv": min(lr_res["rmse_cv"], rf_res["rmse_cv"]),
            "bp_pvalue": bp_pval,
            "moran_I": moran["I"],
            "moran_p": moran["p_value"],
        }
        tag = target.replace(".", "")
        pkl_path = OUT_DIR / f"lur_model_{tag}.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump(model_info, f)
        log.info(f"  Modelo guardado → {pkl_path}")

        results[target] = {
            "model_info": model_info,
            "df_best": df_best,
            "final_vars": final_vars,
        }

    # ── Resumen final ──
    log.info(f"\n{'='*60}\n  RESUMEN FINAL\n{'='*60}")
    for t, r in results.items():
        mi = r["model_info"]
        log.info(
            f"  {t}: {mi['model_name']} | R²_CV={mi['r2_cv']:.4f} | RMSE_CV={mi['rmse_cv']:.3f} | "
            f"BP_p={mi['bp_pvalue']:.4f} | Moran_I={mi['moran_I']:.4f} (p={mi['moran_p']:.4f})"
        )

    return results


if __name__ == "__main__":
    main()
