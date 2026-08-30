#!/usr/bin/env python3
"""Final integrity freeze for the BIHS expansion and cross-dataset synthesis."""

from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs/tables"
R = ROOT / "outputs/reports"


def main():
    validation = pd.read_csv(T / "bihs_replication_validation.csv")
    if len(validation) != 50 or not validation.passed.all():
        raise RuntimeError("Final validation must contain exactly 50 passing checks")

    required = [
        ROOT / "data/raw/bihs/metadata/selected_file_manifest.csv",
        T / "bgd_district_universe.csv", T / "bgd_origin_destination_matrix.csv",
        T / "bemp_stage4_district_gis_features.csv",
        T / "bihs_file_inventory.csv", T / "bihs_migration_variable_audit.csv",
        T / "bihs_internal_migration_events.csv", T / "bihs_household_relocation_events.csv",
        T / "bihs_district_crosswalk.csv", T / "bihs_sample_flow.csv",
        T / "bihs_external_replication_freeze_manifest.csv",
        T / "bihs_replication_choice_set.csv",
        T / "bihs_replication_model_results_grouped.csv",
        T / "bihs_replication_paired_comparisons_grouped.csv",
        T / "bihs_replication_model_results_wave.csv",
        T / "bihs_replication_model_results_loo.csv",
        T / "bihs_replication_paired_comparisons_loo.csv",
        T / "bihs_replication_loo_by_origin.csv",
        T / "bihs_replication_all_model_results.csv",
        T / "bihs_replication_all_paired_comparisons.csv",
        T / "bihs_replication_validation.csv",
        T / "cross_dataset_replication_summary.csv",
        T / "cross_dataset_interpretation_matrix.csv",
        R / "bihs_destination_feasibility_audit.md",
        R / "bihs_external_replication_design_freeze.md",
        R / "bihs_external_replication_results_checkpoint.md",
        R / "bangladesh_climate_destination_choice_final_synthesis.md",
        ROOT / "work/build_bihs_expansion_audit.py",
        ROOT / "work/fit_bihs_external_replication.py",
        ROOT / "work/combine_bihs_loo_results.py",
        ROOT / "work/validate_bihs_replication.py",
        ROOT / "work/build_cross_dataset_synthesis.py",
        Path(__file__),
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing required final artifacts: {missing}")

    rows = []
    for p in required:
        data = p.read_bytes()
        rows.append({
            "artifact": str(p.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "final_freeze_status": "FROZEN",
        })
    out = pd.DataFrame(rows)
    out.to_csv(T / "bihs_replication_final_freeze_manifest.csv", index=False)
    print(f"Frozen {len(out)} artifacts; all {len(validation)} validation checks pass.")
    print(out.tail(12).to_string(index=False))


if __name__ == "__main__":
    main()
