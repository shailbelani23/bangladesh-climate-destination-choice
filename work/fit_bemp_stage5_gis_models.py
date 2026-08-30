#!/usr/bin/env python3
"""Fit the pre-registered low-dimensional BEMP district GIS choice models.

Design principles:
- alternatives are the frozen 64 Bangladesh districts;
- GIS variables are the frozen Stage-4 table, never post-choice survey answers;
- all validation splits are grouped outside model fitting;
- GIS standardization and ridge selection occur inside the outer training fold;
- the exact Stage-2 gravity comparator must be reproduced;
- a sequential nested model separates stay/cross from the cross-district choice.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
CHOICE_PATH = TABLES / "bemp_stage2_event_choice_set.csv"
GIS_PATH = TABLES / "bemp_stage4_district_gis_features.csv"

GIS_RAW = [
    "gfd_ever_flooded_land_share_2000_2018",
    "ghsl_built_surface_share_2020",
    "travel_time_city_ge_50k_median_2015",
    "worldcover_cropland_share_2020",
]
GIS_Z = ["z_gfd_flood", "z_ghsl_built", "z_access_time", "z_cropland"]
BASE_FEATURES = ["log_destination_population_2022", "log_distance_disk_proxy_km"]
LAMBDAS = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]


def bool_col(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().eq("true")


def hash_fold(value, k: int) -> int:
    return int(hashlib.sha256(str(value).encode()).hexdigest()[:8], 16) % k


def logsumexp_rows(z: np.ndarray) -> np.ndarray:
    zmax = np.max(z, axis=1, keepdims=True)
    return zmax[:, 0] + np.log(np.exp(z - zmax).sum(axis=1))


def prepare_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    choice = pd.read_csv(CHOICE_PATH, low_memory=False)
    gis = pd.read_csv(GIS_PATH)
    keep = ["district_pcode", "district"] + GIS_RAW
    choice = choice.merge(
        gis[keep], left_on="destination_pcode", right_on="district_pcode",
        how="left", validate="many_to_one", suffixes=("", "_gis"),
    )
    choice["log_distance_disk_proxy_km"] = np.log(choice["distance_disk_proxy_km"])
    choice["log_radiation_score"] = np.log(np.maximum(choice["radiation_score_adapted"], 1e-300))
    choice["shock_any"] = bool_col(choice["lagged_home_shock_any_yes"]).astype(int)
    choice["shock_observed"] = bool_col(choice["lagged_home_shock_observed"])
    choice["cross_district_event"] = choice["chosen_district"] != choice["origin_district"]
    choice["sample_household_lagged_shock_observed"] = (
        bool_col(choice["sample_household_relocation"]) & choice["shock_observed"]
    )
    if choice[GIS_RAW].isna().any().any():
        raise RuntimeError("GIS join produced missing candidate attributes")
    if len(choice) != 573 * 64 or choice.event_id.nunique() != 573:
        raise RuntimeError("Model-ready choice set is not 573 x 64")
    if not choice.groupby("event_id")["chosen"].sum().eq(1).all():
        raise RuntimeError("Every event must have exactly one chosen district")

    event_cols = [
        "event_id", "respondent_id", "household_id_derived", "baseline_location_lxx",
        "wave", "wave_number", "origin_district", "chosen_district",
        "sample_household_relocation", "sample_household_lagged_shock_yes",
        "sample_household_lagged_shock_observed", "shock_any", "shock_observed",
        "cross_district_event",
    ]
    events = choice[event_cols].drop_duplicates("event_id").reset_index(drop=True)
    choice.to_csv(TABLES / "bemp_stage5_model_ready_choice_set.csv", index=False)
    return choice, events


def scale_gis(train: pd.DataFrame, frames: list[pd.DataFrame]) -> tuple[list[pd.DataFrame], dict]:
    # The candidate universe is static and complete in every training event. Using
    # unique P-codes avoids weighting districts by the number of training events.
    unique = train[["destination_pcode"] + GIS_RAW].drop_duplicates("destination_pcode")
    means = unique[GIS_RAW].mean()
    sds = unique[GIS_RAW].std(ddof=0)
    if (sds <= 0).any() or unique.destination_pcode.nunique() != 64:
        raise RuntimeError("Cannot standardize GIS attributes over the 64-district training universe")
    out = []
    for frame in frames:
        x = frame.copy()
        for raw, z in zip(GIS_RAW, GIS_Z):
            x[z] = (x[raw] - means[raw]) / sds[raw]
        x["shock_x_z_gfd_flood"] = x["shock_any"] * x["z_gfd_flood"]
        x["shock_x_z_access_time"] = x["shock_any"] * x["z_access_time"]
        out.append(x)
    scaling = {f"mean__{c}": float(means[c]) for c in GIS_RAW}
    scaling.update({f"sd__{c}": float(sds[c]) for c in GIS_RAW})
    return out, scaling


def arrays(frame: pd.DataFrame, features: list[str]):
    groups = []
    metas = []
    for event_id, g in frame.groupby("event_id", sort=False):
        g = g.sort_values("destination_district").reset_index(drop=True)
        y = np.flatnonzero(bool_col(g["chosen"]).to_numpy())
        if len(y) != 1:
            raise RuntimeError(f"Event {event_id} has {len(y)} chosen alternatives")
        groups.append((g[features].to_numpy(dtype=float), int(y[0]), g))
        metas.append(event_id)
    if not groups:
        return np.empty((0, 0, len(features))), np.empty(0, dtype=int), [], []
    counts = {len(x[2]) for x in groups}
    if len(counts) != 1:
        raise RuntimeError(f"Candidate counts differ within array: {counts}")
    X = np.stack([x[0] for x in groups])
    y = np.asarray([x[1] for x in groups], dtype=int)
    gframes = [x[2] for x in groups]
    return X, y, metas, gframes


def cond_objective(X, y, beta, ridge_lambda=0.0, penalty_mask=None):
    n, j, p = X.shape
    z = np.einsum("ijp,p->ij", X, beta)
    lse = logsumexp_rows(z)
    probs = np.exp(z - lse[:, None])
    chosen = X[np.arange(n), y]
    means = np.einsum("ij,ijp->ip", probs, X)
    centered = X - means[:, None, :]
    ll = float((z[np.arange(n), y] - lse).sum())
    grad = (chosen - means).sum(axis=0)
    info = np.einsum("ij,ijp,ijq->pq", probs, centered, centered)
    if penalty_mask is None:
        penalty_mask = np.zeros(p)
    ll -= 0.5 * ridge_lambda * float(np.sum(penalty_mask * beta**2))
    grad -= ridge_lambda * penalty_mask * beta
    info += ridge_lambda * np.diag(penalty_mask)
    return ll, grad, info


def fit_conditional(X, y, ridge_lambda=0.0, penalty_mask=None, max_iter=150):
    p = X.shape[2]
    beta = np.zeros(p)
    converged = False
    for iteration in range(1, max_iter + 1):
        ll, grad, info = cond_objective(X, y, beta, ridge_lambda, penalty_mask)
        step = np.linalg.solve(info + np.eye(p) * 1e-9, grad)
        scale = 1.0
        while scale > 1e-8:
            candidate = beta + scale * step
            new_ll, _, _ = cond_objective(X, y, candidate, ridge_lambda, penalty_mask)
            if new_ll >= ll - 1e-12:
                beta = candidate
                break
            scale *= 0.5
        if np.max(np.abs(scale * step)) < 1e-8:
            converged = True
            break
    return beta, iteration, converged


def probabilities(X, beta):
    z = np.einsum("ijp,p->ij", X, beta)
    return np.exp(z - logsumexp_rows(z)[:, None])


def score_probability_arrays(probs, y, event_ids, gframes):
    metric_rows, details = [], []
    for i, (event_id, g) in enumerate(zip(event_ids, gframes)):
        p = probs[i]
        yi = y[i]
        chosen_prob = float(p[yi])
        higher = int(np.sum(p > chosen_prob + 1e-14))
        tied = int(np.sum(np.isclose(p, chosen_prob, atol=1e-14, rtol=0)))
        rank = higher + (tied + 1) / 2
        rr = float(np.mean(1 / np.arange(higher + 1, higher + tied + 1)))
        top = [min(1.0, max(0.0, (k - higher) / tied)) for k in [1, 3, 5]]
        loss = -math.log(max(chosen_prob, 1e-300))
        metric_rows.append([loss, rank, rr, *top])
        maxp = float(p.max())
        top_names = sorted(g.loc[np.isclose(p, maxp, atol=1e-14, rtol=0), "destination_district"])
        details.append({
            "event_id": event_id,
            "household_id_derived": g.household_id_derived.iloc[0],
            "origin_district": g.origin_district.iloc[0],
            "chosen_district": g.loc[g.chosen, "destination_district"].iloc[0],
            "candidate_count": len(g), "chosen_probability": chosen_prob,
            "chosen_log_loss": loss, "chosen_expected_rank": rank,
            "chosen_expected_reciprocal_rank": rr,
            "chosen_top1_probability": top[0], "chosen_top3_probability": top[1],
            "chosen_top5_probability": top[2], "maximum_candidate_probability": maxp,
            "predicted_top_districts_tied": "|".join(top_names),
            "probability_sum": float(p.sum()),
        })
    a = np.asarray(metric_rows)
    metrics = {
        "n_events": len(a), "mean_log_loss": float(a[:, 0].mean()),
        "mean_rank": float(a[:, 1].mean()), "mean_reciprocal_rank": float(a[:, 2].mean()),
        "top1_accuracy": float(a[:, 3].mean()), "top3_accuracy": float(a[:, 4].mean()),
        "top5_accuracy": float(a[:, 5].mean()),
    }
    return metrics, details


def fit_logistic(x, y, max_iter=100):
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(2)
    converged = False
    for iteration in range(1, max_iter + 1):
        z = np.clip(X @ beta, -35, 35)
        p = 1 / (1 + np.exp(-z))
        grad = X.T @ (y - p)
        info = X.T @ ((p * (1 - p))[:, None] * X)
        step = np.linalg.solve(info + np.eye(2) * 1e-8, grad)
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            converged = True
            break
    return beta, iteration, converged


def auc_score(y, p):
    y = np.asarray(y, dtype=int)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = pd.Series(p).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def make_splits(event_frame: pd.DataFrame, scheme: str):
    e = event_frame.copy()
    if scheme == "household_grouped_5fold":
        e["fold"] = e.household_id_derived.map(lambda x: hash_fold(x, 5))
        return [(f"fold_{k}", e[e.fold != k].event_id.tolist(), e[e.fold == k].event_id.tolist()) for k in range(5)]
    if scheme == "location_grouped_5fold":
        e["fold"] = e.baseline_location_lxx.map(lambda x: hash_fold(x, 5))
        return [(f"fold_{k}", e[e.fold != k].event_id.tolist(), e[e.fold == k].event_id.tolist()) for k in range(5)]
    if scheme == "leave_one_origin_out":
        return [(f"holdout_{o}", e[e.origin_district != o].event_id.tolist(),
                 e[e.origin_district == o].event_id.tolist()) for o in sorted(e.origin_district.unique())]
    if scheme == "temporal_w12plus_holdout":
        return [("train_w7_w11_test_w12_w14", e[e.wave_number <= 11].event_id.tolist(),
                 e[e.wave_number >= 12].event_id.tolist())]
    raise KeyError(scheme)


def model_features(interactions=False):
    f = BASE_FEATURES + GIS_Z
    if interactions:
        f += ["shock_x_z_gfd_flood", "shock_x_z_access_time"]
    return f


def inner_tune(train_choice, train_events, universe, interactions, context, tuning_rows):
    e = train_events.copy()
    if universe == "interdistrict_63":
        e = e[bool_col(e.cross_district_event)]
    e["inner_fold"] = e.household_id_derived.map(lambda x: hash_fold(x, 4))
    features = model_features(interactions)
    penalty_mask = np.asarray([0, 0] + [1] * (len(features) - 2), dtype=float)
    losses = {lam: [] for lam in LAMBDAS}
    counts = {lam: 0 for lam in LAMBDAS}
    for k in range(4):
        train_ids = e[e.inner_fold != k].event_id
        test_ids = e[e.inner_fold == k].event_id
        if len(train_ids) == 0 or len(test_ids) == 0:
            continue
        c_train = train_choice[train_choice.event_id.isin(train_ids)].copy()
        c_test = train_choice[train_choice.event_id.isin(test_ids)].copy()
        if universe == "interdistrict_63":
            c_train = c_train[c_train.destination_district != c_train.origin_district]
            c_test = c_test[c_test.destination_district != c_test.origin_district]
        (c_train, c_test), _ = scale_gis(c_train, [c_train, c_test])
        Xtr, ytr, _, _ = arrays(c_train, features)
        Xte, yte, ids, groups = arrays(c_test, features)
        for lam in LAMBDAS:
            beta, _, _ = fit_conditional(Xtr, ytr, lam, penalty_mask)
            m, _ = score_probability_arrays(probabilities(Xte, beta), yte, ids, groups)
            losses[lam].append(m["mean_log_loss"] * m["n_events"])
            counts[lam] += m["n_events"]
    means = {lam: sum(losses[lam]) / counts[lam] for lam in LAMBDAS if counts[lam]}
    best = min(means, key=lambda lam: (means[lam], lam))
    for lam, loss in means.items():
        tuning_rows.append({**context, "candidate_lambda": lam, "inner_mean_log_loss": loss,
                            "selected": lam == best, "inner_events_scored": counts[lam]})
    return best


def fit_direct_fold(train_choice, test_choice, train_events, universe, interactions,
                    context, tuning_rows):
    if universe == "interdistrict_63":
        train_choice = train_choice[train_choice.destination_district != train_choice.origin_district]
        test_choice = test_choice[test_choice.destination_district != test_choice.origin_district]
    (train_s, test_s), scaling = scale_gis(train_choice, [train_choice, test_choice])
    output = []

    # Exact unpenalized gravity benchmark.
    Xtr, ytr, _, _ = arrays(train_s, BASE_FEATURES)
    Xte, yte, ids, groups = arrays(test_s, BASE_FEATURES)
    beta, iters, conv = fit_conditional(Xtr, ytr)
    m, details = score_probability_arrays(probabilities(Xte, beta), yte, ids, groups)
    output.append(("gravity_mle_disk_within", BASE_FEATURES, beta, 0.0, iters, conv, m, details, scaling))

    features = model_features(interactions)
    penalty_mask = np.asarray([0, 0] + [1] * (len(features) - 2), dtype=float)
    lam = inner_tune(train_choice, train_events, universe, interactions, context, tuning_rows)
    Xtr, ytr, _, _ = arrays(train_s, features)
    Xte, yte, ids, groups = arrays(test_s, features)
    beta, iters, conv = fit_conditional(Xtr, ytr, lam, penalty_mask)
    m, details = score_probability_arrays(probabilities(Xte, beta), yte, ids, groups)
    ridge_name = "gis_joint_ridge_shock_interactions" if interactions else "gis_joint_ridge"
    output.append((ridge_name, features, beta, lam, iters, conv, m, details, scaling))

    beta, iters, conv = fit_conditional(Xtr, ytr)
    m, details = score_probability_arrays(probabilities(Xte, beta), yte, ids, groups)
    unpen_name = "gis_joint_unpenalized_shock_interactions" if interactions else "gis_joint_unpenalized"
    output.append((unpen_name, features, beta, 0.0, iters, conv, m, details, scaling))

    # Fixed radiation score; only a conventional comparator interdistrict.
    Xte, yte, ids, groups = arrays(test_s, ["log_radiation_score"])
    m, details = score_probability_arrays(probabilities(Xte, np.asarray([1.0])), yte, ids, groups)
    output.append(("radiation_adapted", ["log_radiation_score"], np.asarray([1.0]), 0.0,
                   0, True, m, details, scaling))
    return output


def fit_nested_fold(train_choice, test_choice, train_events, context, tuning_rows, use_gis):
    train_cross_events = train_events[bool_col(train_events.cross_district_event)]
    cross_train = train_choice[
        train_choice.event_id.isin(train_cross_events.event_id)
        & (train_choice.destination_district != train_choice.origin_district)
    ].copy()
    (cross_s, train_s, test_s), scaling = scale_gis(cross_train, [cross_train, train_choice, test_choice])
    features = model_features(False) if use_gis else BASE_FEATURES
    if use_gis:
        lam = inner_tune(train_choice, train_events, "interdistrict_63", False,
                         {**context, "nested_component": "cross_destination"}, tuning_rows)
        penalty = np.asarray([0, 0] + [1] * 4, dtype=float)
    else:
        lam, penalty = 0.0, np.zeros(len(features))
    Xc, yc, _, _ = arrays(cross_s, features)
    beta, iters, conv = fit_conditional(Xc, yc, lam, penalty)

    def iv_and_groups(frame):
        iv, groups = [], []
        for event_id, g in frame.groupby("event_id", sort=False):
            g = g.sort_values("destination_district").reset_index(drop=True)
            u = g[features].to_numpy(float) @ beta
            self_mask = g.destination_district.eq(g.origin_district).to_numpy()
            iv.append(float(np.log(np.exp(u[~self_mask] - u[~self_mask].max()).sum())
                            + u[~self_mask].max() - u[self_mask][0]))
            groups.append((event_id, g, u, self_mask))
        return np.asarray(iv), groups

    iv_train, train_groups = iv_and_groups(train_s)
    y_cross = np.asarray([bool_col(g[1].cross_district_event).iloc[0] for g in train_groups], dtype=int)
    logit_beta, logit_iters, logit_conv = fit_logistic(iv_train, y_cross)

    iv_test, test_groups = iv_and_groups(test_s)
    p_cross = 1 / (1 + np.exp(-np.clip(logit_beta[0] + logit_beta[1] * iv_test, -35, 35)))
    probs, y, ids, gframes = [], [], [], []
    first_rows = []
    for i, (event_id, g, u, self_mask) in enumerate(test_groups):
        p = np.zeros(len(g))
        ext_u = u[~self_mask]
        ext_p = np.exp(ext_u - (np.log(np.exp(ext_u - ext_u.max()).sum()) + ext_u.max()))
        p[self_mask] = 1 - p_cross[i]
        p[~self_mask] = p_cross[i] * ext_p
        probs.append(p)
        yi = int(np.flatnonzero(bool_col(g.chosen).to_numpy())[0])
        y.append(yi); ids.append(event_id); gframes.append(g)
        yy = int(bool_col(g.cross_district_event).iloc[0])
        first_rows.append({
            "event_id": event_id, "household_id_derived": g.household_id_derived.iloc[0],
            "cross_district": yy, "predicted_cross_probability": float(p_cross[i]),
            "binary_log_loss": -math.log(max(p_cross[i] if yy else 1 - p_cross[i], 1e-300)),
            "binary_brier": float((p_cross[i] - yy) ** 2), "inclusive_value_gap": float(iv_test[i]),
        })
    m, details = score_probability_arrays(np.stack(probs), np.asarray(y), ids, gframes)
    yy = np.asarray([r["cross_district"] for r in first_rows])
    pp = np.asarray([r["predicted_cross_probability"] for r in first_rows])
    first_metrics = {
        "n_events": len(yy), "binary_mean_log_loss": float(np.mean([r["binary_log_loss"] for r in first_rows])),
        "binary_brier": float(np.mean((pp - yy) ** 2)), "binary_auc": auc_score(yy, pp),
        "logit_intercept": float(logit_beta[0]), "logit_inclusive_value_slope": float(logit_beta[1]),
        "logit_iterations": logit_iters, "logit_converged": logit_conv,
    }
    name = "nested_gis_ridge" if use_gis else "nested_gravity"
    return (name, features, beta, lam, iters, conv, m, details, scaling,
            first_metrics, first_rows, logit_beta)


def aggregate_fold_results(fold_result_rows):
    df = pd.DataFrame(fold_result_rows)
    keys = ["sample", "candidate_universe", "validation_scheme", "model"]
    rows = []
    for key, g in df.groupby(keys, sort=False):
        n = g.n_events.sum()
        row = dict(zip(keys, key))
        row.update({
            "n_events_evaluated": int(n), "n_folds_evaluated": len(g),
            "all_folds_converged": bool(g.converged.all()),
            "selected_lambda_median": float(g.ridge_lambda.median()),
            "selected_lambda_min": float(g.ridge_lambda.min()),
            "selected_lambda_max": float(g.ridge_lambda.max()),
        })
        for c in ["mean_log_loss", "top1_accuracy", "top3_accuracy", "top5_accuracy",
                  "mean_rank", "mean_reciprocal_rank"]:
            row[c] = float(np.average(g[c], weights=g.n_events))
        rows.append(row)
    out = pd.DataFrame(rows)
    baseline = out[out.model == "gravity_mle_disk_within"][
        ["sample", "candidate_universe", "validation_scheme", "mean_log_loss"]
    ].rename(columns={"mean_log_loss": "gravity_mean_log_loss"})
    out = out.merge(baseline, on=["sample", "candidate_universe", "validation_scheme"], how="left")
    out["log_loss_improvement_vs_gravity"] = out.gravity_mean_log_loss - out.mean_log_loss
    return out


def paired_comparisons(predictions, events):
    pred = predictions[predictions.validation_scheme == "household_grouped_5fold"]
    event_hh = events.set_index("event_id")["household_id_derived"]
    comparisons = [
        ("gis_joint_ridge", "gravity_mle_disk_within"),
        ("gis_joint_unpenalized", "gravity_mle_disk_within"),
        ("nested_gis_ridge", "nested_gravity"),
        ("nested_gis_ridge", "gravity_mle_disk_within"),
        ("gis_joint_ridge_shock_interactions", "gis_joint_ridge_no_interactions"),
    ]
    rows = []
    rng = np.random.default_rng(20260829)
    for (sample, universe), g in pred.groupby(["sample", "candidate_universe"]):
        for model, comparator in comparisons:
            a = g[g.model == model][["event_id", "chosen_log_loss"]].rename(columns={"chosen_log_loss": "a"})
            b = g[g.model == comparator][["event_id", "chosen_log_loss"]].rename(columns={"chosen_log_loss": "b"})
            m = a.merge(b, on="event_id")
            if m.empty:
                continue
            m["household"] = m.event_id.map(event_hh)
            h = m.groupby("household").agg(diff_sum=("b", "sum"), a_sum=("a", "sum"),
                                             b_sum=("b", "sum"), n=("event_id", "size"))
            # Correct paired difference is comparator loss minus model loss.
            event_diff = m.b - m.a
            households = h.index.to_numpy()
            boots = []
            for _ in range(5000):
                draw = rng.choice(households, size=len(households), replace=True)
                x = h.loc[draw]
                boots.append(float((x.b_sum.sum() - x.a_sum.sum()) / x.n.sum()))
            rows.append({
                "sample": sample, "candidate_universe": universe, "model": model,
                "comparator": comparator, "n_events": len(m), "n_households": m.household.nunique(),
                "mean_log_loss_improvement": float(event_diff.mean()),
                "cluster_bootstrap_ci_low": float(np.quantile(boots, .025)),
                "cluster_bootstrap_ci_high": float(np.quantile(boots, .975)),
                "share_events_model_lower_loss": float((event_diff > 0).mean()),
                "bootstrap_replicates": 5000,
            })
    return pd.DataFrame(rows)


def main():
    choice, events = prepare_data()
    sample_defs = {
        "household_relocation": "sample_household_relocation",
        "household_lagged_shock_yes": "sample_household_lagged_shock_yes",
    }
    schemes = ["household_grouped_5fold", "location_grouped_5fold",
               "leave_one_origin_out", "temporal_w12plus_holdout"]
    fold_results, params, predictions, tuning_rows, first_results, first_predictions, split_rows = ([] for _ in range(7))

    for sample, flag in sample_defs.items():
        e = events[bool_col(events[flag])].copy()
        for scheme in schemes:
            for fold, train_ids, test_ids in make_splits(e, scheme):
                if not train_ids or not test_ids:
                    continue
                e_train = e[e.event_id.isin(train_ids)]
                e_test = e[e.event_id.isin(test_ids)]
                hh_overlap = len(set(e_train.household_id_derived) & set(e_test.household_id_derived))
                split_rows.append({
                    "sample": sample, "validation_scheme": scheme, "fold": fold,
                    "n_train_events": len(train_ids), "n_test_events": len(test_ids),
                    "n_train_households": e_train.household_id_derived.nunique(),
                    "n_test_households": e_test.household_id_derived.nunique(),
                    "household_overlap_count": hh_overlap,
                })
                c_train = choice[choice.event_id.isin(train_ids)].copy()
                c_test = choice[choice.event_id.isin(test_ids)].copy()
                for universe in ["full_64", "interdistrict_63"]:
                    if universe == "interdistrict_63":
                        cross_train_ids = e_train[bool_col(e_train.cross_district_event)].event_id
                        cross_test_ids = e_test[bool_col(e_test.cross_district_event)].event_id
                        if len(cross_train_ids) == 0 or len(cross_test_ids) == 0:
                            continue
                        ct = c_train[c_train.event_id.isin(cross_train_ids)]
                        cv = c_test[c_test.event_id.isin(cross_test_ids)]
                        et = e_train[e_train.event_id.isin(cross_train_ids)]
                    else:
                        ct, cv, et = c_train, c_test, e_train
                    context = {"sample": sample, "candidate_universe": universe,
                               "validation_scheme": scheme, "outer_fold": fold,
                               "interactions": False}
                    fits = fit_direct_fold(ct, cv, et, universe, False, context, tuning_rows)
                    for model, features, beta, lam, iters, conv, m, details, scaling in fits:
                        fold_results.append({**context, "fold": fold, "model": model,
                                             "ridge_lambda": lam, "iterations": iters,
                                             "converged": conv, **m})
                        for feature, coef in zip(features, beta):
                            params.append({**context, "fold": fold, "model": model,
                                           "ridge_lambda": lam, "feature": feature,
                                           "coefficient": float(coef), **scaling})
                        if scheme == "household_grouped_5fold":
                            predictions.extend([{**context, "fold": fold, "model": model, **d} for d in details])

                # Nested models produce full 64-district probabilities.
                context = {"sample": sample, "candidate_universe": "full_64",
                           "validation_scheme": scheme, "outer_fold": fold,
                           "interactions": False}
                for use_gis in [False, True]:
                    fit = fit_nested_fold(c_train, c_test, e_train, context, tuning_rows, use_gis)
                    model, features, beta, lam, iters, conv, m, details, scaling, fm, fdet, lgb = fit
                    fold_results.append({**context, "fold": fold, "model": model,
                                         "ridge_lambda": lam, "iterations": iters,
                                         "converged": conv and fm["logit_converged"], **m})
                    for feature, coef in zip(features, beta):
                        params.append({**context, "fold": fold, "model": model,
                                       "ridge_lambda": lam, "feature": feature,
                                       "coefficient": float(coef), **scaling})
                    params.extend([
                        {**context, "fold": fold, "model": model, "ridge_lambda": lam,
                         "feature": "stay_cross_logit_intercept", "coefficient": float(lgb[0]), **scaling},
                        {**context, "fold": fold, "model": model, "ridge_lambda": lam,
                         "feature": "stay_cross_inclusive_value_slope", "coefficient": float(lgb[1]), **scaling},
                    ])
                    first_results.append({**context, "fold": fold, "model": model, **fm})
                    if scheme == "household_grouped_5fold":
                        predictions.extend([{**context, "fold": fold, "model": model, **d} for d in details])
                        first_predictions.extend([{**context, "fold": fold, "model": model, **d} for d in fdet])

    # Secondary pre-specified shock interactions, household-grouped only.
    sample = "household_lagged_shock_observed"
    e = events[bool_col(events.sample_household_lagged_shock_observed)].copy()
    for fold, train_ids, test_ids in make_splits(e, "household_grouped_5fold"):
        e_train, e_test = e[e.event_id.isin(train_ids)], e[e.event_id.isin(test_ids)]
        c_train, c_test = choice[choice.event_id.isin(train_ids)], choice[choice.event_id.isin(test_ids)]
        for universe in ["full_64", "interdistrict_63"]:
            if universe == "interdistrict_63":
                train_cross = e_train[bool_col(e_train.cross_district_event)]
                test_cross = e_test[bool_col(e_test.cross_district_event)]
                if test_cross.empty:
                    continue
                ct = c_train[c_train.event_id.isin(train_cross.event_id)]
                cv = c_test[c_test.event_id.isin(test_cross.event_id)]
                et = train_cross
            else:
                ct, cv, et = c_train, c_test, e_train
            for interactions in [False, True]:
                context = {"sample": sample, "candidate_universe": universe,
                           "validation_scheme": "household_grouped_5fold", "outer_fold": fold,
                           "interactions": interactions}
                fits = fit_direct_fold(ct, cv, et, universe, interactions, context, tuning_rows)
                # Keep gravity/radiation only once; keep GIS models for both specifications.
                for model, features, beta, lam, iters, conv, m, details, scaling in fits:
                    if interactions is True and model in {"gravity_mle_disk_within", "radiation_adapted"}:
                        continue
                    if interactions is False and model.startswith("gis_"):
                        model = model + "_no_interactions"
                    fold_results.append({**context, "fold": fold, "model": model,
                                         "ridge_lambda": lam, "iterations": iters,
                                         "converged": conv, **m})
                    for feature, coef in zip(features, beta):
                        params.append({**context, "fold": fold, "model": model,
                                       "ridge_lambda": lam, "feature": feature,
                                       "coefficient": float(coef), **scaling})
                    predictions.extend([{**context, "fold": fold, "model": model, **d} for d in details])

    fold_df = pd.DataFrame(fold_results)
    result_df = aggregate_fold_results(fold_results)
    param_df = pd.DataFrame(params)
    pred_df = pd.DataFrame(predictions)
    tuning_df = pd.DataFrame(tuning_rows)
    first_df = pd.DataFrame(first_results)
    first_pred_df = pd.DataFrame(first_predictions)
    split_df = pd.DataFrame(split_rows)
    paired = paired_comparisons(pred_df, events)

    # Full-sample estimates with lambda chosen by inner grouped CV over all data.
    final_rows = []
    for sample, flag in sample_defs.items():
        e = events[bool_col(events[flag])]
        c = choice[choice.event_id.isin(e.event_id)]
        for universe in ["full_64", "interdistrict_63"]:
            if universe == "interdistrict_63":
                euse = e[bool_col(e.cross_district_event)]
                cuse = c[c.event_id.isin(euse.event_id) & (c.destination_district != c.origin_district)]
            else:
                euse, cuse = e, c
            context = {"sample": sample, "candidate_universe": universe,
                       "validation_scheme": "full_sample_inner_cv", "outer_fold": "full",
                       "interactions": False}
            lam = inner_tune(c, e, universe, False, context, tuning_rows)
            (cs,), scaling = scale_gis(cuse, [cuse])
            features = model_features(False)
            X, y, _, _ = arrays(cs, features)
            beta, it, conv = fit_conditional(X, y, lam, np.asarray([0, 0, 1, 1, 1, 1]))
            for f, b in zip(features, beta):
                final_rows.append({"sample": sample, "candidate_universe": universe,
                                   "model": "gis_joint_ridge", "selected_lambda": lam,
                                   "feature": f, "coefficient": float(b),
                                   "iterations": it, "converged": conv, **scaling})

    # Save outputs.
    result_df.to_csv(TABLES / "bemp_stage5_model_results.csv", index=False)
    fold_df.to_csv(TABLES / "bemp_stage5_fold_results.csv", index=False)
    param_df.to_csv(TABLES / "bemp_stage5_fold_parameters.csv", index=False)
    pred_df.to_csv(TABLES / "bemp_stage5_oof_event_predictions.csv", index=False)
    pd.DataFrame(tuning_rows).to_csv(TABLES / "bemp_stage5_lambda_tuning.csv", index=False)
    first_df.to_csv(TABLES / "bemp_stage5_nested_first_stage_results.csv", index=False)
    first_pred_df.to_csv(TABLES / "bemp_stage5_nested_first_stage_predictions.csv", index=False)
    split_df.to_csv(TABLES / "bemp_stage5_split_audit.csv", index=False)
    paired.to_csv(TABLES / "bemp_stage5_paired_logloss_comparisons.csv", index=False)
    pd.DataFrame(final_rows).to_csv(TABLES / "bemp_stage5_final_parameter_estimates.csv", index=False)

    print("Primary household-grouped results")
    print(result_df[result_df.validation_scheme == "household_grouped_5fold"].sort_values(
        ["sample", "candidate_universe", "mean_log_loss"]
    ).to_string(index=False))
    print("\nPaired comparisons")
    print(paired.to_string(index=False))


if __name__ == "__main__":
    main()
