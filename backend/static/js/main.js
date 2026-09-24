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
let drawLayer = null, activeRegion = null;
let supplyLayer, supplyData = null, supplyAir = false, lastOutpost = null;

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
  supplyLayer   = L.layerGroup().addTo(map);
  districtBubbleLayer = L.layerGroup().addTo(map);

  map.on("click", onMapClick);
  map.on("zoomend moveend", scheduleLOD);

  if (map.pm) {
    map.pm.addControls({
      position: "topleft",
      drawMarker: false, drawCircleMarker: false, drawPolyline: false, drawText: false,
      editMode: false, dragMode: false, cutPolygon: false, rotateMode: false,
      drawRectangle: true, drawPolygon: true, drawCircle: true, removalMode: true,
    });
    map.pm.setGlobalOptions({ allowSelfIntersection: false,
                              templineStyle: { color: "#22d3a7" },
                              hintlineStyle: { color: "#22d3a7", dashArray: "5 5" } });
    map.on("pm:create", onShapeCreated);
    map.on("pm:remove", onShapeRemoved);
  }

  loadVillages();
  loadFacilities();
  loadDistricts();
  loadDistrictBubbles();
  loadModes();
  bindControls();
  setInterval(pollSos, 5000);
  pollSos();
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

/* --------------------------------------------------------------- villages */
async function loadVillages() {
  try {
    villagesData = await api("/api/villages");
    villagesData.forEach((v) => villagesById.set(v.Village_ID, v));
    drawVillages();
    populateVillageSelect();
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
        `Need score: ${v.need_score}${v.Underserved_Area_Flag_bin ? " · <b>UNDERSERVED</b>" : ""}` +
        `<button class="popup-btn" onclick="dispatchTo(${v.Latitude}, ${v.Longitude}, '${v.Road_Connectivity}', '${v.Healthcare_Risk_Level}')">🚑 Send emergency services</button>`
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
        `${f.has_ambulance ? "<br>🚑 Ambulance" : ""}` +
        `<button class="popup-btn" onclick="dispatchTo(${f.lat}, ${f.lon})">🚑 Send emergency services</button>`);
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
        radius: Math.min(16, 6 + Math.sqrt(d.underserved || 0) * 0.8),
        color: col, weight: 1, fillColor: col, fillOpacity: 0.55,
      });
      c.bindTooltip(`${d.District}`, { sticky: true });
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

/* ------------------------------------------------ area selection + intel */
function onShapeRemoved() {
  drawLayer = null; activeRegion = null;
  document.getElementById("area-stats").style.display = "none";
  enableOptimize(false);
}

function enableOptimize(on) {
  const btn = document.getElementById("btn-optimize");
  const hint = document.getElementById("optimize-hint");
  if (!btn) return;
  btn.disabled = !on;
  btn.style.opacity = on ? "1" : "0.5";
  btn.style.cursor = on ? "pointer" : "not-allowed";
  if (hint) {
    hint.textContent = on
      ? "✅ Area selected — adjust the sliders, then click Optimize"
      : "⚠️ Draw an area on the map first (use the rectangle, circle, or polygon tool)";
    hint.style.color = on ? "var(--accent)" : "var(--amber)";
  }
}

function onShapeCreated(e) {
  if (drawLayer) map.removeLayer(drawLayer);
  drawLayer = e.layer;
  drawLayer.addTo(map);
  const gj = drawLayer.toGeoJSON();
  let region, areaKm2;
  if (e.shape === "Circle") {
    const c = drawLayer.getLatLng();
    const rKm = drawLayer.getRadius() / 1000;
    region = { type: "circle", lat: c.lat, lon: c.lng, radius_km: rKm };
    areaKm2 = Math.PI * rKm * rKm;
  } else {
    const coords = gj.geometry.coordinates[0].map((p) => [p[0], p[1]]);
    region = { type: "polygon", coordinates: coords };
    areaKm2 = polygonAreaKm2(coords);
  }
  activeRegion = region;
  showAreaStats(region, areaKm2);
  enableOptimize(true);
}

function polygonAreaKm2(coords) {
  const latMean = coords.reduce((s, p) => s + p[1], 0) / coords.length;
  const kx = 111.32 * Math.cos(latMean * Math.PI / 180), ky = 110.57;
  let a = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    a += (coords[i][0] * kx) * (coords[i + 1][1] * ky) -
         (coords[i + 1][0] * kx) * (coords[i][1] * ky);
  }
  return Math.abs(a / 2);
}

function pointInRegion(lat, lon, region) {
  if (region.type === "circle") {
    const R = 6371, toR = Math.PI / 180;
    const dLat = (lat - region.lat) * toR, dLon = (lon - region.lon) * toR;
    const h = Math.sin(dLat / 2) ** 2 +
      Math.cos(region.lat * toR) * Math.cos(lat * toR) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h)) <= region.radius_km;
  }
  const ring = region.coordinates;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function showAreaStats(region, areaKm2) {
  const inV = villagesData.filter((v) => pointInRegion(v.Latitude, v.Longitude, region));
  const pop = inV.reduce((s, v) => s + v.Population, 0);
  const under = inV.filter((v) => v.Underserved_Area_Flag_bin).length;
  const fac = facilitiesData.filter((f) => pointInRegion(f.lat, f.lon, region));
  let clat, clon;
  if (region.type === "circle") { clat = region.lat; clon = region.lon; }
  else {
    const ring = region.coordinates;
    clat = ring.reduce((s, p) => s + p[1], 0) / ring.length;
    clon = ring.reduce((s, p) => s + p[0], 0) / ring.length;
  }
  const near = facilitiesData
    .map((f) => ({ f, d: haversineJS(clat, clon, f.lat, f.lon) }))
    .sort((a, b) => a.d - b.d).slice(0, 3);
  const el = document.getElementById("area-stats");
  el.style.display = "block";
  el.innerHTML =
    `<div class="row">` +
    `<div class="stat"><div class="v">${fmt(Math.round(areaKm2))}</div><div class="l">km²</div></div>` +
    `<div class="stat"><div class="v">${fmt(pop)}</div><div class="l">population</div></div>` +
    `<div class="stat"><div class="v">${fmt(inV.length)}</div><div class="l">villages</div></div>` +
    `<div class="stat"><div class="v">${fmt(under)}</div><div class="l">underserved</div></div>` +
    `<div class="stat"><div class="v">${fmt(fac.length)}</div><div class="l">facilities</div></div>` +
    `</div>` +
    `<div class="meta" style="margin-top:6px">Nearby: ${near.map((n) => `${n.f.Hospital_Name} (${n.d.toFixed(0)} km)`).join(" · ")}</div>` +
    `<div class="meta" style="margin-top:4px">Adjust fleet size & travel time in the sidebar → click ⚡ Optimize</div>`;
}

function haversineJS(lat1, lon1, lat2, lon2) {
  const R = 6371, toR = Math.PI / 180;
  const dLat = (lat2 - lat1) * toR, dLon = (lon2 - lon1) * toR;
  const h = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * toR) * Math.cos(lat2 * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

async function optimizeRegion() {
  if (!activeRegion) return toast("Draw an area first");
  toast("Optimizing within the drawn region…");
  const fleet = +document.getElementById("fleet").value;
  const minutes = +document.getElementById("minutes").value;
  try {
    const r = await api("/api/optimize", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fleet_size: fleet, max_minutes: minutes, region: activeRegion }),
    });
    outposts = r.outposts;
    drawOutposts(r, minutes);
    toast(`✅ ${r.outposts.length} MMUs staged in region · scheduled care ${r.scheduled_care.coverage_pct_villages}% · ${r.scheduled_care.new_population / 1e6 > 1 ? (r.scheduled_care.new_population / 1e6).toFixed(1) + "M" : fmt(r.scheduled_care.new_population)} people`);
  } catch (e) { toast("Region optimize failed: " + e.message); }
}

function clearRegion() {
  if (drawLayer) { map.removeLayer(drawLayer); drawLayer = null; }
  activeRegion = null;
  document.getElementById("area-stats").style.display = "none";
  enableOptimize(false);
}

async function loadIntel(o) {
  lastOutpost = o;
  try {
    const r = await api("/api/outpost-intel", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ district: o.anchor_district, outpost_id: o.outpost_id }),
    });
    renderIntel(o, r);
  } catch (e) { toast("Intel failed: " + e.message); }
  // Supply route: from the supply hub (hospital) to the MMU camp
  if (o.supply_hub) {
    try {
      const s = await api("/api/supply-route", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat: o.lat, lon: o.lon }),
      });
      supplyData = s; supplyAir = false;
      renderSupplyRoute();
    } catch (e) { console.error("supply route failed:", e); }
  }
}

function renderSupplyRoute() {
  supplyLayer.clearLayers();
  const s = supplyData;
  if (!s || !lastOutpost) return;
  const opt = supplyAir ? s.air : s.land;
  const color = supplyAir ? "#3b82f6" : "#f39c12";
  L.polyline([[s.source.lat, s.source.lon], [lastOutpost.lat, lastOutpost.lon]],
    { color, weight: 2.5, dashArray: supplyAir ? "8 6" : undefined })
    .addTo(supplyLayer)
    .bindPopup(`<b>${supplyAir ? "🛩 Air" : "🚚 Land"} resupply</b> · ${lastOutpost.outpost_id}<br>` +
      `From: ${s.source.name}<br>` +
      `${s.distance_km} km · ETA ${opt.eta_min} min @ ${opt.speed_kmph} km/h<br>` +
      `<button class="popup-btn" onclick="toggleSupplyMode()">Switch to ${supplyAir ? "🚚 land" : "🛩 air"}</button>`);
  L.circleMarker([s.source.lat, s.source.lon], {
    radius: 5, color: "#f39c12", fillColor: "#f39c12", fillOpacity: 0.9,
  }).addTo(supplyLayer)
    .bindPopup(`<b>Supply source</b><br>${s.source.name}<br>${s.source.beds} beds · ${s.source.doctors} doctors`);
}

function toggleSupplyMode() { supplyAir = !supplyAir; renderSupplyRoute(); }

function renderIntel(o, r) {
  const p = document.getElementById("intel-panel");
  if (!p) return;
  let html = `<div class="meta"><b>${o.outpost_id}</b> · ${r.district}, ${r.state}</div>`;
  if (r.diseases && r.diseases.length) {
    html += `<div style="margin-top:6px"><b>🦠 Health risks in this area (${r.survey})</b></div>`;
    r.diseases.forEach((d) => { html += `<div class="meta">• ${d.indicator}: <b>${d.value}%</b></div>`; });
  }
  html += `<div style="margin-top:8px"><b>💊 Medicine stock</b> <span class="meta">(simulated)</span></div>` +
          `<table><tr><th>Medicine</th><th>Status</th></tr>`;
  r.stock.forEach((s) => {
    const cls = s.status === "Available" ? "stock-ok" : s.status === "Low" ? "stock-low" : "stock-out";
    html += `<tr><td>${s.medicine}</td><td class="${cls}">${s.status}</td></tr>`;
  });
  html += `</table>`;
  if (r.sourcing && r.sourcing.length) {
    html += `<div style="margin-top:6px"><b>🚚 Restock from</b></div>`;
    r.sourcing.forEach((s) => { html += `<div class="meta">• ${s.medicine} → ${s.from} (${s.note})</div>`; });
  }
  if (o.supply_hub) {
    html += `<div style="margin-top:6px"><b>📦 Supply hub</b></div>` +
            `<div class="meta">${o.supply_hub} · ${o.supply_distance_km} km · ${o.supply_info}</div>`;
  }
  p.innerHTML = html;
  p.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
    toast(`✅ ${fleet} MMU outposts placed · scheduled care ${r.scheduled_care.coverage_pct_villages}% · ` +
          `${(r.scheduled_care.new_population / 1e6).toFixed(1)}M people newly served`);
  } catch (e) { toast("Optimize failed: " + e.message); }
}
function drawOutposts(r, minutes) {
  outpostLayer.clearLayers();
  circuitLayer.clearLayers();
  r.outposts.forEach((o) => {
    // Zone 1: 30-min primary (green, more visible)
    L.circle([o.lat, o.lon], {
      radius: minutes * 666.7, color: "#22d3a7", weight: 2,
      fillColor: "#22d3a7", fillOpacity: 0.15, dashArray: "6 6",
    }).addTo(outpostLayer).bindTooltip(`${minutes}-min reach zone`, { sticky: true });
    // Zone 2: 60-min secondary (amber)
    L.circle([o.lat, o.lon], {
      radius: minutes * 1333.4, color: "#f39c12", weight: 1.5,
      fillColor: "#f39c12", fillOpacity: 0.06, dashArray: "3 7",
    }).addTo(outpostLayer).bindTooltip(`${minutes * 2}-min extended zone`, { sticky: true });

    // Hub-and-spoke: lines from outpost to each circuit village
    o.circuit_village_ids.forEach((vid) => {
      const v = villagesById.get(vid);
      if (!v) return;
      L.polyline([[o.lat, o.lon], [v.Latitude, v.Longitude]], {
        color: "#22d3a7", weight: 0.6, opacity: 0.3, dashArray: "2 4",
      }).addTo(circuitLayer);
      L.circleMarker([v.Latitude, v.Longitude], {
        radius: 2, color: "#22d3a7", weight: 0.5, fillColor: "#22d3a7", fillOpacity: 0.7,
      }).addTo(circuitLayer);
    });

    // Outpost marker with permanent label
    const mk = L.marker([o.lat, o.lon], {
      icon: L.divIcon({ className: "outpost-star", html: "★", iconSize: [28, 28], iconAnchor: [14, 14] }),
    });
    mk.bindTooltip(`<b>${o.outpost_id}</b> · Mobile Clinic`, { permanent: true, direction: "top", offset: [0, -14] });
    const opIdx = r.outposts.indexOf(o);
    mk.bindPopup(
      `<div style="min-width:280px">` +
      `<b style="font-size:14px;color:#22d3a7">⛺ ${o.outpost_id} — Mobile Clinic Camp</b><br>` +
      `<span style="font-size:10px;color:#8ea0c0">Population-weighted center of underserved villages</span><hr>` +
      `<b>Serves ${fmt(o.circuit_villages)} villages</b> (${fmt(o.circuit_population)} people)<br>` +
      `📍 Avg distance to villages: <b>${o.avg_distance_km ?? "—"} km</b><br>` +
      `📍 Farthest village: <b>${o.max_distance_km ?? "—"} km</b><br>` +
      `⏱️ Villages within 30-min reach: <b>${o.villages_within_30min ?? "—"}</b><br>` +
      `🏥 Anchor district: ${o.anchor_district}<br>` +
      `📊 Health need score: ${o.circuit_mean_need}<hr>` +
      `<b style="font-size:11px">📦 Supply hub: ${o.supply_hub ?? "—"}</b><br>` +
      `<span style="font-size:10px;color:#8ea0c0">${o.supply_info ?? ""} · ${o.supply_distance_km ?? "—"} km away</span><hr>` +
      `<button class="popup-btn" onclick="loadIntel(outposts[${opIdx}])">🧪 Health risks, medicines & supply routes</button>` +
      `</div>`
    );
    mk.on("click", (e) => {
      L.DomEvent.stopPropagation(e);
      if (selectedMode) dispatch({ outpost_id: o.outpost_id, lat: o.lat, lon: o.lon });
      else loadIntel(o);
    });
    mk.addTo(outpostLayer);
  });

  // Coverage summary card — THE HERO ELEMENT with per-clinic breakdown
  const sc = document.getElementById("coverage-summary");
  if (sc && r.outposts.length) {
    const totalV = r.outposts.reduce((s, o) => s + o.circuit_villages, 0);
    const totalP = r.outposts.reduce((s, o) => s + o.circuit_population, 0);
    const avgD = r.outposts.reduce((s, o) => s + (o.avg_distance_km || 0), 0) / r.outposts.length;
    const areaV = villagesData.filter((v) => activeRegion && pointInRegion(v.Latitude, v.Longitude, activeRegion));
    const areaUnder = areaV.filter((v) => v.Underserved_Area_Flag_bin).length;
    const covered = r.outposts.reduce((s, o) => s + o.circuit_villages, 0);
    const stillOut = areaV.length - covered;

    let clinicRows = r.outposts.map((o) =>
      `<tr><td><b>${o.outpost_id}</b></td>` +
      `<td>${(o.supply_hub ?? "—").substring(0, 20)}</td>` +
      `<td style="text-align:center">${o.circuit_villages}</td>` +
      `<td style="text-align:center">${o.circuit_population > 1e6 ? (o.circuit_population / 1e6).toFixed(1) + "M" : fmt(o.circuit_population)}</td>` +
      `<td style="text-align:center">${o.avg_distance_km ?? "—"}km</td>` +
      `<td style="text-align:center">${o.max_distance_km ?? "—"}km</td></tr>`
    ).join("");

    sc.style.display = "block";
    sc.innerHTML = `<h3>✅ ${r.outposts.length} Mobile Clinic${r.outposts.length > 1 ? "s" : ""} Deployed</h3>` +
      `<div class="stat-row">` +
      `<div class="stat"><div class="v">${fmt(covered)}</div><div class="l">villages served</div></div>` +
      `<div class="stat"><div class="v">${totalP > 1e6 ? (totalP / 1e6).toFixed(1) + "M" : fmt(totalP)}</div><div class="l">people covered</div></div>` +
      `<div class="stat"><div class="v">${r.scheduled_care.coverage_pct_villages}%</div><div class="l">coverage</div></div>` +
      `</div>` +
      `<div class="stat-row">` +
      `<div class="stat"><div class="v">${r.baseline.coverage_pct_villages}%</div><div class="l">before</div></div>` +
      `<div class="stat"><div class="v">→</div><div class="l"></div></div>` +
      `<div class="stat"><div class="v">${r.scheduled_care.coverage_pct_villages}%</div><div class="l">after</div></div>` +
      `<div class="stat"><div class="v">${avgD.toFixed(0)}km</div><div class="l">avg dist</div></div>` +
      `</div>` +
      `<table style="width:100%;border-collapse:collapse;font-size:10px;margin-top:10px">` +
      `<tr style="color:var(--muted)"><th>Clinic</th><th>Supply hub</th><th>Villages</th><th>People</th><th>Avg km</th><th>Max km</th></tr>` +
      clinicRows + `</table>` +
      `<div class="meta" style="margin-top:8px">Area: ${areaV.length} villages · ${areaUnder} underserved · ${stillOut > 0 ? stillOut + " still uncovered" : "fully covered!"}</div>` +
      `<div class="meta">Click any ⭐ for medical intel · supply routes · medicine stock</div>`;
  }
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
  }).addTo(sosLayer)
   .bindPopup(`<b>🆘 ${a.sos_type.toUpperCase()}</b> · ${a.priority}<br>${a.node_id}` +
     `${a.recommended_mode ? `<br>Suggested: ${a.recommended_mode}` : ""}` +
     `<button class="popup-btn" onclick="dispatchTo(${a.lat}, ${a.lon})">🚑 Send emergency services</button>`);
}

/* ---------------------------------------------------------------- dispatch */
async function dispatch(payload, modeOverride) {
  const mode = modeOverride || selectedMode;
  if (!mode) { toast("Select a dispatch mode first"); return; }
  const body = { ...payload, mode };
  try {
    const job = await api("/api/dispatch", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    renderDispatch(job);
    if (job.handoff) drawUavRoute(job.handoff);
    else if (job.pickup_lat != null) drawGroundRoute(job);
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
      `<div class="meta">${job.eta_min == null ? "⛺ staged asset — no transit ETA" : fast ? "✅ within 30-min target" : "⚠️ exceeds 30-min target — consider air dispatch"}</div>` +
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

function drawGroundRoute(job) {
  dispatchLayer.clearLayers();
  const col = MODE_COLORS[job.mode] || "#3b82f6";
  const isAir = job.mode === "helicopter";
  L.polyline([[job.pickup_lat, job.pickup_lon], [job.lat, job.lon]], {
    color: col, weight: 3, dashArray: isAir ? "8 6" : undefined,
    opacity: 0.8,
  }).addTo(dispatchLayer)
    .bindPopup(`<b>${job.mode.replace("_", " ").toUpperCase()} route</b><br>` +
      `From: ${job.pickup_name}<br>ETA: ${job.eta_min} min`);
  L.circleMarker([job.pickup_lat, job.pickup_lon], {
    radius: 5, color: col, fillColor: col, fillOpacity: 0.9,
  }).bindPopup(`<b>Dispatch from</b><br>${job.pickup_name}`).addTo(dispatchLayer);
  L.circleMarker([job.lat, job.lon], {
    radius: 6, color: "#e74c3c", fillColor: "#e74c3c", fillOpacity: 0.9,
  }).bindPopup(`<b>Emergency location</b><br>${job.mode.replace("_", " ")} dispatched`).addTo(dispatchLayer);
  map.fitBounds([[job.pickup_lat, job.pickup_lon], [job.lat, job.lon]], { padding: [40, 40] });
}
function onMapClick(e) {
  if (!selectedMode) return;
  dispatch({ lat: +e.latlng.lat.toFixed(4), lon: +e.latlng.lng.toFixed(4) });
}

/* ------------------------------------- one-tap emergency from any node */
function autoMode(road, risk) {
  if (road === "Poor" && risk === "High") return "uav";
  if (road === "Poor") return "rider_2w";
  return "ambulance";
}

async function dispatchTo(lat, lon, road, risk) {
  const mode = selectedMode || autoMode(road || "Good", risk || "Low");
  if (!selectedMode) toast(`No mode armed — auto-selecting ${mode}`);
  dispatch({ lat: +lat, lon: +lon }, mode);
}

/* ------------------------------------------------------- SOS form */
function populateVillageSelect() {
  const sel = document.getElementById("sos-village");
  if (!sel || !villagesData.length) return;
  const under = villagesData.filter((v) => v.Underserved_Area_Flag_bin);
  under.slice(0, 200).forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v.Village_ID;
    opt.textContent = `${v.Village_ID} · ${v.District} (${fmt(v.Population)})`;
    sel.appendChild(opt);
  });
}

async function submitSosForm() {
  const type = document.getElementById("sos-type").value;
  const priority = document.getElementById("sos-priority").value;
  const villageId = document.getElementById("sos-village").value;
  let lat = null, lon = null, vid = villageId || null;

  if (!villageId) {
    const pool = villagesData.filter((v) => v.Underserved_Area_Flag_bin);
    if (!pool.length) return toast("No villages loaded yet");
    const v = pool[Math.floor(Math.random() * pool.length)];
    lat = v.Latitude; lon = v.Longitude; vid = v.Village_ID;
  } else {
    const v = villagesById.get(villageId);
    if (v) { lat = v.Latitude; lon = v.Longitude; }
  }

  try {
    const r = await api("/api/sos-alert", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: "CONSOLE-OPS", village_id: vid, sos_type: type,
        priority, lat, lon, source: "console",
      }),
    });
    toast(`🆘 SOS submitted — ${type}${r.recommended_mode ? ` → suggest ${r.recommended_mode}` : ""}`);
    pollSos();
  } catch (e) { toast("SOS failed: " + e.message); }
}

/* -------------------------------------------------------------- UI wiring */
function bindControls() {
  document.getElementById("btn-optimize").onclick = () => {
    if (!activeRegion) { toast("⚠️ Draw an area on the map first"); return; }
    optimizeRegion();
  };
  document.getElementById("btn-sos").onclick = submitSosForm;
  populateVillageSelect();
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
