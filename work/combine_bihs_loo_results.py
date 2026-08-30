#!/usr/bin/env python3
"""Combine checkpointed BIHS leave-one-origin partitions and validate coverage."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs/tables"
sys.path.insert(0, str(ROOT / "work"))
import fit_bihs_external_replication as model  # noqa: E402


def concat(kind):
    paths = sorted(T.glob(f"bihs_replication_{kind}_loo_part*.csv"))
    if len(paths) != 4:
        raise RuntimeError(f"Expected four {kind} partitions; found {len(paths)}")
    frames = []
    for path in paths:
        x = pd.read_csv(path)
        x["checkpoint_source"] = path.name
        frames.append(x)
    return pd.concat(frames, ignore_index=True)


def paired(pred):
    events = model.build_events().set_index("event_id")
    rng = np.random.default_rng(20260830)
    rows = []
    for (sample, universe), g in pred.groupby(["sample", "candidate_universe"]):
        for name in ["gis_joint_ridge", "gis_joint_unpenalized"]:
            a = g[g.model.eq(name)][["event_id", "chosen_log_loss"]].rename(columns={"chosen_log_loss": "a"})
            b = g[g.model.eq("gravity_mle_disk_within")][["event_id", "chosen_log_loss"]].rename(columns={"chosen_log_loss": "b"})
            m = a.merge(b, on="event_id", validate="one_to_one")
            m["household"] = m.event_id.map(events.household_id_derived)
            h = m.groupby("household").agg(a_sum=("a", "sum"), b_sum=("b", "sum"), n=("event_id", "size"))
            ids = h.index.to_numpy()
            boot = []
            for _ in range(5000):
                draw = rng.choice(ids, len(ids), replace=True)
                x = h.loc[draw]
                boot.append(float((x.b_sum.sum() - x.a_sum.sum()) / x.n.sum()))
            rows.append({
                "sample": sample, "candidate_universe": universe, "model": name,
                "comparator": "gravity_mle_disk_within", "n_events": len(m),
                "n_households": m.household.nunique(),
                "mean_log_loss_improvement": float((m.b - m.a).mean()),
                "cluster_bootstrap_ci_low": float(np.quantile(boot, .025)),
                "cluster_bootstrap_ci_high": float(np.quantile(boot, .975)),
                "share_events_model_lower_loss": float(((m.b - m.a) > 0).mean()),
                "bootstrap_replicates": 5000,
            })
    return pd.DataFrame(rows)


def main():
    folds = concat("fold_results")
    params = concat("fold_parameters")
    pred = concat("oof_predictions")
    tuning = concat("lambda_tuning")
    splits = concat("split_audit")

    fold_key = ["sample", "candidate_universe", "validation_scheme", "fold", "model"]
    pred_key = ["sample", "candidate_universe", "validation_scheme", "event_id", "model"]
    if folds.duplicated(fold_key).any() or pred.duplicated(pred_key).any():
        raise RuntimeError("Partition merge produced duplicate fold or prediction keys")
    if not folds.converged.all() or not np.allclose(pred.probability_sum, 1, atol=1e-10):
        raise RuntimeError("Convergence or probability invariant failed")

    results = model.aggregate(folds.drop(columns="checkpoint_source").to_dict("records"))
    comparisons = paired(pred)

    # Origin-specific paired gains for diagnosis, not sample selection.
    g = pred[pred.model.isin(["gravity_mle_disk_within", "gis_joint_ridge"])].pivot_table(
        index=["sample", "candidate_universe", "fold", "event_id", "origin_district"],
        columns="model", values="chosen_log_loss", aggfunc="first",
    ).reset_index()
    g["gis_gain_vs_gravity"] = g.gravity_mle_disk_within - g.gis_joint_ridge
    by_origin = g.groupby(["sample", "candidate_universe", "fold", "origin_district"]).agg(
        n_events=("event_id", "size"), mean_gis_gain_vs_gravity=("gis_gain_vs_gravity", "mean"),
        share_events_gis_lower_loss=("gis_gain_vs_gravity", lambda x: float((x > 0).mean())),
    ).reset_index()

    folds.to_csv(T / "bihs_replication_fold_results_loo.csv", index=False)
    params.to_csv(T / "bihs_replication_fold_parameters_loo.csv", index=False)
    pred.to_csv(T / "bihs_replication_oof_predictions_loo.csv", index=False)
    tuning.to_csv(T / "bihs_replication_lambda_tuning_loo.csv", index=False)
    splits.to_csv(T / "bihs_replication_split_audit_loo.csv", index=False)
    results.to_csv(T / "bihs_replication_model_results_loo.csv", index=False)
    comparisons.to_csv(T / "bihs_replication_paired_comparisons_loo.csv", index=False)
    by_origin.to_csv(T / "bihs_replication_loo_by_origin.csv", index=False)

    print(results.sort_values(["sample", "candidate_universe", "mean_log_loss"]).to_string(index=False))
    print("\nPAIRED\n", comparisons.to_string(index=False))


if __name__ == "__main__":
    main()
