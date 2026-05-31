"use client";

import { useQuery } from "@tanstack/react-query";
import { portfolio, health, market } from "@/lib/api";
import { inr } from "@/lib/utils";
import { Card, Eyebrow, Stat } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { HealthGauge } from "@/components/ui/health-gauge";
import { RegimeBadge } from "@/components/ui/regime-badge";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["portfolio"],
    queryFn: portfolio.get,
  });
  const healthQ = useQuery({ queryKey: ["health"], queryFn: health.get });
  const regimeQ = useQuery({ queryKey: ["regime"], queryFn: market.regime });

  return (
    <div className="px-xl py-lg">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard."
        actions={
          <>
            {regimeQ.data && (
              <div className="flex items-center gap-xs">
                <span className="font-mono text-caption uppercase tracking-wide text-mute">
                  Market regime
                </span>
                <RegimeBadge regime={regimeQ.data.regime} />
              </div>
            )}
            <span className="flex items-center gap-xs font-mono text-caption text-mute">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-up" />
              live
            </span>
          </>
        }
      />

      {isLoading && <p className="text-body text-body-sm">Loading portfolio…</p>}

      {error && (
        <Card className="border-error/40">
          <p className="text-body-sm text-down">
            Could not load portfolio. Is the API running and seeded?
          </p>
        </Card>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-md lg:grid-cols-4">
            <Card className="flex items-center justify-center lg:row-span-1">
              {healthQ.data ? (
                <HealthGauge value={healthQ.data.score} band={healthQ.data.band} size={120} />
              ) : (
                <p className="text-caption text-mute">Health —</p>
              )}
            </Card>
            <Stat label="Cash Balance" value={inr(data.exposure.cash_balance)} />
            <Stat
              label="Open Positions"
              value={String(data.exposure.total_positions)}
              hint="total shares held"
            />
            <Stat
              label="Concentration"
              value={data.exposure.concentration_risk}
              tone={data.exposure.concentration_risk === "high" ? "down" : "default"}
              hint={data.exposure.largest_sector ?? undefined}
            />
          </div>

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
                  {Object.entries(data.profile.holdings).map(([ticker, qty]) => (
                    <tr key={ticker} className="border-b border-hairline/50">
                      <td className="py-xs font-mono text-body-sm text-ink">{ticker}</td>
                      <td className="py-xs text-right font-mono text-body-sm tnum text-body">{qty}</td>
                    </tr>
                  ))}
                  {Object.keys(data.profile.holdings).length === 0 && (
                    <tr>
                      <td colSpan={2} className="py-sm text-body-sm text-mute">
                        No holdings yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>

            <Card>
              <Eyebrow>Sector Breakdown</Eyebrow>
              <div className="mt-sm space-y-xs">
                {Object.entries(data.exposure.sector_breakdown).map(([sector, n]) => (
                  <div key={sector} className="flex items-center justify-between">
                    <span className="text-body-sm capitalize text-body">{sector}</span>
                    <span className="font-mono text-body-sm tnum text-ink">{n}</span>
                  </div>
                ))}
                {Object.keys(data.exposure.sector_breakdown).length === 0 && (
                  <p className="text-body-sm text-mute">No exposure yet.</p>
                )}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
