# BEMP Stage 2 district benchmark design and results

## Bottom line

The public BEMP data support a **district-level revealed destination-choice design**. This stage constructs the complete 64-district choice universe and evaluates only transparent distance, population/gravity, and radiation benchmarks. It is not the final GIS-enriched model.

The most important modeling fact is that within-origin-district moves are common: 33.3% of all 573 district-resolved events, 59.5% of the 264 household relocations, and 61.4% of the 184 household relocations preceded by a recorded home shock. A zero centroid distance would therefore be a serious artifact. The polygon-wide specification replaces zero with a deterministic Monte Carlo estimate of the mean distance between two uniformly sampled points inside that origin district; a pre-specified 1 km self-distance and an equivalent-area disk approximation are reported as sensitivities.

## Authoritative district universe

- 64/64 districts from the Bangladesh DGHS-hosted BBS ADM2 layer are present.
- 64/64 have a 2022 enumerated census population from BBS National Report Volume I, Table P02.
- 64/64 match after explicit historical/spelling crosswalks; no fuzzy matching is used.
- All 7 BEMP origin districts and all 37 observed destination districts match the canonical universe.

Sources: Bangladesh National Portal district list; Bangladesh DGHS hosted BBS 2020 ADM2 layer; Bangladesh Bureau of Statistics, *Population and Housing Census 2022, National Report (Volume I)*, Table P02 (PDF pages 199–200; printed pages 151–152).

## Samples carried forward

| Sample | Events | Same-origin district | Intended use |
|---|---:|---:|---|
| All district-resolved prospective moves | 573 | 33.3% | Endpoint benchmark / power |
| Whole- or partial-household relocations | 264 | 59.5% | Main relocation estimand |
| Household relocations with strictly lagged home shock=yes | 184 | 61.4% | Main climate-conditioned sample |

Origin support in the all-event sample: Kurigram (207), Tangail (132), Sirajganj (92), Bogura (68), Jamalpur (38), Manikganj (25), Gaibandha (11).

## Benchmark definitions

Every event receives all 64 Bangladesh districts as alternatives. The chosen indicator is the observed BEMP destination district. No post-choice reason, destination network response, move distance response, or later-wave information enters a predictor.

- **Uniform:** 1/64 for every district.
- **Population only:** conditional-logit coefficient estimated on log 2022 destination population.
- **Distance only:** coefficient estimated on log straight-line distance.
- **Gravity MLE:** coefficients estimated on log population and log distance.
- **Fixed gravity:** destination population divided by squared distance.
- **Within-district distance sensitivity:** `mc_within` uses the polygon-wide mean random-pair distance; `disk_within` uses the equivalent-area disk expectation; `1km_self` uses a pre-specified 1 km self-alternative floor. Cross-district distances remain centroid-to-centroid in all three.
- **Radiation adapted:** standard population/intervening-population score, with a diagnostic self-district alternative. Because radiation is an inter-unit model, the interdistrict-only result is the principled comparison.

The primary validation is five-fold household-grouped cross-validation. Additional files include location-grouped, leave-one-origin-district-out, and a wave 12–14 temporal holdout. Ranking ties use exact expected ranks and top-k probabilities under random ordering when scores tie. All conditional-logit fits converged.

## Primary climate-sample results: full 64-district universe

| Model | Events | Log loss | Top 1 | Top 3 | Top 5 | Mean rank | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gravity_mle_disk_within | 184 | 1.630 | 61.4% | 83.7% | 87.0% | 3.1 | 0.734 |
| gravity_mle_mc_within | 184 | 1.654 | 61.4% | 82.1% | 87.0% | 3.1 | 0.733 |
| radiation_adapted | 184 | 1.765 | 40.8% | 82.6% | 83.7% | 3.3 | 0.632 |
| distance_only_mle_mc_within | 184 | 1.799 | 59.8% | 81.5% | 86.4% | 3.9 | 0.721 |
| gravity_mle_1km_self | 184 | 1.823 | 61.4% | 82.6% | 86.4% | 3.6 | 0.717 |
| gravity_fixed_mc_within | 184 | 1.976 | 61.4% | 85.3% | 87.5% | 3.0 | 0.736 |
| distance_only_mle_1km_self | 184 | 1.987 | 61.4% | 81.5% | 86.4% | 3.9 | 0.729 |
| gravity_fixed_1km_self | 184 | 3.123 | 61.4% | 85.3% | 87.5% | 3.0 | 0.736 |
| population_only_mle | 184 | 3.855 | 7.1% | 7.6% | 11.4% | 15.8 | 0.165 |
| uniform | 184 | 4.159 | 1.6% | 4.7% | 7.8% | 32.5 | 0.074 |

## Primary climate-sample results: interdistrict sensitivity

This excludes events whose destination district equals the origin and removes the origin district from each candidate set. It is the appropriate domain for the conventional radiation benchmark.

| Model | Events | Log loss | Top 1 | Top 3 | Top 5 | Mean rank | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| radiation_adapted | 71 | 2.434 | 47.9% | 57.7% | 69.0% | 5.4 | 0.574 |
| gravity_mle_mc_within | 71 | 2.484 | 40.8% | 66.2% | 67.6% | 5.2 | 0.560 |
| gravity_mle_1km_self | 71 | 2.484 | 40.8% | 66.2% | 67.6% | 5.2 | 0.560 |
| gravity_mle_disk_within | 71 | 2.484 | 40.8% | 66.2% | 67.6% | 5.2 | 0.560 |
| gravity_fixed_mc_within | 71 | 2.574 | 40.8% | 66.2% | 67.6% | 5.2 | 0.564 |
| gravity_fixed_1km_self | 71 | 2.574 | 40.8% | 66.2% | 67.6% | 5.2 | 0.564 |
| distance_only_mle_mc_within | 71 | 2.901 | 40.8% | 64.8% | 67.6% | 7.5 | 0.534 |
| distance_only_mle_1km_self | 71 | 2.901 | 40.8% | 64.8% | 67.6% | 7.5 | 0.534 |
| population_only_mle | 71 | 3.567 | 18.3% | 19.7% | 29.6% | 13.3 | 0.287 |
| uniform | 71 | 4.143 | 1.6% | 4.8% | 7.9% | 32.0 | 0.075 |

## Survey-distance validation

The BEMP reported move-distance field is used only to audit the district proxy, never as a candidate predictor (it exists only for the chosen destination).

| Subset | N | Reported median km | Proxy median km | Spearman rho | Median absolute error km |
|---|---:|---:|---:|---:|---:|
| all_with_reported_distance | 125 | 2.1 | 32.2 | 0.491 | 27.9 |
| same_district | 76 | 1.2 | 29.0 | 0.387 | 27.6 |
| interdistrict | 49 | 11.9 | 53.6 | 0.436 | 37.4 |

## Interpretation and Stage 1 empirical design

The supported design is a **district-level destination-choice analysis among observed movers**, not a model of whether a household migrates. The most transparent specification is nested:

1. Estimate whether a whole/partial-household move stays inside the origin district or crosses a district boundary (264 moves; 107 cross-district).
2. Conditional on crossing a district boundary, estimate choice among the other 63 districts (107 household moves; 71 in the lagged-shock-positive sample).
3. Retain the one-stage 64-alternative conditional logit as the headline benchmark, but do not interpret its 61.4% top-1 rate as fine-grained destination prediction: it largely identifies the very common self-district alternative.

Use the 264 whole/partial-household moves as the main relocation sample. The core climate-conditioned estimand uses the 184 moves with strictly lagged home shock=yes. A secondary contrast can use the 262 household moves with observed lagged shock status (184 yes versus 78 no) and interact pre-move erosion/flood status with candidate attributes. That contrast describes differential destination preferences; it is not automatically a causal effect of shock exposure. Use the full 573 events only as an endpoint/power benchmark. Cluster or group validation by household; report location-blocked and origin-blocked generalization because the seven origins are unevenly represented.

The next model may add destination GIS characteristics only if they are defined for all 64 candidate districts at a pre-move reference date. Core additions should be flood/erosion exposure, urbanization and employment opportunity, road/market accessibility, and service access. The comparison must be incremental: GIS model versus exactly the frozen benchmarks here, including the strongest validated gravity sensitivity rather than only a convenient weak baseline. Survey reasons and destination relatives are outcomes/mechanisms or heterogeneity variables, not candidate attributes, unless an external pre-choice network measure is constructed.

## Limitations that remain

- BEMP does not reveal exact origin or destination coordinates; all spatial predictors are district-level.
- Origin support is seven districts, so national destination alternatives do not imply national origin representativeness.
- The 2022 population surface is a stable benchmark exposure, not a fully time-varying opportunity measure for every survey wave.
- Centroid distance is an approximation. Same-district effective distance is simulation-based and should retain the supplied 1 km and disk-proxy sensitivities.
- The adapted full-universe radiation score is diagnostic; use the interdistrict version for substantive radiation claims.

## Reproducibility outputs

- `bgd_district_universe.csv`: 64 canonical districts, P-codes, central points, area, within-district distance, and population.
- `bgd_district_name_crosswalk.csv`: exact historical/spelling transformations.
- `bgd_origin_destination_matrix.csv`: all 4,096 district pairs and benchmark features.
- `bemp_stage2_event_choice_set.csv`: 573 × 64 = 36,672 event-alternative rows.
- `bemp_baseline_benchmark_results.csv`: all samples, universes, and validation schemes.
- `bemp_baseline_parameter_estimates.csv`: fold-level fitted coefficients.
- `bemp_baseline_oof_event_predictions.csv`: event-level out-of-fold predictions for household-grouped validation.
- `bemp_distance_proxy_validation.csv`: survey distance versus geographic proxy audit.
- `bemp_stage2_source_manifest.csv`: URLs, hashes, and retrieval metadata.
- `bemp_stage2_climate_destination_support.png`: mapped destination support for the 184-event climate-conditioned household sample.
