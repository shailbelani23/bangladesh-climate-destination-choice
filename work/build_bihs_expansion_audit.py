#!/usr/bin/env python3
"""Construct the official-file BIHS destination audit and frozen event ledgers."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/bihs"
TABLES = ROOT / "outputs/tables"
REPORTS = ROOT / "outputs/reports"
TABLES.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

PATHS = {
    "w1_a": RAW / "wave1_2011_12/001_mod_a_male.dta",
    "w1_b1": RAW / "wave1_2011_12/003_mod_b1_male.dta",
    "w1_t1": RAW / "wave1_2011_12/038_mod_t1_male.dta",
    "w1_v1": RAW / "wave1_2011_12/041_mod_v1_male.dta",
    "w2_a": RAW / "wave2_2015/001_r2_mod_a_male.dta",
    "w2_b1": RAW / "wave2_2015/003_r2_male_mod_b1.dta",
    "w2_b4": RAW / "wave2_2015/007_r2_mod_b4_male.dta",
    "w2_t1": RAW / "wave2_2015/050_r2_mod_t1_male.dta",
    "w2_v1": RAW / "wave2_2015/053_r2_mod_v1_male.dta",
    "w3_a": RAW / "wave3_2018_19/009_bihs_r3_male_mod_a.dta",
    "w3_b1": RAW / "wave3_2018_19/010_bihs_r3_male_mod_b1.dta",
    "w3_t1b": RAW / "wave3_2018_19/067_bihs_r3_male_mod_t1b.dta",
    "w3_t1c": RAW / "wave3_2018_19/068_bihs_r3_male_mod_t1c.dta",
    "w3_v1": RAW / "wave3_2018_19/072_bihs_r3_male_mod_v1.dta",
}

ALIASES = {
    "Barisal": "Barishal", "Bogra": "Bogura", "Chittagong": "Chattogram",
    "Comilla": "Cumilla", "Jessore": "Jashore", "Noagaon": "Naogaon",
    "Nawabganj": "Chapainawabganj", "Chapai Nawabganj": "Chapainawabganj",
    "Gaibanda": "Gaibandha", "Hobiganj": "Habiganj", "Moulovibazar": "Moulvibazar",
    "Maulvibazar": "Moulvibazar", "Jhalakathi": "Jhalokati", "Lakshimpur": "Lakshmipur",
    "Cox’s bazar": "Cox's Bazar", "Coxs bazar": "Cox's Bazar", "Cox???s bazar": "Cox's Bazar",
    "Cox\x92S Bazar": "Cox's Bazar", "Netrokona": "Netrakona",
    "Jhenaidah Zila T": "Jhenaidah", "Kishorgonj": "Kishoreganj", "Mymensing": "Mymensingh",
    "Shatkhira": "Satkhira", "Bormon": "Barguna", "Borguna": "Barguna",
    "Narshingdi": "Narsingdi", "Khagrachori": "Khagrachhari",
    "Bramonbaria": "Brahmanbaria", "Chadpur": "Chandpur", "Laxmipur": "Lakshmipur",
    "Shirajganj": "Sirajganj", "Panchagar": "Panchagarh", "Jholkathi": "Jhalokati",
    "Potuakhali": "Patuakhali",
}


def canon(x):
    if pd.isna(x):
        return np.nan
    s = re.sub(r"\s+", " ", str(x)).strip().title()
    # Restore common capitalization/punctuation before aliasing.
    replacements = {
        "Cox'S Bazar": "Cox's Bazar", "Chapai Nawabganj": "Chapai Nawabganj",
        "Moulovibazar": "Moulovibazar", "Maulvibazar": "Maulvibazar",
    }
    s = replacements.get(s, s)
    return ALIASES.get(s, s)


def hhid(x):
    if pd.isna(x):
        return ""
    return f"{float(x):.6f}".rstrip("0").rstrip(".")


def value_map(path: Path, var: str):
    r = pd.io.stata.StataReader(path)
    labels = r.variable_labels()
    labelset = None
    # pandas does not expose variable-to-labelset directly, but in these files the
    # label-set name equals the variable name for every field we use.
    maps = r.value_labels()
    if var in maps:
        return maps[var]
    # Common shared yes/no labels do not need mapping here.
    return {}


def series_profile(tag, path, variables):
    reader = pd.io.stata.StataReader(path)
    labels = reader.variable_labels()
    maps = reader.value_labels()
    df = pd.read_stata(path, convert_categoricals=False)
    rows = []
    for v in variables:
        if v not in df:
            continue
        s = df[v]
        examples = " | ".join(str(x) for x in s.dropna().drop_duplicates().head(8))
        rows.append({
            "file_tag": tag, "file": str(path.relative_to(ROOT)), "variable": v,
            "question_or_label": labels.get(v, ""), "dtype": str(s.dtype),
            "missing_pct": round(100 * s.isna().mean(), 3),
            "unique_nonmissing": int(s.nunique(dropna=True)), "example_values": examples,
            "value_label_excerpt": json.dumps({str(k): val for k, val in list(maps.get(v, {}).items())[:12]}, ensure_ascii=False),
        })
    return rows


def main():
    frames = {tag: pd.read_stata(path, convert_categoricals=False) for tag, path in PATHS.items()}

    # Frozen canonical universe is inherited unchanged from the BEMP study.
    universe = pd.read_csv(TABLES / "bgd_district_universe.csv")
    district_set = set(universe.district)

    # Destination codes are identical across V1 waves and B4. Decode from official labels.
    dest_raw = value_map(PATHS["w2_v1"], "v1_10")
    dest_map = {int(k): canon(v) for k, v in dest_raw.items() if 1 <= int(k) <= 64}
    assert len(dest_map) == 64 and set(dest_map.values()) == district_set

    # R3 origin districts are anonymized sequential codes. Infer the complete public
    # code-to-name crosswalk from exact household matches to R2 Module A; all 64 codes
    # have matches and every code maps one-to-one.
    a2 = frames["w2_a"].copy()
    a3 = frames["w3_a"].copy()
    m23 = a3[["a01", "district"]].merge(a2[["a01", "District_Name"]], on="a01", how="inner")
    chk = m23.groupby("district")["District_Name"].nunique()
    assert len(chk) == 64 and chk.eq(1).all()
    r3_origin_map = m23.groupby("district")["District_Name"].first().map(canon).to_dict()
    assert set(r3_origin_map.values()) == district_set

    origins = {
        "w1": frames["w1_a"].assign(origin_district=frames["w1_a"].District_Name.map(canon))[["a01", "origin_district"]],
        "w2": frames["w2_a"].assign(origin_district=frames["w2_a"].District_Name.map(canon))[["a01", "origin_district"]],
        "w3": frames["w3_a"].assign(origin_district=frames["w3_a"].district.map(r3_origin_map))[["a01", "origin_district"]],
    }
    for wave, o in origins.items():
        assert o.a01.is_unique and o.origin_district.notna().all(), wave

    # Current internal migrants. The questionnaires define current migrant as away
    # >=6 months, domestic moves as outside the origin upazila, and record current zila.
    ledgers = []
    reason_maps = {w: value_map(PATHS[f"{w}_v1"], "v1_12") for w in ["w1", "w2", "w3"]}
    help_maps = {w: value_map(PATHS[f"{w}_v1"], "v1_15") if w != "w1" else {} for w in ["w1", "w2", "w3"]}
    for wave, survey_year, pid_col, mid_col in [
        ("w1", 2011.5, "pid", None), ("w2", 2015, "pid", "mid"), ("w3", 2018.5, "pid_v1", "mid_v1")
    ]:
        d = frames[f"{wave}_v1"].copy()
        valid = (d.v1_01 == 1) & (d.v1_09 == 1) & d.v1_10.between(1, 64)
        d = d.loc[valid].merge(origins[wave], on="a01", how="left", validate="many_to_one")
        assert d.origin_district.notna().all()
        z = pd.DataFrame({
            "event_id": [f"BIHS-V1-{wave.upper()}-{i+1:04d}" for i in range(len(d))],
            "wave": wave, "survey_year": survey_year,
            "household_id": d.a01.map(hhid), "person_id_record": d[pid_col],
            "panel_member_id": d[mid_col] if mid_col else np.nan,
            "origin_district": d.origin_district, "destination_district": d.v1_10.map(dest_map),
            "migration_elapsed_years_recorded": d.v1_03, "migration_month_recorded": d.v1_04,
            "age": d.v1_05, "sex_code": d.v1_06, "occupation_code": d.v1_08,
            "reason_code": d.v1_12, "reason_label": d.v1_12.map(reason_maps[wave]),
            "destination_help_code": d.v1_15 if "v1_15" in d else np.nan,
            "destination_help_label": d.v1_15.map(help_maps[wave]) if "v1_15" in d else np.nan,
            "prior_midline_migrant_flag": d["del"].eq(1) if "del" in d else False,
        })
        z["cross_district"] = z.origin_district != z.destination_district
        z["analysis_status"] = "supplementary_baseline_current_migrant_stock" if wave == "w1" else "include_interval_primary"
        ledgers.append(z)
    v1 = pd.concat(ledgers, ignore_index=True)

    # Conservative de-duplication for interval-specific R2/R3 analysis.
    w2_keys = set(
        zip(v1.loc[v1.wave.eq("w2"), "household_id"], v1.loc[v1.wave.eq("w2"), "panel_member_id"])
    )
    prior = v1.wave.eq("w3") & v1.prior_midline_migrant_flag
    v1.loc[prior, "analysis_status"] = "exclude_r3_explicit_prior_midline_migrant"
    overlap = v1.wave.eq("w3") & v1.apply(lambda r: (r.household_id, r.panel_member_id) in w2_keys, axis=1)
    v1.loc[overlap & ~prior, "analysis_status"] = "exclude_r3_same_member_already_current_in_r2"
    r3 = v1[v1.wave.eq("w3") & v1.analysis_status.eq("include_interval_primary")]
    dup_keys = r3[["household_id", "panel_member_id"]].duplicated(keep=False)
    dup_idx = r3.index[dup_keys]
    v1.loc[dup_idx, "analysis_status"] = "exclude_r3_ambiguous_duplicate_member_id"
    v1["primary_interval_sample"] = v1.analysis_status.eq("include_interval_primary")
    assert v1.primary_interval_sample.sum() == 1857
    assert set(v1.origin_district) <= district_set and set(v1.destination_district) <= district_set
    v1.to_csv(TABLES / "bihs_internal_migration_events.csv", index=False)

    # R2 household-head relocation history: previous district -> current Module-A district.
    b4 = frames["w2_b4"].merge(origins["w2"], on="a01", how="left", validate="one_to_one")
    b4_origin_map = {int(k): canon(v) for k, v in value_map(PATHS["w2_b4"], "b4_02").items() if 1 <= int(k) <= 64}
    b4_reason_map = value_map(PATHS["w2_b4"], "b4_03")
    b4 = b4[b4.b4_02.between(1, 64)].copy()
    rel = pd.DataFrame({
        "event_id": [f"BIHS-B4-W2-{i+1:04d}" for i in range(len(b4))],
        "wave": "w2", "household_id": b4.a01.map(hhid),
        "origin_district": b4.b4_02.map(b4_origin_map),
        "destination_district": b4.origin_district,
        "move_year_recorded": b4.b4_01,
        "reason_code": b4.b4_03, "reason_label": b4.b4_03.map(b4_reason_map),
        "home_changes_last_5y": b4.b4_04,
    })
    rel["move_year_valid"] = rel.move_year_recorded.between(1900, 2015)
    rel["cross_district"] = rel.origin_district != rel.destination_district
    rel["erosion_motivated"] = rel.reason_code.eq(1)
    assert len(rel) == 526 and rel.erosion_motivated.sum() == 123
    assert set(rel.origin_district) <= district_set and set(rel.destination_district) <= district_set
    rel.to_csv(TABLES / "bihs_household_relocation_events.csv", index=False)

    # Crosswalk provenance.
    cross_rows = []
    for code, raw in sorted(dest_raw.items()):
        if 1 <= int(code) <= 64:
            cross_rows.append({"source": "V1/B4 destination code", "wave": "w1-w3", "raw_code": int(code),
                               "raw_name": raw, "canonical_district": dest_map[int(code)],
                               "method": "official value label plus explicit spelling harmonization"})
    for code, name in sorted(r3_origin_map.items()):
        cross_rows.append({"source": "R3 Module A origin code", "wave": "w3", "raw_code": int(code),
                           "raw_name": name, "canonical_district": name,
                           "method": "one-to-one inference from exact R2-R3 a01 matches; all 64 codes identified"})
    pd.DataFrame(cross_rows).to_csv(TABLES / "bihs_district_crosswalk.csv", index=False)

    # File inventory and merge coverage.
    inv = []
    type_by_tag = {"a": "household geography", "b1": "person roster", "b4": "household relocation history",
                   "t1": "household shocks", "t1b": "household shocks", "t1c": "severe-disaster summary", "v1": "current migrants"}
    for tag, path in PATHS.items():
        df = frames[tag]
        suffix = tag.split("_", 1)[1]
        hhcol = "a01" if "a01" in df else None
        inv.append({
            "file_tag": tag, "file": str(path.relative_to(ROOT)), "rows": len(df), "columns": len(df.columns),
            "wave": tag[:2], "module_type": type_by_tag.get(suffix, suffix),
            "household_key": hhcol or "", "unique_households": int(df[hhcol].nunique()) if hhcol else np.nan,
            "person_keys": "a01+mid" if "mid" in df else ("a01+mid_v1" if "mid_v1" in df else ""),
        })
    pd.DataFrame(inv).to_csv(TABLES / "bihs_file_inventory.csv", index=False)

    variables = {
        "w1_a": ["a01", "dcode", "District_Name", "Upazila", "Upazila_Name", "Union", "Union_Name", "vcode_n"],
        "w2_a": ["a01", "hh_type", "dcode", "District_Name", "uzcode", "Upazila_Name", "uncode", "Union_Name", "vcode", "village_name"],
        "w3_a": ["a01", "hh_type", "x1", "district", "upazila", "union", "village"],
        "w1_v1": ["a01", "v1_01", "pid", "v1_03", "v1_04", "v1_09", "v1_10", "v1_12", "v1_14"],
        "w2_v1": ["a01", "v1_01", "pid", "mid", "v1_03", "v1_04", "v1_09", "v1_10", "v1_12", "v1_15", "v1_14"],
        "w3_v1": ["a01", "v1_01", "pid_v1", "mid_v1", "v1_03", "v1_04", "v1_09", "v1_10", "v1_12", "v1_15", "v1_14", "del"],
        "w2_b4": ["a01", "b4_01", "b4_02", "b4_03", "b4_04", "b4_05", "b4_06", "b4_07", "b4_08"],
        "w1_t1": ["a01", "t1_02", "t1_03", "t1_04", "t1_05", "t1_08a", "t1_08b", "t1_08c"],
        "w2_t1": ["a01", "t1_02", "t1_02a", "t1_03", "t1_04", "t1_05", "t1_08a", "t1_08b", "t1_08c"],
        "w3_t1b": ["a01", "t1b_01", "t1b_02", "t1b_03", "t1b_04", "t1b_05", "t1b_06a", "t1b_06b", "t1b_06c"],
        "w3_t1c": ["a01", "t1c_01", "t1c_02"],
    }
    audit_rows = []
    for tag, vv in variables.items():
        audit_rows += series_profile(tag, PATHS[tag], vv)
    pd.DataFrame(audit_rows).to_csv(TABLES / "bihs_migration_variable_audit.csv", index=False)

    # Transparent sample flow.
    flow = []
    for wave in ["w1", "w2", "w3"]:
        raw = frames[f"{wave}_v1"]
        flow += [
            {"ledger": "V1", "wave": wave, "stage": "all file rows", "n": len(raw)},
            {"ledger": "V1", "wave": wave, "stage": "reported current migrants", "n": int((raw.v1_01 == 1).sum())},
            {"ledger": "V1", "wave": wave, "stage": "domestic migrants", "n": int(((raw.v1_01 == 1) & (raw.v1_09 == 1)).sum())},
            {"ledger": "V1", "wave": wave, "stage": "valid public destination district 1-64", "n": int(((raw.v1_01 == 1) & (raw.v1_09 == 1) & raw.v1_10.between(1, 64)).sum())},
            {"ledger": "V1", "wave": wave, "stage": "frozen primary interval sample", "n": int((v1.wave.eq(wave) & v1.primary_interval_sample).sum())},
        ]
    flow += [
        {"ledger": "B4", "wave": "w2", "stage": "all household rows", "n": len(frames["w2_b4"])},
        {"ledger": "B4", "wave": "w2", "stage": "internal prior district 1-64", "n": len(rel)},
        {"ledger": "B4", "wave": "w2", "stage": "interdistrict relocation", "n": int(rel.cross_district.sum())},
        {"ledger": "B4", "wave": "w2", "stage": "river-erosion motivated", "n": int(rel.erosion_motivated.sum())},
        {"ledger": "B4", "wave": "w2", "stage": "river-erosion, interdistrict, valid year", "n": int((rel.erosion_motivated & rel.cross_district & rel.move_year_valid).sum())},
    ]
    pd.DataFrame(flow).to_csv(TABLES / "bihs_sample_flow.csv", index=False)

    # Validation assertions as a durable artifact.
    validation = [
        ("destination_code_map_complete", len(dest_map) == 64),
        ("r3_origin_code_map_complete", len(r3_origin_map) == 64),
        ("v1_origin_join_complete", v1.origin_district.notna().all()),
        ("v1_destination_join_complete", v1.destination_district.notna().all()),
        ("v1_primary_interval_expected_n", int(v1.primary_interval_sample.sum()) == 1857),
        ("b4_internal_expected_n", len(rel) == 526),
        ("b4_erosion_expected_n", int(rel.erosion_motivated.sum()) == 123),
        ("all_names_in_frozen_64", set(v1.origin_district) | set(v1.destination_district) | set(rel.origin_district) | set(rel.destination_district) <= district_set),
    ]
    val = pd.DataFrame(validation, columns=["check", "passed"])
    val.to_csv(TABLES / "bihs_expansion_validation.csv", index=False)
    if not val.passed.all():
        raise RuntimeError(val[~val.passed].to_string(index=False))

    summary = {
        "v1_public_internal_valid_all_waves": len(v1),
        "v1_primary_interval_n": int(v1.primary_interval_sample.sum()),
        "v1_primary_households": int(v1.loc[v1.primary_interval_sample, "household_id"].nunique()),
        "v1_primary_origins": int(v1.loc[v1.primary_interval_sample, "origin_district"].nunique()),
        "v1_primary_destinations": int(v1.loc[v1.primary_interval_sample, "destination_district"].nunique()),
        "v1_primary_cross_district": int((v1.primary_interval_sample & v1.cross_district).sum()),
        "b4_internal": len(rel), "b4_interdistrict": int(rel.cross_district.sum()),
        "b4_erosion": int(rel.erosion_motivated.sum()),
        "b4_erosion_interdistrict": int((rel.erosion_motivated & rel.cross_district).sum()),
        "b4_erosion_interdistrict_valid_year": int((rel.erosion_motivated & rel.cross_district & rel.move_year_valid).sum()),
    }
    (ROOT / "work/bihs_expansion_summary.json").write_text(json.dumps(summary, indent=2))

    # Freeze the exact source/event/GIS contract before any BIHS outcome is fitted.
    freeze_paths = list(PATHS.values()) + [
        TABLES / "bgd_district_universe.csv",
        TABLES / "bgd_origin_destination_matrix.csv",
        TABLES / "bemp_stage4_district_gis_features.csv",
        TABLES / "bihs_internal_migration_events.csv",
        TABLES / "bihs_household_relocation_events.csv",
        TABLES / "bihs_district_crosswalk.csv",
        REPORTS / "bihs_destination_feasibility_audit.md",
        REPORTS / "bihs_external_replication_design_freeze.md",
        Path(__file__),
    ]
    freeze = []
    for path in freeze_paths:
        data = path.read_bytes()
        freeze.append({
            "artifact": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "role": "raw_official_input" if path in PATHS.values() else "frozen_design_or_input",
        })
    pd.DataFrame(freeze).to_csv(TABLES / "bihs_external_replication_freeze_manifest.csv", index=False)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
