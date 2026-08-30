from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bemp" / "quantitative"
TABLES = ROOT / "outputs" / "tables"

events = pd.read_csv(TABLES / "bemp_prospective_migration_events.csv", low_memory=False)
state = pd.read_csv(TABLES / "bemp_respondent_wave_state.csv", low_memory=False)
crosswalk = pd.read_csv(TABLES / "bemp_destination_admin_crosswalk.csv", low_memory=False)
duplicate_adjudication = pd.read_csv(TABLES / "bemp_duplicate_adjudication.csv", low_memory=False)
flow = pd.read_csv(TABLES / "bemp_stage1_sample_flow.csv", low_memory=False)
dictionary = pd.read_csv(TABLES / "bemp_stage1_data_dictionary.csv", low_memory=False)

checks = {}


def check(name, condition, detail=""):
    ok = bool(condition)
    checks[name] = {"passed": ok, "detail": detail}
    if not ok:
        raise AssertionError(f"{name}: {detail}")


check("event_rows", len(events) == 1066, str(len(events)))
check("event_ids_unique", events["event_id"].is_unique)
check("respondent_ids_complete", events["respondent_id"].notna().all())
check("origin_district_complete", events["origin_district_codebook"].notna().all())
check("state_rows", len(state) == 27662, str(len(state)))
check("crosswalk_rows", len(crosswalk) == 127, str(len(crosswalk)))
check("duplicate_adjudication_rows", len(duplicate_adjudication) == 4, str(len(duplicate_adjudication)))
check("flow_rows", len(flow) == 18, str(len(flow)))
check("dictionary_rows", len(dictionary) == 163, str(len(dictionary)))

check(
    "new_destination_count",
    int(events["is_new_destination_event"].sum()) == 659,
    str(int(events["is_new_destination_event"].sum())),
)
check(
    "return_count",
    int(events["is_return_event"].sum()) == 220,
    str(int(events["is_return_event"].sum())),
)
check(
    "named_endpoint_stage_count",
    int(events["stage1_named_endpoint_eligible"].sum()) == 573,
    str(int(events["stage1_named_endpoint_eligible"].sum())),
)
check(
    "district_endpoint_stage_count",
    int(events["stage1_district_endpoint_eligible"].sum()) == 573,
    str(int(events["stage1_district_endpoint_eligible"].sum())),
)
check(
    "household_stage_count",
    int(events["stage1_household_relocation_eligible"].sum()) == 264,
    str(int(events["stage1_household_relocation_eligible"].sum())),
)
check(
    "climate_screen_count",
    int(events["stage1_climate_screen_eligible"].sum()) == 215,
    str(int(events["stage1_climate_screen_eligible"].sum())),
)

expected_named = (
    events["is_new_destination_event"]
    & events["domestic_event"]
    & events["destination_named_admin_available"]
    & events["duplicate_adjudication_keep"]
)
check(
    "named_stage_flag_formula",
    events["stage1_named_endpoint_eligible"].equals(expected_named),
)
expected_district = expected_named & events["destination_district_endpoint_available"]
expected_household = expected_district & events["move_scope"].isin(
    ["I took the whole household along", "I took parts of the household along"]
)
check(
    "household_stage_flag_formula",
    events["stage1_household_relocation_eligible"].equals(expected_household),
)
check(
    "district_stage_flag_formula",
    events["stage1_district_endpoint_eligible"].equals(expected_district),
)

check(
    "crosswalk_counts_reconcile",
    int(crosswalk["event_count"].sum()) == int(events["destination_admin_raw"].notna().sum()),
    f"{int(crosswalk['event_count'].sum())} vs {int(events['destination_admin_raw'].notna().sum())}",
)
check(
    "all_named_endpoints_resolved",
    events.loc[events["destination_named_admin_available"], "destination_district_official"].notna().all(),
)
check(
    "crosswalk_all_resolved",
    crosswalk["destination_district_official"].notna().all(),
)
check(
    "official_sources_complete",
    crosswalk["destination_resolution_source_url"].notna().all(),
)
check(
    "city_lookup_complete",
    not events["needs_city_to_district_lookup"].any(),
)
check(
    "duplicate_one_retained_per_pair",
    duplicate_adjudication.groupby(["respondent_id", "wave"])["duplicate_adjudication_keep"].sum().eq(1).all(),
)
check(
    "duplicate_raw_rows_preserved",
    int(events["duplicate_respondent_wave_flag"].sum()) == 4,
)

flow_main = flow[flow["step"].astype(str).str.fullmatch(r"\d+")]
expected_flow = [1066, 659, 656, 575, 575, 573, 264, 262, 215]
check(
    "sample_flow_reconciles",
    flow_main["remaining_events"].astype(int).tolist() == expected_flow,
    str(flow_main["remaining_events"].astype(int).tolist()),
)

unmapped17 = events[
    events["destination_city_category"].astype(str).eq("unmapped public code 17")
]
check("unmapped_code_17_one_record", len(unmapped17) == 1, str(len(unmapped17)))
check(
    "unmapped_code_17_not_named",
    (~unmapped17["destination_named_admin_available"]).all(),
)

source_cache = {}
source_failures = []
rule_failures = []
for e in events.itertuples(index=False):
    if e.source_file not in source_cache:
        source_cache[e.source_file] = pd.read_csv(RAW / e.source_file, low_memory=False)
    src = source_cache[e.source_file]
    source_index = int(e.source_row_csv_1_based) - 2
    row = src.iloc[source_index]
    if str(row[e.respondent_id_variable]) != str(e.respondent_id):
        source_failures.append(e.event_id)
        continue

    w = e.wave
    if e.event_class == "first_observed_current_migrant_destination":
        if row["w6_M_q14"] not in {1, 2}:
            rule_failures.append(e.event_id)
    elif e.event_class == "new_other_destination" and w in {
        "w7", "w8", "w9", "w10", "w11", "w13"
    }:
        if row[f"{w}_q1"] != 3:
            rule_failures.append(e.event_id)
    elif e.event_class == "return_to_baseline_home":
        if not (row[f"{w}_q1"] == 1 and row[f"{w}_reg5"] == 2):
            rule_failures.append(e.event_id)
    elif w == "w12_M":
        if not (row["w12_M_reg10"] in {1, 3} or row["w12_M_q16"] == 2):
            rule_failures.append(e.event_id)
    elif w == "w14_M":
        if not (row["w14_M_reg11"] in {1, 3} or row["w14_M_q16"] == 2):
            rule_failures.append(e.event_id)

check("source_row_linkage", not source_failures, json.dumps(source_failures[:10]))
check("event_detection_rules", not rule_failures, json.dumps(rule_failures[:10]))

state_source_failures = []
for e in state.sample(n=min(500, len(state)), random_state=20260828).itertuples(index=False):
    if e.source_file not in source_cache:
        source_cache[e.source_file] = pd.read_csv(RAW / e.source_file, low_memory=False)
    src = source_cache[e.source_file]
    row = src.iloc[int(e.source_row_csv_1_based) - 2]
    if str(row[e.respondent_id_variable]) != str(e.respondent_id):
        state_source_failures.append((e.respondent_id, e.wave))
check(
    "state_source_linkage_500_row_sample",
    not state_source_failures,
    json.dumps(state_source_failures[:10]),
)

result = {
    "all_passed": all(x["passed"] for x in checks.values()),
    "check_count": len(checks),
    "checks": checks,
}
(ROOT / "work" / "bemp_stage1_validation.json").write_text(
    json.dumps(result, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, indent=2))
