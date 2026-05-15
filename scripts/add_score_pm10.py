"""
Add score_pm10 to the existing Supabase lsoa.geojson.
Reads from a downloaded copy, computes score_pm10 from PM10_final,
saves the result ready for re-upload.
"""
import json
from pathlib import Path

INPUT  = Path(__file__).resolve().parent.parent / "outputs" / "maps" / "lsoa_supabase_with_pm10.geojson"
SOURCE = Path(__file__).resolve().parent.parent / "outputs" / "maps" / "lsoa_supabase_input.geojson"


def pm10_score(v: float | None) -> str | None:
    if v is None:
        return None
    if v < 15:
        return "A"
    if v < 30:
        return "B"
    if v < 45:
        return "C"
    if v < 60:
        return "D"
    if v < 75:
        return "E"
    return "F"


def main() -> None:
    gj = json.loads(SOURCE.read_text(encoding="utf-8"))
    n = 0
    for feat in gj["features"]:
        p = feat["properties"]
        v = p.get("PM10_final")
        p["score_pm10"] = pm10_score(v)
        n += 1
    INPUT.write_text(json.dumps(gj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"OK: {n} features → {INPUT.name}")
    sample = gj["features"][0]["properties"]
    print("sample cols:", sorted(sample.keys()))
    print("sample score_pm10:", sample.get("score_pm10"))


if __name__ == "__main__":
    main()
