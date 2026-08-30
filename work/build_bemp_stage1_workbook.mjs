import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve("..");
const tablesDir = path.join(root, "outputs", "tables");
const outputPath = path.join(root, "outputs", "bemp_stage1_event_ledger.xlsx");
const previewDir = path.join(root, "work", "stage1_workbook_previews");

const specs = [
  ["Events", "bemp_prospective_migration_events.csv", 5],
  ["Respondent State", "bemp_respondent_wave_state.csv", 5],
  ["Admin Crosswalk", "bemp_destination_admin_crosswalk.csv", 2],
  ["Duplicate Adjudication", "bemp_duplicate_adjudication.csv", 3],
  ["Sample Flow", "bemp_stage1_sample_flow.csv", 2],
  ["Data Dictionary", "bemp_stage1_data_dictionary.csv", 3],
  ["Recalled History", "bemp_recalled_migration_history.csv", 5],
  ["History Flow", "bemp_recalled_history_flow.csv", 3],
  ["Household Linkage", "bemp_household_key_reconciliation.csv", 3],
  ["Respondent Duplicates", "bemp_respondent_duplicate_audit.csv", 3],
  ["Freeze Manifest", "bemp_stage1_freeze_manifest.csv", 2],
];

function colName(n) {
  let out = "";
  while (n > 0) {
    n -= 1;
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26);
  }
  return out;
}

function csvShape(text) {
  const lines = text.trimEnd().split(/\r?\n/);
  return {
    rows: lines.length,
    cols: lines[0].split(",").length,
  };
}

let workbook;
const shapes = {};
for (let i = 0; i < specs.length; i += 1) {
  const [sheetName, fileName] = specs[i];
  const csvText = await fs.readFile(path.join(tablesDir, fileName), "utf8");
  shapes[sheetName] = csvShape(csvText);
  if (i === 0) {
    workbook = await Workbook.fromCSV(csvText, { sheetName });
  } else {
    await workbook.fromCSV(csvText, { sheetName });
  }
}

const readme = workbook.worksheets.add("README");
readme.showGridLines = false;
readme.getRange("A1:H1").merge();
readme.getRange("A1").values = [["BEMP Stage 1 migration-event ledger"]];
readme.getRange("A1:H1").format = {
  fill: "#0F4C5C",
  font: { bold: true, color: "#FFFFFF", size: 16 },
  verticalAlignment: "center",
};
readme.getRange("A1:H1").format.rowHeight = 28;

readme.getRange("A3:B15").values = [
  ["Metric", "Value"],
  ["All conservative event-rich records", null],
  ["New destination events", null],
  ["Domestic new destinations", null],
  ["Named city/rural-district endpoints", null],
  ["Officially resolved district endpoints", null],
  ["After duplicate adjudication", null],
  ["Whole/partial-household relocations", null],
  ["Broad climate-screen records", null],
  ["Recalled source rows", null],
  ["Observed recalled records", null],
  ["Recalled sensitivity records", null],
  ["Recalled household records", null],
];
readme.getRange("B4:B15").formulas = [
  ["='Sample Flow'!C2"],
  ["='Sample Flow'!C3"],
  ["='Sample Flow'!C4"],
  ["='Sample Flow'!C5"],
  ["='Sample Flow'!C6"],
  ["='Sample Flow'!C7"],
  ["='Sample Flow'!C8"],
  ["='Sample Flow'!C10"],
  ["='History Flow'!D2+'History Flow'!D3+'History Flow'!D4+'History Flow'!D5+'History Flow'!D6+'History Flow'!D7+'History Flow'!D8+'History Flow'!D9"],
  ["='History Flow'!F2+'History Flow'!F3+'History Flow'!F4+'History Flow'!F5+'History Flow'!F6+'History Flow'!F7+'History Flow'!F8+'History Flow'!F9"],
  ["='History Flow'!N2+'History Flow'!N3+'History Flow'!N4+'History Flow'!N5+'History Flow'!N6+'History Flow'!N7+'History Flow'!N8+'History Flow'!N9"],
  ["='History Flow'!O2+'History Flow'!O3+'History Flow'!O4+'History Flow'!O5+'History Flow'!O6+'History Flow'!O7+'History Flow'!O8+'History Flow'!O9"],
];
readme.getRange("A3:B3").format = {
  fill: "#2A6F77",
  font: { bold: true, color: "#FFFFFF" },
};
readme.getRange("A4:A15").format.font = { bold: true, color: "#24323A" };
readme.getRange("B4:B15").format.numberFormat = "#,##0";
readme.getRange("A3:B15").format.borders = {
  preset: "inside",
  style: "thin",
  color: "#D9E2E5",
};

readme.getRange("D3:H3").merge();
readme.getRange("D3").values = [["Scope and interpretation"]];
readme.getRange("D3:H3").format = {
  fill: "#E8F1F2",
  font: { bold: true, color: "#0F4C5C" },
};
readme.getRange("D4:H15").merge();
readme.getRange("D4").values = [[
  "Pre-model construction. No GIS layer or destination-choice model is used. All 127 unique named " +
  "public endpoint strings now have an official containing-district resolution with source provenance. " +
  "Duplicate source rows remain visible after latest-interview adjudication. Recalled histories stay " +
  "separate because of timing, compression, and current-destination overlap. The climate flag is a " +
  "screening definition, not a causal classification; wave-6 records remain endpoint-rich snapshots."
]];
readme.getRange("D4:H15").format = {
  fill: "#F7FAFA",
  font: { color: "#24323A" },
  wrapText: true,
  verticalAlignment: "top",
};

readme.getRange("A17:H17").merge();
readme.getRange("A17").values = [["Workbook contents"]];
readme.getRange("A17:H17").format = {
  fill: "#E8F1F2",
  font: { bold: true, color: "#0F4C5C" },
};
readme.getRange("A18:H29").values = [
  ["Sheet", "Unit", "Rows", "Purpose", null, null, null, null],
  ["Events", "Event/snapshot", shapes["Events"].rows - 1, "Rule-based event ledger with source-variable provenance", null, null, null, null],
  ["Respondent State", "Respondent-wave row", shapes["Respondent State"].rows - 1, "Panel-state backbone; early waves retained without forcing events", null, null, null, null],
  ["Admin Crosswalk", "Unique raw admin string", shapes["Admin Crosswalk"].rows - 1, "Official place/district resolution with method, confidence, and source", null, null, null, null],
  ["Duplicate Adjudication", "Repeated source row", shapes["Duplicate Adjudication"].rows - 1, "Retain/supersede decision while preserving all raw event rows", null, null, null, null],
  ["Sample Flow", "Criterion/wave", shapes["Sample Flow"].rows - 1, "Sequential attrition and wave summaries", null, null, null, null],
  ["Data Dictionary", "Column", shapes["Data Dictionary"].rows - 1, "Column definitions and analytic roles", null, null, null, null],
  ["Recalled History", "Recalled loop/pattern", shapes["Recalled History"].rows - 1, "Separate sensitivity table with timing, compression, endpoint, and overlap flags", null, null, null, null],
  ["History Flow", "Wave-history stream", shapes["History Flow"].rows - 1, "Reported, represented, unresolved, and eligible recalled-move counts", null, null, null, null],
  ["Household Linkage", "Derived household prefix", shapes["Household Linkage"].rows - 1, "Baseline role and panel-coverage reconciliation", null, null, null, null],
  ["Respondent Duplicates", "Repeated source row", shapes["Respondent Duplicates"].rows - 1, "All five respondent-wave duplicate pairs under one latest-date rule", null, null, null, null],
  ["Freeze Manifest", "Output artifact", shapes["Freeze Manifest"].rows - 1, "Checksums for BEMP-only pre-model outputs", null, null, null, null],
];
readme.getRange("A18:D18").format = {
  fill: "#2A6F77",
  font: { bold: true, color: "#FFFFFF" },
};
readme.getRange("A18:D29").format.borders = {
  preset: "inside",
  style: "thin",
  color: "#D9E2E5",
};
readme.getRange("A31:H31").merge();
readme.getRange("A31").values = [[
  "Verdict remains YELLOW: public admin-unit destinations support district-level work, not coordinate-level GIS choice."
]];
readme.getRange("A31:H31").format = {
  fill: "#FFF3CD",
  font: { bold: true, color: "#664D03" },
};
readme.getRange("A:A").format.columnWidth = 34;
readme.getRange("B:B").format.columnWidth = 24;
readme.getRange("C:C").format.columnWidth = 12;
readme.getRange("D:H").format.columnWidth = 16;
readme.getRange("D4:H15").format.rowHeight = 22;
readme.freezePanes.freezeRows(1);

for (const [sheetName, , freezeCols] of specs) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const { rows, cols } = shapes[sheetName];
  const last = colName(cols);
  const used = sheet.getRange("A1:" + last + rows);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(freezeCols);
  used.format.font = { name: "Aptos", size: ["Respondent State", "Recalled History", "Household Linkage"].includes(sheetName) ? 8 : 9 };
  sheet.getRange("A1:" + last + "1").format = {
    fill: "#0F4C5C",
    font: { bold: true, color: "#FFFFFF", size: 9 },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange("A1:" + last + "1").format.rowHeight = 34;
  used.format.columnWidth = 15;
  if (sheetName === "Events") {
    sheet.getRange("A:A").format.columnWidth = 34;
    sheet.getRange("B:C").format.columnWidth = 22;
    sheet.getRange("I:K").format.columnWidth = 24;
    sheet.getRange("R:Y").format.columnWidth = 22;
    sheet.getRange("AG:AM").format.columnWidth = 24;
    sheet.getRange("BV:BY").format.columnWidth = 28;
  } else if (sheetName === "Respondent State") {
    sheet.getRange("A:B").format.columnWidth = 22;
    sheet.getRange("H:K").format.columnWidth = 22;
  } else if (sheetName === "Admin Crosswalk") {
    sheet.getRange("B:C").format.columnWidth = 24;
    sheet.getRange("D:E").format.columnWidth = 24;
    sheet.getRange("I:M").format.columnWidth = 24;
    sheet.getRange("N:N").format.columnWidth = 44;
    sheet.getRange("O:O").format.columnWidth = 62;
    sheet.getRange("U:V").format.columnWidth = 42;
  } else if (sheetName === "Duplicate Adjudication") {
    sheet.getRange("A:B").format.columnWidth = 28;
    sheet.getRange("D:F").format.columnWidth = 18;
    sheet.getRange("G:J").format.columnWidth = 24;
    sheet.getRange("M:O").format.columnWidth = 34;
  } else if (sheetName === "Sample Flow") {
    sheet.getRange("B:B").format.columnWidth = 58;
    sheet.getRange("F:F").format.columnWidth = 58;
    sheet.getRange("E:E").format.numberFormat = "0.0%";
  } else if (sheetName === "Data Dictionary") {
    sheet.getRange("C:C").format.columnWidth = 34;
    sheet.getRange("E:E").format.columnWidth = 72;
    sheet.getRange("F:F").format.columnWidth = 20;
  } else if (sheetName === "Recalled History") {
    sheet.getRange("A:A").format.columnWidth = 36;
    sheet.getRange("B:C").format.columnWidth = 24;
    sheet.getRange("H:J").format.columnWidth = 22;
    sheet.getRange("Q:Z").format.columnWidth = 18;
    sheet.getRange("AA:AF").format.columnWidth = 24;
  } else if (sheetName === "History Flow") {
    sheet.getRange("C:C").format.columnWidth = 32;
    sheet.getRange("D:P").format.columnWidth = 17;
  } else if (sheetName === "Household Linkage") {
    sheet.getRange("A:C").format.columnWidth = 24;
    sheet.getRange("E:F").format.columnWidth = 42;
    sheet.getRange("L:M").format.columnWidth = 42;
    sheet.getRange("R:U").format.columnWidth = 34;
  } else if (sheetName === "Respondent Duplicates") {
    sheet.getRange("A:D").format.columnWidth = 25;
    sheet.getRange("H:I").format.columnWidth = 32;
    sheet.getRange("K:M").format.columnWidth = 42;
  } else if (sheetName === "Freeze Manifest") {
    sheet.getRange("A:A").format.columnWidth = 62;
    sheet.getRange("F:F").format.columnWidth = 68;
    sheet.getRange("H:H").format.columnWidth = 58;
  }
  if (!["Events", "Respondent State", "Recalled History", "Household Linkage"].includes(sheetName)) {
    const tableName = sheetName.replace(/[^A-Za-z0-9]/g, "") + "Table";
    const table = sheet.tables.add("A1:" + last + rows, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  }
  if (sheetName === "Sample Flow") {
    sheet.getRange("E2:E" + rows).setNumberFormat("0.0%");
  }
}

await fs.mkdir(previewDir, { recursive: true });
const renderSpecs = [
  ["README", "A1:H31"],
  ["Events", "A1:Q14"],
  ["Respondent State", "A1:S14"],
  ["Admin Crosswalk", "A1:V18"],
  ["Duplicate Adjudication", "A1:O6"],
  ["Sample Flow", "A1:F18"],
  ["Data Dictionary", "A1:F20"],
  ["Recalled History", "A1:Z14"],
  ["History Flow", "A1:P9"],
  ["Household Linkage", "A1:U16"],
  ["Respondent Duplicates", "A1:M11"],
  ["Freeze Manifest", "A1:H16"],
];
for (const [sheetName, range] of renderSpecs) {
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 1.2,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, sheetName.replace(/\s+/g, "_").toLowerCase() + ".png"),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const readmeInspect = await workbook.inspect({
  kind: "table",
  range: "README!A1:H31",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
  maxChars: 6000,
});
console.log(readmeInspect.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
  maxChars: 3000,
});
console.log(errors.ndjson);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previewDir, shapes }, null, 2));
