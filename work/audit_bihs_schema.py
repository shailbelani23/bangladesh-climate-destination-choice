from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ("w1_a", ROOT / "data/raw/bihs/wave1_2011_12/001_mod_a_male.dta"),
    ("w1_b1", ROOT / "data/raw/bihs/wave1_2011_12/003_mod_b1_male.dta"),
    ("w1_t1", ROOT / "data/raw/bihs/wave1_2011_12/038_mod_t1_male.dta"),
    ("w1_v1", ROOT / "data/raw/bihs/wave1_2011_12/041_mod_v1_male.dta"),
    ("w2_a", ROOT / "data/raw/bihs/wave2_2015/001_r2_mod_a_male.dta"),
    ("w2_b1", ROOT / "data/raw/bihs/wave2_2015/003_r2_male_mod_b1.dta"),
    ("w2_b4", ROOT / "data/raw/bihs/wave2_2015/007_r2_mod_b4_male.dta"),
    ("w2_t1", ROOT / "data/raw/bihs/wave2_2015/050_r2_mod_t1_male.dta"),
    ("w2_v1", ROOT / "data/raw/bihs/wave2_2015/053_r2_mod_v1_male.dta"),
    ("w3_a", ROOT / "data/raw/bihs/wave3_2018_19/009_bihs_r3_male_mod_a.dta"),
    ("w3_b1", ROOT / "data/raw/bihs/wave3_2018_19/010_bihs_r3_male_mod_b1.dta"),
    ("w3_t1b", ROOT / "data/raw/bihs/wave3_2018_19/067_bihs_r3_male_mod_t1b.dta"),
    ("w3_t1c", ROOT / "data/raw/bihs/wave3_2018_19/068_bihs_r3_male_mod_t1c.dta"),
    ("w3_v1", ROOT / "data/raw/bihs/wave3_2018_19/072_bihs_r3_male_mod_v1.dta"),
]

KEYWORDS = (
    "district", "zila", "upazila", "village", "union", "migrat", "move", "relocat",
    "destination", "origin", "year", "month", "shock", "flood", "erosion", "river",
    "disaster", "drought", "cyclone", "return", "temporary", "permanent", "family",
    "friend", "help", "purpose", "reason", "member", "household", "split", "baseline",
)

out = {}
for tag, path in FILES:
    reader = pd.io.stata.StataReader(path)
    labels = reader.variable_labels()
    value_labels = reader.value_labels()
    df = pd.read_stata(path, convert_categoricals=False)
    variables = []
    for col in df.columns:
        label = labels.get(col, "") or ""
        if any(k in (col + " " + label).lower() for k in KEYWORDS) or col.lower() in {
            "a01", "a02", "a03", "a04", "a05", "a06", "a07", "a08", "hhid", "pid", "mid"
        }:
            s = df[col]
            examples = [None if pd.isna(x) else x for x in s.dropna().drop_duplicates().head(12).tolist()]
            variables.append({
                "name": col,
                "label": label,
                "dtype": str(s.dtype),
                "missing_pct": round(float(s.isna().mean() * 100), 3),
                "n_unique": int(s.nunique(dropna=True)),
                "examples": examples,
            })
    out[tag] = {
        "file": str(path.relative_to(ROOT)),
        "rows": len(df),
        "columns": len(df.columns),
        "all_columns": list(df.columns),
        "candidate_variables": variables,
        "value_labels": {
            str(label_set): {str(code): text for code, text in mapping.items()}
            for label_set, mapping in value_labels.items()
        },
    }

dest = ROOT / "work/bihs_schema_audit.json"
dest.write_text(json.dumps(out, indent=2, default=str))
print(dest)
for tag, info in out.items():
    print(f"{tag}: {info['rows']} rows x {info['columns']} cols; candidates={len(info['candidate_variables'])}")
