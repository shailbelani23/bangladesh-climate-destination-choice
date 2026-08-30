#!/usr/bin/env python3
"""Identify every public GFD raster whose spatial bounds overlap Bangladesh."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "work" / "vendor"))
import rasterio

BUCKET_API = "https://storage.googleapis.com/storage/v1/b/gfd_v3/o"
BGD_BOUNDS = (87.5, 20.0, 93.0, 27.0)


def list_objects() -> list[dict]:
    items: list[dict] = []
    token = None
    while True:
        params = {"maxResults": 1000}
        if token:
            params["pageToken"] = token
        with urllib.request.urlopen(BUCKET_API + "?" + urllib.parse.urlencode(params), timeout=120) as r:
            page = json.load(r)
        items.extend(page.get("items", []))
        token = page.get("nextPageToken")
        if not token:
            break
    return items


def inspect(obj: dict) -> dict:
    name = obj["name"]
    url = "https://storage.googleapis.com/gfd_v3/" + urllib.parse.quote(name)
    row = {
        "name": name, "url": url, "bytes": int(obj["size"]), "generation": obj["generation"],
        "md5_base64": obj.get("md5Hash", ""), "etag": obj.get("etag", ""), "error": "",
    }
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_USE_HEAD="NO"):
            with rasterio.open("/vsicurl/" + url) as ds:
                b = ds.bounds
                row.update(left=b.left, bottom=b.bottom, right=b.right, top=b.top,
                           crs=str(ds.crs), width=ds.width, height=ds.height, count=ds.count)
                row["overlaps_bangladesh_bbox"] = bool(
                    b.left < BGD_BOUNDS[2] and b.right > BGD_BOUNDS[0]
                    and b.bottom < BGD_BOUNDS[3] and b.top > BGD_BOUNDS[1]
                )
    except Exception as exc:
        row["error"] = repr(exc)
        row["overlaps_bangladesh_bbox"] = False
    return row


def main() -> None:
    objects = [o for o in list_objects() if o["name"].lower().endswith(".tif")]
    print(f"objects={len(objects)}", flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(inspect, o) for o in objects]
        for i, fut in enumerate(as_completed(futures), 1):
            rows.append(fut.result())
            if i % 100 == 0:
                print(f"inspected={i}", flush=True)
    out = ROOT / "work" / "gfd_public_object_spatial_inventory.csv"
    df = pd.DataFrame(rows).sort_values("name")
    df.to_csv(out, index=False)
    hits = df[df["overlaps_bangladesh_bbox"]]
    hits.to_csv(ROOT / "work" / "gfd_bangladesh_bbox_event_candidates.csv", index=False)
    print(f"errors={(df['error'] != '').sum()} bbox_hits={len(hits)}")
    print(hits[["name", "bytes", "left", "bottom", "right", "top"]].to_string(index=False))


if __name__ == "__main__":
    main()
