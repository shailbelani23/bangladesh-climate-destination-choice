#!/usr/bin/env python3
"""Build the first publication and interactive storytelling visual suite."""

from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape, mapping
from shapely import make_valid, set_precision

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs/tables"
F = ROOT / "outputs/figures"
V = ROOT / "publication" / "interactive"
F.mkdir(parents=True, exist_ok=True)
V.mkdir(parents=True, exist_ok=True)

NAVY = "#17324D"
MUTED = "#617488"
GRID = "#D9E1E8"
TEAL = "#087E8B"
ORANGE = "#D66A2C"
PURPLE = "#7057A8"
RED = "#B74A4A"
PAPER = "#FBFCFD"


def font(size, bold=False):
    paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def rounded(draw, box, fill, radius=10):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def wrap(draw, text, fnt, width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=fnt) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def simplified_geometry():
    src = ROOT / "data/external/bangladesh_admin/bgd_adm2_bbs_20201113.geojson"
    raw = json.loads(src.read_text())
    district_aliases = {
        "Barisal": "Barishal",
        "Bogra": "Bogura",
        "Brahamanbaria": "Brahmanbaria",
        "Chittagong": "Chattogram",
        "Comilla": "Cumilla",
        "Jessore": "Jashore",
        "Maulvibazar": "Moulvibazar",
        "Nawabganj": "Chapainawabganj",
    }
    features = []
    for feat in raw["features"]:
        geom = make_valid(
            set_precision(
                make_valid(shape(feat["geometry"])).simplify(0.012, preserve_topology=True),
                0.001,
                mode="pointwise",
            )
        )
        features.append({
            "type": "Feature",
            "properties": {
                "district": district_aliases.get(feat["properties"]["adm2_en"], feat["properties"]["adm2_en"]),
                "pcode": feat["properties"]["adm2_pcode"],
            },
            "geometry": mapping(geom),
        })
    geo = {"type": "FeatureCollection", "features": features}
    return geo


def draw_forest():
    x = pd.read_csv(T / "cross_dataset_replication_summary.csv")
    x = x[(x.validation_scheme == "household_grouped_5fold") & x.cluster_bootstrap_ci_low.notna()].copy()
    order = [
        ("BEMP", "household_lagged_shock_yes", "full_64", "BEMP shock-linked · full 64"),
        ("BEMP", "household_lagged_shock_yes", "interdistrict_63", "BEMP shock-linked · interdistrict"),
        ("BIHS", "b4_erosion", "full_64", "BIHS river erosion · full 64"),
        ("BIHS", "b4_erosion", "interdistrict_63", "BIHS river erosion · interdistrict"),
        ("BIHS", "b4_all", "full_64", "BIHS all household moves · full 64"),
        ("BIHS", "b4_all", "interdistrict_63", "BIHS all household moves · interdistrict"),
        ("BIHS", "v1_interval", "full_64", "BIHS national migrants · full 64"),
        ("BIHS", "v1_interval", "interdistrict_63", "BIHS national migrants · interdistrict"),
    ]
    rows = []
    for dataset, sample, universe, label in order:
        r = x[(x.dataset == dataset) & (x["sample"] == sample) & (x.candidate_universe == universe)].iloc[0]
        rows.append((label, int(r.n_events_evaluated), float(r.log_loss_improvement_vs_gravity),
                     float(r.cluster_bootstrap_ci_low), float(r.cluster_bootstrap_ci_high),
                     TEAL if dataset == "BIHS" else ORANGE))

    W, H = 1800, 1180
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((70, 48), "District geography improves prediction on held-out moves", fill=NAVY, font=font(42, True))
    d.text((70, 105), "Change in log loss relative to the distance-and-population model", fill=MUTED, font=font(25))
    left, right, top, bottom = 780, 1680, 210, 990
    xmin, xmax = -0.08, 0.68
    px = lambda v: left + (v - xmin) / (xmax - xmin) * (right - left)
    for tick in [-0.05, 0, .1, .2, .3, .4, .5, .6]:
        xx = px(tick)
        d.line((xx, top, xx, bottom), fill="#9AA9B6" if tick == 0 else GRID, width=3 if tick == 0 else 2)
        d.text((xx, bottom + 34), f"{tick:.2f}", anchor="mm", fill=MUTED, font=font(20))
    ys = np.linspace(top + 35, bottom - 35, len(rows))
    for (label, n, est, lo, hi, color), y in zip(rows, ys):
        d.text((735, y - 10), label, anchor="rs", fill=NAVY, font=font(23, True))
        d.text((735, y + 20), f"{n:,} events", anchor="rs", fill=MUTED, font=font(18))
        d.line((px(lo), y, px(hi), y), fill=color, width=7)
        d.line((px(lo), y - 12, px(lo), y + 12), fill=color, width=4)
        d.line((px(hi), y - 12, px(hi), y + 12), fill=color, width=4)
        d.ellipse((px(est) - 11, y - 11, px(est) + 11, y + 11), fill=color)
        d.text((min(px(hi) + 16, right - 160), y), f"{est:.3f}", anchor="lm", fill=NAVY, font=font(19, True))
    d.text(((left + right) / 2, 1080), "Mean held-out log-loss improvement", anchor="mm", fill=NAVY, font=font(24, True))
    d.text((70, 1125), "Whiskers are paired 95% household-cluster bootstrap intervals (5,000 replicates).",
           fill=MUTED, font=font(19))
    img.save(F / "cross_dataset_gis_gain_forest.png", optimize=True)


def draw_transport():
    x = pd.read_csv(T / "cross_dataset_replication_summary.csv")
    specs = [
        ("BEMP", "household_lagged_shock_yes", "full_64", "BEMP shock-linked · full 64"),
        ("BEMP", "household_lagged_shock_yes", "interdistrict_63", "BEMP shock-linked · interdistrict"),
        ("BIHS", "b4_erosion", "full_64", "BIHS erosion · full 64"),
        ("BIHS", "b4_erosion", "interdistrict_63", "BIHS erosion · interdistrict"),
        ("BIHS", "v1_interval", "full_64", "BIHS national migrants · full 64"),
        ("BIHS", "v1_interval", "interdistrict_63", "BIHS national migrants · interdistrict"),
    ]
    rows = []
    for ds, sample, universe, label in specs:
        z = x[(x.dataset == ds) & (x["sample"] == sample) & (x.candidate_universe == universe)]
        grouped = float(z[z.validation_scheme == "household_grouped_5fold"].log_loss_improvement_vs_gravity.iloc[0])
        loo = float(z[z.validation_scheme == "leave_one_origin_out"].log_loss_improvement_vs_gravity.iloc[0])
        temporal = np.nan
        if ds == "BIHS" and sample == "v1_interval":
            temporal = float(z[z.validation_scheme == "wave_holdout_r3"].log_loss_improvement_vs_gravity.iloc[0])
        rows.append((label, grouped, loo, temporal))

    W, H = 1700, 1000
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((65, 45), "Destination ranking holds up across wider origin coverage", fill=NAVY, font=font(42, True))
    d.text((65, 100), "GIS gain over distance and population under three validation tests", fill=MUTED, font=font(25))
    left, right, top, bottom = 710, 1580, 210, 820
    xmin, xmax = -0.34, 0.38
    px = lambda v: left + (v - xmin) / (xmax - xmin) * (right - left)
    for tick in [-.3, -.2, -.1, 0, .1, .2, .3]:
        xx = px(tick)
        d.line((xx, top, xx, bottom), fill="#8C9AA8" if tick == 0 else GRID, width=3 if tick == 0 else 2)
        d.text((xx, bottom + 32), f"{tick:.1f}", anchor="mm", fill=MUTED, font=font(19))
    ys = np.linspace(top + 45, bottom - 45, len(rows))
    for (label, grouped, loo, temporal), y in zip(rows, ys):
        d.text((665, y), label, anchor="rm", fill=NAVY, font=font(22, True))
        d.line((px(grouped), y - 13, px(grouped), y + 13), fill=TEAL, width=7)
        d.ellipse((px(loo) - 9, y - 9, px(loo) + 9, y + 9), outline=ORANGE, width=5)
        if not np.isnan(temporal):
            xx = px(temporal)
            d.polygon([(xx, y - 12), (xx + 12, y + 10), (xx - 12, y + 10)], fill=PURPLE)
    ly = 915
    d.line((520, ly - 13, 520, ly + 13), fill=TEAL, width=7)
    d.text((545, ly), "Household-grouped", anchor="lm", fill=NAVY, font=font(20))
    d.ellipse((790, ly - 9, 808, ly + 9), outline=ORANGE, width=5)
    d.text((823, ly), "Leave one origin out", anchor="lm", fill=NAVY, font=font(20))
    d.polygon([(1120, ly - 12), (1132, ly + 10), (1108, ly + 10)], fill=PURPLE)
    d.text((1148, ly), "Train 2015 → test 2018–19", anchor="lm", fill=NAVY, font=font(20))
    img.save(F / "validation_transportability_comparison.png", optimize=True)


def event_probabilities(event_id):
    choice = pd.read_csv(T / "bihs_replication_choice_set.csv", low_memory=False)
    choice = choice[choice.event_id == event_id].copy()
    pred = pd.read_csv(T / "bihs_replication_oof_predictions_grouped.csv")
    row = pred[(pred.event_id == event_id) & (pred["sample"] == "b4_erosion") &
               (pred.candidate_universe == "full_64") & (pred.model == "gis_joint_ridge")].iloc[0]
    fold = row.fold
    params = pd.read_csv(T / "bihs_replication_fold_parameters_grouped.csv")
    p = params[(params["sample"] == "b4_erosion") & (params.candidate_universe == "full_64") &
               (params.validation_scheme == "household_grouped_5fold") & (params.fold == fold)]
    out = {}
    for model in ["gravity_mle_disk_within", "gis_joint_ridge"]:
        q = p[p.model == model]
        beta = dict(zip(q.feature, q.coefficient))
        util = np.zeros(len(choice))
        for feature, coef in beta.items():
            if feature in choice:
                values = choice[feature].to_numpy(float)
            elif feature.startswith("z_"):
                raw = {
                    "z_gfd_flood": "gfd_ever_flooded_land_share_2000_2018",
                    "z_ghsl_built": "ghsl_built_surface_share_2020",
                    "z_access_time": "travel_time_city_ge_50k_median_2015",
                    "z_cropland": "worldcover_cropland_share_2020",
                }[feature]
                values = (choice[raw] - q[f"mean__{raw}"].iloc[0]) / q[f"sd__{raw}"].iloc[0]
            else:
                raise KeyError(feature)
            util += coef * np.asarray(values)
        probs = np.exp(util - util.max())
        probs /= probs.sum()
        z = choice[["destination_district", "destination_pcode"]].copy()
        z["probability"] = probs
        z = z.sort_values("probability", ascending=False).reset_index(drop=True)
        z["rank"] = np.arange(1, len(z) + 1)
        out[model] = z
    return fold, out


def polygon_rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return list(geom["coordinates"])
    if geom["type"] == "GeometryCollection":
        rings = []
        for part in geom["geometries"]:
            rings.extend(polygon_rings(part))
        return rings
    return []


def draw_story(geo, event, probs):
    W, H = 1900, 1120
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.text((70, 44), "A 2010 move from Faridpur to Manikganj", fill=NAVY, font=font(43, True))
    d.text((70, 102), "Anonymized BIHS household head · river-erosion land loss recorded as the reason", fill=MUTED, font=font(25))

    # Bangladesh district map.
    mx0, my0, mx1, my1 = 75, 190, 850, 875
    coords = []
    for feat in geo["features"]:
        for poly in polygon_rings(feat["geometry"]):
            coords += list(poly[0])
    minx, miny = np.min(coords, axis=0)
    maxx, maxy = np.max(coords, axis=0)
    scale = min((mx1 - mx0) / (maxx - minx), (my1 - my0) / (maxy - miny))
    ox = mx0 + ((mx1 - mx0) - (maxx - minx) * scale) / 2
    oy = my0 + ((my1 - my0) - (maxy - miny) * scale) / 2
    project = lambda xy: (ox + (xy[0] - minx) * scale, my1 - (oy - my0) - (xy[1] - miny) * scale)
    centers = {}
    for feat in geo["features"]:
        name = feat["properties"]["district"]
        fill = "#E8EEF2"
        if name == "Faridpur": fill = "#F3C7B5"
        if name == "Manikganj": fill = "#A6D8D7"
        allpts = []
        for poly in polygon_rings(feat["geometry"]):
            ring = [project(xy) for xy in poly[0]]
            allpts += ring
            d.polygon(ring, fill=fill, outline="#8FA0AD")
        centers[name] = (sum(x for x, _ in allpts) / len(allpts), sum(y for _, y in allpts) / len(allpts))
    a, b = centers["Faridpur"], centers["Manikganj"]
    d.line((a[0], a[1], b[0], b[1]), fill=RED, width=8)
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    ah = 18
    d.polygon([(b[0], b[1]), (b[0]-ah*math.cos(ang-.55), b[1]-ah*math.sin(ang-.55)),
               (b[0]-ah*math.cos(ang+.55), b[1]-ah*math.sin(ang+.55))], fill=RED)
    d.ellipse((a[0]-10, a[1]-10, a[0]+10, a[1]+10), fill=ORANGE)
    d.ellipse((b[0]-10, b[1]-10, b[0]+10, b[1]+10), fill=TEAL)
    d.text((a[0]-15, a[1]+18), "Faridpur", anchor="ra", fill=NAVY, font=font(19, True))
    d.text((b[0]+15, b[1]-18), "Manikganj", anchor="ld", fill=NAVY, font=font(19, True))

    # Human story and prediction comparison.
    sx = 930
    steps = [
        ("1", "Recorded loss", "The household reported losing land or homestead land to river erosion."),
        ("2", "Recorded move", "The household head moved from Faridpur to Manikganj."),
        ("3", "Candidate set", "The model compared Manikganj with all 63 other districts."),
    ]
    y = 190
    for num, title, body in steps:
        d.ellipse((sx, y, sx+54, y+54), fill=NAVY)
        d.text((sx+27, y+27), num, anchor="mm", fill="#FFFFFF", font=font(24, True))
        d.text((sx+75, y+3), title, fill=NAVY, font=font(26, True))
        lines = wrap(d, body, font(21), 720)
        for j, line in enumerate(lines):
            d.text((sx+75, y+38+j*28), line, fill=MUTED, font=font(21))
        y += 155

    labels = [("Gravity", probs["gravity_mle_disk_within"], ORANGE), ("Gravity + GIS", probs["gis_joint_ridge"], TEAL)]
    y0 = 700
    d.text((sx, y0-60), "Probability assigned to the observed destination", fill=NAVY, font=font(25, True))
    for i, (label, z, color) in enumerate(labels):
        row = z[z.destination_district == "Manikganj"].iloc[0]
        yy = y0 + i*105
        d.text((sx, yy), label, fill=NAVY, font=font(22, True))
        d.rectangle((sx+210, yy+2, sx+690, yy+35), fill="#E1E7EC")
        d.rectangle((sx+210, yy+2, sx+210+480*float(row.probability)/.16, yy+35), fill=color)
        d.text((sx+710, yy+18), f"{100*row.probability:.1f}% · rank {int(row['rank'])}", anchor="lm", fill=NAVY, font=font(21, True))
    d.text((sx, 955), "Adding district GIS raised Manikganj from 7.0% to 13.7% and from sixth to second.", fill=NAVY, font=font(22, True))
    d.text((sx, 995), "The score describes one recorded destination and cannot recover the household’s private reasoning.", fill=MUTED, font=font(19))
    img.save(F / "anonymized_household_destination_story.png", optimize=True)


def evidence_html(records):
    data = json.dumps(records, separators=(",", ":"))
    return f'''<div id="climate-evidence-explorer">
  <p class="kicker">Model checks</p>
  <h1>Does destination geography help on held-out moves?</h1>
  <p class="lede">Each dot compares two models on moves they did not train on. The baseline uses distance and population. The second model adds flood history, built surface, travel time to a city, and cropland. Positive values mean the second model gives more probability to the destinations people recorded.</p>
  <div class="viz-controls" aria-label="Evidence filters">
    <label class="form-label">Test split
      <select class="form-select" id="cee-validation">
        <option value="household_grouped_5fold">New households from represented origins</option>
        <option value="leave_one_origin_out">Every move from one unseen origin</option>
        <option value="wave_holdout_r3">Train in 2015, test in 2018–19</option>
      </select>
    </label>
    <label class="form-label">Candidate set
      <select class="form-select" id="cee-universe">
        <option value="full_64">All 64 districts, including the origin</option>
        <option value="interdistrict_63">The 63 districts outside the origin</option>
      </select>
    </label>
  </div>
  <div id="cee-chart"></div>
  <div class="text-small text-muted" id="cee-note" aria-live="polite"></div>
</div>
<style>
#climate-evidence-explorer {{ width:100%; color:var(--foreground); }}
#climate-evidence-explorer #cee-chart {{ width:100%; min-height:360px; }}
#climate-evidence-explorer .cee-label {{ fill:var(--foreground); font-size:12px; }}
#climate-evidence-explorer .cee-axis {{ fill:var(--muted-foreground); font-size:12px; }}
#climate-evidence-explorer .cee-grid {{ stroke:var(--border); stroke-width:1; }}
#climate-evidence-explorer .cee-zero {{ stroke:var(--foreground); stroke-width:1.5; }}
#climate-evidence-explorer .cee-ci {{ stroke-width:4; }}
#climate-evidence-explorer .cee-mark {{ stroke:var(--background); stroke-width:2; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script>
(() => {{
  const root = document.getElementById('climate-evidence-explorer');
  const validation = root.querySelector('#cee-validation');
  const universe = root.querySelector('#cee-universe');
  const chart = root.querySelector('#cee-chart');
  const note = root.querySelector('#cee-note');
  const data = {data};
  const label = d => d.sample_label.replace('BEMP ', '').replace('BIHS ', '');
  const color = d => d.dataset === 'BIHS' ? 'var(--viz-series-1)' : 'var(--viz-series-2)';
  function draw() {{
    const rows = data.filter(d => d.validation_scheme === validation.value && d.candidate_universe === universe.value);
    chart.replaceChildren();
    const width = Math.max(340, chart.getBoundingClientRect().width || 736);
    const height = Math.max(310, 88 + rows.length * 58);
    const margin = {{top:32,right:54,bottom:58,left:Math.min(285, Math.max(170,width*.36))}};
    const svg = d3.select(chart).append('svg').attr('viewBox',`0 0 ${{width}} ${{height}}`)
      .attr('role','img').attr('aria-label','GIS log-loss improvement over gravity by dataset and sample');
    svg.append('title').text('Held-out improvement from adding district GIS measures');
    svg.append('desc').text('Positive values mean the GIS model gives more probability to recorded destinations than the distance-and-population model.');
    const extent = d3.extent(rows.flatMap(d => [d.cluster_bootstrap_ci_low ?? d.log_loss_improvement_vs_gravity, d.cluster_bootstrap_ci_high ?? d.log_loss_improvement_vs_gravity,0]));
    const pad = Math.max(.04,(extent[1]-extent[0])*.16);
    const x = d3.scaleLinear().domain([extent[0]-pad,extent[1]+pad]).nice().range([margin.left,width-margin.right]);
    const y = d3.scaleBand().domain(rows.map(label)).range([margin.top,height-margin.bottom]).padding(.42);
    svg.append('g').selectAll('line').data(x.ticks(width < 500 ? 4 : 7)).join('line')
      .attr('class',d => Math.abs(d)<1e-12?'cee-zero':'cee-grid').attr('x1',x).attr('x2',x)
      .attr('y1',margin.top).attr('y2',height-margin.bottom);
    svg.append('g').selectAll('text').data(rows).join('text').attr('class','cee-label')
      .attr('x',margin.left-12).attr('y',d=>y(label(d))+y.bandwidth()/2+4).attr('text-anchor','end').text(label);
    svg.append('g').selectAll('line').data(rows.filter(d=>d.cluster_bootstrap_ci_low!==null)).join('line')
      .attr('class','cee-ci').attr('stroke',color).attr('x1',d=>x(d.cluster_bootstrap_ci_low))
      .attr('x2',d=>x(d.cluster_bootstrap_ci_high)).attr('y1',d=>y(label(d))+y.bandwidth()/2)
      .attr('y2',d=>y(label(d))+y.bandwidth()/2);
    svg.append('g').selectAll('circle').data(rows).join('circle').attr('class','cee-mark')
      .attr('fill',color).attr('cx',d=>x(d.log_loss_improvement_vs_gravity))
      .attr('cy',d=>y(label(d))+y.bandwidth()/2).attr('r',7)
      .attr('data-tooltip',d=>`${{label(d)}}: gain ${{d.log_loss_improvement_vs_gravity.toFixed(3)}}; ${{d.n_events_evaluated.toLocaleString()}} events`);
    const axis = d3.axisBottom(x).ticks(width < 500 ? 4 : 7).tickFormat(d3.format('.2f'));
    svg.append('g').attr('transform',`translate(0,${{height-margin.bottom}})`).call(axis)
      .call(g=>g.selectAll('text').attr('class','cee-axis')).call(g=>g.select('.domain').attr('stroke','var(--border)'));
    svg.append('text').attr('class','cee-label').attr('data-axis','x').attr('x',(margin.left+width-margin.right)/2)
      .attr('y',height-10).attr('text-anchor','middle').text('Held-out log-loss improvement over distance + population');
    if (rows.length === 0) {{
      svg.append('text').attr('class','cee-label').attr('x',width/2).attr('y',height/2).attr('text-anchor','middle').text('This split has no matching sample.');
    }}
    const positive = rows.filter(d=>d.log_loss_improvement_vs_gravity>0).length;
    note.textContent = rows.length ? `${{positive}} of ${{rows.length}} comparisons give recorded destinations more probability after GIS is added. Lines show 95% household-cluster bootstrap intervals when available.` : '';
  }}
  validation.addEventListener('change',draw); universe.addEventListener('change',draw);
  new ResizeObserver(draw).observe(chart); draw();
}})();
</script>'''


def journey_html(geo, prob_payload, event):
    geo_data = json.dumps(geo, separators=(",", ":"))
    pdata = json.dumps(prob_payload, separators=(",", ":"))
    return f'''<div id="household-journey-map">
  <p class="kicker">One recorded move</p>
  <h1>Faridpur to Manikganj after river erosion</h1>
  <p class="lede">BIHS records a household head who moved in 2010 after losing land or homestead land to river erosion. Select a model to see how it divides probability across all 64 districts. Darker districts receive more probability.</p>
  <div class="viz-controls" aria-label="Model selection">
    <button type="button" class="btn" data-model="gravity_mle_disk_within" aria-pressed="false">Distance + population</button>
    <button type="button" class="btn btn-primary" data-model="gis_joint_ridge" aria-pressed="true">Add four GIS measures</button>
  </div>
  <div id="hjm-map"></div>
  <div class="card" id="hjm-detail" aria-live="polite"></div>
</div>
<style>
#household-journey-map {{ width:100%; color:var(--foreground); }}
#household-journey-map #hjm-map {{ width:100%; min-height:420px; }}
#household-journey-map .hjm-district {{ stroke:var(--border); stroke-width:.7; }}
#household-journey-map .hjm-route {{ stroke:var(--destructive); stroke-width:2.5; fill:none; }}
#household-journey-map .hjm-label {{ fill:var(--foreground); font-size:12px; font-weight:500; }}
#household-journey-map .hjm-rank {{ fill:var(--foreground); font-size:11px; }}
#household-journey-map .hjm-origin {{ fill:var(--viz-series-2); }}
#household-journey-map .hjm-destination {{ fill:var(--viz-series-1); }}
</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<script>
(() => {{
  const root=document.getElementById('household-journey-map');
  const mapEl=root.querySelector('#hjm-map'); const detail=root.querySelector('#hjm-detail');
  const geo={geo_data}; const probs={pdata};
  let model='gis_joint_ridge';
  const origin='{event.origin_district}', destination='{event.destination_district}';
  function draw() {{
    const rows=probs[model]; const byName=new Map(rows.map(d=>[d.destination_district,d]));
    mapEl.replaceChildren(); const width=Math.max(320,mapEl.getBoundingClientRect().width||736); const height=Math.max(390,width*.63);
    const svg=d3.select(mapEl).append('svg').attr('viewBox',`0 0 ${{width}} ${{height}}`).attr('role','img')
      .attr('aria-label',`Bangladesh destination probabilities for an anonymized move from ${{origin}} to ${{destination}}`);
    svg.append('title').text('Probability across 64 candidate districts');
    svg.append('desc').text(`The household moved from ${{origin}} to ${{destination}} after reporting river-erosion land loss.`);
    const projection=d3.geoMercator().fitExtent([[18,14],[width-18,height-22]],geo); const path=d3.geoPath(projection);
    const maxP=d3.max(rows,d=>d.probability); const opacity=d3.scaleSqrt().domain([0,maxP]).range([.08,.82]);
    svg.selectAll('path.hjm-district').data(geo.features).join('path').attr('class','hjm-district')
      .attr('d',path).attr('fill',d=>`color-mix(in srgb, var(--viz-series-1) ${{Math.round(opacity(byName.get(d.properties.district)?.probability||0)*100)}}%, transparent)`)
      .attr('data-tooltip',d=>{{const r=byName.get(d.properties.district);return r ? `${{d.properties.district}}: ${{(100*r.probability).toFixed(1)}}%, rank ${{r.rank}}` : `${{d.properties.district}}: no model score`;}});
    const centers=new Map(geo.features.map(f=>[f.properties.district,path.centroid(f)])); const a=centers.get(origin), b=centers.get(destination);
    svg.append('defs').append('marker').attr('id','hjm-arrow').attr('viewBox','0 -5 10 10').attr('refX',8).attr('refY',0)
      .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto').append('path').attr('d','M0,-5L10,0L0,5').attr('fill','var(--destructive)');
    svg.append('line').attr('class','hjm-route').attr('x1',a[0]).attr('y1',a[1]).attr('x2',b[0]).attr('y2',b[1]).attr('marker-end','url(#hjm-arrow)');
    svg.append('circle').attr('class','hjm-origin').attr('cx',a[0]).attr('cy',a[1]).attr('r',6);
    svg.append('circle').attr('class','hjm-destination').attr('cx',b[0]).attr('cy',b[1]).attr('r',7);
    svg.append('text').attr('class','hjm-label').attr('x',a[0]-8).attr('y',a[1]+18).attr('text-anchor','end').text(origin);
    svg.append('text').attr('class','hjm-label').attr('x',b[0]+8).attr('y',b[1]-12).text(destination);
    const chosen=byName.get(destination), top=rows[0];
    const modelLabel=model==='gis_joint_ridge'?'Distance + population + four GIS measures':'Distance + population';
    detail.innerHTML=`<strong>${{modelLabel}}</strong> gives Manikganj <strong>${{(100*chosen.probability).toFixed(1)}}%</strong> probability. It ranks <strong>${{chosen.rank}}</strong> of 64 districts. The model's first choice is <strong>${{top.destination_district}}</strong>.`;
  }}
  root.querySelectorAll('button[data-model]').forEach(btn=>btn.addEventListener('click',()=>{{
    model=btn.dataset.model; root.querySelectorAll('button[data-model]').forEach(b=>{{const on=b===btn;b.setAttribute('aria-pressed',on);b.classList.toggle('btn-primary',on);}}); draw();
  }}));
  new ResizeObserver(draw).observe(mapEl); draw();
}})();
</script>'''


def main():
    geo = simplified_geometry()
    draw_forest()
    draw_transport()
    event_id = "BIHS-B4-W2-0053"
    event = pd.read_csv(T / "bihs_household_relocation_events.csv").set_index("event_id").loc[event_id]
    _, probs = event_probabilities(event_id)
    prob_payload = {k: v[["destination_district", "destination_pcode", "probability", "rank"]].to_dict("records") for k, v in probs.items()}
    draw_story(geo, event, probs)

    evidence = pd.read_csv(T / "cross_dataset_replication_summary.csv")
    evidence_records = json.loads(evidence[["dataset", "sample_label", "candidate_universe", "validation_scheme",
                                            "n_events_evaluated", "log_loss_improvement_vs_gravity",
                                            "cluster_bootstrap_ci_low", "cluster_bootstrap_ci_high"]].to_json(orient="records"))
    (V / "climate-mobility-evidence.html").write_text(evidence_html(evidence_records))
    (V / "one-household-journey.html").write_text(journey_html(geo, prob_payload, event))
    print(F / "cross_dataset_gis_gain_forest.png")
    print(F / "validation_transportability_comparison.png")
    print(F / "anonymized_household_destination_story.png")
    print(V / "climate-mobility-evidence.html")
    print(V / "one-household-journey.html")


if __name__ == "__main__":
    main()
