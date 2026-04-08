"""
Fase 3 - Integración de Tráfico AADF
1. Descarga los datos de conteo de tráfico DfT para Liverpool (LA code 112).
2. Filtra los puntos del año más reciente disponible (2023, ya que 2024 suele publicarse con retraso).
3. Hace un Spatial Join sobre la red viaria OSM.
4. Imputa el tráfico a los segmentos sin contador usando la mediana por jerarquía 'highway'.
"""

from pathlib import Path
import logging
import requests
import pandas as pd
import geopandas as gpd
from io import StringIO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

ROOT     = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_INT = ROOT / "data" / "interim"
DATA_INT.mkdir(exist_ok=True)

STREETS_GPKG    = DATA_RAW / "streets_liverpool.gpkg"
AADF_CSV_LOCAL  = DATA_RAW / "aadf_liverpool.csv"
OUT_AADF_GPKG   = DATA_INT / "aadf_snapped.gpkg"
OUT_STREETS_TRF = DATA_INT / "streets_with_traffic.gpkg"

# URL oficial de la DfT - datos de conteo de puntos para Liverpool (LA 161)
# https://roadtraffic.dft.gov.uk/local-authorities/161
DFT_URL = (
    "https://api.dft.gov.uk/v1/traffic-counts/local-authority/"
    "161?format=csv&year=2023"
)

# Fallback: dataset nacional filtrado por LA 161 (Liverpool)
DFT_NATIONAL_URL = (
    "https://storage.googleapis.com/dft-statistics/road-traffic/downloads/"
    "aadf/local_authority_id/dft_aadf_local_authority_id_161.csv"
)

HIGHWAY_TRAFFIC_ORDER = [
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service"
]


def download_aadf() -> pd.DataFrame:
    """Descarga los datos AADF para Liverpool. Prueba varias fuentes."""
    if AADF_CSV_LOCAL.exists():
        logging.info(f"Usando AADF local: {AADF_CSV_LOCAL}")
        return pd.read_csv(AADF_CSV_LOCAL)

    sources = [
        ("DfT local authority API", DFT_URL),
        ("DfT national dataset LA-112", DFT_NATIONAL_URL),
    ]

    for name, url in sources:
        try:
            logging.info(f"Descargando AADF desde: {name} ...")
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            logging.info(f"Descarga OK – {len(df)} registros desde {name}")
            df.to_csv(AADF_CSV_LOCAL, index=False)
            return df
        except Exception as e:
            logging.warning(f"Fallo en {name}: {e}")

    raise RuntimeError("No se pudo descargar AADF desde ninguna fuente.")


def prepare_aadf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Limpia y convierte AADF a GeoDataFrame en EPSG:27700."""
    logging.info(f"Columnas AADF: {df.columns.tolist()}")

    # Los nombres de columna varían según la fuente DfT; normalizamos
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Identificar columnas de easting/northing o lat/lon
    coord_map = {}
    for col in df.columns:
        if col in ("easting", "x", "start_easting"):
            coord_map["x"] = col
        if col in ("northing", "y", "start_northing"):
            coord_map["y"] = col
        if col in ("latitude", "lat"):
            coord_map["lat"] = col
        if col in ("longitude", "lon", "long"):
            coord_map["lon"] = col

    # Columna de tráfico total
    aadf_col = next(
        (c for c in df.columns if "all_motor" in c or "aadf" in c or "total" in c),
        None
    )
    if aadf_col is None:
        # Lista las columnas numéricas disponibles para diagnóstico
        logging.warning(f"No se encontró columna de volumen total. Columnas: {df.columns.tolist()}")
        raise KeyError("Columna AADF de tráfico total no encontrada.")

    logging.info(f"Columna de tráfico: '{aadf_col}'")
    df["aadf_total"] = pd.to_numeric(df[aadf_col], errors="coerce")
    df = df.dropna(subset=["aadf_total"])

    if "x" in coord_map and "y" in coord_map:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df[coord_map["x"]], df[coord_map["y"]]),
            crs="EPSG:27700"
        )
    elif "lon" in coord_map and "lat" in coord_map:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df[coord_map["lon"]], df[coord_map["lat"]]),
            crs="EPSG:4326"
        ).to_crs("EPSG:27700")
    else:
        raise KeyError(f"No se encontraron columnas de coordenadas. Disponibles: {df.columns.tolist()}")

    logging.info(f"Puntos AADF válidos: {len(gdf)}")
    return gdf


def join_aadf_to_streets(streets: gpd.GeoDataFrame, aadf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Spatial join: asocia el punto AADF más cercano a cada tramo viario."""
    logging.info("Spatial Join AADF → Red viaria ...")

    aadf_slim = aadf[["geometry", "aadf_total"]].copy()

    streets_joined = streets.sjoin_nearest(
        aadf_slim,
        how="left",
        max_distance=500,          # máximo 500m para no asignar tráfico de otra calle
        distance_col="dist_aadf_m",
        rsuffix="aadf"
    )

    # Si hay duplicados (varios AADF igualmente cercanos), quedarse con el primero
    streets_joined = streets_joined[~streets_joined.index.duplicated(keep="first")].copy()

    matched = streets_joined["aadf_total"].notna().sum()
    logging.info(f"Tramos con AADF directo: {matched} / {len(streets_joined)}")
    return streets_joined


def impute_aadf_by_hierarchy(streets_joined: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Imputa el tráfico (AADF) a tramos sin contador usando la 
    mediana de cada clase 'highway'.
    """
    logging.info("Imputando tráfico por jerarquía viaria ...")

    # Normalizar el campo highway (puede ser una lista de strings)
    streets_joined["highway_norm"] = streets_joined["highway"].apply(
        lambda x: x[0] if isinstance(x, list) else str(x).split(",")[0].strip()
    )

    # Mediana de AADF real por tipo de carretera (sólo medido)
    medians = (
        streets_joined[streets_joined["aadf_total"].notna()]
        .groupby("highway_norm")["aadf_total"]
        .median()
    )
    logging.info(f"Medianas por tipo:\n{medians.sort_values(ascending=False)}")

    # Rellenar faltantes
    def fill_aadf(row):
        if pd.notna(row["aadf_total"]):
            return row["aadf_total"]
        hw = row["highway_norm"]
        # Buscar en la jerarquía hacia arriba si el tipo exacto no tiene datos
        for hw_type in HIGHWAY_TRAFFIC_ORDER:
            if hw == hw_type and hw_type in medians.index:
                return medians[hw_type]
        # Fallback: mediana global
        return streets_joined["aadf_total"].median()

    streets_joined["aadf_imputed"] = streets_joined.apply(fill_aadf, axis=1)
    streets_joined["aadf_source"] = streets_joined["aadf_total"].apply(
        lambda x: "medido" if pd.notna(x) else "imputado"
    )

    imputed_pct = (streets_joined["aadf_source"] == "imputado").mean() * 100
    logging.info(f"Tramos imputados: {imputed_pct:.1f}%")
    return streets_joined


def main():
    logging.info("=== FASE 3: Integración AADF ===")

    streets = gpd.read_file(STREETS_GPKG)
    logging.info(f"Red viaria cargada: {len(streets)} tramos")

    raw_aadf = download_aadf()
    aadf_gdf = prepare_aadf(raw_aadf)
    aadf_gdf.to_file(OUT_AADF_GPKG, driver="GPKG")

    streets_trf = join_aadf_to_streets(streets, aadf_gdf)
    streets_trf = impute_aadf_by_hierarchy(streets_trf)

    # Guardar resultado
    keep_cols = [c for c in streets_trf.columns if c != "index_aadf"]
    streets_trf[keep_cols].to_file(OUT_STREETS_TRF, driver="GPKG")
    logging.info(f"Red viaria con tráfico guardada → {OUT_STREETS_TRF}")

    logging.info("\n=== RESUMEN FINAL ===")
    logging.info(streets_trf[["highway_norm", "aadf_imputed", "aadf_source"]]
                 .groupby(["highway_norm", "aadf_source"])["aadf_imputed"]
                 .agg(["median", "count"])
                 .to_string())


if __name__ == "__main__":
    main()
