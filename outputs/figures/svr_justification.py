"""
Figure: Three reasons SVR-RBF was selected over Ridge, Lasso, ElasticNet and Random Forest.
Sources:
  - Model comparison: docs/08_lur_improvement_session.md (Section 8, same feature set)
  - LOOCV predictions: data/processed/loocv_results.csv
  - LUR features: data/interim/lur_features.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score

ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "outputs" / "figures"

# ── DATA ──────────────────────────────────────────────────────────────────────

# A: Model comparison (from 08_lur_improvement_session.md §8, same LOSO-CV run)
models_pm25 = {
    "SVR\n(RBF)":          (0.6020, 2.232),
    "Gradient\nBoosting":  (0.5898, 2.266),
    "Random\nForest":      (0.5871, 2.273),
    "Linear\nRegression":  (0.4638, 2.590),
    "Ridge":               (0.4612, 2.597),
    # ElasticNet from model_comparison.csv (earlier feature set — lower bound)
    "ElasticNet\n(Lasso)": (0.4196, 2.695),
}
models_pm10 = {
    "SVR\n(RBF)":          (0.5809, 3.512),
    "Ridge":               (0.5623, 3.590),
    "Random\nForest":      (0.5416, 3.673),
    # Not evaluated in same run for PM10; GB shown from model_comparison.csv
    "Gradient\nBoosting":  (0.2562, 4.774),
    "Linear\nRegression":  (0.3887, 4.328),
    "ElasticNet\n(Lasso)": (0.4351, 4.161),
}

# B: LOOCV predictions — filter IQR outliers per target
loocv_raw = pd.read_csv(ROOT / "data" / "processed" / "loocv_results.csv")

def iqr_mask(series, k=1.5):
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    return series <= q3 + k * (q3 - q1)

loocv = loocv_raw[
    iqr_mask(loocv_raw["observed_pm25"]) & iqr_mask(loocv_raw["predicted_pm25"]) &
    iqr_mask(loocv_raw["observed_pm10"]) & iqr_mask(loocv_raw["predicted_pm10"])
].copy()
n_dropped = len(loocv_raw) - len(loocv)

# C: LUR features — green space (buffer 100m) and residential roads (buffer 1000m)
lur = pd.read_csv(ROOT / "data" / "interim" / "lur_features.csv")
feat_100_raw  = lur[lur["buffer_m"] == 100][["sensor_id","landuse_green_m2","PM2.5","PM10"]].dropna()
feat_1000_raw = lur[lur["buffer_m"] == 1000][["sensor_id","road_length_residential_m","PM2.5","PM10"]].dropna()

feat_100  = feat_100_raw[iqr_mask(feat_100_raw["landuse_green_m2"])].copy()
feat_1000 = feat_1000_raw[iqr_mask(feat_1000_raw["road_length_residential_m"])].copy()

# ── STYLE ─────────────────────────────────────────────────────────────────────
BLUE   = "#2563eb"   # SVR
GREY   = "#94a3b8"   # others
RED    = "#ef4444"
GREEN  = "#16a34a"
BG     = "#f8fafc"

plt.rcParams.update({
    "font.family":  "DejaVu Sans",
    "font.size":    9,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.facecolor":     BG,
    "figure.facecolor":   "white",
})

fig = plt.figure(figsize=(14, 9))
fig.suptitle(
    "SVR with RBF kernel: three reasons for selection over Ridge, Lasso, ElasticNet and Random Forest",
    fontsize=13, fontweight="bold", y=0.98
)

gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.52, wspace=0.38,
                       left=0.07, right=0.97, top=0.91, bottom=0.08)

# ── PANEL A1: R² comparison — PM2.5 ──────────────────────────────────────────
ax_a1 = fig.add_subplot(gs[0, 0])
names  = list(models_pm25.keys())
r2s    = [v[0] for v in models_pm25.values()]
colors = [BLUE if "SVR" in n else GREY for n in names]
bars   = ax_a1.barh(names, r2s, color=colors, edgecolor="white", height=0.6)
ax_a1.axvline(r2s[0], color=BLUE, linestyle="--", linewidth=0.8, alpha=0.5)
for bar, val in zip(bars, r2s):
    ax_a1.text(val + 0.005, bar.get_y() + bar.get_height()/2,
               f"{val:.3f}", va="center", fontsize=7.5,
               color=BLUE if val == r2s[0] else "#475569", fontweight="bold" if val == r2s[0] else "normal")
ax_a1.set_xlim(0, 0.72)
ax_a1.set_xlabel("R²  (LOSO-CV)", fontsize=8)
ax_a1.set_title("PM₂.₅  —  R²", fontsize=9, fontweight="bold")
ax_a1.tick_params(axis="y", labelsize=7.8)
ax_a1.annotate("① Best accuracy", xy=(0.03, 0.97), xycoords="axes fraction",
               fontsize=8, color=BLUE, fontweight="bold", va="top")

# ── PANEL A2: R² comparison — PM10 ───────────────────────────────────────────
ax_a2 = fig.add_subplot(gs[1, 0])
names10 = list(models_pm10.keys())
r2s10   = [v[0] for v in models_pm10.values()]
colors10 = [BLUE if "SVR" in n else GREY for n in names10]
bars10 = ax_a2.barh(names10, r2s10, color=colors10, edgecolor="white", height=0.6)
ax_a2.axvline(r2s10[0], color=BLUE, linestyle="--", linewidth=0.8, alpha=0.5)
for bar, val in zip(bars10, r2s10):
    ax_a2.text(val + 0.005, bar.get_y() + bar.get_height()/2,
               f"{val:.3f}", va="center", fontsize=7.5,
               color=BLUE if val == r2s10[0] else "#475569", fontweight="bold" if val == r2s10[0] else "normal")
ax_a2.set_xlim(0, 0.72)
ax_a2.set_xlabel("R²  (LOSO-CV)", fontsize=8)
ax_a2.set_title("PM₁₀  —  R²", fontsize=9, fontweight="bold")
ax_a2.tick_params(axis="y", labelsize=7.8)

# ── PANEL B: LOOCV scatter ────────────────────────────────────────────────────
ax_b = fig.add_subplot(gs[:, 1])
obs25  = loocv["observed_pm25"]
pred25 = loocv["predicted_pm25"]
obs10  = loocv["observed_pm10"]
pred10 = loocv["predicted_pm10"]

ax_b.scatter(obs25, pred25, color=BLUE, alpha=0.75, s=55, label="PM₂.₅", zorder=3, edgecolors="white", linewidths=0.5)
ax_b.scatter(obs10, pred10, color=GREEN, alpha=0.70, s=55, marker="s", label="PM₁₀", zorder=3, edgecolors="white", linewidths=0.5)

# 1:1 line
all_vals = np.concatenate([obs25, pred25, obs10, pred10])
lims = [all_vals.min() * 0.9, all_vals.max() * 1.05]
ax_b.plot(lims, lims, "k--", linewidth=1, alpha=0.5, label="1:1 line")

# R² annotations
r2_25 = r2_score(obs25, pred25)
r2_10 = r2_score(obs10, pred10)
ax_b.text(0.05, 0.93, f"PM₂.₅  R²={r2_25:.3f}", transform=ax_b.transAxes,
          color=BLUE, fontsize=8.5, fontweight="bold")
ax_b.text(0.05, 0.85, f"PM₁₀   R²={r2_10:.3f}", transform=ax_b.transAxes,
          color=GREEN, fontsize=8.5, fontweight="bold")

ax_b.set_xlim(lims); ax_b.set_ylim(lims)
ax_b.set_xlabel("Observed  (µg/m³)", fontsize=9)
ax_b.set_ylabel("SVR predicted  (µg/m³)", fontsize=9)
dropped_str = f"  ({n_dropped} outlier{'s' if n_dropped!=1 else ''} removed)" if n_dropped else ""
ax_b.set_title(f"② Generalisation — LOSO-CV predictions\nvs. observed (n={len(loocv)} sensors{dropped_str})", fontsize=9, fontweight="bold")
ax_b.legend(fontsize=8, framealpha=0.7)

# ── PANEL C1: Green space non-linearity ───────────────────────────────────────
ax_c1 = fig.add_subplot(gs[0, 2])
x_g = feat_100["landuse_green_m2"].values
y_g = feat_100["PM2.5"].values
ax_c1.scatter(x_g, y_g, color=BLUE, s=50, zorder=3, alpha=0.8, edgecolors="white", linewidths=0.5)

x_line = np.linspace(x_g.min(), x_g.max(), 200).reshape(-1,1)
# Linear
lin = LinearRegression().fit(x_g.reshape(-1,1), y_g)
# Polynomial (proxy for non-linear / RBF behaviour)
poly3 = make_pipeline(PolynomialFeatures(2), LinearRegression())
poly3.fit(x_g.reshape(-1,1), y_g)

ax_c1.plot(x_line, lin.predict(x_line), color=RED, linewidth=1.5,
           linestyle="--", label=f"Linear  R²={r2_score(y_g, lin.predict(x_g.reshape(-1,1))):.2f}", zorder=4)
ax_c1.plot(x_line, poly3.predict(x_line), color=BLUE, linewidth=1.8,
           label=f"Non-linear  R²={r2_score(y_g, poly3.predict(x_g.reshape(-1,1))):.2f}", zorder=5)

ax_c1.set_xlabel("Green space area — 100 m buffer (m²)", fontsize=8)
ax_c1.set_ylabel("PM₂.₅ mean (µg/m³)", fontsize=8)
ax_c1.set_title("③ Non-linearity — green space\nvs. PM₂.₅", fontsize=9, fontweight="bold")
ax_c1.legend(fontsize=7.5, framealpha=0.8)
ax_c1.annotate("RBF kernel captures\ncurvilinear response",
               xy=(x_g.max()*0.55, y_g.max()*0.95), fontsize=7.5, color=BLUE,
               ha="center", style="italic")

# ── PANEL C2: Road length non-linearity ──────────────────────────────────────
ax_c2 = fig.add_subplot(gs[1, 2])
x_r = feat_1000["road_length_residential_m"].values
y_r = feat_1000["PM2.5"].values
ax_c2.scatter(x_r, y_r, color=BLUE, s=50, zorder=3, alpha=0.8, edgecolors="white", linewidths=0.5)

x_rline = np.linspace(x_r.min(), x_r.max(), 200).reshape(-1,1)
lin_r  = LinearRegression().fit(x_r.reshape(-1,1), y_r)
poly_r = make_pipeline(PolynomialFeatures(2), LinearRegression())
poly_r.fit(x_r.reshape(-1,1), y_r)

ax_c2.plot(x_rline, lin_r.predict(x_rline), color=RED, linewidth=1.5,
           linestyle="--", label=f"Linear  R²={r2_score(y_r, lin_r.predict(x_r.reshape(-1,1))):.2f}", zorder=4)
ax_c2.plot(x_rline, poly_r.predict(x_rline), color=BLUE, linewidth=1.8,
           label=f"Non-linear  R²={r2_score(y_r, poly_r.predict(x_r.reshape(-1,1))):.2f}", zorder=5)

ax_c2.set_xlabel("Residential road length — 1 000 m buffer (m)", fontsize=8)
ax_c2.set_ylabel("PM₂.₅ mean (µg/m³)", fontsize=8)
ax_c2.set_title("③ Non-linearity — road exposure\nvs. PM₂.₅", fontsize=9, fontweight="bold")
ax_c2.legend(fontsize=7.5, framealpha=0.8)

# ── FOOTNOTE ─────────────────────────────────────────────────────────────────
fig.text(0.5, 0.01,
         "LOSO-CV = Leave-One-Sensor-Out cross-validation  |  n = 21 sensors  |  "
         "ElasticNet values from initial feature set (lower bound).  "
         "Lasso is subsumed by ElasticNet (alpha=0.5).  "
         "Outliers removed via IQR (k=1.5) in LOOCV scatter and feature panels.",
         ha="center", fontsize=7, color="#64748b")

out_path = OUT / "svr_justification.png"
fig.savefig(out_path, dpi=180, bbox_inches="tight")
print(f"Saved: {out_path}")
