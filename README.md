# 🏥 AIS-42 HealthOutreach

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Backend-Flask%20%2B%20SQLite-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io/)
[![SDG 3 & 10](https://img.shields.io/badge/UN%20SDG-3%20%26%2010-green.svg)](https://sdgs.un.org/goals)

> **PS-4B: Rural Healthcare Reachability & Outpost Planning**  
> **AI for Sustainability Hackathon 2026** · JAIN (Deemed-to-be University), JC Road Campus  
> **Team AIS-42** · Track 4: Sustainable Healthcare · UN SDGs 3 & 10  
> **Team Members:** Sahil Thanveer Rai, Ashmita Roy, Subhalaxmi Sahoo, Punit Kumar

---

## 🌟 What is HealthOutreach?

HealthOutreach is an AI-driven spatial planning and decentralized emergency response platform designed to solve the critical "last-mile" healthcare deficit in rural India.

Rather than just presenting static charts, HealthOutreach combines:
1. **Spatial AI Optimization**: Healthcare Need Scoring, DBSCAN clustering, and greedy Maximal Coverage Location Problem (MCLP) algorithms to position **Mobile Medical Units (MMUs)** and permanent outposts where rural vulnerability is highest.
2. **Interactive Geographic Planning & Medical Intel**: Dynamic polygon/circle area drawing tools on the map that instantly calculate population, underserved village counts, endemic disease prevalence (from NFHS-5/DHS), and medicine stockouts (with Jan Aushadhi Kendra cheap sourcing suggestions).
3. **Multi-Modal Emergency Dispatch**: Rule-based dispatch routing across **5 modalities**:
   - 🚑 **108 Emergency Ambulance** (standard road emergencies)
   - 🚐 **Mobile Medical Unit (MMU)** (scheduled circuit primary care)
   - 🏍️ **2W First Responder** (congested or rough terrain)
   - 🚁 **UAV Supply Dispatch** (TechEagle Vertiplane X3 specs for cut-off roads + critical antivenom/blood delivery)
   - ⛺ **Temporary Outpost** (mega-cluster static relief)
4. **Air-Gapped Edge Telemetry (Zero Internet)**: An ESP32-S3 Wi-Fi Captive Portal and LoRa mesh node that enables isolated villagers to transmit encrypted emergency SOS beacons without any SIM card, 4G, or Wi-Fi.

---

## ⚡ Quickstart for Teammates (One-Click Setup)

### 🪟 Windows (Double-Click Setup)
1. **Clone the repository:**
   ```bash
   git clone https://github.com/hambubs/ais42-healthoutreach.git
   cd ais42-healthoutreach
   ```
2. **First-time setup:**
   - Double-click **`setup.bat`** (it creates the `.venv` virtual environment and installs all dependencies automatically).
3. **Launch the Demo:**
   - Double-click **`start_demo.bat`** (or run `powershell -ExecutionPolicy Bypass -File .\start_demo.ps1`).

---

### 🍎 Mac / Linux Setup
```bash
git clone https://github.com/hambubs/ais42-healthoutreach.git
cd ais42-healthoutreach

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Terminal 1 - Ops Console:
python backend/app.py

# Terminal 2 - Impact Dashboard:
streamlit run dashboard/app.py
```

---

## 🖥️ Live Interfaces

Once started, two web applications will launch automatically:

| Interface | URL | Features |
|---|---|---|
| **Command Ops Console** | `http://localhost:5000` | Leaflet map with 12k villages, hospital directory, Geoman area drawing tool, 5 dispatch modes, live SOS alerts feed, and Medical Intelligence panel. |
| **Impact Dashboard** | `http://localhost:8501` | Streamlit executive analytics: Before/After coverage metrics, 19M-person WorldPop BLR pilot heat layer, and live DHS/STATcompiler API explorer. |
| **Offline Hub Sync Page** | `http://localhost:5000/hub` | Simulates an MMU gateway docking with the base hospital to flush cached offline alerts. |

To stop all background services, simply run:
```powershell
.\stop_demo.ps1
```

---

## 📊 Key Results & Impact Metrics

| Metric | Baseline (Pre-Optimization) | Optimized (AIS-42 MMUs) | Impact |
|---|---|---|---|
| **30-Min Rural Reachability** | 13.82% of villages | **22.84%** (3 MMUs) · **36.68%** (8 MMUs) | **+14.75 Million** rural lives reached |
| **Average Travel Time to Care** | 107 minutes | **< 30 minutes** (within MMU circuits) | Reduced by **>70%** |
| **Emergency Dead Zones** | 2,611 underserved villages | Automatic UAV aerial fallback | Zero-lag information relay via LoRa |
| **Independent Validation** | HeiGIT/WorldPop UP: 24.9% / MP: 16.0% | Aligned with published literature | Rigorous peer benchmark |

---

## 🛠️ System Architecture & Data Pipeline

```
Provided Raw Data (12,000 villages + 30,273 hospitals)
        │
        ▼
scripts/prep_data.py   ──► Cleans datasets & computes baseline coverage
scripts/fix_geo.py     ──► Bounded geo-normalization into official district polygons
scripts/fetch_worldpop.py ──► WorldPop 2020 high-res gridded population for BLR pilot
        │
        ▼
backend/seed.py        ──► District boundary GeoJSON + DHS NFHS-5 indicator extraction
backend/app.py         ──► Flask REST API (17 endpoints) + SQLite + Web Ops Console
backend/optimizer.py   ──► Need Score ──► DBSCAN ──► Greedy MCLP Location-Allocation
dashboard/app.py       ──► Multi-tab Streamlit visualizer & DHS live telemetry
edge/esp32_gateway/    ──► ESP32-S3 Arduino sketch: Captive portal, LittleFS queue & AES
```

---

## 📁 Repository Tour

- **`backend/`**: Flask backend server, SQLite models, and spatial optimization algorithms.
  - `backend/app.py`: Core REST API & static web server.
  - `backend/optimizer.py`: DBSCAN clustering & MCLP mathematical solver.
  - `backend/templates/index.html` & `backend/static/`: Leaflet-based interactive Ops Console.
- **`dashboard/`**: Streamlit Impact Dashboard (`dashboard/app.py`).
- **`edge/`**: ESP32-S3 C++ firmware (`esp32_gateway.ino`) and offline hub bridge.
- **`deck/`**: Presentation slides in HTML (`deck/deck.html`) and PowerPoint (`deck/AIS-42_PS-4B.pptx`).
- **`RUNBOOK.md`**: Step-by-step presentation rehearsal guide and demo contingency instructions.
- **`DEMO_SCRIPT.md`**: 5-minute timed pitch script with recovery lines.
- **`DATA_SOURCES.md`**: Data provenance, licensing, and compliance documentation.

---

## 👥 Team AIS-42

- **Sahil Thanveer Rai** — System Architect & Hardware/IoT Lead
- **Ashmita Roy** — Data Science & Frontend Integration
- **Subhalaxmi Sahoo** — Epidemiological Analysis & GIS Mapping
- **Punit Kumar** — Logistics Modeling & Presentation Lead
