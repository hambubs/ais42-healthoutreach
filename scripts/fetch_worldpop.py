"""
Fetch WorldPop population density for the Bengaluru-outskirts pilot.

Primary path : rasterio /vsicurl/ windowed read of the 100m India GeoTIFF
               (1.5 GB on the server — only the pilot bbox window is
               actually transferred over HTTP range requests)
Fallback path: download the 17 MB 1km India file (verified) and clip it.

Output -> backend/data/clean/enrichment/worldpop/
    blr_pop_cells.json  [[lat, lon, pop], ...] cells with pop > 0
    blr_pop_meta.json   bounds, total population, resolution used, provenance

The Streamlit "WorldPop Density" tab consumes these files directly — no
rasterio needed at runtime (HeatMap rendering via folium).
"""
import json
import urllib.request
from pathlib import Path

import numpy as np
import rasterio

OUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "clean" / "enrichment" / "worldpop"
OUT.mkdir(parents=True, exist_ok=True)
RAW = Path(__file__).resolve().parents[1] / "backend" / "data" / "raw"

# Bengaluru-outskirts pilot: Bengaluru Rural, Ramanagara, Kolar, Tumakuru fringe
BBOX = (76.95, 12.60, 78.30, 13.55)  # lon_min, lat_min, lon_max, lat_max

URL_100M = ("https://data.worldpop.org/GIS/Population/Global_2000_2020/"
            "2020/IND/ind_ppp_2020_UNadj.tif")
URL_1KM = ("https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/"
           "2020/IND/ind_ppp_2020_1km_Aggregated_UNadj.tif")

CELL = 0.01  # aggregation grid (~1.1 km) for the heat layer


def read_window(url_or_path, vsicurl=False):
    src_url = f"/vsicurl/{url_or_path}" if vsicurl else str(url_or_path)
    with rasterio.open(src_url) as src:
        win = rasterio.windows.from_bounds(*BBOX, transform=src.transform)
        arr = src.read(1, window=win)
        bounds = rasterio.windows.bounds(win, src.transform)
        return arr, bounds


def main():
    arr = None
    res_label = None
    try:
        print("Trying 100m /vsicurl windowed read (bbox-only transfer)...")
        with rasterio.Env(GDAL_HTTP_TIMEOUT="60", GDAL_HTTP_MAX_RETRY="3"):
            arr, bounds = read_window(URL_100M, vsicurl=True)
        res_label = "100m"
        print(f"100m window read OK: {arr.shape}")
    except Exception as exc:  # noqa: BLE001
        print(f"100m path failed ({exc}); falling back to the 17MB 1km file")
        cache = RAW / "ind_ppp_2020_1km_UNadj.tif"
        if not cache.exists():
            print("downloading 1km fallback (17 MB)...")
            urllib.request.urlretrieve(URL_1KM, cache)
        arr, bounds = read_window(cache)
        res_label = "1km"
        print(f"1km window read OK: {arr.shape}")

    arr = np.nan_to_num(arr.astype("float64"), nan=0.0, posinf=0.0, neginf=0.0)
    arr = np.clip(arr, 0, None)
    total = float(arr.sum())

    # cell-center lat/lon grid for the window
    h, w = arr.shape
    lons = np.linspace(bounds[0], bounds[2], w)
    lats = np.linspace(bounds[3], bounds[1], h)  # top -> bottom
    lon_g, lat_g = np.meshgrid(lons, lats)

    # aggregate to CELL-degree grid
    ix = np.floor((lon_g - BBOX[0]) / CELL).astype(int)
    iy = np.floor((BBOX[3] - lat_g) / CELL).astype(int)
    gx, gy = int((BBOX[2] - BBOX[0]) / CELL) + 1, int((BBOX[3] - BBOX[1]) / CELL) + 1
    acc = np.zeros((gy, gx))
    np.add.at(acc, (iy.ravel(), ix.ravel()), arr.ravel())

    cells = []
    for j in range(gy):
        for i in range(gx):
            p = acc[j, i]
            if p <= 0:
                continue
            cells.append([round(BBOX[3] - (j + 0.5) * CELL, 5),
                          round(BBOX[0] + (i + 0.5) * CELL, 5),
                          round(float(p), 2)])

    (OUT / "blr_pop_cells.json").write_text(json.dumps(cells))
    meta = {
        "bbox": BBOX,
        "total_population_in_bbox": int(total),
        "cells": len(cells),
        "cell_size_deg": CELL,
        "worldpop_resolution": res_label,
        "source": "WorldPop Global 2000-2020, India 2020 (UNadj)",
        "license": "CC-BY 4.0",
        "url": URL_100M if res_label == "100m" else URL_1KM,
        "pilot_districts": ["Bengaluru Rural", "Ramanagara", "Kolar", "Tumakuru"],
    }
    (OUT / "blr_pop_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"resolution used : {res_label}")
    print(f"population in bbox: {int(total):,}")
    print(f"heat cells written: {len(cells)} -> {OUT}")


if __name__ == "__main__":
    main()