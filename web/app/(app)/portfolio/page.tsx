"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { health, portfolio, rebalance, risk, type RebalancePlan } from "@/lib/api";
import { inr } from "@/lib/utils";
import { Card, Eyebrow } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { HealthGauge } from "@/components/ui/health-gauge";
import { BarSeriesChart, DonutChart, chartTokens, seriesColor } from "@/components/charts/primitives";
import { Heatmap } from "@/components/charts/heatmap";

function factorTone(score: number): "up" | "warning" | "down" {
  if (score >= 70) return "up";
  if (score >= 45) return "warning";
  return "down";
}

function resilienceTone(r: string): "up" | "warning" | "down" {
  if (r === "robust") return "up";
  if (r === "moderate") return "warning";
  return "down";
}

const FACTOR_HEX = { up: chartTokens.up, warning: chartTokens.warning, down: chartTokens.down };

export default function PortfolioPage() {
  const portfolioQ = useQuery({ queryKey: ["portfolio"], queryFn: portfolio.get });
  const healthQ = useQuery({ queryKey: ["health"], queryFn: health.get });
  const stressQ = useQuery({ queryKey: ["risk-stress"], queryFn: risk.stress });
  const rebalanceM = useMutation<RebalancePlan>({
    mutationFn: () => rebalance.preview(5),
  });

  const sectors = Object.entries(portfolioQ.data?.exposure.sector_breakdown ?? {}).map(
    ([sector, count]) => ({ sector, count: Number(count) }),
  );
  const factorData =
    healthQ.data?.factors.map((f) => ({ name: f.name.replace(/_/g, " "), score: f.score })) ?? [];

  return (
    <div className="px-xl py-lg">
      <PageHeader eyebrow="Positions & health" title="Portfolio." />

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
          {factorData.length > 0 && (
            <BarSeriesChart
              data={factorData}
              categoryKey="name"
              valueKey="score"
              layout="vertical"
              height={Math.max(140, factorData.length * 40)}
              colorFor={(d) => FACTOR_HEX[factorTone(Number(d.score))]}
              valueFormat={(v) => `${v}`}
            />
          )}
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

      {/* Holdings + allocation */}
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
            <Eyebrow>Allocation by Sector</Eyebrow>
            {portfolioQ.data && (
              <Badge tone={portfolioQ.data.exposure.concentration_risk === "high" ? "down" : "neutral"}>
                {portfolioQ.data.exposure.concentration_risk} concentration
              </Badge>
            )}
          </div>
          {sectors.length > 0 ? (
            <>
              <DonutChart
                data={sectors}
                nameKey="sector"
                valueKey="count"
                valueFormat={(v) => `${v} positions`}
              />
              <div className="mt-sm grid grid-cols-2 gap-x-md gap-y-xxs">
                {sectors.map((s, i) => (
                  <div key={s.sector} className="flex items-center gap-xs">
                    <span className="h-2 w-2 rounded-full" style={{ background: seriesColor(i) }} />
                    <span className="text-caption capitalize text-body">{s.sector}</span>
                    <span className="ml-auto font-mono text-caption tnum text-mute">{s.count}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="mt-sm text-body-sm text-mute">No sector data.</p>
          )}
        </Card>
      </div>

      {/* Sector concentration heatmap */}
      {sectors.length > 0 && (
        <Card className="mt-lg">
          <Eyebrow>Sector Concentration</Eyebrow>
          <p className="mt-xxs text-caption text-mute">Darker cells carry heavier exposure.</p>
          <div className="mt-sm">
            <Heatmap
              cells={sectors.map((s) => ({ label: s.sector, value: s.count }))}
              tone={portfolioQ.data?.exposure.concentration_risk === "high" ? "down" : "warning"}
              valueFormat={(v) => `${v}`}
              columns={4}
            />
          </div>
        </Card>
      )}

      {/* Risk stress test: named macro shocks applied to the whole book */}
      <Card className="mt-lg">
        <div className="flex items-center justify-between">
          <Eyebrow>Risk Stress Test</Eyebrow>
          {stressQ.data && (
            <Badge tone={resilienceTone(stressQ.data.resilience)}>
              {stressQ.data.resilience}
            </Badge>
          )}
        </div>
        {stressQ.isLoading && <p className="mt-sm text-body-sm text-mute">Running shocks…</p>}
        {stressQ.data && stressQ.data.scenarios.length === 0 && (
          <p className="mt-sm text-body-sm text-mute">{stressQ.data.note}</p>
        )}
        {stressQ.data && stressQ.data.scenarios.length > 0 && (
          <>
            <p className="mt-xxs text-caption text-mute">
              How the book holds up under macro shocks · worst case −
              {stressQ.data.worst_case_loss_pct}% of {inr(stressQ.data.portfolio_value)}
            </p>
            <div className="mt-sm space-y-sm">
              {stressQ.data.scenarios.map((s) => (
                <div key={s.name}>
                  <div className="flex items-center justify-between">
                    <span className="text-body-sm text-body">{s.label}</span>
                    <span className="font-mono text-body-sm tnum text-down">
                      −{inr(s.loss)} <span className="text-mute">(−{s.loss_pct}%)</span>
                    </span>
                  </div>
                  <Progress
                    value={Math.min(100, s.loss_pct * 2)}
                    tone={s.loss_pct >= 25 ? "down" : s.loss_pct >= 12 ? "warning" : "up"}
                    className="mt-xxs"
                  />
                  <p className="mt-xxs text-caption text-mute">
                    {s.note}
                    {s.worst_sector && (
                      <span className="ml-xs capitalize">· hardest hit: {s.worst_sector}</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-sm border-t border-hairline pt-sm text-body-sm text-body">
              {stressQ.data.note}
            </p>
          </>
        )}
      </Card>

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
