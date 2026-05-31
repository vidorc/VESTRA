import { cn } from "@/lib/utils";

type Tone = "neutral" | "up" | "down" | "warning" | "info";

const TONES: Record<Tone, string> = {
  neutral: "bg-panel text-body border-hairline",
  up: "bg-up/15 text-up border-up/30",
  down: "bg-down/15 text-down border-down/30",
  warning: "bg-warning/15 text-warning border-warning/30",
  info: "bg-link/15 text-link border-link/30",
};

/** Small inline status pill. Mono for the technical-label voice (DESIGN.md). */
export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-xs py-[2px] font-mono text-caption uppercase tracking-wide",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
