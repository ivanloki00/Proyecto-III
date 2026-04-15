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

from sklearn.linear_model import LinearRegression, RidgeCV, ElasticNetCV  # E3
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.cluster import KMeans                                          # E1
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor

from scipy.spatial.distance import squareform, pdist

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[2]
DATA_INT  = ROOT / "data" / "interim"
OUT_DIR    = ROOT / "data" / "processed" / "LUR"          # CSVs de resultados
MODELS_DIR = ROOT / "outputs" / "models"       # modelos .pkl
FIG_DIR    = ROOT / "outputs" / "figures" / "lur"  # imágenes diagnóstico
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_CSV = DATA_INT / "lur_features.csv"
SENSORS_GPKG = DATA_INT / "sensores_snapped.gpkg"
MONTHLY_CSV  = DATA_INT / "sensores_monthly.csv"
METEO_CSV    = DATA_INT / "meteo_monthly.csv"
ELEV_CSV     = DATA_INT / "sensor_elevation.csv"

BUFFER_RADII   = [50, 100, 250, 500, 1000]
TARGETS        = ["PM2.5", "PM10"]
VIF_THRESHOLD  = 10.0
P_THRESHOLD    = 0.10   # relajado un poco dado n=20
USE_PANEL      = True   # True → entrenar sobre datos mensuales (n~240 vs n=20)

# Variables base que SÍ dependen del radio del buffer (se someten a selección de escala)
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
    "traffic_weighted_exposure",
    "intersections_count",
]

# Variables de sensor que NO dependen del buffer (propiedad del punto, no del entorno)
# CORRECCIÓN A2: dist_industrial_m y dist_centre_m son idénticas para los 4 buffers
# del mismo sensor. No tiene sentido "seleccionar escala" para ellas — se añaden
# directamente como candidatas al filtro p-value/VIF sin pasar por select_best_buffer.
SENSOR_LEVEL_VARS = [
    "dist_industrial_m",
    "dist_centre_m",
    # C3 — fuentes puntuales
    "dist_port_m",
    "dist_tunnel_m",
    "dist_station_m",
    "dist_airport_m",
    "elevation_m",
    # C4 — densidad de población LSOA
    "pop_density_km2",
]


# ═══════════════════════════════════════════════════
# 0. Panel: fusión de datos mensuales + espaciales
# ═══════════════════════════════════════════════════

def build_panel_dataset(df_spatial: pd.DataFrame, target: str) -> pd.DataFrame:
    """
    Construye el dataset panel fusionando:
      - df_spatial    : features espaciales (1 fila/sensor) de select_best_buffer
      - sensores_monthly.csv : observaciones mensuales (sensor × mes)
      - meteo_monthly.csv   : controles meteo (temperatura, viento, lluvia) por mes
      - sensor_elevation.csv: elevación por sensor

    Resultado: ~20 sensores × ~12 meses = ~240 filas.
    Si algún archivo no existe, avisa y devuelve df_spatial sin cambios.
    """
    if not MONTHLY_CSV.exists():
        log.warning("  [PANEL] sensores_monthly.csv no encontrado — usando datos anuales (n=20)")
        return df_spatial

    df_monthly = pd.read_csv(MONTHLY_CSV)
    if target not in df_monthly.columns:
        log.warning(f"  [PANEL] '{target}' no encontrado en sensores_monthly.csv — usando datos anuales")
        return df_spatial

    # Quitar columnas target anuales para no contaminar el join
    drop_targets = [t for t in ["PM2.5", "PM10"] if t in df_spatial.columns]
    df_space = df_spatial.drop(columns=drop_targets)

    # Join: observaciones mensuales + features espaciales
    df_panel = df_monthly[["sensor_id", "year_month", target]].merge(
        df_space, on="sensor_id", how="inner"
    )
    log.info(f"  [PANEL] Join espacial: {len(df_panel)} filas ({df_panel['sensor_id'].nunique()} sensores)")

    # Controles meteorológicos (temperatura, viento, lluvia)
    if METEO_CSV.exists():
        df_meteo = pd.read_csv(METEO_CSV)[
            ["year_month", "air_temperature_mean", "wind_speed_mean", "rain_days"]
        ]
        df_panel = df_panel.merge(df_meteo, on="year_month", how="left")
        n_meteo = df_panel["wind_speed_mean"].notna().sum()
        log.info(f"  [PANEL] Meteo mergeada: {n_meteo}/{len(df_panel)} filas con datos")

    # Codificación cíclica del mes — controla estacionalidad
    if "year_month" in df_panel.columns:
        df_panel["month_num"] = pd.to_datetime(df_panel["year_month"]).dt.month
        df_panel["mes_sin"] = np.sin(2 * np.pi * df_panel["month_num"] / 12)
        df_panel["mes_cos"] = np.cos(2 * np.pi * df_panel["month_num"] / 12)
        df_panel.drop(columns=["month_num"], inplace=True)
        log.info("  [PANEL] Estacionalidad cíclica añadida: mes_sin, mes_cos")

    # Elevación del sensor — sólo añadir si no viene ya de df_space
    if "elevation_m" not in df_panel.columns and ELEV_CSV.exists():
        df_elev = pd.read_csv(ELEV_CSV)[["sensor_id", "elevation_m"]]
        df_panel = df_panel.merge(df_elev, on="sensor_id", how="left")
    if "elevation_m" in df_panel.columns:
        med_elev = df_panel["elevation_m"].median()
        df_panel["elevation_m"] = df_panel["elevation_m"].fillna(med_elev)

    log.info(
        f"  [PANEL] Dataset final: {len(df_panel)} filas, "
        f"{df_panel['sensor_id'].nunique()} sensores, "
        f"columnas={list(df_panel.columns)}"
    )
    return df_panel


# ═══════════════════════════════════════════════════
# 1. Selección de escala óptima por variable
# ═══════════════════════════════════════════════════

def select_best_buffer(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """
    Para cada variable de BASE_VARS, elige el buffer con la mayor |correlación| con target.
    Las variables de SENSOR_LEVEL_VARS se añaden directamente (no dependen del buffer).
    Devuelve un DataFrame de N filas (1 por sensor) con las mejores variables.
    """
    log.info(f"  Seleccionando escala óptima para {target} ...")

    best_records = {}   # col_name -> (best_buffer, base_var, corr)

    # ── Variables con escala de buffer ──────────────────────────────
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
                "sensor_level": False,
            }

    # ── CORRECCIÓN A2: variables sin buffer — se toman del primer buffer (son idénticas) ──
    base_buf = BUFFER_RADII[0]
    for var in SENSOR_LEVEL_VARS:
        sub = df[df["buffer_m"] == base_buf]
        if var not in sub.columns or sub[var].std() == 0:
            continue
        corr = abs(sub[[var, target]].corr().iloc[0, 1])
        if not np.isnan(corr) and corr > 0.05:
            best_records[var] = {
                "buffer": base_buf,
                "base_var": var,
                "corr": corr,
                "sensor_level": True,
            }
            log.info(f"  Variable sensor-level '{var}': |r|={corr:.3f} (sin selección de escala)")

    log.info(f"  Variables retenidas tras selección de escala: {len(best_records)}")

    # ── Integrar densidad de población si está disponible ────────────
    pop_csv = ROOT / "data" / "interim" / "population_density.csv"
    if pop_csv.exists():
        df_pop = pd.read_csv(pop_csv)[["sensor_id", "pop_density_km2"]]
        df = df.merge(df_pop, on="sensor_id", how="left")
        df["pop_density_km2"] = df["pop_density_km2"].fillna(df["pop_density_km2"].median())
        log.info(f"  Densidad de población integrada: {df['pop_density_km2'].notna().sum()} filas")
    else:
        log.warning("  population_density.csv no encontrado — omitiendo pop_density_km2")

    # ── Construir tabla pivotada: sensor × mejor variable ───────────
    pivot_rows = []
    for _, row_sensor in df[df["buffer_m"] == BUFFER_RADII[0]].iterrows():
        sid = row_sensor["sensor_id"]
        record = {"sensor_id": sid, target: row_sensor[target]}
        for col_name, info in best_records.items():
            buf_row = df[(df["sensor_id"] == sid) & (df["buffer_m"] == info["buffer"])].iloc[0]
            record[col_name] = buf_row[info["base_var"]]
        pivot_rows.append(record)

    result = pd.DataFrame(pivot_rows)

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

def loocv(model_class, X: np.ndarray, y: np.ndarray, log_transform: bool = False, **kwargs) -> dict:
    """
    LOOCV genérico. Si log_transform=True, entrena sobre log(y) y back-transforma con exp.
    Soporta instancias pre-construidas (e.g. RidgeCV) pasando model_class=None y kwarg instance=<obj>.
    """
    loo = LeaveOneOut()
    y_pred = np.zeros_like(y, dtype=float)
    y_train_target = np.log(y) if log_transform else y

    for train_idx, test_idx in loo.split(X):
        if model_class is None:
            # Se reutiliza la clase pasada como kwarg 'instance_factory'
            m = kwargs["instance_factory"]()
        else:
            m = model_class(**{k: v for k, v in kwargs.items() if k != "instance_factory"})
        m.fit(X[train_idx], y_train_target[train_idx])
        raw_pred = m.predict(X[test_idx])
        y_pred[test_idx] = np.exp(raw_pred) if log_transform else raw_pred

    r2   = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return {"r2_cv": r2, "rmse_cv": rmse, "y_pred": y_pred}


# ═══════════════════════════════════════════════════
# 3b. Leave-One-Sensor-Out CV (para datos panel)
# ═══════════════════════════════════════════════════

def loocv_panel(model_class, X: np.ndarray, y: np.ndarray,
                sensor_ids: np.ndarray, **kwargs) -> dict:
    """
    Leave-One-Sensor-Out CV para datos panel.
    Deja fuera TODAS las observaciones de un sensor a la vez — evita
    fuga de información temporal entre meses del mismo sensor.

    Parámetros opcionales para spatial lag (anti-data-leakage):
      coords (np.ndarray (n_sensores, 2)): coordenadas BNG de cada sensor único
                                           (mismo orden que unique_sensors)
      sensor_pm_map (dict sensor_id → np.ndarray): PM de ese sensor para cada
                                                   fila del panel (indexado globalmente)
      k_neighbors (int): vecinos para el lag, default 3
    """
    unique_sensors = np.unique(sensor_ids)
    y_pred = np.zeros_like(y, dtype=float)

    coords        = kwargs.get("coords", None)
    sensor_pm_map = kwargs.get("sensor_pm_map", None)
    k_neighbors   = kwargs.get("k_neighbors", 3)
    use_spatial_lag = (
        coords is not None
        and sensor_pm_map is not None
        and len(coords) == len(unique_sensors)
    )

    if use_spatial_lag:
        log.info(f"  [LOOCV-PANEL] Spatial lag activado (k={k_neighbors})")
        coord_map = {s: coords[i] for i, s in enumerate(unique_sensors)}

    for sid in unique_sensors:
        test_mask  = sensor_ids == sid
        train_mask = ~test_mask
        if train_mask.sum() < 2:
            y_pred[test_mask] = y[train_mask].mean() if train_mask.sum() > 0 else y.mean()
            continue

        X_train = X[train_mask].copy()
        X_test  = X[test_mask].copy()

        if use_spatial_lag:
            train_sensors    = [s for s in unique_sensors if s != sid]
            test_coord       = coord_map[sid]
            train_coords_arr = np.array([coord_map[s] for s in train_sensors])

            # Distancias del sensor test a cada sensor de entrenamiento
            dists = np.sqrt(((train_coords_arr - test_coord) ** 2).sum(axis=1))
            k_eff = min(k_neighbors, len(train_sensors))
            nn_sensors = [train_sensors[i] for i in np.argsort(dists)[:k_eff]]

            # Lag del sensor test: media de PM de k vecinos más cercanos (por fila global)
            # ANTI-LEAKAGE: sólo se usan PM de sensores en el training set
            test_indices = np.where(test_mask)[0]
            fallback_mean = np.nanmean(y[train_mask])
            test_lag = np.array([
                np.nanmean([sensor_pm_map[ns][gi] for ns in nn_sensors
                            if ns in sensor_pm_map
                            and not np.isnan(sensor_pm_map[ns][gi])]
                           ) if any(
                               not np.isnan(sensor_pm_map[ns][gi])
                               for ns in nn_sensors if ns in sensor_pm_map
                           )
                else fallback_mean
                for gi in test_indices
            ])

            # Lag de cada fila de entrenamiento: media de sus k vecinos (sin incluirse a sí mismo)
            train_indices = np.where(train_mask)[0]
            train_lag = np.zeros(len(train_indices))
            for row_i, gi in enumerate(train_indices):
                s_i   = sensor_ids[gi]
                peers = [s for s in train_sensors if s != s_i]
                if not peers:
                    peers = train_sensors  # fallback si sólo hay 1 sensor en training
                peer_dists = np.sqrt((
                    (np.array([coord_map[p] for p in peers]) - coord_map[s_i]) ** 2
                ).sum(axis=1))
                k2  = min(k_neighbors, len(peers))
                nn2 = [peers[j] for j in np.argsort(peer_dists)[:k2]]
                vals = [
                    sensor_pm_map[ns][gi]
                    for ns in nn2
                    if ns in sensor_pm_map and not np.isnan(sensor_pm_map[ns][gi])
                ]
                train_lag[row_i] = np.nanmean(vals) if vals else fallback_mean

            # Concatenar spatial lag como última columna
            X_train = np.column_stack([X_train, train_lag])
            X_test  = np.column_stack([X_test,  test_lag])

        # Excluir kwargs internos antes de pasar al modelo
        _model_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ("instance_factory", "coords", "sensor_pm_map", "k_neighbors")
        }
        if model_class is None:
            m = kwargs["instance_factory"]()
        else:
            m = model_class(**_model_kwargs)
        m.fit(X_train, y[train_mask])
        y_pred[test_mask] = m.predict(X_test)

    r2   = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return {"r2_cv": r2, "rmse_cv": rmse, "y_pred": y_pred}


# ═══════════════════════════════════════════════════
# E1. Spatial Cross-Validation (Leave-Cluster-Out)
# ═══════════════════════════════════════════════════

def spatial_cv(model_class, X: np.ndarray, y: np.ndarray,
               coords: np.ndarray, n_clusters: int = 4, **kwargs) -> dict:
    """
    Leave-Cluster-Out CV: agrupa los sensores en n_clusters zonas geográficas
    mediante K-Means y deja fuera un cluster entero en cada fold.

    Esto es más honesto que LOOCV cuando los sensores están espacialmente
    agrupados: el modelo no puede "ver" el entorno geográfico del punto test.

    Args:
        n_clusters: número de grupos espaciales. Con n=20 sensores, 4 clusters
                    → ~5 sensores por fold. Con n>40 usar 5-6 clusters.
    """
    if len(y) < n_clusters * 2:
        log.warning(f"  Spatial CV: n={len(y)} muy pequeño para {n_clusters} clusters → usando LOOCV")
        return loocv(model_class, X, y, **kwargs)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = km.fit_predict(coords)

    y_pred = np.zeros_like(y, dtype=float)
    for cluster_id in range(n_clusters):
        test_mask  = cluster_labels == cluster_id
        train_mask = ~test_mask
        if train_mask.sum() < 3:
            # Cluster con muy pocos datos de entrenamiento → saltar
            y_pred[test_mask] = y[train_mask].mean()
            continue
        if model_class is None:
            m = kwargs["instance_factory"]()
        else:
            m = model_class(**{k: v for k, v in kwargs.items() if k != "instance_factory"})
        m.fit(X[train_mask], y[train_mask])
        y_pred[test_mask] = m.predict(X[test_mask])

    r2   = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    log.info(f"  Spatial CV ({n_clusters} clusters): R²={r2:.4f}, RMSE={rmse:.3f}")
    return {"r2_cv": r2, "rmse_cv": rmse, "y_pred": y_pred, "method": "spatial_cv"}


# ═══════════════════════════════════════════════════
# E2. Bootstrap Prediction Intervals
# ═══════════════════════════════════════════════════

def bootstrap_prediction_intervals(
    model_class, X_train: np.ndarray, y_train: np.ndarray,
    X_pred: np.ndarray, n_boot: int = 200,
    alpha: float = 0.10, **kwargs
) -> dict:
    """
    Intervalos de predicción via bootstrap paramétrico.

    Procedimiento:
      1. Para cada iteración b: muestrear n sensores con reemplazo, ajustar modelo.
      2. Predecir X_pred con el modelo b.
      3. El intervalo (1-alpha) se obtiene de los percentiles de las B predicciones.

    Returns dict con claves: mean, lower, upper (arrays de len X_pred)
    """
    rng = np.random.default_rng(42)
    n   = len(y_train)
    preds = np.zeros((n_boot, len(X_pred)))

    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        Xb, yb = X_train[idx], y_train[idx]
        if len(np.unique(yb)) < 2:
            preds[b] = y_train.mean()
            continue
        if model_class is None:
            m = kwargs["instance_factory"]()
        else:
            m = model_class(**{k: v for k, v in kwargs.items() if k != "instance_factory"})
        try:
            m.fit(Xb, yb)
            preds[b] = m.predict(X_pred)
        except Exception:
            preds[b] = y_train.mean()

    lo = np.percentile(preds, 100 * alpha / 2,     axis=0)
    hi = np.percentile(preds, 100 * (1 - alpha/2), axis=0)
    mu = preds.mean(axis=0)
    log.info(f"  Bootstrap ({n_boot} iter, α={alpha}): intervalo medio ±{(hi-lo).mean()/2:.2f} µg/m³")
    return {"mean": mu, "lower": lo, "upper": hi}


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

    out_path = FIG_DIR / f"diagnostics_{target.replace('.','')}.png"
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
    comparison_rows = []

    for target in TARGETS:
        log.info(f"\n{'#'*60}\n  TARGET: {target}\n{'#'*60}")

        # ── 5.1  Selección de escala ──
        df_best = select_best_buffer(df_all, target)

        # ── 5.2  Filtro p-value — sobre medias anuales por sensor (señal espacial pura) ──
        # IMPORTANTE: la selección de features usa SIEMPRE n=20 (1 fila por sensor),
        # no el panel completo. Razón: el LUR captura variación ESPACIAL entre sensores.
        # Si filtramos sobre n=217, el test de p-value detecta también variación TEMPORAL
        # (estacional) dentro de cada sensor, seleccionando features espurias que no
        # generalizan a nuevas ubicaciones.
        spatial_feature_cols = [c for c in df_best.columns
                                 if c not in ("sensor_id", "PM2.5", "PM10")]
        X_spatial = df_best[spatial_feature_cols].copy()
        y_spatial = df_best[target].copy()

        # Centinela de distancias sobre datos anuales (mismo criterio que antes)
        X_spatial = X_spatial.replace([np.inf, -np.inf], np.nan)
        for dc in [c for c in X_spatial.columns if c.startswith("dist_")]:
            max_val = X_spatial[dc].max()
            fill_val = max_val * 1.5 if (pd.notna(max_val) and max_val > 0) else 9999.0
            X_spatial[dc] = X_spatial[dc].fillna(fill_val)
        X_spatial = X_spatial.fillna(0)

        kept_pval = filter_by_pvalue(X_spatial, y_spatial)
        if len(kept_pval) == 0:
            log.warning(f"  Ninguna variable significativa para {target}. Usando top 5 por |correlación|.")
            corrs = X_spatial.corrwith(y_spatial).abs().sort_values(ascending=False)
            kept_pval = corrs.head(5).index.tolist()

        # ── 5.3  Filtro VIF — también sobre medias anuales ──
        final_vars_spatial = filter_by_vif(X_spatial[kept_pval])
        if len(final_vars_spatial) == 0:
            final_vars_spatial = kept_pval[:1]

        log.info(f"  Variables espaciales seleccionadas para {target}: {final_vars_spatial}")

        # ── 5.0  PANEL: construir dataset con las features espaciales ya seleccionadas ──
        # Controles temporales (meteo) se añaden siempre como controles, no pasan por
        # el filtro de selección — son confounders conocidos, no predictores LUR.
        METEO_CONTROLS = ["air_temperature_mean", "wind_speed_mean", "rain_days",
                          "mes_sin", "mes_cos"]

        if USE_PANEL:
            df_work = build_panel_dataset(df_best, target)
        else:
            df_work = df_best.copy()

        is_panel = "year_month" in df_work.columns
        if is_panel:
            sensor_ids_arr = df_work["sensor_id"].values
            # features = LUR espaciales seleccionadas + controles meteo presentes en el panel
            meteo_present = [c for c in METEO_CONTROLS if c in df_work.columns]
            final_vars = final_vars_spatial + meteo_present
            log.info(
                f"  [PANEL] n={len(df_work)} ({df_work['sensor_id'].nunique()} sensores × meses) | "
                f"features LUR: {final_vars_spatial} | controles meteo: {meteo_present}"
            )
        else:
            sensor_ids_arr = None
            final_vars = final_vars_spatial
            log.info(f"  [ANUAL] n={len(df_work)}")

        # Construir X e y finales sobre el dataset de trabajo (panel o anual)
        # Columnas faltantes en df_work (ej: feature espacial no mergeada) → 0
        missing = [v for v in final_vars if v not in df_work.columns]
        if missing:
            log.warning(f"  Variables no encontradas en df_work, se imputan a 0: {missing}")
            for m in missing:
                df_work[m] = 0.0

        X_final = df_work[final_vars].copy()
        y = df_work[target].copy()

        # Eliminar filas sin valor de target (ej: sensores AURN sin PM2.5)
        valid_mask = y.notna()
        if not valid_mask.all():
            n_dropped = (~valid_mask).sum()
            log.info(f"  Filtrando {n_dropped} filas sin {target} (sensores parciales: AURN, etc.)")
            df_work   = df_work[valid_mask.values].reset_index(drop=True)
            X_final   = X_final[valid_mask].reset_index(drop=True)
            y         = y[valid_mask].reset_index(drop=True)
            if sensor_ids_arr is not None:
                sensor_ids_arr = sensor_ids_arr[valid_mask.values]

        # Centinela de distancias (ahora sobre el dataset de trabajo completo)
        X_final = X_final.replace([np.inf, -np.inf], np.nan)
        for dc in [c for c in X_final.columns if c.startswith("dist_")]:
            max_val = X_final[dc].max()
            fill_val = max_val * 1.5 if (pd.notna(max_val) and max_val > 0) else 9999.0
            X_final[dc] = X_final[dc].fillna(fill_val)
        X_final = X_final.fillna(0)

        log.info(f"  Variables finales para {target}: {final_vars}")

        # ── 6.  Entrenamiento — comparación de modelos ──
        X_np = X_final.values
        y_np = y.values

        # ── Preparación de spatial lag (anti-data-leakage) ──────────────────────
        _coords_arr    = None
        _sensor_pm_map = None
        if is_panel:
            try:
                unique_panel_sensors = np.unique(sensor_ids_arr)
                _coords_arr = np.array([
                    (
                        sensors_gdf.loc[sensors_gdf["sensor_id"] == s, "geometry"].values[0].x,
                        sensors_gdf.loc[sensors_gdf["sensor_id"] == s, "geometry"].values[0].y,
                    )
                    if s in sensors_gdf["sensor_id"].values else (np.nan, np.nan)
                    for s in unique_panel_sensors
                ])
                # sensor_pm_map: para cada sensor, su vector de PM indexado globalmente
                # (posiciones que no corresponden al sensor quedan como NaN)
                _sensor_pm_map = {}
                for s in unique_panel_sensors:
                    mask_s = sensor_ids_arr == s
                    pm_arr = np.full(len(y_np), np.nan)
                    pm_arr[mask_s] = y_np[mask_s]
                    _sensor_pm_map[s] = pm_arr
                log.info(
                    f"  [Spatial lag] {len(_coords_arr)} coordenadas cargadas "
                    f"para {target} (k=3)"
                )
            except Exception as _e:
                log.warning(f"  [Spatial lag] Deshabilitado: {_e}")
                _coords_arr    = None
                _sensor_pm_map = None
        # ── Fin preparación spatial lag ─────────────────────────────────────────

        # Función CV según tipo de datos
        def _cv(model_class, **kwargs):
            if is_panel:
                return loocv_panel(
                    model_class, X_np, y_np, sensor_ids_arr,
                    coords=_coords_arr,
                    sensor_pm_map=_sensor_pm_map,
                    k_neighbors=3,
                    **kwargs,
                )
            else:
                return loocv(model_class, X_np, y_np, **kwargs)

        # Definición de candidatos
        ridge_alphas = [0.01, 0.1, 1.0, 10.0, 100.0]

        candidates = {
            "LinearRegression": {
                "res": _cv(LinearRegression),
                "factory": lambda: LinearRegression(),
                "model_type": "linear",
            },
            "Ridge": {
                "res": _cv(None, instance_factory=lambda: RidgeCV(alphas=ridge_alphas, cv=None)),
                "factory": lambda: RidgeCV(alphas=ridge_alphas, cv=None).fit(X_np, y_np),
                "model_type": "linear",
            },
            # E3 — Elastic Net (sin random_state — no es parámetro válido de ElasticNetCV)
            "ElasticNet": {
                "res": _cv(None, instance_factory=lambda: ElasticNetCV(
                    l1_ratio=[0.1, 0.5, 0.7, 0.9, 1.0],
                    alphas=ridge_alphas,
                    cv=min(5, df_work["sensor_id"].nunique() - 1),
                    max_iter=5000,
                )),
                "factory": lambda: ElasticNetCV(
                    l1_ratio=[0.1, 0.5, 0.7, 0.9, 1.0],
                    alphas=ridge_alphas,
                    cv=min(5, df_work["sensor_id"].nunique() - 1),
                    max_iter=5000,
                ).fit(X_np, y_np),
                "model_type": "linear",
            },
            "LogLinear": {
                "res": _cv(LinearRegression, log_transform=True) if not is_panel
                       else loocv_panel(
                           LinearRegression,
                           X_np,
                           np.log(np.clip(y_np, 1e-9, None)),
                           sensor_ids_arr,
                           coords=_coords_arr,
                           sensor_pm_map=_sensor_pm_map,
                           k_neighbors=3,
                       ),
                "factory": lambda: LinearRegression(),
                "model_type": "linear",
            },
            "RandomForest": {
                "res": _cv(RandomForestRegressor, n_estimators=200, max_features="sqrt", random_state=42),
                "factory": lambda: RandomForestRegressor(n_estimators=200, max_features="sqrt", random_state=42),
                "model_type": "ensemble",
            },
            "GradientBoosting": {
                "res": _cv(GradientBoostingRegressor, n_estimators=100, max_depth=3, random_state=42),
                "factory": lambda: GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42),
                "model_type": "ensemble",
            },
            "LogRidge": {
                "res": _cv(None, instance_factory=lambda: RidgeCV(alphas=ridge_alphas, cv=None), log_transform=True) if not is_panel
                       else (lambda _res: dict(_res, y_pred=np.expm1(_res["y_pred"]),
                                               r2_cv=r2_score(y_np, np.expm1(_res["y_pred"])),
                                               rmse_cv=np.sqrt(mean_squared_error(y_np, np.expm1(_res["y_pred"]))))
                             )(loocv_panel(
                                 None,
                                 X_np,
                                 np.log1p(np.clip(y_np, 1e-9, None)),
                                 sensor_ids_arr,
                                 instance_factory=lambda: RidgeCV(alphas=ridge_alphas, cv=None),
                                 coords=_coords_arr,
                                 sensor_pm_map=_sensor_pm_map,
                                 k_neighbors=3,
                             )),
                "factory": lambda: RidgeCV(alphas=ridge_alphas, cv=None),
                "model_type": "linear",
            },
            "SVR": {
                "res": _cv(None, instance_factory=lambda: Pipeline([("scaler", StandardScaler()), ("svr", SVR(kernel="rbf", C=10, epsilon=0.1))])),
                "factory": lambda: Pipeline([("scaler", StandardScaler()), ("svr", SVR(kernel="rbf", C=10, epsilon=0.1))]),
                "model_type": "ensemble",
            },
        }

        for name, info in candidates.items():
            r = info["res"]
            log.info(f"  {name} LOOCV: R²={r['r2_cv']:.4f}, RMSE={r['rmse_cv']:.3f}")

        # Acumular tabla de comparación
        for name, info in candidates.items():
            r = info["res"]
            comparison_rows.append({
                "target": target,
                "model": name,
                "r2_cv": round(r["r2_cv"], 4),
                "rmse_cv": round(r["rmse_cv"], 4),
                "model_type": info["model_type"],
            })

        # ── Selección del ganador ──
        # 1. Modelos lineales con R²_CV > 0.6 → preferir interpretable
        # 2. Si ninguno > 0.6 → mayor R²_CV global
        linear_above_threshold = [
            name for name, info in candidates.items()
            if info["model_type"] == "linear" and info["res"]["r2_cv"] > 0.6
        ]
        if linear_above_threshold:
            best_name = max(linear_above_threshold,
                            key=lambda n: candidates[n]["res"]["r2_cv"])
            log.info(f"  Criterio: lineal con R²>0.6 → {best_name}")
        else:
            best_name = max(candidates.keys(),
                            key=lambda n: candidates[n]["res"]["r2_cv"])
            log.info(f"  Criterio: mayor R²_CV global → {best_name}")

        best_res = candidates[best_name]["res"]
        best_model = candidates[best_name]["factory"]()
        # Si el factory ya devuelve un modelo ajustado (Ridge), úsalo directamente;
        # en otro caso, ajustar sobre todos los datos
        if not hasattr(best_model, "coef_"):
            if best_name == "LogLinear":
                best_model.fit(X_np, np.log(y_np))
            else:
                best_model.fit(X_np, y_np)

        log.info(f"  Modelo elegido para {target}: {best_name} "
                 f"(R²_CV={best_res['r2_cv']:.4f}, RMSE_CV={best_res['rmse_cv']:.3f})")

        # ── E1: Spatial Cross-Validation ──────────────────────────────────────
        log.info(f"  Ejecutando Spatial CV (Leave-Cluster-Out) para {target} ...")
        if is_panel:
            # Para panel: cluster a nivel sensor, luego dejar fuera todas las filas del cluster
            unique_sids = np.unique(sensor_ids_arr)
            sid_coord_map = {}
            for sid in unique_sids:
                matches = sensors_gdf[sensors_gdf["sensor_id"] == sid]
                if len(matches) > 0:
                    sid_coord_map[sid] = (matches.geometry.iloc[0].x, matches.geometry.iloc[0].y)
            sensor_coords_arr = np.array([sid_coord_map.get(s, (0.0, 0.0)) for s in unique_sids])
            n_clust = min(4, max(2, len(unique_sids) // 5))
            km_s = KMeans(n_clusters=n_clust, random_state=42, n_init=10)
            sensor_cluster_labels = km_s.fit_predict(sensor_coords_arr)
            sensor_cluster_map = {sid: sensor_cluster_labels[i] for i, sid in enumerate(unique_sids)}
            row_clusters = np.array([sensor_cluster_map[s] for s in sensor_ids_arr])
            sp_pred = np.zeros_like(y_np, dtype=float)
            for cid in range(n_clust):
                tmask = row_clusters == cid
                trmask = ~tmask
                if trmask.sum() < 3:
                    sp_pred[tmask] = y_np[trmask].mean()
                    continue
                m_sp = RidgeCV(alphas=ridge_alphas, cv=None)
                m_sp.fit(X_np[trmask], y_np[trmask])
                sp_pred[tmask] = m_sp.predict(X_np[tmask])
            spatial_res = {
                "r2_cv": r2_score(y_np, sp_pred),
                "rmse_cv": np.sqrt(mean_squared_error(y_np, sp_pred)),
            }
            log.info(f"  Spatial CV panel ({n_clust} clusters): R²={spatial_res['r2_cv']:.4f}")
        else:
            spatial_res = spatial_cv(
                None, X_np, y_np, coords,
                n_clusters=min(4, max(2, len(y_np) // 5)),
                instance_factory=lambda: RidgeCV(alphas=ridge_alphas, cv=None),
            )
        log.info(
            f"  Spatial CV R²={spatial_res['r2_cv']:.4f}  vs  "
            f"LOOCV R²={best_res['r2_cv']:.4f}  "
            f"(diferencia: {best_res['r2_cv'] - spatial_res['r2_cv']:+.4f})"
        )

        # ── E2: Bootstrap prediction intervals ──
        log.info(f"  Calculando intervalos bootstrap para {target} ...")
        boot_intervals = bootstrap_prediction_intervals(
            None, X_np, y_np, X_np,
            n_boot=200,
            instance_factory=lambda: RidgeCV(alphas=ridge_alphas, cv=None),
        )

        # ── 7.  Diagnóstico OLS ──
        ols_model, residuals, bp_pval = diagnostics_ols(X_final, y, "Lineal", target)

        # Moran's I — para panel, promediar residuos por sensor antes
        if is_panel:
            res_df = pd.DataFrame({"sensor_id": df_work["sensor_id"].values,
                                   "residual": residuals.values})
            res_by_sensor = res_df.groupby("sensor_id")["residual"].mean()
            morans_sids = [s for s in sensors_gdf["sensor_id"] if s in res_by_sensor.index]
            morans_resids = np.array([res_by_sensor[s] for s in morans_sids])
            morans_coords = np.array([
                [sensors_gdf[sensors_gdf["sensor_id"] == s].geometry.iloc[0].x,
                 sensors_gdf[sensors_gdf["sensor_id"] == s].geometry.iloc[0].y]
                for s in morans_sids
            ])
            moran = morans_i(morans_resids, morans_coords)
        else:
            moran = morans_i(residuals.values, coords)

        # ── Gráficos (usando ganador vs lineal base) ──
        lr_res = candidates["LinearRegression"]["res"]
        rf_res = candidates["RandomForest"]["res"]
        plot_diagnostics(
            y_np, lr_res["y_pred"], rf_res["y_pred"], residuals.values,
            target, lr_res["r2_cv"], rf_res["r2_cv"],
            lr_res["rmse_cv"], rf_res["rmse_cv"]
        )

        # Guardar modelo
        model_info = {
            "model":       best_model,
            "model_name":  best_name,
            "model_type":  candidates[best_name]["model_type"],
            "features":    final_vars,
            "target":      target,
            "r2_cv":       best_res["r2_cv"],
            "rmse_cv":     best_res["rmse_cv"],
            "bp_pvalue":   bp_pval,
            "moran_I":     moran["I"],
            "moran_p":     moran["p_value"],
            "r2_spatial_cv":   spatial_res["r2_cv"],
            "rmse_spatial_cv": spatial_res["rmse_cv"],
            "bootstrap_lower": boot_intervals["lower"],
            "bootstrap_upper": boot_intervals["upper"],
            "is_panel":    is_panel,
            "n_obs":       len(y_np),
            "n_sensors":   df_work["sensor_id"].nunique(),
        }
        tag = target.replace(".", "")
        pkl_path = MODELS_DIR / f"lur_model_{tag}.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump(model_info, f)
        log.info(f"  Modelo guardado -> {pkl_path}")

        results[target] = {
            "model_info": model_info,
            "df_best":    df_work,
            "final_vars": final_vars,
        }

    # -- Tabla de comparacion de modelos --
    comp_df = pd.DataFrame(comparison_rows).sort_values(["target", "r2_cv"], ascending=[True, False])
    comp_path = OUT_DIR / "model_comparison.csv"
    comp_df.to_csv(comp_path, index=False)
    log.info(f"  Tabla comparativa guardada -> {comp_path}")

    # -- Resumen final --
    log.info(f"\n{'='*60}\n  RESUMEN FINAL\n{'='*60}")
    for t, r in results.items():
        mi = r["model_info"]
        panel_str = f"(panel n={mi['n_obs']}, {mi['n_sensors']} sensores)" if mi.get("is_panel") else "(anual)"
        log.info(
            f"  {t} {panel_str}: {mi['model_name']} | "
            f"R2_CV={mi['r2_cv']:.4f} | RMSE_CV={mi['rmse_cv']:.3f} | "
            f"BP_p={mi['bp_pvalue']:.4f} | Moran_I={mi['moran_I']:.4f} (p={mi['moran_p']:.4f})"
        )
    log.info(f"\n  Comparacion completa:\n{comp_df.to_string(index=False)}")

    return results


if __name__ == "__main__":
    main()
