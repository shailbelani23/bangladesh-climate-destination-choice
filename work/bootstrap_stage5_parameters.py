#!/usr/bin/env python3
"""Household-cluster bootstrap for frozen Stage-5 conditional-logit coefficients."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))
import fit_bemp_stage5_gis_models as m

TABLES = ROOT / "outputs" / "tables"
N_BOOT = 1000


def grouped_indices(event_ids, households):
    out = {}
    for i, (event, hh) in enumerate(zip(event_ids, households)):
        out.setdefault(hh, []).append(i)
    return out


def bootstrap_fit(X, y, event_ids, household_lookup, features, lam, penalty, seed):
    households = [household_lookup[e] for e in event_ids]
    by_hh = grouped_indices(event_ids, households)
    unique_hh = np.asarray(sorted(by_hh))
    rng = np.random.default_rng(seed)
    estimates = []
    converged = []
    for _ in range(N_BOOT):
        draw = rng.choice(unique_hh, size=len(unique_hh), replace=True)
        idx = np.concatenate([np.asarray(by_hh[h], dtype=int) for h in draw])
        beta, _, conv = m.fit_conditional(X[idx], y[idx], lam, penalty)
        estimates.append(beta)
        converged.append(conv)
    a = np.asarray(estimates)
    rows = []
    for j, feature in enumerate(features):
        rows.append({
            "feature": feature,
            "bootstrap_mean": float(a[:, j].mean()),
            "bootstrap_sd": float(a[:, j].std(ddof=1)),
            "bootstrap_ci_low": float(np.quantile(a[:, j], .025)),
            "bootstrap_ci_high": float(np.quantile(a[:, j], .975)),
            "bootstrap_median": float(np.median(a[:, j])),
            "bootstrap_share_positive": float((a[:, j] > 0).mean()),
            "bootstrap_replicates": N_BOOT,
            "bootstrap_converged_share": float(np.mean(converged)),
            "interval_note": "household-cluster percentile interval conditional on selected ridge lambda",
        })
    return rows


def main():
    choice, events = m.prepare_data()
    final = pd.read_csv(TABLES / "bemp_stage5_final_parameter_estimates.csv")
    household_lookup = events.set_index("event_id").household_id_derived.to_dict()
    rows = []
    sample_defs = {
        "household_relocation": "sample_household_relocation",
        "household_lagged_shock_yes": "sample_household_lagged_shock_yes",
    }
    seed = 20260829
    for sample, flag in sample_defs.items():
        e = events[m.bool_col(events[flag])]
        c = choice[choice.event_id.isin(e.event_id)]
        for universe in ["full_64", "interdistrict_63"]:
            if universe == "interdistrict_63":
                e = e[m.bool_col(e.cross_district_event)]
                cuse = c[c.event_id.isin(e.event_id) & (c.destination_district != c.origin_district)]
            else:
                cuse = c
            sub = final[(final["sample"] == sample) & (final.candidate_universe == universe)]
            lam = float(sub.selected_lambda.iloc[0])
            (cs,), scaling = m.scale_gis(cuse, [cuse])
            features = m.model_features(False)
            X, y, ids, _ = m.arrays(cs, features)
            penalty = np.asarray([0, 0, 1, 1, 1, 1], dtype=float)
            beta, iterations, converged = m.fit_conditional(X, y, lam, penalty)
            boot = bootstrap_fit(X, y, ids, household_lookup, features, lam, penalty, seed)
            seed += 1
            for feature, estimate, br in zip(features, beta, boot):
                rows.append({
                    "sample": sample, "candidate_universe": universe,
                    "model": "gis_joint_ridge", "selected_lambda": lam,
                    "full_sample_estimate": float(estimate), "full_sample_converged": converged,
                    "full_sample_iterations": iterations, **br, **scaling,
                })

    # Secondary shock interaction estimates and uncertainty.
    sample = "household_lagged_shock_observed"
    eall = events[m.bool_col(events.sample_household_lagged_shock_observed)]
    call = choice[choice.event_id.isin(eall.event_id)]
    tuning_rows = []
    for universe in ["full_64", "interdistrict_63"]:
        if universe == "interdistrict_63":
            e = eall[m.bool_col(eall.cross_district_event)]
            cuse = call[call.event_id.isin(e.event_id) & (call.destination_district != call.origin_district)]
        else:
            e, cuse = eall, call
        context = {"sample": sample, "candidate_universe": universe,
                   "validation_scheme": "full_sample_inner_cv", "outer_fold": "full",
                   "interactions": True}
        lam = m.inner_tune(call, eall, universe, True, context, tuning_rows)
        (cs,), scaling = m.scale_gis(cuse, [cuse])
        features = m.model_features(True)
        X, y, ids, _ = m.arrays(cs, features)
        penalty = np.asarray([0, 0] + [1] * 6, dtype=float)
        beta, iterations, converged = m.fit_conditional(X, y, lam, penalty)
        boot = bootstrap_fit(X, y, ids, household_lookup, features, lam, penalty, seed)
        seed += 1
        for feature, estimate, br in zip(features, beta, boot):
            rows.append({
                "sample": sample, "candidate_universe": universe,
                "model": "gis_joint_ridge_shock_interactions", "selected_lambda": lam,
                "full_sample_estimate": float(estimate), "full_sample_converged": converged,
                "full_sample_iterations": iterations, **br, **scaling,
            })
    pd.DataFrame(rows).to_csv(TABLES / "bemp_stage5_parameter_bootstrap.csv", index=False)
    pd.DataFrame(tuning_rows).to_csv(TABLES / "bemp_stage5_interaction_full_sample_tuning.csv", index=False)
    print(pd.DataFrame(rows)[[
        "sample", "candidate_universe", "feature", "selected_lambda", "full_sample_estimate",
        "bootstrap_ci_low", "bootstrap_ci_high", "bootstrap_share_positive"
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
