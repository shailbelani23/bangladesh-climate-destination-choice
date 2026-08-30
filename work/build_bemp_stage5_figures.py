#!/usr/bin/env python3
"""Publication-style static Stage-5 figures using Pillow."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)


def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def logloss_figure():
    r = pd.read_csv(TABLES / "bemp_stage5_model_results.csv")
    x = r[(r["sample"] == "household_lagged_shock_yes") & (r.candidate_universe == "full_64")]
    models = [
        ("gravity_mle_disk_within", "Gravity", "#6B7280"),
        ("gis_joint_ridge", "Direct GIS", "#0F766E"),
        ("nested_gis_ridge", "Nested GIS", "#D97706"),
    ]
    schemes = [
        ("household_grouped_5fold", "Household 5-fold"),
        ("location_grouped_5fold", "Location 5-fold"),
        ("leave_one_origin_out", "Leave one origin out"),
        ("temporal_w12plus_holdout", "Temporal holdout"),
    ]
    W, H = 1800, 980
    img = Image.new("RGB", (W, H), "#FBFCFE")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "GIS improves prediction within observed origins, not for an unseen origin",
           fill="#15263C", font=font(38, True))
    d.text((70, 98), "184 shock-linked household relocations; lower out-of-fold log loss is better",
           fill="#52677E", font=font(23))
    left, top, right, bottom = 150, 190, 1730, 800
    ymax = 2.15
    for tick in [0, .5, 1.0, 1.5, 2.0]:
        y = bottom - (tick / ymax) * (bottom - top)
        d.line((left, y, right, y), fill="#DDE3EA", width=2)
        d.text((65, y - 14), f"{tick:.1f}", fill="#52677E", font=font(20))
    group_w = (right - left) / len(schemes)
    bar_w = 88
    offsets = [-105, 0, 105]
    for si, (scheme, label) in enumerate(schemes):
        center = left + group_w * (si + .5)
        for off, (model, mlabel, color) in zip(offsets, models):
            v = float(x[(x.validation_scheme == scheme) & (x.model == model)].mean_log_loss.iloc[0])
            y = bottom - (v / ymax) * (bottom - top)
            d.rounded_rectangle((center + off - bar_w/2, y, center + off + bar_w/2, bottom),
                                radius=8, fill=color)
            d.text((center + off, y - 32), f"{v:.2f}", anchor="mm", fill="#273B52", font=font(19, True))
        d.text((center, bottom + 45), label, anchor="mm", fill="#273B52", font=font(21, True))
    d.text((40, 480), "Log loss", fill="#273B52", font=font(22, True))
    lx = 520
    for model, label, color in models:
        d.rounded_rectangle((lx, 895, lx + 30, 925), radius=5, fill=color)
        d.text((lx + 42, 910), label, anchor="lm", fill="#273B52", font=font(21))
        lx += 260
    img.save(FIGURES / "bemp_stage5_validation_logloss.png", optimize=True)


def coefficient_figure():
    b = pd.read_csv(TABLES / "bemp_stage5_parameter_bootstrap.csv")
    b = b[(b["sample"] == "household_lagged_shock_yes") & (b.candidate_universe == "full_64")]
    specs = [
        ("z_gfd_flood", "Historical flood exposure"),
        ("z_ghsl_built", "Built-surface share"),
        ("z_access_time", "Travel time to city (50,000+)"),
        ("z_cropland", "Cropland share"),
    ]
    W, H = 1500, 850
    img = Image.new("RGB", (W, H), "#FBFCFE")
    d = ImageDraw.Draw(img)
    d.text((65, 42), "Climate-sample destination coefficients", fill="#15263C", font=font(40, True))
    d.text((65, 96), "Ridge conditional logit; 95% household-cluster bootstrap intervals",
           fill="#52677E", font=font(23))
    left, right, top, bottom = 560, 1410, 180, 720
    xmin, xmax = -6.4, 1.8
    def px(v): return left + (v - xmin) / (xmax - xmin) * (right - left)
    for tick in [-6, -4, -2, 0, 1]:
        x = px(tick)
        d.line((x, top, x, bottom), fill="#DDE3EA" if tick != 0 else "#98A2B3", width=2)
        d.text((x, bottom + 30), str(tick), anchor="mm", fill="#52677E", font=font(20))
    ys = [235, 365, 495, 625]
    for (feature, label), y in zip(specs, ys):
        rr = b[b.feature == feature].iloc[0]
        est, lo, hi = float(rr.full_sample_estimate), float(rr.bootstrap_ci_low), float(rr.bootstrap_ci_high)
        d.text((520, y), label, anchor="rm", fill="#273B52", font=font(23, True))
        d.line((px(lo), y, px(hi), y), fill="#334155", width=5)
        d.line((px(lo), y-11, px(lo), y+11), fill="#334155", width=4)
        d.line((px(hi), y-11, px(hi), y+11), fill="#334155", width=4)
        d.ellipse((px(est)-10, y-10, px(est)+10, y+10), fill="#0F766E")
        d.text((px(hi)+12, y), f"{est:.2f} [{lo:.2f}, {hi:.2f}]", anchor="lm",
               fill="#273B52", font=font(18))
    d.text(((left+right)/2, 800), "Coefficient per one destination standard deviation",
           anchor="mm", fill="#273B52", font=font(22, True))
    img.save(FIGURES / "bemp_stage5_climate_gis_coefficients.png", optimize=True)


def main():
    logloss_figure()
    coefficient_figure()
    print(FIGURES / "bemp_stage5_validation_logloss.png")
    print(FIGURES / "bemp_stage5_climate_gis_coefficients.png")


if __name__ == "__main__":
    main()
