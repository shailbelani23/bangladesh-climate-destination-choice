# BEMP Stage 4 GIS acquisition, extraction, and pre-model freeze

## Decision

The four pre-registered destination constructs have been acquired, independently verified, extracted for all 64 Bangladesh districts, and frozen **without fitting the final destination-choice model**. The district feature build passes every fatal validation gate. It is now technically ready for a model comparison once modeling is explicitly authorized.

This stage does not alter the BEMP feasibility verdict: **YELLOW** remains correct. Public BEMP identifies destinations at district level, not by exact coordinates. Consequently, these GIS features describe candidate destination districts; they cannot recover neighborhood- or village-level destination choice.

## Frozen primary variables

| Construct | Frozen variable | Source | Resolution/year | District definition |
|---|---|---|---|---|
| Historical flood exposure | `gfd_ever_flooded_land_share_2000_2018` | Global Flood Database v1 | 250 m; 913 selected events, 2000–2018 | Union of flooded pixels, excluding permanent water and intersecting the union with valid 2020 WorldCover land; divided by valid district land |
| Settlement intensity | `ghsl_built_surface_share_2020` | GHS-BUILT-S R2023A | 100 m; 2020 epoch | Fractionally allocated built-surface square metres divided by valid district land square metres |
| Urban accessibility | `travel_time_city_ge_50k_median_2015` | Travel time to cities and ports | 30 arc seconds; 2015 | Area-weighted median minutes among valid district land cells to the nearest urban area with at least 50,000 people |
| Agricultural land | `worldcover_cropland_share_2020` | ESA WorldCover v100 | 10 m; 2020 | Cropland-class area divided by valid mapped district land area |

The model-entry rule remains the Stage 3 rule: enter these four constructs jointly, standardize using training-fold means and standard deviations only, and do not select variables after observing the outcome.

## Source acquisition and provenance

### Global Flood Database

The official GFD catalog contains 913 selected MODIS event maps. A spatial scan of every public GCS GeoTIFF found 134 official-catalog raster envelopes intersecting the Bangladesh bounding box. Range-reading the actual Bangladesh windows showed that 103 contain at least one non-permanent flooded-land pixel in Bangladesh. The frozen union uses Band 1 (`flooded`) and excludes Band 5 (`jrc_perm_water`) according to the official GeoTIFF README. Every candidate object's immutable GCS generation, MD5, ETag, source byte count, and actual-intersection result is recorded in `bemp_stage4_gfd_event_manifest.csv`.

The scan deliberately distinguishes broad watershed-envelope overlap from actual flooded-pixel overlap. Treating all 134 envelopes as observed Bangladesh floods would be incorrect.

### GHSL built-up surface

Four official 100 m Mollweide tiles cover Bangladesh: `R6_C27`, `R6_C28`, `R7_C27`, and `R7_C28`. The primary extraction uses these four tiles, matching the pre-registered preference for 100 m data. A 1 km global archive was also preserved but is not the primary feature.

### Accessibility

Figshare's twelve city layers are immutable but large. The six city-size classes spanning 50,000 to 50 million people were range-read only over Bangladesh and combined by pixelwise minimum, exactly as the publisher README permits. As an independent check, the publisher's precombined `city11` layer was also range-read. It matches the six-layer composite exactly: **zero differing pixels and zero-minute maximum absolute difference**.

### WorldCover

All six official 3° × 3° 2020 v100 COG tiles intersecting Bangladesh were downloaded in full. The source TIFF metadata independently confirms that class `40` is cropland, class `80` is permanent water, the map is 10 m, and the license is CC BY 4.0.

All 24 locally retained source or metadata components exist and reproduce their recorded SHA-256 hashes. The complete acquisition record is `bemp_stage4_source_manifest.csv`.

## Spatial processing contract actually applied

1. Districts are the frozen 64-feature BBS/DGHS ADM2 geometry from Stage 2, keyed by official P-code.
2. Raw archives and full WorldCover source tiles are immutable. Transformed accessibility and flood products live separately under derived/subset directories.
3. Area calculations are equal-area or latitude-area weighted. GHSL is processed in its native Mollweide equal-area CRS. Geographic rasters use row-specific square-metre cell areas.
4. Boundary cells receive exact geometry-intersection fractions. Interior cells are allocated fully. No coarse raster is assigned only by its centroid.
5. WorldCover permanent-water pixels are removed from the common land denominator.
6. GFD's historical union is intersected with the same 10 m WorldCover land mask before computing the final hazard share.
7. Untransformed numerators, denominators, valid areas, cell counts, and coverage measures are retained in the frozen district table.

## QA correction discovered during extraction

The first draft flood share exceeded 1.0 in Sirajganj. The underlying GFD union had already excluded event-specific JRC permanent water, but its numerator still included some pixels classified as permanent water by the separate 2020 WorldCover denominator. That mismatch could make historical flooded area larger than 2020 land area.

The rejected draft was not frozen or modeled. The corrected feature reprojects the GFD union to each 10 m WorldCover district window and counts flooding only on valid WorldCover land pixels. The corrected flood-share range is 0.000 to 0.914. This is the frozen version.

## Coverage and validity

All fatal checks pass:

- 64 rows and 64 unique district P-codes.
- Zero missing values in all four primary features.
- Flood, built-up, and cropland shares all lie in [0, 1].
- Minimum valid coverage is 100.19% for WorldCover, 100.19% for GHSL, and 99.67% of valid WorldCover land for accessibility. Values slightly above 100% arise from comparing spherical/equal-area raster allocation with ellipsoidal polygon area and, for accessibility, coarse mixed land-water cells; the lower-tail coverage gate is the relevant rejection check.
- The six-layer accessibility composite equals the publisher's precombined layer exactly.
- All 24 source/metadata files match recorded hashes.

National extracted totals provide additional plausibility checks:

| Quantity | Extracted total |
|---|---:|
| BBS boundary geodesic area | 139,852 km² |
| WorldCover valid mapped area | 140,171 km² |
| WorldCover valid land area | 132,503 km² |
| WorldCover cropland area | 70,345 km² |
| GHSL built surface | 2,685 km² |
| GFD ever-flooded valid land | 48,419 km² |

These totals are internal spatial checks, not claims that the global products reproduce official Bangladesh land accounts.

## Feature distributions

| Variable | Mean | Median | Minimum | Maximum |
|---|---:|---:|---:|---:|
| GFD ever-flooded land share | 0.368 | 0.342 | 0.000 | 0.914 |
| GHSL built-surface share | 0.022 | 0.018 | 0.002 | 0.101 |
| Travel time to city ≥50,000, minutes | 18.3 | 15.0 | 0 | 174 |
| WorldCover cropland share | 0.562 | 0.611 | 0.022 | 0.772 |

The spatial rankings are substantively plausible and useful for error detection:

- Flood exposure is highest in Sirajganj, Sunamganj, Manikganj, Brahmanbaria, and Kurigram; it is lowest in Bandarban, Khagrachhari, Jhalokati, Thakurgaon, and Rangamati.
- Built-up share is highest in Dhaka, Narayanganj, Gazipur, Cumilla, and Rajshahi.
- Accessibility is poorest in Rangamati (174 minutes), Bandarban (89), and Khagrachhari (54); Dhaka and Narayanganj have median zero-minute cells because large urban areas lie inside the districts.
- Cropland share is highest in Dinajpur, Joypurhat, Thakurgaon, Naogaon, and Netrakona and lowest in the three Chittagong Hill Tracts districts.

## Collinearity before model fitting

The strongest Pearson correlations are flood exposure with cropland share (+0.57) and accessibility with cropland share (−0.57). The strongest Spearman correlations are flood with cropland (+0.57) and built-up with accessibility (−0.57). These are material but not a reason for outcome-guided feature deletion. They reinforce the pre-registered choice of a joint four-feature ridge specification and the requirement to report coefficient stability across folds.

## Precise Stage 1 empirical design supported by BEMP and these fields

The supported estimand remains **destination choice conditional on an observed move**, not whether households migrate.

### Primary descriptive/benchmark population

- Use the 264 whole- or partial-household relocations as the principal relocation sample.
- Retain all 64 districts as candidate destinations, including the origin district.
- Preserve the frozen `gravity_mle_disk_within` comparator because 59.5% of household relocations remain in the origin district and a zero self-distance is invalid.

### Core climate-conditioned population

- Use the 184 whole/partial-household relocations preceded by a strictly lagged recorded home flood or erosion shock.
- These represent 137 households; 113 stay within the origin district and 71 cross a district boundary.
- Evaluate the full 64-alternative model and the 63-alternative interdistrict model separately. The latter has only 71 events and 13 observed destination districts, so it cannot support destination fixed effects or a large feature set.

### Nested interpretation

1. Model staying in the origin district versus crossing a district boundary.
2. Conditional on crossing, model the choice among the other 63 districts.
3. Keep the one-stage 64-alternative conditional logit as the common prediction benchmark, while recognizing that its top-1 accuracy is dominated by same-district moves.

### First GIS comparison, once authorized

- Comparator: frozen gravity model with log destination population and log disk-adjusted distance.
- Addition: exactly the four standardized district constructs in this report, entered jointly.
- Guardrail: ridge-regularized conditional logit, with penalty selected only inside the training data of each outer fold.
- Transparency check: unpenalized low-dimensional model, with convergence and sign instability reported rather than suppressed.
- Primary metric: paired out-of-fold event log loss; secondary metrics top-1/top-3/top-5, mean rank, and reciprocal rank.
- Validation: household-grouped five-fold as primary; location-blocked, leave-one-origin-district-out, and temporal-blocked sensitivity analyses.
- Shock heterogeneity: in the 262 household moves with observed lagged shock status, interact `any lagged home shock` only with destination flood exposure and accessibility. Separate flood-versus-erosion interactions remain secondary because flood-only and erosion-only cells are small.
- Inference: describe differential destination preferences. Do not label the shock interactions causal without stronger exogeneity assumptions.

## Remaining limitations

- District features cannot explain within-district neighborhood choice, although 61.4% of the core climate-conditioned moves remain in the origin district.
- GFD is a selected-event archive, not a complete flood climatology, and its noncommercial license constrains reuse.
- GHSL built surface is an opportunity/settlement proxy, not wages or jobs.
- Accessibility is modeled relative travel time using a 2015 friction surface, not an observed trip time.
- WorldCover reports 74.4% global overall accuracy, and 2020 should not be differenced mechanically against its differently produced 2021 map.
- BEMP has only seven origin districts and highly concentrated destination support; national candidate coverage does not create national origin representativeness.
- BBS 2022 population remains a transparent benchmark variable, not a universally pre-choice causal covariate. A later strict-timing sensitivity should substitute GHS-POP 2020 rather than add it alongside BBS population.

## Frozen outputs

- `bemp_stage4_district_gis_features.csv`: 64-district raw numerators, denominators, coverage fields, and final predictors.
- `bemp_stage4_gis_feature_summary.csv`: descriptive distribution checks.
- `bemp_stage4_gis_feature_correlations.csv`: Pearson and Spearman pre-model correlations.
- `bemp_stage4_gfd_event_manifest.csv`: source-object provenance and Bangladesh pixel-intersection audit.
- `bemp_stage4_source_manifest.csv`: retrieval, local path, byte count, and SHA-256 provenance.
- `bemp_stage4_validation.csv`: all acceptance/rejection checks.
- `bemp_stage4_feature_freeze_manifest.csv`: checksums for the pre-model artifacts.

The feature table is now frozen. No final destination-choice model was fit in this stage.
