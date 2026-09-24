# ESP32-S3 Flash Checklist — MMU Gateway

Team AIS-42 · offline village SOS node · zero wiring required

## 1. One-time IDE setup ( laptop )

You have BOTH **Arduino IDE 2.x** and **PlatformIO** (VS Code). Pick one — the
firmware is identical, just the project shape differs.

**Arduino IDE**
1. **File → Preferences → Additional boards manager URLs**:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
2. **Tools → Board → Boards Manager** → install **esp32 by Espressif Systems**
3. Open `edge/esp32_gateway/esp32_gateway.ino`

**PlatformIO (VS Code)**
1. Install the **PlatformIO IDE** VS Code extension
2. **Create a new project** with the `platformio.ini` below (copy the values)
3. Move the sketch into `src/main.cpp` and add `#include <Arduino.h>` at the top

```ini
[env:esp32-s3-devkitc-1]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
board_build.filesystem = littlefs
build_flags =
    -DARDUINO_USB_CDC_ON_BOOT=1
```

## 2. Board settings for ESP32-S3 (Tools menu)

| Setting | Value |
|---|---|
| Board | **ESP32S3 Dev Module** |
| USB CDC On Boot | **Enabled** (needed for Serial over the S3's native USB) |
| Flash Size | 8 MB (use 4 MB if your module is 4 MB — check the silkscreen) |
| Partition Scheme | Default 4MB with spiffs / 8MB with spiffs (matching flash size) |
| Upload Speed | 921600 |
| Port | The **native-USB** socket (labeled `USB`/`COM`). If only `UART` is exposed, use that for flashing |

If upload hangs at **"Connecting..."** → hold the **BOOT** button on the board while
it tries to connect, release when flashing starts.

## 3. Flash + verify ( 5 minutes )

1. **Upload** (→ button). Watch the console for:
   `MMU-GATEWAY up -> http://192.168.4.1  (records=0)`
2. **Phone A (airplane mode ON, Wi-Fi allowed)** → join Wi-Fi **MMU-GATEWAY**
   (open network). Android will say "Connected, no internet" — that's correct.
   Tap the **"Sign in to network"** notification → the SOS portal auto-opens.
   (If it doesn't pop: open the browser and go to `http://192.168.4.1` manually.)
3. Tap **🩸 Trauma / 🤰 Maternal / 💊 Medicine** → "✅ SOS queued".
4. **Tablet (Wi-Fi → MMU-GATEWAY)** → browser → `http://192.168.4.1/hub`
   → Pull → you should see the alert(s) + the AES ciphertext signature (first bytes).
5. **Copy JSON** on the tablet → switch tablet back to the internet/hotspot →
   open the **server hub page** (`http://localhost:5000/hub` once Phase A adds it)
   → paste → **Sync** → the alert appears live in the Ops Console SOS feed.
6. Reset the demo: `curl -X POST http://192.168.4.1/api/clear` from any device on the AP,
   or re-upload the sketch.

## 4. Stage demo flow ( the story we tell )

1. "This village has **no cell coverage**. The phone is in airplane mode." (show the phone)
2. Phone joins **MMU-GATEWAY** → captive portal pops (zero installs — any browser)
3. One tap: **Maternal Emergency** → AES-128 encrypted, queued on the gateway
4. Tablet (hub) pulls the offline queue — show the ciphertext signature on screen
5. "The MMU drives back toward coverage" → hub syncs → **alert pops live on the console**
6. Console: dispatch 🚁 UAV for the poor-road cluster → TechEagle-class handoff card

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Upload stuck at "Connecting..." | Hold BOOT during connect; check you're on the native-USB socket |
| No Serial output | USB CDC On Boot must be **Enabled**; re-upload |
| Portal doesn't auto-open | Open `http://192.168.4.1` manually — Android captive detection is lazy sometimes |
| "Connected, no internet" warning | Expected — that's why the portal exists |
| LittleFS mount FAILED | Re-upload with matching Partition Scheme (must include SPIFFS/LittleFS) |
| ESP32 acts weird on stage | Fallback: use the console's **🆘 Simulate Village SOS** + **📡 Simulate Hub Sync** demo buttons — same story, zero hardware |

## 6. Hardware notes

- **No external parts needed** — no buttons, no sensors. The phone browser is the interface.
- Runs on the classic ESP32/WROOM-32 too (board: "ESP32 Dev Module", USB CDC setting ignored).
- Power: any USB power bank works for the stage (S3 AP mode draws ~0.5 W).