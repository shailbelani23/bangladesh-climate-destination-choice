#!/usr/bin/env python3
"""Create exact cross-dataset result tables from frozen BEMP and BIHS outputs."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs/tables"


def add_ci(result, paired):
    paired = paired.copy()
    if "validation_scheme" not in paired:
        paired["validation_scheme"] = "household_grouped_5fold"
    keys = ["sample", "candidate_universe", "validation_scheme", "model"]
    q = paired[paired.comparator.eq("gravity_mle_disk_within")][
        keys + ["mean_log_loss_improvement", "cluster_bootstrap_ci_low", "cluster_bootstrap_ci_high"]
    ].drop_duplicates(keys)
    return result.merge(q, on=keys, how="left", validate="many_to_one")


def main():
    bg = pd.read_csv(T / "bihs_replication_model_results_grouped.csv")
    bw = pd.read_csv(T / "bihs_replication_model_results_wave.csv")
    bl = pd.read_csv(T / "bihs_replication_model_results_loo.csv")
    bp_g = pd.read_csv(T / "bihs_replication_paired_comparisons_grouped.csv")
    bp_l = pd.read_csv(T / "bihs_replication_paired_comparisons_loo.csv")
    bihs = pd.concat([bg, bw, bl], ignore_index=True)
    bihs.to_csv(T / "bihs_replication_all_model_results.csv", index=False)
    pd.concat([bp_g.assign(validation_scheme="household_grouped_5fold"),
               bp_l.assign(validation_scheme="leave_one_origin_out")], ignore_index=True).to_csv(
        T / "bihs_replication_all_paired_comparisons.csv", index=False
    )

    direct = bihs[bihs.model.eq("gis_joint_ridge")].copy()
    direct["dataset"] = "BIHS"
    direct = add_ci(direct, pd.concat([
        bp_g.assign(validation_scheme="household_grouped_5fold"),
        bp_l.assign(validation_scheme="leave_one_origin_out"),
    ], ignore_index=True))

    br = pd.read_csv(T / "bemp_stage5_model_results.csv")
    bb = pd.read_csv(T / "bemp_stage5_paired_logloss_comparisons.csv")
    bemp = br[(br.model.eq("gis_joint_ridge")) &
              (br["sample"].isin(["household_lagged_shock_yes", "household_relocation"])) &
              (br.validation_scheme.isin(["household_grouped_5fold", "leave_one_origin_out"]))].copy()
    bemp["dataset"] = "BEMP"
    # BEMP paired intervals are available for grouped CV only.
    bemp = add_ci(bemp, bb)

    keep = ["dataset", "sample", "candidate_universe", "validation_scheme", "n_events_evaluated",
            "gravity_mean_log_loss", "mean_log_loss", "log_loss_improvement_vs_gravity",
            "cluster_bootstrap_ci_low", "cluster_bootstrap_ci_high", "top1_accuracy", "mean_rank"]
    out = pd.concat([bemp[keep], direct[keep]], ignore_index=True)
    labels = {
        "household_lagged_shock_yes": "BEMP shock-linked household relocations",
        "household_relocation": "BEMP all household relocations",
        "b4_erosion": "BIHS river-erosion household relocations",
        "b4_all": "BIHS all household relocations",
        "v1_interval": "BIHS interval-specific current migrants",
    }
    out.insert(2, "sample_label", out["sample"].map(labels))
    out = out.sort_values(["dataset", "sample", "validation_scheme", "candidate_universe"])
    out.to_csv(T / "cross_dataset_replication_summary.csv", index=False)

    # Compact interpretation matrix.
    matrix = []
    for _, r in out.iterrows():
        ci = "not computed"
        if pd.notna(r.cluster_bootstrap_ci_low):
            ci = "positive" if r.cluster_bootstrap_ci_low > 0 else (
                "negative" if r.cluster_bootstrap_ci_high < 0 else "crosses zero"
            )
        matrix.append({
            "dataset": r["dataset"], "sample": r["sample"],
            "candidate_universe": r["candidate_universe"],
            "validation_scheme": r["validation_scheme"], "n_events": int(r["n_events_evaluated"]),
            "gis_gain_direction": "positive" if r["log_loss_improvement_vs_gravity"] > 0 else "negative",
            "gis_gain_vs_gravity": r["log_loss_improvement_vs_gravity"],
            "cluster_interval_assessment": ci,
        })
    pd.DataFrame(matrix).to_csv(T / "cross_dataset_interpretation_matrix.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
