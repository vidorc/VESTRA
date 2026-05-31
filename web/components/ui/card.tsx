import { cn } from "@/lib/utils";

/** Elevated panel using DESIGN.md's stacked-shadow + hairline chrome (dark). */
export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-hairline bg-canvas-soft p-lg shadow-level-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Small mono caption/eyebrow — "mono is the voice of the platform". */
export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-caption uppercase tracking-wide text-mute">
      {children}
    </span>
  );
}

/** A labelled metric tile (value set in mono with tabular figures). */
export function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "up" | "down";
}) {
  return (
    <Card>
      <Eyebrow>{label}</Eyebrow>
      <div
        className={cn(
          "mt-xs font-mono text-display-sm tnum",
          tone === "up" && "text-up",
          tone === "down" && "text-down",
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-xxs text-caption text-mute">{hint}</div>}
    </Card>
  );
}
