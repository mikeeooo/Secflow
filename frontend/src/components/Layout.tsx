import {
  Activity,
  BarChart3,
  FlaskConical,
  LayoutDashboard,
  ListFilter,
  Menu,
  Radio,
  Users,
  X,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router";
import { cx } from "./ui";

export const NAV = [
  { to: "/", label: "Overview", Icon: LayoutDashboard, end: true },
  { to: "/live", label: "Live Transfers", Icon: Radio },
  { to: "/transactions", label: "Transactions", Icon: ListFilter },
  { to: "/accounts", label: "Accounts", Icon: Users },
  { to: "/simulator", label: "Simulator", Icon: FlaskConical },
  { to: "/algorithms", label: "Algorithm Results", Icon: BarChart3 },
];

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <span aria-hidden className="grid size-8 place-items-center rounded-[9px] bg-accent-strong text-white">
        <Activity className="size-[18px]" strokeWidth={2.4} />
      </span>
      <span className="font-display text-[19px] font-bold tracking-[-0.02em]">SecFlow</span>
    </div>
  );
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="space-y-0.5">
      {NAV.map(({ to, label, Icon, end }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cx(
                "flex min-h-10 items-center gap-3 rounded-[10px] px-3 text-[15px] font-medium transition-colors",
                isActive ? "bg-accent-soft text-accent" : "text-label hover:bg-surface-2",
              )
            }
          >
            <Icon aria-hidden className="size-[18px]" strokeWidth={2} />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[248px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-separator bg-surface px-3 py-5 lg:flex">
        <div className="px-3 pb-6">
          <Wordmark />
        </div>
        <nav aria-label="Main">
          <NavItems />
        </nav>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-separator bg-surface/90 px-4 py-2.5 backdrop-blur-xl lg:hidden">
        <Wordmark />
        <button
          type="button"
          aria-label="Open navigation"
          aria-expanded={open}
          onClick={() => setOpen(true)}
          className="grid size-11 place-items-center rounded-[10px] hover:bg-surface-2"
        >
          <Menu aria-hidden className="size-6" />
        </button>
      </header>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <nav aria-label="Main" className="absolute inset-x-0 top-0 rounded-b-[18px] bg-surface px-3 pt-3 pb-5 shadow-xl">
            <div className="mb-3 flex items-center justify-between px-1">
              <Wordmark />
              <button ref={closeRef} type="button" aria-label="Close navigation" onClick={() => setOpen(false)} className="grid size-11 place-items-center rounded-[10px] hover:bg-surface-2">
                <X aria-hidden className="size-6" />
              </button>
            </div>
            <NavItems onNavigate={() => setOpen(false)} />
          </nav>
        </div>
      ) : null}

      <main id="main" className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
        <div className="mx-auto max-w-[1240px]">{children}</div>
      </main>
    </div>
  );
}
