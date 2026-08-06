import type { AIProposalPreview, ProjectListItem, ReconciliationIssue } from "../types/domain";

export const projects: ProjectListItem[] = [
  {
    id: "p-001",
    projectCode: "TRAI-SYN-001",
    title: "Low Cost Assistive Lab Prototype",
    school: "Engineering",
    department: "Mechanical Design",
    academicYear: "2026-27",
    status: "active",
    summary: {
      initialSanctionedAmount: "500000.00",
      approvedFundingIncreases: "50000.00",
      approvedFundingReductions: "0.00",
      totalSanctionedAmount: "550000.00",
      totalRequestedAmount: "300000.00",
      totalApprovedTrancheAmount: "300000.00",
      grossDisbursedAmount: "250000.00",
      totalRefundedAmount: "10000.00",
      netDisbursedAmount: "240000.00",
      totalUtilizedAmount: "180000.00",
      availableSanctionedBalance: "310000.00",
      unutilizedDisbursedBalance: "60000.00",
      pendingApprovedAmount: "50000.00",
      trancheCount: 2,
      reconciliationStatus: "balanced",
    },
  },
  {
    id: "p-002",
    projectCode: "TRAI-SYN-002",
    title: "Campus Water Quality Sensor Network",
    school: "Design",
    department: "Product Innovation",
    academicYear: "2026-27",
    status: "active",
    summary: {
      initialSanctionedAmount: "150000.00",
      approvedFundingIncreases: "0.00",
      approvedFundingReductions: "25000.00",
      totalSanctionedAmount: "125000.00",
      totalRequestedAmount: "160000.00",
      totalApprovedTrancheAmount: "160000.00",
      grossDisbursedAmount: "160000.00",
      totalRefundedAmount: "0.00",
      netDisbursedAmount: "160000.00",
      totalUtilizedAmount: "90000.00",
      availableSanctionedBalance: "-35000.00",
      unutilizedDisbursedBalance: "70000.00",
      pendingApprovedAmount: "0.00",
      trancheCount: 3,
      reconciliationStatus: "over_disbursed",
    },
  },
];

export const reconciliationIssues: ReconciliationIssue[] = [
  {
    id: "r-001",
    severity: "critical",
    issueType: "Over Disbursed",
    projectCode: "TRAI-SYN-002",
    projectTitle: "Campus Water Quality Sensor Network",
    description: "Net disbursement exceeds sanctioned funding by ₹35,000.00.",
    financialImpact: "35000.00",
    suggestedAction: "Review approved reductions and tranche approvals before further payment.",
  },
];

export const aiPreview: AIProposalPreview = {
  action: "propose_tranche_creation",
  target: "TRAI-SYN-001",
  allowed: true,
  warnings: ["Review the payment date before confirmation."],
  errors: [],
  proposedValues: {
    trancheSequence: "3",
    requestedAmount: "50000.00",
    approvedAmount: "50000.00",
    status: "draft",
  },
};

