"use client";

/**
 * Sector heatmap — a grid of cells tinted by intensity. A heatmap reads better
 * as a CSS grid than a Recharts chart, so this is hand-built but uses the same
 * DESIGN.md tokens (up/down/warning) as the charting primitives.
 *
 * Each cell's fill opacity scales with its value relative to the max, so the
 * heaviest exposure reads darkest. Tone picks the hue (e.g. concentration =
 * warning, gains = up).
 */

import { chartTokens } from "./theme";

export interface HeatCell {
  label: string;
  value: number;
}

const TONE_HEX: Record<string, string> = {
  up: chartTokens.up,
  down: chartTokens.down,
  warning: chartTokens.warning,
  link: chartTokens.link,
};

export function Heatmap({
  cells,
  tone = "link",
  valueFormat,
  columns = 3,
}: {
  cells: HeatCell[];
  tone?: "up" | "down" | "warning" | "link";
  valueFormat?: (v: number) => string;
  columns?: number;
}) {
  if (cells.length === 0) {
    return <p className="text-body-sm text-mute">No data.</p>;
  }
  const max = Math.max(...cells.map((c) => c.value), 1);
  const hex = TONE_HEX[tone] ?? chartTokens.link;

  return (
    <div className="grid gap-xs" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
      {cells.map((c) => {
        // Floor the opacity so even small slices stay legible against canvas.
        const intensity = 0.12 + 0.78 * (c.value / max);
        return (
          <div
            key={c.label}
            className="flex flex-col gap-xxs rounded-md border border-hairline p-sm"
            style={{ backgroundColor: `${hex}${Math.round(intensity * 255).toString(16).padStart(2, "0")}` }}
          >
            <span className="truncate font-mono text-caption uppercase tracking-wide text-ink/90">
              {c.label}
            </span>
            <span className="font-mono text-body-sm tnum text-ink">
              {valueFormat ? valueFormat(c.value) : c.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}
