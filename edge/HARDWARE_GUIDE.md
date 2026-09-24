# HARDWARE GUIDE — MMU Gateway + LoRa Beacon (verified against repo firmware)

Team AIS-42 · demo 10 AM · this guide matches `edge/esp32_gateway/esp32_gateway.ino` exactly.

---

## ⚠️ GOLDEN RULE #1 FOR LoRa (DO THIS FIRST)

**NEVER power a LoRa module without its antenna connected.** Transmitting without an
antenna creates a severe impedance mismatch (high VSWR) and can permanently burn out the
SX1278 RF power amplifier. **Screw the antenna on before plugging in USB.**

## What each board is for

| Board | Role tonight |
|---|---|
| **ESP32-S3** | The MMU Gateway — flash `edge/esp32_gateway/esp32_gateway.ino`. The live interactive demo (Wi-Fi AP + captive portal + AES-128 queue). Zero jumper wires. |
| **ESP-WROOM-32 + Ra-02** | The LoRa radio beacon — optional physical proof-of-concept ("when even Wi-Fi can't reach, the same node speaks radio"). |
| **Arduino Uno** | Spare. Not used tonight (it's 5V logic — the Ra-02 is 3.3V only). |

You can run BOTH on the desk: S3 as the live gateway, WROOM+Ra-02 as the radio beacon.

---

## PART 1 — Flash the ESP32-S3 (the MMU Gateway)

The S3 has two USB-C sockets: use the one labeled **COM/UART** for flashing
(the native **USB** one also works on most devkits; if upload stalls, switch sockets).

1. **Arduino IDE → File → Preferences → Additional boards manager URLs**, paste:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json` → OK
2. **Tools → Board → Boards Manager** → search `esp32` → install **esp32 by Espressif Systems**
3. **File → Open** → `E:\ais42-healthoutreach\edge\esp32_gateway\esp32_gateway.ino`
4. **Tools** menu:

| Setting | Value |
|---|---|
| Board | **ESP32S3 Dev Module** |
| USB CDC On Boot | **Enabled** (critical for Serial) |
| Flash Size | 8 MB (N8R2) — use 4 MB if your module says 4MB |
| Partition Scheme | matching "with spiffs" variant |
| Upload Speed | 921600 (drop to 115200 if unstable) |
| Port | the new COM port |

5. **Upload (→)**. Stuck at "Connecting..."? **Hold BOOT** on the board until the
   percentage starts, then release.
6. **Tools → Serial Monitor** (115200). You should see EXACTLY:

```
MMU-GATEWAY up -> http://192.168.4.1  (records=0)
```

and after each SOS tap on the phone:

```
SOS queued (maternal/critical) records=1
```

If you ever see `LittleFS mount FAILED` → wrong Partition Scheme (must include SPIFFS/LittleFS).

---

## PART 2 — Phone & Tablet (the live demo flow)

**📱 Phone A — the "village SOS node"**
1. Airplane mode **ON** (proves: no SIM, no 4G, no internet) → Wi-Fi back **ON**
2. Join the open Wi-Fi **MMU-GATEWAY**
3. Android shows "Connected, no internet" + a **"Sign in to network"** notification → tap it →
   the dark SOS portal pops. (No notification? Chrome → `http://192.168.4.1`)
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
2. Find the laptop IP: `ipconfig` → Wi-Fi IPv4 (home: `192.168.0.145`)
3. Tablet: switch Wi-Fi to the venue/hotspot network → open `http://<LAPTOP-IP>:5000/hub`
4. **Paste** → **📤 Sync to HealthOutreach server**
5. The alert pops **live** in the console SOS feed 🎉

Reset the gateway queue between rehearsals: any device on MMU-GATEWAY →
`http://192.168.4.1/api/clear` (POST — use the browser console, or just re-flash).

---

## PART 3 — LoRa Ra-02 → ESP-WROOM-32 wiring (optional beacon)

**⚠️ VCC → 3.3V ONLY. 5V/VIN instantly destroys the SX1278.**

| Ra-02 pin | ESP-WROOM-32 | Purpose |
|---|---|---|
| VCC / 3.3V | **3V3** | power |
| GND | GND | ground |
| SCK | GPIO 18 | SPI clock |
| MISO | GPIO 19 | SPI data in |
| MOSI | GPIO 23 | SPI data out |
| NSS / CS | GPIO 5 | chip select |
| RST | GPIO 14 | reset |
| DIO0 | GPIO 2 ⚠️ | packet interrupt — **see note** |

Leave DIO1–DIO5 unconnected. Keep SPI jumper wires short (<10 cm).

**⚠️ DIO0 / GPIO 2 note:** GPIO 2 is a boot-strapping pin. If the WROOM refuses to enter
flash mode ("Connecting..." forever) while the module is wired, **unplug the DIO0 jumper
during upload** and reconnect after — or wire DIO0 to GPIO 26 instead.

**📡 Band:** check the frequency **printed on the Ra-02 metal can**:
- 433 MHz module → `LoRa.begin(433E6)`
- 868 MHz module → `LoRa.begin(865E6)` (India IN865 license-free band)
Never mix — a 433 module at 865E6 will barely radiate.

**Library:** Arduino IDE → Tools → Manage Libraries → install **LoRa by Sandeep Mistry**.

**Beacon sketch** (flash to the WROOM-32; Board: "ESP32 Dev Module"):

```cpp
#include <SPI.h>
#include <LoRa.h>
#define SCK   18
#define MISO  19
#define MOSI  23
#define SS    5
#define RST   14
#define DIO0  2      // unplug this jumper during upload if flashing fails
#define BAND  433E6  // match the frequency printed on your Ra-02 can!

void setup() {
  Serial.begin(115200);
  SPI.begin(SCK, MISO, MOSI, SS);
  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(BAND)) {
    Serial.println("LoRa init failed! Check wiring & antenna.");
    while (1);
  }
  Serial.println("LoRa Radio Beacon Active - Team AIS-42");
}

int count = 0;
void loop() {
  Serial.print("Sending SOS packet: ");
  Serial.println(count);
  LoRa.beginPacket();
  LoRa.print("{\"node\":\"ESP_VIL_42\",\"type\":\"MATERNAL\",\"seq\":");
  LoRa.print(count++);
  LoRa.print("}");
  LoRa.endPacket();
  delay(3000);
}
```

Success = a packet counter ticking every 3 s in Serial Monitor. (TX-only beacon is a fine
demo prop. A live RX demo needs a second radio — skip it tonight; the Uno is 5V logic and
would need level-shifting to talk to a 3.3V Ra-02.)

---

## PART 4 — Desk layout & the pitch

- **Left:** breadboard with the ESP32-S3 gateway (+ your perfboard & antenna as props)
- **Center:** the phone in airplane mode showing the captive portal
- **Right:** the tablet showing the hub queue with 🔒 ciphertext signatures
- **Screen:** Ops Console (:5000) + Impact Dashboard (:8501)

**The pitch (corrected — say this):**

> "Judges, rural villages don't have 5G. Standard apps fail here. This phone is in
> airplane mode — it connects to our off-grid ESP32 node, queues an AES-128 encrypted
> emergency SOS, and when our Mobile Medical Unit drives through, the hub harvests the
> alerts and syncs them to our spatial optimization engine. And when even Wi-Fi can't
> reach — the same node speaks LoRa radio; here's the live packet stream."

*(Don't say "over LoRa mesh" for the Wi-Fi portal demo — the LoRa beacon is the
beyond-Wi-Fi extension, shown separately.)*

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| S3 upload stuck at "Connecting..." | Hold BOOT during connect; check USB CDC On Boot = Enabled; try the other USB socket |
| No Serial output | USB CDC On Boot must be Enabled; re-upload |
| `LittleFS mount FAILED` | Partition Scheme must include SPIFFS/LittleFS |
| Portal doesn't auto-open | Chrome → `192.168.4.1` manually |
| "Connected, no internet" | Expected — that's the point |
| Tablet can't reach laptop /hub | Same Wi-Fi? Firewall allowed? Right IP (`ipconfig`)? |
| WROOM won't flash with LoRa wired | Unplug DIO0 (GPIO 2) during upload |
| "LoRa init failed" | Antenna on? 3.3V (not 5V)? Band matches the can? Wiring per table? |
| ESP32 dead on stage | Phone opens `http://<laptop-ip>:5000/sos` on venue Wi-Fi — a REAL phone → REAL server SOS |
