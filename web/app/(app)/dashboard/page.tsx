"use client";

import { useQuery } from "@tanstack/react-query";
import { portfolio } from "@/lib/api";
import { inr } from "@/lib/utils";
import { Card, Eyebrow, Stat } from "@/components/ui/card";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["portfolio"],
    queryFn: portfolio.get,
  });

  return (
    <div className="px-xl py-lg">
      <div className="mb-lg">
        <Eyebrow>Overview</Eyebrow>
        <h1 className="mt-xxs text-display-lg text-ink">Dashboard.</h1>
      </div>

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
          <div className="grid grid-cols-1 gap-md sm:grid-cols-2 lg:grid-cols-4">
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
            <Stat
              label="Risk Tolerance"
              value={data.profile.risk_tolerance}
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
