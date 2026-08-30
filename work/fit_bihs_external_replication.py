#!/usr/bin/env python3
"""Fit the frozen BEMP feature contract to the independent BIHS ledgers."""

from __future__ import annotations

from pathlib import Path
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs/tables"
sys.path.insert(0, str(ROOT / "work"))
import fit_bemp_stage5_gis_models as core  # noqa: E402


def build_events():
    b4 = pd.read_csv(TABLES / "bihs_household_relocation_events.csv")
    v1 = pd.read_csv(TABLES / "bihs_internal_migration_events.csv")
    v1 = v1[v1.primary_interval_sample.astype(str).str.lower().eq("true")].copy()
    common = ["event_id", "household_id", "wave", "origin_district", "destination_district", "cross_district"]
    e1 = b4[common].copy()
    e1["b4_all"] = True
    e1["b4_erosion"] = b4.erosion_motivated.astype(str).str.lower().eq("true")
    e1["b4_erosion_valid_year"] = e1.b4_erosion & b4.move_year_valid.astype(str).str.lower().eq("true")
    e1["v1_interval"] = False
    e2 = v1[common].copy()
    e2["b4_all"] = False
    e2["b4_erosion"] = False
    e2["b4_erosion_valid_year"] = False
    e2["v1_interval"] = True
    e = pd.concat([e1, e2], ignore_index=True)
    e = e.rename(columns={"household_id": "household_id_derived", "destination_district": "chosen_district"})
    e["baseline_location_lxx"] = e.origin_district
    e["cross_district_event"] = e.cross_district.astype(str).str.lower().eq("true")
    e["shock_any"] = e.b4_erosion.astype(int)
    return e


def build_choice(events):
    od = pd.read_csv(TABLES / "bgd_origin_destination_matrix.csv")
    gis = pd.read_csv(TABLES / "bemp_stage4_district_gis_features.csv")
    choice = events.merge(od, on="origin_district", how="left", validate="many_to_many")
    choice["chosen"] = choice.destination_district.eq(choice.chosen_district)
    choice["log_distance_disk_proxy_km"] = np.log(choice.distance_disk_proxy_km)
    choice["log_radiation_score"] = np.log(np.maximum(choice.radiation_score_adapted, 1e-300))
    choice = choice.merge(
        gis[["district_pcode", "district"] + core.GIS_RAW],
        left_on="destination_pcode", right_on="district_pcode", how="left",
        validate="many_to_one", suffixes=("", "_gis"),
    )
    if choice[core.GIS_RAW].isna().any().any():
        raise RuntimeError("GIS merge produced missing destination attributes")
    if not choice.groupby("event_id").size().eq(64).all():
        raise RuntimeError("Every event must have the frozen 64-district choice set")
    if not choice.groupby("event_id").chosen.sum().eq(1).all():
        raise RuntimeError("Every event must have exactly one chosen district")
    if os.environ.get("BIHS_REPLICATION_WRITE_CHOICE", "1") == "1":
        choice.to_csv(TABLES / "bihs_replication_choice_set.csv", index=False)
    return choice


def splits(e, scheme):
    if scheme == "household_grouped_5fold":
        fold = e.household_id_derived.map(lambda x: core.hash_fold(x, 5))
        return [(f"fold_{k}", e.loc[fold != k, "event_id"].tolist(), e.loc[fold == k, "event_id"].tolist()) for k in range(5)]
    if scheme == "leave_one_origin_out":
        return [(f"holdout_{o}", e.loc[e.origin_district != o, "event_id"].tolist(),
                 e.loc[e.origin_district == o, "event_id"].tolist()) for o in sorted(e.origin_district.unique())]
    if scheme == "wave_holdout_r3":
        return [("train_r2_test_r3", e.loc[e.wave == "w2", "event_id"].tolist(),
                 e.loc[e.wave == "w3", "event_id"].tolist())]
    raise KeyError(scheme)


def uniform_fit(test_choice):
    X, y, ids, groups = core.arrays(test_choice, ["log_destination_population_2022"])
    probs = np.full((len(ids), X.shape[1]), 1 / X.shape[1])
    return core.score_probability_arrays(probs, y, ids, groups)


def aggregate(folds):
    d = pd.DataFrame(folds)
    keys = ["sample", "candidate_universe", "validation_scheme", "model"]
    rows = []
    for key, g in d.groupby(keys, sort=False):
        n = g.n_events.sum()
        r = dict(zip(keys, key))
        r["n_events_evaluated"] = int(n)
        r["n_folds_evaluated"] = len(g)
        r["all_folds_converged"] = bool(g.converged.all())
        r["selected_lambda_median"] = float(g.ridge_lambda.median())
        for c in ["mean_log_loss", "top1_accuracy", "top3_accuracy", "top5_accuracy", "mean_rank", "mean_reciprocal_rank"]:
            r[c] = float(np.average(g[c], weights=g.n_events))
        rows.append(r)
    out = pd.DataFrame(rows)
    base = out[out.model == "gravity_mle_disk_within"][
        ["sample", "candidate_universe", "validation_scheme", "mean_log_loss"]
    ].rename(columns={"mean_log_loss": "gravity_mean_log_loss"})
    out = out.merge(base, on=["sample", "candidate_universe", "validation_scheme"], how="left")
    out["log_loss_improvement_vs_gravity"] = out.gravity_mean_log_loss - out.mean_log_loss
    return out


def paired_bootstrap(pred, events):
    rng = np.random.default_rng(20260830)
    if pred.empty or "validation_scheme" not in pred:
        return pd.DataFrame(columns=[
            "sample", "candidate_universe", "model", "comparator", "n_events", "n_households",
            "mean_log_loss_improvement", "cluster_bootstrap_ci_low", "cluster_bootstrap_ci_high",
            "share_events_model_lower_loss", "bootstrap_replicates",
        ])
    p = pred[pred.validation_scheme.eq("household_grouped_5fold")]
    event_hh = events.set_index("event_id").household_id_derived
    pairs = [
        ("gis_joint_ridge", "gravity_mle_disk_within"),
        ("gis_joint_unpenalized", "gravity_mle_disk_within"),
        ("nested_gis_ridge", "nested_gravity"),
        ("nested_gis_ridge", "gravity_mle_disk_within"),
    ]
    rows = []
    for (sample, universe), g in p.groupby(["sample", "candidate_universe"]):
        for model, comp in pairs:
            a = g[g.model.eq(model)][["event_id", "chosen_log_loss"]].rename(columns={"chosen_log_loss": "a"})
            b = g[g.model.eq(comp)][["event_id", "chosen_log_loss"]].rename(columns={"chosen_log_loss": "b"})
            m = a.merge(b, on="event_id")
            if m.empty:
                continue
            m["household"] = m.event_id.map(event_hh)
            h = m.groupby("household").agg(a_sum=("a", "sum"), b_sum=("b", "sum"), n=("event_id", "size"))
            ids = h.index.to_numpy()
            boot = []
            for _ in range(5000):
                draw = rng.choice(ids, len(ids), replace=True)
                x = h.loc[draw]
                boot.append(float((x.b_sum.sum() - x.a_sum.sum()) / x.n.sum()))
            diff = m.b - m.a
            rows.append({
                "sample": sample, "candidate_universe": universe, "model": model, "comparator": comp,
                "n_events": len(m), "n_households": m.household.nunique(),
                "mean_log_loss_improvement": float(diff.mean()),
                "cluster_bootstrap_ci_low": float(np.quantile(boot, .025)),
                "cluster_bootstrap_ci_high": float(np.quantile(boot, .975)),
                "share_events_model_lower_loss": float((diff > 0).mean()), "bootstrap_replicates": 5000,
            })
    return pd.DataFrame(rows)


def main():
    events = build_events()
    choice = build_choice(events)
    sample_flags = {"b4_erosion": "b4_erosion", "b4_all": "b4_all", "v1_interval": "v1_interval"}
    allowed_schemes = set(os.environ.get(
        "BIHS_REPLICATION_SCHEMES",
        "household_grouped_5fold,leave_one_origin_out,wave_holdout_r3",
    ).split(","))
    suffix = os.environ.get("BIHS_REPLICATION_SUFFIX", "")
    origin_part = os.environ.get("BIHS_REPLICATION_ORIGIN_PART", "")
    if origin_part:
        part_index, part_total = (int(x) for x in origin_part.split("/"))
        if not (0 <= part_index < part_total):
            raise ValueError("BIHS_REPLICATION_ORIGIN_PART must be index/total with 0 <= index < total")
    else:
        part_index, part_total = 0, 1
    fold_rows, param_rows, pred_rows, tuning_rows, split_rows = [], [], [], [], []

    for sample, flag in sample_flags.items():
        e = events[events[flag]].copy()
        schemes = ["household_grouped_5fold", "leave_one_origin_out"]
        if sample == "v1_interval":
            schemes.append("wave_holdout_r3")
        schemes = [scheme for scheme in schemes if scheme in allowed_schemes]
        for scheme in schemes:
            scheme_splits = splits(e, scheme)
            if scheme == "leave_one_origin_out" and part_total > 1:
                scheme_splits = [x for i, x in enumerate(scheme_splits) if i % part_total == part_index]
            for fold, train_ids, test_ids in scheme_splits:
                if not train_ids or not test_ids:
                    continue
                etrain = e[e.event_id.isin(train_ids)]
                etest = e[e.event_id.isin(test_ids)]
                split_rows.append({
                    "sample": sample, "validation_scheme": scheme, "fold": fold,
                    "n_train_events": len(train_ids), "n_test_events": len(test_ids),
                    "n_train_households": etrain.household_id_derived.nunique(),
                    "n_test_households": etest.household_id_derived.nunique(),
                    "household_overlap": len(set(etrain.household_id_derived) & set(etest.household_id_derived)),
                })
                ctrain = choice[choice.event_id.isin(train_ids)].copy()
                ctest = choice[choice.event_id.isin(test_ids)].copy()
                for universe in ["full_64", "interdistrict_63"]:
                    if universe == "interdistrict_63":
                        train_cross = etrain[etrain.cross_district_event]
                        test_cross = etest[etest.cross_district_event]
                        if train_cross.empty or test_cross.empty:
                            continue
                        ct = ctrain[ctrain.event_id.isin(train_cross.event_id)]
                        cv = ctest[ctest.event_id.isin(test_cross.event_id)]
                        fit_events = train_cross
                    else:
                        ct, cv, fit_events = ctrain, ctest, etrain
                    context = {"sample": sample, "candidate_universe": universe,
                               "validation_scheme": scheme, "outer_fold": fold, "interactions": False}

                    # Uniform comparator.
                    uv = cv if universe == "full_64" else cv[cv.destination_district != cv.origin_district]
                    um, ud = uniform_fit(uv)
                    fold_rows.append({**context, "fold": fold, "model": "uniform", "ridge_lambda": 0.0,
                                      "iterations": 0, "converged": True, **um})
                    pred_rows += [{**context, "fold": fold, "model": "uniform", **x} for x in ud]

                    fits = core.fit_direct_fold(ct, cv, fit_events, universe, False, context, tuning_rows)
                    for model, features, beta, lam, iters, conv, metrics, details, scaling in fits:
                        if model == "radiation_adapted" and universe == "full_64":
                            continue
                        fold_rows.append({**context, "fold": fold, "model": model, "ridge_lambda": lam,
                                          "iterations": iters, "converged": conv, **metrics})
                        for feature, coef in zip(features, beta):
                            param_rows.append({**context, "fold": fold, "model": model, "ridge_lambda": lam,
                                               "feature": feature, "coefficient": float(coef), **scaling})
                        pred_rows += [{**context, "fold": fold, "model": model, **x} for x in details]

                # Nested models only for the frozen primary grouped validation.
                if scheme == "household_grouped_5fold":
                    context = {"sample": sample, "candidate_universe": "full_64",
                               "validation_scheme": scheme, "outer_fold": fold, "interactions": False}
                    for use_gis in [False, True]:
                        fit = core.fit_nested_fold(ctrain, ctest, etrain, context, tuning_rows, use_gis)
                        model, features, beta, lam, iters, conv, metrics, details, scaling, fm, _, lgb = fit
                        fold_rows.append({**context, "fold": fold, "model": model, "ridge_lambda": lam,
                                          "iterations": iters, "converged": conv and fm["logit_converged"], **metrics})
                        for feature, coef in zip(features, beta):
                            param_rows.append({**context, "fold": fold, "model": model, "ridge_lambda": lam,
                                               "feature": feature, "coefficient": float(coef), **scaling})
                        param_rows += [
                            {**context, "fold": fold, "model": model, "ridge_lambda": lam,
                             "feature": "stay_cross_logit_intercept", "coefficient": float(lgb[0]), **scaling},
                            {**context, "fold": fold, "model": model, "ridge_lambda": lam,
                             "feature": "stay_cross_inclusive_value_slope", "coefficient": float(lgb[1]), **scaling},
                        ]
                        pred_rows += [{**context, "fold": fold, "model": model, **x} for x in details]

    folds = pd.DataFrame(fold_rows)
    params = pd.DataFrame(param_rows)
    pred = pd.DataFrame(pred_rows)
    results = aggregate(fold_rows)
    paired = paired_bootstrap(pred, events)
    folds.to_csv(TABLES / f"bihs_replication_fold_results{suffix}.csv", index=False)
    params.to_csv(TABLES / f"bihs_replication_fold_parameters{suffix}.csv", index=False)
    pred.to_csv(TABLES / f"bihs_replication_oof_predictions{suffix}.csv", index=False)
    results.to_csv(TABLES / f"bihs_replication_model_results{suffix}.csv", index=False)
    paired.to_csv(TABLES / f"bihs_replication_paired_comparisons{suffix}.csv", index=False)
    pd.DataFrame(tuning_rows).to_csv(TABLES / f"bihs_replication_lambda_tuning{suffix}.csv", index=False)
    pd.DataFrame(split_rows).to_csv(TABLES / f"bihs_replication_split_audit{suffix}.csv", index=False)
    print(results.sort_values(["sample", "candidate_universe", "validation_scheme", "mean_log_loss"]).to_string(index=False))
    print("\nPAIRED\n", paired.to_string(index=False))


if __name__ == "__main__":
    main()
