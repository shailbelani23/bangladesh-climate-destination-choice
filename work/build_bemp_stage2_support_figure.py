#!/usr/bin/env python3
"""Draw a static support map for the BEMP climate-conditioned choice sample."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "work/vendor"))
from shapely.geometry import shape  # noqa: E402


FIX = {
    "Barisal": "Barishal", "Bogra": "Bogura", "Brahamanbaria": "Brahmanbaria",
    "Chittagong": "Chattogram", "Comilla": "Cumilla", "Jessore": "Jashore",
    "Kishoregonj": "Kishoreganj", "Maulvibazar": "Moulvibazar",
    "Nawabganj": "Chapainawabganj", "Netrokona": "Netrakona",
}


def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def blend(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    events = pd.read_csv(ROOT / "outputs/tables/bemp_prospective_migration_events.csv", low_memory=False)
    truth = lambda s: s.astype(str).str.lower().eq("true")
    sample = events[
        truth(events.stage1_household_relocation_eligible)
        & truth(events.lagged_home_shock_any_yes)
    ].copy()
    sample["destination"] = sample.destination_district_official.replace(FIX)
    sample["origin"] = sample.origin_district_codebook.replace(FIX)
    counts = sample.destination.value_counts().to_dict()
    origins = set(sample.origin)
    same = int(sample.destination.eq(sample.origin).sum())

    gj = json.loads((ROOT / "data/external/bangladesh_admin/bgd_adm2_bbs_20201113.geojson").read_text())
    geoms = []
    for feat in gj["features"]:
        name = FIX.get(feat["properties"]["adm2_en"], feat["properties"]["adm2_en"])
        geoms.append((name, shape(feat["geometry"]).simplify(0.006, preserve_topology=True)))

    width, height = 1680, 1120
    img = Image.new("RGB", (width, height), "#fbfcfe")
    draw = ImageDraw.Draw(img)
    draw.text((65, 38), "Where shock-linked BEMP household moves end up", fill="#15263c", font=font(42, True))
    draw.text(
        (65, 93),
        f"184 whole/partial-household relocations with a strictly lagged home shock; {same} ({same/len(sample):.1%}) remain in the origin district",
        fill="#42566f", font=font(23),
    )

    map_left, map_top, map_w, map_h = 55, 150, 990, 905
    all_bounds = [g.bounds for _, g in geoms]
    minx = min(b[0] for b in all_bounds); miny = min(b[1] for b in all_bounds)
    maxx = max(b[2] for b in all_bounds); maxy = max(b[3] for b in all_bounds)
    scale = min(map_w / (maxx - minx), map_h / (maxy - miny))
    xpad = (map_w - (maxx - minx) * scale) / 2
    ypad = (map_h - (maxy - miny) * scale) / 2

    def xy(lon, lat):
        return (map_left + xpad + (lon - minx) * scale, map_top + ypad + (maxy - lat) * scale)

    max_count = max(counts.values())
    for name, geom in geoms:
        n = counts.get(name, 0)
        t = math.log1p(n) / math.log1p(max_count) if n else 0
        fill = blend((235, 240, 245), (21, 93, 150), t)
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            pts = [xy(x, y) for x, y in poly.exterior.coords]
            draw.polygon(pts, fill=fill, outline="#ffffff", width=1)

    # Draw origins last so their sampling support is unmistakable.
    for name, geom in geoms:
        if name not in origins:
            continue
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            draw.line([xy(x, y) for x, y in poly.exterior.coords], fill="#d45500", width=5, joint="curve")

    district_centres = pd.read_csv(ROOT / "outputs/tables/bgd_district_universe.csv").set_index("district")
    label_offsets = {"Sirajganj": (7, -15), "Bogura": (7, 7), "Tangail": (7, 7)}
    for name in sorted(origins):
        row = district_centres.loc[name]
        px, py = xy(row.central_lon, row.central_lat)
        dx, dy = label_offsets.get(name, (7, -12))
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill="#d45500")
        draw.text((px + dx, py + dy), name, fill="#6e2e00", font=font(17, True), stroke_width=2, stroke_fill="#ffffff")

    # Legend and explanatory note.
    legend_x, legend_y = 90, 895
    for i in range(120):
        t = i / 119
        draw.line((legend_x + i * 2, legend_y, legend_x + i * 2, legend_y + 18), fill=blend((235, 240, 245), (21, 93, 150), t))
    draw.rectangle((legend_x, legend_y, legend_x + 240, legend_y + 18), outline="#9aa9b9", width=1)
    draw.text((legend_x, legend_y + 25), "0 moves", fill="#42566f", font=font(16))
    draw.text((legend_x + 181, legend_y + 25), f"{max_count} moves", fill="#42566f", font=font(16))
    draw.line((legend_x, legend_y + 75, legend_x + 60, legend_y + 75), fill="#d45500", width=5)
    draw.text((legend_x + 72, legend_y + 63), "BEMP origin district", fill="#42566f", font=font(17))

    # Right-side ranked destination counts.
    panel_x = 1085
    draw.text((panel_x, 170), "Most frequent destination districts", fill="#15263c", font=font(28, True))
    top = pd.Series(counts).sort_values(ascending=False).head(12)
    bar_max = int(top.max())
    y = 230
    for name, n in top.items():
        draw.text((panel_x, y), name, fill="#273b52", font=font(20, name in origins))
        bx, by = panel_x + 170, y + 2
        bw = int(330 * n / bar_max)
        draw.rounded_rectangle((bx, by, bx + bw, by + 22), radius=6, fill="#155d96" if name not in origins else "#d45500")
        draw.text((bx + bw + 9, y - 2), str(n), fill="#273b52", font=font(18, True))
        y += 54

    note_y = 900
    note = [
        "Interpretation", "Color shows event counts, not migration rates.",
        "Orange borders mark the seven sampled origins.",
        "District-level endpoints cannot show where within a district", "a household moved.",
    ]
    draw.text((panel_x, note_y), note[0], fill="#15263c", font=font(22, True))
    for i, line in enumerate(note[1:]):
        draw.text((panel_x, note_y + 35 + i * 27), line, fill="#52677e", font=font(17))

    out_dir = ROOT / "outputs/figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "bemp_stage2_climate_destination_support.png"
    img.save(out, optimize=True)
    print(out)


if __name__ == "__main__":
    main()
