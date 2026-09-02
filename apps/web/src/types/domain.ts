export type Role = "administrator" | "fund_administrator" | "fund_reviewer" | "auditor" | "viewer" | string;

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  roleLabel?: string;
  isActive?: boolean;
}

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
  reconciliationStatus: string;
}

export interface Participant {
  id?: string;
  role: string;
  roleLabel?: string;
  fullName: string;
  email?: string | null;
  phone?: string | null;
  department?: string | null;
  organization?: string | null;
  isPrimary?: boolean;
  startDate?: string | null;
  endDate?: string | null;
  notes?: string | null;
}

export interface ProjectRow {
  id: string;
  projectCode: string;
  project_code?: string;
  title: string;
  shortTitle?: string | null;
  description?: string | null;
  institution?: string | null;
  school?: string | null;
  department?: string | null;
  academicYear?: string | null;
  cohort?: string | null;
  category?: string | null;
  domain?: string | null;
  technologyReadinessLevel?: string | null;
  prototypeStatus?: string | null;
  publicationStatus?: string | null;
  patentStatus?: string | null;
  startupStatus?: string | null;
  status: string;
  projectStatus?: string;
  fundingStatus: string;
  startDate?: string | null;
  expectedCompletionDate?: string | null;
  actualCompletionDate?: string | null;
  closureNotes?: string | null;
  remarks?: string | null;
  participants?: Participant[];
  version: number;
  summary: FinancialSummary;
}

export interface ProjectDetail extends ProjectRow {
  sanctions: Record<string, unknown>[];
  fundingRevisions: Record<string, unknown>[];
  tranches: TrancheRow[];
}

export interface TrancheRow {
  id: string;
  projectId: string;
  projectCode?: string;
  projectTitle?: string;
  sequenceNumber: number;
  transactionType: string;
  transactionTypeLabel?: string;
  requestedAmount: string;
  approvedAmount: string;
  disbursedAmount: string;
  refundAmount: string;
  utilizedAmount: string;
  paymentReference?: string | null;
  paymentMode?: string | null;
  purchaseOrderNumber?: string | null;
  requestDate?: string | null;
  approvalDate?: string | null;
  expectedDisbursementDate?: string | null;
  actualDisbursementDate?: string | null;
  billStatus?: string | null;
  utilizationCertificateStatus?: string | null;
  status: string;
  statusLabel?: string;
  remarks?: string | null;
}

export interface ReconciliationIssue {
  id?: string;
  issueType: string;
  severity: "low" | "medium" | "high" | "critical" | string;
  projectId?: string;
  projectCode: string;
  projectTitle?: string;
  description: string;
  financialImpact?: string | null;
  status?: string;
  suggestedAction?: string;
}

export interface AuditEvent {
  id: string;
  entityType: string;
  entityId: string;
  action: string;
  actorId?: string | null;
  timestamp?: string | null;
  reason?: string | null;
  previousValues: Record<string, unknown>;
  newValues: Record<string, unknown>;
}

export interface SearchResult {
  type: string;
  label: string;
  description?: string | null;
  to: string;
  projectId?: string;
  trancheId?: string;
}

export interface ImportRowResult {
  id: string;
  rowNumber: number;
  status: string;
  proposedAction: string;
  duplicate: boolean;
  errors: string[];
  warnings: string[];
  rawValues: Record<string, unknown>;
  normalizedValues: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface ImportBatch {
  id: string;
  importType: string;
  filename: string;
  status: string;
  rowsDetected: number;
  validRows: number;
  invalidRows: number;
  duplicateRows: number;
  existingRecordsMatched: number;
  proposedCreates: number;
  proposedUpdates: number;
  committedRows: number;
  failedRows: number;
  skippedRows: number;
  rows: ImportRowResult[];
}

export interface AIProposal {
  id: string;
  action: string;
  status: string;
  targetEntityType?: string | null;
  targetEntityId?: string | null;
  currentValues: Record<string, unknown>;
  proposedValues: Record<string, unknown>;
  validationResult?: { valid?: boolean; warnings?: string[]; errors?: string[] };
  message?: string | null;
  expiresAt?: string | null;
  result?: Record<string, unknown>;
}

export interface AIResponse {
  kind: "answer" | "proposal" | "clarification" | "error" | "result" | "export" | string;
  message: string;
  proposal?: AIProposal;
  data?: Record<string, unknown> | Array<Record<string, unknown>>;
  download_url?: string;
}

export interface AIMessage {
  id: string;
  conversationId: string;
  role: "user" | "assistant" | string;
  content: string;
  responseKind?: string | null;
  action?: string | null;
  metadata?: AIResponse | Record<string, unknown>;
  proposalId?: string | null;
  createdAt?: string | null;
}

export interface AIConversation {
  id: string;
  title: string;
  projectId?: string | null;
  projectCode?: string | null;
  archived: boolean;
  messages?: AIMessage[];
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface AIConversationSendResult {
  conversation: AIConversation;
  response: AIResponse;
}

export interface SettingsPayload {
  profile: User;
  roles: Array<{ value: string; label: string }>;
  ai: {
    enabled: boolean;
    baseUrlConfigured: boolean;
    modelConfigured: boolean;
    model?: string | null;
    timeoutSeconds: number;
    maxTokens: number;
    temperature: number;
  };
  application: {
    name: string;
    version: string;
    license: string;
  };
}
