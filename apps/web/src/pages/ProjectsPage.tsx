import { Download, Filter } from "lucide-react";
import { useMemo, useState } from "react";
import { demoProjects } from "../api/client";
import { ProjectTable } from "../features/projects/ProjectTable";

export function ProjectsPage() {
  const [query, setQuery] = useState("");
  const projects = useMemo(
    () => demoProjects.filter((project) => `${project.projectCode} ${project.title} ${project.department}`.toLowerCase().includes(query.toLowerCase())),
    [query]
  );
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-muted">Projects</p>
          <h1 className="text-2xl font-semibold">Project master register</h1>
        </div>
        <button className="focus-ring inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm">
          <Download className="h-4 w-4" />
          Export current result
        </button>
      </div>
      <div className="flex flex-col gap-2 rounded-md border border-line bg-panel p-3 md:flex-row">
        <input className="focus-ring min-w-0 flex-1 rounded-md border border-line bg-surface px-3 py-2 text-sm" placeholder="Search by code, title or department" value={query} onChange={(event) => setQuery(event.target.value)} />
        <button className="focus-ring inline-flex items-center justify-center gap-2 rounded-md border border-line px-3 py-2 text-sm">
          <Filter className="h-4 w-4" />
          Filters
        </button>
      </div>
      <ProjectTable projects={projects} canEdit />
    </div>
  );
}

