"""
AIS-42 | PS-4B Rural Healthcare Reachability & Outpost Planning
Phase 0 data prep.

Inputs  : backend/data/raw/villages_12k.csv        (provided dataset, 12,000 villages)
          backend/data/raw/hospital_directory.csv  (provided dataset, 30,273 facilities)
Outputs : backend/data/clean/villages_clean.csv
          backend/data/clean/facilities_clean.csv
          backend/data/clean/district_summary.csv
          backend/data/clean/baseline_stats.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "backend" / "data" / "raw"
CLEAN = HERE.parent / "backend" / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ villages
v = pd.read_csv(RAW / "villages_12k.csv")
v.columns = [c.strip() for c in v.columns]

NUM = ["Latitude", "Longitude", "Population", "Male_Population", "Female_Population",
       "Elderly_Population", "Child_Population", "Doctors_Count", "Nurses_Count",
       "Beds_Available", "Distance_to_Hospital_km", "Average_Travel_Time_min",
       "Accessibility_Score", "Monthly_Patient_Count"]
for c in NUM:
    v[c] = pd.to_numeric(v[c], errors="coerce")
v = v.dropna(subset=["Latitude", "Longitude", "Population"]).copy()

ROAD_SPEED = {"Good": 40.0, "Average": 25.0, "Poor": 12.0}     # effective km/h
RISK_N = {"Low": 0.2, "Medium": 0.5, "High": 1.0}
v["road_speed_kmph"] = v["Road_Connectivity"].map(ROAD_SPEED)
v["risk_norm"] = v["Healthcare_Risk_Level"].map(RISK_N)
for c in ["Emergency_Service", "Ambulance_Availability", "Doctor_Shortage_Flag", "Underserved_Area_Flag"]:
    v[c + "_bin"] = v[c].astype(str).str.strip().str.lower().map({"yes": 1, "no": 0})

# Healthcare Need Score (0..1): population 40%, epidemiological risk 30%, inaccessibility 30%
pop_n = (v["Population"] - v["Population"].min()) / (v["Population"].max() - v["Population"].min())
acc_n = v["Accessibility_Score"] / 100.0
v["need_score"] = (0.4 * pop_n + 0.3 * v["risk_norm"] + 0.3 * (1 - acc_n)).round(4)

# baseline 30-min coverage from EXISTING facilities
cov = v["Average_Travel_Time_min"] <= 30
baseline = {
    "villages": int(len(v)),
    "covered_villages_30min": int(cov.sum()),
    "coverage_pct_villages": round(100 * cov.mean(), 2),
    "coverage_pct_population": round(100 * v.loc[cov, "Population"].sum() / v["Population"].sum(), 2),
    "underserved_villages": int(v["Underserved_Area_Flag_bin"].sum()),
    "avg_travel_min": round(float(v["Average_Travel_Time_min"].mean()), 1),
    "avg_distance_km": round(float(v["Distance_to_Hospital_km"].mean()), 1),
    "poor_road_villages": int((v["Road_Connectivity"] == "Poor").sum()),
    "high_risk_villages": int((v["Healthcare_Risk_Level"] == "High").sum()),
}

# --------------------------------------------------------------- facilities
f = pd.read_csv(RAW / "hospital_directory.csv", low_memory=False)
f.columns = [c.strip() for c in f.columns]
parts = f["Location_Coordinates"].astype(str).str.split(",", expand=True)
f["lat"] = pd.to_numeric(parts[0], errors="coerce")
f["lon"] = pd.to_numeric(parts[1], errors="coerce") if parts.shape[1] > 1 else np.nan
f = f[f["lat"].between(6, 38) & f["lon"].between(68, 98)].copy()


def _int(x):
    try:
        return int(float(str(x).strip()))
    except (ValueError, TypeError):
        return 0


f["beds"] = f["Total_Num_Beds"].map(_int)
f["doctors"] = f["Number_Doctor"].map(_int)
f["has_emergency"] = ~f["Emergency_Services"].astype(str).str.strip().isin(["0", "0.0", "", "nan", "No"])
f["has_ambulance"] = ~f["Ambulance_Phone_No"].astype(str).str.strip().isin(["0", "0.0", "", "nan"])

fac = f[["Hospital_Name", "State", "District", "Subdistrict", "lat", "lon",
         "beds", "doctors", "has_emergency", "has_ambulance"]].copy()

# ------------------------------------------------------- district join table
ds = v.groupby(["State", "District"]).agg(
    villages=("Village_ID", "count"),
    population=("Population", "sum"),
    avg_travel_min=("Average_Travel_Time_min", "mean"),
    underserved=("Underserved_Area_Flag_bin", "sum"),
    high_risk=("risk_norm", lambda s: int((s >= 1.0).sum())),
    mean_need=("need_score", "mean"),
).reset_index()
fs = fac.groupby(["State", "District"]).agg(
    facilities=("Hospital_Name", "count"),
    emergency_facilities=("has_emergency", "sum"),
    beds=("beds", "sum"),
).reset_index()
ds = ds.merge(fs, on=["State", "District"], how="left")
for c in ["facilities", "emergency_facilities", "beds"]:
    ds[c] = ds[c].fillna(0).astype(int)

v.to_csv(CLEAN / "villages_clean.csv", index=False)
fac.to_csv(CLEAN / "facilities_clean.csv", index=False)
ds.to_csv(CLEAN / "district_summary.csv", index=False)
(CLEAN / "baseline_stats.json").write_text(json.dumps(baseline, indent=2))

print("=== BASELINE (existing facilities only) ===")
print(json.dumps(baseline, indent=2))
print("\n=== Districts ranked by underserved count ===")
print(ds.sort_values("underserved", ascending=False).to_string(index=False))
print(f"\nFacilities with valid coords: {len(fac):,} / 30,273")
print(f"Facility states covered    : {fac['State'].nunique()}")
print("\n=== Emergency_Services raw values (top 8) ===")
print(f["Emergency_Services"].astype(str).value_counts().head(8).to_string())
