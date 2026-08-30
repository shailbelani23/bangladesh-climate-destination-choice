#!/usr/bin/env python3
"""Validate and freeze Stage 3 pre-model artifacts."""

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs/tables"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    timing = pd.read_csv(TABLES / "bemp_stage3_event_timing.csv")
    metrics = pd.read_csv(TABLES / "bemp_stage3_sample_concentration.csv")
    dest = pd.read_csv(TABLES / "bemp_stage3_destination_support.csv")
    waves = pd.read_csv(TABLES / "bemp_stage3_wave_support.csv")
    errors = pd.read_csv(TABLES / "bemp_stage3_baseline_error_by_origin.csv")
    registry = pd.read_csv(TABLES / "bemp_stage3_gis_source_registry.csv")
    checks = []

    def add(name, passed, observed, expected):
        checks.append({"check": name, "passed": bool(passed), "observed": str(observed), "expected": str(expected)})

    add("timing rows", len(timing) == 573, len(timing), 573)
    add("timing event IDs unique", timing.event_id.is_unique, timing.event_id.nunique(), 573)
    add("all prior dates recovered", timing.prior_interview_date.notna().all(), timing.prior_interview_date.notna().sum(), 573)
    add("respondent prior dates", (timing.prior_interview_basis == "respondent").sum() == 571, int((timing.prior_interview_basis == "respondent").sum()), 571)
    add("household fallback dates", (timing.prior_interview_basis == "household").sum() == 2, int((timing.prior_interview_basis == "household").sum()), 2)
    event_date = pd.to_datetime(timing.event_interview_date)
    prior_date = pd.to_datetime(timing.prior_interview_date)
    cutoff = pd.to_datetime(timing.strict_feature_cutoff_date)
    add("prior date precedes event", (prior_date < event_date).all(), "all", "all")
    add("strict cutoff is prior minus one day", (cutoff == prior_date - pd.Timedelta(days=1)).all(), "all", "all")
    add("annual feature year strictly complete", (timing.latest_complete_annual_feature_year == cutoff.dt.year - 1).all(), "all", "all")
    add("nine events require 2020 or earlier", (timing.latest_complete_annual_feature_year == 2020).sum() == 9, int((timing.latest_complete_annual_feature_year == 2020).sum()), 9)
    add("intervals positive", timing.event_interval_days_upper_bound.gt(0).all(), int(timing.event_interval_days_upper_bound.min()), ">0")

    expected_samples = {"all_district_events", "household_relocation", "household_lagged_shock_yes", "household_lagged_shock_observed"}
    add("four analysis samples", set(metrics["sample"]) == expected_samples, sorted(metrics["sample"]), sorted(expected_samples))
    expected_events = {"all_district_events": 573, "household_relocation": 264, "household_lagged_shock_yes": 184, "household_lagged_shock_observed": 262}
    observed_events = metrics.set_index("sample").events.to_dict()
    add("sample event counts", observed_events == expected_events, observed_events, expected_events)
    add("climate interdistrict count", int(metrics.set_index("sample").loc["household_lagged_shock_yes", "cross_district_events"]) == 71, int(metrics.set_index("sample").loc["household_lagged_shock_yes", "cross_district_events"]), 71)
    add("climate effective destinations below eight", metrics.set_index("sample").loc["household_lagged_shock_yes", "effective_destination_count_exp_entropy"] < 8, round(metrics.set_index("sample").loc["household_lagged_shock_yes", "effective_destination_count_exp_entropy"], 3), "<8")
    add("destination shares sum to one", dest.groupby("sample").share.sum().sub(1).abs().lt(1e-10).all(), dest.groupby("sample").share.sum().round(12).to_dict(), "all 1")
    add("wave event totals reconcile", waves.groupby("sample").events.sum().to_dict() == expected_events, waves.groupby("sample").events.sum().to_dict(), expected_events)
    add("baseline error table complete", errors.notna().all().all(), int(errors.isna().sum().sum()), 0)

    add("GIS registry rows", len(registry) == 10, len(registry), 10)
    add("GIS priorities unique 1-10", set(registry.priority) == set(range(1, 11)), sorted(registry.priority), list(range(1, 11)))
    add("exactly four primary constructs", registry.model_role.str.startswith("PRIMARY").sum() == 4, int(registry.model_role.str.startswith("PRIMARY").sum()), 4)
    add("primary constructs universally pre-period", registry.loc[registry.model_role.str.startswith("PRIMARY"), "time_rule"].str.contains("Universally|universally").all(), "all", "all")
    add("no GIS source downloaded", registry.download_status.str.contains("not downloaded|blocked").all(), "all deferred", "all deferred")
    add("source verification date complete", registry.metadata_verified_date.eq("2026-08-28").all(), registry.metadata_verified_date.unique().tolist(), ["2026-08-28"])

    out = pd.DataFrame(checks)
    out.to_csv(TABLES / "bemp_stage3_validation.csv", index=False)
    core = [
        "bemp_stage3_event_timing.csv", "bemp_stage3_sample_concentration.csv",
        "bemp_stage3_destination_support.csv", "bemp_stage3_wave_support.csv",
        "bemp_stage3_baseline_error_by_origin.csv", "bemp_stage3_gis_source_registry.csv",
        "../reports/bemp_stage3_identification_audit.md", "../reports/bemp_stage3_gis_feature_spec.md",
    ]
    frozen = []
    for rel in core:
        path = (TABLES / rel).resolve()
        row = {"relative_path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path), "rows": "", "columns": ""}
        if path.suffix == ".csv":
            x = pd.read_csv(path, low_memory=False)
            row["rows"], row["columns"] = len(x), len(x.columns)
        frozen.append(row)
    pd.DataFrame(frozen).to_csv(TABLES / "bemp_stage3_freeze_manifest.csv", index=False)

    print(out.to_string(index=False))
    failed = out[~out.passed]
    print(f"\n{len(out)-len(failed)}/{len(out)} checks passed")
    if len(failed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
