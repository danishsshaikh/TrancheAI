import { Metric } from "../components/Metric";
import { useQuery } from "@tanstack/react-query";
import { fetchProjects, fetchReconciliation } from "../api/client";
import { useToken } from "../app/AuthContext";

export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div>
      <p className="text-sm text-muted">{description}</p>
      <h1 className="text-2xl font-semibold">{title}</h1>
    </div>
  );
}

export function PageSkeleton({ title }: { title: string }) {
  return (
    <section className="space-y-4">
      <PageHeader title={title} description="Loading current records." />
      <div className="rounded-md border border-line bg-panel p-8 text-sm text-muted">Loading.</div>
    </section>
  );
}

export function ErrorState({ title }: { title: string }) {
  return (
    <section className="space-y-4">
      <PageHeader title={title} description="The server could not return this view." />
      <div className="rounded-md border border-danger bg-panel p-8 text-sm text-danger">Unable to load records.</div>
    </section>
  );
}

export function DashboardPage() {
  const token = useToken();
  const projects = useQuery({ queryKey: ["projects"], queryFn: () => fetchProjects(token) });
  const issues = useQuery({ queryKey: ["reconciliation"], queryFn: () => fetchReconciliation(token) });
  const rows = projects.data ?? [];
  const totals = rows.reduce(
    (acc, project) => ({
      active: acc.active + (project.status === "active" ? 1 : 0),
      sanctioned: acc.sanctioned + Number(project.summary.totalSanctionedAmount),
      disbursed: acc.disbursed + Number(project.summary.netDisbursedAmount),
      available: acc.available + Number(project.summary.availableSanctionedBalance),
      pending: acc.pending + Number(project.summary.pendingApprovedAmount),
    }),
    { active: 0, sanctioned: 0, disbursed: 0, available: 0, pending: 0 },
  );
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-muted">Dashboard</p>
        <h1 className="text-2xl font-semibold">Fund administration overview</h1>
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Metric label="Active Projects" value={String(totals.active)} />
        <Metric label="Total Sanctioned" value={money(totals.sanctioned)} />
        <Metric label="Net Disbursed" value={money(totals.disbursed)} />
        <Metric label="Available Balance" value={money(totals.available)} />
        <Metric label="Pending Tranches" value={money(totals.pending)} />
        <Metric label="Open Issues" value={String(issues.data?.length ?? 0)} />
      </div>
      <section className="rounded-md border border-line bg-panel p-4">
        <h2 className="text-base font-semibold">Recent activity</h2>
        {projects.isLoading ? <div className="mt-3 text-sm text-muted">Loading projects.</div> : null}
        {projects.error ? <div className="mt-3 text-sm text-danger">Projects could not be loaded.</div> : null}
        <div className="mt-3 divide-y divide-line text-sm">
          {rows.slice(0, 5).map((project) => (
            <div key={project.id} className="py-2">
              {project.projectCode} · {project.title}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function money(value: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value);
}
