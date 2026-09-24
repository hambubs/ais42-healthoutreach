"""Smoke test: exercise every backend endpoint via the Flask test client."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import app  # noqa: E402
from models import db  # noqa: E402

with app.app_context():
    db.create_all()

c = app.test_client()


def show(label, resp, n=140):
    body = resp.get_data(as_text=True)
    print(f"{label:32s} {resp.status_code}  len={len(body):>8}  {body[:n]}")


show("GET /api/baseline", c.get("/api/baseline"))
show("GET /api/villages?state=Bihar", c.get("/api/villages?state=Bihar"))
show("GET /api/facilities?state=Bihar", c.get("/api/facilities?state=Bihar"))
show("GET /api/districts", c.get("/api/districts"))
show("GET /api/dhs", c.get("/api/dhs"))
show("GET /api/heigit", c.get("/api/heigit"))
show("GET /api/geojson/districts", c.get("/api/geojson/districts"))
show("GET /api/modes", c.get("/api/modes"))

r = c.post("/api/optimize", json={"fleet_size": 3, "max_minutes": 30})
show("POST /api/optimize", r, 500)
show("GET /api/outposts", c.get("/api/outposts"))

r = c.post("/api/sos-alert", json={"node_id": "ESP_VIL_42", "sos_type": "maternal",
                                   "priority": "critical", "lat": 25.5, "lon": 82.9})
show("POST /api/sos-alert", r, 200)
show("GET /api/sos-alerts", c.get("/api/sos-alerts"))

r = c.post("/api/sync", json={"alerts": [{"node_id": "HUB-01", "sos_type": "trauma",
                                          "lat": 26.0, "lon": 80.0}]})
show("POST /api/sync", r, 200)

r = c.post("/api/dispatch", json={"mode": "uav", "lat": 25.5, "lon": 82.9})
show("POST /api/dispatch (uav)", r, 300)
r = c.post("/api/dispatch", json={"mode": "ambulance", "lat": 25.5, "lon": 82.9, "alert_id": 1})
show("POST /api/dispatch (ambulance)", r, 200)
show("GET /api/dispatches", c.get("/api/dispatches"))

show("POST /api/track", c.post("/api/track", json={"device_id": "MMU-01",
                                                   "latitude": 25.6, "longitude": 82.8}))
show("GET /api/track", c.get("/api/track?device_id=MMU-01"))

# --- LOD checks: district centroids + village bbox filter ---
import json as _json
r3 = c.get("/api/districts")
d = _json.loads(r3.get_data(as_text=True))
has_ll = all(x.get("lat") is not None and x.get("lon") is not None for x in d)
print(f"district centroids: {r3.status_code} rows={len(d)} lat/lon={'PASS' if has_ll else 'FAIL'} "
      f"sample={d[0].get('District')} ({d[0].get('lat')}, {d[0].get('lon')})")

r = c.get("/api/villages?bbox=79.9,25.9,80.6,27.0")
rows = _json.loads(r.get_data(as_text=True))
ok = all(25.9 <= x["Latitude"] <= 27.0 and 79.9 <= x["Longitude"] <= 80.6 for x in rows)
print(f"bbox villages: {r.status_code} count={len(rows)} containment={'PASS' if ok else 'FAIL'}")
r2 = c.get("/api/villages?bbox=abc")
print(f"invalid bbox: {r2.status_code} (expect 400)")

print("\nSMOKE TEST DONE")
