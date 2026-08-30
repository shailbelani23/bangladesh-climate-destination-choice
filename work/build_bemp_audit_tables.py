from __future__ import annotations

import csv
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bemp"
DATA_DIR = RAW / "quantitative"
CODEBOOK_DIR = RAW / "codebooks"
VARIABLE_LIST = RAW / "metadata" / "bemp_variable_list_full.xlsx"
OUTPUT_TABLES = ROOT / "outputs" / "tables"
OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)

WAVES = [
    "w1", "w1_V", "w2", "w3", "w4", "w5", "w6_N", "w6_M", "w7", "w8",
    "w9", "w10", "w11", "w12_N", "w12_M", "w12_V", "w13", "w14_N", "w14_M", "w14_V",
]
WAVE_ORDER = {wave: i for i, wave in enumerate(WAVES)}

RESPONDENT_IDS = {
    "w1": "w1_reg1", "w2": "w2_reg1", "w3": "w3_reg1", "w4": "w4_reg1", "w5": "w5_reg1",
    "w6_N": "w6_N_reg3", "w6_M": "w6_M_reg3", "w7": "w7_reg2", "w8": "w8_reg2",
    "w9": "w9_reg2", "w10": "w10_reg2", "w11": "w11_reg2", "w12_N": "w12_N_reg3",
    "w12_M": "w12_M_reg3", "w13": "w13_reg2", "w14_N": "w14_N_reg3", "w14_M": "w14_M_reg3",
}
LOCATION_IDS = {"w1_V": "w1_V_reg1", "w12_V": "w12_V_reg2", "w14_V": "w14_V_reg2"}

MISSING_TOKENS = {"", "NA", "N/A", "NAN", "NONE", "-55", "-66", "-6", "-7", "-8", "-9"}


def compact(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def wave_from_name(path: Path) -> str:
    match = re.search(r"bemp_(w\d+(?:_[MNV])?)", path.stem)
    return match.group(1) if match else ""


def wave_attributes(wave: str) -> tuple[str, str]:
    if wave in {"w1", "w6_N", "w6_M", "w12_N", "w12_M", "w14_N", "w14_M", "w1_V", "w12_V", "w14_V"}:
        mode = "in-person"
    else:
        mode = "phone"
    if wave.endswith("_M"):
        sample = "migrant respondent"
    elif wave.endswith("_N"):
        sample = "non-migrant respondent"
    elif wave.endswith("_V"):
        sample = "village profile"
    elif wave == "w1":
        sample = "baseline, all respondent types"
    else:
        sample = "main longitudinal respondent"
    return mode, sample


def csv_dimensions(path: Path) -> tuple[int, int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = sum(1 for _ in reader)
    return rows, len(header)


def parse_wave_cell(cell: object) -> str | None:
    match = re.match(r"\s*([A-Za-z0-9_]+)\s+\(n=", str(cell or ""))
    return match.group(1) if match else None


variable_list = pd.read_excel(VARIABLE_LIST, sheet_name="Variable list", dtype=str).fillna("")

SPATIAL_TITLES = {
    "Respondent Code", "Location Number", "District",
    "Respondent Current Location", "Respondent Current Location Domestic Abroad",
    "Respondent Current Location Country", "Respondent Current Location New or Old",
    "Respondent Current Location Rural Urban", "Respondent Current Location Same or Different Village",
    "Respondent Current Location City", "Respondent Current Location Village",
    "Household Origin Domestic Abroad", "Household Origin Country", "Household Origin Rural Urban",
    "Household Origin City", "Household Origin Village", "Household Origin Village Existence",
    "Distance from Previous Location", "Distance from Previous Riverbank", "Distance from Current Riverbank",
    "House Shift Distance", "Total House Shift Distance", "Migration Respondent House Shift Distance",
    "Migration Respondent House Shift Distance (Loop 1)", "Migration Respondent House Shift Distance (Loop 2)",
    "Migration Respondent House Shift Distance (Loop 3)",
    "Secondary Migration Respondent House Shift Distance (Loop 1)",
    "Secondary Migration Respondent House Shift Distance (Loop 2)",
    "Secondary Migration Respondent House Shift Distance (Loop 3)",
    "Distance to Road", "Grocery Shop Distance", "Madrasha Distance", "Medical Facility Distance",
    "Pharmacy Distance", "Primary Government School Distance", "Secondary Government School Distance",
    "Plot Distance from Jamuna", "Household Origin Village River Distance",
    "Riverbank (Home Village) Current Distance", "Riverbank (Home Village) Distance 2019",
    "Riverbank (Home Village) Distance 2020", "Village Migration Individual Distance",
    "Village Migration Permanent Distance", "Village Access", "Residence Type",
    "Current Location Residence Duration", "Respondent Current Location Stay Duration",
}

CORE_HAZARD_TITLES = {
    "Flood (Home Village) Occurrence", "Erosion (Home Village) Occurrence",
    "Flood (Home Village) Occurrence (Migrants)", "Erosion (Home Village) Occurrence (Migrants)",
    "Flood (Migration Location) Occurrence", "Erosion (Migration Location) Occurrence",
    "Current Village Flooding (Home Village)", "Current House Flooding (Home Village)",
    "Current Erosion (Home Village)", "Current Village Flooding (Migration Location)",
    "Current House Flooding (Migration Location)", "Current Erosion (Migration Location)",
    "Flood (Home Village) Impact Household", "Erosion (Home Village) Impact Household",
    "Flood (Migration Location) Impact Household", "Erosion (Migration Location) Impact Household",
    "Flood (Home Village) Land Loss Amount", "Erosion (Home Village) Land Loss Amount",
    "Flood (Migration Location) Land Loss Amount", "Erosion (Migration Location) Land Loss Amount",
    "Flood (Home Village) House Flooded", "Flood (Migration Location) House Flooded",
    "Flood (Home Village) Severity", "Erosion (Home Village) Severity",
    "Flood (Home Village) Duration", "Erosion (Home Village) Duration",
    "Flood (Migration Location) Duration", "Erosion (Migration Location) Duration",
}

DESTINATION_NETWORK_TITLES = {
    "Relatives Location Distribution (Migration Location)",
    "Family Support Location (Migration Location) (Individual Migration)",
    "Family Support Location (Migration Location) (Whole Household Migration)",
    "Migrant Contact Last Year (Migration Location)",
    "External Support Receipt (Migration Location) (Individual Migration)",
    "External Support Receipt (Migration Location) (Whole Household Migration)",
    "External Support Type Family (Migration Location) (Individual Migration)",
    "External Support Type Family (Migration Location) (Whole Household Migration)",
    "Migration Respondent Current Destination Choice Relatives",
    "Migration Respondent Current Destination Choice Reasons",
    "Migration Respondent Current Destination Move Preparation Types",
}


def migration_title(title: str) -> bool:
    direct = {
        "Respondent Current Location", "Respondent Current Location Domestic Abroad",
        "Respondent Current Location Country", "Respondent Current Location New or Old",
        "Respondent Current Location Rural Urban", "Respondent Current Location Same or Different Village",
        "Respondent Current Location City", "Respondent Current Location Village",
        "Respondent Current Migration Individual or Household", "Previous Migration Status",
        "Previous Migration Type", "Household Member Migration", "Household Member Migration (Follow-Up)",
        "Household Migration Frequency", "Household Migration Reasons", "Migration Participants",
        "House Shift Distance", "Total House Shift Distance", "Current Location Residence Duration",
        "Respondent Current Location Stay Duration",
    }
    if title in direct or title in CORE_HAZARD_TITLES or title in DESTINATION_NETWORK_TITLES:
        return True
    patterns = [
        r"^Migration Respondent (Frequency|Domestic Abroad|Rural Urban|Same District|Same or Different Village|City|Village|Country|Individual or Household|Reasons|Return Plans|Return Reasons|Seasonal Pattern|Still Away|Duration|Year|Month|House Shift|Current Destination|Destination Choice)",
        r"^Migration Family Member (Frequency|Domestic Abroad|Rural Urban|Same District|Same or Different Village|City|Village|Country|Individual or Household|Reasons|Return Plans|Return Reasons|Seasonal Pattern|Still Away|Duration|Year|Month|Destination Choice)",
        r"^Secondary Migration Respondent (Domestic Abroad|Rural Urban|Same District|Same or Different Village|City|Village|Country|Individual or Household|Reasons|Return|Seasonal|House Shift|Year|Month)",
        r"^Village Migration (Permanent|Temporary|Returned|Individual|Arrivals|Shifts)",
    ]
    return any(re.search(pattern, title) for pattern in patterns)


spatial_map: dict[str, dict] = {}
migration_map: dict[str, dict] = {}
for _, row in variable_list.iterrows():
    title = row["variable_title"]
    for wave in WAVES:
        varname = parse_wave_cell(row[wave])
        if not varname:
            continue
        base = {"wave": wave, "variable_name": varname, "variable_title": title, "standardized_label": row["variable_label"]}
        if title in SPATIAL_TITLES:
            spatial_map[varname] = base
        if migration_title(title):
            migration_map[varname] = base

selected_names = set(spatial_map) | set(migration_map)

codebook_rows: dict[str, dict] = {}
for path in sorted(CODEBOOK_DIR.glob("*_codebook.csv")):
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    subset = frame[frame["Variable name"].isin(selected_names)]
    for _, row in subset.iterrows():
        record = row.to_dict()
        record["codebook_file"] = path.name
        codebook_rows[record["Variable name"]] = record


def value_label_map(record: dict) -> dict[str, str]:
    result = {}
    for key, value in record.items():
        if re.fullmatch(r"-?\d+", str(key)) and compact(value):
            result[str(key)] = compact(value)
    return result


def detect_dtype(values: pd.Series) -> str:
    if values.empty:
        return "undetermined (no valid values)"
    strings = values.astype(str).str.strip()
    if strings.str.fullmatch(r"[+-]?\d+").all():
        return "integer-coded"
    if strings.str.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?").all():
        return "continuous numeric"
    return "string"


def spatial_interpretation(title: str, varname: str, item_text: str, comment: str) -> tuple[str, str, str, str]:
    lower = f"{title} {varname} {item_text}".lower()
    if title == "Respondent Code":
        return ("baseline origin sampling-location / household code", "anonymized Lxx sampling location; district derivable", "origin", "pseudonymized composite; fixed after moves")
    if title == "Location Number":
        return ("baseline origin sampling-location code", "anonymized Lxx location; district derivable", "origin", "pseudonymized location code; no village name")
    if title == "District":
        return ("district name", "district", "origin village profile", "public district; lower levels suppressed")
    if "current location city" in lower:
        return ("destination city category/name", "city", "destination", "categorical/open-text city; no coordinates")
    if "current location village" in lower and ("x5" in varname or "district" in item_text.lower()):
        return ("rural destination district", "district", "destination", "village/upazila/union removed; district retained")
    if "current location village" in lower and ("x6" in varname or "division" in item_text.lower()):
        return ("rural destination division", "division", "destination", "village/upazila/union removed; division retained")
    if "current location village" in lower:
        return ("rural destination response flag", "relational/nonresponse flag", "destination", "village identity removed")
    if "same or different village" in lower:
        return ("same-versus-another-village relation", "relational", "destination", "categorized; no destination identifier")
    if "rural urban" in lower:
        return ("rural/urban settlement type", "settlement type", "destination", "categorized")
    if "domestic abroad" in lower or "country" in lower:
        return ("domestic/international destination", "country/internal status", "destination", "categorized")
    if title == "Distance from Previous Location":
        return ("coordinate-derived inter-wave distance", "meters; no direction or endpoint", "origin-to-current / inter-wave", "derived from withheld house coordinates")
    if "riverbank" in lower or "jamuna" in lower:
        return ("hazard proximity", "meters or reported distance category", "origin/current residence context", "derived/reported distance; no house coordinates")
    if "distance" in lower:
        return ("reported distance/accessibility", "distance/category per question", "origin/destination context per file", "distance only; endpoints not identified")
    if title in {"Residence Type", "Current Location Residence Duration", "Respondent Current Location Stay Duration"}:
        return ("destination residence characteristic", "house/residence category or duration", "destination", "categorized")
    if title == "Respondent Current Location New or Old":
        return ("same-versus-new inter-wave destination", "relational", "destination", "categorized")
    if title == "Respondent Current Location":
        return ("home-versus-away location status", "relational", "current location", "categorized")
    if "origin" in lower:
        return ("historical origin characteristic", "country/city/district/village relation", "origin", "lower-level identifiers suppressed where applicable")
    if title == "Village Access":
        return ("village transport access", "village profile", "origin village context", "categorized")
    return ("spatial/contextual variable", "see question text", "contextual", "see codebook comment")


def migration_family(title: str) -> str:
    if title in CORE_HAZARD_TITLES:
        return "environmental shock/exposure"
    if title in DESTINATION_NETWORK_TITLES or "Destination Choice" in title or "Current Destination" in title:
        return "destination choice/social network"
    if "Reason" in title:
        return "reason for moving/return"
    if any(term in title for term in ["Return", "Seasonal", "Duration", "Year", "Month", "Previous Migration Type", "New or Old"]):
        return "timing/temporary/permanent/return"
    if any(term in title for term in ["Individual or Household", "Participants", "Household Member"]):
        return "individual-versus-household movement"
    if any(term in title for term in ["City", "Village", "Country", "Rural Urban", "Domestic Abroad", "Same District", "Current Location"]):
        return "move/destination outcome"
    if "Distance" in title:
        return "migration distance"
    if "Village Migration" in title:
        return "village-level mobility context"
    return "migration history/outcome"


def profile_selected(mapping: dict[str, dict], spatial: bool) -> pd.DataFrame:
    by_wave: dict[str, list[str]] = defaultdict(list)
    for varname, meta in mapping.items():
        by_wave[meta["wave"]].append(varname)
    rows = []
    for wave, names in by_wave.items():
        path = DATA_DIR / f"bemp_{wave}.csv"
        header = pd.read_csv(path, nrows=0).columns.tolist()
        usable = [name for name in names if name in header]
        if not usable:
            continue
        data = pd.read_csv(path, usecols=usable, dtype=str, keep_default_na=False, low_memory=False)
        for varname in usable:
            meta = mapping[varname]
            cb = codebook_rows.get(varname, {})
            series = data[varname].astype(str).str.strip()
            nonempty_mask = series.ne("")
            valid_mask = ~series.str.upper().isin(MISSING_TOKENS)
            valid = series[valid_mask]
            value_map = value_label_map(cb)
            counts = valid.value_counts(dropna=False)
            example_raw = counts.head(8).index.astype(str).tolist()
            example_decoded = [value_map.get(value, value) for value in example_raw]
            base = {
                "variable_name": varname,
                "standardized_title": meta["variable_title"],
                "standardized_label": meta["standardized_label"],
                "wave": wave,
                "file": path.name,
                "codebook_file": cb.get("codebook_file", ""),
                "block": compact(cb.get("Block", "")),
                "question_label": compact(cb.get("Question", "")),
                "question_text": compact(cb.get("Question text", "")),
                "item_text": compact(cb.get("Item text", "")),
                "question_type": compact(cb.get("Question type", "")),
                "dtype_observed": detect_dtype(valid),
                "rows": len(series),
                "nonempty_n": int(nonempty_mask.sum()),
                "valid_n": int(valid_mask.sum()),
                "missing_pct": round(100 * (1 - valid_mask.mean()), 2),
                "unique_valid_values": int(valid.nunique(dropna=True)),
                "example_values_raw": json.dumps(example_raw, ensure_ascii=False),
                "example_values_decoded": json.dumps(example_decoded, ensure_ascii=False),
                "top_value_counts": json.dumps({str(k): int(v) for k, v in counts.head(10).items()}, ensure_ascii=False),
                "value_labels": json.dumps(value_map, ensure_ascii=False),
                "codebook_comment": compact(cb.get("Comment", "")),
                "display_skip_logic": compact(" | ".join([cb.get("Block display logic", ""), cb.get("Question display logic", ""), cb.get("Skip logic", "")])),
            }
            if spatial:
                granularity, geographic_granularity, geographic_role, privacy = spatial_interpretation(
                    meta["variable_title"], varname, base["item_text"], base["codebook_comment"]
                )
                base.update({
                    "construct": granularity,
                    "likely_geographic_granularity": geographic_granularity,
                    "origin_or_destination": geographic_role,
                    "privacy_anonymization": privacy,
                })
            else:
                base.update({"migration_family": migration_family(meta["variable_title"])})
            rows.append(base)
    result = pd.DataFrame(rows)
    result["wave_order"] = result["wave"].map(WAVE_ORDER)
    result = result.sort_values(["wave_order", "standardized_title", "variable_name"]).drop(columns="wave_order")
    return result


spatial_df = profile_selected(spatial_map, spatial=True)
migration_df = profile_selected(migration_map, spatial=False)
spatial_df.to_csv(OUTPUT_TABLES / "bemp_spatial_variables.csv", index=False)
migration_df.to_csv(OUTPUT_TABLES / "bemp_migration_variables.csv", index=False)


def summarize_names(names: list[str], limit: int = 30) -> str:
    names = sorted(set(names))
    if len(names) <= limit:
        return "; ".join(names)
    return "; ".join(names[:limit]) + f"; … (+{len(names) - limit} more)"


baseline_ids = set(pd.read_csv(DATA_DIR / "bemp_w1.csv", usecols=["w1_reg1"], dtype=str, keep_default_na=False)["w1_reg1"])
spatial_by_wave = spatial_df.groupby("wave")["variable_name"].apply(list).to_dict()
migration_by_wave = migration_df.groupby("wave")["variable_name"].apply(list).to_dict()

inventory = []
for path in sorted(DATA_DIR.glob("*.csv"), key=lambda p: WAVE_ORDER[wave_from_name(p)]):
    wave = wave_from_name(path)
    rows, columns = csv_dimensions(path)
    mode, sample = wave_attributes(wave)
    respondent_id = RESPONDENT_IDS.get(wave, "")
    location_id = LOCATION_IDS.get(wave, "")
    distinct_respondents = ""
    distinct_households = ""
    duplicate_respondent_rows = ""
    baseline_overlap_pct = ""
    household_id = ""
    id_notes = ""
    if respondent_id:
        ids = pd.read_csv(path, usecols=[respondent_id], dtype=str, keep_default_na=False)[respondent_id]
        distinct_respondents = int(ids.nunique())
        duplicate_respondent_rows = int(ids.duplicated().sum())
        hh = ids.str.rsplit("-", n=1).str[0]
        distinct_households = int(hh.nunique())
        baseline_overlap_pct = round(100 * ids.isin(baseline_ids).mean(), 2)
        household_id = f"derive by removing final respondent-type suffix from {respondent_id}"
        id_notes = "Respondent code is the cross-wave key; household prefix is documented linkage key. Lxx/zone remain baseline-origin codes after migration."
    elif location_id:
        loc = pd.read_csv(path, usecols=[location_id], dtype=str, keep_default_na=False)[location_id]
        distinct_respondents = int(loc.nunique())
        id_notes = "Village-profile location code; joins to Lxx prefix embedded in respondent codes, subject to minor combined-code formatting in later profiles."
    inventory.append({
        "filename": path.name, "relative_path": str(path.relative_to(ROOT)), "file_class": "quantitative CSV",
        "wave": wave, "survey_mode": mode, "sample_type": sample, "rows": rows, "columns": columns,
        "apparent_respondent_id": respondent_id, "apparent_household_id": household_id,
        "apparent_village_location_id": location_id or ("Lxx prefix of respondent code" if respondent_id else ""),
        "distinct_respondent_or_location_ids": distinct_respondents,
        "distinct_derived_household_prefixes": distinct_households,
        "duplicate_respondent_id_rows": duplicate_respondent_rows,
        "respondent_id_overlap_with_w1_pct": baseline_overlap_pct,
        "spatial_variable_count": len(spatial_by_wave.get(wave, [])),
        "key_spatial_variables": summarize_names(spatial_by_wave.get(wave, [])),
        "migration_variable_count": len(migration_by_wave.get(wave, [])),
        "key_migration_variables": summarize_names(migration_by_wave.get(wave, [])),
        "apparent_role": f"{mode} {sample} survey data", "id_notes": id_notes,
    })

for path in sorted(CODEBOOK_DIR.glob("*_codebook.csv"), key=lambda p: WAVE_ORDER[wave_from_name(p)]):
    wave = wave_from_name(path)
    rows, columns = csv_dimensions(path)
    mode, sample = wave_attributes(wave)
    inventory.append({
        "filename": path.name, "relative_path": str(path.relative_to(ROOT)), "file_class": "codebook CSV",
        "wave": wave, "survey_mode": mode, "sample_type": sample, "rows": rows, "columns": columns,
        "apparent_respondent_id": RESPONDENT_IDS.get(wave, ""), "apparent_household_id": "",
        "apparent_village_location_id": LOCATION_IDS.get(wave, ""), "distinct_respondent_or_location_ids": "",
        "distinct_derived_household_prefixes": "", "duplicate_respondent_id_rows": "",
        "respondent_id_overlap_with_w1_pct": "", "spatial_variable_count": len(spatial_by_wave.get(wave, [])),
        "key_spatial_variables": summarize_names(spatial_by_wave.get(wave, [])),
        "migration_variable_count": len(migration_by_wave.get(wave, [])),
        "key_migration_variables": summarize_names(migration_by_wave.get(wave, [])),
        "apparent_role": f"Question text, labels, logic, and value codes for {wave}",
        "id_notes": "One codebook row per quantitative column.",
    })

inventory.append({
    "filename": VARIABLE_LIST.name, "relative_path": str(VARIABLE_LIST.relative_to(ROOT)), "file_class": "metadata XLSX",
    "wave": "cross-wave", "survey_mode": "mixed", "sample_type": "all", "rows": len(variable_list),
    "columns": len(variable_list.columns), "apparent_respondent_id": "Respondent Code concordance row",
    "apparent_household_id": "not explicit", "apparent_village_location_id": "Location Number concordance row",
    "distinct_respondent_or_location_ids": "", "distinct_derived_household_prefixes": "",
    "duplicate_respondent_id_rows": "", "respondent_id_overlap_with_w1_pct": "", "spatial_variable_count": "",
    "key_spatial_variables": "Cross-wave standardized titles/labels and wave-specific variable names",
    "migration_variable_count": "", "key_migration_variables": "Cross-wave standardized titles/labels and wave-specific variable names",
    "apparent_role": "Full cross-wave variable concordance", "id_notes": "7,419 data rows; README states 7,420.",
})

readme = RAW / "metadata" / "README.md"
inventory.append({
    "filename": readme.name, "relative_path": str(readme.relative_to(ROOT)), "file_class": "metadata Markdown",
    "wave": "cross-wave", "survey_mode": "mixed", "sample_type": "all", "rows": len(readme.read_text(encoding="utf-8").splitlines()),
    "columns": "", "apparent_respondent_id": "", "apparent_household_id": "", "apparent_village_location_id": "",
    "distinct_respondent_or_location_ids": "", "distinct_derived_household_prefixes": "", "duplicate_respondent_id_rows": "",
    "respondent_id_overlap_with_w1_pct": "", "spatial_variable_count": "", "key_spatial_variables": "",
    "migration_variable_count": "", "key_migration_variables": "", "apparent_role": "Official dataset README",
    "id_notes": "",
})

for path in sorted((RAW / "archives").glob("*.zip")):
    with zipfile.ZipFile(path) as archive:
        entries = [info for info in archive.infolist() if not info.is_dir()]
    inventory.append({
        "filename": path.name, "relative_path": str(path.relative_to(ROOT)), "file_class": "source ZIP archive",
        "wave": "cross-wave", "survey_mode": "mixed", "sample_type": "all", "rows": "", "columns": "",
        "apparent_respondent_id": "", "apparent_household_id": "", "apparent_village_location_id": "",
        "distinct_respondent_or_location_ids": "", "distinct_derived_household_prefixes": "", "duplicate_respondent_id_rows": "",
        "respondent_id_overlap_with_w1_pct": "", "spatial_variable_count": "", "key_spatial_variables": "",
        "migration_variable_count": "", "key_migration_variables": "", "apparent_role": f"Original archive ({len(entries)} file entries)",
        "id_notes": "Preserved byte-for-byte; archive integrity tested.",
    })

desktop_ini = CODEBOOK_DIR / "desktop.ini"
if desktop_ini.exists():
    inventory.append({
        "filename": desktop_ini.name, "relative_path": str(desktop_ini.relative_to(ROOT)), "file_class": "auxiliary OS file",
        "wave": "", "survey_mode": "", "sample_type": "", "rows": "", "columns": "",
        "apparent_respondent_id": "", "apparent_household_id": "", "apparent_village_location_id": "",
        "distinct_respondent_or_location_ids": "", "distinct_derived_household_prefixes": "", "duplicate_respondent_id_rows": "",
        "respondent_id_overlap_with_w1_pct": "", "spatial_variable_count": "", "key_spatial_variables": "",
        "migration_variable_count": "", "key_migration_variables": "", "apparent_role": "Non-data Windows metadata included in source archive",
        "id_notes": "Not a BEMP dataset.",
    })

inventory_df = pd.DataFrame(inventory)
inventory_df.to_csv(OUTPUT_TABLES / "bemp_file_inventory.csv", index=False)

print(json.dumps({
    "inventory_rows": len(inventory_df),
    "spatial_rows": len(spatial_df),
    "migration_rows": len(migration_df),
    "spatial_by_wave": spatial_df.groupby("wave").size().to_dict(),
    "migration_by_family": migration_df.groupby("migration_family").size().to_dict(),
}, indent=2))
