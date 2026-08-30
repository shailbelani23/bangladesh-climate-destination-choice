from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))
import build_bemp_stage1_events as base  # noqa: E402


TABLES = ROOT / "outputs" / "tables"


def main():
    recalled = pd.read_csv(TABLES / "bemp_recalled_migration_history.csv", low_memory=False)
    flow = pd.read_csv(TABLES / "bemp_recalled_history_flow.csv")
    duplicates = pd.read_csv(TABLES / "bemp_respondent_duplicate_audit.csv")
    households = pd.read_csv(TABLES / "bemp_household_key_reconciliation.csv", low_memory=False)

    checks: dict[str, dict] = {}

    def check(name: str, passed, detail=""):
        checks[name] = {"passed": bool(passed), "detail": str(detail)}

    check("recalled_rows", len(recalled) == 1039, len(recalled))
    check("recalled_ids_unique", recalled["recalled_record_id"].is_unique)
    check("no_recalled_primary_ledger_recommendations", not recalled["recommended_for_primary_prospective_ledger"].any())
    check("flow_reported_move_total", int(flow["reported_moves_total"].sum()) == 2290, int(flow["reported_moves_total"].sum()))
    check("flow_captured_record_total", int(flow["captured_records"].sum()) == len(recalled), int(flow["captured_records"].sum()))
    check(
        "flow_representation_identity",
        (flow["represented_moves_total"] + flow["unrepresented_moves_total"]).eq(flow["reported_moves_total"]).all(),
    )
    check("represented_move_total", int(flow["represented_moves_total"].sum()) == 2126, int(flow["represented_moves_total"].sum()))
    check("unrepresented_move_total", int(flow["unrepresented_moves_total"].sum()) == 164, int(flow["unrepresented_moves_total"].sum()))
    check("exact_overlap_count", int(recalled["current_event_overlap_exact"].sum()) == 310, int(recalled["current_event_overlap_exact"].sum()))
    check("possible_overlap_count", int(recalled["possible_current_destination_overlap"].sum()) == 17, int(recalled["possible_current_destination_overlap"].sum()))
    check(
        "overlaps_excluded_from_sensitivity",
        not recalled.loc[
            recalled["current_event_overlap_exact"] | recalled["possible_current_destination_overlap"],
            "recalled_sensitivity_eligible",
        ].any(),
    )
    expected_eligible = (
        recalled["domestic_abroad"].eq("In Bangladesh")
        & recalled["destination_resolution_status"].eq("resolved")
        & recalled["timing_inference_valid"]
        & ~recalled["current_event_overlap_exact"]
        & ~recalled["possible_current_destination_overlap"]
    )
    check("sensitivity_formula", recalled["recalled_sensitivity_eligible"].eq(expected_eligible).all())
    check("sensitivity_count", int(expected_eligible.sum()) == 319, int(expected_eligible.sum()))
    check(
        "household_sensitivity_count",
        int(recalled["recalled_household_relocation_sensitivity_eligible"].sum()) == 18,
        int(recalled["recalled_household_relocation_sensitivity_eligible"].sum()),
    )
    check("timing_valid_count", int(recalled["timing_inference_valid"].sum()) == 854, int(recalled["timing_inference_valid"].sum()))
    check("resolved_recalled_endpoint_count", int(recalled["destination_resolution_status"].eq("resolved").sum()) == 685, int(recalled["destination_resolution_status"].eq("resolved").sum()))

    source_errors = []
    source_cache = {
        wave: pd.read_csv(base.data_path(wave), usecols=[base.ID_VAR[wave]], low_memory=False)
        for wave in recalled["wave"].unique()
    }
    for rec in recalled.itertuples(index=False):
        wave = rec.wave
        index = int(rec.source_row_csv_1_based) - 2
        source = source_cache[wave]
        if index not in source.index or str(source.loc[index, base.ID_VAR[wave]]) != rec.respondent_id:
            source_errors.append(rec.recalled_record_id)
    check("recalled_source_row_linkage", not source_errors, source_errors[:10])

    check("duplicate_audit_rows", len(duplicates) == 10, len(duplicates))
    pair_counts = duplicates.groupby(["wave", "respondent_id"])["adjudication_keep"].agg(["size", "sum"])
    check("five_duplicate_pairs", len(pair_counts) == 5, len(pair_counts))
    check("one_duplicate_retained_per_pair", pair_counts["size"].eq(2).all() and pair_counts["sum"].eq(1).all())
    check("duplicate_latest_date_retained", all(
        pd.to_datetime(group.loc[group["adjudication_keep"], "interview_date"]).max()
        == pd.to_datetime(group["interview_date"]).max()
        for _, group in duplicates.groupby(["wave", "respondent_id"])
    ))

    check("household_prefix_rows", len(households) == 1704, len(households))
    check("household_prefix_unique", households["household_id_derived"].is_unique)
    check(
        "household_prefix_format",
        households["household_id_derived"].astype(str).str.match(r"^L\d{2}(?:-Z\d{2})?-HH\d{2}$").all(),
    )
    check("no_head_prefix_count", int(households["no_public_baseline_head_flag"].sum()) == 19, int(households["no_public_baseline_head_flag"].sum()))
    check("panel_only_prefix_count", int(households["panel_only_prefix_flag"].sum()) == 1, int(households["panel_only_prefix_flag"].sum()))
    check("no_multiple_baseline_heads", not households["multiple_public_baseline_heads_flag"].any())
    check("all_household_prefixes_recommended_as_cluster_key", households["recommended_cluster_key"].all())
    check("medium_confidence_prefix_count", int(households["household_key_confidence"].eq("medium").sum()) == 20, int(households["household_key_confidence"].eq("medium").sum()))

    # The public loop data include district-selection flags, but every associated
    # rural district free-text field is structurally missing/redacted.
    valid_rural_text = 0
    for wave in ["w6_N", "w6_M", "w12_N", "w12_M", "w14_N", "w14_M"]:
        cb = base.codebook(wave)
        variables = cb.loc[
            cb["Variable label"].astype(str).str.contains(r"_villg5_txt_loop[123]$", regex=True),
            "Variable name",
        ].astype(str).tolist()
        data = pd.read_csv(base.data_path(wave), usecols=variables, low_memory=False)
        for variable in variables:
            valid_rural_text += int(data[variable].map(base.normalize_scalar).notna().sum())
    check("retrospective_rural_district_text_publicly_empty", valid_rural_text == 0, valid_rural_text)

    result = {"all_passed": all(item["passed"] for item in checks.values()), "check_count": len(checks), "checks": checks}
    print(json.dumps(result, indent=2))
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
