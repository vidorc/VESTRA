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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clearToken } from "@/lib/auth";

// Sidebar nav. `ready` marks screens wired to live backend data.
const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, ready: true },
  { href: "/market", label: "Market Intelligence", icon: Activity, ready: true },
  { href: "/reasoning", label: "Agent Reasoning", icon: Brain, ready: true },
  { href: "/execution", label: "Execution", icon: PlayCircle, ready: true },
  { href: "/portfolio", label: "Portfolio", icon: PieChart, ready: true },
  { href: "/audit", label: "Audit", icon: ScrollText, ready: true },
  { href: "/settings", label: "Settings", icon: Settings, ready: true },
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
