#!/usr/bin/env python3
"""Audit frozen manuscript claims and the public release boundary."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "publication"
QA = PUB / "qa"
TABLES = ROOT / "outputs" / "tables"
AUDIT = QA / "final_release_audit.csv"
MANIFEST = QA / "public_release_manifest.csv"

BANNED = [
    "delve", "foster", "leverage", "utilize", "facilitate", "empower",
    "streamline", "robust", "cutting-edge", "paradigm shift", "game changer",
    "this is huge", "this changes everything", "tapestry", "realm", "beacon",
    "multifaceted", "meticulous", "intricate", "paramount", "transformative",
    "elevate", "embark", "supercharge", "harness", "ever-evolving",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(rows, check_id, condition, evidence, source):
    rows.append({
        "check_id": check_id,
        "status": "PASS" if condition else "FAIL",
        "evidence": str(evidence),
        "source": str(source),
    })


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    rows = []

    registry_path = QA / "manuscript_number_registry.csv"
    summary_path = TABLES / "cross_dataset_replication_summary.csv"
    registry = pd.read_csv(registry_path)
    summary = pd.read_csv(summary_path)

    for _, claim in registry[registry.claim_id.str.startswith("C")].iterrows():
        z = summary[
            summary.dataset.eq(claim.dataset)
            & summary["sample"].eq(claim["sample"])
            & summary.candidate_universe.eq(claim.candidate_universe)
            & summary.validation_scheme.eq(claim.validation_scheme)
        ]
        ok = len(z) == 1
        if ok:
            x = z.iloc[0]
            expected_ci = ""
            if pd.notna(x.cluster_bootstrap_ci_low):
                expected_ci = f"[{x.cluster_bootstrap_ci_low:.3f}, {x.cluster_bootstrap_ci_high:.3f}]"
            ok = all([
                int(claim.n_events) == int(x.n_events_evaluated),
                abs(float(claim.gravity_log_loss) - round(float(x.gravity_mean_log_loss), 3)) < 1e-12,
                abs(float(claim.gis_log_loss) - round(float(x.mean_log_loss), 3)) < 1e-12,
                abs(float(claim.gis_gain) - round(float(x.log_loss_improvement_vs_gravity), 3)) < 1e-12,
                ("" if pd.isna(claim.cluster_95_interval) else claim.cluster_95_interval) == expected_ci,
            ])
        check(rows, f"registry_{claim.claim_id}", ok, "registry row matches frozen summary", summary_path.relative_to(ROOT))

    prediction_path = TABLES / "bihs_replication_oof_predictions_grouped.csv"
    if prediction_path.exists():
        predictions = pd.read_csv(prediction_path, low_memory=False)
        z = predictions[
            predictions.event_id.eq("BIHS-B4-W2-0053")
            & predictions["sample"].eq("b4_erosion")
            & predictions.candidate_universe.eq("full_64")
        ]
        for claim_id, model in [("H01", "gravity_mle_disk_within"), ("H02", "gis_joint_ridge")]:
            source_row = z[z.model.eq(model)]
            claim = registry[registry.claim_id.eq(claim_id)].iloc[0]
            ok = len(source_row) == 1
            if ok:
                x = source_row.iloc[0]
                ok = (
                    claim.chosen_probability == f"{100 * x.chosen_probability:.1f}%"
                    and int(claim.chosen_rank) == int(x.chosen_expected_rank)
                )
            check(rows, f"registry_{claim_id}", ok, "household score matches held-out prediction", prediction_path.relative_to(ROOT))

    migration_path = TABLES / "bihs_internal_migration_events.csv"
    if migration_path.exists():
        events = pd.read_csv(migration_path, low_memory=False)
        primary = events[events.primary_interval_sample.eq(True)]
        helped = int(primary.destination_help_label.eq("Friends/family in the migrated location").sum())
        claim = registry[registry.claim_id.eq("N01")].iloc[0]
        ok = int(claim.n_events) == len(primary) and int(claim.network_help_count) == helped
        check(rows, "registry_N01", ok, f"{helped} of {len(primary)}", migration_path.relative_to(ROOT))

    manuscript = (PUB / "manuscript" / "manuscript.md").read_text(encoding="utf-8")
    claim_sheet = (PUB / "claim_sheet.md").read_text(encoding="utf-8")
    explainer = (PUB / "public_explainer.md").read_text(encoding="utf-8")
    public_prose = "\n".join([manuscript, claim_sheet, explainer])

    required_claims = {
        "bemp_main": ["184", "1.630", "1.522", "0.108", "[0.023, 0.189]"],
        "bihs_erosion": ["123", "2.563", "2.465", "0.098", "[0.028, 0.163]"],
        "wide_origin": ["1,857", "1,208", "0.101", "0.107"],
        "household": ["7.0%", "13.7%", "ranked it sixth", "ranked it second"],
        "network": ["1,815", "1,857"],
    }
    for name, tokens in required_claims.items():
        missing = [token for token in tokens if token not in manuscript]
        check(rows, f"manuscript_{name}", not missing, "missing=" + ";".join(missing), "publication/manuscript/manuscript.md")

    lower = public_prose.lower()
    hits = [term for term in BANNED if re.search(rf"\b{re.escape(term)}\b", lower)]
    check(rows, "prose_banned_terms", not hits, "hits=" + ";".join(hits), "publication/*.md")

    for doc in [
        PUB / "manuscript" / "bangladesh_climate_destination_choice_manuscript.a11y.json",
        PUB / "bangladesh_climate_destination_choice_claim_sheet.a11y.json",
    ]:
        text = doc.read_text(encoding="utf-8")
        ok = all(token in text for token in ['"high": 0', '"medium": 0', '"low": 0'])
        check(rows, f"a11y_{doc.stem}", ok, "zero reported issues", doc.relative_to(ROOT))

    pptx = PUB / "presentation" / "bangladesh_climate_destination_choice_7_slide_presentation.pptx"
    with zipfile.ZipFile(pptx) as zf:
        slides = [n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    check(rows, "presentation_slide_count", len(slides) == 7, len(slides), pptx.relative_to(ROOT))

    protected = [
        "data/raw", "data/external", "event_ledger", "internal_migration_events",
        "oof_predictions", "choice_set", "fold_parameters", "split_audit",
    ]
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.splitlines()
    violations = [
        p for p in tracked
        if (p.startswith("data/") or p.startswith("outputs/tables/") or p.startswith("work/"))
        and any(term in p.lower() for term in protected)
    ]
    check(rows, "public_release_boundary", not violations, ";".join(violations), ".gitignore and git index")

    audit_df = pd.DataFrame(rows)
    audit_df.to_csv(AUDIT, index=False)

    release_roots = [ROOT / "README.md", ROOT / "DATA_ACCESS.md", ROOT / "REPRODUCIBILITY.md", PUB, ROOT / "docs", ROOT / "outputs" / "figures"]
    files = []
    for item in release_roots:
        if item.is_file():
            files.append(item)
        elif item.exists():
            files.extend(p for p in item.rglob("*") if p.is_file() and ".DS_Store" not in p.name)
    manifest_rows = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted(set(files))]
    pd.DataFrame(manifest_rows).to_csv(MANIFEST, index=False)

    failed = audit_df[audit_df.status.ne("PASS")]
    print(audit_df.to_string(index=False))
    print(f"\nAudit: {len(audit_df) - len(failed)}/{len(audit_df)} checks passed")
    print(f"Manifest: {len(manifest_rows)} files")
    if len(failed):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
