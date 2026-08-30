# Frozen BIHS external-replication design

## Research target

Test whether the already frozen BEMP district GIS utility specification improves out-of-sample prediction of revealed BIHS destination districts over the identical population–distance gravity benchmark and adapted radiation comparator.

This is a transportability and external-prediction test. It is not a refit of the research question, a new GIS feature search, or an estimate of whether environmental shocks cause migration.

## Frozen samples

### Primary external climate replication: `b4_erosion`

All 123 internal B4 household-head relocations with `b4_03 = 1`, explicitly “land or homestead land was lost due to river erosion.” Origin is `b4_02`; destination is the household’s R2 Module A district. The full-64 analysis includes within-district area moves; the interdistrict-63 analysis contains 71 events. Move year is descriptive and is not used to select events, except for a separately labelled valid-year sensitivity.

### Secondary household replication: `b4_all`

All 526 internal B4 relocations, regardless of reason. This tests whether the BEMP feature contract predicts household relocation generally. It includes 236 interdistrict events.

### Broader-origin individual replication: `v1_interval`

The 1,857 frozen R2/R3 current domestic migrants in `bihs_internal_migration_events.csv` with `primary_interval_sample = true`. The sample excludes 11 explicit pre-midline R3 migrants, 19 R3 `a01 + mid` keys already current migrants in R2, and two conflicting R3 duplicate member keys. It contains 1,208 interdistrict events from all 64 origin districts.

R1 current migrant stocks and excluded R3 rows are never introduced into the primary models; they may be used only in clearly labelled sensitivity analyses after primary results are frozen.

## Choice sets

- `full_64`: all Bangladesh districts, including the origin district. Within-district choices use the pre-existing frozen within-district disk distance proxy.
- `interdistrict_63`: exclude the origin alternative and retain only events whose chosen district differs from origin.

Every event has exactly one chosen alternative. The canonical district universe, population, distance matrix, radiation score, and GIS attributes are inherited unchanged from the BEMP frozen tables.

## Frozen models

1. Uniform 64/63-way probability (descriptive floor).
2. Gravity MLE: log destination population and log effective district distance.
3. Adapted radiation score, interdistrict only.
4. GIS joint ridge: gravity terms plus exactly four frozen destination attributes:
   - ever-flooded land share, 2000–2018;
   - built-surface share, 2020;
   - median travel time to a city of at least 50,000, 2015;
   - cropland share, 2020.
5. GIS joint unpenalized sensitivity.
6. Nested stay/cross model for full-64 analyses, matching the BEMP specification.

No destination fixed effects, new GIS layers, post-choice reason fields, network-assistance fields, or BIHS-derived destination frequencies enter the utility function.

## Validation

Primary comparison: deterministic household-grouped five-fold cross-validation. All events from one `a01` stay in the same fold. GIS scaling and ridge tuning occur inside the outer training fold.

Transportability sensitivity: leave-one-origin-district-out validation. Wave holdout is additionally run for `v1_interval` (train R2, test R3); it is not applicable to the single-wave B4 sample.

Primary metric: event-weighted mean negative log probability of the chosen district. Secondary metrics: top-1/top-3/top-5 accuracy, expected rank, and mean reciprocal rank. Improvements are gravity loss minus model loss, so positive values favor GIS.

Uncertainty: paired household-cluster bootstrap of out-of-fold event loss differences, 5,000 replicates with a fixed seed. The climate replication is judged on effect direction, magnitude, and interval—not a binary significance label alone.

## Pre-specified interpretation

- Strong replication: GIS improves grouped-CV log loss in `b4_erosion`, with a positive paired interval, and the direction is supported in at least one broader sample.
- Partial replication: positive point estimate in `b4_erosion` but interval crosses zero, with consistent gains in broader samples.
- Population-specific result: GIS helps BEMP but not BIHS erosion relocations; report this as failed external transport, not as a tuning opportunity.
- General-migration difference: GIS helps `b4_erosion` but not `v1_interval`; interpret as evidence that environmental displacement has a different destination utility structure than labor/marriage/education migration.

## Prohibited after freeze

Do not change samples after inspecting outcomes, add GIS variables, choose aliases based on model performance, drop Dhaka or same-district moves ad hoc, or redefine river erosion. Any additional analysis must be labelled exploratory and must leave the frozen outputs intact.

