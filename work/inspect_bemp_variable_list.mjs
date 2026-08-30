import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = new URL("../data/raw/bemp/metadata/bemp_variable_list_full.xlsx", import.meta.url);
const input = await FileBlob.load(inputPath.pathname);
const workbook = await SpreadsheetFile.importXlsx(input);

const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 12000,
  tableMaxRows: 8,
  tableMaxCols: 16,
  tableMaxCellChars: 180,
});
console.log(overview.ndjson);

const sheet = workbook.worksheets.getItemAt(0);
const used = sheet.getUsedRange(true);
const values = used.values;
await fs.writeFile(
  new URL("bemp_variable_list_values.json", import.meta.url),
  JSON.stringify(values),
  "utf8",
);
console.log(JSON.stringify({ sheet: sheet.name, rows: values.length, columns: values[0]?.length ?? 0 }));
