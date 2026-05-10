"""
ST-LUR Forecast — Spatiotemporal LUR de dos etapas
====================================================
Extiende el LUR espacial existente con una dimensión temporal para:
  1. Reconstruir la curva histórica 2024 de PM2.5/PM10 en barrios sin sensor.
  2. Predecir los próximos h meses en esas mismas zonas ciegas.

Arquitectura de dos etapas:
  Etapa 1 (espacial) : baseline anual por LSOA  ← lur_barrios_predictions.csv
  Etapa 2 (temporal) : factor de ajuste mensual ← sensores_monthly × meteo_monthly
  PM2.5(LSOA, t)     = baseline(LSOA) × exp(log_AF_model(t))

Salidas:
  outputs/figures/stlur/  ← gráficos histórico + pronóstico
  outputs/stlur_predictions.csv ← curvas mensuales para los 302 LSOAs
"""

# ─── CONFIG ──────────────────────────────────────────────────────────────────
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
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]

DATA_INT   = ROOT / "data" / "interim"
DATA_PROC  = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "outputs" / "models"
FIG_DIR    = ROOT / "outputs" / "figures" / "stlur"
FIG_DIR.mkdir(parents=True, exist_ok=True)

TARGETS           = ["PM2.5", "PM10"]
TEMPORAL_FEATURES = ["air_temperature_mean", "wind_speed_mean", "rain_days",
                     "mes_sin", "mes_cos"]
N_BOOT            = 500    # iteraciones bootstrap para IC
ALPHA_CI          = 0.10   # IC al 90 %
H_FORECAST        = 2      # meses hacia el futuro


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1 — Transformación de Variables Temporales
# ═══════════════════════════════════════════════════════════════════════════════

def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade codificación cíclica del mes y número de mes a un DataFrame
    que tenga la columna 'year_month' (formato '2024-01').
    """
    df = df.copy()
    month_num = pd.to_datetime(df["year_month"]).dt.month
    df["month_num"]  = month_num
    df["mes_sin"]    = np.sin(2 * np.pi * month_num / 12)
    df["mes_cos"]    = np.cos(2 * np.pi * month_num / 12)
    return df


def build_future_meteo(meteo_2024: pd.DataFrame, h_months: int = H_FORECAST) -> pd.DataFrame:
    """
    Genera variables meteorológicas para los h meses siguientes al último
    mes disponible, usando la climatología del mismo mes en 2024 como proxy.

    Razonamiento: con solo 1 año de datos no es posible ajustar un modelo
    de serie temporal para la meteo. El análogo climatológico (mismo mes,
    año anterior) es la opción más conservadora y menos propensa a sesgo.
    """
    meteo_ext = add_temporal_features(meteo_2024)
    last_date  = pd.to_datetime(meteo_2024["year_month"].max())

    future_rows = []
    for i in range(1, h_months + 1):
        future_date  = last_date + pd.DateOffset(months=i)
        future_month = future_date.month

        clim = meteo_ext[meteo_ext["month_num"] == future_month]
        if clim.empty:
            clim = meteo_ext.iloc[-1]
        else:
            clim = clim.iloc[0]

        row = clim.copy()
        row["year_month"] = future_date.strftime("%Y-%m")
        future_rows.append(row)

    df_future = pd.DataFrame(future_rows).reset_index(drop=True)
    df_future = add_temporal_features(df_future)
    log.info("Meteo futura generada: %s", df_future["year_month"].tolist())
    return df_future


def load_all_temporal_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga y prepara los tres datasets temporales base."""
    sensors  = pd.read_csv(DATA_INT / "sensores_monthly.csv")
    meteo    = pd.read_csv(DATA_INT / "meteo_monthly.csv")
    lsoa_preds = pd.read_csv(DATA_PROC / "lur_barrios_predictions.csv")

    meteo   = add_temporal_features(meteo)
    sensors = add_temporal_features(sensors)

    log.info(
        "Datos cargados: %d obs. de sensores | %d meses meteo | %d LSOAs",
        len(sensors), len(meteo), len(lsoa_preds),
    )
    return sensors, meteo, lsoa_preds


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2 — Arquitectura ST-LUR de dos etapas
# ═══════════════════════════════════════════════════════════════════════════════

class STLURModel:
    """
    ST-LUR de dos etapas para barrios sin sensor.

    Etapa 1 — baseline espacial:
        Toma el valor PM2.5_final / PM10_final de lur_barrios_predictions.csv
        (ya entrenado por lur_lsoa_model.py con Ridge sobre features LSOA).

    Etapa 2 — modelo de factor de ajuste temporal:
        log(AF) = log(PM2.5_mes / PM2.5_medio_sensor) ~ temperatura + viento +
                  lluvia + sin(mes) + cos(mes)
        Entrenado sobre el panel de sensores (26 × 12 = ~312 obs).

    Predicción para (LSOA_i, mes_t):
        PM2.5(i, t) = baseline_i × exp(log_AF(mes_t))
    """

    def __init__(self, target: str = "PM2.5"):
        if target not in TARGETS:
            raise ValueError(f"target debe ser uno de {TARGETS}")
        self.target        = target
        self.model_af      = None   # Pipeline(scaler + RidgeCV)
        self._X_train      = None   # guardado para bootstrap
        self._y_train      = None

    # ── Entrenamiento del modelo de factor temporal ──────────────────────────

    def fit(self, sensors: pd.DataFrame, meteo: pd.DataFrame) -> "STLURModel":
        """
        Entrena el modelo log-AF sobre el panel sensor × mes.

        sensors : debe contener [sensor_id, year_month, <target>, mes_sin, mes_cos]
        meteo   : debe contener [year_month] + TEMPORAL_FEATURES sin codificación cíclica
        """
        # Media anual de cada sensor (solo sobre meses con dato)
        annual_mean = (
            sensors.dropna(subset=[self.target])
            .groupby("sensor_id")[self.target]
            .mean()
            .rename("annual_mean")
        )

        # Panel: sensor × mes con meteo
        df = (
            sensors[["sensor_id", "year_month", self.target]]
            .dropna(subset=[self.target])
            .merge(meteo[["year_month"] + TEMPORAL_FEATURES], on="year_month", how="inner")
        )
        df["annual_mean"] = df["sensor_id"].map(annual_mean)
        df = df.dropna(subset=["annual_mean"])

        # Factor de ajuste: desviación relativa respecto a la media anual del sensor
        df["log_af"] = np.log(
            np.clip(df[self.target] / df["annual_mean"], 1e-6, None)
        )

        valid = df["log_af"].replace([np.inf, -np.inf], np.nan).notna()
        df = df[valid].reset_index(drop=True)

        X = df[TEMPORAL_FEATURES].values
        y = df["log_af"].values

        self.model_af = Pipeline([
            ("scaler", StandardScaler()),
            ("ridge",  RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0], cv=5)),
        ])
        self.model_af.fit(X, y)

        self._X_train = X
        self._y_train = y

        # Métricas de validación cruzada interna (leave-one-sensor-out)
        r2, rmse = self._looso_cv(sensors, meteo)
        log.info(
            "[ST-LUR %s] Modelo AF ajustado | n=%d | R²_CV(LOSO)=%.4f | RMSE_CV=%.4f",
            self.target, len(y), r2, rmse,
        )
        return self

    def _looso_cv(self, sensors: pd.DataFrame, meteo: pd.DataFrame) -> tuple[float, float]:
        """Leave-One-Sensor-Out CV para evaluar el modelo de factor temporal."""
        annual_mean = (
            sensors.dropna(subset=[self.target])
            .groupby("sensor_id")[self.target]
            .mean()
        )
        df = (
            sensors[["sensor_id", "year_month", self.target]]
            .dropna(subset=[self.target])
            .merge(meteo[["year_month"] + TEMPORAL_FEATURES], on="year_month", how="inner")
        )
        df["annual_mean"] = df["sensor_id"].map(annual_mean)
        df = df.dropna(subset=["annual_mean"])
        df["log_af"] = np.log(np.clip(df[self.target] / df["annual_mean"], 1e-6, None))
        valid = df["log_af"].replace([np.inf, -np.inf], np.nan).notna()
        df = df[valid].reset_index(drop=True)

        unique_sensors = df["sensor_id"].unique()
        y_pred_cv = np.zeros(len(df))

        for sid in unique_sensors:
            test_mask  = df["sensor_id"] == sid
            train_mask = ~test_mask
            if train_mask.sum() < 5:
                continue
            m = Pipeline([
                ("scaler", StandardScaler()),
                ("ridge",  RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0])),
            ])
            m.fit(df.loc[train_mask, TEMPORAL_FEATURES].values,
                  df.loc[train_mask, "log_af"].values)
            y_pred_cv[test_mask] = m.predict(
                df.loc[test_mask, TEMPORAL_FEATURES].values
            )

        y_true_orig = df[self.target].values
        y_pred_orig = df["annual_mean"].values * np.exp(y_pred_cv)
        r2   = r2_score(y_true_orig, y_pred_orig)
        rmse = np.sqrt(mean_squared_error(y_true_orig, y_pred_orig))
        return r2, rmse

    # ── Predicción del factor temporal ───────────────────────────────────────

    def predict_temporal_factor(self, meteo_series: pd.DataFrame) -> np.ndarray:
        """
        Devuelve el factor multiplicativo exp(log_AF) para cada mes.
        meteo_series debe tener las columnas en TEMPORAL_FEATURES.
        """
        X = meteo_series[TEMPORAL_FEATURES].values
        log_af = self.model_af.predict(X)
        return np.exp(log_af)

    # ── Persistencia ─────────────────────────────────────────────────────────

    def save(self, path: Path | None = None) -> Path:
        tag  = self.target.replace(".", "")
        path = path or (MODELS_DIR / f"stlur_temporal_{tag}.pkl")
        with open(path, "wb") as f:
            pickle.dump(self, f)
        log.info("Modelo ST-LUR guardado → %s", path)
        return path

    @staticmethod
    def load(target: str = "PM2.5") -> "STLURModel":
        tag  = target.replace(".", "")
        path = MODELS_DIR / f"stlur_temporal_{tag}.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3 — Proyección Histórica (evolución 2024)
# ═══════════════════════════════════════════════════════════════════════════════

def project_historical(
    lsoa_id: str,
    model: STLURModel,
    lsoa_preds: pd.DataFrame,
    meteo_2024: pd.DataFrame,
    n_boot: int = N_BOOT,
    alpha: float = ALPHA_CI,
) -> pd.DataFrame:
    """
    Genera la curva mensual PM2.5 estimada para un LSOA sin sensor durante 2024.

    Parámetros
    ----------
    lsoa_id    : código LSOA21CD (p.ej. 'E01006512')
    model      : STLURModel ajustado
    lsoa_preds : DataFrame de lur_barrios_predictions.csv
    meteo_2024 : DataFrame mensual de meteo con TEMPORAL_FEATURES
    n_boot     : iteraciones bootstrap para el IC
    alpha      : nivel de significación (0.10 → IC 90 %)

    Devuelve
    --------
    DataFrame con columnas:
      year_month, date, PM_pred, ci_lower, ci_upper, baseline, temporal_factor
    """
    col_final = f"{model.target}_final"
    row = lsoa_preds[lsoa_preds["LSOA21CD"] == lsoa_id]
    if row.empty:
        raise ValueError(f"LSOA '{lsoa_id}' no encontrado en lur_barrios_predictions.")
    baseline = float(row.iloc[0][col_final])
    lsoa_name = row.iloc[0].get("LSOA21NM", lsoa_id)

    meteo_ext = add_temporal_features(meteo_2024)
    tf = model.predict_temporal_factor(meteo_ext)
    pm_pred = baseline * tf

    # Bootstrap CI
    rng = np.random.default_rng(42)
    X_pred = meteo_ext[TEMPORAL_FEATURES].values
    boot_preds = _bootstrap_predictions(
        model._X_train, model._y_train, X_pred, baseline, rng, n_boot
    )

    result = meteo_ext[["year_month"]].copy()
    result["date"]            = pd.to_datetime(result["year_month"] + "-01")
    result[f"{model.target}_pred"] = pm_pred
    result["ci_lower"]        = np.percentile(boot_preds, 100 * alpha / 2,     axis=0)
    result["ci_upper"]        = np.percentile(boot_preds, 100 * (1 - alpha/2), axis=0)
    result["spatial_baseline"]    = baseline
    result["temporal_factor"] = tf
    result["lsoa_id"]         = lsoa_id
    result["lsoa_name"]       = lsoa_name
    result["type"]            = "historical"

    log.info(
        "[%s] %s | baseline=%.2f µg/m³ | rango mensual=[%.2f, %.2f]",
        model.target, lsoa_name, baseline, pm_pred.min(), pm_pred.max(),
    )
    return result


def _bootstrap_predictions(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_pred: np.ndarray,
    baseline: float,
    rng: np.random.Generator,
    n_boot: int,
) -> np.ndarray:
    """Bootstrap paramétrico sobre el modelo de log-AF."""
    n = len(y_train)
    preds = np.zeros((n_boot, len(X_pred)))
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        m = Pipeline([
            ("scaler", StandardScaler()),
            ("ridge",  RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0])),
        ])
        m.fit(X_train[idx], y_train[idx])
        preds[b] = baseline * np.exp(m.predict(X_pred))
    return preds


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 4 — Forecasting (predicción 2 meses futuros)
# ═══════════════════════════════════════════════════════════════════════════════

def forecast_lsoa(
    lsoa_id: str,
    model: STLURModel,
    lsoa_preds: pd.DataFrame,
    meteo_2024: pd.DataFrame,
    h_months: int = H_FORECAST,
    n_boot: int = N_BOOT,
    alpha: float = ALPHA_CI,
) -> pd.DataFrame:
    """
    Genera la predicción de los próximos h_months meses para un LSOA ciego.

    Meteo futura: análogo climatológico (mismo mes en 2024).
    IC: bootstrap sobre el modelo de log-AF.

    Devuelve DataFrame con las mismas columnas que project_historical,
    con type='forecast'.
    """
    col_final = f"{model.target}_final"
    row = lsoa_preds[lsoa_preds["LSOA21CD"] == lsoa_id]
    if row.empty:
        raise ValueError(f"LSOA '{lsoa_id}' no encontrado.")
    baseline  = float(row.iloc[0][col_final])
    lsoa_name = row.iloc[0].get("LSOA21NM", lsoa_id)

    meteo_future = build_future_meteo(meteo_2024, h_months=h_months)
    tf      = model.predict_temporal_factor(meteo_future)
    pm_pred = baseline * tf

    rng = np.random.default_rng(99)
    X_pred = meteo_future[TEMPORAL_FEATURES].values
    boot_preds = _bootstrap_predictions(
        model._X_train, model._y_train, X_pred, baseline, rng, n_boot
    )

    result = meteo_future[["year_month"]].copy()
    result["date"]             = pd.to_datetime(result["year_month"] + "-01")
    result[f"{model.target}_pred"] = pm_pred
    result["ci_lower"]         = np.percentile(boot_preds, 100 * alpha / 2,     axis=0)
    result["ci_upper"]         = np.percentile(boot_preds, 100 * (1 - alpha/2), axis=0)
    result["spatial_baseline"]     = baseline
    result["temporal_factor"]  = tf
    result["lsoa_id"]          = lsoa_id
    result["lsoa_name"]        = lsoa_name
    result["type"]             = "forecast"

    log.info(
        "[%s] Forecast %s: %s → %.2f µg/m³ (IC 90%%: [%.2f, %.2f])",
        model.target, lsoa_name,
        meteo_future["year_month"].tolist(),
        pm_pred.mean(),
        result["ci_lower"].mean(), result["ci_upper"].mean(),
    )
    return result


def forecast_all_lsoas(
    model: STLURModel,
    lsoa_preds: pd.DataFrame,
    meteo_2024: pd.DataFrame,
    h_months: int = H_FORECAST,
    save: bool = True,
) -> pd.DataFrame:
    """
    Genera proyección histórica + pronóstico para TODOS los LSOAs (302).
    Exporta CSV a outputs/stlur_predictions.csv.
    """
    all_rows = []
    lsoa_ids = lsoa_preds["LSOA21CD"].dropna().unique()

    for lid in lsoa_ids:
        try:
            hist = project_historical(lid, model, lsoa_preds, meteo_2024,
                                       n_boot=200, alpha=ALPHA_CI)
            fore = forecast_lsoa(lid, model, lsoa_preds, meteo_2024,
                                  h_months=h_months, n_boot=200, alpha=ALPHA_CI)
            all_rows.extend([hist, fore])
        except Exception as e:
            log.warning("LSOA %s omitido: %s", lid, e)

    df_all = pd.concat(all_rows, ignore_index=True)
    if save:
        out_path = ROOT / "outputs" / "stlur_predictions.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df_all.to_csv(out_path, index=False)
        log.info("Predicciones completas exportadas → %s (%d filas)", out_path, len(df_all))
    return df_all


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 5 — Visualización
# ═══════════════════════════════════════════════════════════════════════════════

def plot_curve(
    historical: pd.DataFrame,
    forecast: pd.DataFrame,
    target: str = "PM2.5",
    save: bool = True,
) -> plt.Figure:
    """
    Genera el gráfico de línea con:
      - Curva histórica 2024 (con IC 90 %)
      - Pronóstico h meses (con IC 90 %)
      - Línea divisoria histórico / pronóstico
      - Nivel de referencia WHO (PM2.5: 15 µg/m³ | PM10: 45 µg/m³)

    Parámetros
    ----------
    historical : DataFrame de project_historical()
    forecast   : DataFrame de forecast_lsoa()
    target     : 'PM2.5' o 'PM10'
    save       : si True, guarda PNG en outputs/figures/stlur/
    """
    pm_col    = f"{target}_pred"
    lsoa_id   = historical["lsoa_id"].iloc[0]
    lsoa_name = historical["lsoa_name"].iloc[0]
    who_limit = 15.0 if target == "PM2.5" else 45.0

    hist_dates = historical["date"]
    fore_dates = forecast["date"]

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#fafafa")

    # ── Banda IC histórico ──
    ax.fill_between(
        hist_dates, historical["ci_lower"], historical["ci_upper"],
        alpha=0.20, color="#2166ac", label="_nolegend_",
    )

    # ── Curva histórica ──
    ax.plot(
        hist_dates, historical[pm_col],
        "o-", color="#2166ac", linewidth=2, markersize=5,
        label=f"Estimación histórica 2024",
    )

    # ── Banda IC pronóstico ──
    ax.fill_between(
        fore_dates, forecast["ci_lower"], forecast["ci_upper"],
        alpha=0.25, color="#d6604d", label="_nolegend_",
    )

    # ── Curva pronóstico ──
    ax.plot(
        fore_dates, forecast[pm_col],
        "s--", color="#d6604d", linewidth=2.5, markersize=8,
        label=f"Pronóstico ({len(forecast)} meses, IC 90 %)",
    )

    # ── Conexión (línea fina entre último histórico y primer pronóstico) ──
    join_dates = [hist_dates.iloc[-1], fore_dates.iloc[0]]
    join_vals  = [historical[pm_col].iloc[-1], forecast[pm_col].iloc[0]]
    ax.plot(join_dates, join_vals, "--", color="gray", alpha=0.5, linewidth=1)

    # ── Divisor vertical ──
    mid_date = hist_dates.iloc[-1] + (fore_dates.iloc[0] - hist_dates.iloc[-1]) / 2
    ax.axvline(mid_date, color="gray", linestyle=":", alpha=0.7, linewidth=1.2)
    ax.text(mid_date, ax.get_ylim()[0] if ax.get_ylim()[0] > 0 else 0.5,
            "  inicio\n  pronóstico", va="bottom", ha="left",
            fontsize=8, color="gray", style="italic")

    # ── Límite WHO ──
    ax.axhline(who_limit, color="#969696", linestyle="--", linewidth=1, alpha=0.8)
    ax.text(hist_dates.iloc[0], who_limit + 0.3,
            f"Guía OMS ({who_limit} µg/m³)", fontsize=8, color="#969696")

    # ── Baseline espacial ──
    baseline = historical["spatial_baseline"].iloc[0]
    ax.axhline(baseline, color="#4dac26", linestyle="-.", linewidth=1, alpha=0.6)
    ax.text(hist_dates.iloc[0], baseline + 0.3,
            f"Baseline LUR ({baseline:.1f} µg/m³)", fontsize=8, color="#4dac26")

    # ── Formato de fechas ──
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)

    ax.set_xlabel("Mes", fontsize=11)
    ax.set_ylabel(f"{target} (µg/m³)", fontsize=11)
    ax.set_title(
        f"Evolución temporal {target} — {lsoa_name}\n"
        f"(ST-LUR de dos etapas | IC 90 % bootstrap)",
        fontsize=13, fontweight="bold",
    )
    ax.legend(loc="upper right", framealpha=0.85, fontsize=9)
    ax.grid(True, alpha=0.25, linestyle="--")

    plt.tight_layout()

    if save:
        tag  = target.replace(".", "")
        out  = FIG_DIR / f"stlur_{tag}_{lsoa_id}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log.info("Gráfico guardado → %s", out)

    return fig


def plot_multi_lsoa(
    model: STLURModel,
    lsoa_preds: pd.DataFrame,
    meteo_2024: pd.DataFrame,
    lsoa_ids: list[str],
    n_boot: int = 300,
    save: bool = True,
) -> plt.Figure:
    """
    Gráfico de comparación multi-LSOA en un solo panel.
    Útil para visualizar varios barrios ciegas simultáneamente.
    """
    pm_col = f"{model.target}_pred"
    cmap   = plt.cm.get_cmap("tab10", len(lsoa_ids))

    fig, ax = plt.subplots(figsize=(16, 7))
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#fafafa")

    meteo_ext    = add_temporal_features(meteo_2024)
    meteo_future = build_future_meteo(meteo_2024)
    all_meteo    = pd.concat([meteo_ext, meteo_future], ignore_index=True)
    all_dates    = pd.to_datetime(all_meteo["year_month"] + "-01")
    n_hist       = len(meteo_ext)

    for i, lid in enumerate(lsoa_ids):
        col_final = f"{model.target}_final"
        row = lsoa_preds[lsoa_preds["LSOA21CD"] == lid]
        if row.empty:
            continue
        baseline  = float(row.iloc[0][col_final])
        lsoa_name = row.iloc[0].get("LSOA21NM", lid)
        tf        = model.predict_temporal_factor(all_meteo)
        pm_pred   = baseline * tf

        color = cmap(i)
        ax.plot(all_dates[:n_hist], pm_pred[:n_hist],
                "o-", color=color, linewidth=1.8, markersize=4)
        ax.plot(all_dates[n_hist - 1:], pm_pred[n_hist - 1:],
                "s--", color=color, linewidth=1.8, markersize=7,
                label=lsoa_name)

    ax.axvline(all_dates.iloc[n_hist - 1] + pd.Timedelta(days=15),
               color="gray", linestyle=":", alpha=0.6, linewidth=1.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)

    ax.set_xlabel("Mes", fontsize=11)
    ax.set_ylabel(f"{model.target} (µg/m³)", fontsize=11)
    ax.set_title(
        f"Comparación multi-barrio — {model.target}\n"
        f"(barrios sin sensor | ST-LUR de dos etapas)",
        fontsize=13, fontweight="bold",
    )
    ax.legend(loc="upper right", fontsize=8, framealpha=0.85)
    ax.grid(True, alpha=0.25, linestyle="--")
    plt.tight_layout()

    if save:
        tag = model.target.replace(".", "")
        out = FIG_DIR / f"stlur_{tag}_multi.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        log.info("Gráfico multi-LSOA guardado → %s", out)

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Ejecución completa del pipeline ST-LUR
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("=== ST-LUR Forecast Pipeline ===")

    # ── 1. Cargar datos ──────────────────────────────────────────────────────
    sensors, meteo, lsoa_preds = load_all_temporal_data()

    # ── 2. Entrenar modelos temporales (PM2.5 y PM10) ────────────────────────
    models = {}
    for target in TARGETS:
        col_final = f"{target}_final"
        if col_final not in lsoa_preds.columns:
            log.warning("Columna '%s' no encontrada en lur_barrios_predictions.csv — saltando %s",
                        col_final, target)
            continue
        m = STLURModel(target=target).fit(sensors, meteo)
        m.save()
        models[target] = m

    if not models:
        log.error("Ningún modelo pudo entrenarse. Revisa las columnas en lur_barrios_predictions.csv.")
        return

    # ── 3. Ejemplo: proyección histórica + pronóstico para 3 LSOAs de prueba ─
    example_ids = lsoa_preds["LSOA21CD"].dropna().head(3).tolist()
    log.info("Generando ejemplos para LSOAs: %s", example_ids)

    target_demo = "PM2.5"
    if target_demo in models:
        model_demo = models[target_demo]
        for lid in example_ids:
            historical = project_historical(lid, model_demo, lsoa_preds, meteo)
            forecast   = forecast_lsoa(lid, model_demo, lsoa_preds, meteo)
            plot_curve(historical, forecast, target=target_demo)

        # ── Gráfico multi-LSOA ──
        plot_multi_lsoa(model_demo, lsoa_preds, meteo, lsoa_ids=example_ids)

    # ── 4. Exportar predicciones completas para los 302 LSOAs ─────────────
    dfs: dict[str, pd.DataFrame] = {}
    for t in TARGETS:
        if t in models:
            log.info("Generando predicciones %s para todos los LSOAs (puede tardar ~2 min)...", t)
            dfs[t] = forecast_all_lsoas(models[t], lsoa_preds, meteo, save=False)
            log.info("  %s: %d filas para %d LSOAs", t, len(dfs[t]), dfs[t]["lsoa_id"].nunique())

    if dfs:
        base = dfs.get("PM2.5", next(iter(dfs.values())))
        if "PM2.5" in dfs and "PM10" in dfs:
            base = base.merge(
                dfs["PM10"][["lsoa_id", "year_month", "type", "PM10_pred"]],
                on=["lsoa_id", "year_month", "type"],
                how="left",
            )
        out_path = ROOT / "outputs" / "stlur_predictions.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        base.to_csv(out_path, index=False)
        log.info("CSV final exportado → %s (%d filas, cols: %s)",
                 out_path, len(base), list(base.columns))

    log.info("=== Pipeline ST-LUR completado ===")


if __name__ == "__main__":
    main()
