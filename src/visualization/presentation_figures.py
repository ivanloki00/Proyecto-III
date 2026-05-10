"""
Figuras limpias para presentación — Modelo RidgeCV (componente espacial LUR)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.metrics import r2_score, mean_squared_error

ROOT    = Path(__file__).resolve().parents[2]
DATA    = ROOT / "data" / "processed" / "LUR"
FIG_OUT = ROOT / "outputs" / "figures" / "presentation"
FIG_OUT.mkdir(parents=True, exist_ok=True)

PALETTE = {
    "ridge":  "#E07B54",
    "svr":    "#4C8BB5",
    "rf":     "#5BA85C",
    "other":  "#AAAAAA",
    "accent": "#E07B54",
    "line":   "#2C3E50",
}

PLT_PARAMS = {
    "figure.facecolor": "white",
    "axes.facecolor":   "white",
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "font.family":      "sans-serif",
    "font.size":        13,
    "axes.titlesize":   16,
    "axes.labelsize":   13,
    "xtick.labelsize":  12,
    "ytick.labelsize":  12,
    "legend.fontsize":  12,
}
plt.rcParams.update(PLT_PARAMS)

# ── 1. COMPARACIÓN DE MODELOS ─────────────────────────────────────────────────
comp = pd.read_csv(DATA / "model_comparison.csv")

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)
fig.suptitle("Comparación de modelos — LOOCV", fontsize=18, fontweight="bold", y=1.02)

for ax, target in zip(axes, ["PM2.5", "PM10"]):
    df = comp[comp["target"] == target].sort_values("r2_cv", ascending=True)
    # excluir LogLinear (métricas en escala log, no comparables directamente)
    df = df[df["model"] != "LogLinear"]

    colors = []
    for _, row in df.iterrows():
        if row["model"] == "Ridge":
            colors.append(PALETTE["ridge"])
        elif row["model"] == "SVR":
            colors.append(PALETTE["svr"])
        elif row["model"] == "RandomForest":
            colors.append(PALETTE["rf"])
        else:
            colors.append(PALETTE["other"])

    bars = ax.barh(df["model"], df["r2_cv"], color=colors, edgecolor="white", height=0.6)

    # etiquetas de valor
    for bar, val in zip(bars, df["r2_cv"]):
        ax.text(val + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", ha="left", fontsize=11, fontweight="bold")

    ax.set_xlim(0, df["r2_cv"].max() + 0.09)
    ax.set_xlabel("R² (LOOCV)")
    ax.set_title(f"{target}", fontweight="bold")
    ax.axvline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.6, label="R²=0.5")
    ax.legend(handles=[
        mpatches.Patch(color=PALETTE["svr"],   label="SVR (ganador)"),
        mpatches.Patch(color=PALETTE["ridge"],  label="RidgeCV"),
        mpatches.Patch(color=PALETTE["rf"],     label="Random Forest"),
        mpatches.Patch(color=PALETTE["other"],  label="Otros"),
    ], loc="lower right", frameon=False)

plt.tight_layout()
out = FIG_OUT / "01_model_comparison.png"
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close()
print(f"Guardado: {out}")

# ── 2. OBS VS PRED (LOOCV — Ridge espacial) ───────────────────────────────────
loocv = pd.read_csv(DATA / "loocv_results.csv")

fig, axes = plt.subplots(1, 2, figsize=(13, 6))
fig.suptitle("Observado vs Predicho — RidgeCV (LOOCV)", fontsize=18, fontweight="bold", y=1.02)

for ax, obs_col, pred_col, target, unit in zip(
    axes,
    ["observed_pm25", "observed_pm10"],
    ["predicted_pm25", "predicted_pm10"],
    ["PM2.5", "PM10"],
    ["µg/m³", "µg/m³"],
):
    obs  = loocv[obs_col]
    pred = loocv[pred_col]
    r2   = r2_score(obs, pred)
    rmse = mean_squared_error(obs, pred) ** 0.5

    ax.scatter(obs, pred, color=PALETTE["ridge"], s=90, alpha=0.85, edgecolors="white", linewidths=0.8, zorder=3)

    mn, mx = min(obs.min(), pred.min()) - 1, max(obs.max(), pred.max()) + 1
    ax.plot([mn, mx], [mn, mx], "--", color=PALETTE["line"], linewidth=1.5, label="1:1", zorder=2)

    ax.set_xlim(mn, mx)
    ax.set_ylim(mn, mx)
    ax.set_xlabel(f"Observado ({unit})")
    ax.set_ylabel(f"Predicho ({unit})")
    ax.set_title(f"{target}", fontweight="bold")
    ax.text(0.05, 0.92, f"R² = {r2:.3f}\nRMSE = {rmse:.2f} {unit}",
            transform=ax.transAxes, fontsize=12, va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#F5F5F5", edgecolor="lightgray"))
    ax.legend(frameon=False)

plt.tight_layout()
out = FIG_OUT / "02_obs_vs_pred.png"
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close()
print(f"Guardado: {out}")

# ── 3. IMPORTANCIA DE VARIABLES (coeficientes Ridge espacial) ─────────────────
# Valores extraídos del modelo entrenado (proxy: |coef| × std_var)
importance_pm25 = pd.DataFrame({
    "variable": [
        "Espacios verdes\n(buffer 100 m)",
        "Vías residenciales\n(buffer 500 m)",
        "Dist. zona industrial\n(buffer 50 m)",
        "Suelo industrial\n(buffer 250 m)",
    ],
    "importance": [1.657, 1.328, 0.694, 0.217],
    "direction":  ["negativo", "positivo", "negativo", "positivo"],
})

importance_pm10 = pd.DataFrame({
    "variable": [
        "Vías residenciales\n(buffer 500 m)",
        "Espacios verdes\n(buffer 100 m)",
        "Suelo industrial\n(buffer 250 m)",
        "Dist. zona industrial\n(buffer 50 m)",
    ],
    "importance": [1.521, 1.384, 0.812, 0.341],
    "direction":  ["positivo", "negativo", "positivo", "negativo"],
})

dir_colors = {"negativo": "#5BA85C", "positivo": "#E07B54"}

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Importancia de variables — RidgeCV (|coef| × σ)", fontsize=18, fontweight="bold", y=1.02)

for ax, df, target in zip(axes, [importance_pm25, importance_pm10], ["PM2.5", "PM10"]):
    df_s = df.sort_values("importance")
    colors = [dir_colors[d] for d in df_s["direction"]]
    bars = ax.barh(df_s["variable"], df_s["importance"], color=colors, edgecolor="white", height=0.55)

    for bar, val in zip(bars, df_s["importance"]):
        ax.text(val + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}", va="center", ha="left", fontsize=11, fontweight="bold")

    ax.set_xlim(0, df_s["importance"].max() + 0.25)
    ax.set_xlabel("|Coef. Ridge| × Desv. Est.")
    ax.set_title(f"{target}", fontweight="bold")

    legend_patches = [
        mpatches.Patch(color="#5BA85C", label="Efecto protector (↓ PM)"),
        mpatches.Patch(color="#E07B54", label="Efecto contaminante (↑ PM)"),
    ]
    ax.legend(handles=legend_patches, frameon=False, loc="lower right")

plt.tight_layout()
out = FIG_OUT / "03_variable_importance.png"
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close()
print(f"Guardado: {out}")

print("\nListo. Figuras en:", FIG_OUT)
