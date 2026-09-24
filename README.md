# AIS-42 HealthOutreach

**PS-4B: Rural Healthcare Reachability & Outpost Planning** — AI for Sustainability Hackathon 2026
Team AIS-42 · Track 4: Sustainable Healthcare · SDG 3 & 10

Spatial-AI placement of Mobile Medical Units for rural India — staged at **real
facilities**, planned for **maximum area coverage** — with a zero-connectivity
ESP32-S3 SOS node (Wi-Fi captive portal + LoRa beacon) and a 7-mode dispatch engine
(ambulance · MMU van · 2W rider · bike · UAV handoff · helicopter · outpost).

## Quickstart

```powershell
cd E:\ais42-healthoutreach
.\.venv\Scripts\python -m pip install -r backend\requirements.txt   # first time only
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
```

- **Ops Console** → http://localhost:5000 (draw tools, dispatch, supply routes, intel)
- **Impact Dashboard** → http://localhost:8501 (before/after, WorldPop BLR, DHS Live)
- Stop: `.\stop_demo.ps1` · Team share: `.\make_team_package.ps1`

## Headline results

| Metric | Value |
|---|---|
| Baseline 30-min coverage | 13.82% of villages (107-min avg travel) |
| 3 MMUs → scheduled care | 22.84% (14.75M people) |
| 5 / 8 MMUs | 28.58% / 36.68% |
| 30-min emergency (3 MMUs) | 13.82% → 15.09% (bridged by dispatch modes) |

## Doc index

| Doc | What's inside |
|---|---|
| **[docs/TEAM_DOSSIER.md](docs/TEAM_DOSSIER.md)** | everything in one place: data sources, architecture diagram, code map, API reference, AI declaration, contributions, Q&A armor |
| [RUNBOOK.md](RUNBOOK.md) | verify · flash · rehearse — the demo bible |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 5-minute stage flow with recovery lines |
| [TEAM_TASKS.md](TEAM_TASKS.md) | shared task board + the numbers everyone quotes |
| [edge/HARDWARE_GUIDE.md](edge/HARDWARE_GUIDE.md) | breadboard wiring diagram, S3+LoRa flashing, phone/tablet setup |
| [DATA_SOURCES.md](DATA_SOURCES.md) | provenance: PROVIDED vs ENRICHMENT + licenses |
| [STATUS.md](STATUS.md) · [VIDEO.md](VIDEO.md) | progress tracker · backup recording checklist |

## Pipeline

```
prep_data.py → fix_geo.py → seed.py → fetch_worldpop.py
     ↓ (clean CSVs, one data spine)
optimizer.py (Need Score → DBSCAN → MCLP → population-weighted placement)
     ↓                          ↓
app.py (Flask, 22 endpoints)   dashboard/app.py (Streamlit, 3 tabs)
     ↓
static/js/main.js (Leaflet console: LOD, draw tools, dispatch, intel)
     ↑ Wi-Fi captive portal
esp32_gateway(_lora).ino (ESP32-S3 node: AES-128 SOS queue + LoRa beacon)
```

## Data

Provided (core of every metric): 12,000-village accessibility dataset + 30,273-facility
government hospital directory. Enrichment (read-only, acknowledged): geoBoundaries
(ODC-ODbL), DHS/NFHS via HDX (CC BY-ND 4.0), HeiGIT/WorldPop (CC BY-SA), WorldPop 2020
(CC-BY 4.0). See `DATA_SOURCES.md` for the no-contamination guarantee.
