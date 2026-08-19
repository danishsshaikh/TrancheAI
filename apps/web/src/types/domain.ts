export type Role = "administrator" | "fund_administrator" | "fund_reviewer" | "auditor" | "viewer";

export interface FinancialSummary {
  initialSanctionedAmount?: string;
  approvedFundingIncreases?: string;
  approvedFundingReductions?: string;
  totalSanctionedAmount: string;
  totalRequestedAmount?: string;
  totalApprovedTrancheAmount?: string;
  grossDisbursedAmount?: string;
  totalRefundedAmount?: string;
  netDisbursedAmount: string;
  totalUtilizedAmount?: string;
  availableSanctionedBalance: string;
  unutilizedDisbursedBalance?: string;
  pendingApprovedAmount: string;
  trancheCount: number;
  reconciliationStatus: ReconciliationStatus;
}

export interface ProjectRow {
  id: string;
  projectCode: string;
  title: string;
  school?: string;
  department?: string;
  academicYear?: string;
  status: string;
  fundingStatus: string;
  version: number;
  summary: FinancialSummary;
}

export type ProjectListItem = ProjectRow;
export type ReconciliationStatus = "balanced" | "over_disbursed" | "over_utilized" | "missing_sanction" | "refund_conflict" | "attention_required" | string;

export interface ReconciliationIssue {
  id?: string;
  issueType: string;
  severity: "low" | "medium" | "high" | "critical";
  projectId?: string;
  projectCode: string;
  projectTitle?: string;
  description: string;
  financialImpact: string;
  status?: string;
  suggestedAction: string;
}

export interface AIProposalPreview {
  action: string;
  target: string;
  allowed: boolean;
  warnings: string[];
  errors: string[];
  proposedValues: Record<string, string>;
}
