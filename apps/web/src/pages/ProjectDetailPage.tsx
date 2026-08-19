import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { approveRevision, approveSanction, createRevision, createSanction, createTranche, fetchProject, fetchProjectAudit, trancheAction, updateProject } from "../api/client";
import { useAuth, useToken } from "../app/AuthContext";
import { Metric } from "../components/Metric";

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const token = useToken();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("0.00");
  const [projectForm, setProjectForm] = useState({ title: "", school: "", department: "", status: "draft" });
  const { data: project, isLoading, error } = useQuery({ queryKey: ["project", projectId], queryFn: () => fetchProject(token, projectId ?? "") });
  const canReadAudit = user?.role === "administrator" || user?.role === "auditor";
  const auditHistory = useQuery({ queryKey: ["project", projectId, "audit"], queryFn: () => fetchProjectAudit(token, projectId ?? ""), enabled: Boolean(canReadAudit && projectId), retry: false });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["project", projectId] });
  useEffect(() => {
    if (project) {
      setProjectForm({ title: project.title, school: project.school ?? "", department: project.department ?? "", status: project.status });
    }
  }, [project]);
  const saveProject = useMutation({
    mutationFn: () => updateProject(token, projectId ?? "", {
      title: projectForm.title,
      school: projectForm.school || null,
      department: projectForm.department || null,
      project_status: projectForm.status,
      version: project?.version,
    }),
    onSuccess: refresh,
  });
  const addSanction = useMutation({ mutationFn: () => createSanction(token, projectId ?? "", { sanction_reference: `SAN-${Date.now()}`, amount }), onSuccess: refresh });
  const addRevision = useMutation({ mutationFn: () => createRevision(token, projectId ?? "", { revision_number: project?.fundingRevisions.length ? project.fundingRevisions.length + 1 : 1, revision_type: "increase", amount }), onSuccess: refresh });
  const addTranche = useMutation({ mutationFn: () => createTranche(token, projectId ?? "", { sequence_number: project?.tranches.length ? project.tranches.length + 1 : 1, transaction_type: "advance", requested_amount: amount, approved_amount: amount }), onSuccess: refresh });
  const action = useMutation({ mutationFn: ({ trancheId, name, payload }: { trancheId: string; name: string; payload?: Record<string, unknown> }) => trancheAction(token, trancheId, name, payload), onSuccess: refresh });
  const sanctionApproval = useMutation({ mutationFn: (id: string) => approveSanction(token, id), onSuccess: refresh });
  const revisionApproval = useMutation({ mutationFn: (id: string) => approveRevision(token, id), onSuccess: refresh });
  if (isLoading) return <div className="rounded-md border border-line bg-panel p-8 text-sm text-muted">Loading project.</div>;
  if (error || !project) return <div className="rounded-md border border-danger bg-panel p-8 text-sm text-danger">Project could not be loaded.</div>;
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-muted">Projects / {project.projectCode}</p>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h1 className="text-2xl font-semibold">{project.title}</h1>
          <Link className="focus-ring inline-flex w-fit items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm" to={`/ai?projectId=${project.id}&projectCode=${encodeURIComponent(project.projectCode)}`}>
            <Bot className="h-4 w-4 text-accent" />
            AI Assistant
          </Link>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Total Sanctioned" value={project.summary.totalSanctionedAmount} />
        <Metric label="Net Disbursed" value={project.summary.netDisbursedAmount} />
        <Metric label="Available Balance" value={project.summary.availableSanctionedBalance} />
        <Metric label="Reconciliation" value={project.summary.reconciliationStatus} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-md border border-line bg-panel p-4 lg:col-span-2">
          <h2 className="text-base font-semibold">Project Fields</h2>
          <div className="mt-3 grid gap-2 md:grid-cols-[2fr_1fr_1fr_160px_auto]">
            <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" aria-label="Project title" value={projectForm.title} onChange={(event) => setProjectForm((value) => ({ ...value, title: event.target.value }))} />
            <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" aria-label="School" value={projectForm.school} onChange={(event) => setProjectForm((value) => ({ ...value, school: event.target.value }))} />
            <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" aria-label="Department" value={projectForm.department} onChange={(event) => setProjectForm((value) => ({ ...value, department: event.target.value }))} />
            <select className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" aria-label="Project status" value={projectForm.status} onChange={(event) => setProjectForm((value) => ({ ...value, status: event.target.value }))}>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="on_hold">On hold</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <button className="focus-ring rounded-md border border-line px-3 py-2 text-sm" onClick={() => saveProject.mutate()} disabled={saveProject.isPending}>Save</button>
          </div>
          {saveProject.error ? <div className="mt-3 text-sm text-danger">Project update failed. Refresh and check role permissions.</div> : null}
        </section>
        <section className="rounded-md border border-line bg-panel p-4 lg:col-span-2">
          <h2 className="text-base font-semibold">Workflow Actions</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <input className="focus-ring rounded-md border border-line bg-surface px-3 py-2 text-sm" value={amount} onChange={(event) => setAmount(event.target.value)} />
            <button className="focus-ring rounded-md border border-line px-3 py-2 text-sm" onClick={() => addSanction.mutate()}>Add Sanction</button>
            <button className="focus-ring rounded-md border border-line px-3 py-2 text-sm" onClick={() => addRevision.mutate()}>Add Increase</button>
            <button className="focus-ring rounded-md border border-line px-3 py-2 text-sm" onClick={() => addTranche.mutate()}>Add Tranche</button>
          </div>
          {[addSanction.error, addRevision.error, addTranche.error, action.error, sanctionApproval.error, revisionApproval.error].find(Boolean) ? (
            <div className="mt-3 text-sm text-danger">Action failed. Check role permissions and validation rules.</div>
          ) : null}
        </section>
        <RecordSection title="Funding Sanctions" rows={project.sanctions} actionLabel="Approve" onAction={(row) => sanctionApproval.mutate(row.id)} />
        <RecordSection title="Funding Revisions" rows={project.fundingRevisions} actionLabel="Approve" onAction={(row) => revisionApproval.mutate(row.id)} />
        <RecordSection
          title="Tranches"
          rows={project.tranches}
          renderActions={(row) => (
            <div className="mt-2 flex flex-wrap gap-2">
              <button className="focus-ring rounded border border-line px-2 py-1 text-xs" onClick={() => action.mutate({ trancheId: row.id, name: "submit" })}>Submit</button>
              <button className="focus-ring rounded border border-line px-2 py-1 text-xs" onClick={() => action.mutate({ trancheId: row.id, name: "approve" })}>Approve</button>
              <button className="focus-ring rounded border border-line px-2 py-1 text-xs" onClick={() => action.mutate({ trancheId: row.id, name: "disburse", payload: { amount: row.approvedAmount, payment_reference: `UTR-${Date.now()}`, payment_date: new Date().toISOString().slice(0, 10) } })}>Disburse</button>
              <button className="focus-ring rounded border border-line px-2 py-1 text-xs" onClick={() => action.mutate({ trancheId: row.id, name: "record-refund", payload: { amount: "0.00" } })}>Refund</button>
              <button className="focus-ring rounded border border-line px-2 py-1 text-xs" onClick={() => action.mutate({ trancheId: row.id, name: "record-utilization", payload: { amount: row.disbursedAmount ?? "0.00" } })}>Utilize</button>
            </div>
          )}
        />
        <section className="rounded-md border border-line bg-panel p-4 lg:col-span-2">
          <h2 className="text-base font-semibold">Audit History</h2>
          {!canReadAudit ? <div className="mt-3 text-sm text-muted">Visible to administrators and auditors.</div> : null}
          {auditHistory.isLoading ? <div className="mt-3 text-sm text-muted">Loading audit history.</div> : null}
          {auditHistory.error ? <div className="mt-3 text-sm text-danger">Audit history could not be loaded.</div> : null}
          <div className="mt-3 divide-y divide-line text-sm">
            {(auditHistory.data ?? []).slice(0, 10).map((event) => (
              <div key={event.id} className="grid gap-2 py-2 md:grid-cols-[160px_1fr_180px]">
                <span className="font-medium">{event.action}</span>
                <span className="text-muted">{event.entityType}</span>
                <span className="text-muted">{event.timestamp ? new Date(event.timestamp).toLocaleString() : ""}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function RecordSection({
  title,
  rows,
  actionLabel,
  onAction,
  renderActions,
}: {
  title: string;
  rows: Array<Record<string, string>>;
  actionLabel?: string;
  onAction?: (row: Record<string, string>) => void;
  renderActions?: (row: Record<string, string>) => ReactNode;
}) {
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-3 space-y-2 text-sm">
        {rows.length === 0 ? <div className="text-muted">No records yet.</div> : null}
        {rows.map((row) => (
          <div key={row.id} className="rounded border border-line bg-surface p-2">
            {Object.entries(row).slice(1, 5).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-3">
                <span className="text-muted">{key}</span>
                <span>{String(value ?? "")}</span>
              </div>
            ))}
            {actionLabel && onAction ? <button className="focus-ring mt-2 rounded border border-line px-2 py-1 text-xs" onClick={() => onAction(row)}>{actionLabel}</button> : null}
            {renderActions?.(row)}
          </div>
        ))}
      </div>
    </section>
  );
}
