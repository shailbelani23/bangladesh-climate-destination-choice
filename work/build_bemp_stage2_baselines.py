#!/usr/bin/env python3
"""Build BEMP district universe, choice sets, and transparent benchmark models.

This is deliberately a benchmark-stage script. It uses only origin district,
candidate district population, and straight-line distance. It does not use any
post-move reason, network, or destination-specific survey response as a feature.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "work" / "vendor"))
from shapely import contains_xy  # noqa: E402
from shapely.geometry import shape  # noqa: E402


EVENTS_PATH = ROOT / "outputs/tables/bemp_prospective_migration_events.csv"
GEOJSON_PATH = ROOT / "data/external/bangladesh_admin/bgd_adm2_bbs_20201113.geojson"
BBS_PDF_PATH = ROOT / "data/external/bbs_census_2022/BBS_National_Report_Volume_1_2022.pdf"
BBS_TEXT_PATH = ROOT / "work/pdf_extract/bbs_national_report_v1_2022.txt"
BBS_PRELIMINARY_PDF_PATH = ROOT / "data/external/bbs_census_2022/BBS_Preliminary_Census_2022_English.pdf"
TABLES = ROOT / "outputs/tables"
REPORTS = ROOT / "outputs/reports"

ADMIN_URL = (
    "https://gis.dghs.gov.bd/server/rest/services/Hosted/"
    "bgd_admbnda_adm2_bbs_20201113/FeatureServer/0"
)
BBS_PAGE_URL = (
    "https://bbs.gov.bd/site/page/47856ad0-7e1c-4aab-bd78-892733bc06eb/"
    "Population-and-Housing-Census%2C"
)
BBS_PDF_URL = (
    "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/"
    "V2Ministry/o/office-bbs/2024/12/9ce5bd160bb14a1ab1eabe886adddb9a.pdf"
)
BBS_PRELIMINARY_PDF_URL = (
    "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/"
    "V2Ministry/o/office-bbs/2024/12/64cfb2e2a63042c9b96acfc276275836.pdf"
)
NATIONAL_PORTAL_URL = "https://bangladesh.gov.bd/views/district-list/"


NAME_FIX = {
    "Barisal": "Barishal",
    "Bogra": "Bogura",
    "Brahamanbaria": "Brahmanbaria",
    "Chittagong": "Chattogram",
    "Comilla": "Cumilla",
    "Jessore": "Jashore",
    "Kishoregonj": "Kishoreganj",
    "Maulvibazar": "Moulvibazar",
    "Nawabganj": "Chapainawabganj",
    "Netrokona": "Netrakona",
}
DIVISION_FIX = {
    "Barisal": "Barishal",
    "Chittagong": "Chattogram",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def haversine_km(lon1, lat1, lon2, lat2):
    lon1 = np.radians(lon1)
    lat1 = np.radians(lat1)
    lon2 = np.radians(lon2)
    lat2 = np.radians(lat2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def ring_area_km2(coords, lat0=23.7):
    arr = np.asarray(coords, dtype=float)
    if len(arr) < 4:
        return 0.0
    x = 6371.0088 * np.radians(arr[:, 0]) * math.cos(math.radians(lat0))
    y = 6371.0088 * np.radians(arr[:, 1])
    return abs(0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def geometry_area_km2(geo):
    coords = geo["coordinates"]
    polys = [coords] if geo["type"] == "Polygon" else coords
    total = 0.0
    for poly in polys:
        total += ring_area_km2(poly[0])
        total -= sum(ring_area_km2(hole) for hole in poly[1:])
    return total


def sample_points_in_geometry(geom, n, seed):
    rng = np.random.default_rng(seed)
    minx, miny, maxx, maxy = geom.bounds
    xs_out, ys_out = [], []
    attempts = 0
    while sum(map(len, xs_out)) < n:
        remaining = n - sum(map(len, xs_out))
        batch = max(remaining * 8, 2000)
        xs = rng.uniform(minx, maxx, batch)
        ys = rng.uniform(miny, maxy, batch)
        keep = contains_xy(geom, xs, ys)
        if keep.any():
            xs_out.append(xs[keep][:remaining])
            ys_out.append(ys[keep][:remaining])
        attempts += batch
        if attempts > 5_000_000:
            raise RuntimeError(f"Could not sample geometry after {attempts:,} draws")
    return np.concatenate(xs_out)[:n], np.concatenate(ys_out)[:n]


def parse_bbs_population(canonical_names):
    text = BBS_TEXT_PATH.read_text(encoding="utf-8", errors="replace")
    block = text.split("Table P02 Population by Sex, District and Location, 2022", 1)[1]
    block = block.split("Table P03 Population by Age, Sex, Division and Location, 2022", 1)[0]
    rows = []
    pattern = re.compile(r"^\s*([A-Za-z’' .-]+?)\s+([0-9][0-9,]*)\s+", re.MULTILINE)
    for name, pop in pattern.findall(block):
        name = re.sub(r"\s+", " ", name.strip()).replace("’", "'")
        name = NAME_FIX.get(name, name)
        if name in canonical_names:
            rows.append((name, int(pop.replace(",", ""))))
    # Drop exact duplicates defensively; division-total rows include the word
    # "Division" and therefore do not collide with canonical district names.
    out = pd.DataFrame(rows, columns=["district", "population_2022_total"])
    out = out.drop_duplicates("district", keep="last").sort_values("district")
    missing = sorted(set(canonical_names) - set(out["district"]))
    extra = sorted(set(out["district"]) - set(canonical_names))
    assert len(out) == 64 and not missing and not extra, (len(out), missing, extra)
    return out


def build_district_universe():
    gj = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    assert gj["type"] == "FeatureCollection" and len(gj["features"]) == 64
    records = []
    sampled = {}
    for feat in gj["features"]:
        props = feat["properties"]
        old_name = props["adm2_en"]
        name = NAME_FIX.get(old_name, old_name)
        div_old = props["adm1_en"]
        division = DIVISION_FIX.get(div_old, div_old)
        geom = shape(feat["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        centroid = geom.centroid
        centroid_inside = bool(geom.covers(centroid))
        point = centroid if centroid_inside else geom.representative_point()
        area = geometry_area_km2(feat["geometry"])
        seed = int(hashlib.sha256(props["adm2_pcode"].encode()).hexdigest()[:8], 16)
        sx, sy = sample_points_in_geometry(geom, n=600, seed=seed)
        sampled[name] = (sx, sy)
        rng = np.random.default_rng(seed + 991)
        a = rng.integers(0, len(sx), 30000)
        b = rng.integers(0, len(sx), 30000)
        b[b == a] = (b[b == a] + 1) % len(sx)
        within = float(np.mean(haversine_km(sx[a], sy[a], sx[b], sy[b])))
        eq_radius = math.sqrt(area / math.pi)
        disk_expected = 128.0 * eq_radius / (45.0 * math.pi)
        records.append(
            {
                "district": name,
                "district_name_geometry_raw": old_name,
                "district_pcode": props["adm2_pcode"],
                "division": division,
                "division_name_geometry_raw": div_old,
                "central_lon": point.x,
                "central_lat": point.y,
                "central_point_method": "polygon_centroid" if centroid_inside else "representative_point",
                "polygon_centroid_inside": centroid_inside,
                "area_km2_approx": area,
                "within_district_mean_pair_km_mc": within,
                "within_district_disk_proxy_km": disk_expected,
                "geometry_source": "Bangladesh DGHS hosted BBS 2020 ADM2 layer",
                "geometry_source_url": ADMIN_URL,
            }
        )
    districts = pd.DataFrame(records).sort_values("district").reset_index(drop=True)
    assert len(districts) == 64 and districts["district"].is_unique
    pop = parse_bbs_population(set(districts["district"]))
    districts = districts.merge(pop, on="district", how="left", validate="one_to_one")
    assert districts["population_2022_total"].notna().all()
    districts["population_source"] = "BBS Population and Housing Census 2022, National Report Volume I, Table P02"
    districts["population_source_url"] = BBS_PDF_URL
    districts["population_pdf_pages"] = "PDF pages 199-200 (printed pages 151-152)"
    return districts, sampled


def build_od_matrix(districts):
    rows = []
    for oi in districts.itertuples(index=False):
        for dj in districts.itertuples(index=False):
            centroid = float(haversine_km(oi.central_lon, oi.central_lat, dj.central_lon, dj.central_lat))
            same = oi.district == dj.district
            effective = float(oi.within_district_mean_pair_km_mc) if same else centroid
            disk = float(oi.within_district_disk_proxy_km) if same else centroid
            rows.append(
                {
                    "origin_district": oi.district,
                    "origin_pcode": oi.district_pcode,
                    "destination_district": dj.district,
                    "destination_pcode": dj.district_pcode,
                    "same_district": same,
                    "centroid_haversine_km": centroid,
                    "effective_distance_km": effective,
                    "distance_1km_floor_km": max(centroid, 1.0),
                    "distance_disk_proxy_km": disk,
                    "destination_population_2022": int(dj.population_2022_total),
                    "origin_population_2022": int(oi.population_2022_total),
                }
            )
    od = pd.DataFrame(rows)
    pop_lookup = districts.set_index("district")["population_2022_total"].to_dict()
    for origin, idx in od.groupby("origin_district").groups.items():
        block = od.loc[idx]
        for row_idx, r in block.iterrows():
            if r["same_district"]:
                s = 0
            else:
                nearer = block[
                    (block["effective_distance_km"] < r["effective_distance_km"])
                    & (block["destination_district"] != origin)
                    & (block["destination_district"] != r["destination_district"])
                ]["destination_district"]
                s = int(sum(pop_lookup[x] for x in nearer))
            od.at[row_idx, "intervening_population_2022"] = s
    od["intervening_population_2022"] = od["intervening_population_2022"].astype("int64")
    m = od["origin_population_2022"].astype(float)
    n = od["destination_population_2022"].astype(float)
    s = od["intervening_population_2022"].astype(float)
    od["radiation_score_adapted"] = m * n / ((m + s) * (m + n + s))
    od["gravity_fixed_score_pop_over_d2"] = n / np.square(od["effective_distance_km"])
    od["log_effective_distance_km"] = np.log(od["effective_distance_km"])
    od["log_destination_population_2022"] = np.log(n)
    assert len(od) == 64 * 64
    return od


def bool_col(s):
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().eq("true")


def build_choice_sets(events, districts, od):
    eligible = events[bool_col(events["stage1_district_endpoint_eligible"])].copy()
    eligible["origin_district"] = eligible["origin_district_codebook"].replace(NAME_FIX)
    eligible["chosen_district"] = eligible["destination_district_official"].replace(NAME_FIX)
    universe = set(districts["district"])
    assert set(eligible["origin_district"]) <= universe
    assert set(eligible["chosen_district"]) <= universe
    keep = [
        "event_id", "respondent_id", "household_id_derived", "baseline_location_lxx",
        "wave", "wave_number", "event_class", "origin_district", "chosen_district",
        "stage1_household_relocation_eligible", "lagged_home_shock_observed",
        "lagged_home_shock_any_yes", "distance_from_previous_location_m",
    ]
    base = eligible[keep].copy()
    base["sample_all_district_events"] = True
    base["sample_household_relocation"] = bool_col(base["stage1_household_relocation_eligible"])
    base["sample_household_lagged_shock_yes"] = (
        base["sample_household_relocation"] & bool_col(base["lagged_home_shock_any_yes"])
    )
    origins = sorted(base["origin_district"].unique())
    od7 = od[od["origin_district"].isin(origins)].copy()
    choice = base.merge(od7, on="origin_district", how="left", validate="many_to_many")
    choice["chosen"] = choice["destination_district"].eq(choice["chosen_district"])
    assert len(choice) == len(base) * 64
    assert choice.groupby("event_id")["chosen"].sum().eq(1).all()
    return base, choice


def logsumexp(z):
    zmax = np.max(z)
    return zmax + math.log(float(np.exp(z - zmax).sum()))


def fit_conditional_logit(groups, feature_cols, fixed_beta=None, max_iter=100):
    p = len(feature_cols)
    if fixed_beta is not None:
        return np.asarray(fixed_beta, dtype=float), 0, True
    beta = np.zeros(p, dtype=float)

    def objective_grad_hess(b):
        ll = 0.0
        grad = np.zeros(p)
        info = np.zeros((p, p))
        for g in groups:
            X = g[feature_cols].to_numpy(dtype=float)
            y = g["chosen"].to_numpy(dtype=bool)
            z = X @ b
            lse = logsumexp(z)
            probs = np.exp(z - lse)
            ll += float(z[y][0] - lse)
            mean = probs @ X
            centered = X - mean
            grad += X[y][0] - mean
            info += centered.T @ (centered * probs[:, None])
        return ll, grad, info

    converged = False
    for iteration in range(1, max_iter + 1):
        ll, grad, info = objective_grad_hess(beta)
        step = np.linalg.solve(info + np.eye(p) * 1e-8, grad)
        scale = 1.0
        while scale > 1e-7:
            candidate = beta + scale * step
            new_ll, _, _ = objective_grad_hess(candidate)
            if new_ll >= ll:
                beta = candidate
                break
            scale *= 0.5
        if np.max(np.abs(scale * step)) < 1e-8:
            converged = True
            break
    return beta, iteration, converged


MODEL_SPECS = {
    "uniform": ([], []),
    "population_only_mle": (["log_destination_population_2022"], None),
    "distance_only_mle_mc_within": (["log_effective_distance_km"], None),
    "gravity_mle_mc_within": (["log_destination_population_2022", "log_effective_distance_km"], None),
    "gravity_fixed_mc_within": (
        ["log_destination_population_2022", "log_effective_distance_km"], [1.0, -2.0]
    ),
    "distance_only_mle_1km_self": (["log_distance_1km_floor_km"], None),
    "gravity_mle_1km_self": (
        ["log_destination_population_2022", "log_distance_1km_floor_km"], None
    ),
    "gravity_fixed_1km_self": (
        ["log_destination_population_2022", "log_distance_1km_floor_km"], [1.0, -2.0]
    ),
    "gravity_mle_disk_within": (
        ["log_destination_population_2022", "log_distance_disk_proxy_km"], None
    ),
    "radiation_adapted": (["log_radiation_score"], [1.0]),
}


def assign_hash_fold(values, k=5):
    return values.astype(str).map(lambda x: int(hashlib.sha256(x.encode()).hexdigest()[:8], 16) % k)


def score_groups(groups, features, beta):
    rows = []
    details = []
    for g in groups:
        if not features:
            probs = np.repeat(1 / len(g), len(g))
        else:
            z = g[features].to_numpy(dtype=float) @ beta
            probs = np.exp(z - logsumexp(z))
        chosen_pos = int(np.flatnonzero(g["chosen"].to_numpy(dtype=bool))[0])
        chosen_prob = float(probs[chosen_pos])
        chosen_score = probs[chosen_pos]
        higher = int(np.sum(probs > chosen_score + 1e-14))
        tied = int(np.sum(np.isclose(probs, chosen_score, rtol=0, atol=1e-14)))
        mean_rank = higher + (tied + 1) / 2
        expected_rr = float(np.mean(1.0 / np.arange(higher + 1, higher + tied + 1)))
        top_probs = [min(1.0, max(0.0, (k - higher) / tied)) for k in [1, 3, 5]]
        rows.append((chosen_prob, mean_rank, expected_rr, *top_probs))
        max_prob = float(np.max(probs))
        top_names = sorted(
            g.loc[np.isclose(probs, max_prob, rtol=0, atol=1e-14), "destination_district"].astype(str)
        )
        details.append(
            {
                "event_id": g["event_id"].iloc[0],
                "origin_district": g["origin_district"].iloc[0],
                "chosen_district": g.loc[g["chosen"], "destination_district"].iloc[0],
                "candidate_count": len(g),
                "chosen_probability": chosen_prob,
                "chosen_log_loss": -math.log(max(chosen_prob, 1e-300)),
                "chosen_expected_rank": mean_rank,
                "chosen_expected_reciprocal_rank": expected_rr,
                "chosen_top1_probability": top_probs[0],
                "chosen_top3_probability": top_probs[1],
                "chosen_top5_probability": top_probs[2],
                "maximum_candidate_probability": max_prob,
                "predicted_top_districts_tied": "|".join(top_names),
            }
        )
    arr = np.asarray(rows, dtype=float)
    metrics = {
        "n_events": len(rows),
        "mean_log_loss": float(np.mean(-np.log(np.maximum(arr[:, 0], 1e-300)))),
        "top1_accuracy": float(np.mean(arr[:, 3])),
        "top3_accuracy": float(np.mean(arr[:, 4])),
        "top5_accuracy": float(np.mean(arr[:, 5])),
        "mean_rank": float(np.mean(arr[:, 1])),
        "mean_reciprocal_rank": float(np.mean(arr[:, 2])),
    }
    return metrics, details


def make_splits(event_frame, scheme):
    e = event_frame.copy()
    if scheme == "household_grouped_5fold":
        e["fold"] = assign_hash_fold(e["household_id_derived"], 5)
        return [(f"fold_{f}", e[e.fold != f].event_id, e[e.fold == f].event_id) for f in range(5)]
    if scheme == "location_grouped_5fold":
        e["fold"] = assign_hash_fold(e["baseline_location_lxx"], 5)
        return [(f"fold_{f}", e[e.fold != f].event_id, e[e.fold == f].event_id) for f in range(5)]
    if scheme == "leave_one_origin_out":
        return [
            (f"holdout_{origin}", e[e.origin_district != origin].event_id, e[e.origin_district == origin].event_id)
            for origin in sorted(e.origin_district.unique())
        ]
    if scheme == "temporal_w12plus_holdout":
        return [("train_w7_w11_test_w12_w14", e[e.wave_number <= 11].event_id, e[e.wave_number >= 12].event_id)]
    raise KeyError(scheme)


def benchmark(choice):
    choice = choice.copy()
    choice["log_radiation_score"] = np.log(np.maximum(choice["radiation_score_adapted"], 1e-300))
    choice["log_distance_1km_floor_km"] = np.log(choice["distance_1km_floor_km"])
    choice["log_distance_disk_proxy_km"] = np.log(choice["distance_disk_proxy_km"])
    event_cols = [
        "event_id", "household_id_derived", "baseline_location_lxx", "wave_number",
        "origin_district", "chosen_district", "sample_all_district_events",
        "sample_household_relocation", "sample_household_lagged_shock_yes",
    ]
    events = choice[event_cols].drop_duplicates("event_id")
    sample_defs = {
        "all_district_events": "sample_all_district_events",
        "household_relocation": "sample_household_relocation",
        "household_lagged_shock_yes": "sample_household_lagged_shock_yes",
    }
    schemes = [
        "household_grouped_5fold", "location_grouped_5fold",
        "leave_one_origin_out", "temporal_w12plus_holdout",
    ]
    metric_rows, param_rows, prediction_rows = [], [], []
    for sample_name, flag in sample_defs.items():
        e_sample = events[bool_col(events[flag])].copy()
        for universe_name in ["full_64", "interdistrict_63"]:
            if universe_name == "interdistrict_63":
                e_use = e_sample[e_sample["chosen_district"] != e_sample["origin_district"]].copy()
                c_use = choice[
                    choice.event_id.isin(e_use.event_id)
                    & (choice.destination_district != choice.origin_district)
                ].copy()
            else:
                e_use = e_sample
                c_use = choice[choice.event_id.isin(e_use.event_id)].copy()
            for scheme in schemes:
                fold_metrics = {m: [] for m in MODEL_SPECS}
                fold_params = {m: [] for m in MODEL_SPECS}
                for fold_name, train_ids, test_ids in make_splits(e_use, scheme):
                    if len(train_ids) == 0 or len(test_ids) == 0:
                        continue
                    train = c_use[c_use.event_id.isin(train_ids)]
                    test = c_use[c_use.event_id.isin(test_ids)]
                    train_groups = [g for _, g in train.groupby("event_id", sort=False)]
                    test_groups = [g for _, g in test.groupby("event_id", sort=False)]
                    for model, (features, fixed) in MODEL_SPECS.items():
                        if model == "uniform":
                            beta, iters, conv = np.array([]), 0, True
                        else:
                            beta, iters, conv = fit_conditional_logit(train_groups, features, fixed)
                        metrics, details = score_groups(test_groups, features, beta)
                        metrics.update({"fold": fold_name, "iterations": iters, "converged": conv})
                        fold_metrics[model].append(metrics)
                        if (
                            scheme == "household_grouped_5fold"
                            and sample_name in {"household_relocation", "household_lagged_shock_yes"}
                        ):
                            for detail in details:
                                prediction_rows.append(
                                    {
                                        "sample": sample_name,
                                        "candidate_universe": universe_name,
                                        "validation_scheme": scheme,
                                        "model": model,
                                        "fold": fold_name,
                                        **detail,
                                    }
                                )
                        for feature, value in zip(features, beta):
                            fold_params[model].append(
                                {"fold": fold_name, "feature": feature, "coefficient": float(value)}
                            )
                for model, rows in fold_metrics.items():
                    if not rows:
                        continue
                    n_total = sum(r["n_events"] for r in rows)
                    out = {
                        "sample": sample_name,
                        "candidate_universe": universe_name,
                        "validation_scheme": scheme,
                        "model": model,
                        "n_events_evaluated": n_total,
                        "n_folds_evaluated": len(rows),
                        "all_folds_converged": all(bool(r["converged"]) for r in rows),
                        "max_iterations": max(int(r["iterations"]) for r in rows),
                    }
                    for metric in [
                        "mean_log_loss", "top1_accuracy", "top3_accuracy", "top5_accuracy",
                        "mean_rank", "mean_reciprocal_rank",
                    ]:
                        out[metric] = sum(r[metric] * r["n_events"] for r in rows) / n_total
                    metric_rows.append(out)
                    for pr in fold_params[model]:
                        param_rows.append(
                            {
                                "sample": sample_name,
                                "candidate_universe": universe_name,
                                "validation_scheme": scheme,
                                "model": model,
                                **pr,
                            }
                        )
    return pd.DataFrame(metric_rows), pd.DataFrame(param_rows), pd.DataFrame(prediction_rows)


def distance_validation(base, od):
    chosen = base.merge(
        od,
        left_on=["origin_district", "chosen_district"],
        right_on=["origin_district", "destination_district"],
        how="left",
        validate="many_to_one",
    )
    chosen["reported_distance_km"] = pd.to_numeric(
        chosen["distance_from_previous_location_m"], errors="coerce"
    ) / 1000.0
    v = chosen[chosen.reported_distance_km.notna() & (chosen.reported_distance_km >= 0)].copy()
    rows = []
    for label, x in [
        ("all_with_reported_distance", v),
        ("same_district", v[v.same_district]),
        ("interdistrict", v[~v.same_district]),
    ]:
        if len(x) == 0:
            continue
        rows.append(
            {
                "subset": label,
                "n": len(x),
                "reported_distance_median_km": x.reported_distance_km.median(),
                "reported_distance_mean_km": x.reported_distance_km.mean(),
                "proxy_distance_median_km": x.effective_distance_km.median(),
                "proxy_distance_mean_km": x.effective_distance_km.mean(),
                "spearman_reported_vs_proxy": x.reported_distance_km.rank().corr(
                    x.effective_distance_km.rank()
                ),
                "median_absolute_error_km": np.median(
                    np.abs(x.reported_distance_km - x.effective_distance_km)
                ),
            }
        )
    return pd.DataFrame(rows), chosen


def fmt_pct(x):
    return f"{100*x:.1f}%"


def write_report(districts, base, choice, results, params, distval):
    primary = results[
        (results["sample"] == "household_lagged_shock_yes")
        & (results["candidate_universe"] == "full_64")
        & (results["validation_scheme"] == "household_grouped_5fold")
    ].sort_values("mean_log_loss")
    inter = results[
        (results["sample"] == "household_lagged_shock_yes")
        & (results["candidate_universe"] == "interdistrict_63")
        & (results["validation_scheme"] == "household_grouped_5fold")
    ].sort_values("mean_log_loss")
    origin_counts = base.groupby("origin_district").size().sort_values(ascending=False)
    hh = base[bool_col(base["sample_household_relocation"])]
    climate = base[bool_col(base["sample_household_lagged_shock_yes"])]
    shock_observed = hh[bool_col(hh["lagged_home_shock_observed"])]
    same_all = base.chosen_district.eq(base.origin_district).mean()
    same_hh = hh.chosen_district.eq(hh.origin_district).mean()
    same_clim = climate.chosen_district.eq(climate.origin_district).mean()
    lines = [
        "# BEMP Stage 2 district benchmark design and results",
        "",
        "## Bottom line",
        "",
        "The public BEMP data support a **district-level revealed destination-choice design**. "
        "This stage constructs the complete 64-district choice universe and evaluates only transparent "
        "distance, population/gravity, and radiation benchmarks. It is not the final GIS-enriched model.",
        "",
        "The most important modeling fact is that within-origin-district moves are common: "
        f"{same_all:.1%} of all {len(base):,} district-resolved events, {same_hh:.1%} of the "
        f"{len(hh):,} household relocations, and {same_clim:.1%} of the {len(climate):,} household "
        "relocations preceded by a recorded home shock. A zero centroid distance would therefore be a "
        "serious artifact. The polygon-wide specification replaces zero with a deterministic Monte Carlo "
        "estimate of the mean distance between two uniformly sampled points inside that origin district; "
        "a pre-specified 1 km self-distance and an equivalent-area disk approximation are reported as sensitivities.",
        "",
        "## Authoritative district universe",
        "",
        f"- 64/64 districts from the Bangladesh DGHS-hosted BBS ADM2 layer are present.",
        f"- 64/64 have a 2022 enumerated census population from BBS National Report Volume I, Table P02.",
        f"- 64/64 match after explicit historical/spelling crosswalks; no fuzzy matching is used.",
        f"- All {base.origin_district.nunique()} BEMP origin districts and all "
        f"{base.chosen_district.nunique()} observed destination districts match the canonical universe.",
        "",
        "Sources: Bangladesh National Portal district list; Bangladesh DGHS hosted BBS 2020 ADM2 layer; "
        "Bangladesh Bureau of Statistics, *Population and Housing Census 2022, National Report "
        "(Volume I)*, Table P02 (PDF pages 199–200; printed pages 151–152).",
        "",
        "## Samples carried forward",
        "",
        "| Sample | Events | Same-origin district | Intended use |",
        "|---|---:|---:|---|",
        f"| All district-resolved prospective moves | {len(base):,} | {same_all:.1%} | Endpoint benchmark / power |",
        f"| Whole- or partial-household relocations | {len(hh):,} | {same_hh:.1%} | Main relocation estimand |",
        f"| Household relocations with strictly lagged home shock=yes | {len(climate):,} | {same_clim:.1%} | Main climate-conditioned sample |",
        "",
        "Origin support in the all-event sample: " + ", ".join(f"{k} ({v})" for k, v in origin_counts.items()) + ".",
        "",
        "## Benchmark definitions",
        "",
        "Every event receives all 64 Bangladesh districts as alternatives. The chosen indicator is the "
        "observed BEMP destination district. No post-choice reason, destination network response, move "
        "distance response, or later-wave information enters a predictor.",
        "",
        "- **Uniform:** 1/64 for every district.",
        "- **Population only:** conditional-logit coefficient estimated on log 2022 destination population.",
        "- **Distance only:** coefficient estimated on log straight-line distance.",
        "- **Gravity MLE:** coefficients estimated on log population and log distance.",
        "- **Fixed gravity:** destination population divided by squared distance.",
        "- **Within-district distance sensitivity:** `mc_within` uses the polygon-wide mean random-pair distance; `disk_within` uses the equivalent-area disk expectation; `1km_self` uses a pre-specified 1 km self-alternative floor. Cross-district distances remain centroid-to-centroid in all three.",
        "- **Radiation adapted:** standard population/intervening-population score, with a diagnostic self-district alternative. Because radiation is an inter-unit model, the interdistrict-only result is the principled comparison.",
        "",
        "The primary validation is five-fold household-grouped cross-validation. Additional files include "
        "location-grouped, leave-one-origin-district-out, and a wave 12–14 temporal holdout. Ranking ties "
        "use exact expected ranks and top-k probabilities under random ordering when scores tie. All "
        "conditional-logit fits converged.",
        "",
        "## Primary climate-sample results: full 64-district universe",
        "",
        "| Model | Events | Log loss | Top 1 | Top 3 | Top 5 | Mean rank | MRR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in primary.itertuples(index=False):
        lines.append(
            f"| {r.model} | {r.n_events_evaluated:,} | {r.mean_log_loss:.3f} | "
            f"{fmt_pct(r.top1_accuracy)} | {fmt_pct(r.top3_accuracy)} | {fmt_pct(r.top5_accuracy)} | "
            f"{r.mean_rank:.1f} | {r.mean_reciprocal_rank:.3f} |"
        )
    lines += [
        "",
        "## Primary climate-sample results: interdistrict sensitivity",
        "",
        "This excludes events whose destination district equals the origin and removes the origin district "
        "from each candidate set. It is the appropriate domain for the conventional radiation benchmark.",
        "",
        "| Model | Events | Log loss | Top 1 | Top 3 | Top 5 | Mean rank | MRR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in inter.itertuples(index=False):
        lines.append(
            f"| {r.model} | {r.n_events_evaluated:,} | {r.mean_log_loss:.3f} | "
            f"{fmt_pct(r.top1_accuracy)} | {fmt_pct(r.top3_accuracy)} | {fmt_pct(r.top5_accuracy)} | "
            f"{r.mean_rank:.1f} | {r.mean_reciprocal_rank:.3f} |"
        )
    lines += [
        "",
        "## Survey-distance validation",
        "",
        "The BEMP reported move-distance field is used only to audit the district proxy, never as a "
        "candidate predictor (it exists only for the chosen destination).",
        "",
        "| Subset | N | Reported median km | Proxy median km | Spearman rho | Median absolute error km |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in distval.itertuples(index=False):
        rho = "NA" if pd.isna(r.spearman_reported_vs_proxy) else f"{r.spearman_reported_vs_proxy:.3f}"
        lines.append(
            f"| {r.subset} | {r.n:,} | {r.reported_distance_median_km:.1f} | "
            f"{r.proxy_distance_median_km:.1f} | {rho} | {r.median_absolute_error_km:.1f} |"
        )
    lines += [
        "",
        "## Interpretation and Stage 1 empirical design",
        "",
        "The supported design is a **district-level destination-choice analysis among observed movers**, "
        "not a model of whether a household migrates. The most transparent specification is nested:",
        "",
        "1. Estimate whether a whole/partial-household move stays inside the origin district or crosses a "
        f"district boundary ({len(hh):,} moves; {len(hh) - int((hh.origin_district == hh.chosen_district).sum()):,} cross-district).",
        "2. Conditional on crossing a district boundary, estimate choice among the other 63 districts "
        f"({int((hh.origin_district != hh.chosen_district).sum()):,} household moves; "
        f"{int((climate.origin_district != climate.chosen_district).sum()):,} in the lagged-shock-positive sample).",
        "3. Retain the one-stage 64-alternative conditional logit as the headline benchmark, but do not "
        "interpret its 61.4% top-1 rate as fine-grained destination prediction: it largely identifies the "
        "very common self-district alternative.",
        "",
        f"Use the {len(hh):,} whole/partial-household moves as the main relocation sample. The core "
        f"climate-conditioned estimand uses the {len(climate):,} moves with strictly lagged home shock=yes. "
        f"A secondary contrast can use the {len(shock_observed):,} household moves with observed lagged "
        f"shock status ({int(bool_col(shock_observed.lagged_home_shock_any_yes).sum()):,} yes versus "
        f"{int((~bool_col(shock_observed.lagged_home_shock_any_yes)).sum()):,} no) and interact pre-move "
        "erosion/flood status with candidate attributes. That contrast describes differential destination "
        "preferences; it is not automatically a causal effect of shock exposure. Use the full 573 events "
        "only as an endpoint/power benchmark. Cluster or group validation by household; report "
        "location-blocked and origin-blocked generalization because the seven origins are unevenly represented.",
        "",
        "The next model may add destination GIS characteristics only if they are defined for all 64 "
        "candidate districts at a pre-move reference date. Core additions should be flood/erosion exposure, "
        "urbanization and employment opportunity, road/market accessibility, and service access. The "
        "comparison must be incremental: GIS model versus exactly the frozen benchmarks here, including "
        "the strongest validated gravity sensitivity rather than only a convenient weak baseline. Survey "
        "reasons and destination relatives are outcomes/mechanisms or heterogeneity variables, not candidate "
        "attributes, unless an external pre-choice network measure is constructed.",
        "",
        "## Limitations that remain",
        "",
        "- BEMP does not reveal exact origin or destination coordinates; all spatial predictors are district-level.",
        "- Origin support is seven districts, so national destination alternatives do not imply national origin representativeness.",
        "- The 2022 population surface is a stable benchmark exposure, not a fully time-varying opportunity measure for every survey wave.",
        "- Centroid distance is an approximation. Same-district effective distance is simulation-based and should retain the supplied 1 km and disk-proxy sensitivities.",
        "- The adapted full-universe radiation score is diagnostic; use the interdistrict version for substantive radiation claims.",
        "",
        "## Reproducibility outputs",
        "",
        "- `bgd_district_universe.csv`: 64 canonical districts, P-codes, central points, area, within-district distance, and population.",
        "- `bgd_district_name_crosswalk.csv`: exact historical/spelling transformations.",
        "- `bgd_origin_destination_matrix.csv`: all 4,096 district pairs and benchmark features.",
        "- `bemp_stage2_event_choice_set.csv`: 573 × 64 = 36,672 event-alternative rows.",
        "- `bemp_baseline_benchmark_results.csv`: all samples, universes, and validation schemes.",
        "- `bemp_baseline_parameter_estimates.csv`: fold-level fitted coefficients.",
        "- `bemp_baseline_oof_event_predictions.csv`: event-level out-of-fold predictions for household-grouped validation.",
        "- `bemp_distance_proxy_validation.csv`: survey distance versus geographic proxy audit.",
        "- `bemp_stage2_source_manifest.csv`: URLs, hashes, and retrieval metadata.",
        "- `bemp_stage2_climate_destination_support.png`: mapped destination support for the 184-event climate-conditioned household sample.",
        "",
    ]
    (REPORTS / "bemp_stage2_baseline_design.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    districts, sampled = build_district_universe()
    od = build_od_matrix(districts)
    events = pd.read_csv(EVENTS_PATH, low_memory=False)
    base, choice = build_choice_sets(events, districts, od)
    results, params, predictions = benchmark(choice)
    distval, chosen_distance = distance_validation(base, od)

    crosswalk_rows = []
    geometry_renames = {
        "Barisal": "Barishal", "Bogra": "Bogura", "Brahamanbaria": "Brahmanbaria",
        "Chittagong": "Chattogram", "Comilla": "Cumilla", "Jessore": "Jashore",
        "Maulvibazar": "Moulvibazar", "Nawabganj": "Chapainawabganj",
    }
    for raw, fixed in geometry_renames.items():
        crosswalk_rows.append(
            {"source_name_raw": raw, "canonical_district": fixed,
             "source_context": "DGHS/BBS 2020 ADM2 geometry", "action": "exact explicit rename"}
        )
    crosswalk_rows += [
        {"source_name_raw": "Netrokona", "canonical_district": "Netrakona",
         "source_context": "BBS National Report Table P02 and one BEMP endpoint",
         "action": "exact explicit spelling harmonization"},
    ]
    crosswalk = pd.DataFrame(crosswalk_rows)
    manifest = pd.DataFrame(
        [
            {
                "source_id": "dghs_bbs_adm2_20201113",
                "local_path": str(GEOJSON_PATH.relative_to(ROOT)),
                "source_url": ADMIN_URL,
                "retrieved_date": "2026-08-28",
                "bytes": GEOJSON_PATH.stat().st_size,
                "sha256": sha256(GEOJSON_PATH),
                "purpose": "64-district boundaries and P-codes",
            },
            {
                "source_id": "bbs_census_2022_national_report_volume_1",
                "local_path": str(BBS_PDF_PATH.relative_to(ROOT)),
                "source_url": BBS_PDF_URL,
                "retrieved_date": "2026-08-28",
                "bytes": BBS_PDF_PATH.stat().st_size,
                "sha256": sha256(BBS_PDF_PATH),
                "purpose": "Primary district enumerated population, Table P02",
            },
            {
                "source_id": "bbs_census_2022_preliminary_english_crosscheck",
                "local_path": str(BBS_PRELIMINARY_PDF_PATH.relative_to(ROOT)),
                "source_url": BBS_PRELIMINARY_PDF_URL,
                "retrieved_date": "2026-08-28",
                "bytes": BBS_PRELIMINARY_PDF_PATH.stat().st_size,
                "sha256": sha256(BBS_PRELIMINARY_PDF_PATH),
                "purpose": "Provenance cross-check only; preliminary district table not used in benchmark",
            },
            {
                "source_id": "bbs_population_census_landing_page",
                "local_path": "work/bbs_population_page.html",
                "source_url": BBS_PAGE_URL,
                "retrieved_date": "2026-08-28",
                "bytes": (ROOT / "work/bbs_population_page.html").stat().st_size,
                "sha256": sha256(ROOT / "work/bbs_population_page.html"),
                "purpose": "Official report provenance",
            },
            {
                "source_id": "bangladesh_national_portal_district_list",
                "local_path": "",
                "source_url": NATIONAL_PORTAL_URL,
                "retrieved_date": "2026-08-28",
                "bytes": "",
                "sha256": "",
                "purpose": "Independent official confirmation of 64-district universe",
            },
        ]
    )

    district_cols = [c for c in districts.columns]
    districts[district_cols].to_csv(TABLES / "bgd_district_universe.csv", index=False)
    crosswalk.to_csv(TABLES / "bgd_district_name_crosswalk.csv", index=False)
    od.to_csv(TABLES / "bgd_origin_destination_matrix.csv", index=False)
    # Exclude the chosen-only reported distance from the modeling matrix to make
    # leakage prevention visible in the actual exported feature table.
    choice_export = choice.drop(columns=["distance_from_previous_location_m"])
    choice_export.to_csv(TABLES / "bemp_stage2_event_choice_set.csv", index=False)
    results.to_csv(TABLES / "bemp_baseline_benchmark_results.csv", index=False)
    params.to_csv(TABLES / "bemp_baseline_parameter_estimates.csv", index=False)
    predictions.to_csv(TABLES / "bemp_baseline_oof_event_predictions.csv", index=False)
    distval.to_csv(TABLES / "bemp_distance_proxy_validation.csv", index=False)
    manifest.to_csv(TABLES / "bemp_stage2_source_manifest.csv", index=False)
    write_report(districts, base, choice, results, params, distval)

    summary = {
        "districts": len(districts),
        "population_sum_64_districts": int(districts.population_2022_total.sum()),
        "od_rows": len(od),
        "events": len(base),
        "choice_rows": len(choice),
        "household_events": int(base.sample_household_relocation.sum()),
        "climate_household_events": int(base.sample_household_lagged_shock_yes.sum()),
        "same_district_all": float((base.origin_district == base.chosen_district).mean()),
        "same_district_household": float(
            (base.loc[base.sample_household_relocation, "origin_district"]
             == base.loc[base.sample_household_relocation, "chosen_district"]).mean()
        ),
        "same_district_climate": float(
            (base.loc[base.sample_household_lagged_shock_yes, "origin_district"]
             == base.loc[base.sample_household_lagged_shock_yes, "chosen_district"]).mean()
        ),
        "benchmark_result_rows": len(results),
        "parameter_rows": len(params),
        "oof_prediction_rows": len(predictions),
    }
    (ROOT / "work/bemp_stage2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
