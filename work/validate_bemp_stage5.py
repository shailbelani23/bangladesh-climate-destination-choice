#!/usr/bin/env python3
"""Research-quality acceptance checks for the Stage-5 GIS choice models."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "work"))
import fit_bemp_stage5_gis_models as model_code


def row(check, passed, observed, requirement, severity="fatal"):
    return {"check": check, "passed": bool(passed), "observed": observed,
            "requirement": requirement, "severity": severity}


def main():
    choice = pd.read_csv(TABLES / "bemp_stage5_model_ready_choice_set.csv", low_memory=False)
    results = pd.read_csv(TABLES / "bemp_stage5_model_results.csv")
    fold = pd.read_csv(TABLES / "bemp_stage5_fold_results.csv")
    pred = pd.read_csv(TABLES / "bemp_stage5_oof_event_predictions.csv")
    params = pd.read_csv(TABLES / "bemp_stage5_fold_parameters.csv")
    tuning = pd.read_csv(TABLES / "bemp_stage5_lambda_tuning.csv")
    splits = pd.read_csv(TABLES / "bemp_stage5_split_audit.csv")
    paired = pd.read_csv(TABLES / "bemp_stage5_paired_logloss_comparisons.csv")
    boot = pd.read_csv(TABLES / "bemp_stage5_parameter_bootstrap.csv")
    old = pd.read_csv(TABLES / "bemp_baseline_benchmark_results.csv")
    checks = []

    checks += [
        row("model_ready_rows", len(choice) == 573 * 64, len(choice), "573 x 64 = 36,672"),
        row("model_ready_events", choice.event_id.nunique() == 573, choice.event_id.nunique(), "573"),
        row("candidate_count_per_event", choice.groupby("event_id").size().eq(64).all(),
            f"min={choice.groupby('event_id').size().min()}; max={choice.groupby('event_id').size().max()}",
            "exactly 64 for every event"),
        row("chosen_count_per_event", choice.groupby("event_id").chosen.sum().eq(1).all(),
            f"min={choice.groupby('event_id').chosen.sum().min()}; max={choice.groupby('event_id').chosen.sum().max()}",
            "exactly one chosen alternative per event"),
        row("gis_feature_missingness", choice[model_code.GIS_RAW].isna().sum().sum() == 0,
            int(choice[model_code.GIS_RAW].isna().sum().sum()), "zero"),
    ]

    # Exact benchmark reproduction is a strong end-to-end test of splits and likelihood.
    keys = ["sample", "candidate_universe", "validation_scheme", "model"]
    a = old[old.model == "gravity_mle_disk_within"][keys + ["mean_log_loss", "top1_accuracy"]]
    b = results[results.model == "gravity_mle_disk_within"][keys + ["mean_log_loss", "top1_accuracy"]]
    m = a.merge(b, on=keys, suffixes=("_stage2", "_stage5"))
    max_loss_diff = float((m.mean_log_loss_stage5 - m.mean_log_loss_stage2).abs().max())
    max_top1_diff = float((m.top1_accuracy_stage5 - m.top1_accuracy_stage2).abs().max())
    checks.append(row("stage2_gravity_reproduction", len(m) == 16 and max_loss_diff < 1e-7 and max_top1_diff < 1e-12,
                      f"matched={len(m)}; max_logloss_diff={max_loss_diff:.3g}; max_top1_diff={max_top1_diff:.3g}",
                      "16 benchmark cells; differences <1e-7 and <1e-12"))

    prob_error = float((pred.probability_sum - 1).abs().max())
    checks += [
        row("oof_probability_sums", prob_error < 1e-12, prob_error, "maximum absolute error <1e-12"),
        row("oof_chosen_probabilities", ((pred.chosen_probability > 0) & (pred.chosen_probability <= 1)).all(),
            f"min={pred.chosen_probability.min():.3g}; max={pred.chosen_probability.max():.3g}", "0 < p <= 1"),
        row("outer_fit_convergence", fold.converged.all(), int(fold.converged.sum()), f"all {len(fold)} folds"),
        row("bootstrap_fit_convergence", boot.bootstrap_converged_share.min() >= .99,
            float(boot.bootstrap_converged_share.min()), ">= 0.99"),
    ]

    primary_splits = splits[splits.validation_scheme == "household_grouped_5fold"]
    checks.append(row("household_split_overlap", primary_splits.household_overlap_count.max() == 0,
                      int(primary_splits.household_overlap_count.max()), "zero in every primary fold"))
    selected = tuning[tuning.selected]
    tuning_keys = ["sample", "candidate_universe", "validation_scheme", "outer_fold", "interactions"]
    if "nested_component" in selected.columns:
        tuning_keys.append("nested_component")
    selection_counts = selected.groupby(
        tuning_keys,
        dropna=False,
    ).size()
    checks += [
        row("inner_lambda_unique_selection", selection_counts.eq(1).all(),
            f"min={selection_counts.min()}; max={selection_counts.max()}", "one selected lambda per tuning context"),
        row("selected_lambdas_preregistered", set(selected.candidate_lambda) <= set(model_code.LAMBDAS),
            sorted(selected.candidate_lambda.unique().tolist()), str(model_code.LAMBDAS)),
    ]

    # No post-choice survey mechanism is allowed in the fitted design matrix.
    fitted_features = set(params.feature.dropna().unique())
    allowed = set(model_code.BASE_FEATURES + model_code.GIS_Z + [
        "shock_x_z_gfd_flood", "shock_x_z_access_time", "log_radiation_score",
        "stay_cross_logit_intercept", "stay_cross_inclusive_value_slope",
    ])
    checks.append(row("feature_whitelist", fitted_features <= allowed,
                      "|".join(sorted(fitted_features - allowed)) or "no disallowed features",
                      "only frozen baseline/GIS/interactions/nested terms"))

    # Primary gains and explicit transportability warning.
    def get_result(sample, universe, scheme, model):
        x = results[(results["sample"] == sample) & (results.candidate_universe == universe)
                    & (results.validation_scheme == scheme) & (results.model == model)]
        return x.iloc[0]

    climate_gis = get_result("household_lagged_shock_yes", "full_64", "household_grouped_5fold", "gis_joint_ridge")
    climate_nested = get_result("household_lagged_shock_yes", "full_64", "household_grouped_5fold", "nested_gis_ridge")
    checks += [
        row("primary_direct_gis_improves_logloss", climate_gis.log_loss_improvement_vs_gravity > 0,
            float(climate_gis.log_loss_improvement_vs_gravity), ">0", "substantive"),
        row("primary_nested_gis_improves_logloss", climate_nested.log_loss_improvement_vs_gravity > 0,
            float(climate_nested.log_loss_improvement_vs_gravity), ">0", "substantive"),
    ]
    pp = paired[(paired["sample"] == "household_lagged_shock_yes")
                & (paired.candidate_universe == "full_64")]
    for model in ["gis_joint_ridge", "nested_gis_ridge"]:
        x = pp[(pp.model == model) & (pp.comparator == "gravity_mle_disk_within")].iloc[0]
        checks.append(row(f"paired_cluster_ci_positive__{model}", x.cluster_bootstrap_ci_low > 0,
                          f"[{x.cluster_bootstrap_ci_low:.4f}, {x.cluster_bootstrap_ci_high:.4f}]",
                          "95% household-cluster interval entirely >0", "substantive"))

    loo = get_result("household_lagged_shock_yes", "full_64", "leave_one_origin_out", "gis_joint_ridge")
    checks.append(row("unseen_origin_transportability_warning", loo.log_loss_improvement_vs_gravity < 0,
                      float(loo.log_loss_improvement_vs_gravity),
                      "record negative full-universe improvement; do not claim unseen-origin transportability",
                      "warning"))
    interaction = paired[(paired["sample"] == "household_lagged_shock_observed")
                         & (paired.candidate_universe == "full_64")
                         & (paired.model == "gis_joint_ridge_shock_interactions")].iloc[0]
    checks.append(row("shock_interaction_predictive_gain_uncertain",
                      interaction.cluster_bootstrap_ci_low <= 0 <= interaction.cluster_bootstrap_ci_high,
                      f"gain={interaction.mean_log_loss_improvement:.4f}; "
                      f"CI=[{interaction.cluster_bootstrap_ci_low:.4f}, {interaction.cluster_bootstrap_ci_high:.4f}]",
                      "interval includes zero; retain as secondary", "warning"))

    out = pd.DataFrame(checks)
    out.to_csv(TABLES / "bemp_stage5_validation.csv", index=False)
    fatal = out[out.severity == "fatal"]
    if not fatal.passed.all():
        print(out.to_string(index=False))
        raise RuntimeError("Stage-5 fatal validation failed")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
