import { Download, FileUp, TableProperties, Upload } from "lucide-react";
import { useState } from "react";
import { commitImport, downloadFile, previewImport } from "../api/client";
import type { ImportBatch } from "../api/client";
import { useToken } from "../app/AuthContext";
import { Button } from "../components/Button";
import { PageHeader } from "./DashboardPage";

const templates = [
  { label: "Projects", type: "projects" },
  { label: "Funding Sanctions", type: "funding_sanctions" },
  { label: "Funding Revisions", type: "funding_revisions" },
  { label: "Tranches", type: "tranches" },
];
const exports = ["Project Master CSV", "Project Master XLSX", "Tranche Register CSV", "Tranche Register XLSX"];

export function ImportsExportsPage() {
  const token = useToken();
  const [importType, setImportType] = useState("projects");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"preview" | "commit" | null>(null);

  async function handlePreview() {
    if (!file) {
      setError("Select a CSV file first.");
      return;
    }
    setBusy("preview");
    setError(null);
    try {
      setBatch(await previewImport(token, importType, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import preview failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleCommit() {
    if (!batch) return;
    setBusy("commit");
    setError(null);
    try {
      setBatch(await commitImport(token, batch.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import commit failed.");
    } finally {
      setBusy(null);
    }
  }

  const canCommit = Boolean(batch && batch.proposedCreates > 0 && batch.failedRows === 0 && batch.status === "previewed");
  return (
    <section className="space-y-6">
      <PageHeader title="Imports and Exports" description="Canonical templates prevent spreadsheet columns from becoming the database design." />
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-lg border border-border bg-[oklch(99%_0.004_250)]">
          <div className="border-b border-border px-4 py-3 text-sm font-semibold">Import Templates</div>
          <div className="divide-y divide-border">
            {templates.map((item) => (
              <div key={item.type} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="flex items-center gap-3 text-sm"><FileUp className="h-4 w-4 text-primary" />{item.label}</div>
                <Button onClick={() => downloadFile(token, `/api/v1/imports/templates/${item.type}.csv`, `${item.type.replace(/_/g, "-")}.csv`)}>Download CSV</Button>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-lg border border-border bg-[oklch(99%_0.004_250)]">
          <div className="border-b border-border px-4 py-3 text-sm font-semibold">Exports</div>
          <div className="divide-y divide-border">
            {exports.map((name) => (
              <div key={name} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="flex items-center gap-3 text-sm"><TableProperties className="h-4 w-4 text-primary" />{name}</div>
                <Button onClick={() => downloadFile(token, exportPath(name), `${name.toLowerCase().replace(/ /g, "-")}.${name.includes("XLSX") ? "xlsx" : "csv"}`)}><Download className="h-4 w-4" />Generate</Button>
              </div>
            ))}
          </div>
        </section>
      </div>
      <section className="rounded-lg border border-border bg-[oklch(99%_0.004_250)] p-4">
        <div className="text-sm font-semibold">Import Review</div>
        <div className="mt-3 grid gap-3 md:grid-cols-[220px_1fr_auto_auto] md:items-end">
          <label className="block text-sm font-medium" htmlFor="importType">
            Import Type
            <select id="importType" className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm" value={importType} onChange={(event) => { setImportType(event.target.value); setBatch(null); }}>
              {templates.map((item) => <option key={item.type} value={item.type}>{item.label}</option>)}
            </select>
          </label>
          <label className="block text-sm font-medium" htmlFor="importFile">
            CSV File
            <input id="importFile" className="focus-ring mt-1 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm" type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setBatch(null); }} />
          </label>
          <Button onClick={handlePreview} disabled={busy !== null}><Upload className="h-4 w-4" />{busy === "preview" ? "Previewing" : "Preview"}</Button>
          <Button onClick={handleCommit} disabled={!canCommit || busy !== null}>{busy === "commit" ? "Committing" : "Commit"}</Button>
        </div>
        {error ? <div className="mt-3 rounded-md border border-danger bg-surface px-3 py-2 text-sm text-danger">{error}</div> : null}
        {batch ? <ImportPreview batch={batch} /> : <div className="mt-3 rounded-md border border-dashed border-border p-8 text-center text-sm text-[oklch(45%_0.014_250)]">Preview a canonical CSV before committing records.</div>}
      </section>
    </section>
  );
}

function ImportPreview({ batch }: { batch: ImportBatch }) {
  const metrics = [
    ["Rows", batch.rowsDetected],
    ["Valid", batch.validRows],
    ["Invalid", batch.invalidRows],
    ["Duplicates", batch.duplicateRows],
    ["Existing", batch.existingRecordsMatched],
    ["Creates", batch.proposedCreates],
    ["Committed", batch.committedRows],
    ["Failed", batch.failedRows],
  ];
  return (
    <div className="mt-4 space-y-4">
      <div className="grid gap-2 sm:grid-cols-4 xl:grid-cols-8">
        {metrics.map(([label, value]) => (
          <div key={label} className="border-y border-line py-2">
            <div className="text-xs text-muted">{label}</div>
            <div className="text-lg font-semibold">{value}</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-md border border-line">
        <table className="min-w-[960px] w-full text-left text-sm">
          <thead className="bg-surface text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">Row</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Action</th>
              <th className="px-3 py-2">Project</th>
              <th className="px-3 py-2">Messages</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {batch.rows.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2">{row.rowNumber}</td>
                <td className="px-3 py-2"><span className={statusClass(row.status)}>{row.status}</span></td>
                <td className="px-3 py-2">{row.proposedAction}</td>
                <td className="px-3 py-2">{String(row.normalizedValues.project_code ?? "")}</td>
                <td className="px-3 py-2">
                  {[...row.errors, ...row.warnings].length ? [...row.errors, ...row.warnings].join(" ") : "Ready"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function statusClass(status: string) {
  const base = "inline-flex rounded px-2 py-1 text-xs font-medium";
  if (status === "valid" || status === "committed") return `${base} bg-[oklch(94%_0.025_150)] text-[oklch(34%_0.09_150)]`;
  if (status === "invalid" || status === "failed") return `${base} bg-[oklch(94%_0.035_25)] text-danger`;
  return `${base} bg-muted text-[oklch(38%_0.012_250)]`;
}

function exportPath(name: string) {
  if (name === "Project Master CSV") return "/api/v1/exports/project-master.csv";
  if (name === "Project Master XLSX") return "/api/v1/exports/project-master.xlsx";
  if (name === "Tranche Register CSV") return "/api/v1/exports/tranche-register.csv";
  if (name === "Tranche Register XLSX") return "/api/v1/exports/tranche-register.xlsx";
  return "/api/v1/exports/project-master.csv";
}
