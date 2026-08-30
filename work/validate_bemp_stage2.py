#!/usr/bin/env python3
"""Validate and freeze BEMP Stage 2 benchmark artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs/tables"


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    d = pd.read_csv(TABLES / "bgd_district_universe.csv")
    od = pd.read_csv(TABLES / "bgd_origin_destination_matrix.csv")
    c = pd.read_csv(TABLES / "bemp_stage2_event_choice_set.csv", low_memory=False)
    r = pd.read_csv(TABLES / "bemp_baseline_benchmark_results.csv")
    p = pd.read_csv(TABLES / "bemp_baseline_parameter_estimates.csv")
    oof = pd.read_csv(TABLES / "bemp_baseline_oof_event_predictions.csv")
    s = pd.read_csv(TABLES / "bemp_stage2_source_manifest.csv")

    checks = []

    def add(check, passed, observed, expected):
        checks.append(
            {"check": check, "passed": bool(passed), "observed": str(observed), "expected": str(expected)}
        )

    add("district row count", len(d) == 64, len(d), 64)
    add("district names unique", d.district.is_unique, d.district.nunique(), 64)
    add("district P-codes unique", d.district_pcode.is_unique, d.district_pcode.nunique(), 64)
    add("district population complete", d.population_2022_total.notna().all(), d.population_2022_total.notna().sum(), 64)
    add("district population sums to BBS national enumerated total", d.population_2022_total.sum() == 165158616, int(d.population_2022_total.sum()), 165158616)
    add("district coordinates within Bangladesh envelope", d.central_lon.between(87.5, 93.0).all() and d.central_lat.between(20.0, 27.0).all(), "all in bounds", "all in bounds")
    add("district areas positive", d.area_km2_approx.gt(0).all(), float(d.area_km2_approx.min()), ">0")
    add("district area total plausible", 120000 < d.area_km2_approx.sum() < 160000, round(d.area_km2_approx.sum(), 1), "120,000-160,000 km2")
    add("within-district distances positive", d.within_district_mean_pair_km_mc.gt(0).all(), float(d.within_district_mean_pair_km_mc.min()), ">0")

    add("origin-destination row count", len(od) == 4096, len(od), 4096)
    add("origin-destination keys unique", not od.duplicated(["origin_district", "destination_district"]).any(), int(od.duplicated(["origin_district", "destination_district"]).sum()), 0)
    add("64 alternatives per origin", od.groupby("origin_district").size().eq(64).all(), od.groupby("origin_district").size().min(), 64)
    add("64 diagonal alternatives", int(od.same_district.sum()) == 64, int(od.same_district.sum()), 64)
    add("all effective distances positive", od.effective_distance_km.gt(0).all(), float(od.effective_distance_km.min()), ">0")
    add("all radiation scores positive", od.radiation_score_adapted.gt(0).all(), float(od.radiation_score_adapted.min()), ">0")
    add("no missing OD fields", od.notna().all().all(), int(od.isna().sum().sum()), 0)

    add("choice row count", len(c) == 573 * 64, len(c), 36672)
    add("choice event count", c.event_id.nunique() == 573, c.event_id.nunique(), 573)
    add("64 candidates per event", c.groupby("event_id").size().eq(64).all(), c.groupby("event_id").size().min(), 64)
    add("one chosen candidate per event", c.groupby("event_id").chosen.sum().eq(1).all(), c.groupby("event_id").chosen.sum().value_counts().to_dict(), "all 1")
    add("seven origin districts", c.origin_district.nunique() == 7, c.origin_district.nunique(), 7)
    add("37 observed destination districts", c.loc[c.chosen, "destination_district"].nunique() == 37, c.loc[c.chosen, "destination_district"].nunique(), 37)
    add("reported chosen distance excluded from feature table", "distance_from_previous_location_m" not in c.columns, "absent" if "distance_from_previous_location_m" not in c.columns else "present", "absent")
    leak_terms = ["reason_", "relatives", "safer_", "return_plan", "better_earning"]
    leaks = [col for col in c.columns if any(term in col for term in leak_terms)]
    add("obvious post-choice fields excluded", not leaks, leaks, [])

    add("benchmark result row count", len(r) == 240, len(r), 240)
    add("all model folds converged", r.all_folds_converged.astype(bool).all(), int(r.all_folds_converged.astype(bool).sum()), len(r))
    add("benchmark numeric fields complete", r.select_dtypes("number").notna().all().all(), int(r.select_dtypes("number").isna().sum().sum()), 0)
    bounded = ["top1_accuracy", "top3_accuracy", "top5_accuracy", "mean_reciprocal_rank"]
    add("probability metrics bounded", r[bounded].ge(0).all().all() and r[bounded].le(1).all().all(), "all within [0,1]", "all within [0,1]")
    add("top-k metrics monotone", (r.top1_accuracy <= r.top3_accuracy).all() and (r.top3_accuracy <= r.top5_accuracy).all(), "all monotone", "all monotone")
    add("parameter estimates present", len(p) == 1484, len(p), 1484)
    add("OOF prediction row count", len(oof) == 6260, len(oof), 6260)
    add("OOF prediction keys unique", not oof.duplicated(["sample", "candidate_universe", "model", "event_id"]).any(), int(oof.duplicated(["sample", "candidate_universe", "model", "event_id"]).sum()), 0)
    add("OOF chosen probabilities valid", oof.chosen_probability.gt(0).all() and oof.chosen_probability.le(1).all(), "all in (0,1]", "all in (0,1]")
    add("OOF ranks valid", oof.chosen_expected_rank.ge(1).all() and (oof.chosen_expected_rank <= oof.candidate_count).all(), "all within candidate set", "all within candidate set")

    source_hash_ok = True
    source_details = []
    for row in s.itertuples(index=False):
        if not isinstance(row.local_path, str) or not row.local_path or pd.isna(row.sha256):
            continue
        path = ROOT / row.local_path
        ok = path.exists() and hash_file(path) == row.sha256
        source_hash_ok &= ok
        source_details.append(f"{row.source_id}:{'ok' if ok else 'FAIL'}")
    add("source file hashes match manifest", source_hash_ok, "; ".join(source_details), "all ok")

    validation = pd.DataFrame(checks)
    validation.to_csv(TABLES / "bemp_stage2_validation.csv", index=False)

    core_files = [
        "bgd_district_universe.csv", "bgd_district_name_crosswalk.csv",
        "bgd_origin_destination_matrix.csv", "bemp_stage2_event_choice_set.csv",
        "bemp_baseline_benchmark_results.csv", "bemp_baseline_parameter_estimates.csv",
        "bemp_baseline_oof_event_predictions.csv",
        "bemp_distance_proxy_validation.csv", "bemp_stage2_source_manifest.csv",
        "../reports/bemp_stage2_baseline_design.md",
        "../figures/bemp_stage2_climate_destination_support.png",
    ]
    manifest_rows = []
    for rel in core_files:
        path = (TABLES / rel).resolve()
        record = {
            "relative_path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": hash_file(path),
            "rows": "",
            "columns": "",
        }
        if path.suffix == ".csv":
            frame = pd.read_csv(path, low_memory=False)
            record["rows"] = len(frame)
            record["columns"] = len(frame.columns)
        manifest_rows.append(record)
    pd.DataFrame(manifest_rows).to_csv(TABLES / "bemp_stage2_freeze_manifest.csv", index=False)

    failed = validation[~validation.passed]
    print(validation.to_string(index=False))
    print(f"\n{len(validation) - len(failed)}/{len(validation)} checks passed")
    if len(failed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
