#!/usr/bin/env python3
"""Build the frozen manuscript-number registry from final machine-readable tables."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs" / "tables"
OUT = ROOT / "publication" / "qa" / "manuscript_number_registry.csv"


def fmt(x, digits=3):
    return f"{float(x):.{digits}f}"


def row(summary, dataset, sample, universe, scheme):
    z = summary[
        summary.dataset.eq(dataset)
        & summary["sample"].eq(sample)
        & summary.candidate_universe.eq(universe)
        & summary.validation_scheme.eq(scheme)
    ]
    if len(z) != 1:
        raise RuntimeError((dataset, sample, universe, scheme, len(z)))
    return z.iloc[0]


def main():
    s = pd.read_csv(T / "cross_dataset_replication_summary.csv")
    p = pd.read_csv(T / "bihs_replication_oof_predictions_grouped.csv", low_memory=False)
    v = pd.read_csv(T / "bihs_internal_migration_events.csv", low_memory=False)
    rows = []

    specs = [
        ("C01", "BEMP", "household_lagged_shock_yes", "full_64", "household_grouped_5fold"),
        ("C02", "BIHS", "b4_erosion", "full_64", "household_grouped_5fold"),
        ("C03", "BIHS", "b4_erosion", "interdistrict_63", "household_grouped_5fold"),
        ("C04", "BIHS", "v1_interval", "full_64", "household_grouped_5fold"),
        ("C05", "BIHS", "v1_interval", "interdistrict_63", "household_grouped_5fold"),
        ("C06", "BIHS", "v1_interval", "full_64", "leave_one_origin_out"),
        ("C07", "BIHS", "v1_interval", "interdistrict_63", "leave_one_origin_out"),
        ("C08", "BIHS", "b4_erosion", "full_64", "leave_one_origin_out"),
        ("C09", "BIHS", "b4_erosion", "interdistrict_63", "leave_one_origin_out"),
        ("C10", "BIHS", "v1_interval", "full_64", "wave_holdout_r3"),
        ("C11", "BIHS", "v1_interval", "interdistrict_63", "wave_holdout_r3"),
    ]
    for claim_id, dataset, sample, universe, scheme in specs:
        x = row(s, dataset, sample, universe, scheme)
        ci = ""
        if pd.notna(x.cluster_bootstrap_ci_low):
            ci = f"[{fmt(x.cluster_bootstrap_ci_low)}, {fmt(x.cluster_bootstrap_ci_high)}]"
        rows.append({
            "claim_id": claim_id,
            "dataset": dataset,
            "sample": sample,
            "candidate_universe": universe,
            "validation_scheme": scheme,
            "n_events": int(x.n_events_evaluated),
            "gravity_log_loss": fmt(x.gravity_mean_log_loss),
            "gis_log_loss": fmt(x.mean_log_loss),
            "gis_gain": fmt(x.log_loss_improvement_vs_gravity),
            "cluster_95_interval": ci,
            "source_file": "outputs/tables/cross_dataset_replication_summary.csv",
            "release_status": "FROZEN",
        })

    event_id = "BIHS-B4-W2-0053"
    z = p[
        p.event_id.eq(event_id)
        & p["sample"].eq("b4_erosion")
        & p.candidate_universe.eq("full_64")
        & p.model.isin(["gravity_mle_disk_within", "gis_joint_ridge"])
    ].copy()
    if len(z) != 2:
        raise RuntimeError("Household illustration predictions are not unique")
    for model, claim_id in [("gravity_mle_disk_within", "H01"), ("gis_joint_ridge", "H02")]:
        x = z[z.model.eq(model)].iloc[0]
        rows.append({
            "claim_id": claim_id,
            "dataset": "BIHS",
            "sample": "anonymized_household_illustration",
            "candidate_universe": "full_64",
            "validation_scheme": "household_grouped_5fold",
            "n_events": 1,
            "gravity_log_loss": "",
            "gis_log_loss": "",
            "gis_gain": "",
            "cluster_95_interval": "",
            "source_file": "outputs/tables/bihs_replication_oof_predictions_grouped.csv",
            "release_status": "FROZEN",
            "model": model,
            "chosen_probability": f"{100 * x.chosen_probability:.1f}%",
            "chosen_rank": int(x.chosen_expected_rank),
        })

    primary = v[v.primary_interval_sample.eq(True)]
    helped = primary.destination_help_label.eq("Friends/family in the migrated location").sum()
    rows.append({
        "claim_id": "N01",
        "dataset": "BIHS",
        "sample": "v1_interval",
        "candidate_universe": "",
        "validation_scheme": "descriptive",
        "n_events": len(primary),
        "gravity_log_loss": "",
        "gis_log_loss": "",
        "gis_gain": "",
        "cluster_95_interval": "",
        "source_file": "outputs/tables/bihs_internal_migration_events.csv",
        "release_status": "FROZEN",
        "model": "",
        "chosen_probability": "",
        "chosen_rank": "",
        "network_help_count": int(helped),
    })

    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(OUT)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
