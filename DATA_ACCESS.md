# Data access and placement

The analysis uses public sources, but the source files are not redistributed in this repository. Download them from their publishers and preserve the original filenames.

## Household surveys

### Bangladesh Environmental Mobility Panel

Dataset citation: Freihardt, Jan, Lukas Rudolph, and Vally Koubi. *The Bangladesh Environmental Mobility Panel (BEMP): Panel Data on (Im)mobility After Riverbank Erosion and Flooding in Bangladesh*. Zenodo. <https://doi.org/10.5281/zenodo.18229498>

Place the official quantitative CSV archive, codebook CSV archive, variable list, and README under:

```text
data/raw/bemp/source/
```

The audit and extraction scripts preserve raw files and write derived material elsewhere.

### Bangladesh Integrated Household Survey

Download the three public-use waves from Harvard Dataverse:

- 2011–2012: <https://doi.org/10.7910/DVN/OR6MHT>
- 2015: <https://doi.org/10.7910/DVN/BXSYEL>
- 2018–2019: <https://doi.org/10.7910/DVN/NXKLZJ>

Place the selected questionnaire and data archives under:

```text
data/raw/bihs/
```

The exact file inventory and variable audit are reported in `outputs/reports/` and `outputs/tables/bihs_file_inventory.csv` in a full local checkout.

## District and GIS sources

The model uses:

- Bangladesh Bureau of Statistics district boundaries and 2022 population counts
- Global Flood Database event rasters
- GHS-BUILT-S R2023A, 2020 epoch
- the 2015 global travel-time-to-cities surface
- ESA WorldCover 2020

Source names, versions, URLs, hashes, coordinate systems, and extraction decisions are recorded in:

```text
outputs/tables/bemp_stage3_gis_source_registry.csv
outputs/tables/bemp_stage4_source_manifest.csv
outputs/tables/bemp_stage4_feature_freeze_manifest.csv
outputs/reports/bemp_stage4_gis_feature_build.md
```

Large source rasters belong under `data/external/` and are ignored by Git. The released district-level feature table contains no survey respondent information.

## Privacy boundary

Do not commit raw survey files or derived files containing household IDs, respondent IDs, event IDs, exact addresses, fold assignments, or event-level probabilities. The public household illustration is anonymized and reports only year, districts, move reason, and two held-out model scores already used in the paper.
