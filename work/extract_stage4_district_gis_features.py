#!/usr/bin/env python3
"""Extract the four frozen Stage-4 GIS constructs for Bangladesh's 64 districts."""

from __future__ import annotations

import glob
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "work" / "vendor"))
import rasterio
from rasterio.features import geometry_mask, rasterize
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import from_bounds
from pyproj import Geod, Transformer
import shapely
from shapely.geometry import box, mapping, shape
from shapely.ops import transform as shp_transform

GEOD = Geod(ellps="WGS84")
EARTH_R = 6_371_008.8


def cached_extract(name: str, function, districts: list[dict]):
    path = ROOT / "work" / f"stage4_cache_{name}.json"
    if path.exists():
        print(f"loading cached {name}: {path}", flush=True)
        return json.loads(path.read_text())
    result = function(districts)
    path.write_text(json.dumps(result, sort_keys=True))
    print(f"cached {name}: {path}", flush=True)
    return result


def load_districts() -> list[dict]:
    gj = json.load(open(ROOT / "data" / "external" / "bangladesh_admin" / "bgd_adm2_bbs_20201113.geojson"))
    out = []
    for feat in gj["features"]:
        geom = shapely.make_valid(shape(feat["geometry"]))
        p = feat["properties"]
        out.append({
            "district_geometry_name": p["adm2_en"], "district_pcode": p["adm2_pcode"],
            "division_geometry_name": p["adm1_en"], "geometry_wgs84": geom,
            "district_geodesic_area_m2": abs(GEOD.geometry_area_perimeter(geom)[0]),
        })
    if len(out) != 64 or len({d["district_pcode"] for d in out}) != 64:
        raise RuntimeError("District boundary file is not a unique 64-district universe")
    return out


def clipped_window(ds, geom):
    left = max(ds.bounds.left, geom.bounds[0])
    bottom = max(ds.bounds.bottom, geom.bounds[1])
    right = min(ds.bounds.right, geom.bounds[2])
    top = min(ds.bounds.top, geom.bounds[3])
    if left >= right or bottom >= top:
        return None
    w = from_bounds(left, bottom, right, top, ds.transform)
    w = w.round_offsets().round_lengths()
    return w.intersection(rasterio.windows.Window(0, 0, ds.width, ds.height))


def fractional_coverage(geom, out_shape, transform):
    """Exact fractions for boundary cells; full interior cells avoid costly intersections."""
    center_inside = geometry_mask(
        [mapping(geom)], out_shape=out_shape, transform=transform,
        invert=True, all_touched=False,
    )
    boundary = rasterize(
        [(mapping(geom.boundary), 1)], out_shape=out_shape, transform=transform,
        fill=0, all_touched=True, dtype="uint8",
    ).astype(bool)
    fractions = center_inside.astype("float32")
    rr, cc = np.nonzero(boundary)
    if len(rr):
        x0 = transform.c + cc * transform.a
        x1 = x0 + transform.a
        y0 = transform.f + rr * transform.e
        y1 = y0 + transform.e
        cells = shapely.box(np.minimum(x0, x1), np.minimum(y0, y1),
                            np.maximum(x0, x1), np.maximum(y0, y1))
        inter = shapely.intersection(cells, geom)
        cell_area = abs(transform.a * transform.e)
        fractions[rr, cc] = np.clip(shapely.area(inter) / cell_area, 0.0, 1.0)
    return fractions


def geographic_row_areas(transform, height: int) -> np.ndarray:
    """Spherical square-metres per geographic raster cell, one value per row."""
    lat_top = transform.f + np.arange(height) * transform.e
    lat_bottom = lat_top + transform.e
    dlon = abs(transform.a) * math.pi / 180.0
    return (EARTH_R**2 * dlon * np.abs(
        np.sin(np.deg2rad(lat_top)) - np.sin(np.deg2rad(lat_bottom))
    )).reshape(-1, 1)


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum(), side="left")])


def worldcover_one(d: dict, paths: list[str]) -> tuple[str, str, dict]:
    geom = d["geometry_wgs84"]
    accum = {
        "mapped": 0.0, "land": 0.0, "water": 0.0, "crop": 0.0, "built": 0.0,
        "gfd_flood_land": 0.0,
    }
    gfd_path = ROOT / "data" / "external" / "global_flood_database" / "derived" / "gfd_ever_flooded_land_2000_2018_bangladesh.tif"
    with rasterio.open(gfd_path) as gfd_ds:
        for path in paths:
            with rasterio.open(path) as ds:
                if not geom.intersects(box(*ds.bounds)):
                    continue
                w = clipped_window(ds, geom)
                if w is None:
                    continue
                a = ds.read(1, window=w)
                t = ds.window_transform(w)
                f = fractional_coverage(geom, a.shape, t)
                area = f * geographic_row_areas(t, a.shape[0])
                valid = a != ds.nodata
                land = valid & (a != 80)
                flood = np.zeros(a.shape, dtype="uint8")
                reproject(
                    source=rasterio.band(gfd_ds, 1), destination=flood,
                    src_transform=gfd_ds.transform, src_crs=gfd_ds.crs,
                    dst_transform=t, dst_crs=ds.crs,
                    src_nodata=None, dst_nodata=0, resampling=Resampling.nearest,
                )
                accum["mapped"] += float(area[valid].sum())
                accum["water"] += float(area[(a == 80) & valid].sum())
                accum["crop"] += float(area[(a == 40) & valid].sum())
                accum["built"] += float(area[(a == 50) & valid].sum())
                accum["gfd_flood_land"] += float(area[land & (flood == 1)].sum())
    accum["land"] = accum["mapped"] - accum["water"]
    return d["district_pcode"], d["district_geometry_name"], accum


def extract_worldcover(districts: list[dict]) -> dict[str, dict]:
    paths = sorted(glob.glob(str(ROOT / "data" / "external" / "worldcover_2020" / "raw" / "*.tif")))
    out = {}
    # Separate raster handles are opened inside each worker. GEOS and GDAL release
    # the GIL for the expensive boundary intersections and compressed-window reads.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(worldcover_one, d, paths) for d in districts]
        for i, fut in enumerate(as_completed(futures), 1):
            pcode, name, accum = fut.result()
            out[pcode] = accum
            print(f"worldcover {i:02d}/64 {name}", flush=True)
    return out


def extract_ghsl(districts: list[dict]) -> dict[str, dict]:
    paths = sorted(glob.glob(str(
        ROOT / "data" / "external" / "ghsl_built_surface_2020_100m" / "extracted" / "**" / "*.tif"
    ), recursive=True))
    if len(paths) != 4:
        raise RuntimeError(f"Expected four GHSL 100 m tiles, found {len(paths)}")
    to_moll = Transformer.from_crs("EPSG:4326", "ESRI:54009", always_xy=True).transform
    out = {}
    for i, d in enumerate(districts, 1):
        geom = shp_transform(to_moll, d["geometry_wgs84"])
        built_m2 = valid_area_m2 = 0.0
        for path in paths:
            with rasterio.open(path) as ds:
                if not geom.intersects(box(*ds.bounds)):
                    continue
                w = clipped_window(ds, geom)
                if w is None:
                    continue
                a = ds.read(1, window=w)
                t = ds.window_transform(w)
                f = fractional_coverage(geom, a.shape, t)
                valid = a != ds.nodata
                built_m2 += float((a[valid].astype("float64") * f[valid]).sum())
                valid_area_m2 += float((f[valid] * abs(t.a * t.e)).sum())
        out[d["district_pcode"]] = {"built_m2": built_m2, "valid_area_m2": valid_area_m2}
        print(f"ghsl {i:02d}/64 {d['district_geometry_name']}", flush=True)
    return out


def extract_accessibility(districts: list[dict]) -> dict[str, dict]:
    path = ROOT / "data" / "external" / "accessibility_2015" / "derived" / "travel_time_city_ge_50k_2015_bangladesh.tif"
    out = {}
    with rasterio.open(path) as ds:
        for i, d in enumerate(districts, 1):
            geom = d["geometry_wgs84"]
            w = clipped_window(ds, geom)
            a = ds.read(1, window=w)
            t = ds.window_transform(w)
            f = fractional_coverage(geom, a.shape, t)
            area = f * geographic_row_areas(t, a.shape[0])
            valid = (a != ds.nodata) & (f > 0)
            med = weighted_median(a[valid].astype("float64"), area[valid].astype("float64"))
            out[d["district_pcode"]] = {
                "median_minutes": med, "valid_area_m2": float(area[valid].sum()),
                "valid_cell_count": int(valid.sum()),
            }
            print(f"access {i:02d}/64 {d['district_geometry_name']}", flush=True)
    return out


def extract_gfd(districts: list[dict]) -> dict[str, dict]:
    path = ROOT / "data" / "external" / "global_flood_database" / "derived" / "gfd_ever_flooded_land_2000_2018_bangladesh.tif"
    if not path.exists():
        raise RuntimeError("GFD union has not finished")
    out = {}
    with rasterio.open(path) as ds:
        for i, d in enumerate(districts, 1):
            geom = d["geometry_wgs84"]
            w = clipped_window(ds, geom)
            a = ds.read(1, window=w)
            t = ds.window_transform(w)
            f = fractional_coverage(geom, a.shape, t)
            area = f * geographic_row_areas(t, a.shape[0])
            out[d["district_pcode"]] = {
                "flooded_land_m2": float(area[a == 1].sum()),
                "raster_allocated_area_m2": float(area.sum()),
                "flooded_pixel_count": int((a == 1).sum()),
            }
            print(f"gfd {i:02d}/64 {d['district_geometry_name']}", flush=True)
    return out


def main() -> None:
    districts = load_districts()
    wc = cached_extract("worldcover", extract_worldcover, districts)
    ghsl = cached_extract("ghsl", extract_ghsl, districts)
    access = cached_extract("accessibility", extract_accessibility, districts)
    gfd = cached_extract("gfd", extract_gfd, districts)

    universe = pd.read_csv(ROOT / "outputs" / "tables" / "bgd_district_universe.csv")
    canonical = universe.set_index("district_pcode")["district"].to_dict()
    rows = []
    for d in districts:
        p = d["district_pcode"]
        land = wc[p]["land"]
        rows.append({
            "district": canonical[p], "district_pcode": p,
            "district_geometry_name": d["district_geometry_name"],
            "division_geometry_name": d["division_geometry_name"],
            "district_geodesic_area_m2": d["district_geodesic_area_m2"],
            "worldcover_valid_mapped_area_m2": wc[p]["mapped"],
            "worldcover_permanent_water_area_m2": wc[p]["water"],
            "worldcover_valid_land_area_m2": land,
            "worldcover_cropland_area_m2_2020": wc[p]["crop"],
            "worldcover_built_class_area_m2_2020": wc[p]["built"],
            "worldcover_valid_coverage_share": wc[p]["mapped"] / d["district_geodesic_area_m2"],
            "worldcover_cropland_share_2020": wc[p]["crop"] / land,
            "ghsl_built_surface_m2_2020": ghsl[p]["built_m2"],
            "ghsl_valid_allocated_area_m2": ghsl[p]["valid_area_m2"],
            "ghsl_valid_coverage_share": ghsl[p]["valid_area_m2"] / d["district_geodesic_area_m2"],
            "ghsl_built_surface_share_2020": ghsl[p]["built_m2"] / land,
            "travel_time_city_ge_50k_median_2015": access[p]["median_minutes"],
            "accessibility_valid_area_m2": access[p]["valid_area_m2"],
            "accessibility_valid_cell_count": access[p]["valid_cell_count"],
            "accessibility_valid_geometry_coverage_share": access[p]["valid_area_m2"] / d["district_geodesic_area_m2"],
            "accessibility_valid_land_coverage_share": access[p]["valid_area_m2"] / land,
            "gfd_raw_flooded_allocated_area_m2_before_worldcover_land_mask": gfd[p]["flooded_land_m2"],
            "gfd_ever_flooded_land_area_m2_2000_2018": wc[p]["gfd_flood_land"],
            "gfd_raster_allocated_area_m2": gfd[p]["raster_allocated_area_m2"],
            "gfd_flooded_pixel_count": gfd[p]["flooded_pixel_count"],
            "gfd_ever_flooded_land_share_2000_2018": wc[p]["gfd_flood_land"] / land,
        })
    df = pd.DataFrame(rows).sort_values("district").reset_index(drop=True)
    if len(df) != 64 or df["district_pcode"].nunique() != 64:
        raise RuntimeError("Final feature table is not a unique 64-district universe")
    out = ROOT / "outputs" / "tables" / "bemp_stage4_district_gis_features.csv"
    df.to_csv(out, index=False)
    print("\n", out)
    print(df[["district", "gfd_ever_flooded_land_share_2000_2018", "ghsl_built_surface_share_2020",
              "travel_time_city_ge_50k_median_2015", "worldcover_cropland_share_2020"]].to_string(index=False))


if __name__ == "__main__":
    main()
