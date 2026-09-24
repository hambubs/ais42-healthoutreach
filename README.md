# AIS-42 HealthOutreach

**PS-4B: Rural Healthcare Reachability & Outpost Planning** — AI for Sustainability Hackathon 2026
Team AIS-42 · Track 4: Sustainable Healthcare · SDG 3 & 10

Spatial-AI placement of Mobile Medical Units for rural India, with a zero-connectivity
ESP32 SOS edge network and multi-modal dispatch (ambulance · MMU van · 2W rider · UAV handoff · outpost).

## Quickstart

```powershell
cd E:\ais42-healthoutreach
.\.venv\Scripts\python -m pip install -r backend\requirements.txt   # first time only
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
```

- **Ops Console** → http://localhost:5000 (live SOS feed, dispatch, UAV handoff)
- **Impact Dashboard** → http://localhost:8501 (before/after, WorldPop BLR pilot, DHS Live)
- Stop: `.\stop_demo.ps1`

## Pipeline

```
scripts/prep_data.py   -> clean provided datasets + baseline (13.82% / 107 min)
scripts/fix_geo.py    -> normalize synthetic coords into district polygons (originals kept)
scripts/fetch_worldpop.py -> BLR pilot density (enrichment)
backend/seed.py       -> alias joins, district GeoJSON, DHS + HeiGIT extracts
backend/app.py        -> Flask API + SQLite (17 endpoints) + Ops Console
backend/optimizer.py  -> Need Score -> DBSCAN -> greedy MCLP -> dual coverage metrics
dashboard/app.py      -> Streamlit impact dashboard (3 tabs)
edge/                 -> ESP32-S3 captive-portal SOS gateway + hub pages
```

## Headline results

| Metric | Value |
|---|---|
| Baseline 30-min coverage | 13.82% of villages |
| 3 MMUs → scheduled care | 22.84% (14.75M people) |
| 5 / 8 MMUs | 28.58% / 36.68% |
| Avg travel to care | 107 min |

## Docs

- `RUNBOOK.md` — verify · flash · rehearse (the demo bible)
- `STATUS.md` — progress tracker
- `DATA_SOURCES.md` — provenance: PROVIDED vs ENRICHMENT + licenses
- `DEMO_SCRIPT.md` — 5-minute stage flow with recovery lines
- `TEAM_TASKS.md` — shared task board
- `VIDEO.md` — backup recording checklist
- `edge/FLASH-CHECKLIST.md` — ESP32-S3 flashing guide

## Data

Provided (core of every metric): 12,000-village accessibility dataset + 30,273-facility
government hospital directory. Enrichment (read-only, acknowledged): geoBoundaries (ODC-ODbL),
DHS/NFHS via HDX (CC BY-ND 4.0), HeiGIT/WorldPop (CC BY-SA), WorldPop 2020 (CC-BY 4.0).
See `DATA_SOURCES.md` for the no-contamination guarantee.
