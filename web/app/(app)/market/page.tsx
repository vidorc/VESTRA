"use client";

import { useQuery } from "@tanstack/react-query";
import { market, simulations } from "@/lib/api";
import { Card, Eyebrow } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RegimeBadge } from "@/components/ui/regime-badge";

export default function MarketPage() {
  const regimeQ = useQuery({ queryKey: ["regime"], queryFn: market.regime });
  const simsQ = useQuery({ queryKey: ["simulations"], queryFn: () => simulations.list(10) });
  const sims = simsQ.data?.simulations ?? [];

  return (
    <div className="px-xl py-lg">
      <div className="mb-lg">
        <Eyebrow>Conditions & analysis</Eyebrow>
        <h1 className="mt-xxs text-display-lg text-ink">Market Intelligence.</h1>
      </div>

      <div className="grid grid-cols-1 gap-md lg:grid-cols-3">
        <Card>
          <Eyebrow>Market Regime</Eyebrow>
          {regimeQ.data ? (
            <div className="mt-sm">
              <RegimeBadge regime={regimeQ.data.regime} />
              <p className="mt-sm text-body-sm text-body">{regimeQ.data.rationale}</p>
              <p className="mt-xs font-mono text-caption text-mute">
                confidence {Math.round(regimeQ.data.confidence * 100)}%
              </p>
            </div>
          ) : (
            <p className="mt-sm text-body-sm text-mute">
              {regimeQ.isLoading ? "Loading…" : "No regime data."}
            </p>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <Eyebrow>Recent Simulations</Eyebrow>
          {sims.length === 0 ? (
            <p className="mt-sm text-body-sm text-mute">
              {simsQ.isLoading ? "Loading…" : "No simulations yet — they appear as the agent processes events."}
            </p>
          ) : (
            <table className="mt-sm w-full">
              <thead>
                <tr className="border-b border-hairline text-left">
                  <th className="pb-xs font-mono text-caption uppercase text-mute">Expected</th>
                  <th className="pb-xs font-mono text-caption uppercase text-mute">Drawdown</th>
                  <th className="pb-xs font-mono text-caption uppercase text-mute">Upside</th>
                  <th className="pb-xs text-right font-mono text-caption uppercase text-mute">Risk</th>
                </tr>
              </thead>
              <tbody>
                {sims.map((s, i) => (
                  <tr key={s._id ?? i} className="border-b border-hairline/50">
                    <td className="py-xs font-mono text-body-sm tnum text-ink">{s.expected_return_pct}%</td>
                    <td className="py-xs font-mono text-body-sm tnum text-down">{s.expected_drawdown_pct}%</td>
                    <td className="py-xs font-mono text-body-sm tnum text-up">{s.upside_pct}%</td>
                    <td className="py-xs text-right">
                      <Badge tone={s.risk_score >= 0.6 ? "down" : s.risk_score >= 0.3 ? "warning" : "up"}>
                        {Math.round(s.risk_score * 100)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
