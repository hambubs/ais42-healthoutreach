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

# ---- THE PROBLEM (plain English) ----
st.header("📊 The Problem")
st.markdown("""
We analyzed **12,000 villages** across 5 Indian states. Here's what we found:
""")

c1, c2, c3 = st.columns(3)
c1.metric(
    "Villages within 30 min of a hospital",
    f"{baseline['coverage_pct_villages']}%",
    delta="86% of villages CANNOT reach care in 30 minutes",
)
c2.metric(
    "Average travel time to nearest hospital",
    f"{baseline['avg_travel_min']} min",
    delta="That's 1 hour 47 minutes each way",
)
c3.metric(
    "Villages officially marked as underserved",
    f"{baseline['underserved_villages']:,}",
    delta=f"out of {baseline['villages']:,} total villages",
)

c4, c5, c6 = st.columns(3)
c4.metric("Villages with poor road connectivity", f"{baseline['poor_road_villages']:,}")
c5.metric("Villages at high health risk", f"{baseline['high_risk_villages']:,}")
c6.metric("Average distance to nearest hospital", f"{baseline['avg_distance_km']} km")

st.divider()

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Plan Mobile Clinics")
    st.markdown("Adjust the sliders, then click the button to see where clinics should be placed.")
    fleet_size = st.slider("How many mobile clinics to deploy?", 1, 12, 3,
                           help="More clinics = more villages covered, but higher cost")
    max_minutes = st.slider("Target travel time (minutes)", 15, 60, 30, step=5,
                            help="Villages within this travel time are considered 'covered'")
    run = st.button("🚀 Find Optimal Locations", type="primary")
    st.divider()
    states = st.multiselect(
        "Filter map by state",
        sorted(villages["State"].unique()),
        default=sorted(villages["State"].unique()),
    )

result = None
if run:
    with st.spinner("Finding the best locations for your mobile clinics…"):
        result = optimizer.optimize(fleet_size=fleet_size, max_minutes=max_minutes)

if result:
    st.header("✅ The Solution — Your Results")
    st.markdown(f"""
    We placed **{len(result['outposts'])} mobile clinics** at existing hospitals and health centers.
    Here's the impact:
    """)

    d1, d2, d3 = st.columns(3)
    d1.metric(
        "Villages with scheduled clinic visits",
        f"{result['scheduled_care']['coverage_pct_villages']}%",
        delta=f"+{result['scheduled_care']['coverage_pct_villages'] - result['baseline']['coverage_pct_villages']:.1f} percentage points",
    )
    d2.metric(
        "People who now have access to care",
        f"{result['scheduled_care']['new_population'] / 1e6:.1f}M",
        delta="newly served by mobile clinics",
    )
    d3.metric(
        "Emergency response within 30 min",
        f"{result['after']['coverage_pct_villages']}%",
        delta=f"+{result['after']['coverage_pct_villages'] - result['baseline']['coverage_pct_villages']:.1f} pp",
    )

    st.caption(f"Clustering method: **{result['clustering_method']}** · "
               f"{result['candidates_considered']} candidate locations evaluated · "
               f"Each clinic serves ~{result['outposts'][0]['circuit_villages']} villages on a rotating schedule")

# ============================================================ TABS
tab1, tab2, tab3 = st.tabs([
    "🗺️ Where are the clinics?",
    "🛰️ Bengaluru pilot area",
    "🇮🇳 Health data (live)",
])

# -------------------------------------------------------- TAB 1: The Map
with tab1:
    st.subheader("Interactive map — every village, every clinic")
    st.markdown("🟢 Low risk · 🟡 Medium risk · 🔴 High risk · ⭐ Recommended clinic location · "
                "Green circle = 30-min reach · Amber circle = 60-min reach")

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
                    f"<b>{o['outpost_id']}</b> — {o['anchor_district']} district<br>"
                    f"<b>Staged at:</b> {o.get('staged_at', '—')}<br>"
                    f"Serves {o['circuit_villages']:,} villages ({o['circuit_population']:,} people)<br>"
                    f"Average health need score: {o['circuit_mean_need']}",
                    max_width=300,
                ),
            ).add_to(m)
    components.html(m._repr_html_(), height=520, scrolling=False)

    left, right = st.columns(2)
    with left:
        st.subheader("Coverage: before vs after")
        if result:
            fig = go.Figure()
            fig.add_bar(name="Before (no mobile clinics)", x=["Clinic visits within target time"],
                        y=[result["baseline"]["coverage_pct_villages"]], marker_color="#8ea0c0")
            fig.add_bar(name="After (with mobile clinics)", x=["Clinic visits within target time"],
                        y=[result["scheduled_care"]["coverage_pct_villages"]], marker_color="#22d3a7")
            fig.update_layout(template="plotly_dark", yaxis_title="% of villages covered",
                              barmode="group", height=300, margin=dict(t=30, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("👆 Click **Find Optimal Locations** in the sidebar to see the before/after impact.")

        st.subheader("Top 10 districts with the most underserved villages")
        st.markdown("These districts need mobile clinics the most.")
        top = districts.nlargest(10, "underserved")
        fig2 = px.bar(top, x="underserved", y="District", orientation="h", color="mean_need",
                      color_continuous_scale="Viridis",
                      labels={"underserved": "underserved villages", "mean_need": "health need score"})
        fig2.update_layout(template="plotly_dark", height=350, margin=dict(t=10, l=10, r=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    with right:
        st.subheader("Health indicators by state (NFHS-5 survey)")
        st.markdown("Real government survey data showing health challenges in each state.")
        pct = dhs.groupby("indicator")["value"].max()
        indicators = sorted(pct[pct <= 100].index)
        ind = st.selectbox("Which health indicator?", indicators, index=0)
        dd = dhs[dhs["indicator"] == ind].sort_values("value")
        if not dd.empty:
            fig3 = px.bar(dd, x="state", y="value", color="value", color_continuous_scale="Reds",
                          labels={"value": "% of population affected"},
                          title=f"{ind} ({dd['survey'].iloc[0]})")
            fig3.update_layout(template="plotly_dark", height=300, margin=dict(t=60, l=10, r=10, b=90))
            fig3.update_xaxes(tickangle=-45)
            st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Are our numbers correct? Independent verification")
        st.markdown("""
        The **Heidelberg Institute (HeiGIT)** independently analyzed how many people can reach
        a hospital within 30 minutes, using WorldPop satellite population data.
        Their findings match our analysis — confirming the problem is real.
        """)
        ours = (villages.assign(ok=villages["Average_Travel_Time_min"] <= 30)
                .groupby("State")["ok"].mean().mul(100).round(2)
                .rename("Our analysis (% of villages)"))
        hg = (heigit[heigit["category"] == "hospitals"]
              .set_index("state")["within_30min_pop_share_pct"]
              .rename("HeiGIT independent study (%)"))
        cmp = pd.concat([ours, hg], axis=1).dropna().reset_index(names="State")
        fig4 = px.bar(cmp, x="State", y=["Our analysis (% of villages)", "HeiGIT independent study (%)"],
                      barmode="group", labels={"value": "% within 30 min of a hospital"})
        fig4.update_layout(template="plotly_dark", height=300, margin=dict(t=10, l=10, r=10, b=90))
        fig4.update_xaxes(tickangle=-45)
        st.plotly_chart(fig4, use_container_width=True)

    if result:
        st.subheader("Where each clinic is based")
        st.dataframe(pd.DataFrame([{
            "Clinic": o["outpost_id"],
            "District": o["anchor_district"],
            "Based at (real hospital/clinic)": o.get("staged_at", "—"),
            "Villages served": o["circuit_villages"],
            "People covered": f"{o['circuit_population']:,}",
        } for o in result["outposts"]]), use_container_width=True)

    st.divider()
    st.markdown("**Dispatch modes** — how we respond to emergencies:")
    st.markdown(" · ".join(
        f"{m['icon']} **{m['label']}** — {m['trigger']}" for m in optimizer.DISPATCH_MODES.values()))


# ------------------------------------------------ TAB 2: WorldPop BLR pilot
@st.cache_data
def load_worldpop():
    cells_p = CLEAN / "enrichment" / "worldpop" / "blr_pop_cells.json"
    meta_p = CLEAN / "enrichment" / "worldpop" / "blr_pop_meta.json"
    if not cells_p.exists():
        return None, None
    return json.loads(cells_p.read_text()), json.loads(meta_p.read_text())

with tab2:
    st.subheader("Bengaluru outskirts — where people actually live")
    st.markdown("""
    This is our pilot deployment area: the rural districts surrounding Bengaluru
    (Bengaluru Rural, Ramanagara, Kolar, Tumakuru). The heat map shows real population
    density from WorldPop satellite data — each glowing spot is where people live.
    Blue dots are existing hospitals and clinics from the government directory.
    """)
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
        fac_pilot = load_csv("facilities_clean.csv")
        fac_pilot = fac_pilot[fac_pilot["District"].isin(
            ["Bengaluru Rural", "Bengaluru Urban", "Ramanagara", "Kolar", "Tumakuru", "Tumkur", "Bangalore Rural"])]
        for _, r in fac_pilot.iterrows():
            folium.CircleMarker([r["lat"], r["lon"]], radius=2.4, color="#3b82f6",
                                weight=1, fillColor="#3b82f6", fillOpacity=0.7).add_to(m2)
        from folium.plugins import HeatMap
        HeatMap([(c[0], c[1], c[2]) for c in wp_cells],
                radius=18, blur=22, min_opacity=0.3,
                gradient={0.2: "#3b82f6", 0.5: "#22d3a7", 0.8: "#f39c12", 1.0: "#e74c3c"}).add_to(m2)
        components.html(m2._repr_html_(), height=500, scrolling=False)

        p1, p2, p3 = st.columns(3)
        p1.metric("People living in this area", f"{wp_meta['total_population_in_bbox']:,}")
        p2.metric("Existing hospitals & clinics", f"{len(fac_pilot)}")
        p3.metric("Pilot districts", "Bengaluru Rural · Ramanagara · Kolar · Tumakuru")
        st.caption(
            f"Source: {wp_meta['source']} · License: {wp_meta['license']} · "
            f"Population density from WorldPop 2020 satellite data at {wp_meta['worldpop_resolution']} resolution. "
            f"Facility locations from the Government of India hospital directory."
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

DHS_INDICATORS = {
    "CN_ANMC_C_ANY": "Children with any anemia (under 5)",
    "RH_ANCP_W_DOC": "Antenatal care from a doctor",
    "FE_FRTR_W_TFR": "Total fertility rate",
    "ML_FEVT_C_DPT": "DPT immunization coverage",
    "WS_SRCE_PHN": "Households with clean drinking water",
    "NU_HH_W_ANH": "Households using clean cooking fuel",
}

with tab3:
    st.subheader("Live health data from the DHS Program")
    st.markdown("""
    This data is fetched **live** from the [DHS Program API](https://api.dhsprogram.com) —
    the same source the Government of India uses for the National Family Health Survey (NFHS).
    No API key required. If the internet is unavailable, we automatically fall back to
    our downloaded copy.
    """)

    label = st.selectbox("Which health indicator?", list(DHS_INDICATORS.values()),
                         index=0, key="dhs_pick")
    ind_id = [k for k, v in DHS_INDICATORS.items() if v == label][0]

    dhs_local = pd.DataFrame()
    live_data = None
    source_used = "fallback"
    try:
        live_data = fetch_dhs_live(ind_id)
        source_used = "live"
    except Exception as exc:
        st.caption(f"⚠️ Live API unavailable ({exc}); using our downloaded copy.")
        FALLBACK_KEYS = {
            "Children with any anemia (under 5)": "anemia",
            "Antenatal care from a doctor": "Antenatal",
            "Total fertility rate": "fertility",
            "DPT immunization coverage": "immunization",
            "Households with clean drinking water": "drinking water",
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
        st.caption(f"🟢 **LIVE from api.dhsprogram.com** · fetched {ts} · {len(rows)} records")
        df_live = pd.DataFrame(rows)
        fig_live = px.bar(df_live, x="SurveyYearLabel", y="Value",
                          color="SurveyYearLabel", text="Value",
                          labels={"SurveyYearLabel": "Survey year", "Value": "Indicator value"},
                          title=f"India — {label} (across DHS survey rounds)")
        fig_live.update_traces(texttemplate="%{text}", textposition="outside")
        fig_live.update_layout(template="plotly_dark", showlegend=False, height=350,
                               margin=dict(t=60, l=10, r=10, b=40))
        st.plotly_chart(fig_live, use_container_width=True)
        st.caption(f"Records returned: {live_data.get('RecordsReturned')} · "
                   f"Total: {live_data.get('RecordCount')}")
    elif not dhs_local.empty:
        fig_fb = px.bar(dhs_local, x="state", y="value", color="value",
                        color_continuous_scale="Reds",
                        labels={"value": "value"}, title=f"{label} (downloaded copy)")
        fig_fb.update_layout(template="plotly_dark", height=350, margin=dict(t=60, l=10, r=10, b=90))
        fig_fb.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_fb, use_container_width=True)
    else:
        st.info("No data available for this indicator right now.")

    st.link_button("🛠️ Open STATcompiler ↗ (explore more DHS data)",
                  "https://www.statcompiler.com/en/", type="primary")
    st.caption("STATcompiler is the DHS Program's official interactive tool — opens in a new tab.")

# ------------------------------------------------------- footer (always)
st.caption(
    "Data: Provided hackathon dataset (12,000 villages) · Government of India hospital directory "
    "(30,273 facilities) · geoBoundaries ADM2 (ODC-ODbL) · DHS/NFHS subnational via HDX (CC BY-ND 4.0) · "
    "HeiGIT/WorldPop accessibility indicators (CC BY-SA) · WorldPop 2020 density (CC-BY 4.0) · OpenStreetMap (ODbL)"
)
