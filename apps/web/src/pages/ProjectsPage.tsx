import { Download, Filter } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { createProject, downloadFile, fetchProjects } from "../api/client";
import { useToken } from "../app/AuthContext";
import { ProjectTable } from "../features/projects/ProjectTable";

export function ProjectsPage() {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const token = useToken();
  const queryClient = useQueryClient();
  const [newProject, setNewProject] = useState({ project_code: "", title: "", school: "", department: "" });
  const params = useMemo(() => {
    const next = new URLSearchParams();
    if (query) next.set("q", query);
    if (statusFilter) next.set("status", statusFilter);
    return next;
  }, [query, statusFilter]);
  const { data = [], isLoading, error } = useQuery({ queryKey: ["projects", query, statusFilter], queryFn: () => fetchProjects(token, params) });
  const createMutation = useMutation({
    mutationFn: () => createProject(token, { ...newProject, project_status: "active" }),
    onSuccess: () => {
      setNewProject({ project_code: "", title: "", school: "", department: "" });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-muted">Projects</p>
          <h1 className="text-2xl font-semibold">Project master register</h1>
        </div>
        <button className="focus-ring inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm" onClick={() => downloadFile(token, "/api/v1/exports/project-master.csv", "project-master.csv")}>
          <Download className="h-4 w-4" />
          Export current result
        </button>
      </div>
      <div className="flex flex-col gap-2 rounded-md border border-line bg-panel p-3 md:flex-row">
        <input className="focus-ring min-w-0 flex-1 rounded-md border border-line bg-surface px-3 py-2 text-sm" placeholder="Search by code, title or department" value={query} onChange={(event) => setQuery(event.target.value)} />
        <label className="inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm">
          <Filter className="h-4 w-4" />
          <select className="focus-ring bg-transparent" aria-label="Project status filter" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="on_hold">On hold</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
      </div>
      <form className="grid gap-2 rounded-md border border-line bg-panel p-3 md:grid-cols-[1fr_2fr_1fr_1fr_auto]" onSubmit={(event) => { event.preventDefault(); createMutation.mutate(); }}>
        <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" placeholder="Project code" value={newProject.project_code} onChange={(event) => setNewProject((value) => ({ ...value, project_code: event.target.value }))} />
        <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" placeholder="Project title" value={newProject.title} onChange={(event) => setNewProject((value) => ({ ...value, title: event.target.value }))} />
        <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" placeholder="School" value={newProject.school} onChange={(event) => setNewProject((value) => ({ ...value, school: event.target.value }))} />
        <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" placeholder="Department" value={newProject.department} onChange={(event) => setNewProject((value) => ({ ...value, department: event.target.value }))} />
        <button className="focus-ring rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface">Create</button>
        {createMutation.error ? <div className="text-sm text-danger md:col-span-5">{createMutation.error.message}</div> : null}
      </form>
      {isLoading ? <div className="rounded-md border border-line bg-panel p-8 text-sm text-muted">Loading projects.</div> : null}
      {error ? <div className="rounded-md border border-danger bg-panel p-8 text-sm text-danger">Projects could not be loaded.</div> : null}
      {!isLoading && !error ? <ProjectTable projects={data} canEdit /> : null}
    </div>
  );
}
