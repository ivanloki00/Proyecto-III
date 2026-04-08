import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

# Configurar rutas relativas al archivo
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

# Archivos a cargar
STREETS_PATH = RAW_DIR / "streets_liverpool.gpkg"
LANDUSE_PATH = RAW_DIR / "landuse_liverpool.gpkg"
BUILDINGS_PATH = RAW_DIR / "buildings_liverpool.gpkg"

print("Cargando todos los datos de Liverpool...")

# 1. Cargar las capas
print("- Cargando usos de suelo...")
gdf_landuse = gpd.read_file(LANDUSE_PATH)

print("- Cargando edificios...")
gdf_buildings = gpd.read_file(BUILDINGS_PATH)

print("- Cargando calles...")
gdf_streets = gpd.read_file(STREETS_PATH)

# ==========================================
# 2. Configurar el gráfico (Ploteo por capas)
# ==========================================
print("\nGenerando mapa completo...")
fig, ax = plt.subplots(figsize=(12, 12))

# CAPA 1: Usos de suelo (Base)
gdf_landuse.plot(ax=ax, color='#e0eadf', edgecolor='#c5d8c1', alpha=0.9, label='Usos del suelo')

# CAPA 2: Calles
gdf_streets.plot(ax=ax, color='#2c3e50', linewidth=0.5, alpha=0.8, label='Calles')

# CAPA 3: Edificios (Superior)
gdf_buildings.plot(ax=ax, color='#f39c12', alpha=0.6, label='Edificios')

# Configuración estética
plt.title("Visualización Completa: Liverpool OSM Features", fontsize=15, pad=20)
plt.axis('off')

print("¡Listo! Mostrando ventana...")
plt.show()
