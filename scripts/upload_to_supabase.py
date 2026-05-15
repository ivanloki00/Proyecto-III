"""
Upload PM10-enriched files to Supabase Storage (bucket: geojson).
Uses the public bucket's anon-INSERT/UPDATE policies — no service-role key needed.
"""
from pathlib import Path
import sys
import urllib.request
import urllib.error

PROJECT_REF = "tmzxlqbpwokmvpsgzjbh"
ANON_KEY = "sb_publishable_HFs3yMhS535h4iTI968p-w_k8yG5xDn"
BUCKET = "geojson"

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = [
    (ROOT / "outputs" / "maps" / "lsoa_supabase_with_pm10.geojson", "lsoa.geojson",                "application/geo+json"),
    (ROOT / "outputs" / "maps" / "lsoa_supabase_with_pm10.geojson", "lur_lsoa_predictions.geojson", "application/geo+json"),
    (ROOT / "outputs" / "stlur_predictions.csv",                    "timeseries.csv",              "text/csv"),
]


def upload(local: Path, remote: str, mime: str) -> None:
    url = f"https://{PROJECT_REF}.supabase.co/storage/v1/object/{BUCKET}/{remote}"
    body = local.read_bytes()
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Bearer {ANON_KEY}",
            "apikey": ANON_KEY,
            "Content-Type": mime,
            "x-upsert": "true",
            "Cache-Control": "max-age=0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"OK  {remote}  ({len(body):,} bytes)  status={resp.status}")
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        print(f"ERR {remote}  status={e.code}  body={msg[:200]}")
        sys.exit(1)


def main() -> None:
    for local, remote, mime in UPLOADS:
        if not local.exists():
            print(f"MISSING: {local}")
            sys.exit(1)
        upload(local, remote, mime)
    print("All uploads done.")


if __name__ == "__main__":
    main()
