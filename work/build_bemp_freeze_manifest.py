from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MANIFEST = OUT / "tables" / "bemp_stage1_freeze_manifest.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_shape(path: Path):
    frame = pd.read_csv(path, low_memory=False)
    return len(frame), len(frame.columns)


def main():
    files = sorted((OUT / "tables").glob("bemp_*.csv")) + sorted((OUT / "reports").glob("bemp_*.md"))
    files = [path for path in files if path != MANIFEST]
    records = []
    for path in files:
        rows, columns = csv_shape(path) if path.suffix == ".csv" else (None, None)
        records.append({
            "relative_path": str(path.relative_to(ROOT)),
            "file_type": path.suffix.lstrip("."),
            "rows": rows,
            "columns": columns,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "freeze_date": "2026-08-28",
            "freeze_scope": "BEMP-only pre-model audit and Stage 1 data engineering; no GIS or model outputs",
        })
    pd.DataFrame(records).to_csv(MANIFEST, index=False)
    print({"manifest_rows": len(records), "path": str(MANIFEST.relative_to(ROOT))})


if __name__ == "__main__":
    main()
