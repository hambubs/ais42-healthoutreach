"""
Generate AIS-42_PS-4B.pptx — the Team AIS-42 presentation deck.
Run:  .venv\\Scripts\\python scripts\\make_deck.py   ->  deck/AIS-42_PS-4B.pptx
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parents[1] / "deck" / "AIS-42_PS-4B.pptx"
OUT.parent.mkdir(parents=True, exist_ok=True)

BG = RGBColor(0x0B, 0x12, 0x20)
FG = RGBColor(0xE8, 0xEE, 0xFC)
ACCENT = RGBColor(0x22, 0xD3, 0xA7)
MUTED = RGBColor(0x8E, 0xA0, 0xC0)
RED = RGBColor(0xE7, 0x4C, 0x3C)
AMBER = RGBColor(0xF3, 0x9C, 0x12)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
FOOTER = "Team AIS-42 · PS-4B Rural Healthcare Reachability & Outpost Planning · AI for Sustainability Hackathon 2026"


def new_slide():
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    return s


def add_text(s, x, y, w, h, lines, size=18, color=FG, bold=False,
             align=PP_ALIGN.LEFT, space_after=8, anchor=None):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    if anchor:
        tf.vertical_anchor = anchor
    for i, line in enumerate(lines if isinstance(lines, list) else [lines]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        txt, opts = line if isinstance(line, tuple) else (line, {})
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(opts.get("size", size))
        r.font.color.rgb = opts.get("color", color)
        r.font.bold = opts.get("bold", bold)
    return tb


def footer(s):
    add_text(s, Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.35),
             FOOTER, size=10, color=MUTED)


def content_slide(title, kicker, bullets, big=None):
    s = new_slide()
    add_text(s, Inches(0.5), Inches(0.35), Inches(12.3), Inches(0.7),
             title, size=30, color=ACCENT, bold=True)
    if kicker:
        add_text(s, Inches(0.5), Inches(1.05), Inches(12.3), Inches(0.4),
                 kicker, size=13, color=MUTED)
    y = Inches(1.7) if kicker else Inches(1.4)
    if big:
        add_text(s, Inches(0.5), y, Inches(12.3), Inches(1.1), big,
                 size=40, color=FG, bold=True, align=PP_ALIGN.CENTER)
        y = Inches(3.0)
    add_text(s, Inches(0.7), y, Inches(11.9), Inches(5.0), bullets, size=18)
    footer(s)
    return s


# ---------------------------------------------------------------- slides
# 1 — Title
s = new_slide()
add_text(s, Inches(0.5), Inches(1.5), Inches(12.3), Inches(1.2),
         "HealthOutreach", size=54, color=ACCENT, bold=True, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(2.7), Inches(12.3), Inches(0.6),
         "Rural Healthcare Reachability & Outpost Planning",
         size=24, color=FG, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(3.5), Inches(12.3), Inches(0.5),
         "Team AIS-42 — Sahil Rai · Ashmita Roy · Subhalaxmi Sahoo · Punit Kumar",
         size=16, color=MUTED, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(4.1), Inches(12.3), Inches(0.5),
         "AI for Sustainability Hackathon 2026 · Track 4: Sustainable Healthcare · SDG 3 & 10",
         size=14, color=MUTED, align=PP_ALIGN.CENTER)
add_text(s, Inches(0.5), Inches(5.6), Inches(12.3), Inches(0.6),
         "Spatial AI · Offline Edge SOS · Multi-Modal Dispatch",
         size=18, color=ACCENT, align=PP_ALIGN.CENTER)
footer(s)

# 2 — Problem
content_slide(
    "The Problem: Care Is 107 Minutes Away",
    "Provided dataset: 12,000 villages across Uttar Pradesh, Madhya Pradesh, Maharashtra, Rajasthan, Bihar",
    [
        ("Only 13.82% of villages are within 30 minutes of medical care", {"bold": True}),
        ("107 minutes — the average travel time to the nearest facility", {}),
        ("30.4 km — the average distance to a hospital", {}),
        ("2,611 officially underserved villages · 4,030 with poor roads · 3,118 high-risk", {}),
        ("Static facilities cannot reach dispersed rural populations — and emergencies do not wait", {"color": MUTED}),
    ],
    big="13.82%",
)

# 3 — Solution
content_slide(
    "Our Solution: HealthOutreach",
    "One system, three layers — software AI, offline edge hardware, multi-modal dispatch",
    [
        ("1. Spatial AI — DBSCAN settlement clustering + greedy MCLP places Mobile Medical Units for maximum area coverage", {"bold": True}),
        ("2. Offline Edge — ESP32 captive-portal SOS gateway: zero installs, AES-128 encrypted, works with NO cellular", {"bold": True}),
        ("3. Multi-Modal Dispatch — ambulance · MMU van · 2W rider · UAV handoff · mobile outpost", {"bold": True}),
        ("Built on the provided datasets, enriched with acknowledged open data (HDX · DHS · WorldPop)", {"color": MUTED}),
    ],
)

# 4 — Architecture
content_slide(
    "How It Fits Together",
    "One data spine, three surfaces, zero flow breaks",
    [
        ("Data spine — provided 12,000-village dataset + 30,273-facility government directory (in-memory pandas)", {}),
        ("Optimizer — Healthcare Need Score → underserved detection → DBSCAN → greedy MCLP → dual coverage metrics", {}),
        ("Flask API + SQLite — 17 endpoints: optimize · SOS · sync · dispatch · track · DHS · HeiGIT", {}),
        ("Ops Console (Leaflet) — live SOS feed, dispatch cards, UAV flight lines, KPI chips", {}),
        ("Impact Dashboard (Streamlit) — before/after analytics, WorldPop BLR pilot, live DHS API", {}),
        ("Edge — ESP32 'MMU-GATEWAY' + any phone browser → hub tablet → sync when back online", {}),
    ],
)

# 5 — AI Core
content_slide(
    "The AI Core",
    "Maximum area coverage, not minimum travel — eliminating medical dead zones",
    [
        ("Healthcare Need Score = 0.4·population + 0.3·epidemiological risk + 0.3·inaccessibility", {"bold": True, "color": ACCENT}),
        ("Underserved detection: Underserved_Area flag OR travel > 30 min", {}),
        ("DBSCAN clusters underserved villages into settlement pockets (real clusters on normalized geography)", {}),
        ("Greedy MCLP: select outposts maximizing need-weighted population under scheduled care", {}),
        ("Dual metrics: strict 30-min emergency coverage + scheduled MMU circuit care (NHM operational model)", {}),
        ("Circuits capped at ~400 villages per unit — block-scale, matching National Health Mission practice", {"color": MUTED}),
    ],
)

# 6 — Data provenance
content_slide(
    "Data — Clean Provenance",
    "Clear separation: what was provided vs what we added (judges can audit DATA_SOURCES.md)",
    [
        ("PROVIDED (core of every metric): 12,000-village accessibility dataset + 30,273-facility government hospital directory", {"bold": True}),
        ("ENRICHMENT (read-only overlay, acknowledged): geoBoundaries ADM2 (ODC-ODbL) · DHS/NFHS via HDX (CC BY-ND 4.0) · HeiGIT/WorldPop accessibility (CC BY-SA) · WorldPop 2020 density (CC-BY 4.0)", {}),
        ("No-contamination guarantee: enrichment never writes back into provided data", {"bold": True, "color": ACCENT}),
        ("Documented transformation: provided coordinates were synthetic-uniform → normalized into district polygons for visualization, originals preserved in Latitude_orig/Longitude_orig", {"color": MUTED}),
    ],
)

# 7 — Validation
content_slide(
    "Independent Validation",
    "Our numbers cross-checked against external analyses",
    [
        ("HeiGIT / WorldPop isochrone study: 24.9% of UP and 16.0% of MP population within 30 min of a hospital — same story, same order of magnitude as our 13.82% village-level baseline", {}),
        ("DHS Program API (live, keyless): India child anemia 68.1% (NFHS-5 2019-21) — queried on stage", {}),
        ("Every impact number is computed from provided-dataset columns only", {"bold": True, "color": ACCENT}),
    ],
)

# 8 — Impact
content_slide(
    "Impact — Before / After",
    "Scheduled MMU care coverage of villages",
    [
        ("3 MMUs → 22.84% (14.75 million people newly served)", {"bold": True, "color": ACCENT}),
        ("5 MMUs → 28.58%   ·   8 MMUs → 36.68%", {}),
        ("30-min emergency coverage: 13.82% → 15.09% with 3 MMUs — the gap is bridged by dispatch modes", {}),
        ("Zipline field benchmarks: −61% blood delivery time (Rwanda) · −60% vaccine stock-outs (Ghana)", {"color": MUTED}),
    ],
    big="13.82%  →  22.84%",
)

# 9 — Offline edge
content_slide(
    "Zero-Connectivity SOS",
    "The village has no cell coverage. The phone is in airplane mode.",
    [
        ("Phone joins 'MMU-GATEWAY' Wi-Fi → captive portal auto-opens — zero installs, any browser", {"bold": True}),
        ("One tap: Trauma / Maternal / Medicine", {}),
        ("AES-128-CBC encrypted at rest (mbedTLS, random IV) → queue in flash", {}),
        ("MMU hub tablet pulls the queue → carries it to coverage → syncs → alert appears LIVE on the console", {}),
        ("Fallback: mobile /sos page + console demo triggers — the story never breaks on stage", {"color": MUTED}),
    ],
)

# 10 — Dispatch
content_slide(
    "Multi-Modal Dispatch",
    "Rule engine: right vehicle, right terrain, right time",
    [
        ("🚑 Ambulance (60 km/h) · 🚐 MMU Van (40) · 🏍️ 2W Rider (30) · 🚁 UAV (120) · ⛺ Mobile Outpost", {}),
        ("Road = Poor AND Risk = High → automatic air-dispatch suggestion", {"bold": True, "color": ACCENT}),
        ("UAV handoff: TechEagle-class Vertiplane X3 — 3-5 kg payload, 100 km range, DGCA DigitalSky NPNT compliant", {}),
        ("Route line turns green when ETA ≤ 30 minutes, orange beyond", {}),
        ("We didn't build drones — we built the brain that aims India's drone-logistics ecosystem", {"color": MUTED}),
    ],
)

# 11 — SDG
content_slide(
    "SDG 3 & SDG 10",
    "Sustainability is the architecture, not an afterthought",
    [
        ("SDG 3.8 — Universal Health Coverage: care travels to the people, not people to care", {"bold": True}),
        ("SDG 10.2 — Reduced Inequalities: geography stops being a barrier to survival", {"bold": True}),
        ("Equity is hardcoded: the Need Score biases resources toward the least accessible", {}),
        ("Every percentage point of coverage = millions of people", {"color": ACCENT}),
    ],
)

# 12 — Roadmap + close
content_slide(
    "Roadmap & Close",
    "What we build next",
    [
        ("Real road-network routing (OSRM + PostGIS) replacing straight-line estimates", {}),
        ("Government emergency-API integration for the live SOS feed (poisoning · water · accidents)", {}),
        ("Karnataka pilot: Bengaluru Rural · Ramanagara · Kolar · Tumakuru with the district health office", {}),
        ("Sources & licenses: DATA_SOURCES.md — provided datasets + HDX · DHS · geoBoundaries · HeiGIT · WorldPop · OSM", {"color": MUTED}),
        ("Thank you — Team AIS-42 · Questions?", {"bold": True, "size": 24, "color": ACCENT}),
    ],
)

prs.save(OUT)
print(f"deck written: {OUT}")
print(f"slides: {len(prs.slides.__iter__.__self__._sldIdLst)}")
