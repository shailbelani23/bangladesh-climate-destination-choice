# Bangladesh Environmental Mobility Panel feasibility audit

## Post-audit Stage 1 update (2026-08-28)

The recommended event-ledger, administrative-resolution, recalled-history, and linkage-reconciliation work has now been completed without estimating a model or joining GIS covariates. All 127 unique named public endpoints in the prospective ledger resolve to an official containing district, covering all 575 domestic new-destination records with named geography. After retaining the latest completed interview in each of two event-ledger duplicate pairs, the prospective district-endpoint sample contains 573 events; 264 are whole/partial-household moves and 215 meet the broad climate screen. A separate 1,039-record recalled-history table is retained for sensitivity use only. All superseded source rows remain visible. See `bemp_stage1_event_ledger_notes.md` and the output tables for the frozen evidence and rules.

## Research question and audit scope

This audit asks whether the public Bangladesh Environmental Mobility Panel (BEMP) release can support revealed destination-choice research conditional on migration after environmental shocks. It does not estimate a model and does not use external GIS data.

The audit covers the full handoff document, the BEMP README, all 20 quantitative CSV files, all 20 corresponding CSV codebooks, and the full variable-list workbook. The raw archives and metadata were preserved byte-for-byte under data/raw/bemp; both ZIP archives passed integrity tests, and copied-file SHA-256 hashes matched their source files.

The detailed variable-level evidence is in:

- outputs/tables/bemp_spatial_variables.csv: 538 verified spatial or access-related fields.
- outputs/tables/bemp_migration_variables.csv: 7,814 verified migration, reason, shock, network, housing, livelihood, and repeated-event fields.
- outputs/tables/bemp_file_inventory.csv: all released files, dimensions, sample type, identifiers, and key field counts.

“Missing %” in the output tables treats blank values and documented nonresponse/routing codes such as −55, −66, −6, −7, −8, and −9 as missing. It is therefore not the same as CSV blankness. Many high missing percentages are structurally caused by questionnaire routing.

## Raw-data structure

The release was arranged without altering raw files:

    data/raw/bemp/
      archives/
        bemp_quantitative_data_as_csv.zip
        bemp_codebooks_as_csv.zip
      quantitative/
        bemp_w1.csv ... bemp_w14_V.csv
      codebooks/
        bemp_w1_codebook.csv ... bemp_w14_V_codebook.csv
      metadata/
        bemp_variable_list_full.xlsx
        README.md

The quantitative archive contains the following 20 datasets:

| Wave/file | Rows | Columns | Sample or instrument |
|---|---:|---:|---|
| w1 | 2,170 | 1,767 | Baseline respondent |
| w1_V | 29 | 350 | Baseline village profile |
| w2 | 1,545 | 789 | Phone respondent |
| w3 | 1,612 | 915 | Phone respondent |
| w4 | 1,697 | 856 | Phone respondent |
| w5 | 1,686 | 1,172 | Phone respondent |
| w6_N | 2,273 | 2,736 | In-person non-migrant routing |
| w6_M | 221 | 3,006 | In-person migrant routing |
| w7 | 1,851 | 1,251 | Phone respondent |
| w8 | 1,852 | 1,017 | Phone respondent |
| w9 | 1,851 | 1,076 | Phone respondent |
| w10 | 1,852 | 1,114 | Phone respondent |
| w11 | 1,847 | 1,045 | Phone respondent |
| w12_N | 2,268 | 2,625 | In-person non-migrant routing |
| w12_M | 379 | 4,094 | In-person migrant routing |
| w12_V | 35 | 376 | Village profile |
| w13 | 1,845 | 172 | Phone respondent |
| w14_N | 2,232 | 2,865 | In-person non-migrant routing |
| w14_M | 481 | 4,523 | In-person migrant routing |
| w14_V | 32 | 499 | Village profile |

Every codebook has one row per quantitative-data column. The workbook contains 7,419 variable rows and 23 columns on one sheet, Variable list; the supplied README reports 7,420, so the one-row discrepancy should be treated as a release-documentation inconsistency rather than silently corrected.

## Systematic variable search

The workbook and every codebook were searched across variable names, standardized labels, blocks, English questions, item text, comments, and display logic. Broad screening hits in the workbook were: coordinate/location 1,012; administrative geography 1,398; origin/destination 355; migration 3,826; hazards 890; social networks 811; housing/land 673; livelihood 537; and access/services 137. These are screening counts, not counts of independent constructs: repeated waves, multiple-choice items, and looped migration events create extensive duplication.

No field was interpreted from its name alone. The output tables retain the exact English question/item, value labels, codebook comment, and routing logic needed to verify meaning.

## Linkage keys

### Respondent key

The exact cross-wave person key is the respondent code:

| Wave | Variable |
|---|---|
| w1 | w1_reg1 |
| w2–w5 | w2_reg1, w3_reg1, w4_reg1, w5_reg1 |
| w6_N / w6_M | w6_N_reg3 / w6_M_reg3 |
| w7–w11 | w7_reg2 ... w11_reg2 |
| w12_N / w12_M | w12_N_reg3 / w12_M_reg3 |
| w13 | w13_reg2 |
| w14_N / w14_M | w14_N_reg3 / w14_M_reg3 |

The codebook documents the form Lxx-Zyy-HHzz-suffix, with no zone segment for L10, L17, and L18. The suffix identifies respondent role, principally household head (H), spouse/female adult (F), young female (YF), young male (YM), and local leader (LB); a few later codes include numbered role suffixes.

The Lxx and zone portions were assigned at baseline and remain fixed after a respondent moves. They identify the baseline sampling location, not current residence.

### Household key

There is no separate public household-ID field consistently available across waves. The usable household key is derived by removing the final respondent-role suffix from the respondent code. Respondents with the same prefix through HHzz are documented as belonging to the same baseline household.

The reconciliation is complete. Across all respondent files there are 1,704 unique, structurally valid prefixes. Of 1,703 prefixes observed in w1, 1,684 contain exactly one public H-suffixed respondent and 19 contain only female/youth respondents; no prefix contains multiple public baseline heads. One prefix, `L30-Z02-HH12`, first appears after baseline. The 20 exceptional prefixes remain usable for linkage/clustering at medium confidence, but the panel-only prefix cannot enter analyses requiring baseline covariates and the 19 no-head prefixes require explicit missingness handling for head attributes.

Five respondent-wave pairs contain duplicate exact codes: one pair each in w3, w8, w10, w12_M, and w14_M. The frozen rule retains the latest dated interview and preserves both rows in `bemp_respondent_duplicate_audit.csv`. Two of these pairs occur in the prospective event-rich ledger and are also shown in `bemp_duplicate_adjudication.csv`.

### Baseline sampling-location key

Village-profile records use w1_V_reg1, w12_V_reg2, and w14_V_reg2 (“Location Number”), with Lxx values. The respondent code’s leading Lxx can therefore be linked to public village-profile information when that location appears in the corresponding profile. Lxx is pseudonymized and is not a public village name or coordinate.

## Exactly what public geography is available

### Coordinates

- Baseline origin latitude/longitude: not public.
- Migrant destination latitude/longitude: not public.
- Jittered respondent or household coordinates: not found.
- Village centroid coordinates: not found.

There were no latitude, longitude, GPS, coordinate, easting, northing, or comparable endpoint fields in any quantitative header or verified codebook question. The repeated codebook warning is explicit: “Geographic identifiers below the district level were removed from the published dataset to protect participant confidentiality.”

The data contain coordinate-derived distances, which proves that confidential house locations existed during data production; it does not make the endpoints recoverable.

### Origin geography

The public baseline origin is recoverable at district level:

- w1_V_reg1: pseudonymized Lxx baseline location.
- w1_V_q4: baseline district; 29/29 valid, 10 raw spellings representing the seven study-area districts after spelling normalization.
- Respondent-code codebook comment: maps all Lxx groups to baseline districts.

The documented mapping is Bogra/Bogura L19–L21; Gaibandha L23; Jamalpur L01 and L22; Kurigram L24–L36; Manikganj L04–L06; Sirajganj L07–L09; and Tangail L02–L03 and L10–L18.

Union, upazila, named village, and exact baseline coordinates are suppressed. Lxx may be used as a fixed-effect or grouped-origin code, but it must not be described as a named village.

### Destination geography

For domestic migrant destinations, the public release provides:

- city versus village;
- a coded list of named cities plus an “other” text field for urban destinations;
- district and division text for rural destinations;
- relational indicators for home village, prior migration destination, or another location.

It does not provide the named rural village, union, upazila, or coordinates. Destination geography is therefore heterogeneous in its raw form: city for urban moves and district for rural moves. A defensible analysis should harmonize both to destination district, preserving urban/rural as a separate attribute.

The most important endpoint variables are:

| Exact variable | Wave/file | Verified meaning | Observed dtype | Valid n | Missing % | Unique valid | Examples | Granularity/privacy |
|---|---|---|---|---:|---:|---:|---|---|
| w6_M_q14 | w6_M | Did the respondent go to a city or village? | integer-coded | 187 | 15.38 | 2 | City; Village | settlement type; categorized |
| w6_M_q15 / q15_txt | w6_M | Name of city | integer-coded / string | 60 / 6 | 72.85 / 97.29 | 9 / 6 | Dhaka, Gazipur; Savar, Alenga | named city; no coordinates |
| w6_M_q16x5_txt | w6_M | District component of rural destination | string | 111 | 49.77 | 29 raw spellings | Tangail, Kurigram, Jamalpur | district retained; lower units removed |
| w6_M_q16x6_txt | w6_M | Division component of rural destination | string | 44 | 80.09 | 9 raw spellings | Dhaka, Rajshahi, Rangpur | division retained; lower units removed |
| w12_M_q16 | w12_M | Same prior destination or another location | integer-coded | 155 | 59.10 | 2 | prior destination; another location | relational only |
| w12_M_q17 | w12_M | Domestic or abroad for a new location | integer-coded | 177 | 53.30 | 1 public valid category | In Bangladesh | country/internal status |
| w12_M_q19 | w12_M | City or village at current destination | integer-coded | 294 | 22.43 | 2 | City; Village | settlement type |
| w12_M_q20 / q20_txt | w12_M | Name of city for a new destination | integer-coded / string | 85 / 9 | 77.57 / 97.63 | 11 / 9 | Dhaka, Tangail; Savar, Cox’s Bazar | named city; no coordinates |
| w12_M_q21x5_txt | w12_M | District component of rural destination | string | 118 | 68.87 | 21 raw spellings | Tangail, Bogura, Kurigram | district retained; lower units removed |
| w12_M_q21x6_txt | w12_M | Division component of rural destination | string | 81 | 78.63 | 6 raw spellings | Dhaka, Rajshahi, Rangpur | division retained; lower units removed |
| w14_M_q16 | w14_M | Same prior destination or another location | integer-coded | 262 | 45.53 | 2 | prior destination; another location | relational only |
| w14_M_q17 | w14_M | Domestic or abroad for a new location | integer-coded | 150 | 68.81 | 1 public valid category | In Bangladesh | country/internal status |
| w14_M_q19 | w14_M | City or village at current destination | integer-coded | 383 | 20.37 | 2 | City; Village | settlement type |
| w14_M_q20 / q20_txt | w14_M | Name of city for a new destination | integer-coded / string | 53 / 10 | 88.98 / 97.92 | 11 / 8 | Dhaka, Gazipur; Cumilla, Feni | named city; no coordinates |
| w14_M_q21x5_txt | w14_M | District component of rural destination | string | 74 | 84.62 | 16 raw spellings | Kurigram, Tangail, Jamalpur | district retained; lower units removed |
| w14_M_q21x6_txt | w14_M | Division component of rural destination | string | 44 | 90.85 | 4 raw spellings | Rangpur, Dhaka, Rajshahi | division retained; lower units removed |

The high wave-12 and wave-14 missing rates do not mean that all prior destinations are lost. The verified skip logic asks a specific city/district only if the respondent is in another location or was a non-migrant in the prior wave. If the person remains at the previous migration destination, q16 carries that endpoint forward relationally.

Among records where a new domestic destination was actually elicited:

| Wave | New domestic location reports | Named city or rural district available | Coverage |
|---|---:|---:|---:|
| w6_M | 187 analyzable current migrant locations | 171 | 91.4% |
| w7 | 69 | 57 | 82.6% |
| w8 | 63 | 53 | 84.1% |
| w9 | 33 | 29 | 87.9% |
| w10 | 42 | 38 | 90.5% |
| w11 | 40 | 31 | 77.5% |
| w12_M | 177 | 170 | 96.0% |
| w13 | 82 | 70 | 85.4% |
| w14_M | 150 | 127 | 84.7% |
| Total raw wave-events | 843 | 746 | 88.5% |

These are screening counts before exact longitudinal event reconstruction, duplicate-ID resolution, and exclusion of repeat observations of the same destination. They show that destination admin geography is not merely anecdotal.

One w12_M urban record uses city code 17, but code 17 has no label in any of the public city codebooks. It is excluded from the named-endpoint count and retained as an unresolved public code; assigning it a place would be an unsupported guess.

One routing anomaly requires explicit handling: w12_M_q21x5_txt contains a district for 31 respondents coded by w12_M_q16 as still in the previous destination, despite codebook logic saying q21 should be asked only for a different destination. Wave 14 follows the documented routing exactly. The wave-12 values may be prefilled carry-forward information or an implementation inconsistency; they should not independently define a new move.

### Migration distance

The public release includes dist_from_prev_loc in w6_N, w6_M, w12_N, w12_M, w14_N, and w14_M. The codebook definition is the distance in meters between the respondent’s house in the previous in-person survey and the house in the current survey, calculated from confidential house locations.

| Variable | Valid n | Missing % | Unique valid | Interpretation |
|---|---:|---:|---:|---|
| w6_M_dist_from_prev_loc | 65 | 70.59 | 65 | meters between prior and current in-person house; endpoints withheld |
| w12_M_dist_from_prev_loc | 155 | 59.10 | 153 | same |
| w14_M_dist_from_prev_loc | 221 | 54.05 | 217 | same |

Distance is available but has no direction and does not identify the chosen destination. It is concentrated among whole-household movers: of valid migrant-wave distances with a valid current move-type response, 54/62 in w6_M, 132/152 in w12_M, and 196/216 in w14_M are whole-household moves. Distance should be an auxiliary outcome/validation field, not a substitute endpoint.

The N files and w1 also contain distance from the current and prior Jamuna riverbank. For example, w1_dist_from_crrnt_river_bank has 1,987 valid values (8.43% missing), w6_N has 1,801, w12_N has 1,769, and w14_N has 1,597. The codebook says these were derived in ArcGIS from confidential house locations and manually delineated Sentinel-2 riverbanks. They are valuable longitudinal hazard-proximity measures but do not reveal house coordinates.

## Migration event content

### Individual versus household migration

The current-move variables directly distinguish whole-household, part-household, and solo migration:

| Variable | Valid n | Missing % | Whole household | Part household | Alone |
|---|---:|---:|---:|---:|---:|
| w6_M_q19 | 181 | 18.10 | 69 | 19 | 93 |
| w12_M_q24 | 302 | 20.32 | 165 | 28 | 109 |
| w14_M_q24 | 377 | 21.62 | 227 | 25 | 125 |

Multiple-choice “Migration Participants” fields also identify which respondent, spouse, parents, siblings, children, extended family, and others participated. The panel can therefore distinguish a respondent move from a household relocation rather than treating every migrant record as household displacement.

### Temporary, permanent, and return migration

Previous-migration type is recorded longitudinally:

- w12_M_reg11: 49 temporary and 106 permanent among 155 valid.
- w14_M_reg12: 84 temporary and 178 permanent among 262 valid.
- Corresponding prior-type fields exist in phone waves w7–w11 and w13.

Return intention is directly observed:

- w6_M_q67: 79 plan to return and 87 do not, among 166 valid.
- w12_M_q80: 42 yes and 108 no, among 150 valid.
- w14_M_q91: 36 yes and 95 no, among 131 valid.

Phone-wave current-location fields distinguish home village, prior migration destination, and another location. The in-person migrant waves distinguish prior destination versus another location. Timing, duration, seasonality, return plans, prior location, and repeated “secondary migration”/Loop 1–3 blocks permit temporary, permanent, onward, and return events to be constructed.

The retrospective loop audit adds an important constraint. Across eight history streams in six in-person files, 931 source rows report 2,290 moves, but only 1,039 loop/pattern records are public. “Identical moves” compression represents 2,126 of the reported moves; 164 remain unrepresented because the instrument exposes at most three loops or an expected loop is missing. Most timing categories encode month and year, while day is only approximated from beginning/middle/end of month. The public rural-destination district text associated with these historical loops has zero valid values in every file, so retrospective district endpoints are available mainly for coded cities and explicit home/current-location relations.

The recalled table resolves 685 records to districts, but 310 are exact duplicates of the migrant current-location block and 17 are possible final-loop/current-destination overlaps. After excluding overlaps and invalid timing, 319 recalled records remain for a conservative sensitivity sample; only 18 are whole/partial-household moves. Recalled loops therefore do not expand the primary household destination-choice sample in a useful or clean way and are not appended to the prospective ledger.

There is no single universal public migration-event ID. A reproducible event key must be constructed from respondent code + wave + questionnaire event block/loop + within-block event order. Relational “same prior destination” responses must carry the last verified endpoint forward; they must not be counted as new destination choices.

### Reasons for moving and destination choice

Reasons are unusually detailed. Baseline and repeated migration-history blocks include single/repeated erosion, monsoon flooding, sudden disasters, drought/water shortage, other environmental reasons, livelihoods and income, unemployment, lack of farmland, unreliable harvest/crop failure, property loss, marriage/family, education, health, roads, insecurity, forced movement, and other reasons.

The realized current-destination reason battery is especially relevant:

| Variables | Wave | Selected counts among valid routed cases |
|---|---|---|
| w6_M_q62x1–x4 | w6_M | relatives 24; better earning 102; safer from flood 15; safer from erosion 47 (n=172) |
| w12_M_q75x1–x4 | w12_M | relatives 11; better earning 85; safer from flood 12; safer from erosion 39 (n=150) |
| w14_M_q85x1–x4 | w14_M | relatives 21; better earning 64; safer from flood 5; safer from erosion 30 (n=131) |
| w14_M_q85x7 | w14_M | already had house/land there: 13 (n=131) |

These fields can define or validate a climate-related-move subgroup. They should not be treated as exogenous pre-choice attributes: they are self-reported explanations after the destination is realized.

## Environmental shocks available longitudinally

The panel provides repeated home-village flood and erosion occurrence in every post-baseline wave:

- Erosion (Home Village) Occurrence: w2_q85, w3_q105, w4_q99, w5_q141, w6_N_q234 / w6_M_q257, w7_q141, w8_q116, w9_q116, w10_q137, w11_q120, w12_N_q227 / w12_M_q304, w13_q12, w14_N_q258 / w14_M_q359.
- Flood (Home Village) Occurrence: w2_q104, w3_q124, w4_q118, w5_q160, w6_N_q269 / w6_M_q310, w7_q168, w8_q138, w9_q139, w10_q160, w11_q143, w12_N_q261 / w12_M_q357, w13_q20, w14_N_q291 / w14_M_q411.

The reference period changes with survey cadence: usually the last month in phone surveys and the named year or monsoon season in in-person surveys. Harmonization must therefore use exposure windows, not assume identical recall periods.

Migrant files also contain exposure at the realized migration location:

- Erosion: w6_M_q283, w12_M_q330, w14_M_q385.
- Flooding: w6_M_q337, w12_M_q383, w14_M_q437.

Detailed follow-ups cover household impact, ranked impact type, severity, duration, house flooding/water height, land lost, recovery, coping, and perceived future risk. The objective Jamuna riverbank-distance fields add a geographically derived hazard-proximity measure for baseline/N in-person observations. Migrant destinations have self-reported hazard occurrence/impact but no public coordinate-derived riverbank distance.

For event construction, the cleanest temporal exposure is the last home-village erosion/flood occurrence and impact measured before the move. Destination-location shock reports occur after choice and belong in validation or post-move adaptation analyses.

## Destination social networks

The public data contain meaningful realized-destination network measures:

- “Relatives are there” in w6_M_q62x1, w12_M_q75x1, and w14_M_q85x1.
- Move preparation includes contacting family/relatives and contacting friends.
- Family Support Location fields distinguish support at the migration location.
- External Support Receipt and External Support Type Family fields are separated for individual and whole-household migration modules.
- w14_M_q87 identifies husband’s versus wife’s family among a small routed subset (17 valid).
- w14_M_q143 reports relatives’ location distribution: 296 valid responses across categories ranging from almost all in the current location to almost all elsewhere in Bangladesh.
- w14_M_q158 asks whether the migrant had contact in the last year at the migration location: 241 valid, including 56 “yes.”

These are not dyadic network counts for every candidate destination. Most are measured at the chosen destination or are post-choice support outcomes. They are suitable for mechanism descriptions, subgroup analysis, and selection diagnostics, but not as alternative-specific predictors in a revealed-choice model unless an external pre-move network matrix is later obtained.

## Housing, livelihood, and access fields

The release has extensive repeated fields on house ownership and structure, land/plot ownership and loss, rental/tenure arrangements, agricultural land and harvests, occupations, employers and job search, earnings/income, market access, roads and transport, schools, and health facilities. The detailed output tables preserve every matched variable and exact question.

For Stage 1, the defensible pre-choice covariates are household/respondent characteristics and home-origin shock histories observed before the move. Conditions reported only at the realized destination—rent, work, support, hazard experience, services—are outcomes or mechanisms unless converted to destination-wide attributes from an external source later.

## Direct answers to the feasibility questions

| Question | Finding |
|---|---|
| Respondent linkage key | Exact respondent code (wave-specific reg field listed above) |
| Household linkage key | Derived respondent-code prefix through HHzz; no separate universal public HH ID |
| Baseline origin coordinates | No |
| Migrant destination coordinates | No |
| Jittered coordinates | No evidence of any public coordinate field |
| Origin admin identifiers | District recoverable from Lxx/codebook and w1_V; lower units suppressed |
| Destination admin identifiers | Named city for urban moves; district/division for rural moves; lower units suppressed |
| Migration distance | Yes, coordinate-derived meters for in-person wave pairs, but endpoints/direction withheld |
| Individual versus whole household | Yes: whole, part, alone plus participant identities |
| Temporary versus permanent | Yes, as prior migration type in later waves |
| Return migration | Yes: home/prior/new location states, return plans, timing/duration; must be event-constructed |
| Reasons for moving | Yes, including erosion, flood, livelihood, family, property, services, safety, and other causes |
| Longitudinal environmental shocks | Yes, home-village erosion/flood every post-baseline wave plus impacts; destination shocks for migrants |
| Destination networks | Yes at the realized destination, but not for every alternative |
| Retrospective history usability | Separate sensitivity only: timing/overlap/compression flags required; public rural loop district text is empty |

## Most consequential limitations

1. Exact or jittered origins and destinations are not public, so settlement-level GIS choice, fine network distance, floodplain intersection, and raster-cell alternatives cannot be estimated from the public BEMP alone.
2. Destination geography must be harmonized from city names and rural district text. The prospective crosswalk now completes this official city/locality-to-district mapping, but it remains a versioned cleaning dependency rather than original BEMP geography.
3. Public origin is district/Lxx, not the actual pre-move house. District-centroid distance will be a coarse baseline; dist_from_prev_loc can validate distance distributions but cannot reveal the endpoint.
4. Destination fields are routed. A blank city/district often means “same prior destination,” rural/city mismatch, panel dropout, or a documented nonresponse code. Naive complete-case filtering would discard valid persistent destinations and can bias toward recent movers.
5. Temporary/permanent status is often observed in the following survey’s “previous migration type,” so event classification is longitudinal.
6. Social-network and destination-condition fields are mostly realized-destination measures; using them as pre-choice predictors would introduce post-choice leakage.
7. Raw city/district spellings and the few duplicate person IDs require a versioned cleaning crosswalk and explicit duplicate adjudication.
8. Retrospective histories are capped at three loop slots, may compress identical repeated moves, and partly duplicate the current migrant destination. Their public rural district text is structurally empty.

## Recommended Stage 1 empirical design supported by the public fields

### Estimand

Estimate the probability that an internal mover chooses destination district j, conditional on making a move, as a function of origin-to-destination separation and destination-level attributes. This is a district-level revealed-choice design, not a village- or coordinate-level design.

### Event construction

1. Build the person panel with the exact respondent code and derive the household prefix through HHzz.
2. Create the primary prospective ledger from the first observed `w6_M` destination, phone-wave home/prior/another-location transitions, and new-destination branches in `w12_M` and `w14_M`. Keep retrospective and baseline histories separate.
3. Define `event_id` as respondent code + wave + event branch + source row; define separate recalled-record IDs from respondent + wave + history stream + loop.
4. Carry the last verified city/district forward only when the questionnaire explicitly says “previous migration destination.” Do not create a new event for persistence.
5. Treat phone-wave returns to the baseline home as return events and onward moves to another location as new choices.
6. Retain the latest dated interview in each duplicate respondent-wave pair, preserve all source rows in the audit, and flag the 20 medium-confidence household prefixes.

### Primary analytic sample

Use new internal moves with:

- a harmonizable destination district;
- a recoverable baseline origin district;
- move timing sufficient to align a pre-move exposure window; and
- whole- or part-household migration for the main household-relocation specification.

Use all 573 retained district-endpoint events as the general-mover benchmark and the 264 whole/partial-household events as the main household-relocation sample. For the climate-related choice question, use the 184 household events with a strictly earlier-wave home erosion/flood “yes” as the primary definition; use the 262 household events with observed lagged shock status for selection diagnostics. The 58 stated climate-safety cases and the 215-event union are descriptive/heterogeneity screens because the stated reason is measured after choice (27 events meet both definitions). Use solo movers in a prespecified secondary specification. Classify temporary/permanent from the subsequent prior-migration-type field where necessary.

### Choice alternatives and baselines

The preferred outcome is destination district. A versioned official city/locality-to-district crosswalk has now been introduced; candidate sets should be prespecified and sensitivity-tested:

- all destination districts observed in the BEMP event ledger;
- all Bangladesh districts once an official district universe is added; and
- a restricted plausible set by origin and observed migration radius.

After GIS data are authorized in a later stage, compare:

1. distance-only conditional logit;
2. gravity baseline using destination population;
3. radiation-style opportunity baseline;
4. enriched district-choice model with hazard, labor-market, accessibility, service, land/housing, and urban-form attributes.

The public dist_from_prev_loc should validate/coarsely calibrate the distance component and support a secondary migration-distance model for events whose endpoint remains unavailable. It should not be reverse-engineered into a destination.

### Identification and validation

- Frame results as predictive/associational destination choice conditional on moving, not a causal effect of environmental shocks on migration.
- Use only pre-move BEMP characteristics in the choice model. Reserve realized-destination reasons, support, jobs, rent, and post-move hazards for mechanisms and validation.
- Cluster uncertainty at the baseline household prefix and include origin-district or Lxx strata where supported.
- Split validation by time (earlier versus later waves) and by origin location/district; never randomly split repeated events from the same household across train and test.
- Report endpoint availability and model performance separately for whole-household, solo, temporary, permanent, return, erosion-related, and flood-related moves.
- Add an explicit selection analysis comparing events with and without usable destination admin data, using migration type, distance availability, wave, and origin.

### Stage 1 deliverable

The BEMP-only pre-model freeze is complete: event ledger, respondent-wave state, destination-admin crosswalk, recalled-history sensitivity table, respondent duplicate audit, household-prefix reconciliation, provenance columns, attrition flows, and frozen sample rules are documented and validated. No model, candidate alternative set, external GIS join, gravity baseline, or radiation baseline has been built.

## Verdict

**YELLOW — admin-unit destinations are available and still usable.**
