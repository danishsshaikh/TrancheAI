import type {
  AIConversation,
  AIConversationSendResult,
  AIResponse,
  AuditEvent,
  ImportBatch,
  ProjectDetail,
  ProjectRow,
  ReconciliationIssue,
  SearchResult,
  SettingsPayload,
  TrancheRow,
  User,
} from "../types/domain";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export interface AuthSession {
  accessToken: string;
  user: User;
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

export function logout(token: string): Promise<{ status: string }> {
  return request("/api/v1/auth/logout", { token, method: "POST" });
}

export function currentUser(token: string): Promise<User> {
  return request("/api/v1/auth/me", { token });
}

export function fetchSettings(token: string): Promise<SettingsPayload> {
  return request("/api/v1/settings", { token });
}

export function fetchUsers(token: string): Promise<User[]> {
  return request("/api/v1/users", { token });
}

export function createUser(token: string, payload: Record<string, unknown>): Promise<User> {
  return request("/api/v1/users", { token, method: "POST", body: payload });
}

export function updateUser(token: string, userId: string, payload: Record<string, unknown>): Promise<User> {
  return request(`/api/v1/users/${userId}`, { token, method: "PATCH", body: payload });
}

export function globalSearch(token: string, query: string): Promise<SearchResult[]> {
  return request(`/api/v1/search?q=${encodeURIComponent(query)}`, { token });
}

export function fetchProjects(token: string, params: URLSearchParams = new URLSearchParams()): Promise<ProjectRow[]> {
  const query = params.toString();
  return request(`/api/v1/projects${query ? `?${query}` : ""}`, { token });
}

export function createProject(token: string, payload: Record<string, unknown>): Promise<ProjectRow> {
  return request("/api/v1/projects", { token, method: "POST", body: payload });
}

export function fetchProject(token: string, projectId: string): Promise<ProjectDetail> {
  return request(`/api/v1/projects/${projectId}`, { token });
}

export function updateProject(token: string, projectId: string, payload: Record<string, unknown>): Promise<ProjectRow> {
  return request(`/api/v1/projects/${projectId}`, { token, method: "PATCH", body: payload });
}

export function fetchProjectAudit(token: string, projectId: string): Promise<AuditEvent[]> {
  return request(`/api/v1/projects/${projectId}/audit`, { token });
}

export function createSanction(token: string, projectId: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/v1/projects/${projectId}/sanctions`, { token, method: "POST", body: payload });
}

export function submitSanction(token: string, sanctionId: string): Promise<Record<string, unknown>> {
  return request(`/api/v1/sanctions/${sanctionId}/submit`, { token, method: "POST" });
}

export function approveSanction(token: string, sanctionId: string): Promise<Record<string, unknown>> {
  return request(`/api/v1/sanctions/${sanctionId}/approve`, { token, method: "POST" });
}

export function createRevision(token: string, projectId: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/v1/projects/${projectId}/funding-revisions`, { token, method: "POST", body: payload });
}

export function submitRevision(token: string, revisionId: string): Promise<Record<string, unknown>> {
  return request(`/api/v1/funding-revisions/${revisionId}/submit`, { token, method: "POST" });
}

export function approveRevision(token: string, revisionId: string): Promise<Record<string, unknown>> {
  return request(`/api/v1/funding-revisions/${revisionId}/approve`, { token, method: "POST" });
}

export function createTranche(token: string, projectId: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/v1/projects/${projectId}/tranches`, { token, method: "POST", body: payload });
}

export function fetchTranches(token: string): Promise<TrancheRow[]> {
  return request("/api/v1/tranches", { token });
}

export function trancheAction(token: string, trancheId: string, action: string, payload?: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/v1/tranches/${trancheId}/${action}`, { token, method: "POST", body: payload });
}

export function fetchReconciliation(token: string): Promise<ReconciliationIssue[]> {
  return request("/api/v1/reports/reconciliation", { token });
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

export function commitImport(token: string, batchId: string): Promise<ImportBatch> {
  return request(`/api/v1/imports/${batchId}/commit`, { token, method: "POST" });
}

export function listAIConversations(token: string): Promise<AIConversation[]> {
  return request("/api/v1/ai/conversations", { token });
}

export function createAIConversation(token: string, payload: Record<string, unknown>): Promise<AIConversation> {
  return request("/api/v1/ai/conversations", { token, method: "POST", body: payload });
}

export function fetchAIConversation(token: string, conversationId: string): Promise<AIConversation> {
  return request(`/api/v1/ai/conversations/${conversationId}`, { token });
}

export function updateAIConversation(token: string, conversationId: string, payload: Record<string, unknown>): Promise<AIConversation> {
  return request(`/api/v1/ai/conversations/${conversationId}`, { token, method: "PATCH", body: payload });
}

export function sendAIConversationMessage(token: string, conversationId: string, text: string, language?: string): Promise<AIConversationSendResult> {
  return request(`/api/v1/ai/conversations/${conversationId}/messages`, { token, method: "POST", body: { text, language } });
}

export function confirmAIProposal(token: string, proposalId: string): Promise<AIResponse> {
  return request(`/api/v1/ai/proposals/${proposalId}/confirm`, { token, method: "POST" });
}

export function cancelAIProposal(token: string, proposalId: string): Promise<AIResponse> {
  return request(`/api/v1/ai/proposals/${proposalId}/cancel`, { token, method: "POST" });
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
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return body;
}
