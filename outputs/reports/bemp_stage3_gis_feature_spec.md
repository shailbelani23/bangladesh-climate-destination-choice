# BEMP Stage 3 frozen GIS feature specification

## Scope

This is a pre-model specification. No raster has been joined to BEMP and no final GIS model has been estimated. The purpose is to freeze source choices, time rules, transforms, and rejection criteria before observing model improvements.

## First static GIS comparison: exactly four constructs

| Construct | Frozen source/year | Frozen district variable | Directional hypothesis |
|---|---|---|---|
| Historical flood exposure | Global Flood Database, 2000–2018 | `gfd_ever_flooded_land_share_2000_2018` | Ambiguous: avoidance versus floodplain livelihood/urban concentration |
| Settlement intensity | GHSL built-up surface, 2020 | `ghsl_built_surface_share_2020` | Positive |
| Urban accessibility | Travel time to cities, 2015 | `travel_time_city_ge_50k_median_2015` | Negative coefficient on travel minutes |
| Agricultural land | ESA WorldCover, 2020 | `worldcover_cropland_share_2020` | Context-dependent; likely positive for agrarian movers, negative for urban moves |

Distance and population remain benchmark controls. For a strict timing sensitivity, replace BBS 2022 population with GHS-POP 2020; do not include both. Standardize continuous variables across the 64 candidate districts using training-fold means and standard deviations only.

## Time rules

- 2020 is the only universal static reference year supported by every event cutoff.
- A 2021 or later annual layer may be used only when the event ledger's `latest_complete_annual_feature_year` permits it.
- Dynamic rasters must be truncated at `strict_feature_cutoff_date` separately for every event.
- The 2022 BBS population remains a transparent benchmark exposure, not a universally pre-choice causal predictor.
- Current OSM roads or facility registries are prohibited until a dated historical snapshot is verified.

## Raster processing contract

1. Preserve each source raster and checksum it before processing.
2. Reproject Bangladesh districts and rasters to an equal-area CRS before area fractions.
3. Use fractional pixel coverage at district boundaries; never centroid-in-polygon assignment for coarse cells.
4. Report valid-pixel coverage for every district and reject a variable if any district has <95% expected coverage without a documented physical reason.
5. Retain untransformed numerator, denominator, valid area, and final transformed feature.
6. Compare extracted national/district aggregates with publisher summaries when available.
7. Freeze the 64-row district feature table before fitting any choice model.

## Model-entry contract

The first comparison adds the four frozen constructs jointly to the strongest gravity baseline. A ridge penalty is tuned only inside training folds. No stepwise selection, outcome-guided feature dropping, destination fixed effects, or alternative transformations are allowed in the primary run. Pre-specified robustness substitutions are JRC surface water for flood exposure, VIIRS 2020 for settlement intensity, and GHS-POP 2020 for BBS population.

## Verified source facts

- [JRC Global Surface Water](https://global-surface-water.appspot.com/download) provides tiled downloads and yearly/monthly history; later 2022–2024 layers exist but require strict event cutoffs.
- [GHSL](https://human-settlement.emergency.copernicus.eu/dataToolsOverview.php) provides open multitemporal built-up and population products through the 2020 observed epoch.
- [ESA WorldCover](https://esa-worldcover.org/en/data-access) supplies 10 m 2020 and 2021 maps under CC BY 4.0 and warns that the versions use different algorithms.
- [Travel time to cities and ports](https://figshare.com/articles/dataset/Travel_time_to_cities_and_ports_in_the_year_2015/7638134) is a 2015, 30-arc-second modelled accessibility surface.
- [Global Flood Database](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) maps 913 selected events from 2000–2018 and is not a complete census of flooding.
- [CHIRPS v3](https://www.chc.ucsb.edu/data/chirps3) supplies 0.05-degree rainfall from 1981 to near-present.
- [VIIRS annual nighttime lights](https://eogdata.mines.edu/products/vnl/) supplies approximately 500 m annual radiance composites.

The complete registry, including licensing and limitations, is in `bemp_stage3_gis_source_registry.csv`.
