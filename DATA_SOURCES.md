# Data Provenance — AIS-42 HealthOutreach

Team AIS-42 · PS-4B Rural Healthcare Reachability & Outpost Planning
**Clear separation between hackathon-PROVIDED data and our own ENRICHMENT (open data, acknowledged).**

## 1. PROVIDED datasets (given to the team / official sources for this hackathon)

| File | What it is | Where used |
|---|---|---|
| `backend/data/raw/villages_12k.csv` | 12,000-village rural healthcare accessibility dataset (26 columns: population, travel time, road condition, risk level, accessibility score, underserved flag…) | The entire optimization pipeline |
| `backend/data/raw/hospital_directory.csv` | Government of India hospital directory — 30,273 facilities with coordinates, emergency/ambulance/blood-bank phones, beds, doctors | Facility map layer, UAV pickup points, district supply counts |

**Derived from PROVIDED data only** (no enrichment touches these):
- `backend/data/clean/villages_clean.csv` — cleaned + encoded villages (+ computed `need_score`)
- `backend/data/clean/facilities_clean.csv` — coordinate-valid facilities
- `backend/data/clean/baseline_stats.json` — the 13.82% / 107-min baseline
- `backend/data/clean/district_summary.csv` — provided demand ⨯ provided facility counts (our district-alias logic: Kanpur→Kanpur Nagar/Dehat, Prayagraj→Allahabad)

**Geographic normalization (documented transformation):** the provided dataset's
Latitude/Longitude are synthetic-uniform — every state's villages span the same
18–27°N / 72–88°E box, which renders as a giant square on a map. `scripts/fix_geo.py`
re-anchors each village to a plausible position inside its own district polygon
(geoBoundaries ADM2) for geographically meaningful visualization, **preserving the
provided coordinates in `Latitude_orig` / `Longitude_orig`**. No other column is
altered; all metrics still derive from provided values.

## 2. ENRICHMENT datasets (downloaded by us — open data, properly acknowledged)

All enrichment-derived files live in **`backend/data/clean/enrichment/`** — physically separated.

| File | Source | License | What it adds |
|---|---|---|---|
| `raw/india_adm1.geojson`, `raw/india_adm2.geojson` | geoBoundaries (wmgeolab) | ODC-ODbL | State/district map borders → `enrichment/districts.geojson` (filtered to our 26 districts) |
| `raw/dhs_anemia_subnational_ind.csv`, `raw/dhs_access_to_health_care_subnational_ind.csv` | The DHS Program (NFHS) via HDX | CC BY-ND 4.0 | State-level epidemiological indicators → `enrichment/dhs_state_indicators.csv` (dashboard explorer chart) |
| `raw/heigit_phc_access_wide.csv`, `raw/heigit_hospitals_access_wide.csv` | HeiGIT / WorldPop accessibility indicators | CC BY-SA | Independent travel-time validation → `enrichment/heigit_state_access.csv` (validation chart) |
| `raw/ind_ppp_2020_1km_Aggregated_UNadj.tif` | WorldPop Global 2000–2020, India 2020 (1km) | CC-BY 4.0 | Population density for the BLR pilot bbox → `enrichment/worldpop/blr_pop_cells.json` + `blr_pop_meta.json` (Dashboard "WorldPop Density" tab) |
| DHS Program API (live) | `api.dhsprogram.com/rest/dhs/data?countryIds=IA&indicatorIds=...` | no key required | Live indicator trends in the "DHS Live & STATcompiler" tab; local CSV fallback if Wi-Fi drops |

## 3. No-contamination guarantee

- The **Healthcare Need Score** (`0.4·population + 0.3·risk + 0.3·inaccessibility`) and every
  coverage metric (baseline / after / scheduled care) are computed **exclusively** from
  provided-dataset columns: `Population`, `Healthcare_Risk_Level`, `Accessibility_Score`,
  `Average_Travel_Time_min`, `Road_Connectivity`, `Underserved_Area_Flag`.
- Enrichment data is joined **at read time only** (map borders, dashboard charts, validation)
  and is **never written back** into `villages_clean.csv` or any provided-derived file.
- Therefore all impact numbers presented to judges reflect the provided dataset alone;
  enrichment provides context (DHS), independent validation (HeiGIT), and cartography (geoBoundaries).

## 4. Attribution (also shown in the dashboard footer and deck Sources slide)

- Provided hackathon dataset (12,000 villages) · Government of India hospital directory (30,273 facilities)
- geoBoundaries ADM1/ADM2 — ODC-ODbL · DHS/NFHS subnational via HDX — CC BY-ND 4.0
- HeiGIT/WorldPop accessibility indicators — CC BY-SA · OpenStreetMap tiles — ODbL
