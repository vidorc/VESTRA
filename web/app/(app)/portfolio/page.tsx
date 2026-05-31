"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { health, portfolio, rebalance, type RebalancePlan } from "@/lib/api";
import { inr } from "@/lib/utils";
import { Card, Eyebrow } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { HealthGauge } from "@/components/ui/health-gauge";

function factorTone(score: number): "up" | "warning" | "down" {
  if (score >= 70) return "up";
  if (score >= 45) return "warning";
  return "down";
}

export default function PortfolioPage() {
  const portfolioQ = useQuery({ queryKey: ["portfolio"], queryFn: portfolio.get });
  const healthQ = useQuery({ queryKey: ["health"], queryFn: health.get });
  const rebalanceM = useMutation<RebalancePlan>({
    mutationFn: () => rebalance.preview(5),
  });

  return (
    <div className="px-xl py-lg">
      <div className="mb-lg">
        <Eyebrow>Positions & health</Eyebrow>
        <h1 className="mt-xxs text-display-lg text-ink">Portfolio.</h1>
      </div>

      {/* Health + factors */}
      <div className="grid grid-cols-1 gap-md lg:grid-cols-3">
        <Card className="flex items-center justify-center">
          {healthQ.data ? (
            <HealthGauge value={healthQ.data.score} band={healthQ.data.band} />
          ) : (
            <p className="text-body-sm text-mute">{healthQ.isLoading ? "Loading…" : "No health data."}</p>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <Eyebrow>Health Factors</Eyebrow>
          <div className="mt-sm space-y-sm">
            {healthQ.data?.factors.map((f) => (
              <div key={f.name}>
                <div className="flex items-center justify-between">
                  <span className="text-body-sm capitalize text-body">
                    {f.name.replace("_", " ")}
                    <span className="ml-xs font-mono text-caption text-mute">
                      ×{f.weight}
                    </span>
                  </span>
                  <span className="font-mono text-body-sm tnum text-ink">{f.score}</span>
                </div>
                <Progress value={f.score} tone={factorTone(f.score)} className="mt-xxs" />
                <p className="mt-xxs text-caption text-mute">{f.note}</p>
              </div>
            ))}
            {!healthQ.data && <p className="text-body-sm text-mute">—</p>}
          </div>
        </Card>
      </div>

      {/* Holdings + sectors */}
      <div className="mt-lg grid grid-cols-1 gap-md lg:grid-cols-2">
        <Card>
          <Eyebrow>Holdings</Eyebrow>
          <table className="mt-sm w-full">
            <thead>
              <tr className="border-b border-hairline text-left">
                <th className="pb-xs font-mono text-caption uppercase text-mute">Ticker</th>
                <th className="pb-xs text-right font-mono text-caption uppercase text-mute">Qty</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(portfolioQ.data?.profile.holdings ?? {}).map(([t, q]) => (
                <tr key={t} className="border-b border-hairline/50">
                  <td className="py-xs font-mono text-body-sm text-ink">{t}</td>
                  <td className="py-xs text-right font-mono text-body-sm tnum text-body">{q}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-sm flex items-center justify-between">
            <span className="text-caption text-mute">Cash</span>
            <span className="font-mono text-body-sm tnum text-ink">
              {inr(portfolioQ.data?.exposure.cash_balance)}
            </span>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <Eyebrow>Sector Breakdown</Eyebrow>
            {portfolioQ.data && (
              <Badge tone={portfolioQ.data.exposure.concentration_risk === "high" ? "down" : "neutral"}>
                {portfolioQ.data.exposure.concentration_risk} concentration
              </Badge>
            )}
          </div>
          <div className="mt-sm space-y-xs">
            {Object.entries(portfolioQ.data?.exposure.sector_breakdown ?? {}).map(([s, n]) => (
              <div key={s} className="flex items-center justify-between">
                <span className="text-body-sm capitalize text-body">{s}</span>
                <span className="font-mono text-body-sm tnum text-ink">{n}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Rebalance */}
      <Card className="mt-lg">
        <div className="flex items-center justify-between">
          <Eyebrow>Rebalance</Eyebrow>
          <Button
            variant="secondary"
            disabled={rebalanceM.isPending}
            onClick={() => rebalanceM.mutate()}
          >
            {rebalanceM.isPending ? "Computing…" : "Preview plan"}
          </Button>
        </div>

        {rebalanceM.data && (
          <div className="mt-sm">
            {rebalanceM.data.drift_detected ? (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-hairline text-left">
                    <th className="pb-xs font-mono text-caption uppercase text-mute">Action</th>
                    <th className="pb-xs font-mono text-caption uppercase text-mute">Ticker</th>
                    <th className="pb-xs text-right font-mono text-caption uppercase text-mute">Qty</th>
                    <th className="pb-xs font-mono text-caption uppercase text-mute">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {rebalanceM.data.actions.map((a, i) => (
                    <tr key={i} className="border-b border-hairline/50">
                      <td className="py-xs">
                        <Badge tone={a.action === "BUY" ? "up" : "down"}>{a.action}</Badge>
                      </td>
                      <td className="py-xs font-mono text-body-sm text-ink">{a.ticker}</td>
                      <td className="py-xs text-right font-mono text-body-sm tnum text-body">{a.quantity}</td>
                      <td className="py-xs text-caption text-mute">{a.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-body-sm text-up">{rebalanceM.data.notes}</p>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
