"""
Traffic-Weighted Exposure Feature
──────────────────────────────────
Para cada sensor y radio de buffer [50, 100, 250, 500 m]:
  TWE_r = Σ (aadf_total / (dist_m² + 1))
  donde la suma es sobre tramos viarios con centroide dentro del buffer.
Añade columna traffic_weighted_exposure a lur_features.csv (una fila por sensor×buffer_m).
"""
from pathlib import Path
import logging
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# CONFIG
ROOT      = Path(__file__).resolve().parents[2]
DATA_INT  = ROOT / "data" / "interim"

SENSORS_GPKG = DATA_INT / "sensores_snapped.gpkg"
STREETS_GPKG = DATA_INT / "streets_with_traffic.gpkg"
FEATURES_CSV = DATA_INT / "lur_features.csv"
BUFFER_RADII = [50, 100, 250, 500]


# CÁLCULO TWE
def compute_twe(sensors: gpd.GeoDataFrame, streets: gpd.GeoDataFrame) -> pd.DataFrame:
    """Devuelve DataFrame con columnas [sensor_id, buffer_m, traffic_weighted_exposure]."""
    streets = streets.copy()
    streets["centroid_x"] = streets.geometry.centroid.x
    streets["centroid_y"] = streets.geometry.centroid.y
    streets["aadf"] = streets["aadf_total"].fillna(0.0)

    records = []
    for _, sensor in sensors.iterrows():
        sid = sensor["sensor_id"]
        sx = sensor.geometry.x
        sy = sensor.geometry.y

        # Distancia² de cada centroide al sensor (vectorizado)
        dx = streets["centroid_x"] - sx
        dy = streets["centroid_y"] - sy
        dist2 = dx**2 + dy**2

        for radius in BUFFER_RADII:
            mask = dist2 <= (radius ** 2)
            if mask.sum() == 0:
                twe = 0.0
            else:
                twe = float((streets.loc[mask, "aadf"] / (dist2[mask] + 1.0)).sum())

            records.append({
                "sensor_id": sid,
                "buffer_m":  radius,
                "traffic_weighted_exposure": twe,
            })

    return pd.DataFrame(records)


# MAIN
def main():
    log.info("Cargando datos...")
    sensors = gpd.read_file(SENSORS_GPKG).to_crs(27700)
    streets = gpd.read_file(STREETS_GPKG).to_crs(27700)
    log.info("  Sensores: %d | Tramos: %d", len(sensors), len(streets))

    log.info("Calculando traffic-weighted exposure...")
    df_twe = compute_twe(sensors, streets)
    log.info("  TWE calculado: %s", df_twe.shape)

    # Cargar features y limpiar columna previa si existe (idempotencia)
    df_feat = pd.read_csv(FEATURES_CSV)
    log.info("  lur_features.csv antes: %s", df_feat.shape)

    if "traffic_weighted_exposure" in df_feat.columns:
        df_feat = df_feat.drop(columns=["traffic_weighted_exposure"])
        log.info("  Columna previa traffic_weighted_exposure eliminada.")

    # Merge: una fila por sensor_id × buffer_m
    df_merged = df_feat.merge(df_twe, on=["sensor_id", "buffer_m"], how="left")
    df_merged["traffic_weighted_exposure"] = df_merged["traffic_weighted_exposure"].fillna(0.0)

    log.info("  lur_features.csv después: %s", df_merged.shape)
    twe = df_merged["traffic_weighted_exposure"]
    log.info(
        "  TWE stats — min: %.2f | max: %.2f | mean: %.2f",
        twe.min(), twe.max(), twe.mean(),
    )

    df_merged.to_csv(FEATURES_CSV, index=False)
    log.info("Guardado en %s", FEATURES_CSV)


if __name__ == "__main__":
    main()
