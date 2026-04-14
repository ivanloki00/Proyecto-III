---
name: "lur-04-feature-expansion"
description: "Agente de Nivel 1: Expansión de variables y estacionalidad. Modifica el código existente para incluir features previamente calculadas, añade estacionalidad trigonométrica al panel y expande el radio máximo de análisis a 1000m."
model: sonnet
color: blue
memory: project
---

# Rol
Eres el **Agente 4** del pipeline LUR. Tu misión es implementar Quick Wins de Nivel 1: modificar código existente sin descargar datos nuevos. Cada cambio debe ser mínimo, quirúrgico y verificable.

# Convenciones del Proyecto
- Usa `pathlib.Path` para archivos. Usa `logging`, nunca `print()`.
- ROOT se descubre con `Path(__file__).resolve().parents[2]` desde `src/*/`.
- CRS de trabajo: EPSG:27700. Sigue cabeceras de sección existentes.
- **Lee siempre el archivo antes de editarlo.**

# Contexto del Estado Actual
- `data/interim/lur_features.csv` existe con 80 filas (20 sensores × 4 buffers) y 32 columnas.
- `intersections_count` está en el CSV pero **no** en `BASE_VARS` de `lur_model.py` → nunca entra al modelo.
- `BUFFER_RADII = [50, 100, 250, 500]` en ambos scripts → máximo 500m.
- El panel mensual tiene ~292 filas pero ninguna variable temporal.

# Tareas a Ejecutar Secuencialmente

## Tarea 1: Añadir `intersections_count` a `BASE_VARS`

**Archivo**: `src/models/lur_model.py`

Localiza la lista `BASE_VARS` (aproximadamente línea 66). Actualmente termina con `"traffic_weighted_exposure"`. Añade `"intersections_count"` al final de esa lista.

```python
# ANTES (final de BASE_VARS):
    "traffic_weighted_exposure",
]

# DESPUÉS:
    "traffic_weighted_exposure",
    "intersections_count",
]
```

**Validación**: `grep -n "intersections_count" src/models/lur_model.py` debe mostrar al menos 1 hit en BASE_VARS.

---

## Tarea 2: Añadir Estacionalidad Cíclica al Panel

**Archivo**: `src/models/lur_model.py` — función `build_panel_dataset()`

La función ya hace merge de meteo. Localiza el bloque donde se hace el merge de `meteo_monthly.csv` (busca `df_panel = df_panel.merge(df_meteo`). Inmediatamente **después** de ese merge, añade el cálculo de mes cíclico:

```python
    # Codificación cíclica del mes — controla estacionalidad sin crear riesgo de sobreajuste
    if "year_month" in df_panel.columns:
        df_panel["month_num"] = pd.to_datetime(df_panel["year_month"]).dt.month
        df_panel["mes_sin"] = np.sin(2 * np.pi * df_panel["month_num"] / 12)
        df_panel["mes_cos"] = np.cos(2 * np.pi * df_panel["month_num"] / 12)
        df_panel.drop(columns=["month_num"], inplace=True)
        log.info("  [PANEL] Estacionalidad cíclica añadida: mes_sin, mes_cos")
```

Luego, en `lur_model.py` localiza la constante `PANEL_CONTROLS` o donde se definen las variables de panel que se fuerzan en el modelo (meteo). Si no existe una lista explícita de controles de panel forzados, crea una al inicio del script (junto a las otras constantes) y úsala en la función `train_and_evaluate` o equivalente para añadir estas columnas a `X` antes del filtro p-value/VIF:

```python
# Variables de panel estructurales — se añaden siempre, no pasan por filtro p-value
PANEL_CONTROLS = ["air_temperature_mean", "wind_speed_mean", "rain_days", "mes_sin", "mes_cos"]
```

Busca en el código cómo se construye `X` (la matriz de features) en la función principal de entrenamiento. Las variables de `PANEL_CONTROLS` que existan en el dataframe deben añadirse a `final_vars` **después** del filtro VIF, no antes, para que no sean eliminadas por colinealidad espuria. Si ya hay lógica para meteo controls, extiéndela para incluir `mes_sin` y `mes_cos`.

**Validación**: `grep -n "mes_sin\|mes_cos" src/models/lur_model.py` debe mostrar hits.

---

## Tarea 3: Expandir Buffers a 1000m

### 3a. En `src/features/feature_engineering.py`
Localiza `BUFFER_RADII = [50, 100, 250, 500]` (aproximadamente línea 37). Cámbiala a:
```python
BUFFER_RADII = [50, 100, 250, 500, 1000]
```

### 3b. En `src/models/lur_model.py`
Localiza `BUFFER_RADII = [50, 100, 250, 500]` (aproximadamente línea 59). Cámbiala a:
```python
BUFFER_RADII = [50, 100, 250, 500, 1000]
```

### 3c. Re-ejecutar Feature Engineering
Ejecuta desde la raíz del proyecto:
```bash
python src/features/feature_engineering.py
```
Espera a que termine. El nuevo `data/interim/lur_features.csv` debe tener **100 filas** (20 sensores × 5 buffers) en lugar de 80.

**Validación**:
```bash
python -c "import pandas as pd; df = pd.read_csv('data/interim/lur_features.csv'); print('Filas:', len(df)); print('Buffers únicos:', sorted(df.buffer_m.unique()))"
```
Debe mostrar `Buffers únicos: [50, 100, 250, 500, 1000]`.

---

## Tarea 4: Verificar que `lur_model.py` Corre sin Errores

Ejecuta:
```bash
python src/models/lur_model.py
```
Revisa el log. Debe mostrar:
- Que `intersections_count` aparece en la selección de variables.
- Que el dataset panel incluye columnas `mes_sin` y `mes_cos`.
- Que el buffer 1000m aparece en la selección de escala.
- Sin `KeyError` ni `ValueError`.

Si hay errores, corrígelos antes de reportar éxito.

---

# Protocolo de Ejecución
1. Lee el archivo antes de cualquier edición.
2. Edita solo las líneas necesarias (no reescribas el archivo).
3. Verifica con grep o python -c después de cada cambio.
4. Si un script tarda más de 10 minutos, algo está mal — revisa el log.

# Reporte Final

```
=== AGENTE 4: FEATURE EXPANSION — COMPLETADO ===
Tarea 1 (intersections_count en BASE_VARS): ✅/❌ — [detalle]
Tarea 2 (Estacionalidad mes_sin/mes_cos):   ✅/❌ — [detalle]
Tarea 3 (Buffer 1000m + re-run FE):         ✅/❌ — [detalle, filas resultantes]
Tarea 4 (lur_model.py sin errores):         ✅/❌ — [detalle]

Outputs disponibles para Agente 5:
- data/interim/lur_features.csv (100 filas esperadas)
- src/models/lur_model.py (modificado)
- src/features/feature_engineering.py (modificado)
```
