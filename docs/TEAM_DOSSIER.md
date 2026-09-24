# AIS-42 HealthOutreach — Team Dossier

**PS-4B: Rural Healthcare Reachability & Outpost Planning** · AI for Sustainability Hackathon 2026
Team AIS-42 — Sahil Rai · Ashmita Roy · Subhalaxmi Sahoo · Punit Kumar · SDG 3 & 10

> The one document with everything: what we built, where every piece of data came from,
> how the code fits together, which tools and AI we used, and who did what.

---

## 1. The project in 60 seconds

12,000 villages across 5 Indian states (provided dataset) average **107 minutes** of travel
to the nearest medical facility — only **13.82%** are within 30 minutes. HealthOutreach is a
spatial-AI planner + offline SOS network that:

1. **Plans** — clusters underserved villages (DBSCAN) and places Mobile Medical Units via a
   greedy Maximal-Coverage optimizer, placing every unit at the population-weighted center of its circuit
   from the government's 30,273-hospital directory. 3 MMUs take scheduled care from
   **13.82% → 22.84% of villages (14.75 million people)**; 8 MMUs → 36.68%.
2. **Reaches** — when villages have no cellular at all, an ESP32-S3 node broadcasts an
   offline Wi-Fi portal: any phone in airplane mode submits an **AES-128-encrypted** SOS,
   the MMU hub harvests it, and it syncs to the live command console.
3. **Dispatches** — a 7-mode rule engine (ambulance · MMU van · 2W rider · bike · UAV ·
   helicopter · outpost) picks the right vehicle for the terrain; poor-road + high-risk
   villages trigger air dispatch with a TechEagle-class UAV handoff (DGCA DigitalSky NPNT).

## 2. Demo architecture — what runs where

| Device | Role |
|---|---|
| **Laptop** | The server: Flask backend + Ops Console (`:5000`) + Streamlit dashboard (`:8501`) — on the projector. Never run the server on a phone. |
| **ESP32-S3 + Ra-02** | The offline **village node**: Wi-Fi AP "MMU-GATEWAY" + captive portal + AES-128 queue + LoRa beacon (single board) |
| **Phone A** | The village SOS client — airplane mode, joins MMU-GATEWAY, one-tap SOS |
| **Tablet** | The MMU hub — pulls the encrypted queue, carries the JSON online |
| **Phone B (optional)** | Online fallback: opens `http://<laptop-ip>:5000/sos` on venue Wi-Fi |

## 3. Data — sources, cleaning, enrichment, where used

### PROVIDED (the core of every metric)
| Dataset | Cleaning applied | Used by |
|---|---|---|
| 12,000-village accessibility dataset (26 columns) | numeric coercion, Yes/No binarization, road-speed encoding (Good 40 / Avg 25 / Poor 12 km/h), risk normalization, **Healthcare Need Score** = 0.4·pop + 0.3·risk + 0.3·inaccessibility | optimizer, console, dashboard |
| Government of India hospital directory (30,273 facilities) | coordinate parsing (drops "0" placeholders) → 10,672 valid-coordinate facilities | facility layer, UAV/ambulance pickup, outpost staging, supply routes |

**Documented transformation:** the provided coordinates were synthetic-uniform (every
state spanned the same 18–27°N / 72–88°E box — renders as a giant square). We re-anchored
each village to a plausible position **inside its own district polygon** (geoBoundaries)
for meaningful maps, **preserving the originals** in `Latitude_orig`/`Longitude_orig`.
No other column was touched; every metric still derives from provided data alone.

### ENRICHMENT (read-only overlay, physically separated in `data/clean/enrichment/`)
| Source | License | What it adds | Where used |
|---|---|---|---|
| geoBoundaries ADM1/ADM2 | ODC-ODbL | district/state borders | map layers, geo-normalization |
| DHS/NFHS subnational via HDX | CC BY-ND 4.0 | state health indicators (anemia 68.1% etc.) | dashboard DHS tab, medical intel panel |
| HeiGIT/WorldPop accessibility | CC BY-SA | independent 30-min coverage (UP 24.9%, MP 16.0%) | validation chart |
| WorldPop 2020 density (1km) | CC-BY 4.0 | BLR-pilot population heat layer (19M in bbox) | dashboard WorldPop tab |
| DHS Program **live API** (`api.dhsprogram.com`, keyless) | public | live indicator queries on stage | DHS Live tab (auto-fallback to local CSV) |

**No-contamination guarantee:** enrichment is joined at read time only and never written
back into provided-derived files. Full provenance: `DATA_SOURCES.md`.

## 4. System architecture

```
┌───────────────────────────── DATA LAYER ─────────────────────────────┐
│ PROVIDED: 12,000 villages + 30,273-facility directory (clean CSVs)   │
│ ENRICHMENT (separated): geoBoundaries · DHS · HeiGIT · WorldPop     │
└──────────────┬───────────────────────────────────────────────────────┘
               │ scripts: prep_data → fix_geo → seed → fetch_worldpop
               ▼
┌───────────────────── OPTIMIZER (backend/optimizer.py) ──────────────┐
│ Need Score → underserved mask → DBSCAN (+K-Means guard, circuits    │
│ capped ≤400 villages) → greedy MCLP → place at population-weighted centers │
│ → dual coverage metrics · 7-mode dispatch rules · UAV handoff       │
└──────────┬──────────────────────────────────┬───────────────────────┘
           │ in-memory pandas (one data spine) │
   ┌───────▼──────────────┐          ┌────────▼────────────┐
   │ FLASK API + SQLite    │          │ STREAMLIT DASHBOARD │
   │ :5000 · 22 endpoints  │          │ :8501 · 3 tabs       │
   └───────┬──────────────┘          └────────▲────────────┘
           │ serves                          │
   ┌───────▼──────────────────────────────────┴─────────┐
   │ LEAFLET OPS CONSOLE (browser)                       │
   │ zoom-LOD · draw tools + region planning · 7-mode     │
   │ dispatch · supply routes · medical intel · search   │
   └───────▲─────────────────────────────────────────────┘
           │ Wi-Fi captive portal (airplane-mode phone)
   ┌───────┴──────────────────────────────┐
   │ ESP32-S3 NODE (+ Ra-02 LoRa beacon)  │
   │ AES-128 queue → tablet hub → /api/sync when online │
   └──────────────────────────────────────┘
```

## 5. Code map — every file, what it plugs into

| File | What it does | Plugs into |
|---|---|---|
| `scripts/prep_data.py` | cleans both provided datasets, computes Need Score + baseline (13.82% / 107 min) | writes `data/clean/*.csv` consumed by everything |
| `scripts/fix_geo.py` | re-anchors synthetic coords into district polygons (originals preserved) | rewrites `villages_clean.csv` |
| `backend/seed.py` | district alias joins (Kanpur→Kanpur Nagar/Dehat, Prayagraj→Allahabad), GeoJSON filter, DHS + HeiGIT extracts | writes `data/clean/enrichment/*` |
| `scripts/fetch_worldpop.py` | WorldPop 1km window for the BLR pilot bbox (19M people) | writes `enrichment/worldpop/*` |
| `backend/optimizer.py` | the AI core: Need Score, DBSCAN→MCLP, population-weighted placement, region filter, dispatch rules, UAV handoff, district centroids | imported by app.py + dashboard |
| `backend/models.py` | SQLite live state: SosAlert (with recommended_mode), DispatchJob, Outpost, MmuTrack | Flask-SQLAlchemy |
| `backend/app.py` | 22 REST endpoints + serves the console + `/hub` + mobile `/sos` + startup column migration | the single backend |
| `backend/static/js/main.js` | the console brain: zoom-LOD, Geoman draw tools + area stats, 7-mode dispatch, popups with one-tap emergency, supply routes, intel panel, mesh badge, search, SOS polling | talks only to the API above |
| `dashboard/app.py` | Streamlit 3-tab analytics (Impact · WorldPop BLR · DHS Live) | imports optimizer directly |
| `edge/esp32_gateway/esp32_gateway.ino` | Wi-Fi captive-portal SOS gateway (AES-128-CBC, LittleFS queue) | phone → tablet → `/api/sync` |
| `edge/esp32_gateway/esp32_gateway_lora/…ino` | same + LoRa beacon (single-board node) | optional radio extension |
| `edge/hub_page/hub.html` | paste-and-sync page (also served at `/hub`) | POSTs `/api/sync` |
| `scripts/make_deck.py` | generates the PPTX deck programmatically | `deck/AIS-42_PS-4B.pptx` |
| `scripts/smoke_test.py` | 22-endpoint automated verification + LOD checks | run after any backend change |

## 6. API reference (22 endpoints)

`GET /` console · `GET /hub` hub page · `GET /sos` mobile fallback page
`GET /api/baseline` · `GET /api/villages` (+`?bbox=`, `?state=`, `?underserved=1`) ·
`GET /api/facilities` · `GET /api/districts` (with centroids) · `GET /api/dhs` ·
`GET /api/heigit` · `GET /api/geojson/districts` · `GET /api/modes` (7) ·
`GET /api/outposts` · `GET /api/sos-alerts` · `GET /api/dispatches` · `GET /api/track`
`POST /api/optimize` (fleet, minutes, **region**) · `POST /api/sos-alert` (auto mode
recommendation) · `POST /api/sync` (offline hub flush) · `POST /api/dispatch` (7 modes,
nearest-facility pickup, UAV handoff JSON) · `POST /api/supply-route` (land + air) ·
`POST /api/outpost-intel` (DHS diseases + stock matrix + sourcing) · `POST /api/track`

## 7. The AI core, explained

1. **Healthcare Need Score** — `0.4·population + 0.3·epidemiological risk + 0.3·inaccessibility`
   (equity is hardcoded: resources bias toward the least accessible).
2. **Underserved detection** — official flag OR travel > 30 min.
3. **DBSCAN clustering** — finds real settlement pockets (K-Means guard for uniform data;
   mega-clusters split into ≤400-village circuits, matching NHM block-scale practice).
4. **Greedy MCLP** — selects outposts maximizing need-weighted population under scheduled care.
5. **Re-anchoring** — every outpost is staged at the nearest REAL facility (≤50 km), with
   beds/doctors/emergency status; fallback = highest-need village. Emergency coverage is
   recomputed from the final real positions.
6. **Dual metrics** — strict 30-min emergency coverage (13.82→15.09% with 3 MMUs) +
   scheduled circuit care (13.82→22.84%) — the gap is bridged by the dispatch engine.
7. **Dispatch rules** — trauma/maternal on poor+high-risk terrain → helicopter airlift;
   supplies on poor+high-risk → UAV; poor roads → 2W rider; default → MMU van.

## 8. Tools & AI declaration (full transparency)

| Tool | Role | Disclosure |
|---|---|---|
| **GLM 5.3** (via OpenCode / NVIDIA NIM) | primary AI coding co-pilot: backend, optimizer, console JS, Streamlit dashboard, ESP32 firmware, data pipeline, deck generator, docs | AI-assisted, human-reviewed; every change verified by the automated 22-endpoint smoke test |
| **Mimo 2.6 Flash** (free, via OpenCode) | automated read-only audit agents: code reviews, data verification, screenshot/image analysis, bug hunts | AI-assisted verification |
| **Gemini (AI Mode)** | pre-hackathon research: dataset discovery (HDX/DHS/WorldPop/geoBoundaries), architecture brainstorming | research only |
| **Antigravity IDE** | assisted development environment during the sprint | tooling |
| **OpenCode** | agent orchestration environment (main + subagents) | tooling |
| **Canva** | visual/design assets by the team | design |
| **python-pptx / reveal.js** | programmatic deck generation (PPTX + HTML) — deterministic, not generative | tooling |
| **Libraries** | Flask, scikit-learn, pandas, NumPy, Streamlit, Folium, Plotly, Leaflet, Leaflet-Geoman, Esri dark basemap, mbedTLS (AES-128), LittleFS | open-source, attributed |

All AI-assisted code was human-verified: 22/22 endpoint smoke tests green, JS syntax
checked, optimizer outputs recomputed and cross-validated against HeiGIT's independent
WorldPop-based analysis.

## 9. Contributions

| Member | Contribution |
|---|---|
| **Sahil Rai** | system architecture; backend + spatial optimizer; ops console; ESP32-S3 firmware (gateway + LoRa); data pipeline; team coordination |
| **Ashmita Roy** | impact dashboard segment (3 tabs); speaker notes for the analytics walkthrough |
| **Subhalaxmi Sahoo** | data provenance + validation narrative (provided vs enrichment, HeiGIT cross-check, the coordinate-normalization honesty point) |
| **Punit Kumar** | SDG 3/10 impact narrative; judge Q&A preparation (synthetic-data question, MMU scaling, UAV handoff) |

*(Adjust as you see fit before submitting.)*

## 10. Honesty statements (Q&A armor — say these proudly)

1. *"Your coordinates look synthetic."* — Correct: the provided dataset's coordinates were
   synthetic-uniform. We documented it, normalized them into district polygons for
   visualization, **preserved the originals**, and every metric comes from provided
   columns alone. Independent HeiGIT/WorldPop analysis (UP 24.9% within 30 min) confirms
   our numbers' order of magnitude.
2. *"Why only 3 MMUs?"* — It's a slider: 3 → 22.84%, 5 → 28.58%, 8 → 36.68%. The point is
   the planning curve, not a single number.
3. *"How does the UAV work?"* — We don't build drones; we integrate India's drone-logistics
   ecosystem: a TechEagle-class Vertiplane X3 handoff (3–5 kg, 100 km, 120 km/h) with a
   DGCA DigitalSky NPNT-compliant flight request, pickup at the nearest real facility.
4. *"Is the medicine stock real?"* — The stock matrix is simulated (labeled as such in the
   UI); the disease indicators are real NFHS-5 state data. A deployment would sync district
   warehouse inventories.
5. *"Does the SOS really work offline?"* — Live: phone in airplane mode → ESP32 captive
   portal → AES-128-encrypted queue → hub tablet → sync. The LoRa beacon is the
   beyond-Wi-Fi extension of the same node.

## 11. Where everything lives

| Doc | Contents |
|---|---|
| `README.md` | quickstart + doc index |
| `RUNBOOK.md` | verify · flash · rehearse (the demo bible) |
| `DEMO_SCRIPT.md` | 5-minute stage flow with recovery lines |
| `TEAM_TASKS.md` | shared task board + the numbers everyone quotes |
| `VIDEO.md` | backup recording checklist |
| `STATUS.md` | progress tracker |
| `DATA_SOURCES.md` | full provenance + licenses |
| `edge/HARDWARE_GUIDE.md` | wiring diagram, flashing, phone/tablet setup |
| `deck/` | PPTX + reveal.js HTML deck |
