import type { ProjectRow, ReconciliationIssue } from "../types/domain";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: string;
}

export interface AuthSession {
  accessToken: string;
  user: User;
}

export interface ProjectDetail extends ProjectRow {
  sanctions: Array<Record<string, string>>;
  fundingRevisions: Array<Record<string, string>>;
  tranches: Array<Record<string, string>>;
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

export interface ImportRowResult {
  id: string;
  rowNumber: number;
  status: string;
  proposedAction: string;
  duplicate: boolean;
  entityType?: string | null;
  entityId?: string | null;
  existingEntityId?: string | null;
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

export async function login(email: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await parseResponse(response);
  return { accessToken: body.access_token, user: body.user };
}

export async function currentUser(token: string): Promise<User> {
  return request<User>("/api/v1/auth/me", { token });
}

export async function fetchProjects(token: string, params: URLSearchParams = new URLSearchParams()): Promise<ProjectRow[]> {
  return request<ProjectRow[]>(`/api/v1/projects?${params.toString()}`, { token });
}

export async function createProject(token: string, payload: Record<string, unknown>): Promise<ProjectRow> {
  return request<ProjectRow>("/api/v1/projects", { token, method: "POST", body: payload });
}

export async function fetchProject(token: string, projectId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/v1/projects/${projectId}`, { token });
}

export async function updateProject(token: string, projectId: string, payload: Record<string, unknown>): Promise<ProjectRow> {
  return request<ProjectRow>(`/api/v1/projects/${projectId}`, { token, method: "PATCH", body: payload });
}

export async function fetchProjectAudit(token: string, projectId: string): Promise<AuditEvent[]> {
  return request<AuditEvent[]>(`/api/v1/projects/${projectId}/audit`, { token });
}

export async function fetchReconciliation(token: string): Promise<ReconciliationIssue[]> {
  return request<ReconciliationIssue[]>("/api/v1/reports/reconciliation", { token });
}

export async function createSanction(token: string, projectId: string, payload: Record<string, unknown>) {
  return request<Record<string, string>>(`/api/v1/projects/${projectId}/sanctions`, { token, method: "POST", body: payload });
}

export async function approveSanction(token: string, sanctionId: string) {
  return request<Record<string, string>>(`/api/v1/sanctions/${sanctionId}/approve`, { token, method: "POST" });
}

export async function createRevision(token: string, projectId: string, payload: Record<string, unknown>) {
  return request<Record<string, string>>(`/api/v1/projects/${projectId}/funding-revisions`, { token, method: "POST", body: payload });
}

export async function approveRevision(token: string, revisionId: string) {
  return request<Record<string, string>>(`/api/v1/funding-revisions/${revisionId}/approve`, { token, method: "POST" });
}

export async function createTranche(token: string, projectId: string, payload: Record<string, unknown>) {
  return request<Record<string, string>>(`/api/v1/projects/${projectId}/tranches`, { token, method: "POST", body: payload });
}

export async function trancheAction(token: string, trancheId: string, action: string, payload?: Record<string, unknown>) {
  return request<Record<string, string>>(`/api/v1/tranches/${trancheId}/${action}`, { token, method: "POST", body: payload });
}

export async function previewImport(token: string, importType: string, file: File): Promise<ImportBatch> {
  const body = new FormData();
  body.append("import_type", importType);
  body.append("file", file);
  const response = await fetch(`${API_BASE}/api/v1/imports/preview`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
  return parseResponse(response) as Promise<ImportBatch>;
}

export async function commitImport(token: string, batchId: string): Promise<ImportBatch> {
  return request<ImportBatch>(`/api/v1/imports/${batchId}/commit`, { token, method: "POST" });
}

export function exportUrl(path: string) {
  return `${API_BASE}${path}`;
}

export async function downloadFile(token: string, path: string, filename: string) {
  const response = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(`Export failed with ${response.status}`);
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function request<T>(path: string, options: { token: string; method?: string; body?: unknown }): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${options.token}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  return parseResponse(response) as Promise<T>;
}

async function parseResponse(response: Response) {
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(body.detail ?? `Request failed with ${response.status}`);
  }
  return body;
}
