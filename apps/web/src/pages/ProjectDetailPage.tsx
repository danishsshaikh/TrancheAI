import { useParams } from "react-router-dom";
import { demoProjects } from "../api/client";
import { Metric } from "../components/Metric";

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const project = demoProjects.find((item) => item.id === projectId) ?? demoProjects[0];
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-muted">Projects / {project.projectCode}</p>
        <h1 className="text-2xl font-semibold">{project.title}</h1>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Total Sanctioned" value={project.summary.totalSanctionedAmount} />
        <Metric label="Net Disbursed" value={project.summary.netDisbursedAmount} />
        <Metric label="Available Balance" value={project.summary.availableSanctionedBalance} />
        <Metric label="Reconciliation" value={project.summary.reconciliationStatus} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {["Overview", "Participants", "Funding", "Tranches", "Timeline", "Audit History"].map((section) => (
          <section key={section} className="rounded-md border border-line bg-panel p-4">
            <h2 className="text-base font-semibold">{section}</h2>
            <div className="mt-3 text-sm text-muted">Server records will populate this section.</div>
          </section>
        ))}
      </div>
    </div>
  );
}

