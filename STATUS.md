# AIS-42 HealthOutreach — Project Status

**Team AIS-42 · PS-4B Rural Healthcare Reachability & Outpost Planning**
**AI for Sustainability Hackathon 2026 · Presentations 10 AM Sep 25, JC Road Campus**

## ✅ DONE & VERIFIED

### Phase 0 — Data (COMPLETE)
- Repo at `E:\ais42-healthoutreach` (fresh git)
- Provided datasets cleaned: 12,000 villages + 30,273-facility government hospital directory
- Public data downloaded & acknowledged: geoBoundaries ADM1/ADM2 (ODC-ODbL),
  DHS/NFHS subnational indicators via HDX (CC BY-ND 4.0), HeiGIT/WorldPop
  accessibility validation (CC BY-SA)
- **Baseline computed: only 13.82% of villages are within 30 min of care.
  Avg travel = 107 min. 2,611 underserved villages. 4,030 poor-road. 3,118 high-risk.**

### Phase 1 — Backend (22/22 endpoints smoke-tested)
- `backend/app.py` — Flask API + SQLite: `/api/optimize`, `/api/sos-alert`,
  `/api/sync`, `/api/dispatch`, `/api/track`, `/api/villages`, `/api/facilities`,
  `/api/districts`, `/api/dhs`, `/api/heigit`, `/api/geojson/districts`, `/api/modes`…
- `backend/optimizer.py` — Healthcare Need Score → underserved detection →
  DBSCAN (with K-Means fallback + mega-cluster circuit refinement) →
  greedy MCLP → dual coverage metrics (30-min emergency + scheduled MMU care)
- `backend/models.py` — SosAlert, DispatchJob, Outpost, MmuTrack
- **Verified results (final, post geo-normalization): 3 MMUs → scheduled care 13.82% → 22.84%
  (14.75M people); 5 MMUs → 28.58%; 8 MMUs → 36.68%. 30-min emergency: 13.82% → 15.69% (3 MMUs).
  UAV handoff card: TechEagle-class Vertiplane X3 specs, nearest emergency facility pickup, DGCA DigitalSky NPNT.**

### Phase 2 — Ops Console (COMPLETE, live-tested)
- `backend/templates/index.html` + `static/js/main.js` + `static/css/style.css`
- Dark-theme Leaflet command console: zoom-LOD (district bubbles → villages →
  facilities), draw tools + region planning, 7 dispatch-mode cards
  (🚑 🚐 🏍️ 🚴 🛩️ 🚁 ⛺), dual coverage rings, live SOS feed, supply routes,
  medical intel panel, search, demo trigger (Simulate Village SOS — the
  hub-sync flow is the REAL ESP32 + phone + tablet rig)

### Phase 2b — Impact Dashboard (COMPLETE, health-checked)
- `dashboard/app.py` — Streamlit + Folium + Plotly: KPI row, fleet slider,
  before/after metrics, folium map with outposts, 4 plotly charts incl.
  DHS indicator explorer + HeiGIT validation chart, attribution footer

## ⏳ REMAINING

- **Flash the ESP32-S3** and run the phone → tablet → laptop flow once (see `edge/HARDWARE_GUIDE.md`)
- **Record the backup demo video** (see `VIDEO.md`)
- **Rehearse the demo script twice** (see `DEMO_SCRIPT.md`)
- **Backups to USB + Google Drive** (repo zip + video + deck)
- **Final** — README, requirements.txt, dry run, backups (USB + Drive)

## ▶ HOW TO SEE IT RIGHT NOW

```powershell
cd E:\ais42-healthoutreach
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
```

- **Ops Console** → http://localhost:5000 — toggle layers, hit
  "⚡ Run Spatial Optimization", then "🆘 Simulate Village SOS", select the
  🚁 UAV card and click the SOS point on the map.
- **Impact Dashboard** → http://localhost:8501 — sidebar → "🚀 Run Optimization".

Stop with `.\stop_demo.ps1`.
