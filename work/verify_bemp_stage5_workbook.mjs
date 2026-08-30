import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = "outputs/bemp_stage5_research_results.xlsx";
const blob = await FileBlob.load(path);
const wb = await SpreadsheetFile.importXlsx(blob);
const overview = wb.worksheets.getItem("Overview");
const key = wb.worksheets.getItem("Key Results");

const checks = {
  sheets: Array.from(wb.worksheets).map((s) => s.name),
  overviewGains: overview.getRange("B9:B10").values,
  keyGainFormulas: key.getRange("G2:G10").formulas,
  keyGainValues: key.getRange("G2:G10").values,
};
await fs.writeFile("work/workbook_previews/post_import_checks.json", JSON.stringify(checks, null, 2));

const preview = await wb.render({ sheetName: "Overview", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile("work/workbook_previews/post_import_overview.png", new Uint8Array(await preview.arrayBuffer()));

const errorStrings = JSON.stringify(checks).match(/#(?:REF!|VALUE!|NAME\?|DIV\/0!|N\/A)/g) ?? [];
if (checks.sheets.length !== 8) throw new Error(`Expected 8 sheets, found ${checks.sheets.length}`);
if (errorStrings.length) throw new Error(`Formula errors: ${errorStrings.join(", ")}`);
if (Math.abs(Number(checks.overviewGains[0][0]) - 0.108081) > 0.00001) throw new Error("Direct gain mismatch");
if (Math.abs(Number(checks.overviewGains[1][0]) - 0.124013) > 0.00001) throw new Error("Nested gain mismatch");
console.log(JSON.stringify(checks, null, 2));
