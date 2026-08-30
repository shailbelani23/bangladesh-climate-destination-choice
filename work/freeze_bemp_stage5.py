#!/usr/bin/env python3
"""Write the final Stage-5 artifact checksum manifest."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"

artifacts = sorted(
    p for p in TABLES.glob("bemp_stage5_*.csv")
    if p.name != "bemp_stage5_freeze_manifest.csv"
)
artifacts += [
    ROOT / "outputs" / "reports" / "bemp_stage5_gis_model_results.md",
    ROOT / "outputs" / "figures" / "bemp_stage5_validation_logloss.png",
    ROOT / "outputs" / "figures" / "bemp_stage5_climate_gis_coefficients.png",
    ROOT / "outputs" / "bemp_stage5_research_results.xlsx",
    ROOT / "work" / "fit_bemp_stage5_gis_models.py",
    ROOT / "work" / "bootstrap_stage5_parameters.py",
    ROOT / "work" / "validate_bemp_stage5.py",
    ROOT / "work" / "build_bemp_stage5_figures.py",
    ROOT / "work" / "build_bemp_stage5_workbook.mjs",
    ROOT / "work" / "verify_bemp_stage5_workbook.mjs",
]

rows = []
for path in artifacts:
    if not path.exists():
        raise FileNotFoundError(path)
    row_count = ""
    column_count = ""
    if path.suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            column_count = len(header)
            row_count = sum(1 for _ in reader)
    rows.append(
        {
            "relative_path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": row_count,
            "columns": column_count,
            "frozen_at": "2026-08-29",
            "freeze_scope": "final Stage-5 GIS destination-choice analysis",
        }
    )

out = TABLES / "bemp_stage5_freeze_manifest.csv"
with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(out)
print(f"artifacts={len(rows)}")
