from pathlib import Path
import logging
import os
import osmnx as ox
import geopandas as gpd

# =========================
# CONFIG
# =========================
PLACE_NAME = "Liverpool, United Kingdom"
CRS_PROJECTED = "EPSG:27700"

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = ROOT / "outputs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "extract_osm_features.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

ox.settings.use_cache = True
ox.settings.log_console = True


# =========================
# UTILIDADES
# =========================
def standardize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.reset_index(drop=True).copy()
    gdf.columns = [str(c).strip().lower().replace(":", "_").replace(" ", "_")[:60] for c in gdf.columns]
    return gdf


def repair_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()

    invalid = ~gdf.geometry.is_valid
    if invalid.any():
        logger.info("Reparando %s geometrías inválidas", int(invalid.sum()))
        try:
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].make_valid()
        except Exception:
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)

    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    return gdf


def keep_polygonal(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()


def keep_linear(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()


def enforce_closed_valid_polygons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Garantía defensiva para capas poligonales:
    - deja solo polígonos/multipolígonos
    - repara inválidas
    - explota multipartes si hiciera falta
    - vuelve a validar
    """
    gdf = keep_polygonal(gdf)
    gdf = repair_geometries(gdf)
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    gdf = keep_polygonal(gdf)
    gdf = repair_geometries(gdf)
    return gdf


def project_to_27700(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError("La capa no tiene CRS definido.")
    return gdf.to_crs(CRS_PROJECTED)


def save_gpkg(gdf: gpd.GeoDataFrame, path: Path, layer: str) -> None:
    if path.exists():
        os.remove(path)
    gdf.to_file(path, layer=layer, driver="GPKG")
    logger.info("Guardado %s", path)


def log_summary(name: str, gdf: gpd.GeoDataFrame) -> None:
    logger.info(
        "%s | filas=%s | crs=%s | geoms=%s",
        name,
        len(gdf),
        gdf.crs,
        sorted(gdf.geometry.geom_type.unique().tolist())
    )


# =========================
# EXTRACCIÓN
# =========================
def extract_streets() -> gpd.GeoDataFrame:
    logger.info("Extrayendo calles con features_from_place...")

    tags = {
        "highway": ["motorway", "primary", "secondary", "residential"]
    }

    streets = ox.features_from_place(PLACE_NAME, tags=tags)
    streets = standardize_columns(streets)
    streets = keep_linear(streets)
    streets = repair_geometries(streets)
    streets = project_to_27700(streets)

    if streets.empty:
        raise ValueError("La capa de calles quedó vacía.")

    log_summary("streets", streets)
    return streets


def extract_landuse() -> gpd.GeoDataFrame:
    logger.info("Extrayendo usos del suelo con features_from_place...")

    tags = {
        "landuse": ["industrial", "residential", "commercial", "grass", "forest"],
        "leisure": ["park", "garden"]
    }

    landuse = ox.features_from_place(PLACE_NAME, tags=tags)
    landuse = standardize_columns(landuse)
    landuse = enforce_closed_valid_polygons(landuse)
    landuse = project_to_27700(landuse)

    if landuse.empty:
        raise ValueError("La capa de usos del suelo quedó vacía.")

    log_summary("landuse", landuse)
    return landuse


def extract_buildings() -> gpd.GeoDataFrame:
    logger.info("Extrayendo edificios con features_from_place...")

    buildings = ox.features_from_place(PLACE_NAME, tags={"building": True})
    buildings = standardize_columns(buildings)
    buildings = enforce_closed_valid_polygons(buildings)
    buildings = project_to_27700(buildings)

    if buildings.empty:
        raise ValueError("La capa de edificios quedó vacía.")

    log_summary("buildings", buildings)
    return buildings


# =========================
# MAIN
# =========================
def main():
    logger.info("=== INICIO EXTRACCIÓN OSM LIVERPOOL ===")

    streets = extract_streets()
    landuse = extract_landuse()
    buildings = extract_buildings()

    save_gpkg(streets, RAW_DIR / "streets_liverpool.gpkg", "streets")
    save_gpkg(landuse, RAW_DIR / "landuse_liverpool.gpkg", "landuse")
    save_gpkg(buildings, RAW_DIR / "buildings_liverpool.gpkg", "buildings")

    logger.info("=== EXTRACCIÓN FINALIZADA CORRECTAMENTE ===")


if __name__ == "__main__":
    main()