export function money(value: unknown): string {
  const amount = Number(value);
  if (value === null || value === undefined || value === "" || Number.isNaN(amount)) return "-";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}

export function moneyOrNotApplicable(value: unknown): string {
  const amount = Number(value);
  if (value === null || value === undefined || value === "" || Number.isNaN(amount)) return "Not applicable";
  return money(amount);
}

export function labelize(value: unknown): string {
  return String(value ?? "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function dateText(value: unknown): string {
  if (!value) return "-";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

export function safeText(value: unknown, fallback = "-"): string {
  const text = String(value ?? "").trim();
  return text || fallback;
}

export function toNumber(value: unknown): number {
  const amount = Number(value);
  return Number.isNaN(amount) ? 0 : amount;
}
