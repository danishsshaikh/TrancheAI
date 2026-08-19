import { AlertTriangle, Bot, Check, Download, FileText, Loader2, Send, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { cancelAIProposal, confirmAIProposal, downloadFile, sendAIRequest } from "../api/client";
import type { AIProposal, AIResponse } from "../api/client";
import { useToken } from "../app/AuthContext";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: AIResponse;
}

const fallbackSuggestions = [
  "Find projects related to robotics",
  "List reconciliation issues",
  "Generate project master export",
];

export function AiAssistantPage() {
  const token = useToken();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("projectId") ?? undefined;
  const projectCode = searchParams.get("projectCode") ?? undefined;
  const suggestions = useMemo(() => (projectCode ? [`Summarize ${projectCode}`, `Show financial summary for ${projectCode}`, `Create a draft tranche of INR 50000 for ${projectCode}`] : fallbackSuggestions), [projectCode]);
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeProposal, setActiveProposal] = useState<AIProposal | null>(null);

  const ask = useMutation({
    mutationFn: (text: string) => sendAIRequest(token, { text, current_project_id: projectId, current_project_code: projectCode }),
    onSuccess: (response) => {
      setMessages((items) => [...items, { id: uniqueId("assistant"), role: "assistant", text: response.message, response }]);
      if (response.proposal) setActiveProposal(response.proposal);
    },
    onError: (error) => {
      setMessages((items) => [...items, { id: uniqueId("assistant"), role: "assistant", text: error instanceof Error ? error.message : "AI request failed.", response: { kind: "error", message: "AI request failed." } }]);
    },
  });

  const confirm = useMutation({
    mutationFn: () => {
      if (!activeProposal) throw new Error("No proposal selected.");
      return confirmAIProposal(token, activeProposal.id);
    },
    onSuccess: (response) => {
      if (response.proposal) setActiveProposal(response.proposal);
      setMessages((items) => [...items, { id: uniqueId("assistant"), role: "assistant", text: response.message, response }]);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["reconciliation"] });
    },
  });

  const cancel = useMutation({
    mutationFn: () => {
      if (!activeProposal) throw new Error("No proposal selected.");
      return cancelAIProposal(token, activeProposal.id);
    },
    onSuccess: (response) => {
      if (response.proposal) setActiveProposal(response.proposal);
      setMessages((items) => [...items, { id: uniqueId("assistant"), role: "assistant", text: response.message, response }]);
    },
  });

  const download = useMutation({
    mutationFn: (path: string) => downloadFile(token, path, path.split("/").pop() ?? "trancheai-export.csv"),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text || ask.isPending) return;
    setMessages((items) => [...items, { id: uniqueId("user"), role: "user", text }]);
    setPrompt("");
    ask.mutate(text);
  }

  const pendingProposal = activeProposal?.status === "pending_confirmation";

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-muted">AI Assistant</p>
          <h1 className="text-2xl font-semibold">TrancheAI workflow assistant</h1>
        </div>
        {projectCode ? (
          <div className="inline-flex w-fit items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm">
            <FileText className="h-4 w-4 text-accent" />
            <span>{projectCode}</span>
          </div>
        ) : null}
      </div>

      <div className="grid min-h-[680px] gap-4 xl:grid-cols-[minmax(0,1fr)_390px]">
        <section className="flex min-h-[560px] flex-col rounded-md border border-line bg-panel">
          <div className="border-b border-line px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Bot className="h-4 w-4 text-accent" />
              Assistant thread
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 ? (
              <div className="rounded-md border border-dashed border-line bg-surface p-5 text-sm text-muted">No messages yet.</div>
            ) : null}
            {messages.map((message) => (
              <article key={message.id} className={`max-w-[88%] rounded-md border p-3 text-sm ${message.role === "user" ? "ml-auto border-accent bg-surface" : "border-line bg-surface"}`}>
                <div className="mb-1 text-xs font-medium uppercase tracking-normal text-muted">{message.role === "user" ? "You" : "Assistant"}</div>
                <p className="whitespace-pre-wrap break-words">{message.text}</p>
                {message.response?.data ? <DataBlock data={message.response.data} /> : null}
                {message.response?.download_url ? (
                  <button className="focus-ring mt-3 inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-medium" onClick={() => download.mutate(message.response?.download_url ?? "")} disabled={download.isPending}>
                    <Download className="h-4 w-4" />
                    Download export
                  </button>
                ) : null}
              </article>
            ))}
            {ask.isPending ? (
              <div className="inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                Working
              </div>
            ) : null}
          </div>

          <div className="border-t border-line p-4">
            <div className="mb-3 flex flex-wrap gap-2">
              {suggestions.map((item) => (
                <button key={item} className="focus-ring rounded-md border border-line bg-surface px-3 py-1.5 text-xs hover:border-accent" onClick={() => setPrompt(item)} type="button">
                  {item}
                </button>
              ))}
            </div>
            <form className="flex gap-2" onSubmit={submit}>
              <textarea
                className="focus-ring min-h-16 flex-1 resize-none rounded-md border border-line bg-surface px-3 py-2 text-sm"
                aria-label="AI request"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
              <button className="focus-ring inline-flex h-16 w-16 shrink-0 items-center justify-center rounded-md bg-accent text-surface disabled:opacity-55" aria-label="Send AI request" disabled={ask.isPending || !prompt.trim()}>
                {ask.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </button>
            </form>
          </div>
        </section>

        <aside className="space-y-4">
          <ProposalPanel proposal={activeProposal} onConfirm={() => confirm.mutate()} onCancel={() => cancel.mutate()} confirmBusy={confirm.isPending} cancelBusy={cancel.isPending} canAct={Boolean(pendingProposal)} />
          {(confirm.error || cancel.error || download.error) ? (
            <div className="rounded-md border border-danger bg-panel p-3 text-sm text-danger">Action failed. Refresh the proposal and check role permissions.</div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

function ProposalPanel({ proposal, onConfirm, onCancel, confirmBusy, cancelBusy, canAct }: { proposal: AIProposal | null; onConfirm: () => void; onCancel: () => void; confirmBusy: boolean; cancelBusy: boolean; canAct: boolean }) {
  if (!proposal) {
    return (
      <section className="rounded-md border border-line bg-panel p-4">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Check className="h-4 w-4 text-accent" />
          Proposal review
        </div>
        <div className="mt-4 rounded-md border border-dashed border-line bg-surface p-4 text-sm text-muted">No active proposal.</div>
      </section>
    );
  }
  const warnings = proposal.validationResult?.warnings ?? [];
  const errors = proposal.validationResult?.errors ?? [];
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Proposal review</div>
          <div className="mt-1 text-xs text-muted">{proposal.action.replace(/_/g, " ")}</div>
        </div>
        <span className={`rounded-md border px-2 py-1 text-xs ${statusClass(proposal.status)}`}>{proposal.status.replace(/_/g, " ")}</span>
      </div>

      <div className="mt-4 space-y-4 text-sm">
        <KeyValueList title="Current values" values={proposal.currentValues} empty="No existing record." />
        <KeyValueList title="Proposed values" values={proposal.proposedValues} empty="No proposed values." />
        {warnings.length ? <Notice tone="warning" items={warnings} /> : null}
        {errors.length ? <Notice tone="danger" items={errors} /> : null}
        {proposal.expiresAt ? <div className="text-xs text-muted">Expires {new Date(proposal.expiresAt).toLocaleString()}</div> : null}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-surface text-sm font-medium disabled:opacity-55" onClick={onCancel} disabled={!canAct || cancelBusy}>
          {cancelBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
          Cancel
        </button>
        <button className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-accent text-sm font-medium text-surface disabled:opacity-55" onClick={onConfirm} disabled={!canAct || confirmBusy}>
          {confirmBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Confirm
        </button>
      </div>
    </section>
  );
}

function DataBlock({ data }: { data: AIResponse["data"] }) {
  if (!data) return null;
  if (Array.isArray(data)) {
    if (!data.length) return <div className="mt-3 text-xs text-muted">No rows.</div>;
    const keys = Array.from(new Set(data.flatMap((row) => Object.keys(row)))).slice(0, 6);
    return (
      <div className="mt-3 overflow-x-auto rounded-md border border-line">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-panel text-muted">
            <tr>
              {keys.map((key) => <th className="px-2 py-1.5 font-medium" key={key}>{formatKey(key)}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {data.slice(0, 8).map((row, index) => (
              <tr key={index}>
                {keys.map((key) => <td className="max-w-56 break-words px-2 py-1.5" key={key}>{formatValue(row[key])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return <KeyValueList title="Result" values={data} />;
}

function KeyValueList({ title, values, empty = "No values." }: { title: string; values: Record<string, unknown>; empty?: string }) {
  const entries = Object.entries(values ?? {});
  return (
    <div>
      <div className="mb-2 text-xs font-medium uppercase tracking-normal text-muted">{title}</div>
      {entries.length === 0 ? <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">{empty}</div> : null}
      {entries.length > 0 ? <div className="divide-y divide-line rounded-md border border-line bg-surface">
        {entries.map(([key, value]) => (
          <div key={key} className="grid gap-2 px-3 py-2 sm:grid-cols-[140px_minmax(0,1fr)]">
            <span className="text-xs text-muted">{formatKey(key)}</span>
            <span className="break-words text-sm">{formatValue(value)}</span>
          </div>
        ))}
      </div> : null}
    </div>
  );
}

function Notice({ tone, items }: { tone: "warning" | "danger"; items: string[] }) {
  const toneClass = tone === "warning" ? "border-warning text-warning" : "border-danger text-danger";
  return (
    <div className={`rounded-md border bg-surface p-3 text-sm ${toneClass}`}>
      <div className="mb-2 flex items-center gap-2 font-medium">
        <AlertTriangle className="h-4 w-4" />
        {tone === "warning" ? "Warnings" : "Errors"}
      </div>
      <ul className="list-disc space-y-1 pl-5">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function statusClass(status: string) {
  if (status === "executed") return "border-success text-success";
  if (status === "failed" || status === "expired") return "border-danger text-danger";
  if (status === "cancelled") return "border-muted text-muted";
  return "border-warning text-warning";
}

function formatKey(key: string) {
  return key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function uniqueId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
