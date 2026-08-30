# Project finalization and visual-story plan

## Production decision

The modeling stage is complete enough to freeze. The project should now move into publication production: lock the claims, write the paper, package reproducibility materials, and turn the results into a small visual narrative. New model variants should be added only if a reviewer-facing robustness question requires them.

## The one-sentence contribution

Among Bangladeshi households that moved, the attributes of candidate destinations add reproducible predictive information beyond distance and population; however, predicting whether a climate-affected household stays within its origin district is substantially more origin-specific.

## A simple human story

An anonymized BIHS household head reported moving in 2010 from Faridpur to Manikganj after river erosion caused the loss of land or homestead land. A model using only distance and destination population assigned Manikganj a 7.0% probability and ranked it sixth among Bangladesh's 64 districts. Adding GIS characteristics raised the probability to 13.7% and moved Manikganj to second place.

This is what the research adds: the move was not only a departure from an eroding place. It was also a choice among destinations with different physical, agricultural, urban, and accessibility profiles. Distance and city size explained part of that choice, but not all of it.

The household is anonymous. The survey does not provide a name, emotions, a complete biography, or a record of the household's private deliberation. Those details must not be invented. This event should be presented as an observed household journey, not as a fully reconstructed life story or a causal case study.

## Manuscript structure

1. **Abstract.** State the destination-choice question, the two datasets, the frozen comparison, the cross-dataset result, and the transportability boundary.
2. **Motivation.** Explain why climate-mobility research must study where people go, not only whether they leave.
3. **Data and event construction.** Describe BEMP and BIHS, linkage rules, origin/destination harmonization, shock-linked samples, candidate universes, and exclusions.
4. **Empirical design.** Define the revealed-choice task, gravity and radiation baselines, GIS model, grouped out-of-sample validation, leave-one-origin-out validation, and temporal validation.
5. **Results.** Lead with the cross-dataset forest plot, then the transportability comparison, calibration/ranking evidence, and the household illustration.
6. **Interpretation.** Separate the robust destination-attractiveness finding from the weaker and more origin-specific stay-versus-leave result.
7. **Limitations and ethics.** Cover administrative-district granularity, survey recall, observed rather than causal interpretation, candidate-set assumptions, anonymization, and the limits of the household narrative.
8. **Conclusion.** Destination environments matter, but the decision to cross an origin boundary requires locally specific information.

The appendix should contain the event-ledger construction, district crosswalk, variable provenance, sample-flow tables, model formulas, hyperparameter selection, coefficient tables, bootstrap procedure, complete validation matrix, sensitivity checks, and the frozen-file manifest.

## Visual package

### Static figures

1. **Main evidence forest plot:** cross-dataset GIS gains and household-cluster bootstrap intervals.
2. **Transportability figure:** grouped, leave-one-origin-out, and temporal validation side by side.
3. **One-household story:** erosion loss, Faridpur-to-Manikganj move, candidate choice, and the change in the observed destination's probability and rank.
4. **Appendix map:** event counts by origin and destination district, with no household-level disclosure.

### Interactive figures

1. **Evidence explorer:** filter by dataset, candidate universe, and validation scheme; read event counts, point estimates, and uncertainty.
2. **One-household journey:** toggle gravity versus GIS to see how the model redistributes probability across the 64 candidate districts.
3. **Optional publication supplement:** select an origin district and compare aggregate observed destination shares with gravity and GIS predictions. Build this only after the manuscript's main figures and tables are locked.

## Exact work order to finish the project

1. **Lock a claim sheet.** Freeze the primary estimand, samples, model names, numerical claims, and permitted interpretation in one page.
2. **Draft Results and Methods first.** These sections can be written directly from the frozen tables and are less likely to drift than an early introduction.
3. **Complete the visual system.** Finalize figure captions, legends, alt text, print-safe colors, and a consistent vocabulary across static and interactive versions.
4. **Write Introduction, Discussion, and abstract.** Use the verified evidence and the human story without overstating causality or person-level knowledge.
5. **Build the reproducibility release.** Add a top-level README, environment file, data-access instructions, one-command rebuild path, output manifest, and public/private data boundary.
6. **Run a publication audit.** Verify every reported number against a machine-readable table; check anonymization, citations, captions, cross-references, and all links.
7. **Prepare three outputs from one evidence base.** Produce the research paper, a seven-slide talk, and a 600–900 word public explainer centered on the household journey.

## Definition of done

The project is final when the manuscript and appendix are complete; every result is traceable to a frozen table; the static figures work in grayscale and at journal width; the interactives work at narrow and wide widths; the household narrative contains no invented details; and a new researcher can reproduce the final tables and figures from the documented inputs.
