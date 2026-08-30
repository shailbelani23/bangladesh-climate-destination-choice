#!/usr/bin/env python3
"""Acquire frozen Stage-4 rasters and make provenance-preserving local subsets.

This script deliberately keeps downloaded source files immutable under raw/ and
writes all transformed products under derived/ or subsets/.  The accessibility
source is range-read from immutable Figshare file IDs because the full archive
is 6.85 GB; each Bangladesh window retains the source URL and file ID in TIFF
metadata.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "work" / "vendor"))
import rasterio
from rasterio.windows import from_bounds

RETRIEVED = "2026-08-29"
DATA = ROOT / "data" / "external"
MANIFEST_WORK = ROOT / "work" / "bemp_stage4_acquisition_manifest_parts.csv"
BGD_BOUNDS = (87.5, 20.0, 93.0, 27.0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, path: Path) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "BEMP-research-audit/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, length=8 * 1024 * 1024)
        tmp.replace(path)
    return sha256(path), path.stat().st_size


def acquire_ghsl(rows: list[dict]) -> None:
    url = (
        "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
        "GHS_BUILT_S_GLOBE_R2023A/GHS_BUILT_S_E2020_GLOBE_R2023A_54009_1000/"
        "V1-0/GHS_BUILT_S_E2020_GLOBE_R2023A_54009_1000_V1_0.zip"
    )
    base = DATA / "ghsl_built_surface_2020"
    archive = base / "raw" / url.rsplit("/", 1)[-1]
    digest, size = download(url, archive)
    extracted = base / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    marker = extracted / ".complete"
    if not marker.exists():
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extracted)
        marker.write_text("source archive extracted without modification\n")
    rows.append({
        "source_id": "ghsl_built_surface_2020_r2023a_1km",
        "component": archive.name,
        "source_url": url,
        "retrieved_date": RETRIEVED,
        "local_path": str(archive.relative_to(ROOT)),
        "storage_status": "full_source_archive",
        "bytes": size,
        "sha256": digest,
        "source_version_or_file_id": "GHS_BUILT_S_E2020_GLOBE_R2023A_54009_1000_V1_0",
        "notes": "Global 1 km Mollweide built-surface archive; extracted copy is kept separately.",
    })


def acquire_ghsl_100m(rows: list[dict]) -> None:
    """Acquire the two official 100 m Mollweide tiles intersecting Bangladesh."""
    base_url = (
        "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
        "GHS_BUILT_S_GLOBE_R2023A/GHS_BUILT_S_E2020_GLOBE_R2023A_54009_100/"
        "V1-0/tiles/"
    )
    # Bangladesh projected bounds are x=8.165--8.969 Mm, y=2.454--3.291 Mm.
    # In the 1,000-km Mollweide tiling this intersects two rows and two columns.
    tiles = ["R6_C27", "R6_C28", "R7_C27", "R7_C28"]
    base = DATA / "ghsl_built_surface_2020_100m"
    for tile in tiles:
        name = f"GHS_BUILT_S_E2020_GLOBE_R2023A_54009_100_V1_0_{tile}.zip"
        url = base_url + name
        archive = base / "raw" / name
        digest, size = download(url, archive)
        extracted = base / "extracted" / tile
        extracted.mkdir(parents=True, exist_ok=True)
        marker = extracted / ".complete"
        if not marker.exists():
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extracted)
            marker.write_text("source tile archive extracted without modification\n")
        rows.append({
            "source_id": "ghsl_built_surface_2020_r2023a_100m",
            "component": tile,
            "source_url": url,
            "retrieved_date": RETRIEVED,
            "local_path": str(archive.relative_to(ROOT)),
            "storage_status": "full_source_tile_archive",
            "bytes": size,
            "sha256": digest,
            "source_version_or_file_id": f"GHS_BUILT_S_E2020_GLOBE_R2023A_54009_100_V1_0_{tile}",
            "notes": "Official 100 m Mollweide tile intersecting Bangladesh; extracted copy kept separately.",
        })


def acquire_worldcover(rows: list[dict]) -> None:
    tiles = ["N18E087", "N18E090", "N21E087", "N21E090", "N24E087", "N24E090"]
    base = DATA / "worldcover_2020" / "raw"
    for tile in tiles:
        name = f"ESA_WorldCover_10m_2020_v100_{tile}_Map.tif"
        url = f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/{name}"
        path = base / name
        digest, size = download(url, path)
        rows.append({
            "source_id": "esa_worldcover_2020_v100",
            "component": tile,
            "source_url": url,
            "retrieved_date": RETRIEVED,
            "local_path": str(path.relative_to(ROOT)),
            "storage_status": "full_source_tile",
            "bytes": size,
            "sha256": digest,
            "source_version_or_file_id": "v100/2020",
            "notes": "Official 3x3-degree COG; one of six tiles intersecting Bangladesh.",
        })


def acquire_accessibility(rows: list[dict]) -> None:
    # Figshare files city1--city6 jointly define travel time to cities >=50,000.
    files = {
        1: (14189804, 451_133_922),
        2: (14189807, 441_652_102),
        3: (14189810, 442_038_696),
        4: (14189816, 435_220_807),
        5: (14189819, 431_762_883),
        6: (14189825, 426_715_454),
    }
    outdir = DATA / "accessibility_2015" / "subsets"
    outdir.mkdir(parents=True, exist_ok=True)
    arrays = []
    profile = None
    transform = None
    for city_class, (file_id, source_size) in files.items():
        url = f"https://ndownloader.figshare.com/files/{file_id}"
        vsi = "/vsicurl/" + url
        out = outdir / f"accessibility_2015_city{city_class}_bangladesh_window.tif"
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_USE_HEAD="NO",
            GDAL_HTTP_MULTIRANGE="YES",
        ):
            with rasterio.open(vsi) as src:
                window = from_bounds(*BGD_BOUNDS, transform=src.transform).round_offsets().round_lengths()
                arr = src.read(1, window=window)
                win_transform = src.window_transform(window)
                source_meta = {
                    "crs": str(src.crs), "width": src.width, "height": src.height,
                    "dtype": src.dtypes[0], "nodata": src.nodata,
                    "source_bounds": list(src.bounds), "window": [float(x) for x in window.flatten()],
                }
                p = src.profile.copy()
                p.update(
                    driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                    transform=win_transform, compress="deflate", tiled=True,
                    blockxsize=256, blockysize=256,
                )
                if not out.exists():
                    with rasterio.open(out, "w", **p) as dst:
                        dst.write(arr, 1)
                        dst.update_tags(
                            source_url=url, figshare_file_id=str(file_id),
                            source_original_bytes=str(source_size),
                            extraction_bounds_wgs84=",".join(map(str, BGD_BOUNDS)),
                            extraction_date=RETRIEVED,
                        )
        if profile is None:
            profile, transform = p, win_transform
        else:
            if arr.shape != arrays[0].shape or win_transform != transform:
                raise RuntimeError("Accessibility layers are not grid-aligned")
        arrays.append(arr.astype("float32"))
        rows.append({
            "source_id": "weiss_accessibility_2015_city_ge_50k",
            "component": f"city{city_class}",
            "source_url": url,
            "retrieved_date": RETRIEVED,
            "local_path": str(out.relative_to(ROOT)),
            "storage_status": "immutable_remote_range_subset",
            "bytes": out.stat().st_size,
            "sha256": sha256(out),
            "source_version_or_file_id": str(file_id),
            "notes": (
                f"Bangladesh window range-read from immutable Figshare file; original bytes={source_size}; "
                f"source metadata={json.dumps(source_meta, separators=(',', ':'))}"
            ),
        })

    stack = np.stack(arrays)
    # Source uses uint16 maximum as unreachable/no-data, despite no formal nodata tag.
    stack[stack == np.iinfo("uint16").max] = np.nan
    with np.errstate(all="ignore"):
        minimum = np.nanmin(stack, axis=0)
    minimum[~np.isfinite(minimum)] = -9999.0
    composite = DATA / "accessibility_2015" / "derived" / "travel_time_city_ge_50k_2015_bangladesh.tif"
    composite.parent.mkdir(parents=True, exist_ok=True)
    cp = profile.copy()
    cp.update(dtype="float32", nodata=-9999.0)
    with rasterio.open(composite, "w", **cp) as dst:
        dst.write(minimum.astype("float32"), 1)
        dst.update_tags(
            derivation="pixelwise minimum of Figshare city1 through city6 (cities >=50,000)",
            source_file_ids=",".join(str(v[0]) for v in files.values()),
            extraction_bounds_wgs84=",".join(map(str, BGD_BOUNDS)),
        )
    rows.append({
        "source_id": "weiss_accessibility_2015_city_ge_50k",
        "component": "city1_to_city6_minimum",
        "source_url": "https://figshare.com/articles/dataset/7638134",
        "retrieved_date": RETRIEVED,
        "local_path": str(composite.relative_to(ROOT)),
        "storage_status": "derived_bangladesh_composite",
        "bytes": composite.stat().st_size,
        "sha256": sha256(composite),
        "source_version_or_file_id": "10.6084/m9.figshare.7638134",
        "notes": "Frozen model input; pixelwise minimum across city-size classes 1--6.",
    })


def acquire_accessibility_precombined(rows: list[dict]) -> None:
    """Acquire publisher's precombined city11 (50,000--50,000,000) layer for QA."""
    file_id, source_size = 14189849, 420_516_009
    url = f"https://ndownloader.figshare.com/files/{file_id}"
    out = DATA / "accessibility_2015" / "subsets" / "accessibility_2015_city11_bangladesh_window.tif"
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_USE_HEAD="NO"):
        with rasterio.open("/vsicurl/" + url) as src:
            window = from_bounds(*BGD_BOUNDS, transform=src.transform).round_offsets().round_lengths()
            arr = src.read(1, window=window)
            p = src.profile.copy()
            p.update(
                driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                transform=src.window_transform(window), compress="deflate", tiled=True,
                blockxsize=256, blockysize=256,
            )
    with rasterio.open(out, "w", **p) as dst:
        dst.write(arr, 1)
        dst.update_tags(
            source_url=url, figshare_file_id=str(file_id),
            source_original_bytes=str(source_size),
            extraction_bounds_wgs84=",".join(map(str, BGD_BOUNDS)), extraction_date=RETRIEVED,
        )
    composite = DATA / "accessibility_2015" / "derived" / "travel_time_city_ge_50k_2015_bangladesh.tif"
    with rasterio.open(composite) as ds:
        derived = ds.read(1)
    valid11 = arr != np.iinfo("uint16").max
    valid_derived = derived != -9999.0
    if not np.array_equal(valid11, valid_derived):
        raise RuntimeError("Publisher city11 and city1--6 composite have different valid masks")
    difference = np.abs(arr[valid11].astype("int32") - derived[valid_derived].astype("int32"))
    rows.append({
        "source_id": "weiss_accessibility_2015_city_ge_50k",
        "component": "city11_publisher_precombined_qa",
        "source_url": url,
        "retrieved_date": RETRIEVED,
        "local_path": str(out.relative_to(ROOT)),
        "storage_status": "immutable_remote_range_subset",
        "bytes": out.stat().st_size,
        "sha256": sha256(out),
        "source_version_or_file_id": str(file_id),
        "notes": (
            f"Publisher precombined 50,000--50,000,000 layer; compared to city1--6 minimum: "
            f"max_abs_difference_minutes={int(difference.max())}; differing_pixels={int((difference != 0).sum())}."
        ),
    })


def main() -> None:
    rows: list[dict] = []
    task = os.environ.get("BEMP_ACQUIRE_TASK", "all")
    if task in {"all", "ghsl"}:
        acquire_ghsl(rows)
    if task in {"all", "ghsl100m"}:
        acquire_ghsl_100m(rows)
    if task in {"all", "worldcover"}:
        acquire_worldcover(rows)
    if task in {"all", "accessibility"}:
        acquire_accessibility(rows)
    if task in {"all", "accessibility11"}:
        acquire_accessibility_precombined(rows)
    if rows:
        out = MANIFEST_WORK.with_name(f"{MANIFEST_WORK.stem}_{task}.csv")
        pd.DataFrame(rows).to_csv(out, index=False, quoting=csv.QUOTE_MINIMAL)
        print(out)
        print(pd.DataFrame(rows)[["source_id", "component", "bytes", "storage_status"]].to_string(index=False))


if __name__ == "__main__":
    main()
