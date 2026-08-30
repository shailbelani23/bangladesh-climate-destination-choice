# BEMP Stage 1 event-ledger construction notes

## Purpose and status

This is a conservative pre-model data-engineering artifact. It converts the public BEMP respondent files into a respondent-wave state panel, a prospectively observed/high-confidence migration-event ledger, an official destination-to-district crosswalk, a separate recalled-history sensitivity table, auditable respondent/household linkage reconciliation, and an explicit Stage 1 sample flow.

No destination-choice model is estimated and no external GIS layer is joined. Raw BEMP files remain unchanged. The official administrative resolution described below uses Bangladesh government sources accessed on 2026-08-28.

## Outputs

| Artifact | Rows | Unit |
|---|---:|---|
| bemp_respondent_wave_state.csv | 27,662 | Public respondent-file row by wave/route |
| bemp_prospective_migration_events.csv | 1,066 | Conservative migration/return event or first endpoint-rich migrant snapshot |
| bemp_destination_admin_crosswalk.csv | 127 | Unique raw admin value and raw level |
| bemp_duplicate_adjudication.csv | 4 | Source rows in two duplicated respondent-wave pairs |
| bemp_stage1_sample_flow.csv | 18 | Nine sequential criteria plus nine wave summaries |
| bemp_stage1_data_dictionary.csv | 163 | Table-column definitions and roles |
| bemp_recalled_migration_history.csv | 1,039 | Observed recalled-move loop or compressed repeated-move pattern |
| bemp_recalled_history_flow.csv | 8 | Wave-by-history-stream recall coverage and exclusions |
| bemp_respondent_duplicate_audit.csv | 10 | All rows in five duplicated respondent-wave pairs |
| bemp_household_key_reconciliation.csv | 1,704 | Derived household prefix with baseline-role and panel-coverage checks |
| bemp_stage1_freeze_manifest.csv | 15 | SHA-256 checksums for BEMP audit, table, and report outputs (excluding the manifest/workbook themselves) |

The event and recalled-history tables contain source-file, source-row, interview-date, and source-variable provenance. Derived fields never overwrite raw responses, and superseded duplicate rows remain visible.

## Event definition

### Wave 6 migrant snapshot

The 187 `w6_M` records with a valid city/village response are retained as “first observed current migrant destination.” They contain useful destination, reason, household-scope, and hazard fields, but the move may predate wave 6. They remain separate from the prospective new-destination sample.

### Phone waves `w7`–`w11` and `w13`

“Another location” is a new-destination event. “Home village” is a return only when the registration field says the respondent was a migrant in the prior survey. Remaining at the previous migration destination is persistence, not a new event.

### In-person migrant waves `w12_M` and `w14_M`

A new event is recorded when the respondent was a non-migrant in the prior survey, was not interviewed in the prior survey, or explicitly reports another location rather than the previous migration destination. The not-interviewed branch remains medium confidence.

### Early phone waves `w2`–`w5`

These waves do not distinguish persistence at an earlier migrant destination from a new onward move. They remain in the state panel and shock history but are not forced into event rows.

## Event counts

| Event class | Records |
|---|---:|
| New other destination | 389 |
| New migrant from prior non-migrant state | 266 |
| New location after prior non-interview | 4 |
| Return to baseline home | 220 |
| First observed `w6_M` migrant destination | 187 |
| **Total** | **1,066** |

The 659 prospective new-destination records comprise 656 domestic events, one documented international event, and two records without usable domestic/abroad status.

## Official destination resolution

All 127 unique non-missing public destination strings resolve to an official containing district. This covers all 575 domestic new-destination events with a named city or rural-district response. The crosswalk preserves the raw value and records the official place, place type, district, match method, confidence, source URL, evidence note, access date, and manual-review flag.

Resolution rules are deliberately explicit:

- exact and spelling/language-normalized district names are checked against the Bangladesh National Portal district list;
- Savar, Bhuapur, Mirzapur, Moheshkhali, Nabinagar, and Roumari use official upazila containment;
- Elenga/“Alenga,” Aricha, Joydebpur, Kalampur, Konabari, and Kuakata use specific official locality evidence;
- `fangile` and `tabgile` are medium-confidence manual typo matches to Tangail, supported by their reported Dhaka division; and
- `Kirigami` is a medium-confidence manual typo match to Kurigram.

The one `w12_M` urban record with public city code 17 still has no public BEMP label. It has no named raw endpoint, is not part of the 127-row crosswalk, and remains excluded rather than guessed.

Core government references are embedded row by row in the crosswalk. They include:

- Bangladesh National Portal district list: <https://bangladesh.gov.bd/views/district-list/>
- Bangladesh National Portal upazila list: <https://bangladesh.gov.bd/views/upazila-list>
- Bangladesh Krishi Bank Elenga listing: <https://krishibank.gov.bd/pages/static-pages/6922e13f933eb65569e2b193>
- BWDB Aricha/Shivalaya listing: <https://www.hydrology.bwdb.gov.bd/includes/lithology_data_available_print.php?dist=>
- DGHS Konabari facility record: <https://hrm.dghs.gov.bd/public/facility-registry/facilities/28356/profile>
- Public Works Department Joydebpur record: <https://ss.pwd.gov.bd/buildingdatabase/index/5/9340>
- SEC Kalampur/Dhamrai filing: <https://sec.gov.bd/ipoprospectus/Mamun_Agro_Products_Limited_17.01.2022.pdf>
- Patuakhali PBS Kuakata/Kalapara listing: <https://pbs.patuakhali.gov.bd/pages/static-pages/69789baf35ce18e1c066ff63>

## Recalled migration histories

The in-person `w6_N`, `w6_M`, `w12_N`, `w12_M`, `w14_N`, and `w14_M` files contain retrospective migration-history loops. The migrant files at waves 12 and 14 also contain a secondary-migration stream. Each stream reports a move frequency but exposes at most three loop slots. When the enumerator marks repeated moves as identical, the first observed loop is retained as a compressed pattern with `represented_move_count` equal to the reported frequency; otherwise, observed loops represent one move each. No unobserved loop is fabricated.

| Recall accounting | Count |
|---|---:|
| Source rows with positive frequency | 931 |
| Reported moves | 2,290 |
| Observed loop/pattern records | 1,039 |
| Moves represented after identical-pattern compression | 2,126 |
| Reported moves not represented because of the three-loop cap/missing slots | 164 |
| Records with valid approximate timing | 854 |
| Records with an officially resolved district | 685 |
| Exact current-destination overlaps | 310 |
| Possible current-destination overlaps | 17 |
| Conservative recalled sensitivity records | 319 |
| Conservative recalled whole/partial-household records | 18 |

Most month responses encode both month and year. Because exact day is not public, the derived date uses day 5, 15, or 25 for beginning/middle/end, or day 15 when month-part is missing. Records without a valid inferred date are flagged. The public retrospective rural-destination district text fields are structurally empty in all six files: district-selection items exist, but there are zero valid associated district-text values. Resolved retrospective destinations therefore come from coded cities, explicit home/current-location relations, or the small set of named “other city” responses.

The 310 single-move records in the main migrant streams draw their destination from the same current-location block already used by the direct ledger and are exact overlaps. For multi-move main-migrant histories with at most three moves, the final loop may be the current destination; 17 such records are marked possible overlaps. Both groups are excluded from recalled sensitivity eligibility.

The recalled table is **not appended to the 573-event primary prospective ledger**. Its supported use is descriptive/sensitivity analysis of temporary and solo mobility. Only 18 non-overlapping, timed, district-resolved recalled records involve whole or partial households, which is too small to redefine the primary household-relocation design.

## Duplicate adjudication

Five respondent-wave pairs contain repeat public rows. Two pairs occur in the event-rich ledger; all five are documented in `bemp_respondent_duplicate_audit.csv`. Each pair retains the latest dated interview under a single prespecified rule, while all source rows remain available.

| Respondent-wave | Retained source row | Evidence and consequence |
|---|---:|---|
| `L09-Z03-HH10-H`, `w8` | 1,380 (2022-08-09) | Later and substantially more complete; respondent is available. The 2022-08-01 row registers a replacement household head under the same code. The retained row has no named endpoint, so the earlier Tangail response is not used. |
| `L30-Z03-HH02-LB`, `w14_M` | 217 (2024-02-13) | Latest completed re-interview. Both rows report Kurigram, but destination-reason responses differ; the earlier row remains available for sensitivity analysis. |
| `L06-Z03-HH16-H`, `w3` | 1,613 (2021-10-17) | Later and more complete than the 2021-09-10 row. |
| `L28-Z03-HH28-H`, `w10` | 1,308 (2022-11-07) | Later and more complete; the earlier row registers a replacement household head. |
| `L18-HH38-YM`, `w12_M` | 265 (2023-02-24) | Later and more complete. Its registration class is household head although the stable identifier ends `-YM`, showing that the suffix is a panel identifier rather than a time-varying role measure. |

The adjudication confidence is medium because the deposit does not state a formal supersession rule. A sensitivity analysis can swap retained rows without altering the raw ledger.

## Household-key reconciliation

Removing the final respondent suffix yields 1,704 syntactically valid, unique household prefixes across public respondent files. Of 1,703 prefixes observed at baseline, 1,684 contain exactly one public `-H` interview and 19 contain only female/youth interviews. `L30-Z02-HH12` first appears after baseline. No prefix has multiple public baseline heads or a malformed structure.

All prefixes remain recommended cluster/linkage keys because the codebook defines membership by the prefix through `HHzz`. The 19 no-head prefixes and one panel-only prefix are flagged medium confidence. They are not suitable for specifications requiring complete baseline-head covariates without explicit missing-data handling; the panel-only prefix must be excluded from any analysis requiring baseline exposure/covariates.

## Shock alignment and Stage 1 flow

The ledger retains concurrent home-village flood/erosion responses and the latest valid strictly earlier-wave response. Lagged fields are the defensible pre-event exposure screen; concurrent responses may overlap or follow the move.

| Criterion | Remaining |
|---|---:|
| All conservative event-rich records | 1,066 |
| Prospective new-destination event | 659 |
| Domestic new destination | 656 |
| Named city or rural district | 575 |
| Official containing district resolved | 575 |
| Retained after duplicate adjudication | 573 |
| Whole- or partial-household relocation | 264 |
| At least one lagged home shock response | 262 |
| Broad climate screen | 215 |

The broad climate screen is a screening definition, not a causal classification: it requires either a prior home-village flood/erosion “yes” or a realized-destination reason of “safer from flood/erosion.” The two components must be reported separately.

Within the 264 whole/partial-household events, 184 have a lagged shock “yes,” 58 select a climate-safety destination reason, and 27 meet both definitions. Thus the 215-record union consists of 157 lagged-shock-only, 31 stated-reason-only, and 27 overlapping records.

## Supported Stage 1 empirical design

The supported revealed outcome is the **official destination district** for 573 retained prospective domestic events: 291 originate from city responses and 282 from rural-district responses, resolving to 37 destination districts. Use all 573 as the endpoint-availability and general-mover benchmark. Use the 264 whole/partial-household moves as the main household-relocation sample. For the question specifically conditioned on a documented prior environmental shock, use the 184 household moves with a strictly earlier-wave home erosion/flood “yes” as the primary climate-related choice sample; use the 262 with observed lagged shock status for shocked-versus-not selection diagnostics. The 58 stated climate-safety cases and 215-record union remain descriptive/heterogeneity screens because destination reasons are post-choice (27 events meet both definitions).

The Stage 1 unit is an event, with standard errors and validation splits grouped at least by derived baseline household and preferably also tested by baseline `Lxx` location. City and rural responses are now harmonized to one district endpoint. Destination reasons and support variables remain post-choice measures and must not be treated as ex ante alternative attributes.

The feasibility verdict remains **YELLOW**: district-level destination choice is feasible; coordinate-level destination choice is not.

## Frozen pre-model decision rules

The following decisions are frozen for Stage 1:

1. The primary outcome sample is the 573 retained prospective domestic events with an official district endpoint.
2. The main household-relocation specification is the 264 whole/partial-household subset.
3. The primary climate-related definition is the 184 household moves with a strictly earlier-wave home flood/erosion “yes.” The 215-event union is a descriptive screen only, with its lagged-shock and post-choice stated-reason components always reported separately.
4. Recalled loops remain a separate sensitivity table and are never automatically appended to the prospective ledger.
5. The duplicate rule retains the latest dated interview; swapping to the earlier row is a prespecified sensitivity.
6. Household clustering uses the derived prefix through `HHzz`, with the 20 medium-confidence prefixes flagged and baseline-required analyses excluding the panel-only prefix.
7. Realized-destination reasons, support, work, rent, and hazard fields are post-choice measures, not ex ante alternative attributes.

The BEMP-only pre-model freeze is complete. Candidate destination sets, external GIS covariates, and distance/gravity/radiation baselines should be built only after explicit authorization for the modeling stage.
