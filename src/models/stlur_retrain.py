"""
stlur_retrain.py — Reentrenamiento ST-LUR con panel histórico 2021-2025
========================================================================
Usa sensores_monthly_full.csv + meteo_monthly_full.csv para reentrenar
el modelo de factor temporal con 4+ años de datos en lugar de solo 2024.

Mejoras respecto a la versión inicial:
  1. Panel 4× más largo → mejor estimación de estacionalidad y meteo
  2. Modelo de factor temporal más rico:
       log(AF) ~ temp + wind + rain + mes_sin + mes_cos + temp² + temp×wind
  3. IC corregido: suma cuadrática de incertidumbre temporal + espacial LUR
  4. Validación temporal split: entrenar hasta 2024-12, validar en 2025Q1
"""
from __future__ import annotations
import logging
import pickle
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.model_selection import cross_val_score

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT       = Path(__file__).resolve().parents[2]
DATA_INT   = ROOT / "data" / "interim"
DATA_PROC  = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "outputs" / "models"
FIG_DIR    = ROOT / "outputs" / "figures" / "stlur"
FIG_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = ["PM2.5", "PM10"]
ALPHAS  = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 500.0]

# Incertidumbre espacial del modelo LUR LSOA (RMSE del Ridge LSOA)
# Derivada del modelo lur_lsoa_PM25.pkl durante entrenamiento; si no está disponible
# se usa un valor conservador de 3 µg/m³.
LUR_SPATIAL_RMSE = {"PM2.5": 3.0, "PM10": 6.0}

# Columnas de features temporales base
BASE_FEATURES = [
    "air_temperature_mean",
    "wind_speed_mean",
    "rain_days",
    "mes_sin",
    "mes_cos",
]


# ─── UTILIDADES ──────────────────────────────────────────────────────────────

def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    month_num = pd.to_datetime(df["year_month"]).dt.month
    df["month_num"] = month_num
    df["mes_sin"]   = np.sin(2 * np.pi * month_num / 12)
    df["mes_cos"]   = np.cos(2 * np.pi * month_num / 12)
    return df


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Añade términos de segundo orden para el modelo de factor temporal."""
    df = df.copy()
    t  = df["air_temperature_mean"]
    w  = df["wind_speed_mean"]
    r  = df["rain_days"]
    # Cuadráticos: captura no-linealidad temperatura (inversión térmica en frío)
    df["temp_sq"]      = t ** 2
    df["wind_sq"]      = w ** 2
    # Interacciones: viento limpia, lluvia limpia
    df["temp_x_wind"]  = t * w
    df["temp_x_rain"]  = t * r
    df["wind_x_rain"]  = w * r
    return df


def build_meteo_future(meteo_full: pd.DataFrame, h_months: int = 3) -> pd.DataFrame:
    """
    Genera meteo futura como mediana climatológica del mismo mes
    sobre todos los años disponibles (más robusta que usar solo 2024).
    """
    meteo_ext = add_temporal_features(meteo_full)
    meteo_ext = add_interaction_features(meteo_ext)

    last_date = pd.to_datetime(meteo_full["year_month"].max())
    future_rows = []
    for i in range(1, h_months + 1):
        fut = last_date + pd.DateOffset(months=i)
        same_month = meteo_ext[meteo_ext["month_num"] == fut.month]
        if same_month.empty:
            row = meteo_ext.iloc[-1].copy()
        else:
            row = same_month.median(numeric_only=True)
            row = row.copy()
        row["year_month"] = fut.strftime("%Y-%m")
        future_rows.append(row)

    fut_df = pd.DataFrame(future_rows).reset_index(drop=True)
    # Re-calcular mes_sin/cos desde year_month (por si la mediana los distorsionó)
    month_num = pd.to_datetime(fut_df["year_month"]).dt.month
    fut_df["month_num"] = month_num
    fut_df["mes_sin"]   = np.sin(2 * np.pi * month_num / 12)
    fut_df["mes_cos"]   = np.cos(2 * np.pi * month_num / 12)
    log.info("Meteo futura (climatología multi-año): %s", fut_df["year_month"].tolist())
    return fut_df


# ═══════════════════════════════════════════════════════════════════════════════
# MODELO ST-LUR MEJORADO
# ═══════════════════════════════════════════════════════════════════════════════

class STLURModelV2:
    """
    ST-LUR de dos etapas — versión mejorada con panel 2021-2025.

    Mejoras:
      - Features de segundo orden (temp², temp×wind, ...)
      - IC que combina incertidumbre temporal + espacial LUR
      - Climatología multi-año para pronóstico futuro
    """

    def __init__(self, target: str = "PM2.5", degree: int = 2):
        self.target   = target
        self.degree   = degree
        self.model_af = None
        self._X_train = None
        self._y_train = None
        self._feature_names: list[str] = []

    def _build_features(self, meteo: pd.DataFrame) -> np.ndarray:
        base = BASE_FEATURES
        df   = meteo[base].copy()
        if self.degree >= 2:
            t = meteo["air_temperature_mean"]
            w = meteo["wind_speed_mean"]
            r = meteo["rain_days"]
            df = df.copy()
            df["temp_sq"]     = t ** 2
            df["wind_sq"]     = w ** 2
            df["temp_x_wind"] = t * w
            df["temp_x_rain"] = t * r
            df["wind_x_rain"] = w * r
        self._feature_names = list(df.columns)
        return df.values

    # ── Entrenamiento ────────────────────────────────────────────────────────

    def fit(
        self,
        sensors: pd.DataFrame,
        meteo: pd.DataFrame,
        train_until: str | None = None,
        train_from: str = "2022-01",
    ) -> "STLURModelV2":
        """
        Entrena el modelo log-AF con normalización año×sensor.

        La normalización es relativa a la mediana anual DE ESE AÑO para ese sensor,
        lo que elimina la tendencia inter-anual (bajada PM2.5 2022→2024) y deja
        solo la señal estacional/meteorológica pura.

        train_until : usa solo datos hasta esta fecha (split temporal).
        train_from  : ignora datos anteriores a esta fecha (default 2022 — excluye
                      los dos sensores 70b3d549 con lecturas atípicas de 2021).
        """
        sensors = sensors[sensors["year_month"] >= train_from]
        if train_until:
            sensors = sensors[sensors["year_month"] <= train_until]
            meteo   = meteo[meteo["year_month"] <= train_until]

        # Mediana anual por (sensor, año) — normalización año-específica
        sensors = sensors.copy()
        sensors["year"] = pd.to_datetime(sensors["year_month"]).dt.year
        annual_by_year = (
            sensors.dropna(subset=[self.target])
            .groupby(["sensor_id", "year"])[self.target]
            .median()
            .rename("annual_median_year")
            .reset_index()
        )

        meteo_ext = add_temporal_features(meteo)

        df = (
            sensors[["sensor_id", "year_month", "year", self.target]]
            .dropna(subset=[self.target])
            .merge(meteo_ext[["year_month"] + BASE_FEATURES], on="year_month", how="inner")
            .merge(annual_by_year, on=["sensor_id", "year"], how="left")
        )
        df = df.dropna(subset=["annual_median_year"])

        # log-AF: relativo a la mediana del AÑO específico del sensor
        # → elimina tendencia inter-anual, retiene señal estacional pura
        df["log_af"] = np.log(
            np.clip(df[self.target] / df["annual_median_year"], 1e-4, None)
        )
        valid = df["log_af"].replace([np.inf, -np.inf], np.nan).notna()
        df = df[valid].reset_index(drop=True)

        # Guardar mediana 2024 por sensor (ancla para prediccion futura)
        self._annual_2024 = (
            sensors[sensors["year"] == 2024]
            .groupby("sensor_id")[self.target]
            .median()
        )

        X = self._build_features(df)
        y = df["log_af"].values

        self.model_af = Pipeline([
            ("scaler", StandardScaler()),
            ("ridge",  RidgeCV(alphas=ALPHAS, cv=5)),
        ])
        self.model_af.fit(X, y)

        self._X_train = X
        self._y_train = y

        # CV interna: Leave-One-Sensor-Out
        r2_cv, rmse_cv = self._looso_cv(sensors, meteo_ext, annual_by_year)
        alpha_chosen = self.model_af.named_steps["ridge"].alpha_

        log.info(
            "[V2 %s] n=%d obs | %d sensores | alpha=%.3f | R²_LOSO=%.4f | RMSE_LOSO=%.3f",
            self.target, len(y), df["sensor_id"].nunique(),
            alpha_chosen, r2_cv, rmse_cv,
        )
        return self

    def _looso_cv(
        self,
        sensors: pd.DataFrame,
        meteo_ext: pd.DataFrame,
        annual_by_year: pd.DataFrame,
    ) -> tuple[float, float]:
        sensors = sensors.copy()
        sensors["year"] = pd.to_datetime(sensors["year_month"]).dt.year
        df = (
            sensors[["sensor_id", "year_month", "year", self.target]]
            .dropna(subset=[self.target])
            .merge(meteo_ext[["year_month"] + BASE_FEATURES], on="year_month", how="inner")
            .merge(annual_by_year, on=["sensor_id", "year"], how="left")
        )
        df = df.dropna(subset=["annual_median_year"])
        df["log_af"] = np.log(np.clip(df[self.target] / df["annual_median_year"], 1e-4, None))
        df = df[df["log_af"].replace([np.inf, -np.inf], np.nan).notna()].reset_index(drop=True)

        unique_sensors = df["sensor_id"].unique()
        y_pred_orig_cv = np.zeros(len(df))

        for sid in unique_sensors:
            tm = df["sensor_id"] == sid
            tr = ~tm
            if tr.sum() < 10:
                y_pred_orig_cv[tm] = df.loc[tr, self.target].mean()
                continue
            Xtr = self._build_features(df[tr])
            Xte = self._build_features(df[tm])
            m = Pipeline([("scaler", StandardScaler()), ("ridge", RidgeCV(alphas=ALPHAS))])
            m.fit(Xtr, df.loc[tr, "log_af"].values)
            log_af_pred = m.predict(Xte)
            y_pred_orig_cv[tm] = df.loc[tm, "annual_median_year"].values * np.exp(log_af_pred)

        y_true = df[self.target].values
        r2   = r2_score(y_true, y_pred_orig_cv)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred_orig_cv))
        return r2, rmse

    # ── Predicción ───────────────────────────────────────────────────────────

    def predict_temporal_factor(self, meteo_df: pd.DataFrame) -> np.ndarray:
        """Devuelve el factor multiplicativo para cada fila de meteo_df."""
        meteo_ext = add_temporal_features(meteo_df) if "mes_sin" not in meteo_df.columns else meteo_df
        X = self._build_features(meteo_ext)
        return np.exp(self.model_af.predict(X))

    def predict_lsoa_series(
        self,
        baseline: float,
        meteo_series: pd.DataFrame,
        n_boot: int = 500,
        alpha: float = 0.10,
    ) -> pd.DataFrame:
        """
        Genera la serie temporal para un LSOA dado su baseline anual.

        IC corregido:
          σ_total² = σ_temporal_boot² + σ_spatial_LUR²
          (suma cuadrática para combinar fuentes de incertidumbre independientes)
        """
        meteo_ext = add_temporal_features(meteo_series)
        tf        = self.predict_temporal_factor(meteo_ext)
        pm_pred   = baseline * tf

        # Bootstrap sobre el modelo temporal
        X_pred = self._build_features(meteo_ext)
        rng    = np.random.default_rng(42)
        n      = len(self._X_train)
        boot   = np.zeros((n_boot, len(X_pred)))
        for b in range(n_boot):
            idx = rng.integers(0, n, size=n)
            m = Pipeline([("scaler", StandardScaler()), ("ridge", RidgeCV(alphas=ALPHAS))])
            m.fit(self._X_train[idx], self._y_train[idx])
            boot[b] = baseline * np.exp(m.predict(X_pred))

        # Percentiles temporales
        ci_lo_temp = np.percentile(boot, 100 * alpha / 2,     axis=0)
        ci_hi_temp = np.percentile(boot, 100 * (1 - alpha/2), axis=0)

        # Añadir incertidumbre espacial LUR (σ_spatial = RMSE del modelo LSOA)
        sigma_spat = LUR_SPATIAL_RMSE.get(self.target, 3.0)
        z = 1.645  # percentil 95% (IC 90%)
        ci_lo = np.maximum(0.0, pm_pred - np.sqrt((pm_pred - ci_lo_temp)**2 + (z * sigma_spat)**2))
        ci_hi = pm_pred + np.sqrt((ci_hi_temp - pm_pred)**2 + (z * sigma_spat)**2)

        result = meteo_series[["year_month"]].copy()
        result["date"]                  = pd.to_datetime(result["year_month"] + "-01")
        result[f"{self.target}_pred"]   = pm_pred.round(3)
        result["ci_lower"]              = ci_lo.round(3)
        result["ci_upper"]              = ci_hi.round(3)
        result["temporal_factor"]       = tf.round(4)
        result["spatial_baseline"]      = baseline
        return result

    # ── Persistencia ─────────────────────────────────────────────────────────

    def save(self) -> Path:
        tag  = self.target.replace(".", "")
        path = MODELS_DIR / f"stlur_v2_{tag}.pkl"
        with open(path, "wb") as f:
            pickle.dump(self, f)
        log.info("Modelo guardado: %s", path)
        return path

    @staticmethod
    def load(target: str) -> "STLURModelV2":
        tag  = target.replace(".", "")
        path = MODELS_DIR / f"stlur_v2_{tag}.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN TEMPORAL SPLIT
# ═══════════════════════════════════════════════════════════════════════════════

def temporal_split_validation(
    sensors: pd.DataFrame,
    meteo: pd.DataFrame,
    lsoa_preds: pd.DataFrame,
    target: str = "PM2.5",
    train_until: str = "2024-12",
    test_months: list[str] | None = None,
) -> pd.DataFrame:
    """
    Entrena hasta train_until y predice en test_months.
    Compara predicciones ST-LUR con observaciones reales de sensores.
    """
    import geopandas as gpd, re as _re

    if test_months is None:
        test_months = ["2025-01", "2025-02", "2025-03"]

    # Modelo entrenado solo con datos hasta train_until
    model = STLURModelV2(target=target).fit(
        sensors, meteo, train_until=train_until, train_from="2022-01"
    )

    # Meteo futura: usar los valores reales disponibles en meteo_full
    meteo_test = add_temporal_features(
        meteo[meteo["year_month"].isin(test_months)]
    )
    if meteo_test.empty:
        log.warning("No hay meteo disponible para %s — usando climatología", test_months)
        meteo_test = build_meteo_future(
            meteo[meteo["year_month"] <= train_until], h_months=len(test_months)
        )
        meteo_test = meteo_test[meteo_test["year_month"].isin(test_months)]

    # Sensor → LSOA mapping
    sensors_gdf = gpd.read_file(ROOT / "data" / "interim" / "sensores_snapped.gpkg")[["sensor_id","geometry"]]
    lsoa_gdf    = gpd.read_file(ROOT / "data" / "raw" / "lsoa_liverpool.gpkg")[["LSOA21CD","LSOA21NM","geometry"]]
    if sensors_gdf.crs.to_epsg() != lsoa_gdf.crs.to_epsg():
        lsoa_gdf = lsoa_gdf.to_crs(sensors_gdf.crs)
    sensor_lsoa = gpd.sjoin(sensors_gdf, lsoa_gdf, how="left", predicate="within")[["sensor_id","LSOA21CD","LSOA21NM"]]

    col_final = f"{target}_final"
    rows = []
    for sid, grp in sensor_lsoa.dropna(subset=["LSOA21CD"]).groupby("sensor_id"):
        lsoa_id = grp.iloc[0]["LSOA21CD"]
        lsoa_row = lsoa_preds[lsoa_preds["LSOA21CD"] == lsoa_id]
        if lsoa_row.empty or col_final not in lsoa_row.columns:
            continue
        baseline = float(lsoa_row.iloc[0][col_final])

        preds = model.predict_lsoa_series(baseline, meteo_test, n_boot=300)
        for _, pr in preds.iterrows():
            rows.append({
                "sensor_id":     sid,
                "LSOA21CD":      lsoa_id,
                "LSOA21NM":      grp.iloc[0]["LSOA21NM"],
                "year_month":    pr["year_month"],
                f"{target}_pred": pr[f"{target}_pred"],
                "ci_lower":      pr["ci_lower"],
                "ci_upper":      pr["ci_upper"],
                "baseline":      baseline,
            })

    preds_df = pd.DataFrame(rows)

    # Observaciones reales en test_months
    obs = sensors[
        sensors["year_month"].isin(test_months) &
        sensors["sensor_id"].isin(sensor_lsoa["sensor_id"]) &
        sensors["completeness"].ge(0.40)
    ][["sensor_id","year_month",target,"completeness"]].rename(columns={target: f"{target}_obs"})

    val = preds_df.merge(obs, on=["sensor_id","year_month"], how="inner")

    if len(val) < 3:
        log.warning("Solo %d puntos de validacion — demasiado poco para metricas fiables", len(val))
        return val

    y_obs  = val[f"{target}_obs"].values
    y_pred = val[f"{target}_pred"].values
    err    = y_pred - y_obs
    covered = ((y_obs >= val["ci_lower"].values) & (y_obs <= val["ci_upper"].values)).sum()

    log.info("\n=== VALIDACION TEMPORAL SPLIT (%s) ===", target)
    log.info("Train: hasta %s | Test: %s", train_until, test_months)
    log.info("n=%d | R²=%.4f | RMSE=%.3f | MAE=%.3f | Bias=%.3f | IC90%% cov=%d/%d",
             len(val),
             r2_score(y_obs, y_pred),
             np.sqrt(mean_squared_error(y_obs, y_pred)),
             mean_absolute_error(y_obs, y_pred),
             err.mean(),
             covered, len(val))

    return val


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIÓN MEJORADA
# ═══════════════════════════════════════════════════════════════════════════════

def plot_curve_v2(
    historical: pd.DataFrame,
    forecast: pd.DataFrame,
    target: str = "PM2.5",
    obs_points: pd.DataFrame | None = None,
    save: bool = True,
) -> plt.Figure:
    """
    Gráfico histórico + pronóstico con IC corregido.
    obs_points : DataFrame opcional con columnas [date, PM_obs] para plotear
                 puntos observados reales (ej. 2025Q1) sobre la curva.
    """
    pm_col    = f"{target}_pred"
    lsoa_id   = historical["lsoa_id"].iloc[0] if "lsoa_id" in historical.columns else "LSOA"
    lsoa_name = historical["lsoa_name"].iloc[0] if "lsoa_name" in historical.columns else lsoa_id
    who_limit = 15.0 if target == "PM2.5" else 45.0

    hist_dates = historical["date"]
    fore_dates = forecast["date"]

    fig, ax = plt.subplots(figsize=(15, 6))
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#fafafa")

    # Banda IC histórico
    ax.fill_between(hist_dates, historical["ci_lower"], historical["ci_upper"],
                    alpha=0.18, color="#2166ac")
    ax.plot(hist_dates, historical[pm_col], "o-", color="#2166ac",
            lw=2, ms=5, label="Estimación ST-LUR histórica 2024")

    # Banda IC pronóstico
    ax.fill_between(fore_dates, forecast["ci_lower"], forecast["ci_upper"],
                    alpha=0.22, color="#d6604d")
    ax.plot(fore_dates, forecast[pm_col], "s--", color="#d6604d",
            lw=2.5, ms=8, label=f"Pronóstico ({len(forecast)} meses, IC 90 %)")

    # Conector
    ax.plot([hist_dates.iloc[-1], fore_dates.iloc[0]],
            [historical[pm_col].iloc[-1], forecast[pm_col].iloc[0]],
            "--", color="gray", alpha=0.4, lw=1)

    # Observaciones reales 2025 (si se pasan)
    if obs_points is not None and not obs_points.empty:
        ax.scatter(obs_points["date"], obs_points["pm_obs"],
                   color="#4a1942", marker="D", s=60, zorder=5,
                   label="Observado 2025Q1 (sensores)", edgecolors="white", linewidths=0.8)

    # Líneas de referencia
    mid = hist_dates.iloc[-1] + (fore_dates.iloc[0] - hist_dates.iloc[-1]) / 2
    ax.axvline(mid, color="gray", ls=":", alpha=0.6, lw=1.2)
    ax.axhline(who_limit, color="#969696", ls="--", lw=1, alpha=0.7)
    ax.text(hist_dates.iloc[0], who_limit + 0.3,
            f"OMS {who_limit} µg/m³", fontsize=8, color="#969696")
    baseline = historical["spatial_baseline"].iloc[0]
    ax.axhline(baseline, color="#4dac26", ls="-.", lw=1, alpha=0.6)
    ax.text(hist_dates.iloc[0], baseline + 0.3,
            f"Baseline LUR {baseline:.1f} µg/m³", fontsize=8, color="#4dac26")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)
    ax.set_xlabel("Mes", fontsize=11)
    ax.set_ylabel(f"{target} (µg/m³)", fontsize=11)
    ax.set_title(
        f"ST-LUR v2 — {target} — {lsoa_name}\n"
        f"(entrenado 2021-2024, IC corregido = temporal + espacial LUR)",
        fontsize=13, fontweight="bold",
    )
    ax.legend(loc="upper right", framealpha=0.85, fontsize=9)
    ax.grid(True, alpha=0.22, ls="--")
    plt.tight_layout()

    if save:
        tag = target.replace(".", "")
        out = FIG_DIR / f"stlur_v2_{tag}_{lsoa_id}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log.info("Gráfico guardado: %s", out)
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("=== ST-LUR v2 — Reentrenamiento con panel 2021-2025 ===")

    # ── Cargar datos ─────────────────────────────────────────────────────────
    sensors_path = DATA_INT / "sensores_monthly_full.csv"
    meteo_path   = DATA_INT / "meteo_monthly_full.csv"

    if not sensors_path.exists():
        raise FileNotFoundError(
            "sensores_monthly_full.csv no encontrado. "
            "Ejecuta primero: python src/data/build_full_panel.py"
        )
    if not meteo_path.exists():
        raise FileNotFoundError(
            "meteo_monthly_full.csv no encontrado. "
            "Ejecuta primero: python src/data/build_full_panel.py"
        )

    sensors   = pd.read_csv(sensors_path)
    meteo     = pd.read_csv(meteo_path)
    lsoa_preds = pd.read_csv(DATA_PROC / "lur_barrios_predictions.csv")

    log.info(
        "Datos cargados: %d obs. sensores (%d sensores, %s–%s) | %d meses meteo",
        len(sensors), sensors["sensor_id"].nunique(),
        sensors["year_month"].min(), sensors["year_month"].max(),
        len(meteo),
    )

    # ── Entrenar modelos para PM2.5 y PM10 ───────────────────────────────────
    for target in TARGETS:
        col_final = f"{target}_final"
        if col_final not in lsoa_preds.columns:
            log.warning("Columna %s no en lur_barrios_predictions — saltando", col_final)
            continue
        model = STLURModelV2(target=target, degree=2).fit(
            sensors, meteo, train_until=None   # usar todos los datos disponibles
        )
        model.save()

    # ── Validación temporal split (train ≤ 2024-12, test = 2025Q1) ───────────
    log.info("\n-- Validacion temporal split --")
    val_results = temporal_split_validation(
        sensors, meteo, lsoa_preds,
        target="PM2.5",
        train_until="2024-12",
        test_months=["2025-01", "2025-02", "2025-03"],
    )
    if not val_results.empty:
        val_path = ROOT / "outputs" / "stlur_v2_validation.csv"
        val_results.to_csv(val_path, index=False)
        log.info("Validacion guardada: %s", val_path)

    # ── Ejemplo: curva para 3 LSOAs + observaciones 2025 ────────────────────
    model_pm25 = STLURModelV2.load("PM2.5")
    meteo_hist  = add_temporal_features(meteo[meteo["year_month"] <= "2024-12"])
    # Usar meteo real de 2025 si está disponible; si no, climatología
    meteo_2025_real = meteo[meteo["year_month"] > "2024-12"]
    if not meteo_2025_real.empty:
        log.info("Usando meteo REAL de 2025 para pronóstico (%d meses)", len(meteo_2025_real))
        meteo_fore = add_temporal_features(meteo_2025_real)
    else:
        meteo_fore = build_meteo_future(meteo[meteo["year_month"] <= "2024-12"], h_months=3)

    example_ids = lsoa_preds["LSOA21CD"].dropna().head(3).tolist()
    for lid in example_ids:
        col_final = "PM2.5_final"
        row = lsoa_preds[lsoa_preds["LSOA21CD"] == lid]
        if row.empty:
            continue
        baseline  = float(row.iloc[0][col_final])
        lsoa_name = row.iloc[0].get("LSOA21NM", lid)

        hist_df = model_pm25.predict_lsoa_series(baseline, meteo_hist)
        hist_df["lsoa_id"]   = lid
        hist_df["lsoa_name"] = lsoa_name

        fore_df = model_pm25.predict_lsoa_series(baseline, meteo_fore)
        fore_df["lsoa_id"]   = lid
        fore_df["lsoa_name"] = lsoa_name

        plot_curve_v2(hist_df, fore_df, target="PM2.5")

    # ── Predicciones completas 302 LSOAs ─────────────────────────────────────
    log.info("\n-- Generando predicciones para 302 LSOAs --")
    all_rows = []
    meteo_all = pd.concat([meteo_hist, meteo_fore], ignore_index=True)
    # Año de corte para etiquetar histórico vs forecast en el CSV
    cutoff = "2024-12"

    for _, lsoa_row in lsoa_preds.iterrows():
        lid      = lsoa_row["LSOA21CD"]
        baseline = lsoa_row.get("PM2.5_final")
        if pd.isna(baseline):
            continue
        lsoa_name = lsoa_row.get("LSOA21NM", lid)
        series = model_pm25.predict_lsoa_series(baseline, meteo_all, n_boot=200)
        series["lsoa_id"]   = lid
        series["lsoa_name"] = lsoa_name
        series["type"] = series["year_month"].apply(
            lambda m: "historical" if m <= cutoff else "forecast"
        )
        all_rows.append(series)

    df_all = pd.concat(all_rows, ignore_index=True)
    out_path = ROOT / "outputs" / "stlur_v2_predictions.csv"
    df_all.to_csv(out_path, index=False)
    log.info("Predicciones v2 exportadas: %s (%d filas)", out_path, len(df_all))

    log.info("=== ST-LUR v2 completado ===")


if __name__ == "__main__":
    main()
