"""
Geographic normalization for the provided village dataset (fix_geo).

WHY: the provided dataset's Latitude/Longitude are synthetic-uniform —
every state's villages span the same 18-27N / 72-88E box, which renders
as a giant square on the map instead of real settlement geography.

WHAT THIS DOES:
  * Re-anchors every village to a plausible position INSIDE its own
    district polygon (geoBoundaries ADM2), around clustered settlement
    centers with ~3 km Gaussian scatter — the way real villages cluster.
  * PRESERVES the provided coordinates in Latitude_orig / Longitude_orig.
  * Touches NOTHING else: population, travel times, risk, flags and the
    need score stay exactly as provided/derived. The baseline coverage
    (13.82%) is computed from provided travel times and does not change.

Run order: prep_data.py -> fix_geo.py -> seed.py
Provenance: documented in DATA_SOURCES.md ("Geographic normalization").
"""
import json
import unicodedata
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1] / "backend"
RAW = BASE / "data" / "raw"
CLEAN = BASE / "data" / "clean"

ALIASES = {"Kanpur": ["Kanpur Nagar", "Kanpur Dehat"], "Prayagraj": ["Allahabad"]}
SIGMA_DEG = 0.03      # ~3.3 km scatter around settlement centers
PER_CENTER = 40       # villages per settlement center


def outer_rings(ft):
    g = ft["geometry"]
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    if g["type"] == "MultiPolygon":
        return [poly[0] for poly in g["coordinates"]]
    return []


def in_ring(lon, lat, ring):
    """Even-odd ray casting. ring = [[lon, lat], ...]"""
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


def rings_bbox(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def centroid(rings):
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def sample_inside(rings, rng, n, tries=500):
    x0, y0, x1, y1 = rings_bbox(rings)
    out = []
    for _ in range(n):
        for _ in range(tries):
            lon, lat = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if in_any(lon, lat, rings):
                out.append((lon, lat))
                break
    return out


def main():
    v = pd.read_csv(CLEAN / "villages_clean.csv")
    if "Latitude_orig" in v.columns:
        print("orig columns found — restoring provided coordinates before re-anchoring")
        v["Latitude"] = v["Latitude_orig"]
        v["Longitude"] = v["Longitude_orig"]
    else:
        v["Latitude_orig"] = v["Latitude"]
        v["Longitude_orig"] = v["Longitude"]

    gj = json.loads((CLEAN / "enrichment" / "districts.geojson").read_text(encoding="utf-8"))
    adm1 = json.loads((RAW / "india_adm1.geojson").read_text(encoding="utf-8"))
    def fold(s):
        """ASCII-fold: geoBoundaries uses diacritics (Mahārāshtra, Bihār)."""
        return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip().lower()

    state_rings = {fold(ft["properties"].get("shapeName", "")): outer_rings(ft) for ft in adm1["features"]}

    by_name = {}
    for ft in gj["features"]:
        by_name.setdefault(ft["properties"].get("shapeName", ""), []).append(ft)

    # resolve each (state, district) -> polygon rings
    # (handles the Aurangabad MH/BR ambiguity via the ADM1 state polygon)
    resolved = {}
    for (state, district), _ in v.groupby(["State", "District"]):
        names = ALIASES.get(district, [district])
        cands = [ft for n in names for ft in by_name.get(n, [])]
        if not cands:
            print(f"WARN no polygon for {district}, {state} — coords unchanged")
            continue
        chosen = cands[0]
        if len(cands) > 1:
            sp = state_rings.get(fold(state))
            if sp:
                for ft in cands:
                    cx, cy = centroid(outer_rings(ft))
                    if in_any(cx, cy, sp):
                        chosen = ft
                        break
        resolved[(state, district)] = outer_rings(chosen)

    moved = 0
    for (state, district), g in v.groupby(["State", "District"]):
        rings = resolved.get((state, district))
        if not rings:
            continue
        rng = np.random.default_rng(zlib.crc32(f"{state}|{district}".encode()) & 0xFFFFFFFF)
        n = len(g)
        centers = sample_inside(rings, rng, max(3, n // PER_CENTER))
        if not centers:
            continue
        lats, lons = [], []
        for i in range(n):
            cx, cy = centers[i % len(centers)]
            lat = lon = None
            for _ in range(80):
                tlon = cx + rng.normal(0, SIGMA_DEG)
                tlat = cy + rng.normal(0, SIGMA_DEG)
                if in_any(tlon, tlat, rings):
                    lat, lon = tlat, tlon
                    break
            if lat is None:
                lat, lon = cy, cx
            lats.append(lat)
            lons.append(lon)
        v.loc[g.index, "Latitude"] = lats
        v.loc[g.index, "Longitude"] = lons
        moved += n

    v.to_csv(CLEAN / "villages_clean.csv", index=False)
    print(f"re-anchored {moved:,} villages into their district polygons")
    chk = v.groupby(["State", "District"]).agg(
        lat_min=("Latitude", "min"), lat_max=("Latitude", "max"),
        lon_min=("Longitude", "min"), lon_max=("Longitude", "max")).round(2)
    print(chk.to_string())


if __name__ == "__main__":
    main()
