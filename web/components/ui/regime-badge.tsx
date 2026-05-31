import { Badge } from "./badge";
import type { RegimeType } from "@/lib/api";

const REGIME_META: Record<RegimeType, { label: string; tone: "up" | "down" | "warning" | "neutral" }> = {
  bull: { label: "Bull", tone: "up" },
  bear: { label: "Bear", tone: "down" },
  sideways: { label: "Sideways", tone: "neutral" },
  high_volatility: { label: "High Volatility", tone: "warning" },
  crisis: { label: "Crisis", tone: "down" },
};

/** Maps a market regime to a tinted badge (terminal convention: up/down/warn). */
export function RegimeBadge({ regime }: { regime: RegimeType }) {
  const meta = REGIME_META[regime] ?? REGIME_META.sideways;
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}
