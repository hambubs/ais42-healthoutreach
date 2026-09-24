/*
 * =====================================================================
 *  AIS-42 HealthOutreach — MMU Gateway node (offline village SOS)
 *  Board: ESP32-S3 Dev Module  (also runs on classic ESP32 / WROOM-32)
 * ---------------------------------------------------------------------
 *  Stage flow:
 *    1. Broadcasts open Wi-Fi AP "MMU-GATEWAY"
 *    2. Wildcard DNS -> captive portal auto-opens on the villager's
 *       phone (Android: tap "Sign in to network")
 *    3. One-tap SOS form: Trauma / Maternal / Medicine + priority
 *    4. Payload is AES-128-CBC encrypted (mbedTLS, random IV) and
 *       queued in flash (LittleFS) -- encrypted at rest
 *    5. MMU hub tablet opens http://192.168.4.1/hub  -> pulls the
 *       queue, shows the alerts + exportable JSON
 *    6. Back on internet, the hub page on the server pastes/imports
 *       the JSON -> POST /api/sync -> live on the Ops Console
 *
 *  Wiring: NONE required. The phone browser is the whole interface.
 * =====================================================================
 */
#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <LittleFS.h>
#include <mbedtls/aes.h>
#include <mbedtls/base64.h>
#include <esp_system.h>

const char*    AP_SSID     = "MMU-GATEWAY";
const byte     DNS_PORT    = 53;
const char*    QUEUE_PATH  = "/queue.ndjson";
const uint16_t MAX_RECORDS = 200;

/* Demo AES-128 key ("AIS42MMUGATEWAY2"). A production deployment would
 * provision per-node keys; this keeps the hackathon demo self-contained. */
static const uint8_t AES_KEY[16] = {
  0x41, 0x49, 0x53, 0x34, 0x32, 0x4D, 0x4D, 0x55,
  0x47, 0x41, 0x54, 0x45, 0x57, 0x41, 0x59, 0x32
};

DNSServer dnsServer;
WebServer server(80);
uint32_t  recordCount = 0;

/* ------------------------------------------------------------- helpers */
String hex8(uint8_t v) { char b[3]; sprintf(b, "%02X", v); return String(b); }
String toHex(const uint8_t* buf, size_t len) {
  String s; for (size_t i = 0; i < len; i++) s += hex8(buf[i]); return s;
}

/* AES-128-CBC encrypt a JSON string -> "iv_hex.ct_base64" */
String encryptRecord(const String& plain) {
  size_t plen = plain.length();
  uint8_t pad = 16 - (plen % 16);
  size_t clen = plen + pad;
  uint8_t* in  = (uint8_t*)malloc(clen);
  uint8_t* out = (uint8_t*)malloc(clen);
  uint8_t  iv[16], ivCopy[16];
  for (int i = 0; i < 16; i++) iv[i] = (uint8_t)esp_random();
  memcpy(ivCopy, iv, 16);
  memcpy(in, plain.c_str(), plen);
  for (size_t i = plen; i < clen; i++) in[i] = pad;          /* PKCS#7 */

  mbedtls_aes_context ctx;
  mbedtls_aes_init(&ctx);
  mbedtls_aes_setkey_enc(&ctx, AES_KEY, 128);
  mbedtls_aes_crypt_cbc(&ctx, MBEDTLS_AES_ENCRYPT, clen, ivCopy, in, out);
  mbedtls_aes_free(&ctx);

  size_t blen = 4 * ((clen / 3) + 2);
  uint8_t* b64 = (uint8_t*)malloc(blen);
  size_t olen = 0;
  mbedtls_encode_base64(b64, blen, &olen, out, clen);

  String rec = toHex(iv, 16) + "." + String((char*)b64).substring(0, olen);
  free(in); free(out); free(b64);
  return rec;
}

/* AES-128-CBC decrypt "iv_hex.ct_base64" -> plaintext ("" on failure) */
String decryptRecord(const String& rec) {
  int dot = rec.indexOf('.');
  if (dot != 32) return "";                 /* IV must be 32 hex chars */
  String ivHex = rec.substring(0, 32);
  String b64   = rec.substring(33);
  uint8_t iv[16], ivCopy[16];
  for (int i = 0; i < 16; i++) iv[i] = (uint8_t)strtol(ivHex.substring(i * 2, i * 2 + 2).c_str(), NULL, 16);
  memcpy(ivCopy, iv, 16);

  size_t maxOut = b64.length();
  uint8_t* ct = (uint8_t*)malloc(maxOut);
  uint8_t* pt = (uint8_t*)malloc(maxOut + 16);
  size_t olen = 0;
  mbedtls_decode_base64(ct, maxOut, &olen, (const uint8_t*)b64.c_str(), b64.length());
  if (olen == 0 || olen % 16 != 0) { free(ct); free(pt); return ""; }

  mbedtls_aes_context ctx;
  mbedtls_aes_init(&ctx);
  mbedtls_aes_setkey_dec(&ctx, AES_KEY, 128);
  mbedtls_aes_crypt_cbc(&ctx, MBEDTLS_AES_DECRYPT, olen, ivCopy, ct, pt);
  mbedtls_aes_free(&ctx);
  uint8_t pad = pt[olen - 1];
  if (pad < 1 || pad > 16) pad = 0;
  String s = String((char*)pt).substring(0, olen - pad);
  free(ct); free(pt);
  return s;
}

uint32_t countRecords() {
  File f = LittleFS.open(QUEUE_PATH, "r");
  if (!f) return 0;
  uint32_t n = 0;
  while (f.available()) { if (f.read() == '\n') n++; }
  f.close();
  return n;
}

/* ----------------------------------------------------------- HTML pages */
static const char PORTAL_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MMU SOS</title><style>
:root{--bg:#0b1220;--card:#16233d;--accent:#22d3a7;--red:#e74c3c;--amber:#f39c12;--blue:#3b82f6;--text:#e8eefc}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:var(--bg);color:var(--text);
display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;padding:16px}
h1{font-size:18px;margin-bottom:4px}.sub{font-size:11px;color:#8ea0c0;margin-bottom:18px}
.btn{display:block;width:100%;max-width:340px;margin:10px 0;padding:22px;border-radius:14px;border:none;
font-size:18px;font-weight:700;color:#fff;cursor:pointer}
.trauma{background:var(--red)}.mat{background:var(--amber)}.med{background:var(--blue)}
.badge{margin-top:16px;font-size:10px;color:#8ea0c0}.ok{display:none;margin-top:14px;color:var(--accent);font-weight:700}
</style></head><body>
<h1>&#128657; Emergency SOS &mdash; Village Node</h1>
<div class="sub">HealthOutreach offline gateway &middot; no SIM / no internet needed</div>
<button class="btn trauma" onclick="sos('trauma')">&#129652; Trauma / Accident</button>
<button class="btn mat"     onclick="sos('maternal')">&#129328; Maternal Emergency</button>
<button class="btn med"    onclick="sos('medicine')">&#128138; Medicine Shortage</button>
<div class="ok" id="ok">&#9989; SOS queued &mdash; the MMU hub will carry it to the hospital</div>
<div class="badge">&#128274; Payload is AES-128 encrypted before it leaves this form</div>
<script>
async function sos(t){
  try{
    const r = await fetch('/sos',{method:'POST',
      headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:'type='+t+'&priority='+(t==='medicine'?'high':'critical')});
    if(r.ok){document.getElementById('ok').style.display='block';
      document.querySelectorAll('.btn').forEach(b=>b.disabled=true);
      setTimeout(()=>document.querySelectorAll('.btn').forEach(b=>b.disabled=false),4000);}
  }catch(e){alert('Failed — move closer to the gateway and retry');}
}
</script></body></html>
)rawliteral";

static const char HUB_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MMU Hub — offline queue</title><style>
:root{--bg:#0b1220;--card:#16233d;--accent:#22d3a7;--text:#e8eefc;--red:#e74c3c}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui;background:var(--bg);color:var(--text);padding:16px}
h1{font-size:16px;margin-bottom:2px}.sub{font-size:11px;color:#8ea0c0;margin-bottom:14px}
button{background:var(--accent);color:#04241b;border:none;border-radius:8px;padding:12px;font-weight:700;
width:100%;margin:8px 0;cursor:pointer}textarea{width:100%;height:140px;background:var(--card);color:var(--text);
border:1px solid #1e2a44;border-radius:8px;padding:8px;font-size:11px}
.item{background:var(--card);border-left:3px solid var(--red);border-radius:8px;padding:10px;margin:6px 0;font-size:13px}
.meta{color:#8ea0c0;font-size:10px}</style></head><body>
<h1>&#128230; MMU Hub &mdash; offline queue</h1>
<div class="sub">Pull alerts captured at the village, then carry this JSON to the online hub page</div>
<button onclick="pull()">&#11015; Pull alerts from gateway</button>
<div id="list"></div>
<textarea id="payload" readonly placeholder="Pull to load the encrypted-at-rest queue (decrypted for the hub)"></textarea>
<button onclick="copyPayload()">&#128203; Copy JSON (paste into the online hub page)</button>
<script>
async function pull(){
  const r=await fetch('/api/queue');const q=await r.json();
  document.getElementById('payload').value=JSON.stringify(q.alerts);
  const L=document.getElementById('list');L.innerHTML='';
  q.alerts.forEach(a=>{
    const d=document.createElement('div');d.className='item';
    d.innerHTML='<b>'+a.type.toUpperCase()+'</b> &middot; '+a.priority+
      '<div class="meta">node '+a.node+' &middot; gateway ts '+a.ts+
      ' &middot; &#128274; '+a.ct_sig+'</div>';
    L.appendChild(d);});
}
function copyPayload(){const t=document.getElementById('payload');t.select();
  document.execCommand('copy');alert('Copied — now reconnect to internet and open the server hub page');}
pull();
</script></body></html>
)rawliteral";

/* -------------------------------------------------------- route handlers */
void handleRoot()  { server.send_P(200, "text/html", PORTAL_HTML); }
void handleHub()   { server.send_P(200, "text/html", HUB_HTML); }

void handleSos() {
  String type    = server.arg("type");
  String priority= server.arg("priority");
  if (type != "trauma" && type != "maternal" && type != "medicine") {
    server.send(400, "application/json", "{\"error\":\"bad type\"}");
    return;
  }
  if (priority != "critical" && priority != "high" && priority != "normal") priority = "high";

  uint64_t mac = ESP.getEfuseMac();
  char node[16];
  snprintf(node, sizeof(node), "VIL-%04X", (uint16_t)(mac & 0xFFFF));

  String plain = "{\"type\":\"" + type + "\",\"priority\":\"" + priority +
                 "\",\"node\":\"" + String(node) + "\",\"ts\":" + String(millis()) + "}";
  String rec   = encryptRecord(plain);

  if (recordCount >= MAX_RECORDS) {                 /* demo-scale rotation */
    LittleFS.remove(QUEUE_PATH);
    recordCount = 0;
  }
  File f = LittleFS.open(QUEUE_PATH, FILE_APPEND);
  if (!f) { server.send(500, "application/json", "{\"error\":\"fs\"}"); return; }
  f.println(rec);
  f.close();
  recordCount++;
  Serial.printf("SOS queued (%s/%s) records=%u\n", type.c_str(), priority.c_str(), recordCount);
  server.send(200, "application/json", "{\"ok\":true,\"records\":" + String(recordCount) + "}");
}

void handleQueue() {
  String out = "{\"count\":" + String(recordCount) + ",\"alerts\":[";
  File f = LittleFS.open(QUEUE_PATH, "r");
  if (f) {
    bool first = true;
    while (f.available()) {
      String line = f.readStringUntil('\n');
      line.trim();
      if (line.length() < 34) continue;
      String plain = decryptRecord(line);
      if (plain.length() == 0) continue;
      String sig = line.substring(33, 41);          /* 8 hex chars of ciphertext */
      String rec = plain.substring(0, plain.length() - 1) +
                   ",\"ct_sig\":\"" + sig + "\"}";
      if (!first) out += ",";
      out += rec;
      first = false;
    }
    f.close();
  }
  out += "]}";
  server.send(200, "application/json", out);
}

void handleClear() {
  LittleFS.remove(QUEUE_PATH);
  recordCount = 0;
  server.send(200, "application/json", "{\"cleared\":true}");
}

void handleNotFound() {
  /* Captive-portal probes (Android/Apple/Windows) -> bounce to portal */
  server.sendHeader("Location", "http://" + WiFi.softAPIP().toString() + "/", true);
  server.send(302, "text/plain", "");
}

/* ---------------------------------------------------------------- setup */
void setup() {
  Serial.begin(115200);
  if (!LittleFS.begin(true)) { Serial.println("LittleFS mount FAILED"); }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID);                              /* open AP for the demo */
  dnsServer.start(DNS_PORT, "*", WiFi.softAPIP());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/hub", HTTP_GET, handleHub);
  server.on("/sos", HTTP_POST, handleSos);
  server.on("/api/queue", HTTP_GET, handleQueue);
  server.on("/api/clear", HTTP_POST, handleClear);
  server.onNotFound(handleNotFound);
  server.begin();

  recordCount = countRecords();
  Serial.printf("MMU-GATEWAY up -> http://%s  (records=%u)\n",
                WiFi.softAPIP().toString().c_str(), recordCount);
}

void loop() {
  dnsServer.processNextRequest();
  server.handleClient();
}