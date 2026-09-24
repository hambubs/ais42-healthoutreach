"""
AIS-42 HealthOutreach — Impact Dashboard
Streamlit + Folium + Plotly analytics showcase for PS-4B
(Team AIS-42, AI for Sustainability Hackathon 2026).

Run:
    .venv\\Scripts\\python -m streamlit run dashboard/app.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import optimizer  # noqa: E402

CLEAN = Path(__file__).resolve().parents[1] / "backend" / "data" / "clean"
RISK_COLORS = {"Low": "#2ecc71", "Medium": "#f39c12", "High": "#e74c3c"}
ESRI_DARK = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
             "Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}")

st.set_page_config(page_title="AIS-42 HealthOutreach", page_icon="🏥", layout="wide")


# ---------------------------------------------------------------- data load
@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(CLEAN / name)


@st.cache_data
def load_geojson() -> dict:
    return json.loads((CLEAN / "enrichment" / "districts.geojson").read_text(encoding="utf-8"))


villages = load_csv("villages_clean.csv")
districts = load_csv("district_summary.csv")
dhs = load_csv("enrichment/dhs_state_indicators.csv")
heigit = load_csv("enrichment/heigit_state_access.csv")
baseline = optimizer.baseline_stats()

# ------------------------------------------------------------------- header
st.title("🏥 AIS-42 HealthOutreach — Impact Dashboard")
st.caption("PS-4B Rural Healthcare Reachability & Outpost Planning · SDG 3 Good Health & Well-Being · SDG 10 Reduced Inequalities")

k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)
k1.metric("30-min coverage today", f"{baseline['coverage_pct_villages']}%")
k2.metric("Avg travel to care", f"{baseline['avg_travel_min']} min")
k3.metric("Underserved villages", f"{baseline['underserved_villages']:,}")
k4.metric("High-risk villages", f"{baseline['high_risk_villages']:,}")
k5.metric("Poor-road villages", f"{baseline['poor_road_villages']:,}")
k6.metric("Avg distance to care", f"{baseline['avg_distance_km']} km")

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Optimization")
    fleet_size = st.slider("Fleet size (MMUs)", 1, 12, 3)
    max_minutes = st.slider("Max travel (minutes)", 15, 60, 30, step=5)
    run = st.button("🚀 Run Optimization", type="primary")
    st.divider()
    states = st.multiselect(
        "Map filter — states",
        sorted(villages["State"].unique()),
        default=sorted(villages["State"].unique()),
    )

result = None
if run:
    with st.spinner("Running DBSCAN clustering + greedy MCLP…"):
        result = optimizer.optimize(fleet_size=fleet_size, max_minutes=max_minutes)

if result:
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "30-min emergency coverage",
        f"{result['after']['coverage_pct_villages']}%",
        delta=f"{result['after']['coverage_pct_villages'] - result['baseline']['coverage_pct_villages']:+.2f} pp",
    )
    c2.metric(
        "Scheduled MMU care coverage",
        f"{result['scheduled_care']['coverage_pct_villages']}%",
        delta=f"{result['scheduled_care']['coverage_pct_villages'] - result['baseline']['coverage_pct_villages']:+.2f} pp",
    )
    c3.metric("People newly served", f"{result['scheduled_care']['new_population'] / 1e6:.1f}M")
    st.caption(
        f"Clustering: **{result['clustering_method']}** · {result['candidates_considered']} candidate circuits · "
        f"{result['noise_villages']:,} hyper-remote villages flagged for **UAV-only outreach**"
    )

# ============================================================ TABS
tab1, tab2, tab3 = st.tabs([
    "🗺️ Impact & Analytics",
    "🛰️ WorldPop BLR Pilot",
    "🇮🇳 DHS Live",
])

# -------------------------------------------------------- TAB 1: Impact
with tab1:
    vf = villages[villages["State"].isin(states)] if states else villages
    m = folium.Map(location=[22.8, 80.5], zoom_start=5, tiles=ESRI_DARK, attr="Esri")
    folium.GeoJson(
        load_geojson(),
        style_function=lambda f: {"color": "#3b82f6", "weight": 1, "opacity": 0.5,
                                  "dashArray": "4 4", "fill": False},
    ).add_to(m)
    for lat, lon, risk in zip(vf["Latitude"], vf["Longitude"], vf["Healthcare_Risk_Level"]):
        folium.CircleMarker(
            [lat, lon], radius=1.2, weight=0,
            color=RISK_COLORS.get(risk, "#888"), fill=True, fill_opacity=0.6,
        ).add_to(m)
    if result:
        for o in result["outposts"]:
            folium.Circle([o["lat"], o["lon"]], radius=20000, color="#22d3a7",
                          weight=1.5, dashArray="6 6", fill=False).add_to(m)
            folium.Marker(
                [o["lat"], o["lon"]], icon=folium.Icon(color="green", icon="star"),
                popup=folium.Popup(
                    f"<b>{o['outpost_id']}</b> · {o['anchor_district']}<br>"
                    f"Staged at: {o.get('staged_at', '—')}<br>"
                    f"Circuit: {o['circuit_villages']:,} villages · {o['circuit_population']:,} people<br>"
                    f"Mean need: {o['circuit_mean_need']}",
                    max_width=280,
                ),
            ).add_to(m)
    components.html(m._repr_html_(), height=560, scrolling=False)

    left, right = st.columns(2)
    with left:
        st.subheader("Coverage: before vs after")
        if result:
            fig = go.Figure()
            fig.add_bar(name="Before", x=["30-min emergency", "Scheduled MMU care"],
                        y=[result["baseline"]["coverage_pct_villages"],
                           result["baseline"]["coverage_pct_villages"]], marker_color="#8ea0c0")
            fig.add_bar(name="After", x=["30-min emergency", "Scheduled MMU care"],
                        y=[result["after"]["coverage_pct_villages"],
                           result["scheduled_care"]["coverage_pct_villages"]], marker_color="#22d3a7")
            fig.update_layout(template="plotly_dark", yaxis_title="% of villages covered",
                              barmode="group", height=340, margin=dict(t=30, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Run the optimization to see the before/after impact.")
        st.subheader("Top-10 districts by underserved villages")
        top = districts.nlargest(10, "underserved")
        fig2 = px.bar(top, x="underserved", y="District", orientation="h", color="mean_need",
                      color_continuous_scale="Viridis", labels={"underserved": "underserved villages"})
        fig2.update_layout(template="plotly_dark", height=380, margin=dict(t=10, l=10, r=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    with right:
        st.subheader("DHS / NFHS indicator explorer")
        pct = dhs.groupby("indicator")["value"].max()
        indicators = sorted(pct[pct <= 100].index)
        ind = st.selectbox("Indicator", indicators, index=0)
        st.caption("Percentage-type indicators only (values ≤ 100).")
        dd = dhs[dhs["indicator"] == ind].sort_values("value")
        if not dd.empty:
            fig3 = px.bar(dd, x="state", y="value", color="value", color_continuous_scale="Reds",
                          labels={"value": "% prevalence"}, title=f"{ind} ({dd['survey'].iloc[0]})")
            fig3.update_layout(template="plotly_dark", height=340, margin=dict(t=60, l=10, r=10, b=90))
            fig3.update_xaxes(tickangle=-45)
            st.plotly_chart(fig3, use_container_width=True)
        st.subheader("Validation: our 30-min coverage vs HeiGIT/WorldPop")
        ours = (villages.assign(ok=villages["Average_Travel_Time_min"] <= 30)
                .groupby("State")["ok"].mean().mul(100).round(2)
                .rename("Our dataset (villages ≤30 min)"))
        hg = (heigit[heigit["category"] == "hospitals"]
              .set_index("state")["within_30min_pop_share_pct"]
              .rename("HeiGIT (pop. within 30 min)"))
        cmp = pd.concat([ours, hg], axis=1).dropna().reset_index(names="State")
        fig4 = px.bar(cmp, x="State", y=["Our dataset (villages ≤30 min)", "HeiGIT (pop. within 30 min)"],
                      barmode="group", labels={"value": "% within 30 min"})
        fig4.update_layout(template="plotly_dark", height=340, margin=dict(t=10, l=10, r=10, b=90))
        fig4.update_xaxes(tickangle=-45)
        st.plotly_chart(fig4, use_container_width=True)
    if result:
        st.subheader("Recommended MMU outposts")
        st.dataframe(pd.DataFrame([{
            "outpost": o["outpost_id"], "anchor district": o["anchor_district"],
            "staged at": o.get("staged_at", "—"),
            "circuit villages": o["circuit_villages"], "circuit population": f"{o['circuit_population']:,}",
            "30-min emergency gain": o["emergency_new_villages"],
        } for o in result["outposts"]]), use_container_width=True)
    st.divider()
    st.markdown("**Dispatch modes** — " + " · ".join(
        f"{m['icon']} **{m['label']}** ({m['trigger']})" for m in optimizer.DISPATCH_MODES.values()))


# ------------------------------------------------ TAB 2: WorldPop BLR pilot
@st.cache_data
def load_worldpop():
    cells_p = CLEAN / "enrichment" / "worldpop" / "blr_pop_cells.json"
    meta_p  = CLEAN / "enrichment" / "worldpop" / "blr_pop_meta.json"
    if not cells_p.exists():
        return None, None
    return json.loads(cells_p.read_text()), json.loads(meta_p.read_text())

with tab2:
    wp_cells, wp_meta = load_worldpop()
    if wp_cells is None:
        st.error("WorldPop data not found — run `python scripts/fetch_worldpop.py`")
    else:
        bbox = wp_meta["bbox"]
        mid = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]
        m2 = folium.Map(location=mid, zoom_start=8, tiles=ESRI_DARK, attr="Esri")
        folium.GeoJson(
            load_geojson(),
            style_function=lambda f: {"color": "#3b82f6", "weight": 1, "opacity": 0.5,
                                      "dashArray": "4 4", "fill": False},
        ).add_to(m2)
        # facilities from the 4 pilot districts (Karnataka)
        fac_pilot = load_csv("facilities_clean.csv")
        fac_pilot = fac_pilot[fac_pilot["District"].isin(
            ["Bengaluru Rural", "Bengaluru Urban", "Ramanagara", "Kolar", "Tumakuru", "Tumkur", "Bangalore Rural"])]
        for _, r in fac_pilot.iterrows():
            folium.CircleMarker([r["lat"], r["lon"]], radius=2.4, color="#3b82f6",
                                weight=1, fillColor="#3b82f6", fillOpacity=0.7).add_to(m2)
        # WorldPop heat
        from folium.plugins import HeatMap
        HeatMap([(c[0], c[1], c[2]) for c in wp_cells],
                radius=18, blur=22, min_opacity=0.3,
                gradient={0.2: "#3b82f6", 0.5: "#22d3a7", 0.8: "#f39c12", 1.0: "#e74c3c"}).add_to(m2)
        components.html(m2._repr_html_(), height=520, scrolling=False)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pilot population", f"{wp_meta['total_population_in_bbox']:,}")
        c2.metric("WorldPop resolution", wp_meta["worldpop_resolution"])
        c3.metric("Heat cells", f"{wp_meta['cells']:,}")
        c4.metric("Pilot districts", ", ".join(wp_meta["pilot_districts"][:2]) + "…")
        st.caption(
            f"Source: {wp_meta['source']} · License: {wp_meta['license']} · "
            f"BBox {bbox} · Aggregation {wp_meta['cell_size_deg']}° (~1.1 km). "
            f"Fetched via `scripts/fetch_worldpop.py` (100m /vsicurl primary → 17 MB 1km fallback). "
            f"Facilities (blue dots): 10,672 coordinate-mapped facilities from the 30,273-row "
            f"government hospital directory, filtered to the BLR pilot districts."
        )


# ----------------------------------------- TAB 3: DHS Live + STATcompiler
@st.cache_data(ttl=3600)
def fetch_dhs_live(indicator_id: str):
    """Live query to the DHS Program API. Verified keyless (no token needed)."""
    import requests
    url = (f"https://api.dhsprogram.com/rest/dhs/data"
           f"?countryIds=IA&indicatorIds={indicator_id}&limit=20")
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return r.json()

# Curated indicator IDs verified to return clean JSON from the DHS API
DHS_INDICATORS = {
    "CN_ANMC_C_ANY": "Children with any anemia (under 5)",
    "RH_ANCP_W_DOC": "Antenatal care from a doctor",
    "FE_FRTR_W_TFR": "Total fertility rate",
    "ML_FEVT_C_DPT": "DPT immunization coverage",
    "WS_SRCE_PHN":   "Households with access to an improved drinking water source",
    "NU_HH_W_ANH":   "Households using clean cooking fuel",
}

with tab3:
    label = st.selectbox("Indicator (live from api.dhsprogram.com)",
                        list(DHS_INDICATORS.values()),
                        index=0, key="dhs_pick")
    ind_id = [k for k, v in DHS_INDICATORS.items() if v == label][0]

    dhs_local = pd.DataFrame()  # populated only if live fetch fails
    live_data = None
    source_used = "fallback"
    try:
        live_data = fetch_dhs_live(ind_id)
        source_used = "live"
    except Exception as exc:  # noqa: BLE001
        st.caption(f"⚠️ Live API unavailable ({exc}); falling back to local DHS CSV.")
        # fallback: local dhs_state_indicators
        FALLBACK_KEYS = {
            "Children with any anemia (under 5)": "anemia",
            "Antenatal care from a doctor": "Antenatal",
            "Total fertility rate": "fertility",
            "DPT immunization coverage": "immunization",
            "Households with access to an improved drinking water source": "drinking water",
            "Households using clean cooking fuel": "cooking",
        }
        key = FALLBACK_KEYS.get(label, label.split(" ")[0])
        dhs_local = dhs[dhs["indicator"].str.contains(key, case=False, na=False)]
        if not dhs_local.empty:
            latest = dhs_local["survey"].max()
            dhs_local = dhs_local[dhs_local["survey"] == latest]

    if source_used == "live" and live_data and live_data.get("Data"):
        rows = live_data["Data"]
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        st.caption(f"🟢 **Live from api.dhsprogram.com** · fetched {ts} · {len(rows)} records")
        df_live = pd.DataFrame(rows)
        fig_live = px.bar(df_live, x="SurveyYearLabel", y="Value",
                          color="SurveyYearLabel", text="Value",
                          labels={"SurveyYearLabel": "Survey year", "Value": "Indicator value"},
                          title=f"India — {label} (across DHS survey rounds)")
        fig_live.update_traces(texttemplate="%{text}", textposition="outside")
        fig_live.update_layout(template="plotly_dark", showlegend=False, height=380,
                               margin=dict(t=60, l=10, r=10, b=40))
        st.plotly_chart(fig_live, use_container_width=True)
        st.caption(f"Records returned by API: {live_data.get('RecordsReturned')} · "
                   f"Total: {live_data.get('RecordCount')}")
    elif not dhs_local.empty:
        fig_fb = px.bar(dhs_local, x="state", y="value", color="value",
                        color_continuous_scale="Reds",
                        labels={"value": "value"}, title=f"{label} (local fallback)")
        fig_fb.update_layout(template="plotly_dark", height=380, margin=dict(t=60, l=10, r=10, b=90))
        fig_fb.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_fb, use_container_width=True)
    else:
        st.info("No data for this indicator.")

    st.link_button("🛠️ Open STATcompiler ↗ (DHS Program)",
                  "https://www.statcompiler.com/en/", type="primary")
    st.caption("STATcompiler is the DHS Program's official interactive tool — no public API, so it opens in a new tab.")

# ------------------------------------------------------- footer (always)
st.caption(
    "Data: Provided hackathon dataset (12,000 villages) · Government of India hospital directory "
    "(30,273 facilities) · geoBoundaries ADM2 (ODC-ODbL) · DHS/NFHS subnational via HDX (CC BY-ND 4.0) · "
    "HeiGIT/WorldPop accessibility indicators (CC BY-SA) · WorldPop 2020 density (CC-BY 4.0) · OpenStreetMap (ODbL)"
)
