from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CODEBOOK_DIR = ROOT / "data" / "raw" / "bemp" / "codebooks"
VARIABLE_LIST = ROOT / "data" / "raw" / "bemp" / "metadata" / "bemp_variable_list_full.xlsx"

SEARCH_FIELDS = [
    "Variable name",
    "Variable label",
    "Block",
    "Question",
    "Question text",
    "Item text",
    "Comment",
]

PATTERNS = {
    "coordinates_location": [
        r"\blatitude\b", r"\blongitude\b", r"\blat\b", r"\blon\b", r"\blng\b",
        r"\bgps\b", r"\bcoordinates?\b", r"\bgeograph(?:y|ic|ical)\b", r"\bgeocode\w*\b",
        r"\blocation\b", r"\blocated\b",
    ],
    "admin_place": [
        r"\bvillage\b", r"\bunion\b", r"\bupazila\b", r"\bdistrict\b", r"\bthana\b",
        r"\bward\b", r"\bsettlement\b", r"\btown\b", r"\bcity\b",
    ],
    "origin_destination_residence": [
        r"\borigin\b", r"\bdestination\b", r"\bresiden(?:ce|t|tial)\b", r"\bcurrent residence\b",
        r"\bprevious residence\b", r"\bhometown\b", r"\bplace of (?:birth|residence|origin)\b",
    ],
    "migration_mobility": [
        r"\bmigrat\w*\b", r"\bmoved?\b", r"\bmoving\b", r"\brelocat\w*\b",
        r"\bdisplac\w*\b", r"\bdistance\b", r"\breturn(?:ed|ing|s)?\b",
        r"\btemporary\b", r"\bpermanent(?:ly)?\b", r"\bmobility\b",
    ],
    "hazards_shocks": [
        r"\bflood\w*\b", r"\berosion\b", r"\briver(?:bank)?\b", r"\bhazard\b",
        r"\bshock\b", r"\bcyclone\b", r"\bsalinity\b", r"\bdrought\b", r"\bheat\b",
        r"\brainfall\b", r"\bdisaster\b", r"\binundat\w*\b",
    ],
    "social_networks": [
        r"\brelatives?\b", r"\bfamily\b", r"\bfriends?\b", r"\bnetwork\b",
        r"\bcontacts?\b", r"\bknown person\b", r"\bacquaintance\b", r"\bsocial ties?\b",
    ],
    "housing_land": [
        r"\bhous(?:e|es|ing)\b", r"\bdwelling\b", r"\bland\b", r"\bplots?\b",
        r"\brent(?:ed|ing|s)?\b", r"\btenure\b", r"\bownership\b", r"\bshelter\b",
    ],
    "livelihood_opportunity": [
        r"\boccupation\b", r"\bemploy(?:ment|ed|er|ee)\b", r"\bjobs?\b", r"\bwages?\b",
        r"\bincome\b", r"\bagricultur\w*\b", r"\bfarm(?:ing|er|ers)?\b", r"\bbusiness\b",
    ],
    "access_services": [
        r"\broads?\b", r"\btransport\w*\b", r"\btravel\w*\b", r"\bmarkets?\b",
        r"\bschools?\b", r"\bhealth facilit(?:y|ies)\b", r"\bhospitals?\b", r"\bclinics?\b",
        r"\belectricity\b", r"\bwater\b", r"\bsanitation\b",
    ],
}

COMPILED = {group: [re.compile(pattern, re.I) for pattern in patterns] for group, patterns in PATTERNS.items()}


def wave_from_name(path: Path) -> str:
    match = re.search(r"bemp_(w\d+(?:_[MNV])?)", path.stem)
    return match.group(1) if match else ""


frames = []
for path in sorted(CODEBOOK_DIR.glob("*_codebook.csv")):
    frame = pd.read_csv(path, dtype=str, usecols=SEARCH_FIELDS, keep_default_na=False)
    frame.insert(0, "wave", wave_from_name(path))
    frame.insert(0, "codebook_file", path.name)
    frames.append(frame)

codebooks = pd.concat(frames, ignore_index=True)
codebooks["search_text"] = codebooks[SEARCH_FIELDS].agg(" | ".join, axis=1)

matches = []
for _, row in codebooks.iterrows():
    text = row["search_text"]
    for group, patterns in COMPILED.items():
        hits = sorted({pattern.pattern for pattern in patterns if pattern.search(text)})
        if hits:
            matches.append(
                {
                    "category": group,
                    "wave": row["wave"],
                    "codebook_file": row["codebook_file"],
                    "variable_name": row["Variable name"],
                    "variable_label": row["Variable label"],
                    "block": row["Block"],
                    "question": row["Question"],
                    "question_text": row["Question text"],
                    "item_text": row["Item text"],
                    "comment": row["Comment"],
                    "matched_patterns": "; ".join(hits),
                }
            )

matches_df = pd.DataFrame(matches).sort_values(["category", "wave", "variable_name"])
matches_df.to_csv(ROOT / "work" / "bemp_codebook_keyword_matches.csv", index=False)

variable_list = pd.read_excel(VARIABLE_LIST, sheet_name="Variable list", dtype=str).fillna("")
variable_list["search_text"] = variable_list[["variable_title", "variable_label"]].agg(" | ".join, axis=1)
vl_matches = []
for _, row in variable_list.iterrows():
    text = row["search_text"]
    for group, patterns in COMPILED.items():
        hits = sorted({pattern.pattern for pattern in patterns if pattern.search(text)})
        if hits:
            vl_matches.append(
                {
                    "category": group,
                    "variable_title": row["variable_title"],
                    "variable_label": row["variable_label"],
                    "appears_in": row["appears_in"],
                    "matched_patterns": "; ".join(hits),
                }
            )

vl_matches_df = pd.DataFrame(vl_matches).sort_values(["category", "variable_title", "variable_label"])
vl_matches_df.to_csv(ROOT / "work" / "bemp_variable_list_keyword_matches.csv", index=False)

summary = {
    "codebook_matches_by_category": matches_df.groupby("category").size().to_dict(),
    "codebook_unique_variables_by_category": matches_df.groupby("category")["variable_name"].nunique().to_dict(),
    "variable_list_matches_by_category": vl_matches_df.groupby("category").size().to_dict(),
    "codebook_matches_by_wave_category": matches_df.groupby(["wave", "category"]).size().unstack(fill_value=0).to_dict(orient="index"),
}
(ROOT / "work" / "bemp_keyword_search_summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(summary, indent=2, ensure_ascii=False))
