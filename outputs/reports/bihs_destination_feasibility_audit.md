# BIHS broader-origin and external-replication feasibility audit

## Verdict

**YELLOW — public district-to-district origins and destinations are available and usable.**

The Bangladesh Integrated Household Survey (BIHS) materially expands the project. It does not publish migrant destination coordinates, but it supports two independent district-choice ledgers:

1. **Household-head relocation history (2015 Module B4):** 526 internal relocations with a previous district, the present household district, the year, and a reason. Exactly **123 moves are explicitly attributed to loss of land or homestead land from river erosion**.
2. **Current individual migrants (Modules V1, 2011–12/2015/2018–19):** 3,017 public domestic migrant records with a household origin district and current destination district. A conservative interval-specific R2/R3 sample contains **1,857 unique usable records from 1,404 households** after removing explicit and suspected repeats.

This is enough to test whether the frozen BEMP GIS model travels to all 64 origin districts and to a genuinely independent river-erosion relocation sample. It is not coordinate-level modeling and it does not identify a causal effect of shocks on the decision to migrate.

## Official files audited

The audit uses the original Stata files and English questionnaires from the official Harvard Dataverse releases. Download hashes were checked against the official metadata manifest in `data/raw/bihs/metadata/selected_file_manifest.csv`. No external GIS data were acquired for this expansion; the already frozen BEMP district universe and GIS features are reused unchanged.

The relevant questionnaire pages were rendered and visually inspected in `work/bihs/pdf_render/`:

- 2011–12: Negative Shocks (PDF pages 79–81) and Current Migrants (85–87)
- 2015: Household Relocation History (19–20), Negative Shocks (110–112), Current Migrants (116–118)
- 2018–19: Negative Shocks and Severe Disaster (162–166), Current Migrants (174–176)

The converted official codebooks were also checked against the Stata variable/value labels. The conversion copies in `work/bihs/codebooks_xlsx/` are inspection artifacts; the raw `.xls` files were not modified.

## Geography and linkage

### Household key

`a01` is the household identifier in all audited modules and waves. Decimal suffixes (for example, `10.1`, `10.2`) identify split households and must be preserved; the ledger stores `a01` as a canonical string. Within a wave, Module A provides one geography record per `a01`, and every retained V1/B4 event merges to exactly one origin record.

Across waves, exact `a01` links the same continuing or split household identifier. It is not safe to strip decimal suffixes or coerce split households back to the integer baseline ID.

### Person key

- R1 V1 provides `pid` values used to enumerate current migrants but no baseline roster-member key.
- R2 V1 provides `pid` plus `mid`, labelled “Baseline Household member id.”
- R3 V1 provides `pid_v1` plus `mid_v1`, labelled “Member id.”

For R2/R3, `a01 + mid` is the best public person linkage. Nineteen R3 domestic records reuse an R2-current-migrant `a01 + mid`; eleven have the same destination. They are conservatively excluded from the frozen interval-specific sample because the public files cannot prove whether these are new remigrations or repeated current-migrant stocks. R3 also contains 11 records explicitly flagged `del = 1` (“Migrated before the midline survey”) and two conflicting R3 records with the same `a01 + mid`; all are excluded.

### Origin geography

- R1 Module A publishes district name/code, upazila, union, and village code.
- R2 Module A publishes district, upazila, union, mouza, and village identifiers. The public `village_name` field is masked as `xxxxxx`.
- R3 Module A publishes numeric district/upazila/union/mouza/village identifiers. The 64 district codes have no value labels in the public Stata file. Every code is identified one-to-one by exact `a01` matches to R2 Module A; the complete derivation is in `bihs_district_crosswalk.csv`.

No household latitude/longitude/GPS field appears in the audited public files.

### Destination geography

V1 `v1_10` asks: **“If in-country, write zila code.”** All three waves use the same official 1–64 district list. B4 `b4_02` records the district from which the household head moved; current Module A geography supplies the revealed destination.

No destination upazila, union, village, latitude, longitude, migration distance, or coordinate precision flag is published in these modules. Destination geography is therefore exact administrative district, not anonymized coordinates.

## Household relocation ledger: Module B4

The official question text establishes the direction of the move:

- `b4_01`: “When did the head of the household move to this area/district?”
- `b4_02`: “Which area/district did the head of the household move to this area?” (the prior area/district; the grammar is imperfect, but the question sequence and B4_07 parallel verify direction)
- `b4_03`: “For which reason did you want to move to this area/city?”
- `b4_04`: number of home/house changes in the last five years

The official `b4_03` reason codes are:

1. land or homestead land lost due to river erosion
2. land lost for other reasons
3. moved because land is fertile
4. hope of comparatively better jobs
5. marital reasons
6. other

Among 6,436 R2 households, 565 report a prior district/country, of which 526 have a valid Bangladesh district. These 526 span 61 origin districts and 63 destination districts. There are 290 within-district area moves and 236 interdistrict moves. The river-erosion subset has 123 events (71 interdistrict); 120 have a plausible calendar year from 1900–2015, including 69 interdistrict events.

This ledger is unusually valuable because the environmental reason is event-specific, the mover is the household head, and origin and destination direction are directly observed. Its main limitation is retrospective timing: some moves occurred decades before survey, while the frozen GIS attributes are modern district summaries.

## Current-migrant ledger: Module V1

The three questionnaires define a current migrant as someone currently living away for at least six months, either abroad or within Bangladesh but not in the same upazila. Each person is reported on a separate row. Thus V1 is an individual current-migrant stock, not a whole-household relocation module.

| Wave | Current migrant rows | Domestic | Valid district | Frozen interval sample | Cross-district |
|---|---:|---:|---:|---:|---:|
| 2011–12 | 1,660 | 1,128 | 1,128 | supplementary only | — |
| 2015 | 634 | 487 | 474 | 474 | 366 |
| 2018–19 | 1,715 | 1,415 | 1,415 | 1,383 | 842 |
| **R2/R3 total** |  |  | 1,889 | **1,857** | **1,208** |

The frozen R2/R3 sample spans all 64 origin districts and 63 destination districts. The R1 stock adds 1,128 records but is kept supplementary because it lacks the roster member key needed to adjudicate repeats and its timing field contains long durations inconsistent with a narrow interval interpretation.

### Migration type and timing

V1 identifies current migrants away at least six months. It does not identify whether the move is intended to be permanent, whether the whole household moved, or whether the migrant later returned. The roster modules ask whether a member had been abroad and why that member returned, but those are return-from-abroad fields and do not convert V1 into a complete domestic migration spell history.

`v1_03` is labelled “When did migrate? (Year),” but public values are elapsed-looking integers (R2: 0–4; R3 mostly 0–6), not calendar years, and the questionnaire/codebook does not document a transformation rule. It is preserved exactly as `migration_elapsed_years_recorded` and is not used to impose event-level shock ordering in the frozen replication.

### Reasons and destination networks

`v1_12` records initial purpose: employment, education, marriage, health/treatment, escape war/violence, drought/famine/disease, business/self-employment, or other. In the frozen R2/R3 sample, employment is most common (854), followed by marriage (324) and education (249). Only six records use the drought/famine/disease category, so that field cannot sustain a climate-specific destination model by itself.

R2/R3 `v1_15` asks who helped in the migration process. Of 1,857 frozen records:

- 1,815 report friends/family at the migrated location;
- 8 report an agent in Bangladesh;
- 6 report both;
- 28 report other.

This is powerful descriptive evidence that destination networks matter, but it is not a pre-choice, destination-by-destination covariate. It should be reported as a mechanism and heterogeneity field, not inserted into the GIS utility function.

## Longitudinal environmental-shock fields

The negative-shock modules are household-level and repeat closely related categories:

- loss of home due to river erosion (`t1_02 = 6`; R3 also land erosion `t1b_01 = 43`)
- crop, livestock, productive asset, or consumption asset loss due to flood (`9`, `11`, `14`, `16`)
- crop/asset loss due to drought, storms, pests, disease, cyclone, or related causes (`10`, `15`, `101`, `111`, and wave-specific extensions)
- R3 too much rain, too little rain, and land erosion (`41`–`44`)

R1 records the last occurrence month/year within a five-year recall period. R2 records last occurrence month/year since the 2011 baseline. R3 records whether each shock occurred since midline and in the last 12 months, plus severity, but no exact year/month. R3 `t1c_01` and `t1c_02` identify the single biggest disaster in the last 12 months and five years.

Households with any broadly climate/environmental category number 894 in R1, 366 in R2, and 517 in R3 under the transparent code groupings used in the audit. These support household shock histories and descriptive overlap with migration. They do **not** support strict event-level temporal ordering for V1 without undocumented assumptions about `v1_03`.

## What can and cannot be distinguished

| Question | Public BIHS answer |
|---|---|
| Household linkage across waves | Yes: `a01`, preserving decimal split suffixes |
| Person linkage across R2/R3 V1 | Usually: `a01 + mid`; conservative repeat exclusions required |
| Origin coordinates | No |
| Destination coordinates | No |
| Origin admin geography | Yes: district in all waves; lower identifiers in Module A |
| Destination admin geography | Yes: district (`v1_10`; B4 prior/current district construction) |
| Migration distance | No direct field; GIS district distance can be constructed |
| Individual vs whole household | V1 is individual; B4 is household-head relocation; neither proves whole-household movement |
| Temporary/permanent | Only “current and away ≥6 months”; intended permanence absent |
| Return migration | No complete domestic return-spell measure; limited roster questions concern return from abroad |
| Reasons | Yes: V1 purpose; B4 reason, including explicit river erosion |
| Environmental shocks | Repeated household modules, but timing precision changes by wave |
| Destination networks | R2/R3 assistance category; no destination-specific network counts or locations |

## Consequential interpretation

The BEMP result is no longer resting on four erosion-prone origins. BIHS gives a national origin frame, an independent erosion-motivated household relocation sample nearly as large as the BEMP climate sample, and a much larger individual migrant sample. A successful replication would show that the GIS signal is not an artifact of BEMP’s narrow study geography or questionnaire. A failure would be equally informative: it would delimit the original result to shock-displaced households or specific origin environments.

The files do not justify a coordinate-level or causal shock-to-migration claim. The defensible claim is comparative predictive validity for revealed district destinations, conditional on observed relocation/migration.

## Produced artifacts

- `outputs/tables/bihs_file_inventory.csv`
- `outputs/tables/bihs_migration_variable_audit.csv`
- `outputs/tables/bihs_internal_migration_events.csv`
- `outputs/tables/bihs_household_relocation_events.csv`
- `outputs/tables/bihs_district_crosswalk.csv`
- `outputs/tables/bihs_sample_flow.csv`
- `outputs/tables/bihs_expansion_validation.csv`

