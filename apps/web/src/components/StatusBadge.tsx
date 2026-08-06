import type { ReconciliationStatus } from "../types/domain";

const styles: Record<string, string> = {
  balanced: "bg-[oklch(94%_0.025_150)] text-[oklch(34%_0.09_150)]",
  active: "bg-[oklch(92%_0.03_230)] text-primary",
  over_disbursed: "bg-[oklch(94%_0.035_25)] text-danger",
  over_utilized: "bg-[oklch(94%_0.035_25)] text-danger",
  missing_sanction: "bg-[oklch(95%_0.045_80)] text-[oklch(42%_0.12_80)]",
  attention_required: "bg-[oklch(95%_0.045_80)] text-[oklch(42%_0.12_80)]",
};

export function StatusBadge({ value }: { value: string | ReconciliationStatus }) {
  return <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ${styles[value] ?? "bg-muted text-[oklch(38%_0.012_250)]"}`}>{label(value)}</span>;
}

function label(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char: string) => char.toUpperCase());
}
