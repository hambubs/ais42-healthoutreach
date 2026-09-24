"""Peek at DHS / HeiGIT CSV structures so the backend can wire them correctly."""
import pathlib

import pandas as pd

RAW = pathlib.Path(__file__).resolve().parents[1] / "backend" / "data" / "raw"
FILES = [
    "dhs_anemia_subnational_ind.csv",
    "dhs_access_to_health_care_subnational_ind.csv",
    "heigit_phc_access_wide.csv",
    "heigit_hospitals_access_wide.csv",
]
for name in FILES:
    df = pd.read_csv(RAW / name, nrows=4, low_memory=False)
    print(f"=== {name} ===")
    print("columns:", list(df.columns))
    print(df.head(3).to_string(max_colwidth=28))
    print()
