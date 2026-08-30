import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

process.on("uncaughtException", (error) => {
  console.error(`WORKBOOK_ERROR: ${error?.message ?? error}`);
  process.exit(1);
});
process.on("unhandledRejection", (error) => {
  console.error(`WORKBOOK_ERROR: ${error?.message ?? error}`);
  process.exit(1);
});

const outDir = "outputs";
const tableDir = "outputs/tables";
const previewDir = "work/workbook_previews";
await fs.mkdir(outDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const wb = Workbook.create();
const overview = wb.worksheets.add("Overview");
const key = wb.worksheets.add("Key Results");

function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  const width = Math.max(...rows.map((r) => r.length));
  return rows.map((r, ri) => {
    const padded = [...r];
    while (padded.length < width) padded.push("");
    return padded.map((v) => {
      if (ri === 0 || v === "") return v;
      if (v === "True" || v === "TRUE") return true;
      if (v === "False" || v === "FALSE") return false;
      const n = Number(v);
      return Number.isFinite(n) && v.trim() !== "" ? n : v;
    });
  });
}

// Add machine-readable source tables. Artifact-tool's incremental CSV importer is
// incompatible with a workbook that already has sheets in this runtime, so the
// same quoted CSV rows are parsed once and block-written into artifact-tool.
const imports = [
  ["Model Results", "bemp_stage5_model_results.csv"],
  ["Paired Comparisons", "bemp_stage5_paired_logloss_comparisons.csv"],
  ["Coefficients", "bemp_stage5_parameter_bootstrap.csv"],
  ["Validation", "bemp_stage5_validation.csv"],
  ["GIS Districts", "bemp_stage4_district_gis_features.csv"],
  ["Sources", "bemp_stage4_source_manifest.csv"],
];
for (const [sheetName, fileName] of imports) {
  const csvText = await fs.readFile(`${tableDir}/${fileName}`, "utf8");
  const matrix = parseCSV(csvText);
  const sh = wb.worksheets.add(sheetName);
  sh.getRangeByIndexes(0, 0, matrix.length, matrix[0].length).values = matrix;
}

const navy = "#17324D";
const teal = "#0F766E";
const amber = "#D97706";
const light = "#EAF2F5";
const soft = "#F7FAFC";
const muted = "#52677E";
const grid = "#D8E1E8";

overview.showGridLines = false;
overview.getRange("A1:H2").merge();
overview.getRange("A1").values = [["BEMP climate-related migration destination choice"]];
overview.getRange("A1:H2").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF", size: 22 },
  verticalAlignment: "center",
  wrapText: true,
};
overview.getRange("A3:H3").merge();
overview.getRange("A3").values = [["Stage 5 research results | public geography verdict: YELLOW"]];
overview.getRange("A3:H3").format = {
  fill: "#D6A84B",
  font: { bold: true, color: "#263238", size: 12 },
  verticalAlignment: "center",
};

overview.getRange("A5:B11").values = [
  ["Decision", "GIS improves household-out-of-sample destination probabilities within observed BEMP origins."],
  ["Primary sample", "184 whole/partial-household moves after a strictly lagged home flood or river-erosion report; 137 households."],
  ["Choice universe", "64 Bangladesh districts; 113 same-district and 71 cross-district moves."],
  ["Primary metric", "Household-grouped five-fold mean log loss; lower is better."],
  ["Direct GIS gain", null],
  ["Nested GIS gain", null],
  ["Critical limit", "Leave-one-origin-out full-choice performance is worse than gravity; do not claim national unseen-origin transportability."],
];
overview.getRange("B9").formulas = [["='Key Results'!G2"]];
overview.getRange("B10").formulas = [["='Key Results'!H2"]];
overview.getRange("B9:B10").format.numberFormat = "0.000";
overview.getRange("A5:A11").format = { fill: light, font: { bold: true, color: navy }, wrapText: true };
overview.getRange("B5:B11").format = { fill: "#FFFFFF", font: { color: "#263B50" }, wrapText: true };
overview.getRange("A5:B11").format.borders = { preset: "all", style: "thin", color: grid };

overview.getRange("A13:H13").merge();
overview.getRange("A13").values = [["Interpretation contract"]];
overview.getRange("A13:H13").format = { fill: teal, font: { bold: true, color: "#FFFFFF" } };
overview.getRange("A14:H17").merge(true);
overview.getRange("A14:A17").values = [
  ["SUPPORTED: Four pre-registered district GIS characteristics improve predictive probabilities beyond fitted gravity in the observed origin settings."],
  ["NOT SUPPORTED: Causal effects of destination characteristics or causal shock heterogeneity."],
  ["NOT SUPPORTED: Village/neighborhood choice or prediction from an unseen Bangladesh origin district."],
  ["CAUTION: Positive destination flood association is conditional and may reflect floodplain livelihoods, networks, urban geography, or origin composition."],
];
overview.getRange("A14:H17").format = { fill: soft, font: { color: "#263B50" }, wrapText: true };
overview.getRange("A14:H17").format.borders = { preset: "all", style: "thin", color: grid };

overview.getRange("A19:H19").merge();
overview.getRange("A19").values = [["Workbook guide"]];
overview.getRange("A19:H19").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
overview.getRange("A20:B26").values = [
  ["Key Results", "Curated validation comparison with formula-derived GIS gains."],
  ["Model Results", "All aggregate performance cells across samples, universes, models, and validation schemes."],
  ["Paired Comparisons", "Household-cluster bootstrap intervals for paired out-of-fold loss differences."],
  ["Coefficients", "Full-sample estimates and 1,000-replicate household-cluster bootstrap intervals."],
  ["Validation", "Fatal, substantive, and warning-level computation checks."],
  ["GIS Districts", "Frozen 64-district GIS feature table and extraction QA fields."],
  ["Sources", "Retrieval URLs, versions, local paths, byte counts, and SHA-256 provenance."],
];
overview.getRange("A20:A26").format = { fill: light, font: { bold: true, color: navy } };
overview.getRange("A20:B26").format.wrapText = true;
overview.getRange("A20:B26").format.borders = { preset: "all", style: "thin", color: grid };
overview.getRange("A28:H29").merge();
overview.getRange("A28").values = [["This workbook is a readable companion to outputs/reports/bemp_stage5_gis_model_results.md. Machine-readable event predictions, fold parameters, tuning losses, and split audits remain in outputs/tables/."]];
overview.getRange("A28:H29").format = { fill: "#FFF7E6", font: { color: "#6B4F16", italic: true }, wrapText: true };
overview.getRange("A:A").format.columnWidth = 23;
overview.getRange("B:B").format.columnWidth = 92;
overview.getRange("C:H").format.columnWidth = 12;
overview.getRange("1:29").format.rowHeight = 22;
overview.getRange("1:2").format.rowHeight = 30;
overview.freezePanes.freezeRows(3);

key.showGridLines = false;
key.getRange("A1:J1").values = [[
  "Sample", "Universe", "Validation", "Events", "Gravity log loss", "Direct GIS log loss",
  "Direct GIS gain", "Nested GIS gain", "Gravity top-1", "Direct GIS top-1"
]];
key.getRange("A2:J10").values = [
  ["Shock-linked", "Full 64", "Household 5-fold", 184, 1.630313, 1.522232, null, null, 0.614130, 0.614130],
  ["Shock-linked", "Full 64", "Location 5-fold", 184, 1.644185, 1.618063, null, null, 0.614130, 0.614130],
  ["Shock-linked", "Full 64", "Temporal W12+", 112, 1.561084, 1.548287, null, null, 0.607143, 0.607143],
  ["Shock-linked", "Full 64", "Leave one origin out", 184, 1.686900, 1.813405, null, null, 0.614130, 0.527174],
  ["Shock-linked", "Interdistrict 63", "Household 5-fold", 71, 2.484222, 2.157289, null, null, 0.408451, 0.422535],
  ["Shock-linked", "Interdistrict 63", "Leave one origin out", 71, 2.771590, 2.547951, null, null, 0.408451, 0.422535],
  ["All household moves", "Full 64", "Household 5-fold", 264, 1.711789, 1.616504, null, null, 0.598485, 0.598485],
  ["All household moves", "Full 64", "Temporal W12+", 181, 1.657032, 1.538523, null, null, 0.613260, 0.613260],
  ["All household moves", "Interdistrict 63", "Household 5-fold", 107, 2.518454, 2.223899, null, null, 0.401869, 0.411215],
];
key.getRange("G2").formulas = [["=E2-F2"]];
key.getRange("G2:G10").fillDown();
key.getRange("H2:H10").values = [
  [0.124013], [0.018979], [-0.030221], [-0.258851], [null], [null], [0.124960], [0.142323], [null]
];
key.getRange("A1:J1").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, wrapText: true };
key.getRange("A2:J10").format.borders = { preset: "all", style: "thin", color: grid };
key.getRange("A2:J10").format.wrapText = true;
key.getRange("E2:H10").format.numberFormat = "0.000";
key.getRange("I2:J10").format.numberFormat = "0.0%";
key.getRange("G2:H10").format = { fill: "#E9F5F2", font: { bold: true, color: teal }, numberFormat: "0.000" };
key.getRange("A5:J5").format.fill = "#FFF0F0";
key.getRange("A1:J10").format.autofitColumns();
key.getRange("A:A").format.columnWidth = 23;
key.getRange("B:B").format.columnWidth = 19;
key.getRange("C:C").format.columnWidth = 24;
key.getRange("D:J").format.columnWidth = 17;
key.freezePanes.freezeRows(1);

// Consistent research-table styling for imported machine-readable sheets.
for (const [sheetName] of imports) {
  const sh = wb.worksheets.getItem(sheetName);
  sh.showGridLines = false;
  const used = sh.getUsedRange();
  if (used) {
    used.format.font = { color: "#263B50", size: 10 };
    used.format.borders = { preset: "all", style: "thin", color: grid };
    used.format.autofitColumns();
    used.format.autofitRows();
  }
  const header = sh.getRangeByIndexes(0, 0, 1, used ? used.columnCount : 1);
  header.format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 10 }, wrapText: true };
  sh.freezePanes.freezeRows(1);
}

// Readability overrides for wide narrative/provenance fields.
wb.worksheets.getItem("Validation").getRange("A:E").format.wrapText = true;
wb.worksheets.getItem("Validation").getRange("A:A").format.columnWidth = 45;
wb.worksheets.getItem("Validation").getRange("C:D").format.columnWidth = 55;
wb.worksheets.getItem("Sources").getRange("A:J").format.wrapText = true;
wb.worksheets.getItem("Sources").getRange("C:C").format.columnWidth = 65;
wb.worksheets.getItem("Sources").getRange("E:E").format.columnWidth = 55;
wb.worksheets.getItem("Sources").getRange("J:J").format.columnWidth = 55;
wb.worksheets.getItem("GIS Districts").getRange("A:AZ").format.numberFormat = "0.0000";

const overviewPreview = await wb.render({ sheetName: "Overview", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(`${previewDir}/overview.png`, new Uint8Array(await overviewPreview.arrayBuffer()));
const resultsPreview = await wb.render({ sheetName: "Key Results", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(`${previewDir}/key_results.png`, new Uint8Array(await resultsPreview.arrayBuffer()));

const inspect = await wb.inspect({ kind: "sheet,formula", maxChars: 12000, options: { maxResults: 200 } });
await fs.writeFile(`${previewDir}/inspect.ndjson`, inspect.ndjson ?? String(inspect));

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${outDir}/bemp_stage5_research_results.xlsx`);

console.log(`${outDir}/bemp_stage5_research_results.xlsx`);
console.log(`${previewDir}/overview.png`);
console.log(`${previewDir}/key_results.png`);
