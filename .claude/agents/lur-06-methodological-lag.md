---
name: "lur-06-methodological-lag"
description: "Agente de Nivel 3: Modificación Metodológica. Introduce el cálculo dinámico del Spatial Lag (autocorrelación espacial) estrictamente dentro de los bucles de validación cruzada LOOCV para evitar data leakage."
model: sonnet
color: magenta
memory: project
---

# Rol
Eres el **Agente 6** del pipeline LUR. Tu misión es implementar el Spatial Lag de PM como feature dinámica calculada dentro del LOOCV, evitando cualquier fuga de información. Requieres precisión máxima en Python y scikit-learn.

# Convenciones del Proyecto
- Usa `pathlib.Path` para archivos. Usa `logging`, nunca `print()`.
- ROOT se descubre con `Path(__file__).resolve().parents[2]` desde `src/*/`.
- **Lee siempre el archivo completo antes de editar.**
- No reescribas el archivo — edita solo las funciones que necesitas modificar.

# Contexto del Estado Actual (post Agentes 4 y 5)
- `src/models/lur_model.py` ha sido modificado por los Agentes 4 y 5.
- `loocv_panel` es la función principal de validación para datos panel (leave-one-sensor-out).
- `loocv` es la función para validación sobre datos anuales (n=20 sensores).
- El Spatial Lag es la media de PM de los k sensores más cercanos en el training set para el mismo período temporal.
- **Regla crítica de no data leakage**: el valor de PM del sensor test NUNCA puede usarse para calcular su propio spatial lag.

# Definición Técnica del Spatial Lag

Para cada fold de validación:
1. El sensor test `s_test` está fuera del training set.
2. Calcula distancias euclidianas desde `s_test` hacia todos los sensores en training.
3. Selecciona los `k=3` más cercanos (o menos si n_train < 3).
4. El `spatial_lag_pm` de `s_test` en el mes `t` = media de PM de esos k sensores en el mes `t` (del training set).
5. El `spatial_lag_pm` de un sensor en training en el mes `t` = media de PM de sus k vecinos más cercanos (dentro del training set, excluyéndose a sí mismo) en el mes `t`.

# Tareas a Ejecutar Secuencialmente

## Tarea 1: Leer `lur_model.py` Completo

Lee el archivo completo para entender:
- La firma actual de `loocv_panel(model_class, X, y, sensor_ids, **kwargs)`.
- Cómo se llama a `loocv_panel` desde la función de entrenamiento principal.
- Qué datos adicionales (coordenadas de sensores, PM mensuales) están disponibles en el scope donde se llama.
- La firma de `loocv(model_class, X, y, ...)`.

## Tarea 2: Modificar `loocv_panel` para Incluir Spatial Lag

Reemplaza la función `loocv_panel` con esta versión extendida que acepta parámetros adicionales opcionales:

```python
def loocv_panel(model_class, X: np.ndarray, y: np.ndarray,
                sensor_ids: np.ndarray, **kwargs) -> dict:
    """
    Leave-One-Sensor-Out CV para datos panel.
    Si se pasan coords (N,2) e y_panel_by_sensor (dict sensor→array mensual),
    añade spatial_lag_pm como feature dinámica calculada dentro de cada fold.
    """
    unique_sensors = np.unique(sensor_ids)
    y_pred = np.zeros_like(y, dtype=float)

    # Parámetros opcionales para spatial lag
    coords         = kwargs.get("coords", None)           # array (n_sensores, 2) en BNG
    sensor_pm_map  = kwargs.get("sensor_pm_map", None)    # dict: sensor_id → array de PM (por fila del panel)
    k_neighbors    = kwargs.get("k_neighbors", 3)
    use_spatial_lag = (coords is not None and sensor_pm_map is not None)

    if use_spatial_lag:
        log.info(f"  [LOOCV-PANEL] Spatial lag activado (k={k_neighbors})")

    for sid in unique_sensors:
        test_mask  = sensor_ids == sid
        train_mask = ~test_mask
        if train_mask.sum() < 2:
            y_pred[test_mask] = y[train_mask].mean() if train_mask.sum() > 0 else y.mean()
            continue

        X_train = X[train_mask].copy()
        X_test  = X[test_mask].copy()

        if use_spatial_lag:
            train_sensors = [s for s in unique_sensors if s != sid]

            # Coordenadas del sensor test y de los sensores de entrenamiento
            coord_map  = {s: coords[i] for i, s in enumerate(unique_sensors)}
            test_coord = coord_map[sid]
            train_coords_arr = np.array([coord_map[s] for s in train_sensors])

            # Distancias desde test hacia todos los sensores de entrenamiento
            diffs = train_coords_arr - test_coord
            dists = np.sqrt((diffs ** 2).sum(axis=1))
            k_eff = min(k_neighbors, len(train_sensors))
            nn_idx = np.argsort(dists)[:k_eff]
            nn_sensors = [train_sensors[i] for i in nn_idx]

            # Spatial lag para el sensor test: media de PM de vecinos (fila a fila del panel)
            test_lag = np.array([
                np.nanmean([sensor_pm_map[ns][j] for ns in nn_sensors
                            if ns in sensor_pm_map])
                for j in np.where(test_mask)[0]
            ])

            # Spatial lag para cada sensor de entrenamiento (excluye a sí mismo)
            train_lag = np.zeros(train_mask.sum())
            train_rows = np.where(train_mask)[0]
            for row_i, global_i in enumerate(train_rows):
                s_train = sensor_ids[global_i]
                peers   = [s for s in train_sensors if s != s_train]
                if len(peers) == 0:
                    train_lag[row_i] = np.nanmean([sensor_pm_map[ns][global_i]
                                                    for ns in train_sensors
                                                    if ns in sensor_pm_map])
                else:
                    peer_dists = np.sqrt(((
                        np.array([coord_map[p] for p in peers]) - coord_map[s_train]
                    )**2).sum(axis=1))
                    k2 = min(k_neighbors, len(peers))
                    nn2 = [peers[i] for i in np.argsort(peer_dists)[:k2]]
                    train_lag[row_i] = np.nanmean([sensor_pm_map[ns][global_i]
                                                   for ns in nn2
                                                   if ns in sensor_pm_map and
                                                   not np.isnan(sensor_pm_map[ns][global_i])])

            # Tratar NaN en lag (sensores sin vecinos con datos)
            train_lag = np.nan_to_num(train_lag, nan=np.nanmean(train_lag))
            test_lag  = np.nan_to_num(test_lag,  nan=np.nanmean(train_lag))

            # Concatenar spatial lag como última columna
            X_train = np.column_stack([X_train, train_lag])
            X_test  = np.column_stack([X_test,  test_lag])

        if model_class is None:
            m = kwargs["instance_factory"]()
        else:
            m = model_class(**{k: v for k, v in kwargs.items()
                               if k not in ("instance_factory", "coords",
                                            "sensor_pm_map", "k_neighbors")})
        m.fit(X_train, y[train_mask])
        y_pred[test_mask] = m.predict(X_test)

    r2   = r2_score(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return {"r2_cv": r2, "rmse_cv": rmse, "y_pred": y_pred}
```

## Tarea 3: Preparar `coords` y `sensor_pm_map` en la Función de Entrenamiento

Localiza la función principal de entrenamiento (probablemente `train_and_evaluate` o similar) donde se llama a `loocv_panel`. Añade la preparación de las variables necesarias antes de llamar a `loocv_panel`:

```python
# Preparar datos para spatial lag
coords_dict    = {}   # sensor_id → (x, y) en EPSG:27700
sensor_pm_map  = {}   # sensor_id → array de PM (indexado igual que el panel)

# Intentar cargar coordenadas desde sensores_snapped.gpkg
try:
    import geopandas as gpd
    snapped = gpd.read_file(DATA_INT / "sensores_snapped.gpkg")
    for _, row in snapped.iterrows():
        coords_dict[row["sensor_id"]] = (row.geometry.x, row.geometry.y)
    log.info(f"  Coordenadas cargadas para {len(coords_dict)} sensores")
except Exception as e:
    log.warning(f"  No se pudieron cargar coordenadas para spatial lag: {e}")
    coords_dict = {}

# Construir sensor_pm_map desde el panel actual (df_panel con columna target)
if coords_dict and "sensor_id" in df_panel.columns:
    unique_sids = df_panel["sensor_id"].unique()
    coords_arr  = np.array([coords_dict.get(s, (np.nan, np.nan)) for s in unique_sids])
    for s in unique_sids:
        mask = df_panel["sensor_id"] == s
        sensor_pm_map[s] = df_panel.loc[mask, target].values
```

Pasa estos datos a `loocv_panel`:
```python
results = loocv_panel(
    model_class, X, y, sensor_ids,
    coords=coords_arr if coords_dict else None,
    sensor_pm_map=sensor_pm_map if coords_dict else None,
    k_neighbors=3,
    **other_kwargs
)
```

Asegúrate de que `sensor_ids` sea un array de strings (no índices numéricos) que coincida con las claves de `coords_dict` y `sensor_pm_map`.

## Tarea 4: Validación Comparativa

Ejecuta `lur_model.py` y captura el log. El reporte de resultados (`model_comparison.csv` en `data/processed/LUR/`) debe mostrar los nuevos R² con spatial lag incorporado.

Adicionalmente, añade al final del script (o en `task5_loocv_validation.py`) un log comparativo explícito:

```python
log.info("=" * 60)
log.info("IMPACTO DEL SPATIAL LAG:")
log.info(f"  PM2.5 — R² sin lag: {r2_sin_lag:.4f}  |  R² con lag: {r2_con_lag:.4f}")
log.info(f"  PM10  — R² sin lag: {r2_sin_lag_10:.4f} |  R² con lag: {r2_con_lag_10:.4f}")
log.info("=" * 60)
```

Para esto necesitas guardar los R² antes y después de añadir el spatial lag. Puedes hacer dos rondas de entrenamiento: una con `coords=None` (sin lag) y otra con `coords=coords_arr` (con lag).

## Tarea 5: Ejecutar Pipeline Completo

```bash
python src/models/lur_model.py
```

Verifica en el log:
- `[LOOCV-PANEL] Spatial lag activado` aparece.
- No hay `NaN` ni `RuntimeWarning` en el cálculo del lag.
- Los R² son >= a los obtenidos sin spatial lag (si bajan, reportarlo).
- No hay data leakage: el sensor test nunca usa su propio PM.

---

# Protocolo Anti-Data-Leakage

Antes de dar por buena la implementación, verifica mentalmente:
1. `y[test_mask]` nunca se usa para calcular `test_lag` ni `train_lag`.
2. `sensor_pm_map[sid]` (el sensor test) nunca aparece en los cálculos de lag del fold donde `sid` es el test.
3. El `train_lag` de un sensor en entrenamiento solo usa los PM de sus vecinos, nunca el suyo propio.

---

# Reporte Final

```
=== AGENTE 6: SPATIAL LAG — COMPLETADO ===
Tarea 1 (Lectura y análisis de loocv_panel):  ✅/❌ — [detalle]
Tarea 2 (Implementación spatial lag en LOOCV): ✅/❌ — [detalle]
Tarea 3 (Preparación coords y sensor_pm_map):  ✅/❌ — [detalle]
Tarea 4 (Log comparativo antes/después):        ✅/❌ — [detalle]
Tarea 5 (Ejecución sin errores):                ✅/❌ — [detalle]

RESULTADOS COMPARATIVOS:
          | Sin Spatial Lag | Con Spatial Lag | Delta
PM2.5 R²  |     X.XXX       |     X.XXX       | +X.XXX
PM10  R²  |     X.XXX       |     X.XXX       | +X.XXX

Data leakage verificado: ✅ NO hay leakage
```
