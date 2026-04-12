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
├── src/                # EL MOTOR: Funciones compartidas o constantes (Opcional)
│   └── utils.py          # Utilidades auxiliares (si es necesario)
├── notebooks/          # EL ESCAPARATE Y LA LÓGICA: Análisis, limpieza y gráficos
│   └── liverpool_air_quality.ipynb  # Reporte principal del proyecto
│   └── Analisis_Datos_Crudos.ipynb  # Pipeline de Ingesta y limpieza
├── outputs/            # Resultados finales (Mapas, Figuras, Modelos entrenados)
├── docs/               # Documentación adicional y entregables
└── .gitignore          # Filtro para no saturar Git con archivos pesados
```

---

## ⚙️ Metodología de Trabajo

Para evitar conflictos y trabajar de forma profesional, seguiremos estas reglas:

1. **Notebooks como Motor:** Toda la lógica pesada (limpieza de datos, cálculos complejos, geoprocesamiento) y la visualización de resultados se realizará en cuadernos Jupyter (`.ipynb`). Esto asegura que todo el proceso quede completamente documentado de forma interactiva paso a paso.
2. **Modularización Subdividida:** Para mantener el orden, procuraremos crear diferentes notebooks para áreas temáticas distintas para que no queden cuadernos extremadamente largos ni bucles infinitos.
3. **Control de Versiones:** Cada tarea o Issue tiene su propia rama.
   - Ejemplo: `ingesta-sensores` para el Issue #16.
4. **Datos Protegidos:** Nunca subas archivos CSV pesados a GitHub. Usa la carpeta `data/` y asegúrate de que el `.gitignore` esté configurado.

---

## 🚀 Cómo empezar (Issue #16 - Ingesta)

Si quieres ejecutar el proceso de limpieza de sensores que ya hemos construido:

1. Abre el cuaderno `Analisis_Datos_Crudos.ipynb`.
2. Ejecuta todas las celdas de código. Hacia el final del archivo ("Pipeline de Ingesta y Limpieza") verás el proceso automatizado de recolección temporal.
3. El resultado aparecerá automáticamente procesado y guardado en `data/processed/sensors_cleaned.csv`.



---


## Extracción de capas urbanas con OSMnx

El script `src/analysis/extract_osm_features.py` implementa la fase de extracción espacial del proyecto para la ciudad de Liverpool a partir de OpenStreetMap, utilizando la librería OSMnx.

### Capas extraídas
- Red de calles
- Usos del suelo
- Edificios

### Metodología
La extracción se realiza mediante `features_from_place`, siguiendo la guía metodológica del proyecto. Posteriormente, las capas se someten a un proceso de limpieza geométrica defensiva que incluye:
- eliminación de geometrías nulas o vacías,
- reparación de geometrías inválidas,
- filtrado de tipos geométricos coherentes,
- validación específica de capas poligonales.

Finalmente, todas las capas se reproyectan a `EPSG:27700` (British National Grid), sistema de referencia adecuado para operaciones métricas en Liverpool.

### Salidas
El script genera los siguientes archivos:
- `data/raw/streets_liverpool.gpkg`
- `data/raw/landuse_liverpool.gpkg`
- `data/raw/buildings_liverpool.gpkg`

### Objetivo dentro del proyecto
Estas capas constituyen la base espacial sobre la que se desarrollarán etapas posteriores del proyecto, como la generación de buffers alrededor de sensores y la construcción de variables para el modelo LUR.




## 👥 Colaboradores
* **ivanloki00** (Coordinación y Limpieza)
* **Juanjocepe05** (Análisis Temporal)
* **elsenyordata** (Extracción OSMNX)
* **camposh663-hue** (Geometría Urbana)
* **pableras120** (Análisis de Impacto)
