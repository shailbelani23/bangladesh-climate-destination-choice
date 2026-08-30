#!/usr/bin/env python3
"""Independent invariants for the checkpointed BIHS external replication."""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs/tables"


def check(name, passed, observed, expected):
    return {"check": name, "passed": bool(passed), "observed": observed, "expected": expected}


def main():
    c = pd.read_csv(T / "bihs_replication_choice_set.csv", low_memory=False)
    r = pd.read_csv(T / "bihs_replication_model_results_grouped.csv")
    p = pd.read_csv(T / "bihs_replication_oof_predictions_grouped.csv")
    b = pd.read_csv(T / "bihs_replication_paired_comparisons_grouped.csv")
    s = pd.read_csv(T / "bihs_replication_split_audit_grouped.csv")
    w = pd.read_csv(T / "bihs_replication_model_results_wave.csv")
    lr = pd.read_csv(T / "bihs_replication_model_results_loo.csv")
    lp = pd.read_csv(T / "bihs_replication_oof_predictions_loo.csv", low_memory=False)
    lb = pd.read_csv(T / "bihs_replication_paired_comparisons_loo.csv")
    ls = pd.read_csv(T / "bihs_replication_split_audit_loo.csv")
    rows = []
    rows.append(check("choice_set_2383_by_64", len(c) == 2383 * 64 and c.event_id.nunique() == 2383,
                      f"rows={len(c)}; events={c.event_id.nunique()}", "152512 rows; 2383 events"))
    rows.append(check("one_chosen_per_event", c.groupby("event_id").chosen.sum().eq(1).all(),
                      int(c.groupby("event_id").chosen.sum().eq(1).sum()), 2383))
    rows.append(check("all_choice_sets_64", c.groupby("event_id").size().eq(64).all(),
                      sorted(c.groupby("event_id").size().unique().tolist()), [64]))
    rows.append(check("no_grouped_household_leakage", s.household_overlap.eq(0).all(),
                      int(s.household_overlap.max()), 0))
    rows.append(check("all_grouped_fits_converged", r.all_folds_converged.all(),
                      int(r.all_folds_converged.sum()), len(r)))
    rows.append(check("all_wave_fits_converged", w.all_folds_converged.all(),
                      int(w.all_folds_converged.sum()), len(w)))
    rows.append(check("oof_probability_sums", np.allclose(p.probability_sum, 1, atol=1e-10),
                      float((p.probability_sum - 1).abs().max()), "<=1e-10"))
    # Each sample-event-model-universe has one OOF prediction.
    rows.append(check("oof_unique_keys", not p.duplicated(["sample", "candidate_universe", "model", "event_id"]).any(),
                      int(p.duplicated(["sample", "candidate_universe", "model", "event_id"]).sum()), 0))

    required = {
        ("b4_erosion", "full_64"): (123, 0.098000),
        ("b4_erosion", "interdistrict_63"): (71, 0.182204),
        ("b4_all", "full_64"): (526, 0.057765),
        ("v1_interval", "full_64"): (1857, 0.108129),
        ("v1_interval", "interdistrict_63"): (1208, 0.108377),
    }
    for (sample, universe), (n, approx) in required.items():
        x = r[(r["sample"] == sample) & (r.candidate_universe == universe) & (r.model == "gis_joint_ridge")].iloc[0]
        rows.append(check(f"{sample}_{universe}_n", int(x.n_events_evaluated) == n, int(x.n_events_evaluated), n))
        rows.append(check(f"{sample}_{universe}_positive_gain", x.log_loss_improvement_vs_gravity > 0,
                          float(x.log_loss_improvement_vs_gravity), ">0"))
        y = b[(b["sample"] == sample) & (b.candidate_universe == universe) &
              (b.model == "gis_joint_ridge") & (b.comparator == "gravity_mle_disk_within")].iloc[0]
        rows.append(check(f"{sample}_{universe}_point_match",
                          abs(x.log_loss_improvement_vs_gravity - y.mean_log_loss_improvement) < 1e-10,
                          float(x.log_loss_improvement_vs_gravity - y.mean_log_loss_improvement), "<1e-10"))
        rows.append(check(f"{sample}_{universe}_bootstrap_positive", y.cluster_bootstrap_ci_low > 0,
                          float(y.cluster_bootstrap_ci_low), ">0"))

    wf = w[(w["sample"] == "v1_interval") & (w.candidate_universe == "full_64") & (w.model == "gis_joint_ridge")].iloc[0]
    wi = w[(w["sample"] == "v1_interval") & (w.candidate_universe == "interdistrict_63") & (w.model == "gis_joint_ridge")].iloc[0]
    rows.append(check("wave_holdout_full_positive", wf.log_loss_improvement_vs_gravity > 0,
                      float(wf.log_loss_improvement_vs_gravity), ">0"))
    rows.append(check("wave_holdout_interdistrict_positive", wi.log_loss_improvement_vs_gravity > 0,
                      float(wi.log_loss_improvement_vs_gravity), ">0"))

    rows.append(check("loo_all_fits_converged", lr.all_folds_converged.all(),
                      int(lr.all_folds_converged.sum()), len(lr)))
    rows.append(check("loo_probability_sums", np.allclose(lp.probability_sum, 1, atol=1e-10),
                      float((lp.probability_sum - 1).abs().max()), "<=1e-10"))
    rows.append(check("loo_unique_prediction_keys",
                      not lp.duplicated(["sample", "candidate_universe", "model", "event_id"]).any(),
                      int(lp.duplicated(["sample", "candidate_universe", "model", "event_id"]).sum()), 0))
    rows.append(check("loo_no_household_overlap", ls.household_overlap.eq(0).all(),
                      int(ls.household_overlap.max()), 0))
    rows.append(check("loo_fold_matches_heldout_origin",
                      (lp.fold == "holdout_" + lp.origin_district).all(),
                      int((lp.fold != "holdout_" + lp.origin_district).sum()), 0))

    loo_expected = {
        ("b4_erosion", "full_64"): (123, 29),
        ("b4_erosion", "interdistrict_63"): (71, 21),
        ("b4_all", "full_64"): (526, 61),
        ("b4_all", "interdistrict_63"): (236, 52),
        ("v1_interval", "full_64"): (1857, 64),
        ("v1_interval", "interdistrict_63"): (1208, 64),
    }
    for (sample, universe), (n, nfolds) in loo_expected.items():
        x = lr[(lr["sample"] == sample) & (lr.candidate_universe == universe) & (lr.model == "gis_joint_ridge")].iloc[0]
        y = lb[(lb["sample"] == sample) & (lb.candidate_universe == universe) &
               (lb.model == "gis_joint_ridge")].iloc[0]
        rows.append(check(f"loo_{sample}_{universe}_coverage",
                          int(x.n_events_evaluated) == n and int(x.n_folds_evaluated) == nfolds,
                          f"events={int(x.n_events_evaluated)}; folds={int(x.n_folds_evaluated)}",
                          f"events={n}; folds={nfolds}"))
        rows.append(check(f"loo_{sample}_{universe}_point_match",
                          abs(x.log_loss_improvement_vs_gravity - y.mean_log_loss_improvement) < 1e-10,
                          float(x.log_loss_improvement_vs_gravity - y.mean_log_loss_improvement), "<1e-10"))

    for universe in ["full_64", "interdistrict_63"]:
        x = lb[(lb["sample"] == "v1_interval") & (lb.candidate_universe == universe) &
               (lb.model == "gis_joint_ridge")].iloc[0]
        rows.append(check(f"loo_v1_{universe}_positive_interval", x.cluster_bootstrap_ci_low > 0,
                          float(x.cluster_bootstrap_ci_low), ">0"))

    x = lb[(lb["sample"] == "b4_erosion") & (lb.candidate_universe == "full_64") &
           (lb.model == "gis_joint_ridge")].iloc[0]
    rows.append(check("loo_erosion_full_transportability_warning", x.mean_log_loss_improvement < 0,
                      float(x.mean_log_loss_improvement), "<0 (pre-specified boundary report)"))

    out = pd.DataFrame(rows)
    out.to_csv(T / "bihs_replication_validation.csv", index=False)
    print(out.to_string(index=False))
    if not out.passed.all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
