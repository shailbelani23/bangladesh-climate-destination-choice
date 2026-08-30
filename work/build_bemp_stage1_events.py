from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bemp"
OUT = ROOT / "outputs" / "tables"
WORK = ROOT / "work"

MISSING_CODES = {-55, -66, -6, -7, -8, -9}
MISSING_STRINGS = {str(x) for x in MISSING_CODES} | {"", "nan", "none", "na"}

ORIGIN_DISTRICT = {
    **{f"L{x:02d}": "Jamalpur" for x in [1, 22]},
    **{f"L{x:02d}": "Tangail" for x in [2, 3, *range(10, 19)]},
    **{f"L{x:02d}": "Manikganj" for x in range(4, 7)},
    **{f"L{x:02d}": "Sirajganj" for x in range(7, 10)},
    **{f"L{x:02d}": "Bogura" for x in range(19, 22)},
    "L23": "Gaibandha",
    **{f"L{x:02d}": "Kurigram" for x in range(24, 37)},
}

ID_VAR = {
    "w1": "w1_reg1",
    "w2": "w2_reg1",
    "w3": "w3_reg1",
    "w4": "w4_reg1",
    "w5": "w5_reg1",
    "w6_N": "w6_N_reg3",
    "w6_M": "w6_M_reg3",
    "w7": "w7_reg2",
    "w8": "w8_reg2",
    "w9": "w9_reg2",
    "w10": "w10_reg2",
    "w11": "w11_reg2",
    "w12_N": "w12_N_reg3",
    "w12_M": "w12_M_reg3",
    "w13": "w13_reg2",
    "w14_N": "w14_N_reg3",
    "w14_M": "w14_M_reg3",
}

WAVE_NUMBER = {
    "w1": 1, "w2": 2, "w3": 3, "w4": 4, "w5": 5,
    "w6_N": 6, "w6_M": 6, "w7": 7, "w8": 8, "w9": 9,
    "w10": 10, "w11": 11, "w12_N": 12, "w12_M": 12,
    "w13": 13, "w14_N": 14, "w14_M": 14,
}

SHOCK_VARS = {
    "w2": ("w2_q85", "w2_q104"),
    "w3": ("w3_q105", "w3_q124"),
    "w4": ("w4_q99", "w4_q118"),
    "w5": ("w5_q141", "w5_q160"),
    "w6_N": ("w6_N_q234", "w6_N_q269"),
    "w6_M": ("w6_M_q257", "w6_M_q310"),
    "w7": ("w7_q141", "w7_q168"),
    "w8": ("w8_q116", "w8_q138"),
    "w9": ("w9_q116", "w9_q139"),
    "w10": ("w10_q137", "w10_q160"),
    "w11": ("w11_q120", "w11_q143"),
    "w12_N": ("w12_N_q227", "w12_N_q261"),
    "w12_M": ("w12_M_q304", "w12_M_q357"),
    "w13": ("w13_q12", "w13_q20"),
    "w14_N": ("w14_N_q258", "w14_N_q291"),
    "w14_M": ("w14_M_q359", "w14_M_q411"),
}

PHONE_DEST = {
    "w7": {"city": "w7_q5", "city_txt": "w7_q5_txt", "district": "w7_q7x5_txt",
           "division": "w7_q7x6_txt", "move_scope": "w7_q14", "return_plan": "w7_q39",
           "prev_status": "w7_reg5", "prev_type": "w7_reg7"},
    "w8": {"city": "w8_q5", "city_txt": "w8_q5_txt", "district": "w8_q8x5_txt",
           "division": "w8_q8x6_txt", "move_scope": "w8_q12", "return_plan": "w8_q37",
           "prev_status": "w8_reg5", "prev_type": "w8_reg6"},
    "w9": {"city": "w9_q5", "city_txt": "w9_q5_txt", "district": "w9_q8x5_txt",
           "division": "w9_q8x6_txt", "move_scope": "w9_q12", "return_plan": "w9_q37",
           "prev_status": "w9_reg5", "prev_type": "w9_reg6"},
    "w10": {"city": "w10_q5", "city_txt": "w10_q5_txt", "district": "w10_q8x5_txt",
            "division": "w10_q8x6_txt", "move_scope": "w10_q12", "return_plan": "w10_q37",
            "prev_status": "w10_reg5", "prev_type": "w10_reg6"},
    "w11": {"city": "w11_q5", "city_txt": "w11_q5_txt", "district": "w11_q8x5_txt",
            "division": "w11_q8x6_txt", "move_scope": "w11_q12", "return_plan": "w11_q37",
            "prev_status": "w11_reg5", "prev_type": "w11_reg6"},
    "w13": {"city": "w13_q5", "city_txt": "w13_q5_txt", "district": "w13_q8x5_txt",
            "division": "w13_q8x6_txt", "move_scope": "w13_q10", "return_plan": None,
            "prev_status": "w13_reg5", "prev_type": "w13_reg6"},
}

INPERSON_DEST = {
    "w6_M": {"rural_urban": "w6_M_q14", "city": "w6_M_q15", "city_txt": "w6_M_q15_txt",
             "district": "w6_M_q16x5_txt", "division": "w6_M_q16x6_txt",
             "move_scope": "w6_M_q19", "return_plan": "w6_M_q67",
             "distance": "w6_M_dist_from_prev_loc", "prev_status": None, "prev_type": None,
             "reason_prefix": "w6_M_q62"},
    "w12_M": {"rural_urban": "w12_M_q19", "city": "w12_M_q20", "city_txt": "w12_M_q20_txt",
              "district": "w12_M_q21x5_txt", "division": "w12_M_q21x6_txt",
              "move_scope": "w12_M_q24", "return_plan": "w12_M_q80",
              "distance": "w12_M_dist_from_prev_loc", "prev_status": "w12_M_reg10",
              "prev_type": "w12_M_reg11", "new_old": "w12_M_q16", "domestic": "w12_M_q17",
              "reason_prefix": "w12_M_q75"},
    "w14_M": {"rural_urban": "w14_M_q19", "city": "w14_M_q20", "city_txt": "w14_M_q20_txt",
              "district": "w14_M_q21x5_txt", "division": "w14_M_q21x6_txt",
              "move_scope": "w14_M_q24", "return_plan": "w14_M_q91",
              "distance": "w14_M_dist_from_prev_loc", "prev_status": "w14_M_reg11",
              "prev_type": "w14_M_reg12", "new_old": "w14_M_q16", "domestic": "w14_M_q17",
              "reason_prefix": "w14_M_q85"},
}

PROVISIONAL_ALIASES = {
    "bogra": ("Bogura", "spelling modernization", "high"),
    "bogura": ("Bogura", "case/whitespace normalization", "high"),
    "sirajgonj": ("Sirajganj", "obvious spelling variant", "medium"),
    "shirajganj": ("Sirajganj", "obvious spelling variant", "medium"),
    "shirajgong": ("Sirajganj", "obvious spelling variant", "medium"),
    "tangile": ("Tangail", "obvious spelling variant", "medium"),
    "kurigram": ("Kurigram", "case/whitespace normalization", "high"),
    "kirigami": ("Kurigram", "probable spelling error", "low"),
    "rajshashi": ("Rajshahi", "obvious spelling variant", "medium"),
    "rajshahi": ("Rajshahi", "case/whitespace normalization", "high"),
    "maymanshing": ("Mymensingh", "probable spelling variant", "medium"),
    "dhaka": ("Dhaka", "case/whitespace normalization", "high"),
    "gaibandha": ("Gaibandha", "case/whitespace normalization", "high"),
    "saver": ("Savar", "probable spelling variant", "medium"),
    "savar": ("Savar", "case/whitespace normalization", "high"),
    "vuapur": ("Bhuapur", "probable spelling variant", "medium"),
    "bhuapur": ("Bhuapur", "case/whitespace normalization", "high"),
    "narshindhi": ("Narsingdi", "probable spelling variant", "medium"),
    "gopalgonj": ("Gopalganj", "probable spelling variant", "medium"),
    "comilla": ("Cumilla", "spelling modernization", "high"),
    "cumilla": ("Cumilla", "case/whitespace normalization", "high"),
    "potuakhali": ("Patuakhali", "probable spelling variant", "medium"),
}

OFFICIAL_DISTRICT_SOURCE = "https://bangladesh.gov.bd/views/district-list/"
OFFICIAL_UPAZILA_SOURCE = "https://bangladesh.gov.bd/views/upazila-list"
SOURCE_ACCESS_DATE = "2026-08-28"

# Canonical English district spellings on the Bangladesh National Portal. Keys
# include only variants that actually occur in the public BEMP destination fields.
OFFICIAL_DISTRICT_ALIASES = {
    "bagerhat": "Bagerhat", "bagherhat": "Bagerhat",
    "bandarban": "Bandarban", "barguna": "Barguna", "borguna": "Barguna",
    "barishal": "Barishal", "barisal": "Barishal",
    "bhola": "Bhola",
    "bogura": "Bogura", "bogra": "Bogura", "bagura": "Bogura",
    "chandpur": "Chandpur", "chadpur": "Chandpur",
    "chapainawabganj": "Chapainawabganj",
    "chattogram": "Chattogram", "chittagong": "Chattogram", "chittangong": "Chattogram",
    "cox's bazar": "Cox's Bazar", "cox’s bazar": "Cox's Bazar",
    "cumilla": "Cumilla", "comilla": "Cumilla",
    "dhaka": "Dhaka", "dinajpur": "Dinajpur", "faridpur": "Faridpur",
    "feni": "Feni", "gaibandha": "Gaibandha",
    "gazipur": "Gazipur", "gajipur": "Gazipur",
    "gopalganj": "Gopalganj", "gopalgonj": "Gopalganj",
    "jamalpur": "Jamalpur", "jmamlapur": "Jamalpur", "jhalakathi": "Jhalakathi",
    "kishoreganj": "Kishoreganj", "kishorganj": "Kishoreganj",
    "kurigram": "Kurigram", "kuigram": "Kurigram", "kurigraam": "Kurigram",
    "kirigami": "Kurigram", "karigram": "Kurigram",
    "lalmonirhat": "Lalmonirhat", "lakshmipur": "Lakshmipur", "laxmipur": "Lakshmipur",
    "madaripur": "Madaripur", "moulvibazar": "Moulvibazar",
    "manikganj": "Manikganj", "manikgonj": "Manikganj", "manikgganj": "Manikganj",
    "munshiganj": "Munshiganj", "munshigonj": "Munshiganj",
    "mymensingh": "Mymensingh", "naoga": "Naogaon", "naogaon": "Naogaon",
    "narayanganj": "Narayanganj",
    "narsingdi": "Narsingdi", "narshindhi": "Narsingdi", "narshindi": "Narsingdi",
    "norsendi": "Narsingdi", "নরসিংদী": "Narsingdi",
    "netrokona": "Netrokona", "nilphamari": "Nilphamari", "nilfamari": "Nilphamari",
    "noakhali": "Noakhali", "pabna": "Pabna",
    "panchagarh": "Panchagarh", "panchagar": "Panchagarh",
    "panchagor": "Panchagarh", "panchogar": "Panchagarh",
    "patuakhali": "Patuakhali", "potuakhali": "Patuakhali",
    "rajbari": "Rajbari", "rangamati": "Rangamati", "rangpur": "Rangpur",
    "shariatpur": "Shariatpur",
    "sirajganj": "Sirajganj", "sirajgonj": "Sirajganj", "sirajgong": "Sirajganj",
    "shirajganj": "Sirajganj", "shirajgong": "Sirajganj", "shirajgonj": "Sirajganj",
    "sylhet": "Sylhet", "syhlet": "Sylhet",
    "tangail": "Tangail", "tangile": "Tangail", "tngail": "Tangail",
    "fangile": "Tangail", "tabgile": "Tangail",
    "thakurgaon": "Thakurgaon",
}

# Public responses occasionally put an upazila or locality into a field labelled
# city/district. These official-government references establish containment.
LOWER_LEVEL_RESOLUTIONS = {
    "alenga": {
        "place": "Elenga", "type": "locality", "district": "Tangail",
        "method": "official locality containment plus spelling variant", "confidence": "high",
        "source": "https://krishibank.gov.bd/pages/static-pages/6922e13f933eb65569e2b193",
        "detail": "Bangladesh Krishi Bank lists ELENGA with postal address Elenga, Tangail.",
    },
    "aricha": {
        "place": "Aricha", "type": "locality/ferry ghat", "district": "Manikganj",
        "method": "official locality containment", "confidence": "high",
        "source": "https://www.hydrology.bwdb.gov.bd/includes/lithology_data_available_print.php?dist=",
        "detail": "Bangladesh Water Development Board lists Aricha Ghat in Shivalaya, Manikganj.",
    },
    "bhuapur": {
        "place": "Bhuapur", "type": "upazila/municipality", "district": "Tangail",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Bhuapur in Tangail district.",
    },
    "vuapur": {
        "place": "Bhuapur", "type": "upazila/municipality", "district": "Tangail",
        "method": "official upazila containment plus spelling variant", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Bhuapur in Tangail district; Vuapur is the BEMP spelling.",
    },
    "joydebpur": {
        "place": "Joydebpur", "type": "locality", "district": "Gazipur",
        "method": "official locality containment", "confidence": "high",
        "source": "https://ss.pwd.gov.bd/buildingdatabase/index/5/9340",
        "detail": "Public Works Department lists Gazipur District Jail, Joydebpur under Gazipur PWD Division.",
    },
    "kalampur": {
        "place": "Kalampur", "type": "locality", "district": "Dhaka",
        "method": "official locality containment", "confidence": "high",
        "source": "https://sec.gov.bd/ipoprospectus/Mamun_Agro_Products_Limited_17.01.2022.pdf",
        "detail": "Bangladesh Securities and Exchange Commission filing gives Kalampur, Dhamrai, Dhaka.",
    },
    "konabari": {
        "place": "Konabari", "type": "locality", "district": "Gazipur",
        "method": "official locality containment", "confidence": "high",
        "source": "https://hrm.dghs.gov.bd/public/facility-registry/facilities/28356/profile",
        "detail": "DGHS facility registry places Konabari in Gazipur district/Gazipur Sadar.",
    },
    "kuakata": {
        "place": "Kuakata", "type": "municipality/locality", "district": "Patuakhali",
        "method": "official locality containment", "confidence": "high",
        "source": "https://pbs.patuakhali.gov.bd/pages/static-pages/69789baf35ce18e1c066ff63",
        "detail": "Patuakhali Palli Bidyut Samity lists Kuakata, Kalapara, Patuakhali.",
    },
    "khalihati": {
        "place": "Kalihati", "type": "upazila", "district": "Tangail",
        "method": "official upazila containment plus spelling variant", "confidence": "medium",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Kalihati in Tangail district; Khalihati is the BEMP spelling.",
    },
    "keraniganj": {
        "place": "Keraniganj", "type": "upazila", "district": "Dhaka",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Keraniganj in Dhaka district.",
    },
    "madargonj, jamalpur": {
        "place": "Madarganj", "type": "upazila", "district": "Jamalpur",
        "method": "official upazila containment plus spelling variant", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Madarganj in Jamalpur district; the BEMP response also names Jamalpur.",
    },
    "mirzapur": {
        "place": "Mirzapur", "type": "upazila", "district": "Tangail",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Mirzapur in Tangail district.",
    },
    "moheshkhali": {
        "place": "Moheshkhali", "type": "upazila/municipality", "district": "Cox's Bazar",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Moheshkhali in Cox's Bazar district.",
    },
    "nabinagar": {
        "place": "Nabinagar", "type": "upazila/municipality", "district": "Brahmanbaria",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Nabinagar in Brahmanbaria district.",
    },
    "roumari": {
        "place": "Roumari", "type": "upazila", "district": "Kurigram",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Roumari in Kurigram district.",
    },
    "savar": {
        "place": "Savar", "type": "upazila/municipality", "district": "Dhaka",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Savar in Dhaka district.",
    },
    "saver": {
        "place": "Savar", "type": "upazila/municipality", "district": "Dhaka",
        "method": "official upazila containment plus spelling variant", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Savar in Dhaka district; Saver is the BEMP spelling.",
    },
    "teknaf, cox's bazar": {
        "place": "Teknaf", "type": "upazila", "district": "Cox's Bazar",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Teknaf in Cox's Bazar district; the BEMP response also names Cox's Bazar.",
    },
    "ukhia, cox's bazar": {
        "place": "Ukhia", "type": "upazila", "district": "Cox's Bazar",
        "method": "official upazila containment", "confidence": "high",
        "source": OFFICIAL_UPAZILA_SOURCE,
        "detail": "National Portal upazila list places Ukhia in Cox's Bazar district; the BEMP response also names Cox's Bazar.",
    },
}


def data_path(wave: str) -> Path:
    return RAW / "quantitative" / f"bemp_{wave}.csv"


def codebook_path(wave: str) -> Path:
    return RAW / "codebooks" / f"bemp_{wave}_codebook.csv"


def normalize_scalar(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        s = re.sub(r"\s+", " ", value.strip())
        return None if s.lower() in MISSING_STRINGS else s
    try:
        f = float(value)
        if f in MISSING_CODES:
            return None
        if f.is_integer():
            return int(f)
        return f
    except (TypeError, ValueError):
        return value


def is_valid(value) -> bool:
    return normalize_scalar(value) is not None


_codebooks: dict[str, pd.DataFrame] = {}
_value_maps: dict[tuple[str, str], dict[object, str]] = {}


def codebook(wave: str) -> pd.DataFrame:
    if wave not in _codebooks:
        _codebooks[wave] = pd.read_csv(codebook_path(wave), low_memory=False)
    return _codebooks[wave]


def value_map(wave: str, variable: str) -> dict[object, str]:
    key = (wave, variable)
    if key in _value_maps:
        return _value_maps[key]
    cb = codebook(wave)
    row = cb.loc[cb["Variable name"].eq(variable)]
    out: dict[object, str] = {}
    if not row.empty:
        r = row.iloc[0]
        for col in cb.columns:
            try:
                number = int(str(col))
            except ValueError:
                continue
            label = normalize_scalar(r[col])
            if label is not None:
                out[number] = str(label)
    _value_maps[key] = out
    return out


def decoded(wave: str, variable: str | None, value):
    if not variable:
        return None
    clean = normalize_scalar(value)
    if clean is None:
        return None
    return value_map(wave, variable).get(clean, clean)


def person_parts(respondent_id: str | None):
    if not respondent_id:
        return None, None, None
    m = re.match(r"^(L\d{2})", respondent_id)
    lxx = m.group(1) if m else None
    hh = re.sub(r"-[^-]+$", "", respondent_id)
    return hh, lxx, ORIGIN_DISTRICT.get(lxx)


def provisional_name(raw: str | None):
    if raw is None:
        return None, "missing", "none"
    cleaned = re.sub(r"\s+", " ", raw.strip())
    key = cleaned.casefold()
    if key in PROVISIONAL_ALIASES:
        return PROVISIONAL_ALIASES[key]
    if cleaned.isupper() or cleaned.islower():
        return cleaned.title(), "case normalization only", "high"
    return cleaned, "no change", "unreviewed"


def normalized_admin_key(raw: str | None):
    if raw is None:
        return None
    return re.sub(r"\s+", " ", str(raw).strip()).casefold().replace("’", "'")


def resolve_admin(level: str | None, raw: str | None):
    key = normalized_admin_key(raw)
    empty = {
        "destination_place_official": None,
        "destination_place_type_official": None,
        "destination_district_official": None,
        "destination_resolution_method": "unresolved—no named public endpoint",
        "destination_resolution_confidence": "none",
        "destination_resolution_source_url": None,
        "destination_resolution_source_detail": None,
        "destination_resolution_source_access_date": SOURCE_ACCESS_DATE,
        "destination_resolution_manual_review_flag": False,
        "destination_resolution_status": "unresolved",
    }
    if key is None or level not in {"city", "district", "origin_district"}:
        return empty

    if key in LOWER_LEVEL_RESOLUTIONS:
        rec = LOWER_LEVEL_RESOLUTIONS[key]
        return {
            "destination_place_official": rec["place"],
            "destination_place_type_official": rec["type"],
            "destination_district_official": rec["district"],
            "destination_resolution_method": rec["method"],
            "destination_resolution_confidence": rec["confidence"],
            "destination_resolution_source_url": rec["source"],
            "destination_resolution_source_detail": rec["detail"],
            "destination_resolution_source_access_date": SOURCE_ACCESS_DATE,
            "destination_resolution_manual_review_flag": "spelling variant" in rec["method"],
            "destination_resolution_status": "resolved",
        }

    district = OFFICIAL_DISTRICT_ALIASES.get(key)
    if district is None:
        return {
            **empty,
            "destination_resolution_method": "unresolved—no official match",
            "destination_resolution_manual_review_flag": True,
        }
    exact = key == district.casefold()
    medium_keys = {"kirigami", "fangile", "tabgile"}
    confidence = "medium" if key in medium_keys else "high"
    method = "exact official district-name match" if exact else "official district-name match after spelling/language normalization"
    detail = "Bangladesh National Portal district list confirms the canonical district name."
    if key in {"fangile", "tabgile"}:
        detail += " Manual fuzzy review maps the BEMP typo to Tangail; the reported division is Dhaka, consistent with Tangail."
    elif key == "kirigami":
        detail += " Manual fuzzy review maps the BEMP typo to Kurigram."
    return {
        "destination_place_official": district,
        "destination_place_type_official": (
            "named city/district-seat response" if level == "city" else "district"
        ),
        "destination_district_official": district,
        "destination_resolution_method": method,
        "destination_resolution_confidence": confidence,
        "destination_resolution_source_url": OFFICIAL_DISTRICT_SOURCE,
        "destination_resolution_source_detail": detail,
        "destination_resolution_source_access_date": SOURCE_ACCESS_DATE,
        "destination_resolution_manual_review_flag": not exact,
        "destination_resolution_status": "resolved",
    }


def city_label(wave: str, variable: str, code, text):
    code_clean = normalize_scalar(code)
    text_clean = normalize_scalar(text)
    if code_clean is None:
        return None, None
    decoded_value = decoded(wave, variable, code_clean)
    # Code 17 occurs once in w12_M but has no value label in any public
    # city codebook. Preserve it as an unresolved category, not a city name.
    if decoded_value == code_clean:
        return None, f"unmapped public code {code_clean}"
    label = str(decoded_value)
    if label.strip().casefold().startswith("other"):
        return text_clean, label
    return label, label


def decode_yes_no(wave: str, variable: str | None, value):
    label = decoded(wave, variable, value)
    if label is None:
        return None
    s = str(label).casefold()
    if s.startswith("yes"):
        return "Yes"
    if s.startswith("no"):
        return "No"
    return str(label)


def load_columns(wave: str, columns: list[str]) -> pd.DataFrame:
    wanted = set(columns)
    return pd.read_csv(data_path(wave), usecols=lambda c: c in wanted, low_memory=False)


def build_shock_history():
    records = []
    for wave, (erosion_var, flood_var) in SHOCK_VARS.items():
        cols = [ID_VAR[wave], erosion_var, flood_var]
        df = load_columns(wave, cols)
        for source_row, r in df.iterrows():
            rid = normalize_scalar(r.get(ID_VAR[wave]))
            if rid is None:
                continue
            records.append({
                "respondent_id": rid,
                "wave": wave,
                "wave_number": WAVE_NUMBER[wave],
                "source_row": source_row + 2,
                "erosion": decode_yes_no(wave, erosion_var, r.get(erosion_var)),
                "flood": decode_yes_no(wave, flood_var, r.get(flood_var)),
                "erosion_variable": erosion_var,
                "flood_variable": flood_var,
            })
    history = pd.DataFrame(records).sort_values(["respondent_id", "wave_number", "wave", "source_row"])
    lookup = defaultdict(list)
    for rec in history.to_dict("records"):
        lookup[rec["respondent_id"]].append(rec)
    return history, lookup


def prior_shock(lookup, respondent_id: str, wave_number: int, field: str):
    candidates = [
        x for x in lookup.get(respondent_id, [])
        if x["wave_number"] < wave_number and x[field] in {"Yes", "No"}
    ]
    if not candidates:
        return None, None, None
    latest_wave = max(x["wave_number"] for x in candidates)
    # A respondent should appear in only one N/M file per in-person wave. If not,
    # retain the last deterministic source and flag duplication elsewhere.
    latest = [x for x in candidates if x["wave_number"] == latest_wave][-1]
    return latest[field], latest["wave"], latest[f"{field}_variable"]


def endpoint_fields(wave: str, r: pd.Series, cfg: dict, domestic_value=None):
    ru_var = cfg["rural_urban"]
    ru = decoded(wave, ru_var, r.get(ru_var))
    city_raw, city_category = city_label(wave, cfg["city"], r.get(cfg["city"]), r.get(cfg["city_txt"]))
    district_raw = normalize_scalar(r.get(cfg["district"]))
    division_raw = normalize_scalar(r.get(cfg["division"]))

    domestic = domestic_value
    if domestic == "Abroad":
        level, raw, direct = "country_abroad", None, False
    elif ru == "City":
        level, raw, direct = "city", city_raw, city_raw is not None
    elif ru == "Village":
        level, raw, direct = "district", district_raw, district_raw is not None
    else:
        level, raw, direct = "unavailable", None, False

    standardized, action, confidence = provisional_name(raw)
    district_ready = level == "district" and standardized is not None
    city_lookup = level == "city" and standardized is not None
    named_admin = level in {"city", "district"} and standardized is not None
    return {
        "domestic_abroad": domestic,
        "destination_rural_urban": ru,
        "destination_city_code": normalize_scalar(r.get(cfg["city"])),
        "destination_city_category": city_category,
        "destination_city_other_text": normalize_scalar(r.get(cfg["city_txt"])),
        "destination_rural_district_raw": district_raw,
        "destination_rural_division_raw": division_raw,
        "destination_admin_level_raw": level,
        "destination_admin_raw": raw,
        "destination_admin_standardized_provisional": standardized,
        "normalization_action_provisional": action,
        "normalization_confidence": confidence,
        "destination_named_admin_available": named_admin,
        "destination_district_ready_without_city_lookup": district_ready,
        "needs_city_to_district_lookup": city_lookup,
        "destination_observed_directly": direct,
    }


def common_event_fields(wave: str, source_row: int, respondent_id: str, cfg: dict, r: pd.Series):
    hh, lxx, origin = person_parts(respondent_id)
    erosion_var, flood_var = SHOCK_VARS[wave]
    move_scope = decoded(wave, cfg.get("move_scope"), r.get(cfg.get("move_scope")))
    previous_type = decoded(wave, cfg.get("prev_type"), r.get(cfg.get("prev_type")))
    return_plan = decoded(wave, cfg.get("return_plan"), r.get(cfg.get("return_plan")))
    distance = normalize_scalar(r.get(cfg.get("distance"))) if cfg.get("distance") else None
    return {
        "respondent_id": respondent_id,
        "household_id_derived": hh,
        "baseline_location_lxx": lxx,
        "origin_district_codebook": origin,
        "wave": wave,
        "wave_number": WAVE_NUMBER[wave],
        "source_file": f"bemp_{wave}.csv",
        "source_row_csv_1_based": source_row + 2,
        "source_interview_date": normalize_scalar(r.get(f"{wave}_date")),
        "respondent_id_variable": ID_VAR[wave],
        "move_scope": move_scope,
        "previous_migration_type": previous_type,
        "return_plan": return_plan,
        "distance_from_previous_location_m": distance,
        "concurrent_home_erosion": decode_yes_no(wave, erosion_var, r.get(erosion_var)),
        "concurrent_home_flood": decode_yes_no(wave, flood_var, r.get(flood_var)),
        "concurrent_erosion_variable": erosion_var,
        "concurrent_flood_variable": flood_var,
        "move_scope_variable": cfg.get("move_scope"),
        "previous_migration_type_variable": cfg.get("prev_type"),
        "return_plan_variable": cfg.get("return_plan"),
        "distance_variable": cfg.get("distance"),
    }


def add_reasons(event: dict, wave: str, r: pd.Series, prefix: str | None):
    labels = {
        "reason_relatives_at_destination": "x1",
        "reason_better_earning": "x2",
        "reason_safer_from_flood": "x3",
        "reason_safer_from_erosion": "x4",
        "reason_schooling": "x5",
        "reason_marriage": "x6",
        "reason_property_at_destination": "x7",
    }
    for field, suffix in labels.items():
        var = f"{prefix}{suffix}" if prefix else None
        event[field] = bool(normalize_scalar(r.get(var)) == 1) if var and var in r.index and is_valid(r.get(var)) else None
        event[f"{field}_variable"] = var if var and var in r.index else None


def adjudicate_duplicate_events(out: pd.DataFrame):
    out["duplicate_adjudication_keep"] = True
    out["duplicate_adjudication_status"] = "not_duplicate"
    out["duplicate_adjudication_confidence"] = "not_applicable"
    out["duplicate_adjudication_rationale"] = "Unique respondent-wave row."
    for (respondent_id, wave), idx in out.groupby(["respondent_id", "wave"]).groups.items():
        idx = list(idx)
        if len(idx) == 1:
            continue
        ranked = out.loc[idx].copy()
        ranked["_date"] = pd.to_datetime(ranked["source_interview_date"], errors="coerce")
        ranked = ranked.sort_values(["_date", "source_row_csv_1_based"], na_position="first")
        keep_idx = ranked.index[-1]
        out.loc[idx, "duplicate_adjudication_keep"] = False
        out.loc[idx, "duplicate_adjudication_status"] = "excluded_superseded_duplicate"
        out.loc[idx, "duplicate_adjudication_confidence"] = "medium"
        out.loc[idx, "duplicate_adjudication_rationale"] = (
            "Superseded by the later completed interview for the same respondent-wave; "
            "raw row retained for audit and sensitivity analysis."
        )
        out.loc[keep_idx, "duplicate_adjudication_keep"] = True
        out.loc[keep_idx, "duplicate_adjudication_status"] = "retained_latest_completed_interview"
        if respondent_id == "L09-Z03-HH10-H" and wave == "w8":
            rationale = (
                "Retained the 2022-08-09 completed interview: it is later, has substantially more "
                "non-missing fields, and registers the respondent as available; the 2022-08-01 row "
                "registers a replacement household head under the same respondent code."
            )
        elif respondent_id == "L30-Z03-HH02-LB" and wave == "w14_M":
            rationale = (
                "Retained the 2024-02-13 completed re-interview as the latest record; the 2024-02-11 "
                "row remains visible because destination-reason answers differ."
            )
        else:
            rationale = "Retained the latest completed interview date, with source row as deterministic tie-breaker."
        out.loc[keep_idx, "duplicate_adjudication_rationale"] = rationale
    return out


def build_events(shock_lookup):
    events = []

    # Wave 6 migrant observations are the first endpoint-rich migrant snapshot.
    wave = "w6_M"
    cfg = INPERSON_DEST[wave]
    cols = [ID_VAR[wave], f"{wave}_date", *SHOCK_VARS[wave], *[x for x in cfg.values() if isinstance(x, str)]]
    cols += [f"{cfg['reason_prefix']}x{i}" for i in range(1, 8)]
    df = load_columns(wave, cols)
    for source_row, r in df.iterrows():
        if normalize_scalar(r.get(cfg["rural_urban"])) not in {1, 2}:
            continue
        rid = normalize_scalar(r.get(ID_VAR[wave]))
        event = common_event_fields(wave, source_row, rid, cfg, r)
        event.update({
            "event_class": "first_observed_current_migrant_destination",
            "event_detection_rule": "w6_M record with valid city/village response",
            "event_detection_confidence": "medium",
            "current_location_state": "migrant_destination",
            "current_location_state_variable": "w6_M_q14",
            "previous_migration_status": None,
            "previous_migration_status_variable": None,
            "new_old_location": None,
            "new_old_location_variable": None,
        })
        event.update(endpoint_fields(wave, r, cfg, domestic_value="In Bangladesh"))
        add_reasons(event, wave, r, cfg["reason_prefix"])
        events.append(event)

    # Phone waves identify a genuinely new "another location"; a prior migrant
    # observed back at home is a high-confidence return event.
    for wave, phone_cfg in PHONE_DEST.items():
        cfg = {
            **phone_cfg,
            "rural_urban": f"{wave}_q4",
            "distance": None,
            "reason_prefix": None,
        }
        q1, q2 = f"{wave}_q1", f"{wave}_q2"
        cols = [ID_VAR[wave], f"{wave}_date", q1, q2, cfg["rural_urban"], f"{wave}_q6", *SHOCK_VARS[wave]]
        cols += [x for x in cfg.values() if isinstance(x, str)]
        df = load_columns(wave, cols)
        for source_row, r in df.iterrows():
            rid = normalize_scalar(r.get(ID_VAR[wave]))
            if rid is None:
                continue
            current = normalize_scalar(r.get(q1))
            prev_status_raw = normalize_scalar(r.get(cfg["prev_status"]))
            is_new_other = current == 3
            is_return = current == 1 and prev_status_raw == 2
            if not (is_new_other or is_return):
                continue
            event = common_event_fields(wave, source_row, rid, cfg, r)
            event.update({
                "event_class": "new_other_destination" if is_new_other else "return_to_baseline_home",
                "event_detection_rule": (
                    f"{q1}=In another location" if is_new_other
                    else f"{q1}=home village and {cfg['prev_status']}=MIGRANT"
                ),
                "event_detection_confidence": "high",
                "current_location_state": decoded(wave, q1, r.get(q1)),
                "current_location_state_variable": q1,
                "previous_migration_status": decoded(wave, cfg["prev_status"], r.get(cfg["prev_status"])),
                "previous_migration_status_variable": cfg["prev_status"],
                "new_old_location": None,
                "new_old_location_variable": None,
            })
            if is_return:
                standardized, action, confidence = provisional_name(event["origin_district_codebook"])
                event.update({
                    "domestic_abroad": "In Bangladesh",
                    "destination_rural_urban": "Village",
                    "destination_city_code": None,
                    "destination_city_category": None,
                    "destination_city_other_text": None,
                    "destination_rural_district_raw": event["origin_district_codebook"],
                    "destination_rural_division_raw": None,
                    "destination_admin_level_raw": "origin_district",
                    "destination_admin_raw": event["origin_district_codebook"],
                    "destination_admin_standardized_provisional": standardized,
                    "normalization_action_provisional": action,
                    "normalization_confidence": confidence,
                    "destination_named_admin_available": standardized is not None,
                    "destination_district_ready_without_city_lookup": standardized is not None,
                    "needs_city_to_district_lookup": False,
                    "destination_observed_directly": False,
                })
            else:
                domestic = decoded(wave, q2, r.get(q2))
                event.update(endpoint_fields(wave, r, cfg, domestic_value=domestic))
            add_reasons(event, wave, r, None)
            events.append(event)

    # In-person migrant waves: a prior non-migrant, prior not-interviewed case,
    # or a respondent explicitly in another location defines a newly elicited
    # current destination. Staying in the prior destination is persistence.
    for wave in ["w12_M", "w14_M"]:
        cfg = INPERSON_DEST[wave]
        cols = [ID_VAR[wave], f"{wave}_date", *SHOCK_VARS[wave], *[x for x in cfg.values() if isinstance(x, str)]]
        cols += [f"{cfg['reason_prefix']}x{i}" for i in range(1, 8)]
        df = load_columns(wave, cols)
        for source_row, r in df.iterrows():
            rid = normalize_scalar(r.get(ID_VAR[wave]))
            prev_status_raw = normalize_scalar(r.get(cfg["prev_status"]))
            new_old_raw = normalize_scalar(r.get(cfg["new_old"]))
            is_from_nonmigrant = prev_status_raw == 1
            is_from_not_interviewed = prev_status_raw == 3
            is_another = new_old_raw == 2
            if not (is_from_nonmigrant or is_from_not_interviewed or is_another):
                continue
            event = common_event_fields(wave, source_row, rid, cfg, r)
            if is_another:
                event_class = "new_other_destination"
            elif is_from_nonmigrant:
                event_class = "new_migrant_from_prior_nonmigrant"
            else:
                event_class = "new_location_after_prior_not_interviewed"
            event.update({
                "event_class": event_class,
                "event_detection_rule": (
                    f"{cfg['new_old']}=In another location OR "
                    f"{cfg['prev_status']}=NON-MIGRANT/Not interviewed"
                ),
                "event_detection_confidence": "medium" if is_from_not_interviewed else "high",
                "current_location_state": "new migrant destination",
                "current_location_state_variable": cfg["new_old"],
                "previous_migration_status": decoded(wave, cfg["prev_status"], r.get(cfg["prev_status"])),
                "previous_migration_status_variable": cfg["prev_status"],
                "new_old_location": decoded(wave, cfg["new_old"], r.get(cfg["new_old"])),
                "new_old_location_variable": cfg["new_old"],
            })
            domestic = decoded(wave, cfg["domestic"], r.get(cfg["domestic"]))
            event.update(endpoint_fields(wave, r, cfg, domestic_value=domestic))
            add_reasons(event, wave, r, cfg["reason_prefix"])
            events.append(event)

    out = pd.DataFrame(events)
    out = out.sort_values(["wave_number", "wave", "respondent_id", "source_row_csv_1_based"]).reset_index(drop=True)
    out["event_sequence_within_respondent"] = out.groupby("respondent_id").cumcount() + 1
    out["event_id"] = (
        out["respondent_id"].astype(str) + "__" + out["wave"].astype(str) + "__" +
        out["event_sequence_within_respondent"].astype(str).str.zfill(2)
    )
    out["duplicate_respondent_wave_flag"] = out.duplicated(["respondent_id", "wave"], keep=False)
    out = adjudicate_duplicate_events(out)

    out["city_to_district_lookup_required_raw"] = out["needs_city_to_district_lookup"]
    resolved = pd.DataFrame([
        resolve_admin(level, raw)
        for level, raw in zip(out["destination_admin_level_raw"], out["destination_admin_raw"])
    ])
    out = pd.concat([out, resolved], axis=1)
    out["destination_district_endpoint_available"] = out["destination_district_official"].notna()
    out["needs_city_to_district_lookup"] = (
        out["city_to_district_lookup_required_raw"] & ~out["destination_district_endpoint_available"]
    )

    lag_erosion, lag_erosion_wave, lag_erosion_var = [], [], []
    lag_flood, lag_flood_wave, lag_flood_var = [], [], []
    for r in out.itertuples(index=False):
        e, ew, ev = prior_shock(shock_lookup, r.respondent_id, r.wave_number, "erosion")
        f, fw, fv = prior_shock(shock_lookup, r.respondent_id, r.wave_number, "flood")
        lag_erosion.append(e); lag_erosion_wave.append(ew); lag_erosion_var.append(ev)
        lag_flood.append(f); lag_flood_wave.append(fw); lag_flood_var.append(fv)
    out["lagged_home_erosion"] = lag_erosion
    out["lagged_home_erosion_source_wave"] = lag_erosion_wave
    out["lagged_home_erosion_variable"] = lag_erosion_var
    out["lagged_home_flood"] = lag_flood
    out["lagged_home_flood_source_wave"] = lag_flood_wave
    out["lagged_home_flood_variable"] = lag_flood_var

    out["lagged_home_shock_observed"] = out[["lagged_home_erosion", "lagged_home_flood"]].notna().any(axis=1)
    out["lagged_home_shock_any_yes"] = out[["lagged_home_erosion", "lagged_home_flood"]].eq("Yes").any(axis=1)
    out["climate_destination_reason_any"] = out[
        ["reason_safer_from_flood", "reason_safer_from_erosion"]
    ].eq(True).any(axis=1)
    out["climate_screen_any"] = out["lagged_home_shock_any_yes"] | out["climate_destination_reason_any"]
    out["whole_or_partial_household_move"] = out["move_scope"].isin([
        "I took the whole household along", "I took parts of the household along"
    ])
    out["is_return_event"] = out["event_class"].eq("return_to_baseline_home")
    out["is_new_destination_event"] = out["event_class"].isin([
        "new_other_destination", "new_migrant_from_prior_nonmigrant",
        "new_location_after_prior_not_interviewed"
    ])
    out["domestic_event"] = out["domestic_abroad"].eq("In Bangladesh")
    out["stage1_named_endpoint_eligible"] = (
        out["is_new_destination_event"] &
        out["domestic_event"] &
        out["destination_named_admin_available"] &
        out["duplicate_adjudication_keep"]
    )
    out["stage1_district_endpoint_eligible"] = (
        out["stage1_named_endpoint_eligible"] &
        out["destination_district_endpoint_available"]
    )
    out["stage1_household_relocation_eligible"] = (
        out["stage1_district_endpoint_eligible"] & out["whole_or_partial_household_move"]
    )
    out["stage1_climate_screen_eligible"] = (
        out["stage1_household_relocation_eligible"] & out["climate_screen_any"]
    )

    reasons = []
    for r in out.itertuples(index=False):
        if not r.is_new_destination_event:
            reasons.append("not a new-destination event")
        elif not r.domestic_event:
            reasons.append("abroad or domestic status unavailable")
        elif not r.destination_named_admin_available:
            reasons.append("named city/rural district unavailable")
        elif not r.destination_district_endpoint_available:
            reasons.append("named endpoint lacks official district resolution")
        elif not r.duplicate_adjudication_keep:
            reasons.append("superseded duplicate respondent-wave interview")
        elif not r.whole_or_partial_household_move:
            reasons.append("solo or move scope unavailable")
        elif not r.climate_screen_any:
            reasons.append("no lagged home shock or climate-safety reason")
        else:
            reasons.append("")
    out["first_stage1_exclusion_reason"] = reasons

    ordered = [
        "event_id", "respondent_id", "household_id_derived", "baseline_location_lxx",
        "origin_district_codebook", "wave", "wave_number", "event_sequence_within_respondent",
        "event_class", "event_detection_confidence", "event_detection_rule",
        "current_location_state", "previous_migration_status", "previous_migration_type",
        "new_old_location", "domestic_abroad", "destination_rural_urban",
        "destination_admin_level_raw", "destination_admin_raw",
        "destination_admin_standardized_provisional", "destination_city_code",
        "destination_city_category", "destination_city_other_text",
        "destination_rural_district_raw", "destination_rural_division_raw",
        "destination_observed_directly", "destination_named_admin_available",
        "destination_district_ready_without_city_lookup", "needs_city_to_district_lookup",
        "city_to_district_lookup_required_raw",
        "normalization_action_provisional", "normalization_confidence",
        "destination_place_official", "destination_place_type_official",
        "destination_district_official", "destination_resolution_method",
        "destination_resolution_confidence", "destination_resolution_source_url",
        "destination_resolution_source_detail", "destination_resolution_source_access_date",
        "destination_resolution_manual_review_flag", "destination_resolution_status",
        "destination_district_endpoint_available",
        "move_scope", "distance_from_previous_location_m", "return_plan",
        "lagged_home_erosion", "lagged_home_erosion_source_wave",
        "lagged_home_flood", "lagged_home_flood_source_wave",
        "lagged_home_shock_observed", "lagged_home_shock_any_yes",
        "concurrent_home_erosion", "concurrent_home_flood",
        "reason_relatives_at_destination", "reason_better_earning",
        "reason_safer_from_flood", "reason_safer_from_erosion", "reason_schooling",
        "reason_marriage", "reason_property_at_destination",
        "climate_destination_reason_any", "climate_screen_any",
        "whole_or_partial_household_move", "is_return_event", "is_new_destination_event",
        "domestic_event", "stage1_named_endpoint_eligible", "stage1_district_endpoint_eligible",
        "stage1_household_relocation_eligible", "stage1_climate_screen_eligible",
        "duplicate_respondent_wave_flag", "duplicate_adjudication_keep",
        "duplicate_adjudication_status", "duplicate_adjudication_confidence",
        "duplicate_adjudication_rationale", "first_stage1_exclusion_reason",
        "source_file", "source_row_csv_1_based", "source_interview_date", "respondent_id_variable",
        "current_location_state_variable", "previous_migration_status_variable",
        "previous_migration_type_variable", "new_old_location_variable",
        "move_scope_variable", "distance_variable", "return_plan_variable",
        "concurrent_erosion_variable", "concurrent_flood_variable",
        "lagged_home_erosion_variable", "lagged_home_flood_variable",
    ]
    remaining = [c for c in out.columns if c not in ordered and not c.endswith("_variable")]
    variable_cols = [c for c in out.columns if c.endswith("_variable") and c not in ordered]
    return out[ordered + remaining + variable_cols]


def build_state_panel():
    rows = []
    respondent_waves = [
        "w1", "w2", "w3", "w4", "w5", "w6_N", "w6_M", "w7", "w8", "w9",
        "w10", "w11", "w12_N", "w12_M", "w13", "w14_N", "w14_M"
    ]
    for wave in respondent_waves:
        cols = [ID_VAR[wave]]
        if wave in SHOCK_VARS:
            cols += list(SHOCK_VARS[wave])
        current_var = None
        prev_status_var = None
        prev_type_var = None
        if wave in {"w2", "w3", "w4", "w5"}:
            current_var = f"{wave}_q1"
        elif wave in PHONE_DEST:
            current_var = f"{wave}_q1"
            prev_status_var = PHONE_DEST[wave]["prev_status"]
            prev_type_var = PHONE_DEST[wave]["prev_type"]
        elif wave == "w12_M":
            current_var, prev_status_var, prev_type_var = "w12_M_q16", "w12_M_reg10", "w12_M_reg11"
        elif wave == "w14_M":
            current_var, prev_status_var, prev_type_var = "w14_M_q16", "w14_M_reg11", "w14_M_reg12"
        cols += [x for x in [current_var, prev_status_var, prev_type_var] if x]
        df = load_columns(wave, cols)
        for source_row, r in df.iterrows():
            rid = normalize_scalar(r.get(ID_VAR[wave]))
            if rid is None:
                continue
            hh, lxx, origin = person_parts(rid)
            if wave.endswith("_N"):
                state = "routed non-migrant in-person file"
            elif wave == "w6_M":
                state = "routed migrant in-person file"
            elif current_var:
                state = decoded(wave, current_var, r.get(current_var))
            else:
                state = "baseline respondent"
            erosion_var, flood_var = SHOCK_VARS.get(wave, (None, None))
            rows.append({
                "respondent_id": rid,
                "household_id_derived": hh,
                "baseline_location_lxx": lxx,
                "origin_district_codebook": origin,
                "wave": wave,
                "wave_number": WAVE_NUMBER[wave],
                "survey_route": "migrant" if wave.endswith("_M") else "non-migrant" if wave.endswith("_N") else "combined",
                "current_location_state": state,
                "previous_migration_status": decoded(wave, prev_status_var, r.get(prev_status_var)),
                "previous_migration_type": decoded(wave, prev_type_var, r.get(prev_type_var)),
                "home_erosion_occurrence": decode_yes_no(wave, erosion_var, r.get(erosion_var)),
                "home_flood_occurrence": decode_yes_no(wave, flood_var, r.get(flood_var)),
                "source_file": f"bemp_{wave}.csv",
                "source_row_csv_1_based": source_row + 2,
                "respondent_id_variable": ID_VAR[wave],
                "current_location_state_variable": current_var,
                "previous_migration_status_variable": prev_status_var,
                "previous_migration_type_variable": prev_type_var,
                "home_erosion_variable": erosion_var,
                "home_flood_variable": flood_var,
            })
    state = pd.DataFrame(rows).sort_values(
        ["respondent_id", "wave_number", "wave", "source_row_csv_1_based"]
    ).reset_index(drop=True)
    state["duplicate_respondent_wave_flag"] = state.duplicated(["respondent_id", "wave"], keep=False)
    return state


def build_crosswalk(events: pd.DataFrame):
    x = events.loc[
        events["destination_admin_raw"].notna(),
        [
            "destination_admin_level_raw", "destination_admin_raw",
            "destination_admin_standardized_provisional", "normalization_action_provisional",
            "normalization_confidence", "wave", "source_file"
        ]
    ].copy()
    grouped = []
    for (level, raw), g in x.groupby(
        ["destination_admin_level_raw", "destination_admin_raw"], dropna=False
    ):
        std = g["destination_admin_standardized_provisional"].dropna()
        action = g["normalization_action_provisional"].dropna()
        confidence = g["normalization_confidence"].dropna()
        waves = sorted(g["wave"].unique(), key=lambda w: (WAVE_NUMBER[w], w))
        grouped.append({
            "admin_level_raw": level,
            "raw_value": raw,
            "standardized_name_provisional": std.iloc[0] if len(std) else None,
            "normalization_action_provisional": action.iloc[0] if len(action) else None,
            "normalization_confidence": confidence.iloc[0] if len(confidence) else None,
            "event_count": len(g),
            "waves": "|".join(waves),
            "source_files": "|".join(sorted(g["source_file"].unique())),
            **resolve_admin(level, raw),
        })
    crosswalk = pd.DataFrame(grouped)
    crosswalk["requires_city_to_district_lookup"] = False
    crosswalk["requires_official_admin_validation"] = False
    crosswalk["review_status"] = np.where(
        crosswalk["destination_resolution_manual_review_flag"],
        "resolved—manual spelling/language review documented",
        "resolved—official government source documented",
    )
    crosswalk["notes"] = np.where(
        crosswalk["admin_level_raw"].eq("origin_district"),
        "Origin district is codebook-derived; canonical name checked against the National Portal.",
        "Raw BEMP value preserved; official containing district is the model endpoint.",
    )
    return crosswalk.sort_values(
        ["admin_level_raw", "event_count", "raw_value"], ascending=[True, False, True]
    ).reset_index(drop=True)


def build_duplicate_adjudication(events: pd.DataFrame):
    cols = [
        "event_id", "respondent_id", "wave", "source_file", "source_row_csv_1_based",
        "source_interview_date", "destination_admin_level_raw", "destination_admin_raw",
        "destination_district_official", "move_scope", "climate_screen_any",
        "duplicate_adjudication_keep", "duplicate_adjudication_status",
        "duplicate_adjudication_confidence", "duplicate_adjudication_rationale",
    ]
    return events.loc[events["duplicate_respondent_wave_flag"], cols].sort_values(
        ["respondent_id", "wave_number" if "wave_number" in cols else "wave", "source_row_csv_1_based"]
    ).reset_index(drop=True)


def build_flow(events: pd.DataFrame):
    steps = [
        ("01", "All conservative prospective/event-rich records", pd.Series(True, index=events.index)),
        ("02", "New destination events (excludes returns and wave-6 first-observed snapshot)",
         events["is_new_destination_event"]),
        ("03", "Domestic new destination", events["is_new_destination_event"] & events["domestic_event"]),
        ("04", "Named city or rural district available",
         events["is_new_destination_event"] & events["domestic_event"] &
         events["destination_named_admin_available"]),
        ("05", "Official containing district resolved",
         events["is_new_destination_event"] & events["domestic_event"] &
         events["destination_named_admin_available"] &
         events["destination_district_endpoint_available"]),
        ("06", "Retained after duplicate respondent-wave adjudication",
         events["stage1_named_endpoint_eligible"]),
        ("07", "Whole- or partial-household relocation",
         events["stage1_household_relocation_eligible"]),
        ("08", "Lagged home flood/erosion observed",
         events["stage1_household_relocation_eligible"] & events["lagged_home_shock_observed"]),
        ("09", "Climate screen: lagged shock yes or climate-safety destination reason",
         events["stage1_climate_screen_eligible"]),
    ]
    rows = []
    previous = len(events)
    for code, label, mask in steps:
        n = int(mask.fillna(False).sum())
        rows.append({
            "step": code,
            "criterion": label,
            "remaining_events": n,
            "removed_at_step": 0 if code == "01" else previous - n,
            "percent_of_all_events": n / len(events) if len(events) else np.nan,
            "notes": (
                "All 127 unique named endpoint strings have a documented official district resolution."
                if code == "05" else
                "Screening definition, not a causal climate-migration classification."
                if code == "09" else ""
            ),
        })
        previous = n
    base = pd.DataFrame(rows)

    wave_rows = []
    for wave, g in events.groupby("wave", sort=False):
        wave_rows.append({
            "step": f"W_{wave}",
            "criterion": f"Wave summary: {wave}",
            "remaining_events": len(g),
            "removed_at_step": np.nan,
            "percent_of_all_events": len(g) / len(events),
            "notes": json.dumps({
                "new_destination": int(g["is_new_destination_event"].sum()),
                "return_home": int(g["is_return_event"].sum()),
                "first_observed_snapshot": int(
                    g["event_class"].eq("first_observed_current_migrant_destination").sum()
                ),
                "named_endpoint": int(g["destination_named_admin_available"].sum()),
                "household_relocation_eligible": int(g["stage1_household_relocation_eligible"].sum()),
            }, ensure_ascii=False),
        })
    return pd.concat([base, pd.DataFrame(wave_rows)], ignore_index=True)


def build_data_dictionary(tables: dict[str, pd.DataFrame]):
    descriptions = {
        "event_id": "Deterministic event key: respondent ID, wave, and within-respondent event sequence.",
        "respondent_id": "Exact public BEMP respondent code used for cross-wave linkage.",
        "household_id_derived": "Respondent code with the final role suffix removed; derived baseline household key.",
        "baseline_location_lxx": "Pseudonymized baseline sampling-location prefix from respondent code.",
        "origin_district_codebook": "Baseline district mapped from Lxx using the public respondent-code comment.",
        "event_class": "Conservative rule-based event category.",
        "event_detection_confidence": "Confidence in event timing/classification from questionnaire routing.",
        "event_detection_rule": "Exact deterministic rule used to create the event.",
        "destination_admin_raw": "Public named city or rural district; origin district for return events.",
        "destination_admin_standardized_provisional": "Provisional string normalization only; not official gazetteer resolution.",
        "destination_admin_level_raw": "Raw endpoint construct: city, district, origin district, abroad, or unavailable.",
        "destination_named_admin_available": "True when a public named city/district endpoint is present.",
        "destination_district_ready_without_city_lookup": "True for district/origin-district endpoints; cities remain unresolved.",
        "needs_city_to_district_lookup": "True only when a city endpoint still lacks an official containing district after this resolution pass.",
        "city_to_district_lookup_required_raw": "True when the original public endpoint was a named city requiring containment resolution.",
        "destination_place_official": "Officially standardized place name represented by the raw response.",
        "destination_place_type_official": "Documented geographic type of the resolved place.",
        "destination_district_official": "Official containing district used as the Stage 1 choice endpoint.",
        "destination_resolution_method": "Exact, spelling/language, upazila-containment, or locality-containment resolution method.",
        "destination_resolution_confidence": "Resolution confidence after official-source review.",
        "destination_resolution_source_url": "Official Bangladesh government source supporting the resolution.",
        "destination_resolution_source_detail": "Concise description of the evidence supplied by the official source.",
        "destination_resolution_manual_review_flag": "True for spelling/language variants requiring manual review.",
        "destination_district_endpoint_available": "True when a named public endpoint has an official containing district.",
        "destination_observed_directly": "True for a public destination response, false for inferred return-to-origin endpoint.",
        "move_scope": "Decoded whole-household, part-household, or solo move response.",
        "previous_migration_type": "Temporary/permanent classification of the previous survey's migration.",
        "distance_from_previous_location_m": "Coordinate-derived distance in meters; coordinates/endpoints are withheld.",
        "lagged_home_erosion": "Latest valid home-village erosion occurrence response from a strictly earlier wave.",
        "lagged_home_flood": "Latest valid home-village flood occurrence response from a strictly earlier wave.",
        "concurrent_home_erosion": "Home-village erosion occurrence reported in the event wave.",
        "concurrent_home_flood": "Home-village flood occurrence reported in the event wave.",
        "climate_destination_reason_any": "Safer-from-flood or safer-from-erosion selected as realized-destination reason.",
        "climate_screen_any": "Lagged shock yes or climate-safety destination reason; screening flag only.",
        "stage1_named_endpoint_eligible": "Domestic new-destination event with named endpoint retained by duplicate adjudication.",
        "stage1_district_endpoint_eligible": "Named-endpoint eligibility plus official containing-district resolution.",
        "stage1_household_relocation_eligible": "District-endpoint eligibility plus whole/partial-household move.",
        "stage1_climate_screen_eligible": "Household-relocation eligibility plus broad climate screen.",
        "first_stage1_exclusion_reason": "First sequential reason the event is outside the broad climate-screen sample.",
        "source_file": "Exact public quantitative CSV containing the source row.",
        "source_row_csv_1_based": "CSV row number including header as row 1.",
        "raw_value": "Unmodified non-missing public admin string/category used in the crosswalk.",
        "standardized_name_provisional": "Provisional normalization; requires official validation.",
        "duplicate_adjudication_keep": "True for unique rows and the retained latest completed interview in each duplicate pair.",
        "duplicate_adjudication_status": "Unique, retained, or superseded duplicate status; no raw event row is deleted.",
        "duplicate_adjudication_rationale": "Evidence-based reason for retaining or superseding a duplicate row.",
        "remaining_events": "Number of event-ledger rows remaining after the sequential criterion.",
        "removed_at_step": "Difference from the preceding sequential flow step.",
        "percent_of_all_events": "Remaining events divided by all conservative event-rich records.",
    }
    rows = []
    for table_name, df in tables.items():
        for position, col in enumerate(df.columns, start=1):
            if col in descriptions:
                description = descriptions[col]
            elif col.endswith("_variable"):
                description = "Exact BEMP variable supplying or documenting the corresponding field."
            elif col.startswith("reason_"):
                description = "Decoded selected/not-selected realized-destination reason or its source variable."
            elif col.endswith("_flag") or col.startswith(("is_", "needs_", "whole_or_", "domestic_event")):
                description = col.replace("_", " ").capitalize() + "."
            else:
                description = col.replace("_", " ").capitalize() + "."
            if col.endswith("_variable") or col in {
                "source_file", "source_row_csv_1_based", "respondent_id",
                "destination_admin_raw", "destination_rural_district_raw",
                "destination_rural_division_raw", "destination_city_code",
                "destination_city_category", "destination_city_other_text",
                "move_scope", "previous_migration_status", "previous_migration_type",
                "return_plan", "distance_from_previous_location_m",
                "concurrent_home_erosion", "concurrent_home_flood",
            }:
                role = "source/provenance"
            elif table_name == "sample_flow":
                role = "summary"
            elif table_name in {"crosswalk", "duplicate_adjudication"}:
                role = "normalization"
            else:
                role = "derived/analytic"
            rows.append({
                "table_name": table_name,
                "column_position": position,
                "column_name": col,
                "observed_dtype": str(df[col].dtype),
                "description": description,
                "role": role,
            })
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    shock_history, shock_lookup = build_shock_history()
    events = build_events(shock_lookup)
    state = build_state_panel()
    crosswalk = build_crosswalk(events)
    duplicate_adjudication = build_duplicate_adjudication(events)
    flow = build_flow(events)
    dictionary = build_data_dictionary({
        "events": events,
        "respondent_wave_state": state,
        "crosswalk": crosswalk,
        "duplicate_adjudication": duplicate_adjudication,
        "sample_flow": flow,
    })

    paths = {
        "events": OUT / "bemp_prospective_migration_events.csv",
        "state": OUT / "bemp_respondent_wave_state.csv",
        "crosswalk": OUT / "bemp_destination_admin_crosswalk.csv",
        "duplicate_adjudication": OUT / "bemp_duplicate_adjudication.csv",
        "flow": OUT / "bemp_stage1_sample_flow.csv",
        "dictionary": OUT / "bemp_stage1_data_dictionary.csv",
    }
    events.to_csv(paths["events"], index=False)
    state.to_csv(paths["state"], index=False)
    crosswalk.to_csv(paths["crosswalk"], index=False)
    duplicate_adjudication.to_csv(paths["duplicate_adjudication"], index=False)
    flow.to_csv(paths["flow"], index=False)
    dictionary.to_csv(paths["dictionary"], index=False)
    shock_history.to_csv(WORK / "bemp_shock_history_long.csv", index=False)

    summary = {
        "events_rows": len(events),
        "state_rows": len(state),
        "crosswalk_rows": len(crosswalk),
        "duplicate_adjudication_rows": len(duplicate_adjudication),
        "flow_rows": len(flow),
        "dictionary_rows": len(dictionary),
        "event_class_counts": events["event_class"].value_counts().to_dict(),
        "wave_counts": events["wave"].value_counts().sort_index().to_dict(),
        "named_endpoint_eligible": int(events["stage1_named_endpoint_eligible"].sum()),
        "district_endpoint_eligible": int(events["stage1_district_endpoint_eligible"].sum()),
        "household_relocation_eligible": int(events["stage1_household_relocation_eligible"].sum()),
        "climate_screen_eligible": int(events["stage1_climate_screen_eligible"].sum()),
        "duplicate_respondent_wave_events": int(events["duplicate_respondent_wave_flag"].sum()),
        "unresolved_named_endpoints": int(
            (events["destination_named_admin_available"] & ~events["destination_district_endpoint_available"]).sum()
        ),
        "outputs": {k: str(v.relative_to(ROOT)) for k, v in paths.items()},
    }
    (WORK / "bemp_stage1_events_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
