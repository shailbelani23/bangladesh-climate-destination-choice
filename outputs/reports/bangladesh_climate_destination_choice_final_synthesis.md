# Climate-related migration destination choice in Bangladesh

## Final cross-dataset synthesis

### Research question

Conditional on an observed move, can characteristics of candidate destination districts predict where Bangladeshi households and individuals relocate better than distance, population/gravity, and radiation benchmarks?

### Answer

**Yes, with a clear boundary.** The frozen four-variable GIS model consistently improves ordinary out-of-sample destination prediction in both BEMP and BIHS. It also transports across all 64 unseen BIHS origin districts for the large national migrant sample. For small climate-specific samples, however, the full stay-versus-leave problem is origin-dependent: when an entire origin is unseen, GIS does not reliably improve the probability of staying in the origin district versus leaving it. Conditional on an interdistrict move, the GIS advantage remains positive in both climate datasets, though the small-sample intervals are wide.

This is a stronger and more credible result than the original four-origin BEMP finding alone. It is now supported by a separate national survey, a directly measured river-erosion relocation sample, a larger general-migration sample, temporal holdout, and national origin holdout.

## Data designs actually supported by the public fields

### BEMP discovery sample

- 184 shock-linked household relocation events in the full 64-district choice set.
- 71 interdistrict events for the conditional destination analysis.
- Origin and destination are public districts; exact coordinates are absent.
- Longitudinal household shocks permit a stronger shock-linked interpretation than BIHS V1.

### BIHS climate replication

- 123 household-head relocations explicitly attributed to loss of land or homestead land from river erosion in 2015 Module B4.
- Previous district is the origin; the current Module A district is the revealed destination.
- 71 are interdistrict moves.
- This is an independent household-level climate relocation sample, not a recoding of BEMP.

### BIHS national generalization sample

- 1,857 conservative R2/R3 interval-specific current domestic migrants from 1,404 households.
- All 64 origin districts and 63 observed destination districts are represented.
- 1,208 moves cross district boundaries.
- Migrants are individuals currently away at least six months and outside the origin upazila; permanence and complete return spells are not observed.

## Frozen empirical design

Each event receives the same 64 candidate destination districts. The chosen alternative is the reported destination. The primary utility comparison is:

- gravity: log destination population plus log effective origin–destination distance;
- GIS: the same gravity terms plus destination ever-flooded land share, built-surface share, urban travel time, and cropland share;
- radiation and uniform models as transparent secondary benchmarks.

No BIHS outcome was used to select GIS layers. No destination fixed effects, survey destination frequencies, migration reasons, or post-choice network fields enter the utility function. GIS variables are standardized and the ridge penalty is chosen inside each training fold.

The two candidate universes answer different questions:

- **Full 64:** can the model jointly predict staying within the origin district versus moving elsewhere, and then which district?
- **Interdistrict 63:** conditional on crossing a district boundary, which destination district is chosen?

Validation uses household-grouped five-fold cross-validation, R2-to-R3 temporal holdout for BIHS V1, and leave-one-origin-district-out testing. Uncertainty for comparable out-of-fold predictions is a paired 5,000-replicate household-cluster bootstrap.

## Main results

### Ordinary grouped out-of-sample prediction

| Dataset and sample | Universe | Events | GIS gain over gravity | 95% household-cluster interval |
|---|---|---:|---:|---:|
| BEMP shock-linked relocations | Full 64 | 184 | **0.108** | **[0.023, 0.189]** |
| BEMP shock-linked relocations | Interdistrict 63 | 71 | **0.327** | [-0.001, 0.634] |
| BIHS river-erosion relocations | Full 64 | 123 | **0.098** | **[0.028, 0.163]** |
| BIHS river-erosion relocations | Interdistrict 63 | 71 | **0.182** | **[0.076, 0.287]** |
| BIHS all household relocations | Full 64 | 526 | **0.058** | **[0.030, 0.088]** |
| BIHS all household relocations | Interdistrict 63 | 236 | **0.116** | **[0.056, 0.179]** |
| BIHS interval-specific migrants | Full 64 | 1,857 | **0.108** | **[0.082, 0.135]** |
| BIHS interval-specific migrants | Interdistrict 63 | 1,208 | **0.108** | **[0.073, 0.145]** |

Positive gain is gravity log loss minus GIS log loss, so larger positive values mean better probability assigned to the actual destination. The near-identical 0.108 BEMP and 0.108 national BIHS gains are not imposed by design; they emerge in separate samples.

The nested full-64 GIS model strengthens the grouped results further: gains over direct gravity are 0.124 for the BEMP climate sample, 0.129 for BIHS erosion relocations, 0.116 for all BIHS household relocations, and 0.216 for the national migrant sample.

### Temporal holdout

Training on BIHS R2 and testing only on R3 still favors GIS:

- full 64: gain **0.094** across 1,383 R3 events;
- interdistrict 63: gain **0.112** across 842 R3 interdistrict events.

Thus the national result is not merely interpolation among random folds from the same wave.

### Unseen-origin transportability

| Sample | Universe | Events | GIS gain | 95% household-cluster interval |
|---|---|---:|---:|---:|
| BIHS interval-specific migrants | Full 64 | 1,857 | **0.101** | **[0.074, 0.128]** |
| BIHS interval-specific migrants | Interdistrict 63 | 1,208 | **0.107** | **[0.073, 0.144]** |
| BIHS all household relocations | Full 64 | 526 | 0.027 | [-0.003, 0.059] |
| BIHS all household relocations | Interdistrict 63 | 236 | **0.082** | **[0.020, 0.146]** |
| BIHS river-erosion relocations | Full 64 | 123 | -0.016 | [-0.086, 0.045] |
| BIHS river-erosion relocations | Interdistrict 63 | 71 | 0.058 | [-0.034, 0.140] |

For national migration, the GIS utility transports to origins entirely absent from training. Forty-six of 64 origin districts have a positive mean full-64 GIS gain. The erosion-only sample is too small and concentrated for equally strong origin transport.

The climate-specific pattern is consistent across datasets. BEMP’s leave-one-origin result is -0.127 full-64 but +0.224 interdistrict; BIHS erosion is -0.016 full-64 but +0.058 interdistrict. The reasonable interpretation is that origin-specific conditions govern whether a climate-affected household remains within its district, while GIS destination attributes retain more portable information once an interdistrict move is known to occur.

## How important is this finding?

In plain language, the model is no longer succeeding only because it has seen similar movers from a few erosion hotspots. It works in another survey, on a direct river-erosion question, across the country, in a later wave, and for households from origin districts omitted entirely during training.

That moves the project from a promising single-dataset exercise toward a research-quality, externally replicated predictive finding. The most defensible contribution is:

> Among observed Bangladeshi movers, destination districts are not selected by distance and population alone. A small, pre-specified set of environmental, urban, accessibility, and agricultural destination characteristics adds reproducible out-of-sample predictive information.

The result should not be described as proof that these GIS characteristics cause migration. Nor should the climate-specific unseen-origin full-64 limitation be hidden. Reporting that boundary makes the central conditional-destination claim more precise and credible.

## Recommended Stage 1 paper specification

1. **Primary estimand:** district destination choice conditional on an observed household relocation after a lagged BEMP shock; full-64 direct and nested specifications.
2. **Primary external climate replication:** BIHS B4 river-erosion household relocations using the unchanged 64-district feature contract.
3. **National external-validity analysis:** conservative BIHS R2/R3 V1 migrant ledger, clearly labelled individual current migration rather than household displacement.
4. **Transportability claim:** emphasize strong national V1 leave-one-origin performance; present climate interdistrict transport as directionally consistent but sample-limited.
5. **Mechanism evidence:** report that 1,815 of 1,857 BIHS interval migrants received help from friends/family at the destination, but do not place this endogenous post-choice field in the GIS utility model.
6. **Benchmarks and metrics:** retain identical gravity, radiation, uniform, grouped-CV log loss, temporal holdout, leave-one-origin, rank metrics, and clustered paired intervals.

## Limitations

- Public origins and destinations are districts, not exact coordinates.
- BEMP’s shock-linked timing is stronger than the BIHS V1 shock timing; BIHS V1 should not be marketed as a causal climate-migration sample.
- BIHS B4 is retrospective, and some relocation years predate the GIS observation years.
- V1 is a stock of current individual migrants away at least six months, not a complete migration-spell panel.
- The four GIS attributes are jointly predictive, but individual coefficients are not causal effects.
- The erosion sample contains only 29 observed origin districts and 123 events, limiting unseen-origin precision.

## Reproducible artifacts

- Feasibility audit: `outputs/reports/bihs_destination_feasibility_audit.md`
- Frozen design: `outputs/reports/bihs_external_replication_design_freeze.md`
- Exact cross-dataset table: `outputs/tables/cross_dataset_replication_summary.csv`
- BIHS grouped, temporal, and origin-holdout results: `outputs/tables/bihs_replication_all_model_results.csv`
- Event ledgers: `outputs/tables/bihs_household_relocation_events.csv` and `outputs/tables/bihs_internal_migration_events.csv`
- Validation: `outputs/tables/bihs_replication_validation.csv`
- Final hashes: `outputs/tables/bihs_replication_final_freeze_manifest.csv`

