"""
Spatial optimization core for PS-4B (Team AIS-42).

Pipeline
--------
1. Underserved detection   : Underserved_Area_Flag OR travel > threshold
2. DBSCAN clustering      : dense pockets of underserved villages
3. Candidate MMU locations: cluster centroids
4. Greedy MCLP            : pick `fleet_size` sites maximizing need-weighted
                            population within the travel-time threshold
5. Coverage BEFORE/AFTER  : baseline (existing facilities) vs baseline+outposts

Travel-time model
-----------------
No road-network routing inside a 24h sprint: candidate->village travel
minutes are estimated as haversine distance / village road speed, where
road speed encodes Road_Connectivity (Good 40 / Average 25 / Poor 12 km/h).
The provided per-village Average_Travel_Time_min is used for the BASELINE
(existing facility access). DBSCAN "noise" villages are hyper-remote and
get flagged for UAV-only outreach.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans

CLEAN = Path(__file__).resolve().parent / "data" / "clean"

ROAD_SPEED = {"Good": 40.0, "Average": 25.0, "Poor": 12.0}
DEFAULT_SPEED = 25.0
R_EARTH_KM = 6371.0

_cache: dict = {}


def load_data(force: bool = False):
    """Load cleaned datasets (cached in memory for the process lifetime)."""
    if force or "villages" not in _cache:
        _cache.pop("centroids", None)
        _cache["villages"] = pd.read_csv(CLEAN / "villages_clean.csv")
        _cache["facilities"] = pd.read_csv(CLEAN / "facilities_clean.csv")
        _cache["districts"] = pd.read_csv(CLEAN / "district_summary.csv")
    return _cache["villages"], _cache["facilities"], _cache["districts"]


def baseline_stats() -> dict:
    return json.loads((CLEAN / "baseline_stats.json").read_text())


def district_centroids() -> dict:
    """(State, District) -> (lat, lon) mean of village coords. Cached."""
    if "centroids" not in _cache:
        v, _, _ = load_data()
        g = v.groupby(["State", "District"])[["Latitude", "Longitude"]].mean()
        _cache["centroids"] = {
            (s, d): (float(r["Latitude"]), float(r["Longitude"]))
            for (s, d), r in g.iterrows()
        }
    return _cache["centroids"]


# ------------------------------------------------------------------ geometry
def pairwise_haversine_km(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(A,2) x (B,2) lat/lon arrays -> (A,B) distance matrix in km."""
    lat_a = np.radians(a[:, 0])[:, None]
    lon_a = np.radians(a[:, 1])[:, None]
    lat_b = np.radians(b[:, 0])[None, :]
    lon_b = np.radians(b[:, 1])[None, :]
    dlat = lat_b - lat_a
    dlon = lon_b - lon_a
    h = np.sin(dlat / 2.0) ** 2 + np.cos(lat_a) * np.cos(lat_b) * np.sin(dlon / 2.0) ** 2
    return 2.0 * R_EARTH_KM * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return float(pairwise_haversine_km(np.array([[lat1, lon1]]), np.array([[lat2, lon2]]))[0, 0])


# -------------------------------------------------------------- optimization
def underserved_mask(v: pd.DataFrame, max_minutes: int = 30) -> pd.Series:
    return (v["Underserved_Area_Flag_bin"] == 1) | (v["Average_Travel_Time_min"] > max_minutes)


def dbscan_candidates(v: pd.DataFrame, eps_km: float = 25.0, min_samples: int = 10,
                      min_candidates: int = 8, max_circuit: int = 400):
    """Cluster underserved villages; centroids become candidate MMU sites.

    DBSCAN is the primary algorithm (dense settlement pockets; -1 noise =
    hyper-remote villages earmarked for UAV-only outreach). Two guards keep
    the optimizer stage-proof on any data:
      * too few DBSCAN clusters (uniform data) -> K-Means fallback;
      * mega-clusters (chained uniform blobs)   -> K-Means sub-split into
        MMU-sized circuits of <= max_circuit villages (block-scale,
        matching NHM Mobile Medical Unit practice).

    Returns (candidates_df, noise_df, method, labeled_df).
    """
    sub = v[underserved_mask(v)].copy()
    coords = sub[["Latitude", "Longitude"]].to_numpy()
    labels = DBSCAN(eps=eps_km / 111.0, min_samples=min_samples).fit_predict(coords)
    method = "dbscan"
    core_mask = labels != -1
    n_core_clusters = pd.Series(labels[core_mask]).nunique() if core_mask.any() else 0
    if n_core_clusters < min_candidates:
        labels = KMeans(n_clusters=24, n_init=10, random_state=42).fit_predict(coords)
        core_mask = np.ones(len(sub), dtype=bool)
        method = "kmeans_fallback"

    # refine mega-clusters into MMU-sized circuits
    final = np.full(len(sub), -1, dtype=int)
    next_label = 0
    for cid in np.unique(labels[core_mask]):
        m = (labels == cid) & core_mask
        n = int(m.sum())
        if n > max_circuit:
            k = int(np.ceil(n / max_circuit))
            km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(coords[m])
            positions = np.where(m)[0]
            for sl in range(k):
                final[positions[km.labels_ == sl]] = next_label
                next_label += 1
        else:
            final[m] = next_label
            next_label += 1
    sub["cluster"] = final

    noise = sub[sub["cluster"] == -1].copy()
    core = sub[sub["cluster"] != -1]
    rows = []
    for cid, g in core.groupby("cluster"):
        rows.append({
            "candidate_id": f"C{int(cid):03d}",
            "lat": float(g["Latitude"].mean()),
            "lon": float(g["Longitude"].mean()),
            "villages": int(len(g)),
            "population": int(g["Population"].sum()),
            "mean_need": float(g["need_score"].mean()),
        })
    labeled = sub[["Village_ID", "Population", "need_score", "cluster"]].copy()
    return pd.DataFrame(rows), noise, method, labeled


def travel_minutes_matrix(cand_coords: np.ndarray, v: pd.DataFrame) -> np.ndarray:
    """(C,V) estimated travel minutes from each candidate to every village."""
    dist = pairwise_haversine_km(cand_coords, v[["Latitude", "Longitude"]].to_numpy())
    speed = v["road_speed_kmph"].fillna(DEFAULT_SPEED).to_numpy()
    return dist / speed[None, :] * 60.0


def greedy_mclp(cands: pd.DataFrame, v: pd.DataFrame, travel: np.ndarray,
                fleet_size: int = 3, max_minutes: int = 30):
    """Greedy Maximal Coverage Location Problem.

    Iteratively selects the candidate covering the most need-weighted
    population (need_score x Population) within max_minutes that is not
    already covered. Returns (chosen_indices, covered_mask).
    """
    weight = (v["need_score"] * v["Population"]).to_numpy(dtype=float)
    reachable = travel <= max_minutes
    covered = np.zeros(len(v), dtype=bool)
    chosen: list[int] = []
    for _ in range(min(fleet_size, len(cands))):
        remaining = ~covered
        gain = reachable[:, remaining] @ weight[remaining]
        if gain.size == 0 or gain.max() <= 0:
            break
        j = int(np.argmax(gain))
        chosen.append(j)
        covered |= reachable[j]
    return chosen, covered


def optimize(fleet_size: int = 3, max_minutes: int = 30,
             eps_km: float = 25.0, min_samples: int = 10) -> dict:
    """Full pipeline run -> dict ready for the API/dashboard."""
    v, fac, ds = load_data()
    cands, noise, method, labeled = dbscan_candidates(v, eps_km, min_samples)
    if cands.empty:
        raise RuntimeError("clustering produced no candidates")

    pop = v["Population"].to_numpy(dtype=float)
    need = v["need_score"].to_numpy(dtype=float)
    base = (v["Average_Travel_Time_min"] <= max_minutes).to_numpy()

    # ---- map each candidate cluster to village row indices -----------------
    vid2row = pd.Series(np.arange(len(v)), index=v["Village_ID"].values)
    cluster_indices = []
    for cid in cands["candidate_id"]:
        label = int(cid[1:])
        vids = labeled.loc[labeled["cluster"] == label, "Village_ID"]
        cluster_indices.append(vid2row.reindex(vids).dropna().astype(int).to_numpy())

    # ---- greedy MCLP: maximize need-weighted population brought under
    #      scheduled MMU care (cluster circuits, NHM MMU operational model) --
    covered_sched = np.zeros(len(v), dtype=bool)
    chosen: list[int] = []
    for _ in range(min(fleet_size, len(cands))):
        gain = np.full(len(cands), -1.0)
        for ci in range(len(cands)):
            if ci in chosen:
                continue
            idx = cluster_indices[ci]
            new = idx[~covered_sched[idx]]
            gain[ci] = float(pop[new] @ need[new]) if new.size else 0.0
        if gain.max() <= 0:
            break
        j = int(np.argmax(gain))
        chosen.append(j)
        covered_sched[cluster_indices[j]] = True

    # ---- re-anchor each outpost to a REAL place ------------------------------
    # An MMU stages from an actual health facility (government directory) —
    # never an arbitrary map point. Fallback: the highest-need village of the
    # circuit when no facility lies within 50 km.
    fac_coords = fac[["lat", "lon"]].to_numpy()
    outposts = []
    final_positions = []
    for rank, ci in enumerate(chosen, start=1):
        c = cands.iloc[ci]
        idx = cluster_indices[ci]
        circuit = v.iloc[idx]
        district = circuit["District"].mode()

        d_fac = pairwise_haversine_km(np.array([[c["lat"], c["lon"]]]), fac_coords)[0]
        fi = int(np.argmin(d_fac))
        f_row = fac.iloc[fi]
        if d_fac[fi] <= 50.0:
            o_lat, o_lon = float(f_row["lat"]), float(f_row["lon"])
            staged_at = str(f_row["Hospital_Name"])[:80]
            staged_kind = "facility"
            emerg = " · ⚡ emergency" if bool(f_row["has_emergency"]) else ""
            staged_info = f"{int(f_row['beds'])} beds · {int(f_row['doctors'])} doctors{emerg}"
        else:
            hv = circuit.loc[circuit["need_score"].idxmax()]
            o_lat, o_lon = float(hv["Latitude"]), float(hv["Longitude"])
            staged_at = f"{hv['Village_ID']} (highest-need village)"
            staged_kind = "village"
            staged_info = f"population {int(hv['Population']):,}"

        final_positions.append((o_lat, o_lon))
        outposts.append({
            "outpost_id": f"MMU-{rank:02d}",
            "lat": round(o_lat, 5),
            "lon": round(o_lon, 5),
            "staged_at": staged_at,
            "staged_kind": staged_kind,
            "staged_info": staged_info,
            "circuit_villages": int(len(idx)),
            "circuit_population": int(pop[idx].sum()),
            "circuit_mean_need": round(float(c["mean_need"]), 3),
            "anchor_district": str(district.iloc[0]) if len(district) else "",
            "circuit_village_ids": circuit["Village_ID"].tolist(),
        })

    # ---- strict 30-min emergency reach from the FINAL outpost positions ------
    final_arr = np.array(final_positions)
    reachable_final = travel_minutes_matrix(final_arr, v) <= max_minutes
    covered_emerg = np.zeros(len(v), dtype=bool)
    for j in range(len(final_arr)):
        covered_emerg |= reachable_final[j]
    after_emerg = base | covered_emerg
    for rank, o in enumerate(outposts):
        new_mask = reachable_final[rank] & ~base
        o["emergency_new_villages"] = int(new_mask.sum())
        o["emergency_village_ids"] = v.loc[new_mask, "Village_ID"].tolist()

    after_care = base | covered_sched
    return {
        "params": {"fleet_size": fleet_size, "max_minutes": max_minutes,
                    "eps_km": eps_km, "min_samples": min_samples},
        "clustering_method": method,
        "baseline": {
            "coverage_pct_villages": round(100.0 * base.mean(), 2),
            "coverage_pct_population": round(100.0 * pop[base].sum() / pop.sum(), 2),
        },
        "after": {
            "coverage_pct_villages": round(100.0 * after_emerg.mean(), 2),
            "coverage_pct_population": round(100.0 * pop[after_emerg].sum() / pop.sum(), 2),
        },
        "scheduled_care": {
            "coverage_pct_villages": round(100.0 * after_care.mean(), 2),
            "coverage_pct_population": round(100.0 * pop[after_care].sum() / pop.sum(), 2),
            "new_villages": int((covered_sched & ~base).sum()),
            "new_population": int(pop[covered_sched & ~base].sum()),
        },
        "outposts": outposts,
        "candidates_considered": int(len(cands)),
        "noise_villages": int(len(noise)),
        "noise_population": int(noise["Population"].sum()) if len(noise) else 0,
        "noise_note": "DBSCAN noise = hyper-remote villages flagged for UAV-only outreach",
    }


# ------------------------------------------------------------ dispatch engine
DISPATCH_MODES = {
    "ambulance": {"label": "Ambulance", "icon": "\U0001F691", "speed_kmph": 60.0,
                  "payload": "patient transport", "trigger": "emergency SOS"},
    "mmu_van": {"label": "MMU Van", "icon": "\U0001F690", "speed_kmph": 40.0,
                "payload": "team + equipment", "trigger": "scheduled clinic at outpost"},
    "rider_2w": {"label": "2W Health Rider", "icon": "\U0001F3CD\uFE0F", "speed_kmph": 30.0,
                 "payload": "small cold box", "trigger": "poor roads, routine care"},
    "bike": {"label": "Bike Medic", "icon": "\U0001F6B4\uFE0F", "speed_kmph": 35.0,
             "payload": "medic + cold box", "trigger": "narrow tracks, fast response"},
    "uav": {"label": "UAV Handoff", "icon": "\U0001F6E9", "speed_kmph": 120.0,
            "payload": "3-5 kg medical payload", "trigger": "poor road AND high risk"},
    "helicopter": {"label": "Helicopter", "icon": "\U0001F681", "speed_kmph": 200.0,
                   "payload": "critical patient airlift", "trigger": "terrain-locked critical"},
    "outpost": {"label": "Mobile Outpost", "icon": "\u26F1\uFE0F", "speed_kmph": 0.0,
                "payload": "multi-day camp", "trigger": "DBSCAN noise villages"},
}


def recommend_mode(road: str, risk: str, sos_type: str = "routine") -> str:
    """Rule engine: pick the dispatch mode for a village/cluster."""
    if sos_type in ("trauma", "maternal", "emergency"):
        if road == "Poor" and risk == "High":
            return "helicopter"      # terrain-locked critical airlift
        return "ambulance"
    if road == "Poor" and risk == "High":
        return "uav"                 # supply air-drop
    if road == "Poor":
        return "rider_2w"
    return "mmu_van"


def uav_handoff(drop_lat: float, drop_lon: float, facilities: pd.DataFrame | None = None) -> dict:
    """Build a partner handoff payload (TechEagle-class Vertiplane X3 specs:
    3-5 kg, 100 km range, 120 km/h cruise).

    Pickup = nearest facility overall, preferring an emergency-capable one
    within 100 km. (The has_emergency pool is sparse — ~319 of 10,672 — so
    restricting to it produced absurd 200+ km pickups.)
    """
    if facilities is None:
        _, facilities, _ = load_data()
    coords = facilities[["lat", "lon"]].to_numpy()
    d = pairwise_haversine_km(np.array([[drop_lat, drop_lon]]), coords)[0]
    order = np.argsort(d)
    pick = int(order[0])
    for i in order[:50]:
        if bool(facilities.iloc[int(i)]["has_emergency"]) and d[i] <= 100.0:
            pick = int(i)
            break
    f = facilities.iloc[pick]
    eta = float(d[pick]) / 120.0 * 60.0 + 5.0  # cruise + load/launch buffer
    return {
        "partner": "TechEagle-class BVLOS operator (Vertiplane X3)",
        "pickup": {"name": str(f["Hospital_Name"])[:80],
                   "lat": round(float(f["lat"]), 5), "lon": round(float(f["lon"]), 5)},
        "drop": {"lat": round(float(drop_lat), 5), "lon": round(float(drop_lon), 5)},
        "distance_km": round(float(d[pick]), 1),
        "cruise_kmph": 120.0,
        "payload_kg": "3-5",
        "eta_min": round(eta, 1),
        "regulatory": "DGCA DigitalSky NPNT-compliant flight request",
    }
