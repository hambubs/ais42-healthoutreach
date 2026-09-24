"""One-off diagnostic: why is Maharashtra|Aurangabad still anchored in Bihar?"""
import json
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "backend"
RAW = BASE / "data" / "raw"
CLEAN = BASE / "data" / "clean"


def outer_rings(ft):
    g = ft["geometry"]
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    if g["type"] == "MultiPolygon":
        return [p[0] for p in g["coordinates"]]
    return []


def fold(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip().lower()


def in_ring(lon, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def in_any(lon, lat, rings):
    return any(in_ring(lon, lat, r) for r in rings)


def centroid(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return sum(xs) / len(xs), sum(ys) / len(ys)


adm1 = json.loads((RAW / "india_adm1.geojson").read_text(encoding="utf-8"))
print("ADM1 features:", len(adm1["features"]))
print("ALL folded ADM1 names:")
for ft in adm1["features"]:
    nm = ft["properties"].get("shapeName", "")
    print("  ", fold(nm))

state_rings = {fold(ft["properties"].get("shapeName", "")): outer_rings(ft) for ft in adm1["features"]}
sp = state_rings.get(fold("Maharashtra"))
print("fold('Maharashtra') lookup:", "FOUND" if sp else "MISSING")

gj = json.loads((CLEAN / "enrichment" / "districts.geojson").read_text(encoding="utf-8"))
aur = [ft for ft in gj["features"] if ft["properties"].get("shapeName") == "Aurangabad"]
print("Aurangabad candidates in districts.geojson:", len(aur))
for k, ft in enumerate(aur):
    cx, cy = centroid(outer_rings(ft))
    inside = in_any(cx, cy, sp) if sp else None
    print(f"  cand {k}: centroid ({cx:.2f}, {cy:.2f}) inside Maharashtra: {inside}")
