# BEMP climate-related destination choice: Stage 5 GIS model results

## Executive decision

**Result: district GIS characteristics improve out-of-sample destination probabilities for shock-linked household relocations within the observed BEMP origin contexts.** In household-grouped five-fold validation, the direct ridge GIS model reduces mean log loss from **1.630** for the fitted gravity benchmark to **1.522**, an improvement of **0.108** (6.6%). A nested GIS model that separates staying in the origin district from crossing a district boundary reaches **1.506**, an improvement of **0.124** (7.6%). Household-cluster bootstrap intervals for both gains exclude zero.

The result is predictive and associational, not causal. It is also not nationally transportable as currently estimated. When each origin district is withheld completely, the direct full-universe GIS model performs worse than gravity (1.813 versus 1.687). Conditional on already crossing a district boundary, however, the GIS destination utility continues to outperform gravity under leave-one-origin-out validation (2.548 versus 2.772). The main generalization weakness is therefore the stay-versus-cross component, not necessarily the relative ranking of other districts.

The original BEMP feasibility verdict remains **YELLOW**: public destinations are observed at district level and support district-choice modeling, but public exact destination coordinates are not available.

## Research question and supported estimand

The estimand is destination choice **conditional on an observed whole- or partial-household move**. It is not the probability of migrating. The core climate-conditioned sample contains 184 moves by 137 households that were preceded by a strictly lagged recorded home flood or river-erosion shock. Of these moves, 113 remain within the origin district and 71 cross a district boundary.

Each event is expanded to the same frozen national choice universe:

- Full model: all 64 Bangladesh districts, including the origin district.
- Interdistrict model: the 63 districts other than the origin, evaluated only for the 71 observed cross-district moves.
- Origin geography: the district reconstructed from the latest valid pre-move BEMP residence.
- Destination geography: the public BEMP destination district after codebook-verified administrative reconciliation.
- Linkage and sample construction: frozen in the Stage 1 event ledger and household reconciliation tables.

District-level prediction is the finest defensible public-data analysis. The model cannot explain which village, neighborhood, or address a household selects within a district.

## Frozen predictors and comparators

The fitted gravity comparator contains only log destination population and log disk-adjusted origin-destination distance. Disk adjustment gives within-district alternatives a finite positive distance and avoids treating the very common same-district move as zero-distance travel. The adapted radiation benchmark is also retained.

The GIS model adds exactly four pre-registered destination constructs, entered jointly:

| Construct | Frozen district variable | Interpretation |
|---|---|---|
| Historical flood exposure | `gfd_ever_flooded_land_share_2000_2018` | Share of valid land ever flooded in the selected-event Global Flood Database union |
| Settlement intensity | `ghsl_built_surface_share_2020` | Built-surface area divided by valid district land |
| Urban accessibility | `travel_time_city_ge_50k_median_2015` | Area-weighted median minutes to an urban area of at least 50,000 people |
| Agricultural land | `worldcover_cropland_share_2020` | ESA WorldCover cropland share of valid land |

All four GIS predictors are standardized using training-fold moments only. The joint ridge penalty applies to the four GIS coefficients; the gravity terms remain unpenalized. The penalty is chosen from the frozen grid `{0.001, 0.01, 0.1, 1, 10, 100}` using household-grouped inner validation inside each outer training split. The low-dimensional unpenalized model is reported as a transparency check, not used to select features.

## Primary predictive results

### Shock-linked household relocations

Household-grouped five-fold results are fully out of sample at the household level.

| Choice universe | Model | Events | Mean log loss | Top-1 accuracy | Improvement vs gravity |
|---|---|---:|---:|---:|---:|
| Full 64 | Gravity | 184 | 1.630 | 61.4% | — |
| Full 64 | Radiation | 184 | 1.765 | 40.8% | -0.135 |
| Full 64 | Direct GIS ridge | 184 | **1.522** | 61.4% | **+0.108** |
| Full 64 | Direct GIS unpenalized | 184 | 1.521 | 61.4% | +0.109 |
| Full 64 | Nested gravity | 184 | 1.640 | 61.4% | -0.010 |
| Full 64 | Nested GIS ridge | 184 | **1.506** | 61.4% | **+0.124** |
| Interdistrict 63 | Gravity | 71 | 2.484 | 40.8% | — |
| Interdistrict 63 | Radiation | 71 | 2.434 | **47.9%** | +0.050 |
| Interdistrict 63 | GIS ridge | 71 | **2.157** | 42.3% | **+0.327** |

Lower log loss is better. The unchanged full-universe top-1 accuracy is expected: 61.4% of shock-linked relocations remain in their origin district, and both gravity and GIS usually rank that alternative first. GIS improves probability calibration and lower-ranked alternatives rather than changing the most likely district. In the cross-district subset, GIS has substantially better log loss but radiation has higher top-1 accuracy; no single metric supports claiming universal dominance.

### Paired household-cluster uncertainty

The following intervals use 5,000 bootstrap resamples of households applied to the same out-of-fold event losses.

| Comparison | Events / households | Mean log-loss gain | 95% cluster interval | Events with lower GIS loss |
|---|---:|---:|---:|---:|
| Direct GIS vs gravity, full 64 | 184 / 137 | **0.108** | **[0.023, 0.189]** | 71.7% |
| Nested GIS vs gravity, full 64 | 184 / 137 | **0.124** | **[0.015, 0.233]** | 58.2% |
| Nested GIS vs nested gravity, full 64 | 184 / 137 | **0.134** | **[0.005, 0.260]** | 62.5% |
| Direct GIS vs gravity, interdistrict | 71 / 50 | 0.327 | [-0.001, 0.634] | 74.6% |

The full-universe result clears the pre-specified predictive threshold. The interdistrict estimate is large but imprecise because it uses only 71 events and 50 households; its percentile interval narrowly crosses zero.

## Validation and transportability

| Validation scheme, shock-linked sample | Gravity | Direct GIS | Nested GIS | Direct GIS gain | Nested GIS gain |
|---|---:|---:|---:|---:|---:|
| Household-grouped five-fold | 1.630 | **1.522** | **1.506** | +0.108 | +0.124 |
| Location-grouped five-fold | 1.644 | **1.618** | **1.625** | +0.026 | +0.019 |
| Temporal W12+ holdout | 1.561 | **1.548** | 1.591 | +0.013 | -0.030 |
| Leave one origin district out | **1.687** | 1.813 | 1.946 | **-0.127** | **-0.259** |

These tests answer different questions. Household grouping protects against repeated-household leakage and is the primary design. Location grouping is a stronger spatial dependence check and retains a smaller GIS gain. The temporal holdout gives a small gain for the direct model but not the nested model. Leave-one-origin-out asks the hardest question—prediction from an origin district never represented in training—and rejects a broad national full-choice claim.

For the 71 cross-district moves alone, direct GIS still improves leave-one-origin-out log loss by 0.224 (2.548 versus 2.772). This contrast suggests that the difficult part is estimating whether a household stays within its origin district, which depends on origin-specific processes that seven BEMP origin districts cannot identify nationally.

## Destination associations

The table reports the direct ridge model fit to all 184 shock-linked events with the selected penalty of 0.1. GIS coefficients are per one standard deviation of the destination feature. Intervals use 1,000 household-cluster bootstrap replications and condition on the selected penalty.

| Predictor | Estimate | 95% bootstrap interval | Stable sign in bootstrap? |
|---|---:|---:|---:|
| Log destination population | +1.072 | [-0.010, +2.833] | 97.3% positive |
| Log disk-adjusted distance | -4.029 | [-5.209, -3.467] | 100.0% negative |
| Historical flood exposure | +0.574 | [+0.140, +1.080] | 99.4% positive |
| Built-surface share | -0.347 | [-0.774, -0.042] | 99.3% negative |
| Travel time to city ≥50,000 | -3.104 | [-5.736, -1.126] | 100.0% negative |
| Cropland share | -1.380 | [-2.017, -0.842] | 100.0% negative |

The clearest conditional association is accessibility: otherwise comparable destination districts with longer travel times to a city receive lower predicted choice probability. The positive flood coefficient does **not** mean households seek flood danger. It means that, conditional on population, distance, accessibility, built surface, and cropland, observed destinations tend to be in districts with greater historical floodplain exposure. Floodplain livelihoods, social networks, urban geography, and origin composition are all plausible confounders. Similarly, the negative built-surface coefficient is a multivariable residual association and should not be paraphrased as “migrants avoid cities.”

## Nested model interpretation

The nested model first predicts staying within the origin district versus crossing to another district, then predicts the destination conditional on crossing. In household-grouped validation, the GIS first-stage binary log loss is 0.674 and AUC is 0.556, compared with 0.681 and 0.578 for nested gravity. GIS improves full destination log loss without improving binary AUC. The nested gain should therefore be interpreted as better probability allocation across the full choice process, not as strong discrimination of who crosses a district boundary.

## Secondary shock-interaction analysis

The secondary sample contains 262 household moves with observed lagged shock status. Only two pre-registered interactions were allowed: shock × destination flood exposure and shock × destination accessibility.

- Full 64: the interaction model improves log loss by 0.010 relative to the same GIS model without interactions; the paired interval is [-0.011, 0.031].
- Interdistrict 63: the interaction model is worse by 0.011; the paired interval is [-0.039, 0.014].
- The fitted shock × flood coefficient is positive, but the model-level predictive interval includes no gain.

This analysis does not show reliable predictive heterogeneity by recorded shock status and cannot support a causal claim that floods or erosion change destination preferences.

## All-move robustness sample

The broader sample of 264 whole- or partial-household relocations produces the same main pattern. In household-grouped validation, direct GIS improves full-universe log loss by 0.095 over gravity, with a 95% household-cluster interval of [0.019, 0.170]. Nested GIS improves by 0.125, with an interval of [0.014, 0.225]. The consistency shows that the core finding is not created solely by the shock-linked sample definition, but it also means the GIS signal is not uniquely “climate migration.”

## Validation status and reproducibility

Every fatal computation gate passes:

- 573 modeled events expanded to 36,672 rows, exactly 64 alternatives and one chosen alternative per event.
- Zero missing values in the four frozen GIS features.
- Stage 2 gravity results reproduced in all 16 benchmark cells; maximum log-loss difference is 5.24×10⁻⁹.
- Out-of-fold probabilities sum to one with maximum error below 2×10⁻¹⁵.
- All 412 outer fits converged; the 1,000-replicate parameter bootstrap convergence rate is 100%.
- No household overlaps its primary training and test fold.
- Every tuning context selects exactly one penalty from the pre-registered grid.
- No post-choice survey variables or unregistered GIS features enter the destination utilities.

The full machine-readable validation record is `bemp_stage5_validation.csv`. Event-level predictions, fold parameters, inner-tuning losses, split audits, and bootstrap results are retained in the Stage 5 tables.

## Precise empirical conclusion

The supported Stage 1 claim is:

> Among observed BEMP whole- or partial-household relocations after a strictly lagged home flood or river-erosion report, four pre-registered district GIS characteristics jointly improve household-out-of-sample destination probability predictions beyond fitted population-distance gravity and adapted radiation benchmarks. The improvement is clearest in log loss, not top-1 accuracy, and is valid for the observed BEMP origin settings.

The unsupported claims are:

- that the GIS coefficients are causal effects of destination characteristics;
- that the positive flood association means households prefer environmental risk;
- that the model predicts village or neighborhood destinations;
- that it generalizes to an unseen Bangladesh origin district;
- that shock interactions reliably distinguish “climate migrants” from other movers.

## Recommended next empirical stage

The strongest next design is not a larger black-box model. It is an origin-transportability and mechanism stage:

1. Keep the 184-event shock-linked full-universe ridge model as the primary registered specification and the 264-event all-move model as robustness.
2. Treat same-district versus cross-district movement as a separate process. Report the 71-event interdistrict model as a conditional destination analysis rather than forcing one model to explain both processes.
3. Add pre-move origin and destination network measures only when their timing can be verified and when they can be defined for every candidate district. Do not use post-move network reports as destination attributes.
4. Seek additional origin districts or another panel with district destinations before claiming national transportability. With only seven BEMP origins, richer algorithms cannot solve the support problem.
5. If stricter temporal alignment is desired, replace the 2022 population benchmark with a pre-move gridded population product in a sensitivity analysis; do not add it alongside the existing population term.
6. Preserve the current feature freeze, nested validation, and household-cluster uncertainty as the comparison contract for every extension.

The project has therefore answered the narrow research question with a qualified **yes**: GIS improves revealed district-choice prediction beyond simple baselines in the observed sample, but the public BEMP geography and origin support constrain how broadly that answer can be generalized.
