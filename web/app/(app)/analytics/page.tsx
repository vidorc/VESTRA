"use client";

import { useQuery } from "@tanstack/react-query";
import { memory, reasoning, type ReasoningTrace } from "@/lib/api";
import { Card, Eyebrow, Stat } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import {
  BarSeriesChart,
  DonutChart,
  RadialGauge,
  TrendChart,
  actionColor,
  chartTokens,
} from "@/components/charts/primitives";

// Map each regime to a 1-5 "stress level" so it plots as a timeline; higher = more stressed.
const REGIME_LEVEL: Record<string, number> = {
  bull: 1,
  sideways: 2,
  bear: 3,
  high_volatility: 4,
  crisis: 5,
};
const REGIME_COLOR: Record<string, string> = {
  bull: chartTokens.up,
  sideways: chartTokens.mute,
  bear: chartTokens.warning,
  high_volatility: chartTokens.warning,
  crisis: chartTokens.down,
};

function shortTime(ts?: string): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function AnalyticsPage() {
  const tracesQ = useQuery({ queryKey: ["reasoning"], queryFn: () => reasoning.list(50) });
  const memoryQ = useQuery({ queryKey: ["memory"], queryFn: () => memory.get(200) });

  // Chronological (oldest-first) for time-axis charts.
  const traces: ReasoningTrace[] = [...(tracesQ.data?.traces ?? [])].reverse();

  const confidenceSeries = traces.map((t, i) => ({
    t: shortTime(t.ts) + ` ·${i + 1}`,
    confidence: t.confidence ? Math.round(t.confidence.overall * 100) : 0,
    decision: t.confidence ? Math.round(t.confidence.decision_confidence * 100) : 0,
    risk: t.confidence ? Math.round(t.confidence.risk_confidence * 100) : 0,
  }));

  const regimeSeries = traces
    .filter((t) => t.regime)
    .map((t, i) => ({
      t: shortTime(t.ts) + ` ·${i + 1}`,
      level: REGIME_LEVEL[t.regime!.regime] ?? 2,
      regime: t.regime!.regime,
    }));

  // Decision mix (final decisions the agent produced).
  const mixCounts = traces.reduce<Record<string, number>>((acc, t) => {
    const a = t.decision?.action ?? "HOLD";
    acc[a] = (acc[a] ?? 0) + 1;
    return acc;
  }, {});
  const decisionMix = Object.entries(mixCounts).map(([action, count]) => ({ action, count }));

  const analytics = memoryQ.data?.analytics;
  const byTicker = (analytics?.by_ticker ?? []).map((t) => ({
    ticker: t.ticker,
    completed: t.completed,
    losses: t.losses,
  }));

  return (
    <div className="px-xl py-lg">
      <PageHeader
        eyebrow="Executive analytics"
        title="Analytics."
        description="Decision history, agent confidence, market regime, and learning outcomes."
      />

      {/* Top-line stats */}
      <div className="grid grid-cols-2 gap-md lg:grid-cols-4">
        <Stat label="Decisions" value={String(traces.length)} />
        <Stat label="Trades Recorded" value={String(analytics?.total ?? 0)} />
        <Stat
          label="Win Rate"
          value={analytics ? `${Math.round(analytics.win_rate * 100)}%` : "—"}
          tone={analytics && analytics.win_rate >= 0.5 ? "up" : "default"}
        />
        <Stat
          label="Open Outcomes"
          value={String(analytics?.pending ?? 0)}
        />
      </div>

      {/* Confidence trend + memory win rate */}
      <div className="mt-lg grid grid-cols-1 gap-md lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <Eyebrow>Agent Confidence Trend</Eyebrow>
          {confidenceSeries.length > 0 ? (
            <TrendChart
              data={confidenceSeries}
              xKey="t"
              yDomain={[0, 100]}
              valueFormat={(v) => `${v}%`}
              series={[
                { key: "confidence", label: "Overall", color: chartTokens.link },
                { key: "decision", label: "Decision", color: chartTokens.cyan },
                { key: "risk", label: "Risk", color: chartTokens.violet },
              ]}
            />
          ) : (
            <p className="mt-sm text-body-sm text-mute">
              {tracesQ.isLoading ? "Loading…" : "No decisions yet."}
            </p>
          )}
        </Card>

        <Card className="flex flex-col items-center justify-center">
          <Eyebrow>Win Rate</Eyebrow>
          {analytics && analytics.completed + analytics.losses > 0 ? (
            <RadialGauge
              value={analytics.win_rate * 100}
              color={analytics.win_rate >= 0.5 ? chartTokens.up : chartTokens.down}
              label="wins"
            />
          ) : (
            <p className="mt-sm text-body-sm text-mute">No decided trades yet.</p>
          )}
          {analytics && (
            <div className="mt-xs flex gap-md font-mono text-caption text-mute">
              <span className="text-up">{analytics.completed} won</span>
              <span className="text-down">{analytics.losses} lost</span>
            </div>
          )}
        </Card>
      </div>

      {/* Regime timeline + decision mix */}
      <div className="mt-lg grid grid-cols-1 gap-md lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <Eyebrow>Market Regime Timeline</Eyebrow>
          {regimeSeries.length > 0 ? (
            <>
              <TrendChart
                data={regimeSeries}
                xKey="t"
                yDomain={[0, 5]}
                series={[{ key: "level", label: "Stress", color: chartTokens.warning }]}
                valueFormat={(v) => ["calm", "bull", "sideways", "bear", "volatile", "crisis"][Number(v)] ?? `${v}`}
              />
              <div className="mt-sm flex flex-wrap gap-xxs">
                {regimeSeries.slice(-12).map((r, i) => (
                  <span
                    key={i}
                    className="rounded-full px-xs py-[2px] font-mono text-caption"
                    style={{ backgroundColor: `${REGIME_COLOR[r.regime] ?? chartTokens.mute}26`, color: REGIME_COLOR[r.regime] ?? chartTokens.mute }}
                  >
                    {r.regime}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <p className="mt-sm text-body-sm text-mute">
              {tracesQ.isLoading ? "Loading…" : "No regime history yet."}
            </p>
          )}
        </Card>

        <Card>
          <Eyebrow>Decision Mix</Eyebrow>
          {decisionMix.length > 0 ? (
            <>
              <DonutChart
                data={decisionMix}
                nameKey="action"
                valueKey="count"
                colorFor={(d) => actionColor(String(d.action))}
              />
              <div className="mt-sm flex justify-center gap-md">
                {decisionMix.map((d) => (
                  <div key={d.action} className="flex items-center gap-xs">
                    <Badge tone={d.action === "BUY" ? "up" : d.action === "SELL" ? "down" : "neutral"}>
                      {d.action}
                    </Badge>
                    <span className="font-mono text-caption tnum text-ink">{d.count}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="mt-sm text-body-sm text-mute">No decisions yet.</p>
          )}
        </Card>
      </div>

      {/* Memory analytics: per-ticker outcomes */}
      <Card className="mt-lg">
        <Eyebrow>Outcomes by Ticker</Eyebrow>
        {byTicker.length > 0 ? (
          <BarSeriesChart
            data={byTicker}
            categoryKey="ticker"
            valueKey="completed"
            layout="vertical"
            height={Math.max(160, byTicker.length * 36)}
            colorFor={(d) => (Number(d.losses) > Number(d.completed) ? chartTokens.down : chartTokens.up)}
            valueFormat={(v) => `${v} completed`}
          />
        ) : (
          <p className="mt-sm text-body-sm text-mute">
            {memoryQ.isLoading ? "Loading…" : "No trade outcomes recorded yet — they accrue as the agent executes."}
          </p>
        )}
      </Card>
    </div>
  );
}
