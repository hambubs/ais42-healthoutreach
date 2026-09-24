# 🎯 RUNBOOK — Verify · Flash · Rehearse

Team AIS-42 · PS-4B · Presentations 10 AM Sep 25, JC Road Campus
**Laptop LAN IP (home Wi-Fi): `192.168.0.145`** — re-check at the venue with `ipconfig` (Wi-Fi adapter)

---

## PART 1 — WHAT WAS DONE (review checklist)

### A. Data layer ✅
| What | Where | Verify |
|---|---|---|
| 12,000 villages cleaned + scored | `backend/data/clean/villages_clean.csv` | 12,000 rows, `need_score` column |
| 10,672 facilities (valid coords) | `backend/data/clean/facilities_clean.csv` | from the provided 30,273 directory |
| Baseline: **13.82% within 30-min, 107-min avg travel** | `backend/data/clean/baseline_stats.json` | open the file |
| District summary (alias-fixed) | `backend/data/clean/district_summary.csv` | Kanpur→Kanpur Nagar/Dehat, Prayagraj→Allahabad |
| **ENRICHMENT (separated)** | `backend/data/clean/enrichment/` | DHS, HeiGIT, district borders, WorldPop |
| Provenance manifest | `DATA_SOURCES.md` | PROVIDED vs ENRICHMENT + licenses |

### B. Backend ✅ (22/22 endpoints smoke-tested)
`backend/app.py` — Flask + SQLite. Key endpoints: `/api/optimize` (DBSCAN→MCLP, region-scoped), `/api/sos-alert` (auto mode recommendation), `/api/sync` (offline hub flush), `/api/dispatch` (7 modes + UAV handoff), `/api/supply-route`, `/api/outpost-intel`, `/api/villages` (bbox), `/api/districts` (centroids), `/api/dhs`, `/api/heigit`, `/api/geojson/districts`, `/hub`, `/sos`.

### C. Ops Console ✅ (`http://localhost:5000`)
Dark Leaflet command console: zoom-LOD (district bubbles → villages → facilities), draw tools + area planning, 7 dispatch-mode cards, dual coverage rings, live SOS feed (5s poll), supply routes, medical intel panel, search, **"📊 Impact Dashboard ↗" nav tab**.

### D. Impact Dashboard ✅ (`http://localhost:8501`)
3 tabs: **🗺️ Impact & Analytics** (before/after, top-10 districts, DHS explorer, HeiGIT validation) · **🛰️ WorldPop BLR Pilot** (19M people heat layer) · **🇮🇳 DHS Live** (live API + fallback + STATcompiler launch button).

### E. Edge rig ✅ (code written — flash per `edge/HARDWARE_GUIDE.md`)
`edge/esp32_gateway/esp32_gateway.ino` — AP "MMU-GATEWAY" + captive portal + one-tap SOS + AES-128-CBC (mbedTLS) + LittleFS queue. `edge/esp32_gateway/esp32_gateway_lora/esp32_gateway_lora.ino` — same + LoRa beacon (single-board S3 demo). `edge/hub_page/hub.html` — paste-and-sync page (also served at `/hub`).

### F. Verified numbers (for the deck) — FINAL, everyone quotes these
- Baseline: 13.82% villages within 30-min · 2,611 underserved · 107-min avg travel
- 3 MMUs → scheduled care **22.84%** (14.75M people) · 5 MMUs → 28.58% · 8 MMUs → 36.68%
- 30-min emergency coverage: 13.82% → 15.69% with 3 MMUs (bridged by dispatch modes)
- UAV trigger: villages with Road=Poor AND Risk=High → air dispatch (rule engine)
- HeiGIT validation: UP 24.9% / MP 16.0% within 30-min (independent WorldPop-based analysis)
- DHS live: India child anemia 2019-21 = 68.1% (verified via API)

---

## PART 2 — STEP-BY-STEP

### STEP 1 · Verify the software (5 min, do this FIRST)
```powershell
cd E:\ais42-healthoutreach
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
```
Both browsers open. On the **Console** (:5000):
1. Tick "Hospitals & facilities" layer → blue dots appear
2. Click **⚡ Run Spatial Optimization** → ★ outposts + dual coverage rings appear and the toast shows scheduled care → ~22.8%
3. Click **🆘 Simulate Village SOS** → toast + red pulse on map + feed entry
4. Click the **🚁 UAV** card → click the SOS point → handoff card + blue flight line
5. Click **"📊 Impact Dashboard ↗"** → dashboard opens in a new tab

On the **Dashboard** (:8501):
6. Sidebar → **🚀 Run Optimization** → before/after metrics + map updates
7. **🛰️ WorldPop tab** → BLR heat layer renders
8. **🇮🇳 DHS Live tab** → pick an indicator → live chart (or fallback caption if Wi-Fi blocks it)

Stop: `.\stop_demo.ps1`

### STEP 2 · Flash the ESP32-S3 (10 min)
**Arduino IDE path** (simplest for one sketch):
1. Arduino IDE → **File → Preferences → Additional boards manager URLs**, paste:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json` → OK
2. **Tools → Board → Boards Manager** → search `esp32` → install **esp32 by Espressif Systems** (few minutes)
3. **File → Open** → `E:\ais42-healthoutreach\edge\esp32_gateway\esp32_gateway.ino`
4. **Tools → Board → esp32 → ESP32S3 Dev Module**
5. **Tools → USB CDC On Boot → Enabled**
6. **Tools → Flash Size** → match your module (8MB typical; check the silkscreen)
7. **Tools → Partition Scheme** → "Default 4MB with spiffs" (or 8MB variant to match)
8. Plug the S3 via **USB-C — the socket labeled `USB`/`COM`** (if there are two, NOT the `UART` one)
9. **Tools → Port** → select the new COM port
10. **Upload (→)**. Stuck at "Connecting..."? **Hold the BOOT button** on the board until upload starts.
11. **Tools → Serial Monitor** (115200) → after reboot you should see:
    `MMU-GATEWAY up -> http://192.168.4.1  (records=0)`

**PlatformIO alternative**: create a project with `board = esp32-s3-devkitc-1`, `framework = arduino`, `board_build.filesystem = littlefs`, build flag `-DARDUINO_USB_CDC_ON_BOOT=1`; move the sketch to `src/main.cpp` with `#include <Arduino.h>` on top.

### STEP 3 · Phone A — the village SOS node (3 min)
1. Phone A: turn **Airplane mode ON**, then turn **Wi-Fi back ON** (this proves: no SIM, no cellular, no internet)
2. Wi-Fi settings → join **MMU-GATEWAY** (open network)
3. Android shows *"MMU-GATEWAY, connected (no internet)"* — **expected**. A **"Sign in to network"** notification appears within a few seconds → **tap it** → the SOS portal opens
4. No notification? Open Chrome → type `192.168.4.1` → portal opens
5. Test: tap **🤰 Maternal Emergency** → "✅ SOS queued — the MMU hub will carry it to the hospital"

### STEP 4 · Tablet — the MMU hub (3 min)
1. Tablet: join **MMU-GATEWAY** Wi-Fi
2. Chrome → `http://192.168.4.1/hub`
3. Tap **⬇ Pull alerts from gateway** → the alert(s) appear with the 🔒 AES ciphertext signature
4. Tap **📋 Copy JSON** → "Copied" alert

### STEP 5 · Laptop — the payoff (5 min)
1. Laptop: `.\start_demo.ps1` (console + dashboard up). **First run: Windows Firewall prompt → Allow** (Private networks)
2. Check the LAN IP at the venue: `ipconfig` → Wi-Fi adapter IPv4 (at home it's `192.168.0.145`)
3. Tablet: switch Wi-Fi from MMU-GATEWAY → your **home/venue Wi-Fi** (the clipboard survives the switch)
4. Tablet Chrome → `http://192.168.0.145:5000/hub` (use the venue IP)
5. **Paste** (long-press → Paste) → tap **📤 Sync to HealthOutreach server**
6. Look at the console → **the SOS appears live in the feed** 🎉
7. Reset the ESP queue for the next rehearsal: any device on MMU-GATEWAY → `http://192.168.4.1/api/clear` (POST only — use the browser console or just re-flash; or add a Clear button on the hub page)

### STEP 6 · Full 5-minute rehearsal (repeat twice)
| # | Who | Action | Audience sees |
|---|---|---|---|
| 1 | Presenter | Console: "12,000 villages, only 13.8% within 30 min of care" | district bubbles + borders |
| 2 | Presenter | Run Optimization (fleet 3) | ★ outposts, coverage 13.8→22.8%, 14.75M served |
| 3 | You | "This village has no cell coverage" — show Phone A in airplane mode | the phone |
| 4 | Phone A | Join MMU-GATEWAY → portal → tap Maternal SOS | one-tap, zero installs |
| 5 | Tablet | `/hub` → Pull → show the 🔒 ct_sig | encrypted-at-rest proof |
| 6 | Tablet | Switch to Wi-Fi → paste into `http://<laptop-ip>:5000/hub` → Sync | alert pops on console |
| 7 | Presenter | Select 🚁 UAV → click the SOS/cluster | TechEagle handoff card + flight line |
| 8 | Presenter | Switch to Dashboard → WorldPop tab → DHS Live tab | BLR pilot density + live DHS API |
| 9 | All | Q&A | rubric-mapped numbers |

### STEP 7 · Fallbacks (know these cold)
| If this fails | Do this |
|---|---|
| ESP32 won't flash | Hold BOOT during connect; check native-USB socket; check USB CDC On Boot = Enabled |
| Captive portal doesn't pop | Open `192.168.4.1` manually |
| Tablet can't reach laptop `/hub` | Same Wi-Fi? Firewall allowed? Right IP? (`ipconfig`) |
| ESP32 dead on stage | Fallback: open **http://<laptop-ip>:5000/sos** on the phone (venue Wi-Fi) — a REAL phone → REAL server SOS; or the console's 🆘 Simulate Village SOS button |
| Venue Wi-Fi dead | Dashboard runs standalone (local data); DHS tab falls back to local CSV |
| Everything on fire | Recorded demo video (Phase C) |

---

## PART 3 — WHAT'S LEFT BEFORE 10 AM
1. **Phase C — deck + team package** (PPTX + HTML + demo script + per-person tasks + video checklist + Drive zip) — say **go**
2. README + requirements.txt refresh
3. Record the backup demo video (after rehearsal)
4. Copy everything to USB + Google Drive (guidelines mandate backups)
