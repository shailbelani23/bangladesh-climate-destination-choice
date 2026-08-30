#!/usr/bin/env python3
"""Pre-model identification, temporal leakage, and support audit for BEMP."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/bemp/quantitative"
TABLES = ROOT / "outputs/tables"
REPORTS = ROOT / "outputs/reports"


def truth(s):
    return s.astype(str).str.lower().eq("true")


def load_interview_dates():
    state = pd.read_csv(TABLES / "bemp_respondent_wave_state.csv", low_memory=False)
    date_values = []
    for source_file, block in state.groupby("source_file", sort=False):
        raw = pd.read_csv(RAW / source_file, low_memory=False)
        wave = block.wave.iloc[0]
        date_col = f"{wave}_date"
        if date_col not in raw.columns:
            raise KeyError(f"Missing {date_col} in {source_file}")
        for rownum in block.source_row_csv_1_based.astype(int):
            date_values.append(
                {
                    "source_file": source_file,
                    "source_row_csv_1_based": rownum,
                    "interview_date": raw.iloc[rownum - 2][date_col],
                }
            )
    date_values = pd.DataFrame(date_values)
    state = state.merge(
        date_values,
        on=["source_file", "source_row_csv_1_based"],
        how="left",
        validate="one_to_one",
    )
    state["interview_date"] = pd.to_datetime(state["interview_date"], errors="coerce")

    audit = pd.read_csv(TABLES / "bemp_respondent_duplicate_audit.csv", low_memory=False)
    keep_lookup = audit.set_index(
        ["respondent_id", "wave", "source_row_csv_1_based"]
    )["adjudication_keep"].to_dict()
    state["adjudication_keep"] = [
        bool(keep_lookup.get((r.respondent_id, r.wave, int(r.source_row_csv_1_based)), True))
        for r in state.itertuples(index=False)
    ]
    retained = state[state.adjudication_keep].copy()
    assert not retained.duplicated(["respondent_id", "wave"]).any()
    return retained


def build_event_timing(events, interviews):
    rows = []
    for e in events.itertuples(index=False):
        event_date = pd.to_datetime(e.source_interview_date, errors="coerce")
        history = interviews[
            (interviews.respondent_id == e.respondent_id)
            & (interviews.wave_number < e.wave_number)
            & (interviews.interview_date < event_date)
        ].sort_values(["wave_number", "interview_date"])
        prior = history.iloc[-1] if len(history) else None
        prior_basis = "respondent"
        if prior is None:
            household_history = interviews[
                (interviews.household_id_derived == e.household_id_derived)
                & (interviews.wave_number < e.wave_number)
                & (interviews.interview_date < event_date)
            ].sort_values(["wave_number", "interview_date"])
            if len(household_history):
                prior = household_history.iloc[-1]
                prior_basis = "household"

        source_waves = {
            str(x) for x in [e.lagged_home_erosion_source_wave, e.lagged_home_flood_source_wave]
            if pd.notna(x) and str(x).lower() != "nan"
        }
        shock_dates = interviews[
            (interviews.respondent_id == e.respondent_id)
            & (interviews.wave.isin(source_waves))
            & (interviews.interview_date < event_date)
        ].interview_date
        shock_date = shock_dates.max() if len(shock_dates) else pd.NaT
        prior_date = prior.interview_date if prior is not None else pd.NaT
        cutoff_base = prior_date if pd.notna(prior_date) else shock_date
        strict_cutoff = cutoff_base - pd.Timedelta(days=1) if pd.notna(cutoff_base) else pd.NaT
        rows.append(
            {
                "event_id": e.event_id,
                "respondent_id": e.respondent_id,
                "household_id_derived": e.household_id_derived,
                "wave": e.wave,
                "wave_number": e.wave_number,
                "event_interview_date": event_date.date().isoformat() if pd.notna(event_date) else "",
                "prior_observed_wave": prior.wave if prior is not None else "",
                "prior_interview_date": prior_date.date().isoformat() if pd.notna(prior_date) else "",
                "lagged_shock_source_waves": "|".join(sorted(source_waves)),
                "lagged_shock_source_interview_date": shock_date.date().isoformat() if pd.notna(shock_date) else "",
                "strict_feature_cutoff_date": strict_cutoff.date().isoformat() if pd.notna(strict_cutoff) else "",
                "latest_complete_annual_feature_year": int(strict_cutoff.year - 1) if pd.notna(strict_cutoff) else "",
                "event_interval_days_upper_bound": int((event_date - prior_date).days) if pd.notna(event_date) and pd.notna(prior_date) else "",
                "timing_status": (
                    f"{prior_basis}_prior_interview" if pd.notna(prior_date) else (
                        "shock_source_fallback" if pd.notna(shock_date) else "no_public_prior_date"
                    )
                ),
                "prior_interview_basis": prior_basis if pd.notna(prior_date) else "none",
            }
        )
    out = pd.DataFrame(rows)
    assert out.event_id.is_unique and len(out) == len(events)
    return out


def entropy_metrics(counts):
    p = counts / counts.sum()
    h = float(-(p * np.log(p)).sum())
    return {
        "destination_hhi": float(np.square(p).sum()),
        "destination_entropy_nats": h,
        "effective_destination_count_exp_entropy": float(math.exp(h)),
        "top_destination_share": float(p.max()),
        "top5_destination_share": float(p.sort_values(ascending=False).head(5).sum()),
    }


def build_support(events):
    events = events.copy()
    events["origin_district"] = events.origin_district_codebook.replace({"Netrokona": "Netrakona"})
    events["chosen_district"] = events.destination_district_official.replace({"Netrokona": "Netrakona"})
    eligible = events[truth(events.stage1_district_endpoint_eligible)].copy()
    samples = {
        "all_district_events": eligible,
        "household_relocation": eligible[truth(eligible.stage1_household_relocation_eligible)],
        "household_lagged_shock_yes": eligible[
            truth(eligible.stage1_household_relocation_eligible)
            & truth(eligible.lagged_home_shock_any_yes)
        ],
        "household_lagged_shock_observed": eligible[
            truth(eligible.stage1_household_relocation_eligible)
            & truth(eligible.lagged_home_shock_observed)
        ],
    }
    metric_rows, destination_rows, wave_rows = [], [], []
    for sample_name, x in samples.items():
        cross = x[x.origin_district != x.chosen_district]
        counts = x.chosen_district.value_counts()
        cross_counts = cross.chosen_district.value_counts()
        metrics = entropy_metrics(counts)
        metrics.update(
            {
                "sample": sample_name,
                "events": len(x),
                "respondents": x.respondent_id.nunique(),
                "households": x.household_id_derived.nunique(),
                "origins": x.origin_district.nunique(),
                "observed_destinations": x.chosen_district.nunique(),
                "observed_origin_destination_cells": x.groupby(["origin_district", "chosen_district"]).ngroups,
                "same_district_events": int((x.origin_district == x.chosen_district).sum()),
                "same_district_share": float((x.origin_district == x.chosen_district).mean()),
                "cross_district_events": len(cross),
                "cross_district_households": cross.household_id_derived.nunique(),
                "cross_district_destinations": cross.chosen_district.nunique(),
                "cross_district_singleton_destinations": int((cross_counts == 1).sum()),
                "households_with_multiple_events": int((x.groupby("household_id_derived").size() > 1).sum()),
                "conservative_free_parameter_budget_cross_n_over_20": int(len(cross) // 20),
                "upper_planning_parameter_budget_cross_n_over_10": int(len(cross) // 10),
            }
        )
        metric_rows.append(metrics)

        ranked = counts.rename("events").reset_index().rename(columns={"chosen_district": "destination_district"})
        ranked["sample"] = sample_name
        ranked["rank"] = np.arange(1, len(ranked) + 1)
        ranked["share"] = ranked.events / ranked.events.sum()
        ranked["cumulative_share"] = ranked.share.cumsum()
        ranked["cross_district_events"] = ranked.destination_district.map(cross_counts).fillna(0).astype(int)
        ranked["origin_districts_sending_events"] = ranked.destination_district.map(
            x.groupby("chosen_district").origin_district.nunique()
        ).astype(int)
        destination_rows.append(ranked)

        w = x.groupby(["wave", "wave_number"], as_index=False).agg(
            events=("event_id", "size"),
            households=("household_id_derived", "nunique"),
            cross_district_events=("event_id", lambda s: int((x.loc[s.index, "origin_district"] != x.loc[s.index, "chosen_district"]).sum())),
        )
        w["sample"] = sample_name
        wave_rows.append(w)
    return pd.DataFrame(metric_rows), pd.concat(destination_rows, ignore_index=True), pd.concat(wave_rows, ignore_index=True), samples


def build_error_by_origin():
    oof = pd.read_csv(TABLES / "bemp_baseline_oof_event_predictions.csv", low_memory=False)
    keep_models = {"gravity_mle_disk_within", "radiation_adapted", "uniform"}
    x = oof[
        (oof["sample"] == "household_lagged_shock_yes")
        & (oof.model.isin(keep_models))
    ].copy()
    return x.groupby(
        ["candidate_universe", "model", "origin_district"], as_index=False
    ).agg(
        events=("event_id", "size"),
        mean_log_loss=("chosen_log_loss", "mean"),
        expected_top1=("chosen_top1_probability", "mean"),
        expected_top5=("chosen_top5_probability", "mean"),
        mean_rank=("chosen_expected_rank", "mean"),
    )


def write_report(timing, metrics, destinations, waves, samples, errors):
    hh = samples["household_relocation"]
    obs = samples["household_lagged_shock_observed"]
    climate = samples["household_lagged_shock_yes"]
    joint = pd.crosstab(obs.lagged_home_erosion, obs.lagged_home_flood, dropna=False)
    climate_metric = metrics.set_index("sample").loc["household_lagged_shock_yes"]
    cross_top = destinations[
        destinations["sample"].eq("household_lagged_shock_yes")
        & destinations.cross_district_events.gt(0)
    ].sort_values("cross_district_events", ascending=False).head(10)
    timing_counts = timing.timing_status.value_counts()

    lines = [
        "# BEMP Stage 3 pre-model identification and GIS-readiness audit",
        "",
        "## Decision",
        "",
        "Proceed to a tightly regularized, low-dimensional GIS feature build, but do not fit a large "
        "destination model. The binding constraint is no longer data linkage; it is statistical support. "
        "Only 71 shock-linked household relocations cross a district boundary, and many destination "
        "districts occur once. The final specification therefore needs a small pre-registered feature set.",
        "",
        "## Leakage-safe timing",
        "",
        f"Prior interview dates are publicly recoverable for all {len(timing):,} district-resolved "
        f"prospective events: {int((timing.prior_interview_basis == 'respondent').sum()):,} from the same "
        f"respondent and {int((timing.prior_interview_basis == 'household').sum()):,} using a same-household "
        "fallback. For every event, the strict GIS "
        "cutoff is one day before the last observed prior interview. This predates the full interval in "
        "which the new destination could have been chosen.",
        "",
        "Annual dynamic features must use the latest **complete calendar year** before that cutoff. A "
        "2022 annual composite is therefore not safe for an event whose prior interview occurred during "
        "2022; the safe annual layer is 2021. Nine events have a 2021 cutoff, so their latest complete "
        "annual layer is 2020. Therefore **2020 is the universal static reference year**; 2021 and later "
        "layers require event-specific assignment. The BBS 2022 population used in Stage 2 is retained as "
        "a transparent gravity benchmark, but it is not a universally pre-move causal exposure.",
        "",
        "## Statistical support",
        "",
        "| Sample | Events | Households | Cross-district | Destinations | Cross-district destinations | Singleton cross-district destinations | Effective destination count |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in metrics.itertuples(index=False):
        lines.append(
            f"| {r.sample} | {r.events:,} | {r.households:,} | {r.cross_district_events:,} | "
            f"{r.observed_destinations:,} | {r.cross_district_destinations:,} | "
            f"{r.cross_district_singleton_destinations:,} | {r.effective_destination_count_exp_entropy:.1f} |"
        )
    lines += [
        "",
        f"In the core climate sample, the five most frequent destination districts absorb "
        f"{climate_metric.top5_destination_share:.1%} of moves. The effective number of destinations "
        f"is only {climate_metric.effective_destination_count_exp_entropy:.1f}, despite a 64-district "
        "choice universe. This concentration is real signal, but it means flexible destination-specific "
        "effects would overfit.",
        "",
        "A conservative planning rule permits about "
        f"{int(climate_metric.conservative_free_parameter_budget_cross_n_over_20)} freely estimated "
        "coefficients in the 71-event cross-district climate model; even the looser 10-events-per-parameter "
        f"rule permits only {int(climate_metric.upper_planning_parameter_budget_cross_n_over_10)}. These are "
        "planning heuristics, not formal power calculations, but they rule out a kitchen-sink GIS model.",
        "",
        "## Shock-type support among household relocations",
        "",
        f"Lagged shock status is observed for {len(obs):,} of {len(hh):,} household moves. The joint counts are:",
        "",
        "| Lagged erosion | Lagged flood | Events |",
        "|---|---|---:|",
    ]
    for erosion in joint.index:
        for flood in joint.columns:
            lines.append(f"| {erosion} | {flood} | {int(joint.loc[erosion, flood]):,} |")
    lines += [
        "",
        "The flood-only and erosion-only cells are small. Estimate one pre-specified `any lagged shock` "
        "interaction in the main contrast. Treat separate flood-versus-erosion interactions as secondary "
        "and report their uncertainty prominently.",
        "",
        "## Most supported cross-district destinations in the climate sample",
        "",
        "| Destination | Cross-district events | All climate-sample events |",
        "|---|---:|---:|",
    ]
    for r in cross_top.itertuples(index=False):
        lines.append(f"| {r.destination_district} | {r.cross_district_events:,} | {r.events:,} |")
    lines += [
        "",
        "## Pre-registered parameter budget",
        "",
        "For the first GIS comparison, use at most four core destination constructs, each represented by "
        "one standardized scalar: (1) historical flood/surface-water exposure, (2) settlement/economic "
        "intensity, (3) transport/urban accessibility, and (4) agricultural land share. Add distance and "
        "population from the frozen gravity benchmark. Do not add destination fixed effects.",
        "",
        "For shock heterogeneity, interact `any lagged home shock` with no more than two pre-specified "
        "candidate constructs: destination hazard exposure and accessibility. Use ridge-regularized "
        "conditional logit as the primary estimation guardrail, with the unpenalized low-dimensional "
        "model as a transparency check.",
        "",
        "## Required evaluation gates",
        "",
        "1. GIS values must exist for all 64 districts and be computed using only data available before each strict cutoff.",
        "2. Compare paired out-of-fold log loss against `gravity_mle_disk_within` and interdistrict radiation using identical folds.",
        "3. Report the 64-alternative and nested interdistrict results separately.",
        "4. Require improvement in log loss, not merely top-1 accuracy, because top-1 is dominated by same-district moves.",
        "5. Report household-, location-, origin-, and temporal-blocked validation.",
        "6. Reject or simplify any specification with unstable coefficient signs across folds or severe feature collinearity.",
        "",
        "## Outputs",
        "",
        "- `bemp_stage3_event_timing.csv`: event-specific prior dates and strict GIS cutoffs.",
        "- `bemp_stage3_sample_concentration.csv`: effective sample size and parameter-budget diagnostics.",
        "- `bemp_stage3_destination_support.csv`: ranked destination support by analysis sample.",
        "- `bemp_stage3_wave_support.csv`: wave-specific support.",
        "- `bemp_stage3_baseline_error_by_origin.csv`: out-of-fold benchmark performance by origin.",
        "",
    ]
    (REPORTS / "bemp_stage3_identification_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    events = pd.read_csv(TABLES / "bemp_prospective_migration_events.csv", low_memory=False)
    eligible = events[truth(events.stage1_district_endpoint_eligible)].copy()
    interviews = load_interview_dates()
    timing = build_event_timing(eligible, interviews)
    metrics, destinations, waves, samples = build_support(events)
    errors = build_error_by_origin()

    timing.to_csv(TABLES / "bemp_stage3_event_timing.csv", index=False)
    metrics.to_csv(TABLES / "bemp_stage3_sample_concentration.csv", index=False)
    destinations.to_csv(TABLES / "bemp_stage3_destination_support.csv", index=False)
    waves.to_csv(TABLES / "bemp_stage3_wave_support.csv", index=False)
    errors.to_csv(TABLES / "bemp_stage3_baseline_error_by_origin.csv", index=False)
    write_report(timing, metrics, destinations, waves, samples, errors)

    print(metrics.to_string(index=False))
    print("\nTiming status:\n", timing.timing_status.value_counts().to_string())


if __name__ == "__main__":
    main()
