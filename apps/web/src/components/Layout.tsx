import { ClipboardList, FileDown, Gauge, Landmark, ListChecks, Search, Settings, WalletCards } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../app/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/projects", label: "Projects", icon: ClipboardList },
  { to: "/tranches/new", label: "Tranches", icon: WalletCards },
  { to: "/reconciliation", label: "Reconciliation", icon: ListChecks },
  { to: "/imports-exports", label: "Imports and Exports", icon: FileDown },
  { to: "/settings", label: "Settings", icon: Settings }
];

export function Layout({ children }: { children: ReactNode }) {
  const auth = useAuth();
  return (
    <div className="min-h-screen bg-surface text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-panel px-3 py-4 md:block">
        <div className="mb-6 flex items-center gap-2 px-2 text-base font-semibold">
          <Landmark className="h-5 w-5 text-accent" />
          TrancheAI
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.label}
              to={item.to}
              className={({ isActive }) =>
                `focus-ring flex items-center gap-2 rounded-md px-3 py-2 text-sm ${isActive ? "bg-surface text-ink" : "text-muted hover:bg-surface/70 hover:text-ink"}`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="md:pl-64">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-line bg-surface/95 px-4 backdrop-blur">
          <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-1.5 text-sm text-muted">
            <Search className="h-4 w-4" />
            <span>Search projects, tranches or payment references</span>
          </div>
          <button className="focus-ring rounded-md border border-line px-3 py-1.5 text-sm" onClick={auth.logout}>
            {auth.user?.fullName ?? "Logout"}
          </button>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </div>
    </div>
  );
}
