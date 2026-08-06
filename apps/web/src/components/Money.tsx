export function Money({ value }: { value: string }) {
  const amount = Number(value);
  return <span className={amount < 0 ? "font-medium text-danger" : "tabular-nums"}>{formatMoney(value)}</span>;
}

export function formatMoney(value: string | number) {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}

