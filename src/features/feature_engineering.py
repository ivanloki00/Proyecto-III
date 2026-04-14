"""
Fase 4 - Feature Engineering (Buffers Multi-escala)
Para cada sensor y cada radio (50, 100, 250, 500m):
  - Tráfico total y medio (AADF imputado) de los tramos dentro del buffer
  - Longitud de carretera total y por jerarquía
  - Huella edificatoria total (m²)
  - Cobertura de uso de suelo: Industrial, Residencial, Comercial, Verde
  - Número de intersecciones viarias dentro del buffer (nodos únicos)
  - Distancia al centro de Liverpool (EPSG:27700)
Salida: data/interim/lur_features.csv
"""

from pathlib import Path
import logging
import warnings
import geopandas as gpd
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

ROOT     = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INT = ROOT / "data" / "interim"

SENSORS_GPKG  = DATA_INT / "sensores_snapped.gpkg"
STREETS_GPKG  = DATA_INT / "streets_with_traffic.gpkg"
BUILDINGS_GPKG = DATA_RAW / "buildings_liverpool.gpkg"
LANDUSE_GPKG  = DATA_RAW / "landuse_liverpool.gpkg"
OUT_CSV       = DATA_INT / "lur_features.csv"

BUFFER_RADII = [50, 100, 250, 500, 1000]   # metros

# Centro de Liverpool en EPSG:27700 (British National Grid)
LIVERPOOL_CENTRE_X = 335000.0
LIVERPOOL_CENTRE_Y = 390000.0

# C3 — Fuentes puntuales en EPSG:27700
# Coordenadas obtenidas de OS Maps / Google Maps y convertidas a BNG
POINT_SOURCES = {
    # Puerto de Liverpool (Royal Albert Dock centroid)
    "dist_port_m":       (334300.0, 389700.0),
    # Túnel Queensway (entrada Birkenhead, salida Liverpool)
    "dist_tunnel_m":     (333600.0, 390100.0),
    # Liverpool Lime Street Station
    "dist_station_m":    (335900.0, 390600.0),
    # Liverpool Airport (fuente de emisiones de aviación)
    "dist_airport_m":    (334900.0, 383700.0),
}

# Categorías de jerarquía viaria que queremos desagregar
HIGHWAY_CATS = {
    "motorway":    ["motorway", "motorway_link"],
    "primary":     ["primary", "primary_link", "trunk", "trunk_link"],
    "secondary":   ["secondary", "secondary_link"],
    "residential": ["residential", "tertiary", "tertiary_link", "unclassified",
                    "living_street", "service"],
}

# Etiquetas de uso de suelo según OSM
LANDUSE_CATS = {
    "industrial":   ["industrial"],
    "residential":  ["residential"],
    "commercial":   ["commercial", "retail"],
    "green":        ["grass", "forest", "park", "garden"],
}


# ─────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────

def normalize_highway(val) -> str:
    """Extrae la primera categoría si es lista o string compuesto."""
    if isinstance(val, list):
        val = val[0]
    return str(val).split(",")[0].strip().lower()


def assign_highway_cat(hw: str) -> str:
    for cat, types in HIGHWAY_CATS.items():
        if hw in types:
            return cat
    return "other"


def clip_and_area(gdf: gpd.GeoDataFrame, buffer_geom) -> float:
    """Intersecta gdf con buffer_geom y devuelve área total (m²)."""
    try:
        clipped = gdf.clip(buffer_geom)
        return clipped.geometry.area.sum()
    except Exception:
        return 0.0


def clip_and_length(gdf: gpd.GeoDataFrame, buffer_geom) -> float:
    """Intersecta gdf con buffer_geom y devuelve longitud total (m)."""
    try:
        clipped = gdf.clip(buffer_geom)
        return clipped.geometry.length.sum()
    except Exception:
        return 0.0


def count_intersections_in_buffer(streets_in: gpd.GeoDataFrame, buffer_geom) -> int:
    """
    Cuenta el número de nodos viarios únicos dentro del buffer.
    Para cada tramo se extraen sus puntos extremos (inicio y fin);
    se retienen los que caen dentro del buffer y se agrupan por
    coordenada redondeada a 1 metro para eliminar duplicados.
    """
    if len(streets_in) == 0:
        return 0
    try:
        clipped = streets_in.clip(buffer_geom)
        if len(clipped) == 0:
            return 0
        coords = set()
        for geom in clipped.geometry:
            if geom is None or geom.is_empty:
                continue
            # Extraer coords de inicio y fin del tramo recortado
            if geom.geom_type == "LineString":
                coords.add((round(geom.coords[0][0]), round(geom.coords[0][1])))
                coords.add((round(geom.coords[-1][0]), round(geom.coords[-1][1])))
            elif geom.geom_type == "MultiLineString":
                for part in geom.geoms:
                    coords.add((round(part.coords[0][0]), round(part.coords[0][1])))
                    coords.add((round(part.coords[-1][0]), round(part.coords[-1][1])))
        # Un nodo viario es intersección si al menos 2 tramos pasan por él.
        # Dado que contamos extremos de tramos recortados, todos los nodos
        # interiores al buffer son potenciales intersecciones; la cuenta de
        # nodos únicos es la métrica solicitada.
        return len(coords)
    except Exception:
        return 0


# ─────────────────────────────────────────────────
# Carga de capas
# ─────────────────────────────────────────────────

def load_layers():
    logging.info("Cargando sensores snapped ...")
    sensors = gpd.read_file(SENSORS_GPKG)

    logging.info("Cargando red viaria con tráfico ...")
    streets = gpd.read_file(STREETS_GPKG)
    streets["hw_norm"] = streets["highway"].apply(normalize_highway)
    streets["hw_cat"]  = streets["hw_norm"].apply(assign_highway_cat)

    logging.info("Cargando edificios ...")
    buildings = gpd.read_file(BUILDINGS_GPKG)
    if buildings.crs != sensors.crs:
        buildings = buildings.to_crs(sensors.crs)

    logging.info("Cargando usos del suelo ...")
    landuse = gpd.read_file(LANDUSE_GPKG)
    if landuse.crs != sensors.crs:
        landuse = landuse.to_crs(sensors.crs)

    logging.info(
        f"Capas: sensores={len(sensors)}, streets={len(streets)}, "
        f"buildings={len(buildings)}, landuse={len(landuse)}"
    )
    return sensors, streets, buildings, landuse


# ─────────────────────────────────────────────────
# Cálculo de variables por sensor × buffer
# ─────────────────────────────────────────────────

def compute_features_for_sensor(row, streets, buildings, landuse, radius) -> dict:
    buf = row.geometry.buffer(radius)
    feat = {"sensor_id": row["sensor_id"], "buffer_m": radius}

    # ── Tráfico ────────────────────────────────
    streets_in = streets[streets.geometry.intersects(buf)].copy()
    if len(streets_in) > 0:
        feat[f"aadf_total_sum"]  = streets_in["aadf_imputed"].sum()
        feat[f"aadf_total_mean"] = streets_in["aadf_imputed"].mean()
        feat[f"aadf_total_max"]  = streets_in["aadf_imputed"].max()
    else:
        feat[f"aadf_total_sum"]  = 0.0
        feat[f"aadf_total_mean"] = 0.0
        feat[f"aadf_total_max"]  = 0.0

    # ── Longitud viaria total y por categoría ──
    feat["road_length_total_m"] = clip_and_length(streets_in, buf)
    for cat in HIGHWAY_CATS:
        sub = streets_in[streets_in["hw_cat"] == cat]
        feat[f"road_length_{cat}_m"] = clip_and_length(sub, buf)

    # ── Densidad de intersecc. (nodos dentro buffer) ──
    # Proxy: número de tramos / área del buffer
    buf_area = buf.area
    feat["road_density_m_per_m2"] = feat["road_length_total_m"] / buf_area if buf_area > 0 else 0.0

    # ── Intersecciones viarias (nodos únicos) ─────────
    feat["intersections_count"] = count_intersections_in_buffer(streets_in, buf)

    # ── Distancia al centro de Liverpool ─────────────
    # NOTA A2: esta variable NO depende del radio del buffer — es una propiedad
    # del sensor, no del entorno a N metros. Se calcula aquí por completitud del
    # registro, pero en lur_model.py se trata como variable sin escala de buffer.
    centre_x, centre_y = LIVERPOOL_CENTRE_X, LIVERPOOL_CENTRE_Y
    dx = row.geometry.x - centre_x
    dy = row.geometry.y - centre_y
    feat["dist_centre_m"] = float(np.sqrt(dx**2 + dy**2))

    # ── Edificación ────────────────────────────
    feat["building_area_m2"] = clip_and_area(buildings, buf)
    feat["building_coverage_ratio"] = feat["building_area_m2"] / buf_area if buf_area > 0 else 0.0

    # ── Uso del suelo ──────────────────────────
    for lu_cat, lu_tags in LANDUSE_CATS.items():
        # Filtrar por columnas disponibles: 'landuse' ó 'leisure'
        masks = []
        for col in ["landuse", "leisure"]:
            if col in landuse.columns:
                masks.append(landuse[col].isin(lu_tags))
        if masks:
            combined_mask = masks[0]
            for m in masks[1:]:
                combined_mask = combined_mask | m
            sub_lu = landuse[combined_mask]
        else:
            sub_lu = landuse.iloc[0:0]
        feat[f"landuse_{lu_cat}_m2"]    = clip_and_area(sub_lu, buf)
        feat[f"landuse_{lu_cat}_ratio"] = feat[f"landuse_{lu_cat}_m2"] / buf_area if buf_area > 0 else 0.0

    # ── C3: Distancias a fuentes puntuales ───────────────────
    # (tampoco dependen del buffer — son propiedades del sensor)
    from shapely.geometry import Point
    for source_name, (sx, sy) in POINT_SOURCES.items():
        source_pt = Point(sx, sy)
        feat[source_name] = float(row.geometry.distance(source_pt))

    # ── Distancia a zona industrial más cercana ──
    industrial_tags = LANDUSE_CATS["industrial"]
    masks_ind = []
    for col in ["landuse", "leisure"]:
        if col in landuse.columns:
            masks_ind.append(landuse[col].isin(industrial_tags))
    if masks_ind:
        combined_ind = masks_ind[0]
        for m in masks_ind[1:]:
            combined_ind = combined_ind | m
        ind_zones = landuse[combined_ind]
        if len(ind_zones) > 0:
            feat["dist_industrial_m"] = ind_zones.geometry.distance(row.geometry).min()
        else:
            feat["dist_industrial_m"] = np.nan
    else:
        feat["dist_industrial_m"] = np.nan

    return feat


def compute_all_features(sensors, streets, buildings, landuse) -> pd.DataFrame:
    all_rows = []
    total = len(sensors) * len(BUFFER_RADII)
    done = 0

    for _, sensor_row in sensors.iterrows():
        for radius in BUFFER_RADII:
            feat = compute_features_for_sensor(sensor_row, streets, buildings, landuse, radius)
            all_rows.append(feat)
            done += 1
            if done % 10 == 0:
                logging.info(f"  Progreso: {done}/{total}")

    df = pd.DataFrame(all_rows)

    # ── Estadísticas detalladas por buffer ────────────
    logging.info("─── Estadísticas por buffer ───────────────────────────────")
    key_vars = [
        "aadf_total_sum", "road_length_total_m", "intersections_count",
        "dist_industrial_m", "dist_centre_m", "building_coverage_ratio",
    ]
    for radius in BUFFER_RADII:
        sub = df[df["buffer_m"] == radius]
        logging.info(f"  Buffer {radius:>4}m — n={len(sub)}")
        for var in key_vars:
            if var in sub.columns:
                vals = sub[var]
                logging.info(
                    f"    {var:<35} mean={vals.mean():>10.2f}  "
                    f"min={vals.min():>10.2f}  max={vals.max():>10.2f}  "
                    f"zeros={int((vals==0).sum())}"
                )

    return df


# ─────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────

def main():
    logging.info("=== FASE 4: Feature Engineering ===")
    sensors, streets, buildings, landuse = load_layers()

    # Añadir PM2.5 y PM10 al dataframe de features para usarlo después
    pm_cols = [c for c in sensors.columns if c in ["PM2.5", "PM10", "sensor_id"]]
    pm_ref = sensors[pm_cols].copy()

    logging.info(f"Calculando variables para {len(sensors)} sensores × {len(BUFFER_RADII)} buffers ...")
    features_df = compute_all_features(sensors, streets, buildings, landuse)

    # Unir PM2.5 / PM10
    features_df = features_df.merge(pm_ref, on="sensor_id", how="left")

    # Añadir elevación del sensor (sensor-level, idéntica para todos los buffers)
    elev_path = DATA_INT / "sensor_elevation.csv"
    if elev_path.exists():
        df_elev = pd.read_csv(elev_path)[["sensor_id", "elevation_m"]]
        features_df = features_df.merge(df_elev, on="sensor_id", how="left")
        med_elev = features_df["elevation_m"].median()
        features_df["elevation_m"] = features_df["elevation_m"].fillna(med_elev)
        logging.info(f"Elevación añadida: {features_df['elevation_m'].notna().sum()}/{len(features_df)} filas con datos")
    else:
        logging.warning(f"sensor_elevation.csv no encontrado en {elev_path} — columna elevation_m omitida")

    features_df.to_csv(OUT_CSV, index=False)
    logging.info(f"Features guardadas → {OUT_CSV}")
    logging.info(f"Shape: {features_df.shape}")
    logging.info(f"Columnas: {features_df.columns.tolist()}")

    # Resumen rápido
    numeric_cols = features_df.select_dtypes(include="number").columns
    logging.info(f"\n{features_df[numeric_cols].describe().round(2).to_string()}")


if __name__ == "__main__":
    main()
