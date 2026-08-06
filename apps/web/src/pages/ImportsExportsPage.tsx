import { Download, FileUp, TableProperties } from "lucide-react";
import { downloadFile } from "../api/client";
import { useToken } from "../app/AuthContext";
import { Button } from "../components/Button";
import { PageHeader } from "./DashboardPage";

const templates = ["Projects", "Funding Sanctions", "Funding Revisions", "Tranches"];
const exports = ["Project Master CSV", "Project Master XLSX", "Tranche Register CSV", "Tranche Register XLSX"];

export function ImportsExportsPage() {
  const token = useToken();
  return (
    <section className="space-y-6">
      <PageHeader title="Imports and Exports" description="Canonical templates prevent spreadsheet columns from becoming the database design." />
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-lg border border-border bg-[oklch(99%_0.004_250)]">
          <div className="border-b border-border px-4 py-3 text-sm font-semibold">Import Templates</div>
          <div className="divide-y divide-border">
            {templates.map((name) => (
              <div key={name} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="flex items-center gap-3 text-sm"><FileUp className="h-4 w-4 text-primary" />{name}</div>
                <Button onClick={() => downloadFile(token, `/api/v1/imports/templates/${name.toLowerCase().replace(/ /g, "_")}.csv`, `${name.toLowerCase().replace(/ /g, "-")}.csv`)}>Download CSV</Button>
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
        <div className="text-sm font-semibold">Import Preview</div>
        <div className="mt-3 rounded-md border border-dashed border-border p-8 text-center text-sm text-[oklch(45%_0.014_250)]">Template downloads are available now. Bulk upload ingestion is deferred until the server import review workflow is implemented.</div>
      </section>
    </section>
  );
}

function exportPath(name: string) {
  if (name === "Project Master CSV") return "/api/v1/exports/project-master.csv";
  if (name === "Project Master XLSX") return "/api/v1/exports/project-master.xlsx";
  if (name === "Tranche Register CSV") return "/api/v1/exports/tranche-register.csv";
  if (name === "Tranche Register XLSX") return "/api/v1/exports/tranche-register.xlsx";
  return "/api/v1/exports/project-master.csv";
}
