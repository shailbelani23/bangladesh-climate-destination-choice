# Climate-related migration destination choice in Bangladesh

This repository studies a specific question: after a household moves following flood or river erosion, which district does it choose?

The analysis links two public household surveys to a common 64-district candidate set. A fitted gravity benchmark uses distance and destination population. The expanded conditional-choice model adds four district measures available for every candidate: historical flood exposure, built surface, travel time to a city, and cropland share.

Across the Bangladesh Environmental Mobility Panel (BEMP) and Bangladesh Integrated Household Survey (BIHS), the GIS-expanded model assigns more held-out probability to the destinations people actually chose. The main gain is 0.108 log-loss units for 184 shock-linked BEMP relocations and 0.098 for 123 BIHS river-erosion relocations. The wider BIHS sample covers all 64 origin districts and retains a positive gain when each origin is left out of training.

The estimates are predictive. They do not identify the causal effect of a destination attribute.

## Start here

- [One-page claim sheet](publication/claim_sheet.md)
- [Research paper](publication/manuscript/manuscript.md)
- [Public explainer](publication/public_explainer.md)
- [Interactive story](docs/index.html)
- [Seven-slide presentation](publication/presentation/bangladesh_climate_destination_choice_7_slide_presentation.pptx)
- [Figure captions and alt text](publication/figures/figure_captions_and_alt_text.md)
- [Machine-readable claim registry](publication/qa/manuscript_number_registry.csv)

## Repository map

```text
docs/                  public web story and interactive evidence explorers
outputs/figures/       final static figures
outputs/reports/       feasibility, design, and validation reports
outputs/tables/        public-safe aggregate tables and derived GIS features
publication/           paper, claim sheet, presentation, explainer, and QA
work/                  analysis, validation, and publication-build code
```

Raw survey files and any table containing household, respondent, or event identifiers are excluded from Git. See [DATA_ACCESS.md](DATA_ACCESS.md) for acquisition and placement instructions.

## Reproduce the public release

Create a Python environment, install the listed packages, and run:

```bash
make reproduce-public
```

This rebuilds the claim registry when protected intermediate tables are present, rebuilds the public web pages, and runs the final claim, prose, accessibility, and release-boundary checks. The committed aggregate tables are sufficient for the public audit. A full model refit requires the separately acquired survey and GIS files.

Run the longer analysis validation suite with:

```bash
make validate-analysis
```

The deck source uses `@oai/artifact-tool`; the exported `.pptx` is included for users without that runtime.

## Main release boundary

The repository includes code, documentation, aggregate results, district-level GIS features, figures, and publication files. It excludes raw BEMP and BIHS files, event ledgers, choice sets, event-level predictions, fold assignments, and any direct identifiers. Those exclusions protect survey participants and respect source-data distribution terms.

## Author

Shail Belani<br>
Undergraduate Researcher, Northwestern University<br>
[shailbelani2027@u.northwestern.edu](mailto:shailbelani2027@u.northwestern.edu)

## License

Code is released under the [MIT License](LICENSE). Source datasets retain their original terms and are not redistributed here.
