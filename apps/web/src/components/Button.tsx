import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, PropsWithChildren } from "react";

type Variant = "primary" | "secondary" | "danger";

export function Button({ children, className = "", disabled, variant = "secondary", loading = false, ...props }: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }>) {
  const variants: Record<Variant, string> = {
    primary: "border-primary bg-primary text-[oklch(98%_0.006_250)] hover:bg-[oklch(43%_0.12_230)]",
    secondary: "border-border bg-[oklch(99%_0.004_250)] hover:bg-muted",
    danger: "border-danger bg-danger text-[oklch(98%_0.006_250)] hover:bg-[oklch(48%_0.16_25)]",
  };
  return (
    <button
      className={`focus-ring inline-flex h-9 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
      {children}
    </button>
  );
}

