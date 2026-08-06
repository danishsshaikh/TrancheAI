import { Metric } from "../components/Metric";
import { demoIssues, demoProjects } from "../api/client";

export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div>
      <p className="text-sm text-muted">{description}</p>
      <h1 className="text-2xl font-semibold">{title}</h1>
    </div>
  );
}

export function DashboardPage() {
  const project = demoProjects[0];
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-muted">Dashboard</p>
        <h1 className="text-2xl font-semibold">Fund administration overview</h1>
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Metric label="Active Projects" value="1" />
        <Metric label="Total Sanctioned" value={project.summary.totalSanctionedAmount} />
        <Metric label="Net Disbursed" value={project.summary.netDisbursedAmount} />
        <Metric label="Available Balance" value={project.summary.availableSanctionedBalance} />
        <Metric label="Pending Tranches" value={project.summary.pendingApprovedAmount} />
        <Metric label="Open Issues" value={String(demoIssues.length)} />
      </div>
      <section className="rounded-md border border-line bg-panel p-4">
        <h2 className="text-base font-semibold">Recent activity</h2>
        <div className="mt-3 text-sm text-muted">Server activity will appear here after the API is connected.</div>
      </section>
    </div>
  );
}
