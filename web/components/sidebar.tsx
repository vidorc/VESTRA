"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  Brain,
  PlayCircle,
  ScrollText,
  PieChart,
  LogOut,
  Settings,
  BarChart3,
  History,
  Gauge,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clearToken } from "@/lib/auth";

// Sidebar nav, grouped into labelled sections for terminal-style density.
// `ready` marks screens wired to live backend data.
const SECTIONS = [
  {
    label: "Overview",
    items: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, ready: true }],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/market", label: "Market Intelligence", icon: Activity, ready: true },
      { href: "/reasoning", label: "Agent Reasoning", icon: Brain, ready: true },
      { href: "/analytics", label: "Analytics", icon: BarChart3, ready: true },
      { href: "/review", label: "Decision Review", icon: History, ready: true },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/execution", label: "Execution", icon: PlayCircle, ready: true },
      { href: "/portfolio", label: "Portfolio", icon: PieChart, ready: true },
      { href: "/audit", label: "Audit", icon: ScrollText, ready: true },
      { href: "/observability", label: "Observability", icon: Gauge, ready: true },
    ],
  },
  {
    label: "Account",
    items: [{ href: "/settings", label: "Settings", icon: Settings, ready: true }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-hairline bg-canvas-soft">
      {/* Brand */}
      <div className="flex h-16 items-center gap-xs border-b border-hairline px-lg">
        <span className="grid h-6 w-6 place-items-center rounded-sm bg-ink font-mono text-caption font-semibold text-canvas">
          V
        </span>
        <span className="font-mono text-display-sm font-semibold tracking-tight text-ink">
          vestra
        </span>
        <span className="ml-auto rounded-pill border border-hairline bg-panel px-xs py-[2px] font-mono text-[10px] uppercase tracking-wide text-mute">
          v0.2
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-sm py-md">
        {SECTIONS.map((section) => (
          <div key={section.label} className="mb-md">
            <p className="px-sm pb-xxs font-mono text-[10px] uppercase tracking-[0.12em] text-mute">
              {section.label}
            </p>
            <div className="space-y-[2px]">
              {section.items.map(({ href, label, icon: Icon, ready }) => {
                const active = pathname === href || pathname.startsWith(href + "/");
                return (
                  <Link
                    key={href}
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group relative flex items-center gap-sm rounded-sm py-xs pl-sm pr-sm text-body-sm transition-all duration-150",
                      active
                        ? "bg-panel text-ink"
                        : "text-body hover:bg-panel/50 hover:text-ink",
                    )}
                  >
                    {/* Left-edge active indicator (DESIGN.md app-shell-row). */}
                    <span
                      className={cn(
                        "absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-ink transition-all duration-150",
                        active ? "opacity-100" : "opacity-0 group-hover:opacity-30",
                      )}
                    />
                    <Icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        active ? "text-ink" : "text-mute group-hover:text-body",
                      )}
                    />
                    <span className="flex-1">{label}</span>
                    {!ready && (
                      <span className="font-mono text-[10px] uppercase text-mute">soon</span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Sign out */}
      <div className="border-t border-hairline p-sm">
        <button
          onClick={logout}
          className="flex w-full items-center gap-sm rounded-sm px-sm py-xs text-body-sm text-body transition-colors hover:bg-panel/60 hover:text-down"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
