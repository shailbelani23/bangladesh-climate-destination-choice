#!/usr/bin/env python3
"""Range-read official GFD events and build Bangladesh ever-flooded-land union."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "work" / "vendor"))
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.transform import from_origin

BOUNDS = (87.5, 20.0, 93.0, 27.0)
RES = 0.002245788210298803  # native GFD grid spacing (~250 m at equator)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    inventory = pd.read_csv(ROOT / "work" / "gfd_public_object_spatial_inventory.csv")
    stats_path = ROOT / "work" / "gfd_event_stats.csv"
    stats = pd.read_csv(stats_path)
    official_names = set(stats["system:index"].astype(str) + ".tif")
    inventory["in_official_913_catalog"] = inventory["name"].isin(official_names)
    candidates = inventory[
        inventory["overlaps_bangladesh_bbox"] & inventory["in_official_913_catalog"]
    ].copy()
    if len(official_names) != 913:
        raise RuntimeError(f"Expected 913 catalog events, found {len(official_names)}")

    width = math.ceil((BOUNDS[2] - BOUNDS[0]) / RES)
    height = math.ceil((BOUNDS[3] - BOUNDS[1]) / RES)
    transform = from_origin(BOUNDS[0], BOUNDS[3], RES, RES)
    flood_count = np.zeros((height, width), dtype="uint16")
    observed_event_count = np.zeros((height, width), dtype="uint16")
    rows = []

    for i, row in enumerate(candidates.itertuples(index=False), 1):
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_USE_HEAD="NO",
            GDAL_HTTP_MULTIRANGE="YES",
        ):
            with rasterio.open("/vsicurl/" + row.url) as src:
                with WarpedVRT(
                    src, crs="EPSG:4326", transform=transform, width=width, height=height,
                    resampling=Resampling.nearest, add_alpha=False,
                ) as vrt:
                    flooded = vrt.read(1)
                    clear_views = vrt.read(3)
                    permanent_water = vrt.read(5)
        observed = clear_views > 0
        # The target construct is flooded land, so JRC permanent surface water is excluded.
        event_flood = (flooded >= 1) & (permanent_water < 1)
        flood_count += event_flood.astype("uint16")
        observed_event_count += observed.astype("uint16")
        rows.append({
            "name": row.name,
            "source_url": row.url,
            "generation": row.generation,
            "source_bytes": row.bytes,
            "source_md5_base64": row.md5_base64,
            "source_etag": row.etag,
            "bbox_overlap": True,
            "actual_flooded_land_pixels_in_bgd_window": int(event_flood.sum()),
            "actual_flood_intersection": bool(event_flood.any()),
            "observed_pixels_in_bgd_window": int(observed.sum()),
        })
        if i % 10 == 0:
            print(f"processed={i}/{len(candidates)} actual_hits={sum(r['actual_flood_intersection'] for r in rows)}", flush=True)

    base = ROOT / "data" / "external" / "global_flood_database" / "derived"
    base.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff", "width": width, "height": height, "count": 1,
        "crs": "EPSG:4326", "transform": transform, "compress": "deflate",
        "tiled": True, "blockxsize": 256, "blockysize": 256,
    }
    union_path = base / "gfd_ever_flooded_land_2000_2018_bangladesh.tif"
    with rasterio.open(union_path, "w", dtype="uint8", nodata=0, **profile) as dst:
        dst.write((flood_count > 0).astype("uint8"), 1)
        dst.update_tags(
            derivation="union of GFD flooded band after excluding JRC permanent water",
            catalog_event_count="913", bbox_candidate_count=str(len(candidates)),
            source_period="2000-2018", gfd_native_resolution_degrees=str(RES),
        )
    count_path = base / "gfd_flood_event_count_2000_2018_bangladesh.tif"
    with rasterio.open(count_path, "w", dtype="uint16", nodata=0, **profile) as dst:
        dst.write(flood_count, 1)
    observed_path = base / "gfd_observed_event_count_2000_2018_bangladesh.tif"
    with rasterio.open(observed_path, "w", dtype="uint16", nodata=0, **profile) as dst:
        dst.write(observed_event_count, 1)

    event_manifest = pd.DataFrame(rows)
    event_manifest.to_csv(ROOT / "outputs" / "tables" / "bemp_stage4_gfd_event_manifest.csv", index=False)
    source_row = pd.DataFrame([{
        "source_id": "global_flood_database_v1_2000_2018",
        "component": "ever_flooded_land_union",
        "source_url": "https://storage.googleapis.com/gfd_v3/",
        "retrieved_date": "2026-08-29",
        "local_path": str(union_path.relative_to(ROOT)),
        "storage_status": "derived_bangladesh_union_from_immutable_remote_range_reads",
        "bytes": union_path.stat().st_size,
        "sha256": sha256(union_path),
        "source_version_or_file_id": "GLOBAL_FLOOD_DB_MODIS_EVENTS_V1",
        "notes": (
            f"Filtered {len(candidates)} catalog events with raster bounding boxes intersecting Bangladesh; "
            f"{event_manifest.actual_flood_intersection.sum()} contained actual non-permanent flooded-land pixels. "
            "Every contributing source generation and MD5 is recorded in bemp_stage4_gfd_event_manifest.csv."
        ),
    }])
    source_row.to_csv(ROOT / "work" / "bemp_stage4_acquisition_manifest_parts_gfd.csv", index=False)
    print(f"candidates={len(candidates)} actual_hits={event_manifest.actual_flood_intersection.sum()}")
    print(f"union_pixels={int((flood_count > 0).sum())} max_event_count={int(flood_count.max())}")
    print(union_path)


if __name__ == "__main__":
    main()
