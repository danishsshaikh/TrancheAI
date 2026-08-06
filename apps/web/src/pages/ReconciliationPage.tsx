import { useQuery } from "@tanstack/react-query";
import { CircleAlert } from "lucide-react";
import { fetchReconciliation } from "../api/client";
import { useToken } from "../app/AuthContext";
import { Money } from "../components/Money";
import { ErrorState, PageHeader, PageSkeleton } from "./DashboardPage";

export function ReconciliationPage() {
  const token = useToken();
  const { data = [], isLoading, error } = useQuery({ queryKey: ["reconciliation"], queryFn: () => fetchReconciliation(token) });
  if (isLoading) return <PageSkeleton title="Reconciliation" />;
  if (error) return <ErrorState title="Reconciliation" />;
  return (
    <section className="space-y-5">
      <PageHeader title="Reconciliation" description="Open issues that require administrative review before further disbursement or closure." />
      <div className="overflow-x-auto rounded-lg border border-border bg-[oklch(99%_0.004_250)]">
        <table className="min-w-[900px] w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase text-[oklch(42%_0.014_250)]">
            <tr>
              <th className="px-3 py-3">Severity</th>
              <th className="px-3 py-3">Issue Type</th>
              <th className="px-3 py-3">Project</th>
              <th className="px-3 py-3">Description</th>
              <th className="px-3 py-3 text-right">Impact</th>
              <th className="px-3 py-3">Suggested Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.map((issue) => (
              <tr key={issue.id}>
                <td className="px-3 py-3"><span className="inline-flex items-center gap-1 rounded bg-[oklch(94%_0.035_25)] px-2 py-1 text-xs font-medium text-danger"><CircleAlert className="h-3 w-3" />{issue.severity}</span></td>
                <td className="px-3 py-3 font-medium">{issue.issueType}</td>
                <td className="px-3 py-3">{issue.projectCode}<div className="text-xs text-[oklch(45%_0.014_250)]">{issue.projectTitle}</div></td>
                <td className="px-3 py-3">{issue.description}</td>
                <td className="px-3 py-3 text-right"><Money value={issue.financialImpact} /></td>
                <td className="px-3 py-3">{issue.suggestedAction}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 ? <div className="p-8 text-center text-sm text-[oklch(45%_0.014_250)]">No reconciliation issues are open.</div> : null}
      </div>
    </section>
  );
}
