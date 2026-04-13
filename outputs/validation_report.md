# Validation Report — Task 5 LOOCV
**Proyecto:** PROYIII Liverpool Air Quality LUR
**Fecha:** 2026-04-10
**Modelo:** Ridge Regression (ganador Task 4)
**Protocolo:** Leave-One-Out Cross-Validation (LOOCV), n = 20 folds

---

## 1. Metricas LOOCV

| Metrica | PM2.5 | PM10 |
|---------|-------|------|
| R² (LOOCV) | 0.6034 | 0.4137 |
| RMSE (µg/m³) | 1.8042 | 3.9235 |
| MAE (µg/m³) | 1.4997 | 3.1906 |
| MAPE (%) | 20.78 | 20.67 |

**Clasificacion:**
- PM2.5: ROBUSTO (R² > 0.6)
- PM10:  ACEPTABLE CON LIMITACIONES (0.4 ≤ R² ≤ 0.6)

---

## 2. Sensores Outlier (|residuo| > 2 x RMSE)

**PM2.5** (umbral = 3.608 µg/m³):
- `f008d1cbc5dc`: residuo = +3.623 µg/m³

**PM10** (umbral = 7.847 µg/m³):
Ninguno identificado para PM10.


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
| PM2.5 | 0.0162 | Heterocedasticidad detectada (p <= 0.05) |
| PM10  | 0.0219 | Heterocedasticidad detectada (p <= 0.05) |

### 3.2 Shapiro-Wilk (normalidad de residuos)

| Target | W | p-value | Interpretacion |
|--------|---|---------|----------------|
| PM2.5 | 0.9727 | 0.8106 | Residuos normales (p > 0.05) |
| PM10  | 0.9823 | 0.9606 | Residuos normales (p > 0.05) |

### 3.3 Moran's I (autocorrelacion espacial)

| Target | I | E[I] | z | p-value | Interpretacion |
|--------|---|------|---|---------|----------------|
| PM2.5 | -0.0517 | -0.0526 | 0.015 | 0.9877 | Sin autocorrelación espacial (p > 0.05) |
| PM10  | -0.0446 | -0.0526 | 0.134 | 0.8934 | Sin autocorrelación espacial (p > 0.05) |

### 3.4 Durbin-Watson (informativo, orden por sensor_id)

| Target | DW |
|--------|----|
| PM2.5 | 2.8297 |
| PM10  | 2.6588 |

> DW ~ 2.0 indica sin autocorrelacion serial. Rango aceptable: 1.5–2.5.

---

## 4. Interpretacion Global

**Rendimiento del modelo:**
- PM2.5 Ridge LOOCV: R²=0.603, RMSE=1.80 µg/m³, MAE=1.50 µg/m³.
- PM10  Ridge LOOCV: R²=0.414, RMSE=3.92 µg/m³, MAE=3.19 µg/m³.

**Supuestos del modelo:**
- Homocedasticidad: PM2.5 FALLA / PM10 FALLA.
  > Si alguno falla, los intervalos de confianza de Ridge son anticonservadores.
- Normalidad residuos: PM2.5 OK / PM10 OK.
- Autocorrelacion espacial: PM2.5 OK / PM10 OK.

---

## 5. Recomendacion: aptitud para extrapolacion

### PM2.5
ROBUSTO (R² > 0.6)
- R² > 0.6: el modelo puede usarse para extrapolacion espacial con cautela. Se recomienda reportar incertidumbre (intervalo de prediccion) en zonas sin sensores.

### PM10
ACEPTABLE CON LIMITACIONES (0.4 ≤ R² ≤ 0.6)
- R² entre 0.4-0.6: aceptable para descripcion espacial relativa (alta/baja contaminacion), pero NO para predicciones absolutas en zonas sin validar.

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
