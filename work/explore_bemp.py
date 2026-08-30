from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "bemp" / "quantitative"
CODEBOOK_DIR = ROOT / "data" / "raw" / "bemp" / "codebooks"
VARIABLE_LIST = ROOT / "data" / "raw" / "bemp" / "metadata" / "bemp_variable_list_full.xlsx"


def csv_dimensions(path: Path) -> tuple[int, int, list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = sum(1 for _ in reader)
    return rows, len(header), header


def wave_from_name(path: Path) -> str:
    match = re.search(r"bemp_(w\d+(?:_[MNV])?)", path.stem)
    return match.group(1) if match else ""


data_summary = []
for path in sorted(DATA_DIR.glob("*.csv")):
    rows, columns, header = csv_dimensions(path)
    data_summary.append(
        {
            "file": path.name,
            "wave": wave_from_name(path),
            "rows": rows,
            "columns": columns,
            "first_columns": header[:20],
        }
    )

codebook_summary = []
for path in sorted(CODEBOOK_DIR.glob("*_codebook.csv")):
    rows, columns, header = csv_dimensions(path)
    codebook_summary.append(
        {
            "file": path.name,
            "wave": wave_from_name(path),
            "rows": rows,
            "columns": columns,
            "first_columns": header[:20],
        }
    )

variable_list = pd.read_excel(VARIABLE_LIST, sheet_name="Variable list", dtype=str)

result = {
    "data": data_summary,
    "codebooks": codebook_summary,
    "variable_list": {
        "rows": len(variable_list),
        "columns": len(variable_list.columns),
        "headers": variable_list.columns.tolist(),
        "first_rows": variable_list.head(3).fillna("").to_dict(orient="records"),
    },
}

out = ROOT / "work" / "bemp_schema_overview.json"
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
