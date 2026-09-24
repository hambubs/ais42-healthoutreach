"""Quick verification of the refined clustering + coverage numbers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import optimizer  # noqa: E402

v, _, _ = optimizer.load_data()
cands, noise, method, labeled = optimizer.dbscan_candidates(v)
print("method:", method, "| candidates:", len(cands),
      "| circuit sizes min/max:", cands.villages.min(), "/", cands.villages.max(),
      "| noise villages:", len(noise))

for fleet in (3, 5, 8):
    r = optimizer.optimize(fleet_size=fleet)
    sc = r["scheduled_care"]
    print(f"fleet {fleet} | 30-min emergency: {r['baseline']['coverage_pct_villages']} -> "
          f"{r['after']['coverage_pct_villages']} | scheduled care: {sc['coverage_pct_villages']}% "
          f"villages | new pop served: {sc['new_population']:,}")

r = optimizer.optimize(fleet_size=3)
for o in r["outposts"]:
    print(f"{o['outpost_id']} {o['anchor_district']:12s} | circuit villages: "
          f"{o['circuit_villages']:4d} | circuit pop: {o['circuit_population']:,} "
          f"| 30-min new: {o['emergency_new_villages']}")
