import { cn } from "@/lib/utils";

const BAND_TONE: Record<string, { stroke: string; text: string }> = {
  excellent: { stroke: "stroke-up", text: "text-up" },
  good: { stroke: "stroke-up", text: "text-up" },
  fair: { stroke: "stroke-warning", text: "text-warning" },
  poor: { stroke: "stroke-down", text: "text-down" },
};

/**
 * A 0-100 health ring (SVG arc). The arc fills proportionally to `value` and is
 * tinted by `band`. The number is set in the mono face with tabular figures,
 * matching DESIGN.md's "mono for technical labels" rule. The label/value are
 * absolutely centered over the ring.
 */
export function HealthGauge({
  value,
  band,
  size = 140,
  label = "Health",
}: {
  value: number;
  band: string;
  size?: number;
  label?: string;
}) {
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const offset = c - (pct / 100) * c;
  const tone = BAND_TONE[band] ?? BAND_TONE.fair;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          className="stroke-panel"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className={cn("transition-all duration-700", tone.stroke)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("font-mono text-display-md tnum", tone.text)}>{Math.round(pct)}</span>
        <span className="font-mono text-caption uppercase tracking-wide text-mute">{label}</span>
      </div>
    </div>
  );
}
