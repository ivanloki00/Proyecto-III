# 🌬️ Liverpool Air Quality - Proyecto III

¡Bienvenidos al repositorio del Proyecto III sobre la Calidad del Aire en Liverpool! Este proyecto utiliza una red de 40+ sensores para analizar patrones de contaminación (PM2.5, PM10) y su relación con el entorno urbano.

---

## 🏗️ Estructura del Proyecto

```text
PROYIII/
├── data/               # Gestión de datos (No se suben a GitHub los CSVs grandes)
│   ├── raw/            # Datos brutos (DatosCompletos, CoordsSensores)
│   ├── interim/        # Datos en procesos intermedios
│   └── processed/      # Datasets finales limpios (Ej: sensors_cleaned.csv)
├── src/                # EL MOTOR: Scripts de Python (.py) con la lógica pesada
│   └── ingesta_sensores.py  # Pipeline de limpieza y unificación
├── notebooks/          # EL ESCAPARATE: Análisis, gráficos y explicaciones
│   └── liverpool_air_quality.ipynb  # Reporte principal del proyecto
├── outputs/            # Resultados finales (Mapas, Figuras, Modelos entrenados)
├── docs/               # Documentación adicional y entregables
└── .gitignore          # Filtro para no saturar Git con archivos pesados
```

---

## ⚙️ Metodología de Trabajo

Para evitar conflictos y trabajar de forma profesional, seguiremos estas reglas:

1. **Modularización:** La lógica pesada (limpieza de datos, cálculos complejos, geoprocesamiento) debe ir en archivos `.py` dentro de `src/`.
2. **Notebooks Limpios:** Los cuadernos Jupyter (`.ipynb`) se usarán para **visualizar resultados** e importar las funciones creadas en `src/`. No queremos notebooks de 2000 líneas con bucles complejos.
3. **Control de Versiones:** Cada tarea o Issue tiene su propia rama.
   - Ejemplo: `ingesta-sensores` para el Issue #16.
4. **Datos Protegidos:** Nunca subas archivos CSV pesados a GitHub. Usa la carpeta `data/` y asegúrate de que el `.gitignore` esté configurado.

---

## 🚀 Cómo empezar (Issue #16 - Ingesta)

Si quieres ejecutar el proceso de limpieza de sensores que ya hemos construido:

1. Abre tu terminal en la carpeta `src/`.
2. Ejecuta el script:
   ```bash
   python ingesta_sensores.py
   ```
3. El resultado aparecerá automáticamente en `data/processed/sensors_cleaned.csv`.

Desde un **Notebook**, puedes usar las funciones así:
```python
from src.ingesta_sensores import ejecutar_pipeline_ingesta

# Carga y limpia todo de un golpe
df = ejecutar_pipeline_ingesta(
    ruta_entrada="../data/raw/DatosCompletos",
    ruta_salida="../data/processed/sensors_cleaned.csv",
    ruta_coords="../data/raw/CoordsSensores.csv"
)
```

---

## 👥 Colaboradores
* **ivanloki00** (Coordinación y Limpieza)
* **Juanjocepe05** (Análisis Temporal)
* **elsenyordata** (Extracción OSMNX)
* **camposh663-hue** (Geometría Urbana)
* **pableras120** (Análisis de Impacto)
