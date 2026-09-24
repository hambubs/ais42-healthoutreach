"""Seed: district alias fixes, filtered district GeoJSON, DHS + HeiGIT extracts.

Run AFTER scripts/prep_data.py:
    python scripts/seed.py
"""
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1] / "backend"
RAW = BASE / "data" / "raw"
CLEAN = BASE / "data" / "clean"
(CLEAN / "enrichment").mkdir(parents=True, exist_ok=True)

# dataset district -> names used in the government hospital directory
DISTRICT_ALIASES = {
    "Kanpur": ["Kanpur Nagar", "Kanpur Dehat"],
    "Prayagraj": ["Allahabad"],
}
# Karnataka pilot districts (name variants across sources)
KARNATAKA_PILOT = ["Bengaluru Rural", "Bangalore Rural", "Bengaluru Urban", "Bangalore Urban",
                   "Ramanagara", "Ramanagaram", "Kolar", "Tumakuru", "Tumkur"]


def main():
    # ---------------- 1. district summary: alias-aware facility counts --------
    ds = pd.read_csv(CLEAN / "district_summary.csv")
    f = pd.read_csv(RAW / "hospital_directory.csv", low_memory=False)
    f.columns = [c.strip() for c in f.columns]
    parts = f["Location_Coordinates"].astype(str).str.split(",", expand=True)
    f["lat"] = pd.to_numeric(parts[0], errors="coerce")
    f["lon"] = pd.to_numeric(parts[1], errors="coerce") if parts.shape[1] > 1 else float("nan")
    f["valid"] = f["lat"].between(6, 38) & f["lon"].between(68, 98)

    totals, mapped = [], []
    for _, r in ds.iterrows():
        names = DISTRICT_ALIASES.get(r["District"], [r["District"]])
        m = (f["State"] == r["State"]) & (f["District"].isin(names))
        totals.append(int(m.sum()))
        mapped.append(int((m & f["valid"]).sum()))
    ds["facilities_directory"] = totals   # all rows in gov directory (aliases incl.)
    ds["facilities_mapped"] = mapped       # subset with valid coordinates
    ds.to_csv(CLEAN / "district_summary.csv", index=False)
    print("district_summary.csv updated with alias-aware facility counts")

    # ---------------- 2. filtered district boundaries GeoJSON ---------------
    gj = json.loads((RAW / "india_adm2.geojson").read_text(encoding="utf-8"))
    keep = set()
    for _, r in ds.iterrows():
        keep.update(DISTRICT_ALIASES.get(r["District"], [r["District"]]))
    keep.update(KARNATAKA_PILOT)
    feats = [ft for ft in gj["features"]
             if str(ft.get("properties", {}).get("shapeName", "")) in keep]
    out = {"type": "FeatureCollection", "features": feats}
    (CLEAN / "enrichment" / "districts.geojson").write_text(json.dumps(out), encoding="utf-8")
    print(f"districts.geojson: kept {len(feats)} of {len(gj['features'])} features")

    # ---------------- 3. DHS extract (latest survey, state level) -----------
    rows = []
    for name in ["dhs_anemia_subnational_ind.csv",
                 "dhs_access_to_health_care_subnational_ind.csv"]:
        d = pd.read_csv(RAW / name, low_memory=False)
        yr = d["SurveyYear"].max()
        dd = d[(d["SurveyYear"] == yr) & (d["IsTotal"] == 1) & (d["LevelRank"] == 1)]
        if dd.empty:
            dd = d[(d["SurveyYear"] == yr) & (d["IsPreferred"] == 1) & (d["LevelRank"] == 1)]
        for _, r in dd.iterrows():
            rows.append({"state": r["Location"], "indicator": r["Indicator"],
                         "value": r["Value"], "survey": r["SurveyYearLabel"]})
    pd.DataFrame(rows).to_csv(CLEAN / "enrichment" / "dhs_state_indicators.csv", index=False)
    print(f"dhs_state_indicators.csv: {len(rows)} rows (survey year {yr})")

    # ---------------- 4. HeiGIT validation extract ---------------------------
    rows = []
    for cat, fname in [("hospitals", "heigit_hospitals_access_wide.csv"),
                       ("primary_healthcare", "heigit_phc_access_wide.csv")]:
        d = pd.read_csv(RAW / fname, low_memory=False)
        dd = d[(d["admin_level"] == "ADM1") & (d["range"] == 1800)]
        for _, r in dd.iterrows():
            rows.append({"state": r["name"], "category": cat,
                         "within_30min_pop_share_pct": round(float(r["population_share"]), 2)})
    pd.DataFrame(rows).to_csv(CLEAN / "enrichment" / "heigit_state_access.csv", index=False)
    print(f"heigit_state_access.csv: {len(rows)} rows")

    print("seed complete")


if __name__ == "__main__":
    main()
