import type { AIProposalPreview, ProjectRow, ReconciliationIssue } from "../types/domain";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export async function fetchProjects(params: URLSearchParams = new URLSearchParams()): Promise<ProjectRow[]> {
  const response = await fetch(`${API_BASE}/api/v1/projects?${params.toString()}`);
  if (!response.ok) throw new Error("Projects could not be loaded.");
  return response.json();
}

export async function fetchReconciliation(): Promise<ReconciliationIssue[]> {
  const response = await fetch(`${API_BASE}/api/v1/reports/reconciliation`);
  if (!response.ok) throw new Error("Reconciliation issues could not be loaded.");
  return response.json();
}

export async function fetchAiPreview(): Promise<AIProposalPreview> {
  if (import.meta.env.VITE_USE_MOCK_API !== "false") return demoAiPreview;
  const response = await fetch(`${API_BASE}/api/v1/ai/preview`);
  if (!response.ok) throw new Error("AI preview could not be loaded.");
  return response.json();
}

export const api = {
  projects: fetchProjects,
  reconciliation: fetchReconciliation,
  aiPreview: fetchAiPreview
};

export const demoProjects: ProjectRow[] = [
  {
    id: "demo-1",
    projectCode: "SP-001",
    title: "Synthetic Assistive Mobility Prototype",
    school: "School of Engineering",
    department: "Mechanical",
    academicYear: "2026-27",
    status: "Active",
    fundingStatus: "Partially Disbursed",
    summary: {
      totalSanctionedAmount: "500000.00",
      netDisbursedAmount: "240000.00",
      availableSanctionedBalance: "260000.00",
      pendingApprovedAmount: "125000.00",
      trancheCount: 3,
      reconciliationStatus: "balanced"
    }
  }
];

export const demoIssues: ReconciliationIssue[] = [
  {
    issueType: "missing_payment_reference",
    severity: "medium",
    projectId: "demo-1",
    projectCode: "SP-001",
    description: "Disbursed tranche is missing a payment reference.",
    financialImpact: "0.00",
    status: "open",
    suggestedAction: "Record the cheque, UTR or bank reference."
  }
];

export const demoAiPreview: AIProposalPreview = {
  action: "propose_tranche_creation",
  target: "SP-001",
  allowed: true,
  warnings: ["Review the payment date before confirmation."],
  errors: [],
  proposedValues: {
    trancheSequence: "4",
    requestedAmount: "50000.00",
    approvedAmount: "50000.00",
    status: "draft"
  }
};
