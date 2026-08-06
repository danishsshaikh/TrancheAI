import type { ProjectRow } from "../../types/domain";

export function ProjectTable({ projects, canEdit = false }: { projects: ProjectRow[]; canEdit?: boolean }) {
  if (projects.length === 0) {
    return <div className="rounded-md border border-line bg-panel p-8 text-sm text-muted">No projects match the current filters.</div>;
  }
  return (
    <div className="overflow-hidden rounded-md border border-line bg-panel">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="bg-surface text-xs uppercase tracking-normal text-muted">
          <tr>
            {["Project Code", "Project Title", "School", "Department", "Status", "Total Sanctioned", "Net Disbursed", "Available", "Tranches", "Reconciliation"].map((header) => (
              <th key={header} className="border-b border-line px-3 py-2 font-semibold">
                {header}
              </th>
            ))}
            {canEdit ? <th className="border-b border-line px-3 py-2 font-semibold">Action</th> : null}
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => (
            <tr key={project.id} className="hover:bg-surface/70">
              <td className="border-b border-line px-3 py-2 font-medium">{project.projectCode}</td>
              <td className="border-b border-line px-3 py-2">{project.title}</td>
              <td className="border-b border-line px-3 py-2">{project.school}</td>
              <td className="border-b border-line px-3 py-2">{project.department}</td>
              <td className="border-b border-line px-3 py-2">{project.status}</td>
              <td className="border-b border-line px-3 py-2">{project.summary.totalSanctionedAmount}</td>
              <td className="border-b border-line px-3 py-2">{project.summary.netDisbursedAmount}</td>
              <td className="border-b border-line px-3 py-2">{project.summary.availableSanctionedBalance}</td>
              <td className="border-b border-line px-3 py-2">{project.summary.trancheCount}</td>
              <td className="border-b border-line px-3 py-2">{project.summary.reconciliationStatus}</td>
              {canEdit ? <td className="border-b border-line px-3 py-2"><button className="focus-ring rounded-md bg-accent px-2 py-1 text-xs font-medium text-surface">Edit</button></td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

