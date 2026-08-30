# Reproducibility guide

## Public release check

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make reproduce-public
```

The command creates `publication/qa/final_release_audit.csv` and `publication/qa/public_release_manifest.csv`. Every audit row must end in `PASS`.

## Analysis order

After placing the licensed source data as described in [DATA_ACCESS.md](DATA_ACCESS.md), the study can be rebuilt in this order:

1. BEMP feasibility audit and event ledger.
2. Gravity and radiation baselines.
3. Candidate-support and identification checks.
4. District GIS extraction and freeze.
5. BEMP conditional-choice models and grouped validation.
6. BIHS migration ledger, wider-origin replication, origin-held-out validation, and temporal validation.
7. Cross-dataset synthesis, frozen claim registry, figures, paper, web story, and presentation.

The scripts in `work/` follow this order in their filenames and outputs. Validators fail on duplicate choices, missing alternatives, leakage across grouped folds, probability sums that differ from one, inconsistent district universes, and changed frozen files.

## Two levels of reproducibility

`make reproduce-public` checks every public claim against the committed machine-readable outputs. When protected event-level tables exist locally, the same command also checks the household illustration and destination-network statistic against those tables.

`make validate-analysis` runs the BEMP and BIHS validation scripts against the complete local analysis state. It requires the licensed microdata and large GIS sources.

## Presentation and document builds

The paper and claim-sheet Word files are created with `work/publication_build/build_documents.py`. The seven-slide deck is created with `work/presentation_build/build_deck.mjs` and requires `@oai/artifact-tool`. Exported DOCX, PDF, and PPTX files are committed so the research outputs remain readable without either authoring runtime.
