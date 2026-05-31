import { cn } from "@/lib/utils";

/** A thin labelled progress bar (0-100). Used for goal funding + health factors. */
export function Progress({
  value,
  tone = "ink",
  className,
}: {
  value: number;
  tone?: "ink" | "up" | "down" | "warning";
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const fill = {
    ink: "bg-ink",
    up: "bg-up",
    down: "bg-down",
    warning: "bg-warning",
  }[tone];
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-panel", className)}>
      <div className={cn("h-full rounded-full transition-all", fill)} style={{ width: `${pct}%` }} />
    </div>
  );
}
