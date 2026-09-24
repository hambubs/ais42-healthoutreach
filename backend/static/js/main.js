/* =====================================================================
   AIS-42 HealthOutreach — Ops Console (Leaflet)
   Villages (risk) · facilities · district borders · DBSCAN→MCLP outposts
   Live SOS feed · 5-mode dispatch · UAV partner handoff
   ===================================================================== */
const RISK_COLORS = { Low: "#2ecc71", Medium: "#f39c12", High: "#e74c3c" };
const MODE_COLORS = { ambulance: "#e74c3c", mmu_van: "#22d3a7", rider_2w: "#f39c12", bike: "#2ecc71", uav: "#3b82f6", helicopter: "#e67e22", outpost: "#a78bfa" };

let map, villagesData = [], facilitiesData = [], villagesById = new Map();
let villageLayer, facilityLayer, districtLayer, outpostLayer, sosLayer, dispatchLayer, circuitLayer;
let outposts = [], selectedMode = null, seenSos = new Set(), sosCount = 0, lastFeedSig = null;
let districtBubbleLayer, lodTimer = null;

/* ------------------------------------------------------------------ init */
function init() {
  map = L.map("map", { preferCanvas: true }).setView([22.8, 80.5], 5);
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    attribution: "Tiles &copy; Esri &middot; Data &copy; OpenStreetMap contributors", maxZoom: 18
  }).addTo(map);

  districtLayer = L.layerGroup().addTo(map);
  villageLayer  = L.layerGroup().addTo(map);
  circuitLayer = L.layerGroup().addTo(map);
  facilityLayer = L.layerGroup();
  outpostLayer  = L.layerGroup().addTo(map);
  sosLayer      = L.layerGroup().addTo(map);
  dispatchLayer = L.layerGroup().addTo(map);
  districtBubbleLayer = L.layerGroup().addTo(map);

  map.on("click", onMapClick);
  map.on("zoomend moveend", scheduleLOD);

  loadVillages();
  loadFacilities();
  loadDistricts();
  loadDistrictBubbles();
  loadModes();
  bindControls();
  setInterval(pollSos, 5000);
  pollSos();
  loadBaseline();
  scheduleLOD();
  window.addEventListener("online", updateMeshBadge);
  window.addEventListener("offline", updateMeshBadge);
}

/* --------------------------------------------------------------- helpers */
function toast(msg, ms = 3200) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.display = "block";
  clearTimeout(t._timer);
  t._timer = setTimeout(() => (t.style.display = "none"), ms);
}
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
  return r.json();
}
const fmt = (n) => n.toLocaleString("en-IN");

async function loadBaseline() {
  try {
    const b = await api("/api/baseline");
    document.getElementById("kpi-coverage").textContent = b.coverage_pct_villages + "%";
    document.getElementById("kpi-sched").textContent = b.coverage_pct_villages + "%";
    document.getElementById("kpi-under").textContent = fmt(b.underserved_villages);
  } catch (e) { /* keep hardcoded defaults */ }
}

/* --------------------------------------------------------------- villages */
async function loadVillages() {
  try {
    villagesData = await api("/api/villages");
    villagesData.forEach((v) => villagesById.set(v.Village_ID, v));
    drawVillages();
  } catch (e) { toast("Failed to load villages: " + e.message); }
}
function drawVillages() {
  villageLayer.clearLayers();
  if (map.getZoom() < 7) return;            // LOD: bubbles own the low-zoom view
  const state = document.getElementById("state-filter").value;
  const b = map.getBounds();
  villagesData
    .filter((v) => (!state || v.State === state) &&
      v.Latitude >= b.getSouth() && v.Latitude <= b.getNorth() &&
      v.Longitude >= b.getWest() && v.Longitude <= b.getEast())
    .forEach((v) => {
      const c = L.circleMarker([v.Latitude, v.Longitude], {
        radius: Math.min(2 + Math.sqrt(v.Population) / 60, 6),
        color: RISK_COLORS[v.Healthcare_Risk_Level] || "#888",
        weight: v.Underserved_Area_Flag_bin ? 1.5 : 0.4,
        opacity: 0.9,
        fillColor: RISK_COLORS[v.Healthcare_Risk_Level] || "#888",
        fillOpacity: 0.55,
      });
      c.bindPopup(
        `<b>${v.Village_ID}</b> · ${v.District}, ${v.State}<br>` +
        `Population: ${fmt(v.Population)}<br>` +
        `Travel to care: ${v.Average_Travel_Time_min} min (${v.Distance_to_Hospital_km ?? "—"} km)<br>` +
        `Road: ${v.Road_Connectivity} · Risk: ${v.Healthcare_Risk_Level}<br>` +
        `Need score: ${v.need_score}${v.Underserved_Area_Flag_bin ? " · <b>UNDERSERVED</b>" : ""}`
      );
      villageLayer.addLayer(c);
    });
}

/* -------------------------------------------------------------- facilities */
async function loadFacilities() {
  try {
    facilitiesData = await api("/api/facilities?state=Uttar+Pradesh&state=Madhya+Pradesh&state=Maharashtra&state=Rajasthan&state=Bihar&state=Karnataka");
    facilitiesData.forEach((f) => {
      const c = L.circleMarker([f.lat, f.lon], {
        radius: 2.4, color: f.has_emergency ? "#3b82f6" : "#1e5fa8",
        weight: 1, fillColor: "#3b82f6", fillOpacity: 0.7,
      });
      c.bindPopup(`<b>${f.Hospital_Name}</b><br>${f.District}, ${f.State}` +
        `${f.has_emergency ? "<br>⚡ Emergency services" : ""}` +
        `${f.has_ambulance ? "<br>🚑 Ambulance" : ""}`);
      facilityLayer.addLayer(c);
    });
  } catch (e) { toast("Failed to load facilities: " + e.message); }
}

/* --------------------------------------------------------------- districts */
async function loadDistricts() {
  try {
    const gj = await api("/api/geojson/districts");
    L.geoJSON(gj, {
      style: { color: "#3b82f6", weight: 1, opacity: 0.5, dashArray: "4 4", fill: false },
      onEachFeature: (ft, ly) =>
        ly.bindPopup(`<b>${ft.properties.shapeName}</b> district`),
    }).addTo(districtLayer);
  } catch (e) { toast("Failed to load district borders: " + e.message); }
}

/* ------------------------------------------------- zoom Level-of-Detail */
async function loadDistrictBubbles() {
  try {
    const ds = await api("/api/districts");
    const state = document.getElementById("state-filter").value;
    districtBubbleLayer.clearLayers();
    ds.forEach((d) => {
      if (d.lat == null || d.lon == null) return;
      if (state && d.State !== state) return;
      const need = d.mean_need ?? 0;
      const col = need < 0.40 ? "#2ecc71" : need < 0.45 ? "#f39c12" : "#e74c3c";
      const c = L.circleMarker([d.lat, d.lon], {
        radius: Math.min(34, 10 + Math.sqrt(d.underserved || 0) * 1.2),
        color: col, weight: 1, fillColor: col, fillOpacity: 0.55,
      });
      c.bindPopup(
        `<b>${d.District}, ${d.State}</b><br>` +
        `${fmt(d.villages)} villages · ${fmt(d.population)} people<br>` +
        `${fmt(d.underserved)} underserved · ${d.facilities_directory ?? d.facilities} facilities<br>` +
        `mean need ${d.mean_need != null ? d.mean_need.toFixed(3) : "—"}`
      );
      districtBubbleLayer.addLayer(c);
    });
  } catch (e) { console.error("bubbles failed:", e); }
}

function scheduleLOD() {
  clearTimeout(lodTimer);
  lodTimer = setTimeout(applyLOD, 300);
}

function applyLOD() {
  const z = map.getZoom();
  const villagesOn = document.getElementById("layer-villages").checked;
  const facOn = document.getElementById("layer-facilities").checked;
  if (z < 7) {
    map.addLayer(districtBubbleLayer);
    map.removeLayer(villageLayer);
    map.removeLayer(facilityLayer);
  } else {
    map.removeLayer(districtBubbleLayer);
    if (villagesOn) { map.addLayer(villageLayer); drawVillages(); }
    else map.removeLayer(villageLayer);
    if (facOn && z >= 8) map.addLayer(facilityLayer);
    else map.removeLayer(facilityLayer);
  }
}

/* -------------------------------------------------- mesh badge + search */
let pendingSync = 0;
function updateMeshBadge() {
  const el = document.getElementById("mesh-mode");
  if (!el) return;
  el.textContent = navigator.onLine ? "🟢 Online" : "🔴 Offline";
  const q = document.getElementById("mesh-queue");
  if (q) q.textContent = pendingSync > 0 ? `⏳ ${pendingSync} queued` : "✓ synced";
}

function doSearch(q) {
  q = (q || "").trim().toLowerCase();
  if (!q) return;
  const v = villagesData.find((x) =>
    x.Village_ID.toLowerCase() === q || x.District.toLowerCase().includes(q));
  if (v) { map.flyTo([v.Latitude, v.Longitude], 11); toast(`${v.Village_ID} · ${v.District}, ${v.State}`); return; }
  const f = facilitiesData.find((x) => (x.Hospital_Name || "").toLowerCase().includes(q));
  if (f) { map.flyTo([f.lat, f.lon], 12); toast(`${f.Hospital_Name} · ${f.District}`); return; }
  toast("No match found");
}

/* ------------------------------------------------------------------ modes */
async function loadModes() {
  const modes = await api("/api/modes");
  const grid = document.getElementById("mode-grid");
  grid.innerHTML = "";
  Object.entries(modes).forEach(([key, m]) => {
    const el = document.createElement("div");
    el.className = "mode-card";
    el.dataset.mode = key;
    el.innerHTML = `<span class="icon">${m.icon}</span><b>${m.label}</b><br><span class="hint">${m.trigger}</span>`;
    el.onclick = () => selectMode(key, m.label, el);
    grid.appendChild(el);
  });
}
function selectMode(key, label, el) {
  document.querySelectorAll(".mode-card").forEach((c) => c.classList.remove("selected"));
  if (selectedMode === key) { selectedMode = null; return; }
  selectedMode = key;
  el.classList.add("selected");
  toast(`${label} armed — click an outpost ★ or a map point to dispatch`);
}

/* --------------------------------------------------------------- optimize */
async function runOptimize() {
  const fleet = +document.getElementById("fleet").value;
  const minutes = +document.getElementById("minutes").value;
  toast("Running DBSCAN + greedy MCLP…");
  try {
    const r = await api("/api/optimize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fleet_size: fleet, max_minutes: minutes }),
    });
    outposts = r.outposts;
    drawOutposts(r, minutes);
    document.getElementById("kpi-coverage").textContent = r.after.coverage_pct_villages + "%";
    document.getElementById("kpi-sched").textContent = r.scheduled_care.coverage_pct_villages + "%";
    toast(`✅ ${fleet} MMU outposts placed · scheduled care ${r.scheduled_care.coverage_pct_villages}% · ` +
          `${(r.scheduled_care.new_population / 1e6).toFixed(1)}M people newly served`);
  } catch (e) { toast("Optimize failed: " + e.message); }
}
function drawOutposts(r, minutes) {
  outpostLayer.clearLayers();
  circuitLayer.clearLayers();
  r.outposts.forEach((o) => {
    L.circle([o.lat, o.lon], {           // Zone 1: 30-min primary (green)
      radius: minutes * 666.7, color: "#22d3a7", weight: 1.4,
      fillColor: "#22d3a7", fillOpacity: 0.12, dashArray: "6 6",
    }).addTo(outpostLayer);
    L.circle([o.lat, o.lon], {           // Zone 2: 60-min secondary (amber)
      radius: minutes * 1333.4, color: "#f39c12", weight: 1,
      fillColor: "#f39c12", fillOpacity: 0.05, dashArray: "3 7",
    }).addTo(outpostLayer);
    const mk = L.marker([o.lat, o.lon], {
      icon: L.divIcon({ className: "outpost-star", html: "★", iconSize: [22, 22], iconAnchor: [11, 11] }),
    });
    mk.bindPopup(
      `<b>${o.outpost_id}</b> · anchor: ${o.anchor_district}<br>` +
      `Staged at: ${o.staged_at ?? "cluster centroid"}<br>` +
      `${o.staged_info ?? ""}<br>` +
      `Circuit: ${fmt(o.circuit_villages)} villages · ${fmt(o.circuit_population)} people<br>` +
      `Mean need: ${o.circuit_mean_need}<br>` +
      `30-min emergency reach: +${o.emergency_new_villages} villages`
    );
    mk.on("click", (e) => { L.DomEvent.stopPropagation(e); if (selectedMode) dispatch({ outpost_id: o.outpost_id, lat: o.lat, lon: o.lon }); });
    mk.addTo(outpostLayer);
    o.circuit_village_ids.forEach((vid) => {
      const v = villagesById.get(vid);
      if (!v) return;
      L.circleMarker([v.Latitude, v.Longitude], {
        radius: 1.6, color: "#22d3a7", weight: 0.5, fillColor: "#22d3a7", fillOpacity: 0.8,
      }).addTo(circuitLayer);
    });
  });
}

/* --------------------------------------------------------------------- SOS */
async function pollSos() {
  try {
    const alerts = await api("/api/sos-alerts?limit=200");
    alerts.forEach((a) => {
      if (!seenSos.has(a.id)) {
        seenSos.add(a.id);
        addSosMarker(a);
      }
    });
    const sig = JSON.stringify(alerts);
    if (sig !== lastFeedSig) { lastFeedSig = sig; renderSosFeed(alerts); }
    document.getElementById("kpi-sos").textContent = alerts.length;
    pendingSync = alerts.filter((a) => a.source === "hub_sync" && a.status === "new").length;
    updateMeshBadge();
  } catch (e) { console.error("pollSos failed:", e); }
}
function renderSosFeed(alerts) {
  const feed = document.getElementById("sos-feed");
  feed.innerHTML = "";
  alerts.slice(0, 12).forEach((a) => {
    const el = document.createElement("div");
    el.className = "sos-item";
    const icon = { trauma: "🩸", maternal: "🤰", medicine: "💊", routine: "🩺",
                   poisoning: "☠️", water_contamination: "💧",
                   suicide_attempt: "🧠", natural_hazard: "⚡" }[a.sos_type] || "🆘";
    el.innerHTML =
      `<div><b>${icon} ${a.sos_type.toUpperCase()}</b> · ${a.priority}` +
      `${a.recommended_mode ? ` → suggest ${a.recommended_mode}` : ""}</div>` +
      `<div class="meta">${a.node_id} · ${a.source} · ${new Date(a.created_at).toLocaleTimeString()}</div>`;
    el.onclick = () => a.lat && map.panTo([a.lat, a.lon]);
    feed.appendChild(el);
  });
}
function addSosMarker(a) {
  if (a.lat == null) return;
  L.marker([a.lat, a.lon], {
    icon: L.divIcon({ className: "sos-pin", html: '<span class="pulse"></span>🆘', iconSize: [26, 26], iconAnchor: [13, 13] }),
  }).addTo(sosLayer);
}

/* ---------------------------------------------------------------- dispatch */
async function dispatch(payload) {
  if (!selectedMode) { toast("Select a dispatch mode first"); return; }
  const body = { mode: selectedMode, ...payload };
  try {
    const job = await api("/api/dispatch", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    renderDispatch(job);
    if (job.handoff) drawUavRoute(job.handoff);
    toast(`Dispatched ${job.mode}${job.eta_min ? " · ETA " + job.eta_min + " min" : ""}`);
  } catch (e) { toast("Dispatch failed: " + e.message); }
}
function renderDispatch(job) {
  const log = document.getElementById("dispatch-log");
  if (log.querySelector(".hint")) log.innerHTML = "";
  const el = document.createElement("div");
  el.className = "dispatch-item";
  el.style.borderLeftColor = MODE_COLORS[job.mode] || "#3b82f6";
  let html = `<b>${job.mode.replace("_", " ").toUpperCase()}</b>${job.eta_min ? " · ETA " + job.eta_min + " min" : ""}` +
             `<div class="meta">${new Date(job.created_at).toLocaleTimeString()} · ${job.status}</div>`;
  if (job.handoff) {
    const h = job.handoff;
    html += `<div class="handoff">🚁 <b>${h.partner}</b><br>` +
      `Pickup: ${h.pickup.name}<br>` +
      `${h.distance_km} km @ ${h.cruise_kmph} km/h · payload ${h.payload_kg} kg<br>` +
      `${h.regulatory}</div>`;
  }
  el.innerHTML = html;
  log.prepend(el);

  const rc = document.getElementById("route-card");
  if (rc) {
    const fast = job.eta_min != null && job.eta_min <= 30;
    rc.style.borderLeftColor = MODE_COLORS[job.mode] || "#3b82f6";
    rc.style.display = "block";
    rc.innerHTML = `<h3>${(job.mode || "").replace("_", " ").toUpperCase()} dispatched</h3>` +
      `<div class="eta ${fast ? "" : "slow"}">${job.eta_min != null ? job.eta_min + " min" : "—"}</div>` +
      `<div class="meta">${fast ? "✅ within 30-min target" : "⚠️ exceeds 30-min target — consider air dispatch"}</div>` +
      (job.pickup_name ? `<div class="meta">From: ${job.pickup_name}</div>` : "");
  }
}
function drawUavRoute(h) {
  dispatchLayer.clearLayers();
  L.polyline([[h.pickup.lat, h.pickup.lon], [h.drop.lat, h.drop.lon]], {
    color: "#3b82f6", weight: 2, dashArray: "8 6",
  }).addTo(dispatchLayer);
  L.circleMarker([h.pickup.lat, h.pickup.lon], {
    radius: 5, color: "#3b82f6", fillColor: "#3b82f6", fillOpacity: 0.9,
  }).bindPopup(`<b>Pickup</b><br>${h.pickup.name}`).addTo(dispatchLayer);
  L.circleMarker([h.drop.lat, h.drop.lon], {
    radius: 5, color: "#e74c3c", fillColor: "#e74c3c", fillOpacity: 0.9,
  }).bindPopup("<b>Drop zone</b><br>UAV payload delivery").addTo(dispatchLayer);
  map.fitBounds([[h.pickup.lat, h.pickup.lon], [h.drop.lat, h.drop.lon]].map((c) => c), { padding: [40, 40] });
}
function onMapClick(e) {
  if (!selectedMode) return;
  dispatch({ lat: +e.latlng.lat.toFixed(4), lon: +e.latlng.lng.toFixed(4) });
}

/* ------------------------------------------------------------ demo triggers */
async function demoSos() {
  const pool = villagesData.filter((v) => v.Underserved_Area_Flag_bin);
  if (!pool.length) return toast("No underserved villages loaded yet");
  const v = pool[Math.floor(Math.random() * pool.length)];
  const types = ["trauma", "maternal", "medicine", "poisoning", "water_contamination", "natural_hazard"];
  const type = types[Math.floor(Math.random() * types.length)];
  const r = await api("/api/sos-alert", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      node_id: "VIL-" + v.Village_ID, village_id: v.Village_ID, sos_type: type,
      priority: type === "medicine" ? "high" : "critical",
      lat: v.Latitude, lon: v.Longitude, source: "demo",
    }),
  });
  toast(`🆘 SOS from ${v.Village_ID} (${v.District}) — ${type}` +
        (r.recommended_mode ? ` → recommend ${r.recommended_mode}` : ""));
  pollSos();
}
async function demoSync() {
  const r = await api("/api/sync", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ alerts: [
      { node_id: "HUB-01", sos_type: "medicine", priority: "high", lat: 25.9, lon: 81.8 },
      { node_id: "HUB-01", sos_type: "trauma", priority: "critical", lat: 24.6, lon: 78.4 },
    ]}),
  });
  toast(`📡 Hub back online — ${r.synced} offline alerts synced`);
  pollSos();
}

/* -------------------------------------------------------------- UI wiring */
function bindControls() {
  document.getElementById("btn-optimize").onclick = runOptimize;
  document.getElementById("btn-demo-sos").onclick = demoSos;
  document.getElementById("btn-demo-sync").onclick = demoSync;
  const sb = document.getElementById("search-box");
  if (sb) sb.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(sb.value); });
  document.getElementById("fleet").oninput = (e) => (document.getElementById("fleet-val").textContent = e.target.value);
  document.getElementById("minutes").oninput = (e) => (document.getElementById("minutes-val").textContent = e.target.value);
  document.getElementById("state-filter").onchange = () => { drawVillages(); loadDistrictBubbles(); };
  document.getElementById("layer-villages").onchange = () => applyLOD();
  document.getElementById("layer-facilities").onchange = () => applyLOD();
  document.getElementById("layer-districts").onchange = (e) => toggle(districtLayer, e.target.checked);
  document.getElementById("layer-outposts").onchange = (e) => { toggle(outpostLayer, e.target.checked); toggle(circuitLayer, e.target.checked); };
}
function toggle(layer, on) { on ? layer.addTo(map) : map.removeLayer(layer); }

document.addEventListener("DOMContentLoaded", init);
