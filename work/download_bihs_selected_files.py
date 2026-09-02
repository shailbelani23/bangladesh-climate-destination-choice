#!/usr/bin/env python3
"""Download only the BIHS modules required for migration-destination feasibility."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bihs"
GUESTBOOK_EMAIL = os.environ["BIHS_GUESTBOOK_EMAIL"]
GUESTBOOK_INSTITUTION = os.environ.get("BIHS_GUESTBOOK_INSTITUTION", "Northwestern University")
GUESTBOOK_POSITION = os.environ.get(
    "BIHS_GUESTBOOK_POSITION", "Undergraduate Researcher, Northwestern University"
)

selection = {
    "w1": {
        "dir": "wave1_2011_12",
        "ids": [2435038, 2434897, 2434899, 2434922, 2434935, 4367339],
    },
    "w2": {
        "dir": "wave2_2015",
        "ids": [2962555, 3350843, 3349623, 3349624, 2962400, 2962442, 2962445, 4367423],
    },
    "w3": {
        "dir": "wave3_2018_19",
        "ids": [4098413, 4097604, 4098392, 4098252, 4097591, 4097517, 4097535, 4097519, 4367284],
    },
}

rows = []
for wave, cfg in selection.items():
    meta_path = RAW / "metadata" / f"{wave}_dataverse.json"
    dataset = json.loads(meta_path.read_text(encoding="utf-8"))["data"]
    version = dataset["latestVersion"]
    by_id = {f["dataFile"]["id"]: f for f in version["files"]}
    out_dir = RAW / cfg["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for file_id in cfg["ids"]:
        f = by_id[file_id]
        df = f["dataFile"]
        label = f["label"]
        is_ingested_tabular = bool(df.get("tabularData") and df.get("originalFileName"))
        download_name = df["originalFileName"] if is_ingested_tabular else label
        expected_bytes = (
            df.get("originalFileSize", df["filesize"])
            if is_ingested_tabular
            else df["filesize"]
        )
        target = out_dir / download_name
        url = f"https://dataverse.harvard.edu/api/access/datafile/{file_id}"
        download_url = f"{url}?format=original" if is_ingested_tabular else url
        if not target.exists() or target.stat().st_size != expected_bytes:
            guestbook = json.dumps(
                {
                    "guestbookResponse": {
                        "email": GUESTBOOK_EMAIL,
                        "institution": GUESTBOOK_INSTITUTION,
                        "position": GUESTBOOK_POSITION,
                        "answers": [],
                    }
                }
            ).encode("utf-8")
            signed_req = urllib.request.Request(
                f"{download_url}{'&' if '?' in download_url else '?'}signed=true",
                data=guestbook,
                headers={
                    "User-Agent": "BEMP-BIHS-research-audit/1.0",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(signed_req, timeout=180) as response:
                signed_url = json.loads(response.read())["data"]["signedUrl"]
            req = urllib.request.Request(
                signed_url, headers={"User-Agent": "BEMP-BIHS-research-audit/1.0"}
            )
            with urllib.request.urlopen(req, timeout=180) as response, target.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
        md5 = hashlib.md5(target.read_bytes()).hexdigest()
        expected = df["checksum"]["value"]
        if md5 != expected:
            raise RuntimeError(f"MD5 mismatch for {target}: {md5} != {expected}")
        rows.append(
            {
                "wave": wave,
                "dataset_doi": dataset["persistentUrl"],
                "dataset_version": f"{version['versionNumber']}.{version['versionMinorNumber']}",
                "file_id": file_id,
                "dataverse_label": label,
                "filename": download_name,
                "description": f.get("description", ""),
                "category": "; ".join(f.get("categories", [])),
                "source_url": download_url,
                "bytes": target.stat().st_size,
                "md5": md5,
                "restricted": f.get("restricted", False),
                "local_path": target.relative_to(ROOT).as_posix(),
            }
        )
        print(f"verified {wave} {download_name} {target.stat().st_size:,} bytes")

manifest = RAW / "metadata" / "selected_file_manifest.csv"
with manifest.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(manifest)
