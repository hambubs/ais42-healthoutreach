"""
AIS-42 HealthOutreach backend — PS-4B Rural Healthcare Reachability.
Flask API + ops console. Static datasets are served from in-memory pandas
(optimizer.load_data); SQLite stores live state (SOS alerts, dispatch jobs,
outposts, MMU breadcrumbs).
"""
import json
from pathlib import Path

import numpy as np
from flask import Flask, Response, jsonify, render_template, request, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

import optimizer
from models import DispatchJob, MmuTrack, Outpost, SosAlert, db

BASE = Path(__file__).resolve().parent
CLEAN = BASE / "data" / "clean"

app = Flask(__name__)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(BASE / "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


# ------------------------------------------------------------------ static UI
@app.get("/")
def index():
    return render_template("index.html")


# ------------------------------------------------- Hub page + mobile SOS
HUB_HTML = Path(__file__).resolve().parents[1] / "edge" / "hub_page" / "hub.html"
MOBILE_SOS_HTML = """
<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HealthOutreach — SOS</title>
<style>
:root{--bg:#0b1220;--card:#16233d;--accent:#22d3a7;--red:#e74c3c;--amber:#f39c12;--blue:#3b82f6;--text:#e8eefc}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:var(--bg);color:var(--text);
display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:16px}
h1{font-size:18px;margin-bottom:4px}.sub{font-size:11px;color:#8ea0c0;margin-bottom:18px;text-align:center;max-width:340px}
.btn{display:block;width:100%;max-width:340px;margin:10px 0;padding:22px;border-radius:14px;border:none;
font-size:18px;font-weight:700;color:#fff;cursor:pointer}.trauma{background:var(--red)}.mat{background:var(--amber)}.med{background:var(--blue)}
.ok{display:none;margin-top:14px;color:var(--accent);font-weight:700}.err{display:none;margin-top:14px;color:var(--red);font-weight:700}
</style></head><body>
<h1>🆘 Emergency SOS</h1>
<div class="sub">Mobile fallback · submits directly to the HealthOutreach server<br>
(use this when no MMU-GATEWAY Wi-Fi is available)</div>
<button class="btn trauma" onclick="sos('trauma','critical')">🩸 Trauma / Accident</button>
<button class="btn mat"     onclick="sos('maternal','critical')">🤰 Maternal Emergency</button>
<button class="btn med"    onclick="sos('medicine','high')">💊 Medicine Shortage</button>
<div class="ok" id="ok">✅ SOS sent — the command console has it</div>
<div class="err" id="err">❌ Failed — try again</div>
<script>
async function sos(type, priority){
  let lat = null, lon = null;
  if (navigator.geolocation) {
    try { const p = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, {timeout: 3000}));
      lat = p.coords.latitude; lon = p.coords.longitude; } catch (_) {}
  }
  try {
    const r = await fetch('/api/sos-alert', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: 'VIL-MOBILE', sos_type: type, priority,
        lat, lon, source: 'mobile_fallback' }) });
    if (r.ok) document.getElementById('ok').style.display = 'block';
    else document.getElementById('err').style.display = 'block';
  } catch { document.getElementById('err').style.display = 'block'; }
}
</script></body></html>
"""


@app.get("/hub")
def hub():
    if not HUB_HTML.exists():
        return "Hub page not found — ensure edge/hub_page/hub.html exists", 500
    return send_file(HUB_HTML, mimetype="text/html")


@app.get("/sos")
def mobile_sos():
    return Response(MOBILE_SOS_HTML, mimetype="text/html")


# ------------------------------------------------------- static data endpoints
@app.get("/api/baseline")
def api_baseline():
    return jsonify(optimizer.baseline_stats())


@app.get("/api/villages")
def api_villages():
    v, _, _ = optimizer.load_data()
    df = v
    state = request.args.get("state")
    if state:
        df = df[df["State"] == state]
    if request.args.get("underserved") == "1":
        df = df[(df["Underserved_Area_Flag_bin"] == 1) | (df["Average_Travel_Time_min"] > 30)]
    bbox = request.args.get("bbox")
    if bbox:
        try:
            lon_min, lat_min, lon_max, lat_max = [float(x) for x in bbox.split(",")]
            if not (lon_min < lon_max and lat_min < lat_max):
                raise ValueError
        except ValueError:
            return jsonify({"error": "bbox must be lon_min,lat_min,lon_max,lat_max "
                                     "with lon_min<lon_max and lat_min<lat_max"}), 400
        df = df[(df["Longitude"] >= lon_min) & (df["Longitude"] <= lon_max) &
                (df["Latitude"] >= lat_min) & (df["Latitude"] <= lat_max)]
    cols = ["Village_ID", "District", "State", "Latitude", "Longitude", "Population",
            "Average_Travel_Time_min", "Distance_to_Hospital_km", "Road_Connectivity",
            "Healthcare_Risk_Level", "Accessibility_Score", "need_score",
            "Underserved_Area_Flag_bin"]
    out = df[cols].copy()
    out["Latitude"] = out["Latitude"].round(4)
    out["Longitude"] = out["Longitude"].round(4)
    out["need_score"] = out["need_score"].round(3)
    out["Average_Travel_Time_min"] = out["Average_Travel_Time_min"].round(1)
    out["Distance_to_Hospital_km"] = out["Distance_to_Hospital_km"].round(1)
    return Response(out.to_json(orient="records"), mimetype="application/json")


@app.get("/api/facilities")
def api_facilities():
    _, fac, _ = optimizer.load_data()
    df = fac
    states = request.args.getlist("state")
    if states:
        df = df[df["State"].isin(states)]
    cols = ["Hospital_Name", "State", "District", "lat", "lon",
            "has_emergency", "has_ambulance", "beds", "doctors"]
    out = df[cols].copy()
    out["lat"] = out["lat"].round(5)
    out["lon"] = out["lon"].round(5)
    return Response(out.to_json(orient="records"), mimetype="application/json")


@app.get("/api/districts")
def api_districts():
    _, _, ds = optimizer.load_data()
    cents = optimizer.district_centroids()
    out = ds.copy()
    lats, lons = [], []
    for _, r in out.iterrows():
        c = cents.get((r["State"], r["District"]))
        lats.append(round(c[0], 5) if c else None)
        lons.append(round(c[1], 5) if c else None)
    out["lat"] = lats
    out["lon"] = lons
    return Response(out.to_json(orient="records"), mimetype="application/json")


@app.get("/api/dhs")
def api_dhs():
    """NFHS/DHS state-level indicators (latest survey)."""
    path = CLEAN / "enrichment" / "dhs_state_indicators.csv"
    if not path.exists():
        return jsonify([])
    import pandas as pd
    return Response(pd.read_csv(path).to_json(orient="records"), mimetype="application/json")


@app.get("/api/heigit")
def api_heigit():
    """HeiGIT validation: % of state population within 30 min of care."""
    path = CLEAN / "enrichment" / "heigit_state_access.csv"
    if not path.exists():
        return jsonify([])
    import pandas as pd
    return Response(pd.read_csv(path).to_json(orient="records"), mimetype="application/json")


@app.get("/api/geojson/districts")
def api_geojson_districts():
    path = CLEAN / "enrichment" / "districts.geojson"
    if not path.exists():
        return jsonify({"error": "run scripts/seed.py first"}), 404
    return send_file(path, mimetype="application/geo+json")


@app.get("/api/modes")
def api_modes():
    return jsonify(optimizer.DISPATCH_MODES)


# ------------------------------------------------- medical intelligence
ESSENTIAL_MEDS = ["Anti-venom", "Insulin", "Oxytocin", "ORS", "Amoxicillin",
                  "Paracetamol", "Anti-malarial", "Rabies vaccine"]


@app.post("/api/outpost-intel")
def api_outpost_intel():
    """Disease indicators (real DHS/NFHS state data) + simulated medicine
    stock matrix + cheap-sourcing suggestions for stockouts."""
    import zlib

    d = request.get_json(silent=True) or {}
    district = str(d.get("district") or "")
    if not district:
        return jsonify({"error": "district required"}), 400
    _, _, ds = optimizer.load_data()
    row = ds[ds["District"] == district]
    state = str(row.iloc[0]["State"]) if not row.empty else ""

    def med_status(dist, med):
        h = zlib.crc32(f"{dist}|{med}".encode()) % 10
        return "Stockout" if h <= 2 else ("Low" if h <= 4 else "Available")

    stock = [{"medicine": m, "status": med_status(district, m)} for m in ESSENTIAL_MEDS]
    stockouts = [s["medicine"] for s in stock if s["status"] == "Stockout"]

    sourcing = []
    if state:
        cents = optimizer.district_centroids()
        home = cents.get((state, district))
        peers = ds[ds["State"] == state]
        for med in stockouts:
            best, bestd = None, None
            for _, pr in peers.iterrows():
                if pr["District"] == district:
                    continue
                if med_status(pr["District"], med) != "Available":
                    continue
                c = cents.get((state, pr["District"]))
                if not c or not home:
                    continue
                dist = optimizer.haversine_km(home[0], home[1], c[0], c[1])
                if bestd is None or dist < bestd:
                    best, bestd = pr["District"], dist
            if best:
                sourcing.append({"medicine": med, "from": best,
                                 "note": f"{bestd:.0f} km · district warehouse rate"})

    diseases, survey = [], "NFHS"
    dhs_path = CLEAN / "enrichment" / "dhs_state_indicators.csv"
    if dhs_path.exists() and state:
        import pandas as pd
        dhs = pd.read_csv(dhs_path)
        dd = dhs[(dhs["state"] == state) & (dhs["value"] <= 100)]
        dd = dd.sort_values("value", ascending=False).head(4)
        for _, r in dd.iterrows():
            diseases.append({"indicator": str(r["indicator"]), "value": float(r["value"])})
            survey = str(r["survey"])

    return jsonify({"district": district, "state": state, "stock": stock,
                    "sourcing": sourcing, "diseases": diseases, "survey": survey,
                    "stock_note": "simulated demo data — real deployment would sync "
                                   "from district warehouse inventories"})


@app.post("/api/supply-route")
def api_supply_route():
    """Supply route for an outpost: nearest major facility (emergency-capable
    or >=50 beds within 150 km, else nearest overall) with land + air options."""
    d = request.get_json(silent=True) or {}
    lat, lon = d.get("lat"), d.get("lon")
    if lat is None or lon is None:
        return jsonify({"error": "lat/lon required"}), 400
    _, fac, _ = optimizer.load_data()
    coords = fac[["lat", "lon"]].to_numpy()
    dists = optimizer.pairwise_haversine_km(np.array([[float(lat), float(lon)]]), coords)[0]
    order = np.argsort(dists)
    pick = int(order[0])
    for i in order[:100]:
        row = fac.iloc[int(i)]
        if (bool(row["has_emergency"]) or int(row["beds"]) >= 50) and dists[i] <= 150.0:
            pick = int(i)
            break
    f = fac.iloc[pick]
    dist = float(dists[pick])
    return jsonify({
        "source": {"name": str(f["Hospital_Name"])[:80],
                   "lat": round(float(f["lat"]), 5), "lon": round(float(f["lon"]), 5),
                   "beds": int(f["beds"]), "doctors": int(f["doctors"]),
                   "emergency": bool(f["has_emergency"])},
        "distance_km": round(dist, 1),
        "land": {"speed_kmph": 40.0, "eta_min": round(dist / 40.0 * 60.0, 1)},
        "air": {"speed_kmph": 120.0, "eta_min": round(dist / 120.0 * 60.0 + 5.0, 1)},
    })


# ------------------------------------------------------------- optimization
@app.post("/api/optimize")
def api_optimize():
    data = request.get_json(silent=True) or {}
    try:
        result = optimizer.optimize(
            fleet_size=int(data.get("fleet_size", 3)),
            max_minutes=int(data.get("max_minutes", 30)),
            eps_km=float(data.get("eps_km", 25.0)),
            min_samples=int(data.get("min_samples", 10)),
            region=data.get("region"),
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400
    Outpost.query.delete()
    for o in result["outposts"]:
        db.session.add(Outpost(
            outpost_id=o["outpost_id"], lat=o["lat"], lon=o["lon"],
            anchor_district=o["anchor_district"],
            population_newly_covered=o["circuit_population"],
            villages=o["circuit_village_ids"],
        ))
    db.session.commit()
    return jsonify(result)


@app.get("/api/outposts")
def api_outposts():
    rows = Outpost.query.all()
    return jsonify([r.to_dict() for r in rows])


# ----------------------------------------------------------------- SOS flow
@app.post("/api/sos-alert")
def api_sos_alert():
    d = request.get_json(silent=True) or {}
    village_id = d.get("village_id")
    sos_type = str(d.get("sos_type", "routine"))
    rec = None
    if village_id:
        v, _, _ = optimizer.load_data()
        row = v[v["Village_ID"] == village_id]
        if not row.empty:
            r0 = row.iloc[0]
            rec = optimizer.recommend_mode(r0["Road_Connectivity"],
                                           r0["Healthcare_Risk_Level"], sos_type)
    a = SosAlert(
        node_id=str(d.get("node_id", "unknown")),
        village_id=village_id,
        sos_type=sos_type,
        priority=str(d.get("priority", "normal")),
        lat=d.get("lat"), lon=d.get("lon"),
        source=str(d.get("source", "node")),
        recommended_mode=rec,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"status": "received", "alert": a.to_dict(), "recommended_mode": rec})


@app.get("/api/sos-alerts")
def api_sos_alerts():
    try:
        n = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    rows = SosAlert.query.order_by(SosAlert.id.desc()).limit(n).all()
    return jsonify([r.to_dict() for r in rows])


@app.post("/api/sync")
def api_sync():
    """Offline hub queue flush: bulk-insert alerts captured while offline."""
    d = request.get_json(silent=True) or {}
    created = []
    for item in d.get("alerts", []):
        a = SosAlert(
            node_id=str(item.get("node_id", "unknown")),
            village_id=item.get("village_id"),
            sos_type=str(item.get("sos_type", "routine")),
            priority=str(item.get("priority", "normal")),
            lat=item.get("lat"), lon=item.get("lon"),
            source="hub_sync",
        )
        db.session.add(a)
        created.append(a)
    db.session.commit()
    return jsonify({"synced": len(created),
                    "alerts": [a.to_dict() for a in created]})


# ------------------------------------------------------------------ dispatch
@app.post("/api/dispatch")
def api_dispatch():
    d = request.get_json(silent=True) or {}
    mode = d.get("mode", "mmu_van")
    if mode not in optimizer.DISPATCH_MODES:
        return jsonify({"error": f"unknown mode '{mode}'"}), 400

    alert_id = d.get("alert_id")
    outpost_id = d.get("outpost_id")
    lat, lon = d.get("lat"), d.get("lon")
    if outpost_id:
        op = Outpost.query.filter_by(outpost_id=outpost_id).first()
        if op:
            lat, lon = lat if lat is not None else op.lat, lon if lon is not None else op.lon
    if (lat is None or lon is None) and alert_id:
        a = SosAlert.query.get(alert_id)
        if a:
            lat, lon = a.lat, a.lon
    if lat is None or lon is None:
        return jsonify({"error": "provide lat/lon, alert_id or outpost_id"}), 400

    handoff, eta, pickup_name = None, None, None
    if mode == "uav":
        handoff = optimizer.uav_handoff(float(lat), float(lon))
        eta = handoff["eta_min"]
        pickup_name = handoff["pickup"]["name"]
    elif mode != "outpost":
        speed = optimizer.DISPATCH_MODES[mode]["speed_kmph"] or 25.0
        _, fac, _ = optimizer.load_data()
        coords = fac[["lat", "lon"]].to_numpy()
        dists = optimizer.pairwise_haversine_km(np.array([[float(lat), float(lon)]]), coords)[0]
        order = np.argsort(dists)
        pick = int(order[0])
        for i in order[:50]:
            row = fac.iloc[int(i)]
            pref = "has_ambulance" if mode == "ambulance" else "has_emergency"
            if pref in row.index and bool(row[pref]) and dists[i] <= 100.0:
                pick = int(i)
                break
        pickup_name = str(fac.iloc[pick]["Hospital_Name"])[:80]
        eta = round(float(dists[pick]) / speed * 60.0, 1)

    job = DispatchJob(alert_id=alert_id, outpost_id=outpost_id, mode=mode,
                      eta_min=eta, handoff=handoff)
    db.session.add(job)
    if alert_id:
        a = SosAlert.query.get(alert_id)
        if a:
            a.status = "dispatched"
    db.session.commit()
    return jsonify({**job.to_dict(), "pickup_name": pickup_name})


@app.get("/api/dispatches")
def api_dispatches():
    try:
        n = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    rows = DispatchJob.query.order_by(DispatchJob.id.desc()).limit(n).all()
    return jsonify([r.to_dict() for r in rows])


# ------------------------------------------------------------- MMU tracking
@app.post("/api/track")
def api_track():
    d = request.get_json(silent=True) or {}
    t = MmuTrack(device_id=str(d.get("device_id", "unknown")),
                 lat=float(d.get("latitude", d.get("lat", 0))),
                 lon=float(d.get("longitude", d.get("lon", 0))))
    db.session.add(t)
    db.session.commit()
    return jsonify({"status": "success"})


@app.get("/api/track")
def api_track_get():
    device = request.args.get("device_id")
    q = MmuTrack.query
    if device:
        q = q.filter_by(device_id=device)
    rows = q.order_by(MmuTrack.id.desc()).limit(200).all()
    return jsonify([r.to_dict() for r in rows])


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # create_all() won't add columns to existing tables — tiny startup migration
        from sqlalchemy import text
        cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(sos_alerts)"))]
        if cols and "recommended_mode" not in cols:
            db.session.execute(text("ALTER TABLE sos_alerts ADD COLUMN recommended_mode VARCHAR(20)"))
            db.session.commit()
    print("AIS-42 HealthOutreach API -> http://localhost:5000  (LAN devices: http://<laptop-ip>:5000)")
    app.run(debug=True, host="0.0.0.0", port=5000)
