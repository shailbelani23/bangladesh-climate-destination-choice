from __future__ import annotations

import calendar
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))

import build_bemp_stage1_events as base  # noqa: E402


OUT = ROOT / "outputs" / "tables"

STREAMS = [
    ("w6_N", "main_nonmigrant", "w6_N_migr_resp"),
    ("w6_M", "main_migrant", "w6_M_migr_resp"),
    ("w12_N", "main_nonmigrant", "w12_N_migr_resp"),
    ("w12_M", "main_migrant", "w12_M_migr_resp"),
    ("w12_M", "secondary_migrant", "w12_M_scndr_migr_resp"),
    ("w14_N", "main_nonmigrant", "w14_N_migr_resp"),
    ("w14_M", "main_migrant", "w14_M_migr_resp"),
    ("w14_M", "secondary_migrant", "w14_M_scndr_migr_resp"),
]

CLIMATE_PUSH_ITEMS = {
    1: "riverbank_erosion",
    2: "monsoon_flood",
    3: "other_sudden_disaster",
    4: "drought_water_shortage",
    5: "other_environmental",
}

DEST_REASON_ITEMS = {
    1: "relatives",
    2: "better_earning",
    3: "safer_flood",
    4: "safer_erosion",
    5: "schooling",
    6: "marriage",
    7: "property",
}


def label_index(wave: str) -> tuple[dict[str, str], dict[str, str]]:
    cb = base.codebook(wave)
    label_to_var = dict(zip(cb["Variable label"].astype(str), cb["Variable name"].astype(str)))
    var_to_label = dict(zip(cb["Variable name"].astype(str), cb["Variable label"].astype(str)))
    return label_to_var, var_to_label


def var_for(label_to_var: dict[str, str], label: str) -> str | None:
    return label_to_var.get(label)


def get_raw(row: pd.Series, variable: str | None):
    return base.normalize_scalar(row.get(variable)) if variable else None


def get_decoded(wave: str, row: pd.Series, variable: str | None):
    return base.decoded(wave, variable, row.get(variable)) if variable else None


def selected_any(wave: str, row: pd.Series, variables: list[str]) -> bool | None:
    observed = False
    selected = False
    for variable in variables:
        raw = base.normalize_scalar(row.get(variable))
        if raw is None:
            continue
        observed = True
        decoded = str(base.decoded(wave, variable, raw)).casefold()
        if raw == 1 or decoded.startswith("selected") or decoded.startswith("yes"):
            selected = True
    return selected if observed else None


def matching_item_vars(
    cb: pd.DataFrame,
    prefix: str,
    loop: int,
    item: int,
    kind: str,
) -> list[str]:
    labels = cb["Variable label"].astype(str)
    if kind == "push":
        pattern = rf"^{re.escape(prefix)}_reasn_(?:one_move|multi_moves){item}_loop{loop}$"
    else:
        pattern = rf"^{re.escape(prefix)}_(?:cntr_|city_|villg_)?(?:dest_)?choic_reasn{item}_loop{loop}$"
    return cb.loc[labels.str.match(pattern), "Variable name"].astype(str).tolist()


def find_suffix_var(label_to_var: dict[str, str], prefix: str, suffixes: list[str]) -> str | None:
    for suffix in suffixes:
        found = label_to_var.get(prefix + suffix)
        if found:
            return found
    return None


def parse_month(month_value) -> tuple[int | None, int | None]:
    if month_value is None:
        return None, None
    text = str(month_value).strip().casefold()
    match = re.fullmatch(r"([a-z]+)\s+(\d{4})", text)
    reported_year = int(match.group(2)) if match else None
    month_text = match.group(1) if match else text
    for number in range(1, 13):
        if month_text in {calendar.month_name[number].casefold(), calendar.month_abbr[number].casefold()}:
            return number, reported_year
    try:
        number = int(float(text))
        return (number, None) if 1 <= number <= 12 else (None, None)
    except ValueError:
        return None, None


def infer_timing(interview_date, month_value, month_part):
    survey = pd.to_datetime(interview_date, errors="coerce")
    month, reported_year = parse_month(month_value)
    if pd.isna(survey) or month is None:
        return {
            "move_month_number": month,
            "inferred_move_date_midpoint": None,
            "timing_precision": "unresolved",
            "recall_days_approx": None,
            "timing_inference_valid": False,
            "timing_inference_rule": "Month or interview date unavailable; no year imputed.",
        }
    part = str(month_part or "").casefold()
    if "begin" in part:
        day, precision = 5, "month_part_midpoint"
    elif "middle" in part:
        day, precision = 15, "month_part_midpoint"
    elif "end" in part:
        day, precision = 25, "month_part_midpoint"
    else:
        day, precision = 15, "month_midpoint"
    year = reported_year if reported_year is not None else (
        survey.year if month <= survey.month else survey.year - 1
    )
    day = min(day, calendar.monthrange(year, month)[1])
    inferred = pd.Timestamp(year=year, month=month, day=day)
    recall_days = int((survey.normalize() - inferred).days)
    valid = 0 <= recall_days <= 397
    return {
        "move_month_number": month,
        "inferred_move_date_midpoint": inferred.date().isoformat(),
        "timing_precision": precision,
        "recall_days_approx": recall_days,
        "timing_inference_valid": valid,
        "timing_inference_rule": (
            ("Reported month and year used directly; " if reported_year is not None else
             "Most recent occurrence of the reported month on/before interview; ")
            +
            "day set to month-part midpoint (5/15/25) or day 15 when month part is missing."
        ),
    }


def current_endpoint(wave: str, row: pd.Series):
    if wave not in base.INPERSON_DEST:
        return None
    cfg = base.INPERSON_DEST[wave]
    if wave == "w6_M":
        domestic = "In Bangladesh"
    else:
        domestic = get_decoded(wave, row, cfg.get("domestic"))
    endpoint = base.endpoint_fields(wave, row, cfg, domestic)
    endpoint.update(base.resolve_admin(endpoint["destination_admin_level_raw"], endpoint["destination_admin_raw"]))
    return endpoint


def loop_endpoint(
    wave: str,
    stream: str,
    prefix: str,
    loop: int,
    frequency: int,
    row: pd.Series,
    label_to_var: dict[str, str],
    origin_district: str | None,
):
    one_or_multi = "one_move" if frequency == 1 else "multi_moves"
    domestic_var = find_suffix_var(
        label_to_var, prefix, [f"_dmstc_abrod_{one_or_multi}_loop{loop}"]
    )
    ru_var = find_suffix_var(label_to_var, prefix, [f"_rural_urban_loop{loop}"])
    city_var = find_suffix_var(label_to_var, prefix, [f"_city_loop{loop}"])
    city_txt_var = find_suffix_var(label_to_var, prefix, [f"_city_txt_loop{loop}"])
    same_var = find_suffix_var(label_to_var, prefix, [f"_same_or_diff_villg_loop{loop}"])
    district_var = find_suffix_var(label_to_var, prefix, [f"_villg5_txt_loop{loop}"])
    division_var = find_suffix_var(label_to_var, prefix, [f"_villg6_txt_loop{loop}"])

    domestic = get_decoded(wave, row, domestic_var)
    ru = get_decoded(wave, row, ru_var)
    same = get_decoded(wave, row, same_var)
    city_raw, city_category = (None, None)
    if city_var:
        city_raw, city_category = base.city_label(
            wave, city_var, row.get(city_var), row.get(city_txt_var)
        )
    district_raw = get_raw(row, district_var)
    division_raw = get_raw(row, division_var)
    level = "unavailable"
    raw = None
    source = "recalled_loop"

    current = current_endpoint(wave, row) if wave.endswith("_M") else None
    if stream == "main_migrant" and frequency == 1 and current:
        domestic = current["domestic_abroad"] or "In Bangladesh"
        ru = current["destination_rural_urban"]
        city_raw = current["destination_admin_raw"] if current["destination_admin_level_raw"] == "city" else None
        city_category = current["destination_city_category"]
        district_raw = current["destination_rural_district_raw"]
        division_raw = current["destination_rural_division_raw"]
        level = current["destination_admin_level_raw"]
        raw = current["destination_admin_raw"]
        source = "current_location_block_fallback"
    elif domestic == "Abroad":
        level = "country_abroad"
    elif same and "home village" in str(same).casefold() and origin_district:
        level, raw, source = "origin_district", origin_district, "home_village_inference"
    elif same and "current location" in str(same).casefold() and current:
        level = current["destination_admin_level_raw"]
        raw = current["destination_admin_raw"]
        source = "current_location_inference"
    elif ru == "City" and city_raw:
        level, raw = "city", city_raw
    elif ru == "Village" and district_raw:
        level, raw = "district", district_raw

    resolution = base.resolve_admin(level, raw)
    return {
        "domestic_abroad": domestic,
        "destination_rural_urban": ru,
        "destination_same_or_different_village": same,
        "destination_city_raw": city_raw,
        "destination_city_category": city_category,
        "destination_rural_district_raw": district_raw,
        "destination_rural_division_raw": division_raw,
        "destination_admin_level_raw": level,
        "destination_admin_raw": raw,
        "destination_endpoint_source": source,
        **resolution,
        "domestic_abroad_variable": domestic_var,
        "destination_rural_urban_variable": ru_var,
        "destination_city_variable": city_var,
        "destination_city_text_variable": city_txt_var,
        "destination_same_village_variable": same_var,
        "destination_district_text_variable": district_var,
        "destination_division_text_variable": division_var,
    }


def build_recalled_history():
    records: list[dict] = []
    stream_summaries: list[dict] = []
    for wave, stream, prefix in STREAMS:
        data = pd.read_csv(base.data_path(wave), low_memory=False)
        cb = base.codebook(wave)
        label_to_var, _ = label_index(wave)
        freq_var = var_for(label_to_var, prefix + "_freq")
        freq_txt_var = var_for(label_to_var, prefix + "_freq_txt")
        for row_index, row in data.iterrows():
            freq_raw = get_raw(row, freq_txt_var)
            try:
                frequency = int(float(freq_raw)) if freq_raw is not None else None
            except (TypeError, ValueError):
                frequency = None
            if not frequency or frequency < 1:
                continue
            respondent_id = str(row[base.ID_VAR[wave]])
            household, lxx, origin = base.person_parts(respondent_id)
            interview_date = get_raw(row, f"{wave}_date")
            loop_payloads = []
            for loop in range(1, 4):
                one_or_multi = "one_move" if frequency == 1 else "multi_moves"
                month_var = find_suffix_var(
                    label_to_var,
                    prefix,
                    [f"_month_{one_or_multi}_loop{loop}", f"_month_{one_or_multi}_txt_loop{loop}"],
                )
                month_part_var = find_suffix_var(
                    label_to_var, prefix, [f"_month_part_{one_or_multi}_loop{loop}"]
                )
                seasonal_var = find_suffix_var(label_to_var, prefix, [f"_seasl_pttrn_loop{loop}"])
                duration_var = find_suffix_var(label_to_var, prefix, [f"_durat_loop{loop}"])
                duration_txt_var = find_suffix_var(label_to_var, prefix, [f"_durat_txt_loop{loop}"])
                scope_var = find_suffix_var(label_to_var, prefix, [f"_indiv_or_hh_loop{loop}"])
                identical_var = find_suffix_var(label_to_var, prefix, [f"_moves_ident_loop{loop}"])
                return_var = find_suffix_var(label_to_var, prefix, [f"_retrn_route_loop{loop}"])

                push_vars = {
                    name: matching_item_vars(cb, prefix, loop, number, "push")
                    for number, name in CLIMATE_PUSH_ITEMS.items()
                }
                reason_vars = {
                    name: matching_item_vars(cb, prefix, loop, number, "destination")
                    for number, name in DEST_REASON_ITEMS.items()
                }
                push_values = {name: selected_any(wave, row, variables) for name, variables in push_vars.items()}
                reason_values = {name: selected_any(wave, row, variables) for name, variables in reason_vars.items()}
                endpoint = loop_endpoint(wave, stream, prefix, loop, frequency, row, label_to_var, origin)
                core_vars = [
                    month_var, month_part_var, seasonal_var, duration_var, duration_txt_var,
                    scope_var, identical_var, return_var,
                    endpoint["domestic_abroad_variable"], endpoint["destination_rural_urban_variable"],
                    endpoint["destination_city_variable"], endpoint["destination_city_text_variable"],
                    endpoint["destination_same_village_variable"], endpoint["destination_district_text_variable"],
                ] + [v for variables in push_vars.values() for v in variables] + [v for variables in reason_vars.values() for v in variables]
                observed = any(base.is_valid(row.get(v)) for v in core_vars if v)
                # Migrant main-stream single moves put geography in the current-location block.
                if stream == "main_migrant" and frequency == 1 and loop == 1:
                    observed = observed or endpoint["destination_endpoint_source"] == "current_location_block_fallback"
                if not observed:
                    continue

                month_value = get_decoded(wave, row, month_var)
                month_part = get_decoded(wave, row, month_part_var)
                timing = infer_timing(interview_date, month_value, month_part)
                loop_payloads.append({
                    "loop_index": loop,
                    "month_reported": month_value,
                    "month_part_reported": month_part,
                    "seasonal_pattern": get_decoded(wave, row, seasonal_var),
                    "duration_category": get_decoded(wave, row, duration_var),
                    "duration_text": get_raw(row, duration_txt_var),
                    "move_scope": get_decoded(wave, row, scope_var),
                    "moves_identical": get_decoded(wave, row, identical_var),
                    "return_route": get_decoded(wave, row, return_var),
                    "month_variable": month_var,
                    "month_part_variable": month_part_var,
                    "seasonal_pattern_variable": seasonal_var,
                    "duration_variable": duration_var,
                    "duration_text_variable": duration_txt_var,
                    "move_scope_variable": scope_var,
                    "moves_identical_variable": identical_var,
                    "return_route_variable": return_var,
                    **{f"push_{name}": value for name, value in push_values.items()},
                    **{f"push_{name}_variables": "|".join(push_vars[name]) or None for name in CLIMATE_PUSH_ITEMS.values()},
                    **{f"reason_{name}": value for name, value in reason_values.items()},
                    **{f"reason_{name}_variables": "|".join(reason_vars[name]) or None for name in DEST_REASON_ITEMS.values()},
                    **endpoint,
                    **timing,
                })

            captured = len(loop_payloads)
            compressed = bool(
                loop_payloads
                and frequency > 1
                and str(loop_payloads[0].get("moves_identical") or "").casefold().startswith("yes")
            )
            represented_total = frequency if compressed else captured
            unexpected_missing = captured < min(frequency, 3) and not compressed
            for payload in loop_payloads:
                loop = payload["loop_index"]
                represented = frequency if compressed and loop == 1 else 1
                exact_overlap = stream == "main_migrant" and frequency == 1 and loop == 1
                possible_overlap = stream == "main_migrant" and frequency <= 3 and frequency > 1 and loop == frequency
                domestic = payload["domestic_abroad"] == "In Bangladesh"
                resolved = payload["destination_resolution_status"] == "resolved"
                timing_valid = bool(payload["timing_inference_valid"])
                sensitivity = domestic and resolved and timing_valid and not exact_overlap and not possible_overlap
                whole_partial = payload["move_scope"] in {
                    "Took whole family along", "Took parts of family along [specify whom]:"
                }
                record_kind = (
                    "compressed_identical_repeated_pattern" if compressed and loop == 1
                    else "single_recalled_move" if frequency == 1
                    else "observed_move_within_multi_move_history"
                )
                climate_push = any(payload.get(f"push_{name}") is True for name in CLIMATE_PUSH_ITEMS.values())
                destination_climate_safety = any(
                    payload.get(f"reason_{name}") is True for name in ["safer_flood", "safer_erosion"]
                )
                records.append({
                    "recalled_record_id": f"R-{wave}-{row_index + 2}-{stream}-L{loop}",
                    "respondent_id": respondent_id,
                    "household_id_derived": household,
                    "baseline_location_lxx": lxx,
                    "origin_district_codebook": origin,
                    "wave": wave,
                    "wave_number": base.WAVE_NUMBER[wave],
                    "history_stream": stream,
                    "history_label_prefix": prefix,
                    "source_file": f"bemp_{wave}.csv",
                    "source_row_csv_1_based": row_index + 2,
                    "source_interview_date": interview_date,
                    "respondent_id_variable": base.ID_VAR[wave],
                    "frequency_variable": freq_var,
                    "frequency_text_variable": freq_txt_var,
                    "reported_move_frequency": frequency,
                    "captured_loop_count": captured,
                    "represented_move_count": represented,
                    "represented_move_count_stream_total": represented_total,
                    "unrepresented_move_count_stream": max(frequency - represented_total, 0),
                    "three_loop_instrument_cap_flag": frequency > 3,
                    "unexpected_missing_loop_flag": unexpected_missing,
                    "record_kind": record_kind,
                    "current_event_overlap_exact": exact_overlap,
                    "possible_current_destination_overlap": possible_overlap,
                    "recommended_for_primary_prospective_ledger": False,
                    "recalled_sensitivity_eligible": sensitivity,
                    "recalled_household_relocation_sensitivity_eligible": sensitivity and whole_partial,
                    "climate_push_reason_any": climate_push,
                    "destination_climate_safety_reason_any": destination_climate_safety,
                    **payload,
                })
            stream_summaries.append({
                "wave": wave,
                "history_stream": stream,
                "history_label_prefix": prefix,
                "source_rows_with_positive_frequency": 1,
                "reported_moves_total": frequency,
                "captured_records": captured,
                "represented_moves_total": represented_total,
                "unrepresented_moves_total": max(frequency - represented_total, 0),
                "unexpected_missing_loop_source_row": unexpected_missing,
                "compressed_identical_source_row": compressed,
            })

    recalled = pd.DataFrame(records)
    if not recalled.empty:
        recalled = recalled.sort_values(
            ["wave_number", "history_stream", "respondent_id", "source_row_csv_1_based", "loop_index"]
        ).reset_index(drop=True)
    stream_rows = pd.DataFrame(stream_summaries)
    summary = stream_rows.groupby(["wave", "history_stream", "history_label_prefix"], as_index=False).agg(
        source_rows_with_positive_frequency=("source_rows_with_positive_frequency", "sum"),
        reported_moves_total=("reported_moves_total", "sum"),
        captured_records=("captured_records", "sum"),
        represented_moves_total=("represented_moves_total", "sum"),
        unrepresented_moves_total=("unrepresented_moves_total", "sum"),
        source_rows_with_unexpected_missing_loops=("unexpected_missing_loop_source_row", "sum"),
        compressed_identical_source_rows=("compressed_identical_source_row", "sum"),
    )
    if not recalled.empty:
        extra = recalled.groupby(["wave", "history_stream"], as_index=False).agg(
            district_resolved_records=("destination_resolution_status", lambda s: int((s == "resolved").sum())),
            exact_current_overlap_records=("current_event_overlap_exact", "sum"),
            possible_current_overlap_records=("possible_current_destination_overlap", "sum"),
            sensitivity_eligible_records=("recalled_sensitivity_eligible", "sum"),
            household_relocation_sensitivity_eligible_records=("recalled_household_relocation_sensitivity_eligible", "sum"),
            climate_push_records=("climate_push_reason_any", "sum"),
        )
        summary = summary.merge(extra, on=["wave", "history_stream"], how="left")
    return recalled, summary


def build_duplicate_audit():
    records = []
    for wave, id_var in base.ID_VAR.items():
        data = pd.read_csv(base.data_path(wave), low_memory=False)
        duplicate_mask = data.duplicated(id_var, keep=False)
        for respondent_id, group in data.loc[duplicate_mask].groupby(id_var, sort=True):
            date_var = f"{wave}_date" if f"{wave}_date" in data.columns else None
            dates = pd.to_datetime(group[date_var], errors="coerce") if date_var else pd.Series(pd.NaT, index=group.index)
            keep_index = dates.idxmax() if dates.notna().any() else group.index.max()
            for index, row in group.iterrows():
                keep = index == keep_index
                status_var = next(
                    (v for v in [f"{wave}_reg7", f"{wave}_reg10", f"{wave}_reg12"] if v in data.columns and base.is_valid(row.get(v))),
                    None,
                )
                status = get_decoded(wave, row, status_var)
                if keep:
                    rationale = "Retained latest dated interview in duplicated respondent-wave pair."
                    if int(row.notna().sum()) == int(group.notna().sum(axis=1).max()):
                        rationale += " It is also the most complete row in the pair."
                    elif wave == "w14_M":
                        rationale += " Latest-date rule is applied consistently although this row has fewer populated fields."
                else:
                    rationale = "Superseded by the later dated interview; source row remains visible for sensitivity checks."
                    if status and "replacement" in str(status).casefold():
                        rationale += " This earlier row registers a replacement household head."
                records.append({
                    "wave": wave,
                    "source_file": f"bemp_{wave}.csv",
                    "respondent_id": respondent_id,
                    "household_id_derived": base.person_parts(str(respondent_id))[0],
                    "source_row_csv_1_based": index + 2,
                    "interview_date": get_raw(row, date_var),
                    "nonmissing_cell_count": int(row.notna().sum()),
                    "availability_status_variable": status_var,
                    "availability_status": status,
                    "adjudication_keep": keep,
                    "adjudication_status": "retained_latest_completed_interview" if keep else "superseded_duplicate",
                    "adjudication_confidence": "medium",
                    "adjudication_rationale": rationale,
                })
    return pd.DataFrame(records).sort_values(["wave", "respondent_id", "source_row_csv_1_based"])


def build_household_reconciliation(duplicate_audit: pd.DataFrame):
    baseline = pd.read_csv(base.data_path("w1"), low_memory=False)
    baseline_records = defaultdict(list)
    all_records = defaultdict(list)
    for _, row in baseline.iterrows():
        respondent = base.normalize_scalar(row.get(base.ID_VAR["w1"]))
        if respondent:
            household, lxx, origin = base.person_parts(str(respondent))
            baseline_records[household].append(str(respondent))
    for wave, id_var in base.ID_VAR.items():
        data = pd.read_csv(base.data_path(wave), usecols=[id_var], low_memory=False)
        for respondent in data[id_var].dropna().astype(str):
            household, lxx, origin = base.person_parts(respondent)
            all_records[household].append((wave, respondent))

    duplicate_counts = duplicate_audit.groupby("household_id_derived").size().to_dict()
    records = []
    for household in sorted(all_records):
        baseline_respondents = baseline_records.get(household, [])
        roles = [respondent.rsplit("-", 1)[-1] for respondent in baseline_respondents]
        lxx = re.match(r"^(L\d{2})", household).group(1)
        rows = all_records[household]
        waves = sorted({wave for wave, _ in rows}, key=lambda w: (base.WAVE_NUMBER[w], w))
        respondents = sorted({respondent for _, respondent in rows})
        head_ids = [respondent for respondent in baseline_respondents if respondent.endswith("-H")]
        panel_only = not baseline_respondents
        no_head = bool(baseline_respondents) and not head_ids
        if panel_only:
            status = "panel_only_prefix_not_observed_at_baseline"
            confidence = "medium"
        elif no_head:
            status = "baseline_prefix_without_public_head_interview"
            confidence = "medium"
        else:
            status = "standard_baseline_household_prefix"
            confidence = "high"
        records.append({
            "household_id_derived": household,
            "baseline_location_lxx": lxx,
            "origin_district_codebook": base.ORIGIN_DISTRICT.get(lxx),
            "baseline_respondent_count": len(baseline_respondents),
            "baseline_respondent_ids": "|".join(sorted(baseline_respondents)) or None,
            "baseline_role_suffixes": "|".join(sorted(roles)) or None,
            "baseline_head_count": len(head_ids),
            "baseline_head_respondent_ids": "|".join(head_ids) or None,
            "no_public_baseline_head_flag": no_head,
            "multiple_public_baseline_heads_flag": len(head_ids) > 1,
            "panel_only_prefix_flag": panel_only,
            "panel_unique_respondent_count": len(respondents),
            "panel_respondent_ids": "|".join(respondents),
            "panel_wave_count": len(waves),
            "panel_waves": "|".join(waves),
            "panel_source_row_count": len(rows),
            "duplicate_source_rows_in_audit": int(duplicate_counts.get(household, 0)),
            "household_key_status": status,
            "household_key_confidence": confidence,
            "recommended_cluster_key": True,
            "reconciliation_note": (
                "Exact prefix through HHzz; codebook-defined household grouping. "
                + ("No public w1 -H interview, so household-head attributes require missingness handling."
                   if no_head else
                   "First observed after w1; retain for panel linkage but exclude from analyses requiring baseline covariates."
                   if panel_only else
                   "Public w1 includes exactly one -H respondent.")
            ),
        })
    return pd.DataFrame(records)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    recalled, flow = build_recalled_history()
    duplicate_audit = build_duplicate_audit()
    household = build_household_reconciliation(duplicate_audit)
    recalled.to_csv(OUT / "bemp_recalled_migration_history.csv", index=False)
    flow.to_csv(OUT / "bemp_recalled_history_flow.csv", index=False)
    duplicate_audit.to_csv(OUT / "bemp_respondent_duplicate_audit.csv", index=False)
    household.to_csv(OUT / "bemp_household_key_reconciliation.csv", index=False)
    print({
        "recalled_records": len(recalled),
        "recalled_resolved": int(recalled["destination_resolution_status"].eq("resolved").sum()),
        "recalled_sensitivity_eligible": int(recalled["recalled_sensitivity_eligible"].sum()),
        "exact_overlap": int(recalled["current_event_overlap_exact"].sum()),
        "possible_overlap": int(recalled["possible_current_destination_overlap"].sum()),
        "duplicate_audit_rows": len(duplicate_audit),
        "household_prefixes": len(household),
        "household_medium_confidence": int(household["household_key_confidence"].eq("medium").sum()),
    })


if __name__ == "__main__":
    main()
