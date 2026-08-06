import { useQuery } from "@tanstack/react-query";
import { Bot, CheckCircle2, ShieldCheck, TriangleAlert } from "lucide-react";
import { api } from "../api/client";
import { Button } from "../components/Button";
import { ErrorState, PageHeader, PageSkeleton } from "./DashboardPage";

export function AIAssistantPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["ai-preview"], queryFn: api.aiPreview });
  if (isLoading) return <PageSkeleton title="AI Assistant" />;
  if (error || !data) return <ErrorState title="AI Assistant" />;
  return (
    <section className="max-w-5xl space-y-6">
      <PageHeader title="AI Assistant" description="Local model output is treated as a proposal. Financial writes still require validation and confirmation." />
      <div className="rounded-lg border border-border bg-[oklch(99%_0.004_250)] p-4">
        <label className="text-sm font-medium" htmlFor="request">Request</label>
        <textarea id="request" className="mt-2 min-h-28 w-full rounded-md border border-border bg-transparent p-3 text-sm outline-none focus:border-primary" defaultValue="Add a ₹50,000 tranche to TRAI-SYN-001" />
        <div className="mt-3 flex justify-end"><Button variant="primary"><Bot className="h-4 w-4" />Preview Action</Button></div>
      </div>
      <section className="rounded-lg border border-border bg-[oklch(99%_0.004_250)]">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="text-sm font-semibold">Action Preview</div>
          <span className="inline-flex items-center gap-1 rounded bg-[oklch(94%_0.025_150)] px-2 py-1 text-xs font-medium text-success"><ShieldCheck className="h-3 w-3" />Allowed</span>
        </div>
        <div className="grid gap-4 p-4 md:grid-cols-2">
          <Line label="Action" value={data.action} />
          <Line label="Target" value={data.target} />
          {Object.entries(data.proposedValues).map(([key, value]) => <Line key={key} label={key} value={value} />)}
        </div>
        {data.warnings.length ? <div className="mx-4 mb-4 rounded-md border border-warning bg-[oklch(98%_0.024_80)] p-3 text-sm text-[oklch(42%_0.12_80)]"><TriangleAlert className="mr-2 inline h-4 w-4" />{data.warnings.join(" ")}</div> : null}
        <div className="flex justify-end gap-2 border-t border-border p-4">
          <Button>Cancel</Button>
          <Button variant="primary"><CheckCircle2 className="h-4 w-4" />Confirm Through Domain Service</Button>
        </div>
      </section>
    </section>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs uppercase text-[oklch(45%_0.014_250)]">{label}</div><div className="mt-1 text-sm font-medium">{value}</div></div>;
}

