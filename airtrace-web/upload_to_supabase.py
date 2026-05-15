"""
upload_to_supabase.py
---------------------
Sube los archivos de datos estáticos al bucket "geojson" de Supabase Storage.

Uso:
    python upload_to_supabase.py --key <SERVICE_ROLE_KEY>

El SERVICE_ROLE_KEY lo encuentras en:
    Supabase Dashboard → Project Settings → API → service_role (secret)

Requiere: requests  (pip install requests)
"""

import argparse
import mimetypes
import sys
from pathlib import Path

import requests

# ── CONFIG ──────────────────────────────────────────────────────────────────
SUPABASE_URL = "https://tmzxlqbpwokmvpsgzjbh.supabase.co"
BUCKET = "geojson"

# Raíz de este script (airtrace-web/)
ROOT = Path(__file__).parent

# (ruta local relativa a ROOT, nombre en el bucket)
FILES = [
    (ROOT / "public" / "data" / "lsoa.geojson",              "lsoa.geojson"),
    (ROOT / "public" / "data" / "streets.geojson",            "streets.geojson"),
    (ROOT / "public" / "data" / "sensors.geojson",            "sensors.geojson"),
    (ROOT / "public" / "data" / "lsoa_ward_lookup.json",      "lsoa_ward_lookup.json"),
    (ROOT / "public" / "data" / "sensor_timeline.json",       "sensor_timeline.json"),
    (ROOT / "public" / "data" / "timeseries.csv",             "timeseries.csv"),
    # lur_lsoa_predictions.geojson viene del pipeline (un nivel arriba)
    (ROOT.parent / "outputs" / "maps" / "lur_lsoa_predictions.geojson", "lur_lsoa_predictions.geojson"),
]
# ── FIN CONFIG ───────────────────────────────────────────────────────────────


def upload(local_path: Path, bucket_path: str, headers: dict) -> None:
    if not local_path.exists():
        print(f"  ⚠  SKIP  {bucket_path}  (no encontrado: {local_path})")
        return

    content_type, _ = mimetypes.guess_type(str(local_path))
    if content_type is None:
        content_type = "application/octet-stream"

    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{bucket_path}"
    data = local_path.read_bytes()

    # Intenta UPSERT (PUT) para no fallar si el archivo ya existe
    resp = requests.put(
        url,
        data=data,
        headers={**headers, "Content-Type": content_type, "x-upsert": "true"},
    )

    if resp.status_code in (200, 201):
        size_kb = len(data) / 1024
        print(f"  ✓  {bucket_path}  ({size_kb:.0f} KB)")
    else:
        print(f"  ✗  {bucket_path}  →  HTTP {resp.status_code}: {resp.text[:200]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sube datos a Supabase Storage")
    parser.add_argument("--key", required=True, help="Supabase service_role key")
    args = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {args.key}",
        "apikey": args.key,
    }

    print(f"Subiendo {len(FILES)} archivos a {SUPABASE_URL}/storage/v1/object/public/{BUCKET}/\n")
    errors = 0
    for local_path, bucket_path in FILES:
        upload(local_path, bucket_path, headers)
        if not local_path.exists():
            errors += 1

    print(f"\nListo. {len(FILES) - errors}/{len(FILES)} archivos procesados.")
    if errors:
        print("Revisa los archivos marcados con ⚠ arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()
