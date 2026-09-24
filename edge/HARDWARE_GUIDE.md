# HARDWARE GUIDE — The MMU-Gateway Node (ESP32-S3 + LoRa, single board)

Team AIS-42 · verified against `edge/esp32_gateway/*.ino` · demo 10 AM

---

## ⚠️ GOLDEN RULE — DO THIS FIRST

**NEVER power the Ra-02 LoRa module without its antenna connected.** Transmitting
without an antenna creates a severe impedance mismatch (high VSWR) and can permanently
burn out the SX1278 power amplifier. **Screw the antenna onto the gold/u.FL connector
BEFORE plugging in USB.**

## The single-board node

One ESP32-S3 does BOTH jobs:

1. **Wi-Fi Gateway** — broadcasts "MMU-GATEWAY", serves the captive-portal SOS form,
   AES-128-encrypts every SOS, queues them in flash (LittleFS)
2. **LoRa Beacon** — transmits a radio packet every 3 s
   ("when even Wi-Fi can't reach, the same node speaks radio")

If LoRa init fails (no module / no antenna / wrong band), the gateway keeps working —
the firmware guards every radio call.

---

## Breadboard wiring — Ra-02 → ESP32-S3

```
        MMU-GATEWAY NODE — ESP32-S3 + Ra-02 LoRa (breadboard top view)

   ESP32-S3 DevKit                       Ra-02 LoRa module
  ┌──────────────────┐                 ┌─────────────────┐
  │            3V3 ──┼── red ─────────┼── VCC            │
  │            GND ──┼── black ───────┼── GND            │
  │   GPIO12 (SCK) ──┼── orange ──────┼── SCK            │
  │  GPIO13 (MISO) ──┼── yellow ───────┼── MISO           │
  │  GPIO11 (MOSI) ──┼── green ───────┼── MOSI           │
  │   GPIO10 (NSS) ──┼── blue ────────┼── NSS            │
  │   GPIO14 (RST) ──┼── violet ──────┼── RST            │
  │   GPIO21 (DIO0)──┼── grey ────────┼── DIO0           │
  └──────────────────┘                 │   📡 ANTENNA    │
                                       └─────────────────┘
   USB-C → laptop or power bank        (DIO1–DIO5: leave unconnected)
```

| Ra-02 pin | ESP32-S3 pin | Purpose |
|---|---|---|
| VCC / 3.3V | **3V3** | power — **3.3V ONLY, 5V destroys it** |
| GND | GND | ground |
| SCK | GPIO 12 | SPI clock |
| MISO | GPIO 13 | SPI data in |
| MOSI | GPIO 11 | SPI data out |
| NSS / CS | GPIO 10 | chip select |
| RST | GPIO 14 | reset |
| DIO0 | GPIO 21 | packet interrupt (safe pin on the S3 — no strapping issues) |

Keep SPI jumper wires short (<10 cm). All 8 wires fit comfortably across a
half-breadboard; plug the Ra-02 into one side, the S3 devkit into the other.

**Band:** check the frequency printed on the Ra-02 metal can —
433 MHz module → `LORA_BAND 433E6` · 868 MHz module → `LORA_BAND 865E6`
(India IN865 license-free band). Never mix.

---

## Flashing

**Arduino IDE setup (once):**
1. File → Preferences → Additional boards manager URLs:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
2. Tools → Board → Boards Manager → install **esp32 by Espressif Systems**
3. Tools → Manage Libraries → install **LoRa by Sandeep Mistry** (for the beacon)

**Board settings (Tools menu):**

| Setting | Value |
|---|---|
| Board | **ESP32S3 Dev Module** |
| USB CDC On Boot | **Enabled** (critical for Serial) |
| Flash Size | 8 MB (N8R2) — or 4 MB to match your module |
| Partition Scheme | matching "with spiffs" variant |
| Upload Speed | 921600 (drop to 115200 if unstable) |

**Which sketch to flash:**

| File | What it gives you |
|---|---|
| `edge/esp32_gateway/esp32_gateway.ino` | Wi-Fi gateway only (zero wiring needed) |
| `edge/esp32_gateway/esp32_gateway_lora/esp32_gateway_lora.ino` | **Wi-Fi gateway + LoRa beacon (recommended — matches the wiring above)** |

**USB socket:** most S3 devkits have two USB-C sockets — **USB** (native) and
**UART/COM** (bridge). Either can flash. If one shows no COM port or stalls at
"Connecting...", use the other. Still stuck? **Hold the BOOT button** until the
upload percentage starts, then release.

**Success in Serial Monitor (115200):**

```
MMU-GATEWAY up -> http://192.168.4.1  (records=0)
LoRa beacon active
```

then per SOS tap: `SOS queued (maternal/critical) records=1`
and every 3 s: `LoRa beacon N sent`

If you see `LittleFS mount FAILED` → wrong Partition Scheme.
If you see `LoRa init failed (gateway continues)` → check antenna, 3.3V power,
band vs the can, and the wiring table.

---

## Phone & tablet (the live demo flow)

**📱 Phone A — the "village SOS node"**
1. Airplane mode **ON** (proves: no SIM, no 4G, no internet) → Wi-Fi back **ON**
2. Join the open Wi-Fi **MMU-GATEWAY**
3. Android shows "Connected, no internet" + a **"Sign in to network"** notification →
   tap it → the dark SOS portal pops. (No notification? Chrome → `http://192.168.4.1`)
4. Tap **🤰 Maternal Emergency** / **🩸 Trauma** / **💊 Medicine** → "✅ SOS queued"

**📟 Tablet — the "MMU van hub"**
1. Join **MMU-GATEWAY** Wi-Fi
2. Chrome → `http://192.168.4.1/hub` → **⬇ Pull alerts from gateway** →
   alerts render with their 🔒 AES ciphertext signature
3. **📋 Copy JSON**

**💻 Laptop — the payoff**
1. Start the demo (PowerShell):
   ```powershell
   cd E:\ais42-healthoutreach
   powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
   ```
   (First run: allow the Windows Firewall prompt.)
2. Find the laptop IP: `ipconfig` → Wi-Fi IPv4
3. Tablet: switch Wi-Fi to the venue/hotspot network → open `http://<LAPTOP-IP>:5000/hub`
4. **Paste** → **📤 Sync to HealthOutreach server**
5. The alert pops **live** in the console SOS feed 🎉

Reset the node's queue between rehearsals: any device on MMU-GATEWAY →
`http://192.168.4.1/api/clear` (POST — run from the browser dev console), or re-flash.

---

## Desk layout & the pitch

- **Left:** breadboard — S3 node + Ra-02 + antenna proudly standing up
- **Center:** the phone in airplane mode showing the captive portal
- **Right:** the tablet showing the hub queue with 🔒 ciphertext signatures
- **Screen:** Ops Console (:5000) + Impact Dashboard (:8501)

**The pitch:**

> "Judges, rural villages don't have 5G. Standard apps fail here. This phone is in
> airplane mode — it connects to our off-grid ESP32 node, queues an AES-128 encrypted
> emergency SOS, and when our Mobile Medical Unit drives through, the hub harvests the
> alerts and syncs them to our spatial optimization engine. And when even Wi-Fi can't
> reach — the same node speaks LoRa radio; that's the live packet stream on the serial
> monitor."

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Upload stuck at "Connecting..." | Hold BOOT during connect; try the other USB socket; USB CDC On Boot = Enabled |
| No Serial output | USB CDC On Boot must be Enabled; re-upload |
| `LittleFS mount FAILED` | Partition Scheme must include SPIFFS/LittleFS |
| Portal doesn't auto-open | Chrome → `192.168.4.1` manually |
| "Connected, no internet" | Expected — that's the point |
| Tablet can't reach laptop /hub | Same Wi-Fi? Firewall allowed? Right IP (`ipconfig`)? |
| `LoRa init failed` | Antenna on? 3.3V (not 5V)? Band matches the can? Wiring per table? |
| No `LoRa beacon N sent` in Serial | You flashed the plain gateway sketch — flash the `_lora` variant |
| ESP32 dead on stage | Phone opens `http://<laptop-ip>:5000/sos` on venue Wi-Fi — a REAL phone → REAL server SOS |
