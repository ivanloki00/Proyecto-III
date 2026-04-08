"""
Generador de Mapas de Predicción LUR
Este script toma el GeoJSON resultante y genera comprobaciones visuales 
(mapas de contaminación) para PM2.5 y PM10 guardándolos en formato PNG.
"""

import os
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt

# Configuramos matplotlib para que no intente abrir ventanas si estamos en headless
import matplotlib
matplotlib.use("Agg")

def plot_pollution_maps():
    # Directorio actual (outputs)
    OUT_DIR = Path(__file__).resolve().parent
    GEOJSON_PATH = OUT_DIR / "liverpool_pollution_map.geojson"
    
    if not GEOJSON_PATH.exists():
        print(f"Error: No se encuentra {GEOJSON_PATH}")
        return

    print("Cargando GeoJSON (esto puede tomar varios segundos)...")
    gdf = gpd.read_file(GEOJSON_PATH)
    
    # Asegurarnos de que el CRS es apto para visualización (Pseudo-Mercator o dejar en WGS84)
    # WGS84 deforma un poco UK, mejor pasarlo a EPSG:27700 solo para el plot, 
    # o usar tal cual sabiendo que es indicativo.
    gdf = gdf.to_crs("EPSG:27700")

    targets = [
        {"col": "pm25_pred", "title": "Predicción PM2.5 (Liverpool 2024)", "output": "map_PM25.png", "vmax_percentile": 99},
        {"col": "pm10_pred", "title": "Predicción PM10 (Liverpool 2024)", "output": "map_PM10.png", "vmax_percentile": 99}
    ]

    for t in targets:
        print(f"Generando mapa para {t['col']}...")
        
        # Filtramos un poco los valores extremos superiores para que la rampa de color respire bien
        vmax = gdf[t['col']].quantile(t['vmax_percentile'] / 100.0)
        vmin = gdf[t['col']].min()

        fig, ax = plt.subplots(1, 1, figsize=(14, 14), facecolor="#111111")
        ax.set_facecolor("#111111")
        
        # Ocultar ejes
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        # Título
        plt.title(t['title'], fontsize=18, fontweight="bold", color="white", pad=20)

        # Plotear lineas. Ajustar el linewidth en función de si es motorway o no para dar jerarquía (opcional),
        # aquí usaremos un linewidth constante estándar.
        gdf.plot(
            column=t['col'],
            ax=ax,
            cmap="inferno",
            linewidth=1.2,
            vmin=vmin,
            vmax=vmax,
            legend=True,
            legend_kwds={
                "shrink": 0.5,
                "label": "Concentración (µg/m³)",
                "orientation": "horizontal",
                "pad": 0.05
            }
        )
        
        # Ajustar el texto de la leyenda para que se vea en fondo oscuro
        cb = ax.get_figure().axes[-1]
        cb.tick_params(colors="white")
        cb.xaxis.label.set_color("white")
        
        # Guardar
        out_path = OUT_DIR / t["output"]
        plt.tight_layout()
        plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close()
        
        print(f"Mapa guardado exitosamente: {out_path}")

if __name__ == "__main__":
    plot_pollution_maps()
