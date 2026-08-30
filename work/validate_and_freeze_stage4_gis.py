#!/usr/bin/env python3
"""Validate, summarize, and checksum the frozen 64-district GIS table."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
PRIMARY = [
    "gfd_ever_flooded_land_share_2000_2018",
    "ghsl_built_surface_share_2020",
    "travel_time_city_ge_50k_median_2015",
    "worldcover_cropland_share_2020",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validation_row(check, passed, observed, requirement, severity="fatal"):
    return {"check": check, "passed": bool(passed), "observed": observed,
            "requirement": requirement, "severity": severity}


def build_source_manifest() -> pd.DataFrame:
    paths = sorted((ROOT / "work").glob("bemp_stage4_acquisition_manifest_parts_*.csv"))
    frames = [pd.read_csv(p) for p in paths]
    manifest = pd.concat(frames, ignore_index=True)
    extras = [
        ("global_flood_database_v1_2000_2018", "official_geotiff_readme",
         "https://storage.googleapis.com/gfd_metadata/README_GFD.pdf",
         ROOT / "data/external/global_flood_database/raw/README_GFD.pdf", "official_metadata"),
        ("global_flood_database_v1_2000_2018", "official_913_event_statistics",
         "https://storage.googleapis.com/event_stats/gfd_event_stats_20215_13_error_fixed_2.csv",
         ROOT / "work/gfd_event_stats.csv", "official_metadata"),
        ("weiss_accessibility_2015_city_ge_50k", "publisher_readme",
         "https://ndownloader.figshare.com/files/37847109",
         ROOT / "data/external/accessibility_2015/raw/README.txt", "official_metadata"),
        ("weiss_accessibility_2015_city_ge_50k", "publisher_metadata_csv",
         "https://ndownloader.figshare.com/files/37847112",
         ROOT / "data/external/accessibility_2015/raw/metadata.csv", "official_metadata"),
    ]
    extra_rows = []
    for sid, component, url, path, status in extras:
        extra_rows.append({
            "source_id": sid, "component": component, "source_url": url,
            "retrieved_date": "2026-08-29", "local_path": str(path.relative_to(ROOT)),
            "storage_status": status, "bytes": path.stat().st_size, "sha256": sha256(path),
            "source_version_or_file_id": "", "notes": "Official supporting metadata retained locally.",
        })
    manifest = pd.concat([manifest, pd.DataFrame(extra_rows)], ignore_index=True)
    manifest = manifest.drop_duplicates(subset=["source_id", "component", "local_path"], keep="last")
    manifest = manifest.sort_values(["source_id", "component"]).reset_index(drop=True)
    manifest.to_csv(TABLES / "bemp_stage4_source_manifest.csv", index=False)
    return manifest


def main() -> None:
    features_path = TABLES / "bemp_stage4_district_gis_features.csv"
    df = pd.read_csv(features_path)
    manifest = build_source_manifest()

    summary = df[PRIMARY].describe(percentiles=[.05, .25, .5, .75, .95]).T.reset_index()
    summary = summary.rename(columns={"index": "feature"})
    summary["missing_count"] = [df[c].isna().sum() for c in PRIMARY]
    summary.to_csv(TABLES / "bemp_stage4_gis_feature_summary.csv", index=False)

    pearson = df[PRIMARY].corr(method="pearson")
    spearman = df[PRIMARY].corr(method="spearman")
    corr_rows = []
    for method, matrix in [("pearson", pearson), ("spearman", spearman)]:
        for i, a in enumerate(PRIMARY):
            for b in PRIMARY[i + 1:]:
                corr_rows.append({"method": method, "feature_a": a, "feature_b": b,
                                  "correlation": matrix.loc[a, b]})
    pd.DataFrame(corr_rows).to_csv(TABLES / "bemp_stage4_gis_feature_correlations.csv", index=False)

    checks = []
    checks.append(validation_row("district_row_count", len(df) == 64, len(df), "exactly 64"))
    checks.append(validation_row("unique_district_pcodes", df.district_pcode.nunique() == 64,
                                 df.district_pcode.nunique(), "exactly 64"))
    checks.append(validation_row("primary_feature_missingness", df[PRIMARY].isna().sum().sum() == 0,
                                 int(df[PRIMARY].isna().sum().sum()), "zero missing values"))
    for c in [PRIMARY[0], PRIMARY[1], PRIMARY[3]]:
        lo, hi = float(df[c].min()), float(df[c].max())
        checks.append(validation_row(f"bounded_share__{c}", lo >= 0 and hi <= 1,
                                     f"min={lo:.8f}; max={hi:.8f}", "0 <= share <= 1"))
    checks.append(validation_row("accessibility_nonnegative", df[PRIMARY[2]].min() >= 0,
                                 float(df[PRIMARY[2]].min()), ">= 0 minutes"))
    for c in ["worldcover_valid_coverage_share", "ghsl_valid_coverage_share",
              "accessibility_valid_land_coverage_share"]:
        m = float(df[c].min())
        checks.append(validation_row(f"minimum_coverage__{c}", m >= .95, f"min={m:.6f}",
                                     "every district >= 0.95", severity="fatal"))
    city11 = manifest[manifest.component == "city11_publisher_precombined_qa"].iloc[0]
    m = re.search(r"differing_pixels=(\d+)", str(city11.notes))
    differing = int(m.group(1)) if m else -1
    checks.append(validation_row("accessibility_city11_equivalence", differing == 0, differing,
                                 "zero differing pixels"))
    gfd_events = pd.read_csv(TABLES / "bemp_stage4_gfd_event_manifest.csv")
    checks.append(validation_row("gfd_catalog_bbox_candidates", len(gfd_events) == 134, len(gfd_events),
                                 "134 catalog rasters from spatial scan", severity="informational"))
    checks.append(validation_row("gfd_actual_intersections", gfd_events.actual_flood_intersection.sum() == 103,
                                 int(gfd_events.actual_flood_intersection.sum()),
                                 "103 events with actual non-permanent flooded pixels", severity="informational"))
    checks.append(validation_row("source_manifest_local_files_exist",
                                 all((ROOT / p).exists() for p in manifest.local_path),
                                 int(sum((ROOT / p).exists() for p in manifest.local_path)),
                                 f"all {len(manifest)} local components exist"))
    checksum_matches = sum(
        sha256(ROOT / row.local_path) == row.sha256 for row in manifest.itertuples(index=False)
    )
    checks.append(validation_row("source_manifest_sha256_matches", checksum_matches == len(manifest),
                                 checksum_matches, f"all {len(manifest)} local component hashes match"))
    val = pd.DataFrame(checks)
    val.to_csv(TABLES / "bemp_stage4_validation.csv", index=False)

    if not val.loc[val.severity == "fatal", "passed"].all():
        print(val.to_string(index=False))
        raise RuntimeError("Stage-4 fatal validation checks failed")

    freeze_targets = [
        ROOT / "outputs" / "reports" / "bemp_stage4_gis_feature_audit.md",
        features_path,
        TABLES / "bemp_stage4_gis_feature_summary.csv",
        TABLES / "bemp_stage4_gis_feature_correlations.csv",
        TABLES / "bemp_stage4_source_manifest.csv",
        TABLES / "bemp_stage4_gfd_event_manifest.csv",
        TABLES / "bemp_stage4_validation.csv",
    ]
    freeze = pd.DataFrame([{
        "artifact": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
        "sha256": sha256(p), "frozen_at": "2026-08-29",
        "freeze_scope": "pre-model Stage-4 GIS feature build",
    } for p in freeze_targets])
    freeze.to_csv(TABLES / "bemp_stage4_feature_freeze_manifest.csv", index=False)
    print(val.to_string(index=False))
    print("\nSummary\n", summary.to_string(index=False))
    print("\nCorrelations\n", pd.DataFrame(corr_rows).to_string(index=False))


if __name__ == "__main__":
    main()
