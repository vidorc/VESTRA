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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clearToken } from "@/lib/auth";

// The six screens from the product brief. Only Dashboard is live in Phase 0;
// the rest are routed placeholders that later phases fill in.
const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, ready: true },
  { href: "/market", label: "Market Intelligence", icon: Activity, ready: false },
  { href: "/reasoning", label: "Agent Reasoning", icon: Brain, ready: false },
  { href: "/execution", label: "Execution", icon: PlayCircle, ready: false },
  { href: "/audit", label: "Audit", icon: ScrollText, ready: true },
  { href: "/portfolio", label: "Portfolio", icon: PieChart, ready: false },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-hairline bg-canvas-soft">
      <div className="flex h-16 items-center gap-xs px-lg">
        <span className="font-mono text-display-sm font-semibold tracking-tight text-ink">
          vestra
        </span>
        <span className="rounded-pill bg-panel px-xs py-[2px] font-mono text-caption text-mute">
          v0.2
        </span>
      </div>

      <nav className="flex-1 space-y-[2px] px-sm">
        {NAV.map(({ href, label, icon: Icon, ready }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group flex items-center gap-sm rounded-sm px-sm py-xs text-body-sm transition-colors",
                active
                  ? "bg-panel text-ink"
                  : "text-body hover:bg-panel/60 hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{label}</span>
              {!ready && (
                <span className="font-mono text-[10px] uppercase text-mute">soon</span>
              )}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={logout}
        className="m-sm flex items-center gap-sm rounded-sm px-sm py-xs text-body-sm text-body transition-colors hover:bg-panel/60 hover:text-ink"
      >
        <LogOut className="h-4 w-4" />
        Sign out
      </button>
    </aside>
  );
}
