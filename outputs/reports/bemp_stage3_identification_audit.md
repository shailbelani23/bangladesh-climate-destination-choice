# BEMP Stage 3 pre-model identification and GIS-readiness audit

## Decision

Proceed to a tightly regularized, low-dimensional GIS feature build, but do not fit a large destination model. The binding constraint is no longer data linkage; it is statistical support. Only 71 shock-linked household relocations cross a district boundary, and many destination districts occur once. The final specification therefore needs a small pre-registered feature set.

## Leakage-safe timing

Prior interview dates are publicly recoverable for all 573 district-resolved prospective events: 571 from the same respondent and 2 using a same-household fallback. For every event, the strict GIS cutoff is one day before the last observed prior interview. This predates the full interval in which the new destination could have been chosen.

Annual dynamic features must use the latest **complete calendar year** before that cutoff. A 2022 annual composite is therefore not safe for an event whose prior interview occurred during 2022; the safe annual layer is 2021. Nine events have a 2021 cutoff, so their latest complete annual layer is 2020. Therefore **2020 is the universal static reference year**; 2021 and later layers require event-specific assignment. The BBS 2022 population used in Stage 2 is retained as a transparent gravity benchmark, but it is not a universally pre-move causal exposure.

## Statistical support

| Sample | Events | Households | Cross-district | Destinations | Cross-district destinations | Singleton cross-district destinations | Effective destination count |
|---|---:|---:|---:|---:|---:|---:|---:|
| all_district_events | 573 | 367 | 382 | 37 | 36 | 11 | 11.4 |
| household_relocation | 264 | 174 | 107 | 16 | 14 | 3 | 7.8 |
| household_lagged_shock_yes | 184 | 137 | 71 | 15 | 13 | 3 | 7.8 |
| household_lagged_shock_observed | 262 | 173 | 106 | 16 | 14 | 3 | 7.9 |

In the core climate sample, the five most frequent destination districts absorb 81.0% of moves. The effective number of destinations is only 7.8, despite a 64-district choice universe. This concentration is real signal, but it means flexible destination-specific effects would overfit.

A conservative planning rule permits about 3 freely estimated coefficients in the 71-event cross-district climate model; even the looser 10-events-per-parameter rule permits only 7. These are planning heuristics, not formal power calculations, but they rule out a kitchen-sink GIS model.

## Shock-type support among household relocations

Lagged shock status is observed for 262 of 264 household moves. The joint counts are:

| Lagged erosion | Lagged flood | Events |
|---|---|---:|
| No | No | 78 |
| No | Yes | 22 |
| Yes | No | 36 |
| Yes | Yes | 126 |

The flood-only and erosion-only cells are small. Estimate one pre-specified `any lagged shock` interaction in the main contrast. Treat separate flood-versus-erosion interactions as secondary and report their uncertainty prominently.

## Most supported cross-district destinations in the climate sample

| Destination | Cross-district events | All climate-sample events |
|---|---:|---:|
| Tangail | 26 | 55 |
| Dhaka | 13 | 13 |
| Manikganj | 7 | 8 |
| Jamalpur | 6 | 9 |
| Gazipur | 6 | 6 |
| Sirajganj | 2 | 22 |
| Gaibandha | 2 | 3 |
| Panchagarh | 2 | 2 |
| Nilphamari | 2 | 2 |
| Narayanganj | 2 | 2 |

## Pre-registered parameter budget

For the first GIS comparison, use at most four core destination constructs, each represented by one standardized scalar: (1) historical flood/surface-water exposure, (2) settlement/economic intensity, (3) transport/urban accessibility, and (4) agricultural land share. Add distance and population from the frozen gravity benchmark. Do not add destination fixed effects.

For shock heterogeneity, interact `any lagged home shock` with no more than two pre-specified candidate constructs: destination hazard exposure and accessibility. Use ridge-regularized conditional logit as the primary estimation guardrail, with the unpenalized low-dimensional model as a transparency check.

## Required evaluation gates

1. GIS values must exist for all 64 districts and be computed using only data available before each strict cutoff.
2. Compare paired out-of-fold log loss against `gravity_mle_disk_within` and interdistrict radiation using identical folds.
3. Report the 64-alternative and nested interdistrict results separately.
4. Require improvement in log loss, not merely top-1 accuracy, because top-1 is dominated by same-district moves.
5. Report household-, location-, origin-, and temporal-blocked validation.
6. Reject or simplify any specification with unstable coefficient signs across folds or severe feature collinearity.

## Outputs

- `bemp_stage3_event_timing.csv`: event-specific prior dates and strict GIS cutoffs.
- `bemp_stage3_sample_concentration.csv`: effective sample size and parameter-budget diagnostics.
- `bemp_stage3_destination_support.csv`: ranked destination support by analysis sample.
- `bemp_stage3_wave_support.csv`: wave-specific support.
- `bemp_stage3_baseline_error_by_origin.csv`: out-of-fold benchmark performance by origin.
