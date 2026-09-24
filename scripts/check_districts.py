"""List district names in the hospital directory per state to fix name mismatches."""
import pathlib

import pandas as pd

RAW = pathlib.Path(__file__).resolve().parents[1] / "backend" / "data" / "raw"
f = pd.read_csv(RAW / "hospital_directory.csv", low_memory=False)
f.columns = [c.strip() for c in f.columns]
STATES = ["Uttar Pradesh", "Rajasthan", "Madhya Pradesh", "Maharashtra", "Bihar", "Karnataka"]
for s in STATES:
    d = sorted(f.loc[f["State"] == s, "District"].astype(str).unique())
    print(f"\n=== {s} ({len(d)} districts) ===")
    print(", ".join(d))
