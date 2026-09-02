import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = path.resolve(process.cwd());
const OUT = path.join(ROOT, "publication", "presentation");
const QA = path.join(ROOT, "work", "presentation_build", "rendered");

const C = {
  ink: "#111827",
  muted: "#556070",
  panel: "#F2F4F7",
  rule: "#CBD1D9",
  blue: "#1877C9",
  blueLight: "#DDF0FC",
  green: "#147D64",
  orange: "#C66A15",
  white: "#FFFFFF",
};
const FONT = "Arial";

async function bytes(file) {
  const b = await fs.readFile(file);
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
}

function box(slide, name, left, top, width, height, fill = "none", line = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry: "rect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: lineWidth },
  });
}

function text(slide, name, value, left, top, width, height, size, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = {
    fontFamily: FONT,
    fontSize: size,
    bold: Boolean(opts.bold),
    color: opts.color || C.ink,
    alignment: opts.align || "left",
    verticalAlignment: opts.valign || "top",
  };
  return shape;
}

function header(slide, title, kicker, number) {
  text(slide, `kicker-${number}`, kicker.toUpperCase(), 52, 34, 420, 24, 13, { bold: true, color: C.blue });
  text(slide, `title-${number}`, title, 52, 70, 1176, 72, 38, { bold: true });
  box(slide, `header-rule-${number}`, 52, 151, 1176, 2, C.ink);
  text(slide, `number-${number}`, String(number).padStart(2, "0"), 1178, 680, 50, 18, 11, { align: "right", color: C.muted });
}

function notes(slide, body, sources) {
  slide.speakerNotes.textFrame.setText(`${body}\n\n[Sources]\n${sources.join("\n")}\n[/Sources]`);
  slide.speakerNotes.setVisible(true);
}

async function addImage(slide, name, file, position, alt, fit = "contain") {
  slide.images.add({
    blob: await bytes(file),
    contentType: "image/png",
    name,
    alt,
    fit,
    position,
  });
}

async function main() {
  await fs.mkdir(OUT, { recursive: true });
  await fs.mkdir(QA, { recursive: true });

  const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  // 1. Cover: adapted from Codex Grid slide 08 (half text, half image).
  {
    const s = p.slides.add();
    s.background.fill = C.white;
    box(s, "cover-accent", 52, 46, 10, 100, C.blue);
    text(s, "cover-kicker", "BANGLADESH • CLIMATE MOBILITY", 86, 51, 470, 28, 14, { bold: true, color: C.blue });
    text(s, "cover-title", "Where do climate-affected households go?", 52, 178, 560, 210, 54, { bold: true });
    text(s, "cover-subtitle", "Revealed destination choice after flood and river erosion", 52, 414, 540, 72, 23, { color: C.muted });
    text(s, "cover-author", "Shail Belani  •  Undergraduate Researcher\nNorthwestern University", 52, 574, 560, 58, 16, { color: C.ink });
    await addImage(s, "cover-map", path.join(ROOT, "outputs/figures/anonymized_household_destination_story.png"), { left: 644, top: 44, width: 584, height: 590 }, "Map and probability comparison for an anonymized household that moved from Faridpur to Manikganj after river erosion.");
    text(s, "cover-number", "01", 1178, 680, 50, 18, 11, { align: "right", color: C.muted });
    notes(s, "Open with the household, not the model. One surveyed household lost land and a homestead to river erosion, then moved from Faridpur to Manikganj in 2010. The study asks why that district became the destination.", [
      "Local frozen output: outputs/figures/anonymized_household_destination_story.png",
      "BIHS public-use surveys: https://doi.org/10.7910/DVN/OR6MHT",
    ]);
  }

  // 2. Human story: adapted from Codex Grid slide 17 (timeline).
  {
    const s = p.slides.add();
    s.background.fill = C.white;
    header(s, "A lost homestead became a destination decision", "One anonymized household", 2);
    const y = 330;
    box(s, "timeline", 120, y, 1040, 3, C.rule);
    const points = [190, 640, 1090];
    const titles = ["River erosion", "Move in 2010", "Manikganj chosen"];
    const bodies = [
      "The survey records loss of land or homestead as the reason for moving.",
      "The household leaves Faridpur. Its exact address and identity remain private.",
      "Among 64 districts, the GIS model ranks the observed destination 2nd; gravity ranks it 6th.",
    ];
    for (let i = 0; i < 3; i++) {
      box(s, `dot-${i}`, points[i] - 9, y - 8, 18, 18, i === 2 ? C.blue : C.ink);
      text(s, `step-title-${i}`, titles[i], points[i] - 150, 218, 300, 48, 24, { bold: true, align: "center" });
      text(s, `step-body-${i}`, bodies[i], points[i] - 154, 374, 308, 120, 17, { align: "center", color: C.muted });
    }
    box(s, "prob-strip", 366, 555, 548, 60, C.blueLight);
    text(s, "probability", "Observed-destination probability: 7.0% gravity  →  13.7% GIS", 390, 573, 500, 30, 18, { bold: true, align: "center", color: C.blue });
    notes(s, "This is the central human story. The probabilities are out-of-fold predictions, so the model did not train on this household when scoring it. The example illustrates prediction, not a causal claim about why the family moved.", [
      "Local frozen out-of-fold prediction table and figure: outputs/figures/anonymized_household_destination_story.png",
      "BIHS migration module documentation: https://doi.org/10.7910/DVN/OR6MHT",
    ]);
  }

  // 3. Empirical design: adapted from Codex Grid slide 07 (three-column process).
  {
    const s = p.slides.add();
    s.background.fill = C.white;
    header(s, "The test is simple: can destination geography beat distance?", "Empirical design", 3);
    const cols = [52, 452, 852];
    const labels = ["1  Observe a move", "2  Offer 64 districts", "3  Score the choice"];
    const copy = [
      "BEMP and BIHS identify an origin district, an observed destination district, and a migration event.",
      "Every Bangladeshi district is a candidate. The baseline uses distance and population; the expanded model adds GIS measures.",
      "Grouped cross-validation asks how much probability each model assigns to the destination that was actually chosen.",
    ];
    const accents = [C.orange, C.blue, C.green];
    for (let i = 0; i < 3; i++) {
      box(s, `method-panel-${i}`, cols[i], 216, 350, 344, C.panel);
      box(s, `method-accent-${i}`, cols[i], 216, 350, 9, accents[i]);
      text(s, `method-label-${i}`, labels[i], cols[i] + 26, 247, 296, 60, 23, { bold: true });
      text(s, `method-copy-${i}`, copy[i], cols[i] + 26, 326, 296, 150, 18, { color: C.muted });
    }
    text(s, "method-footer", "Households stay in one fold; harder tests also withhold whole origins and a later wave.", 52, 600, 960, 36, 18, { bold: true, color: C.ink });
    notes(s, "The comparison is between a transparent distance-population baseline and a GIS-expanded conditional logit. Main estimates group validation folds by household. Separate origin-held-out and later-wave tests ask whether the destination utility travels. The outcome is observed district choice conditional on moving, not whether a household moves.", [
      "Local methods and frozen claims: publication/manuscript/manuscript.md",
      "Radiation model: https://doi.org/10.1038/nature10856",
      "Global Human Settlement Layer: https://doi.org/10.2760/098587",
    ]);
  }

  // 4. Independent replication and transport: adapted from Codex Grid slide 21.
  {
    const s = p.slides.add();
    s.background.fill = C.white;
    header(s, "The BIHS result survives unseen origins and a later wave", "Independent replication", 4);
    await addImage(s, "transport-plot", path.join(ROOT, "outputs/figures/validation_transportability_comparison.png"), { left: 52, top: 178, width: 760, height: 450 }, "Comparison of grouped, leave-one-origin-out, and later-wave log-loss gains in BIHS and climate-specific samples.");
    box(s, "result-rail", 850, 190, 378, 390, C.panel);
    text(s, "result-stat-1", "+0.101", 880, 232, 320, 62, 38, { bold: true, color: C.blue });
    text(s, "result-desc-1", "Leave one origin out\n1,857 BIHS migrants", 880, 302, 310, 66, 18, { color: C.muted });
    box(s, "result-rule", 880, 390, 286, 2, C.rule);
    text(s, "result-stat-2", "+0.094", 880, 422, 320, 62, 38, { bold: true, color: C.green });
    text(s, "result-desc-2", "Train 2015, test 2018–19\n1,383 later-wave migrants", 880, 492, 310, 66, 18, { color: C.muted });
    text(s, "result-note", "Held-out log-loss improvement over fitted gravity. Positive values favor GIS.", 850, 603, 378, 52, 14, { color: C.muted });
    notes(s, "Lead with the independent BIHS transport result. The sample covers all 64 origin districts. GIS retains a 0.101 log-loss gain when each test origin is removed from training and a 0.094 gain when a 2015 model predicts 2018–19 migrants. These are not climate-labeled migrants; they test geographic and temporal portability of the destination specification.", [
      "Local validation output: outputs/tables/bihs_replication_validation.csv",
      "BIHS public-use data: https://doi.org/10.7910/DVN/OR6MHT",
    ]);
  }

  // 5. Climate-specific replication: adapted from Codex Grid slide 22.
  {
    const s = p.slides.add();
    s.background.fill = C.white;
    header(s, "Two climate samples reproduce the grouped gain", "Climate-specific evidence", 5);
    await addImage(s, "forest-plot", path.join(ROOT, "outputs/figures/cross_dataset_gis_gain_forest.png"), { left: 52, top: 180, width: 710, height: 430 }, "Forest plot of held-out log-loss gains from adding GIS variables to fitted gravity across BEMP and BIHS samples.");
    text(s, "validation-head", "Same model, different surveys", 820, 205, 360, 42, 23, { bold: true });
    box(s, "validation-blue", 820, 275, 14, 105, C.blue);
    text(s, "validation-good", "BIHS erosion moves: +0.098 across 123 relocations from 29 origins.", 858, 270, 330, 120, 19, { color: C.ink });
    box(s, "validation-orange", 820, 435, 14, 105, C.orange);
    text(s, "validation-caution", "BEMP shock-linked moves: +0.108 across 184 later relocations from 7 origins.", 858, 430, 330, 120, 19, { color: C.ink });
    notes(s, "The climate-specific samples use the same destination outcome and fixed feature set. BIHS independently identifies erosion-related land loss as the move reason; BEMP provides the stronger sequence from a recorded shock to a later relocation. Prior BEMP research asks whether shocks change migration likelihood, type, or distance. This project conditions on a move and predicts its district.", [
      "Local frozen summary: outputs/tables/cross_dataset_replication_summary.csv",
      "BEMP public-use data: https://doi.org/10.5281/zenodo.18229498",
      "BIHS public-use data: https://doi.org/10.7910/DVN/OR6MHT",
      "Existing BEMP incidence paper: https://doi.org/10.1007/s11111-025-00478-7",
    ]);
  }

  // 6. Limits and survey design: adapted from Codex Grid slide 09 (message + three callouts).
  {
    const s = p.slides.add();
    s.background.fill = C.white;
    header(s, "The result sharpens the next measurement problem", "What this study cannot yet answer", 6);
    text(s, "limits-lead", "GIS describes candidate districts before the move. The surveys reveal less about the household-specific ties that made one candidate reachable.", 52, 188, 1110, 84, 25, { bold: true });
    const xs = [52, 452, 852];
    const h = ["Networks", "Resolution", "Interpretation"];
    const b = [
      "1,815 of 1,857 BIHS interval migrants report friends or family help at destination, but that measure is recorded after the choice.",
      "Public geography is district-level. The model cannot distinguish neighborhoods, villages, or exact addresses.",
      "These are out-of-sample predictions. They do not identify the causal effect of any single GIS feature.",
    ];
    for (let i = 0; i < 3; i++) {
      box(s, `limit-panel-${i}`, xs[i], 335, 350, 240, C.panel);
      text(s, `limit-head-${i}`, h[i], xs[i] + 24, 364, 300, 40, 23, { bold: true, color: i === 0 ? C.blue : C.ink });
      text(s, `limit-body-${i}`, b[i], xs[i] + 24, 421, 302, 118, 17, { color: C.muted });
    }
    notes(s, "The network statistic is substantively striking but post-choice, so it is excluded from the predictive specification. A future survey should measure pre-move ties and household-specific access to land, housing, and jobs across the candidate set.", [
      "Local audited statistic: publication/qa/manuscript_number_registry.csv",
      "Local limitations: publication/manuscript/manuscript.md",
    ]);
  }

  // 7. Close: adapted from Codex Grid slide 01 (large-message close).
  {
    const s = p.slides.add();
    s.background.fill = C.ink;
    text(s, "close-kicker", "WHAT WE NOW KNOW", 52, 47, 400, 28, 14, { bold: true, color: "#73C7F3" });
    text(s, "close-title", "After a climate-linked move, destination geography still matters.", 52, 162, 1040, 142, 50, { bold: true, color: C.white });
    text(s, "close-body", "Distance matters, but it is not enough. Across two public household surveys, the geography of candidate destinations improves prediction of where movers actually go.", 52, 351, 945, 116, 24, { color: "#D6DBE2" });
    box(s, "close-rule", 52, 522, 1176, 2, "#5A6572");
    text(s, "close-action", "Next: measure pre-move social ties, housing, land, and jobs for every plausible destination.", 52, 558, 1070, 72, 23, { bold: true, color: "#73C7F3" });
    text(s, "close-number", "07", 1178, 680, 50, 18, 11, { align: "right", color: "#9AA4B0" });
    notes(s, "Return to the household. The study cannot tell us every reason Manikganj was possible, but it shows that destination geography contains predictive information beyond distance. The next data collection should make household-destination links observable before the move.", [
      "Local claim sheet: publication/claim_sheet.md",
      "Local paper: publication/manuscript/manuscript.md",
    ]);
  }

  for (const [i, slide] of p.slides.items.entries()) {
    const stem = `slide-${String(i + 1).padStart(2, "0")}`;
    const png = await p.export({ slide, format: "png", scale: 1 });
    await fs.writeFile(path.join(QA, `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(QA, `${stem}.layout.json`), await layout.text());
  }
  const montage = await p.export({ format: "webp", montage: true, scale: 1 });
  await fs.writeFile(path.join(QA, "deck-montage.webp"), new Uint8Array(await montage.arrayBuffer()));
  const pptx = await PresentationFile.exportPptx(p);
  await pptx.save(path.join(OUT, "bangladesh_climate_destination_choice_7_slide_presentation.pptx"));
  const snapshot = await p.inspect({ kind: "slide,textbox,image,notes", maxChars: 50000 });
  await fs.writeFile(path.join(QA, "deck-inspect.ndjson"), snapshot.ndjson);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
