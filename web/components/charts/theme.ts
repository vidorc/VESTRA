/**
 * Chart theme — the single source of truth that maps Recharts (which needs raw
 * hex values, not Tailwind classes) onto the DESIGN.md dark-terminal tokens.
 *
 * These hexes mirror tailwind.config.ts exactly. Keep them in sync: charts must
 * read as part of the same system as the rest of the terminal, not a bolt-on.
 */

export const chartTokens = {
  canvas: "#0a0a0a",
  panel: "#1a1a1a",
  hairline: "#262626",
  hairlineStrong: "#404040",
  ink: "#ededed",
  body: "#a1a1a1",
  mute: "#6b6b6b",
  up: "#0ac27e",
  down: "#ff4d4d",
  warning: "#f5a623",
  link: "#0070f3",
  violet: "#7928ca",
  cyan: "#50e3c2",
  pink: "#ff0080",
} as const;

/**
 * Categorical series palette, drawn from DESIGN.md's gradient/semantic accents.
 * Ordered for maximum adjacent contrast on the dark canvas.
 */
export const seriesPalette = [
  chartTokens.link,
  chartTokens.cyan,
  chartTokens.violet,
  chartTokens.warning,
  chartTokens.pink,
  chartTokens.up,
] as const;

export function seriesColor(i: number): string {
  return seriesPalette[i % seriesPalette.length];
}

/** Map a financial action to its terminal-convention tone. */
export function actionColor(action?: string): string {
  if (action === "BUY") return chartTokens.up;
  if (action === "SELL") return chartTokens.down;
  return chartTokens.mute;
}

/** Shared axis tick styling — mono, muted, small (DESIGN.md "technical labels"). */
export const axisTick = {
  fill: chartTokens.mute,
  fontSize: 11,
  fontFamily: "var(--font-mono), ui-monospace, monospace",
} as const;

export const gridStroke = chartTokens.hairline;
