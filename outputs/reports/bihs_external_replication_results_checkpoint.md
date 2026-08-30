# BIHS external replication: validated checkpoint

## Bottom line

The frozen BEMP GIS specification replicates in an independent national survey and in a directly comparable river-erosion relocation sample. Across every pre-specified grouped-CV sample, the four GIS destination attributes improve chosen-district log loss over the same population–distance gravity model. All reported direct-GIS household-cluster bootstrap intervals are above zero.

This is a major strengthening of the project. The original BEMP result could plausibly have been peculiar to four erosion-prone origin areas. BIHS instead supplies origins in all 64 districts and a separate questionnaire. The fact that the gain persists under an unchanged GIS contract makes “narrow-sample artifact” substantially less plausible.

## Frozen grouped-CV results

| Sample | Universe | Events | Gravity | Direct GIS | GIS gain | Household-bootstrap 95% interval |
|---|---|---:|---:|---:|---:|---:|
| River-erosion household relocations | Full 64 | 123 | 2.563 | 2.465 | **0.098** | **[0.028, 0.163]** |
| River-erosion household relocations | Interdistrict 63 | 71 | 3.256 | 3.074 | **0.182** | **[0.076, 0.287]** |
| All household relocations | Full 64 | 526 | 2.206 | 2.148 | **0.058** | **[0.030, 0.088]** |
| All household relocations | Interdistrict 63 | 236 | 3.253 | 3.138 | **0.116** | **[0.056, 0.179]** |
| Interval-specific current migrants | Full 64 | 1,857 | 2.060 | 1.952 | **0.108** | **[0.082, 0.135]** |
| Interval-specific current migrants | Interdistrict 63 | 1,208 | 2.021 | 1.913 | **0.108** | **[0.073, 0.145]** |

Positive gain means lower out-of-fold log loss than gravity. Events from the same household are kept in one fold; GIS scaling and the ridge penalty are selected inside each training fold. The paired intervals resample households 5,000 times.

The full-64 nested model is also consistently stronger than direct gravity:

- erosion relocations: 2.434 log loss, a 0.129 gain over gravity;
- all household relocations: 2.090, a 0.116 gain;
- current migrants: 1.844, a 0.216 gain.

The adapted radiation comparator performs substantially worse than fitted gravity in all BIHS interdistrict samples. It remains a transparent benchmark but is not competitive here.

## Temporal transport

Training the individual migrant model only on R2 (2015) and testing prospectively on the frozen R3 (2018–19) sample still favors GIS:

- full 64: gravity 2.090, GIS 1.996, gain **0.094** across 1,383 R3 events;
- interdistrict 63: gravity 2.053, GIS 1.941, gain **0.112** across 842 R3 events.

This is important because the improvement is not only random-fold interpolation. Destination attributes learned from the earlier wave continue to improve later-wave predictions.

## Comparison with BEMP

The original BEMP direct-GIS gain for the shock-linked household sample was 0.108 log-loss units. BIHS produces 0.098 for independently measured river-erosion household relocations and 0.108 for the much larger national current-migrant sample. The magnitudes are strikingly similar even though the surveys, samples, migration definitions, and origin coverage differ.

This does not prove a universal structural coefficient or causal mechanism. It does show that the predictive value of destination flood exposure, built environment, urban access, and cropland is reproducible beyond BEMP.

## What the result does not establish

- BIHS destinations are districts, not coordinates.
- B4 moves are retrospective and may long predate the modern GIS layers.
- V1 contains current individual migrants, not whole-household displacement spells.
- Household shock timing and V1 migration timing are not precise enough for a strict shock-before-move causal ordering.
- The GIS features improve prediction jointly; this checkpoint does not claim that any single feature is causal.

## Validation status

All 50 invariant and substantive checks in `bihs_replication_validation.csv` pass: 2,383 events have exactly 64 alternatives and one chosen district; grouped and origin-held-out folds have zero household overlap; all grouped, temporal, and leave-one-origin fits converge; probability sums equal one; paired point estimates reproduce aggregate results; and origin-holdout folds match their named test origins exactly.

The leave-one-origin block is now complete. National V1 transport remains strong (gain 0.101 full-64 and 0.107 interdistrict, both with positive household-cluster intervals). The smaller erosion sample shows a boundary: full-64 origin transport is slightly negative (-0.016), while interdistrict transport is positive (+0.058) but imprecise. This mirrors BEMP, where full-64 climate transport is negative but interdistrict transport is positive, and indicates that the stay-versus-leave stage is more origin-specific than destination choice conditional on crossing districts.

## Artifacts

- `outputs/reports/bihs_destination_feasibility_audit.md`
- `outputs/reports/bihs_external_replication_design_freeze.md`
- `outputs/tables/bihs_replication_key_results.csv`
- `outputs/tables/bihs_replication_model_results_grouped.csv`
- `outputs/tables/bihs_replication_paired_comparisons_grouped.csv`
- `outputs/tables/bihs_replication_model_results_wave.csv`
- `outputs/tables/bihs_replication_validation.csv`
