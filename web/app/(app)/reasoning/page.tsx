"use client";

import { useQuery } from "@tanstack/react-query";
import { reasoning, type ReasoningTrace, type Evidence } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

function actionTone(action?: string): "up" | "down" | "neutral" {
  if (action === "BUY") return "up";
  if (action === "SELL") return "down";
  return "neutral";
}

function severityTone(sev?: string): "up" | "warning" | "down" | "neutral" {
  if (sev === "critical" || sev === "high") return "down";
  if (sev === "medium") return "warning";
  return "neutral";
}

function verdictTone(v?: string): "up" | "warning" | "down" | "neutral" {
  if (v === "sound") return "up";
  if (v === "questionable") return "down";
  if (v === "acceptable") return "warning";
  return "neutral";
}

function stanceTone(s?: string): "up" | "down" | "neutral" {
  if (s === "supports") return "up";
  if (s === "cautions") return "down";
  return "neutral";
}

/** Trust layer: plain-English summary, the evidence behind the call, and the
 * "why not the other actions" counterfactuals. Leads the card because it's the
 * human-readable view; the technical pipeline below is the supporting detail. */
function TrustPanel({
  explanation,
}: {
  explanation: NonNullable<ReasoningTrace["explanation"]>;
}) {
  const supporting = explanation.evidence.filter((e) => e.stance === "supports");
  const cautioning = explanation.evidence.filter((e) => e.stance === "cautions");
  const ordered: Evidence[] = [
    ...supporting,
    ...cautioning,
    ...explanation.evidence.filter((e) => e.stance === "neutral"),
  ];

  return (
    <div className="mt-md rounded-md border border-hairline bg-canvas-soft p-md">
      <span className="font-mono text-caption uppercase tracking-wide text-mute">
        Why this call
      </span>
      <p className="mt-xxs max-w-prose text-body-sm text-ink">{explanation.summary}</p>

      {ordered.length > 0 && (
        <ul className="mt-sm space-y-xxs">
          {ordered.map((e, i) => (
            <li key={i} className="flex items-baseline gap-xs text-body-sm text-body">
              <Badge tone={stanceTone(e.stance)}>{e.source}</Badge>
              <span>{e.detail}</span>
            </li>
          ))}
        </ul>
      )}

      {explanation.why_not.length > 0 && (
        <div className="mt-sm border-t border-hairline pt-sm">
          {explanation.why_not.map((w) => (
            <div key={w.action} className="flex items-baseline gap-xs text-caption text-mute">
              <span className="font-mono uppercase tracking-wide">Why not {w.action}?</span>
              <span className="text-body">{w.reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** One labelled step in the reasoning pipeline. */
function Step({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-l border-hairline pl-sm">
      <span className="font-mono text-caption uppercase tracking-wide text-mute">{label}</span>
      <div className="mt-xxs text-body-sm text-body">{children}</div>
    </div>
  );
}

/** Did the CIO change the analyst's proposal (action or size)? */
function cioIntervention(trace: ReasoningTrace): { label: string; tone: "down" | "warning" } | null {
  const cio = trace.cio;
  const analyst = trace.analyst_decision;
  if (!cio || !analyst) return null;
  if (cio.vetoed) return { label: "CIO vetoed", tone: "down" };
  if (cio.overrode) return { label: "CIO overrode council", tone: "warning" };
  const final = cio.final_decision;
  if (final.action !== analyst.action) return { label: "CIO changed action", tone: "down" };
  if (final.quantity < analyst.quantity) return { label: "CIO downsized", tone: "warning" };
  return null;
}

function TraceCard({ trace }: { trace: ReasoningTrace }) {
  const d = trace.decision;
  const conf = trace.confidence;
  const ts = trace.ts ? new Date(trace.ts).toLocaleString() : null;
  const intervention = cioIntervention(trace);
  const analyst = trace.analyst_decision;

  return (
    <Card>
      {/* Governance banner: when the CIO altered the analyst's call, lead with it. */}
      {intervention && analyst && (
        <div className="-mx-lg -mt-lg mb-md flex items-center gap-xs rounded-t-lg border-b border-hairline bg-canvas-soft px-lg py-xs">
          <Badge tone={intervention.tone}>{intervention.label}</Badge>
          <span className="font-mono text-caption text-mute">
            analyst {analyst.action} {analyst.quantity || ""} → final {d?.action} {d?.quantity || ""}
          </span>
        </div>
      )}

      <div className="flex items-start justify-between gap-md">
        <div className="flex items-center gap-xs">
          {d ? (
            <>
              <Badge tone={actionTone(d.action)}>{d.action}</Badge>
              <span className="font-mono text-display-sm tnum text-ink">
                {d.quantity} {d.ticker}
              </span>
            </>
          ) : (
            <span className="text-body-sm text-mute">No decision recorded</span>
          )}
        </div>
        <div className="text-right">
          {conf && (
            <div className="font-mono text-display-sm tnum text-ink">
              {Math.round(conf.overall * 100)}%
              <span className="ml-xs text-caption uppercase text-mute">conf</span>
            </div>
          )}
          {ts && <p className="mt-xxs font-mono text-caption text-mute">{ts}</p>}
        </div>
      </div>

      {/* Trust layer leads: plain-English account of the decision + why-not. */}
      {trace.explanation && <TrustPanel explanation={trace.explanation} />}

      {/* The 7-stage pipeline, in graph order */}
      <div className="mt-md grid grid-cols-1 gap-sm md:grid-cols-2">
        {trace.signal && (
          <Step label="Signal">
            <span className="flex items-center gap-xs">
              <Badge tone={severityTone(trace.signal.severity)}>{trace.signal.severity}</Badge>
              <span>{trace.signal.event_type}</span>
            </span>
            {trace.signal.impacted_assets.length > 0 && (
              <p className="mt-xxs font-mono text-caption text-mute">
                {trace.signal.impacted_assets.join(", ")}
              </p>
            )}
          </Step>
        )}

        {trace.research && (
          <Step label="Research">
            <span className="capitalize">{trace.research.sentiment}</span>
            {trace.research.sector_impact && (
              <span className="text-mute"> · {trace.research.sector_impact}</span>
            )}
            <p className="mt-xxs font-mono text-caption text-mute">
              data {Math.round(trace.research.data_completeness * 100)}%
            </p>
          </Step>
        )}

        {trace.risk && (
          <Step label="Risk">
            <span className="capitalize">{trace.risk.concentration_risk} concentration</span>
            {trace.risk.liquidity_pressure && (
              <Badge
                tone={
                  trace.risk.liquidity_pressure === "high"
                    ? "down"
                    : trace.risk.liquidity_pressure === "medium"
                      ? "warning"
                      : "neutral"
                }
                className="ml-xs"
              >
                {trace.risk.liquidity_pressure} liquidity
              </Badge>
            )}
            <p className="mt-xxs font-mono text-caption text-mute">
              safe limit {trace.risk.safe_trade_limit}
            </p>
          </Step>
        )}

        {d && (
          <Step label="Strategy">
            <p className="max-w-prose">{d.reasoning}</p>
          </Step>
        )}

        {trace.reflection && (
          <Step label="Reflection">
            <Badge tone={verdictTone(trace.reflection.verdict)}>{trace.reflection.verdict}</Badge>
            {trace.reflection.better_alternative && (
              <p className="mt-xxs text-caption text-mute">
                alt: {trace.reflection.better_alternative}
              </p>
            )}
          </Step>
        )}

        {conf && (
          <Step label="Confidence">
            <Progress value={conf.overall * 100} tone="up" />
            <p className="mt-xxs font-mono text-caption text-mute">
              decision {Math.round(conf.decision_confidence * 100)}% · risk{" "}
              {Math.round(conf.risk_confidence * 100)}% · data{" "}
              {Math.round(conf.data_completeness * 100)}%
            </p>
          </Step>
        )}

        {trace.council && (
          <Step label="Council">
            <span className="flex items-center gap-xs">
              <Badge tone={actionTone(trace.council.consensus_action)}>
                {trace.council.consensus_action}
              </Badge>
              <span className="font-mono text-caption text-mute">
                {Math.round((1 - trace.council.dissent) * 100)}% agree
              </span>
            </span>
            <p className="mt-xxs text-caption text-mute">{trace.council.rationale}</p>
          </Step>
        )}

        {trace.cio && (
          <Step label="CIO (final)">
            <span className="flex items-center gap-xs">
              <Badge tone={actionTone(trace.cio.final_decision.action)}>
                {trace.cio.final_decision.action} {trace.cio.final_decision.quantity || ""}
              </Badge>
              {trace.cio.vetoed && <Badge tone="down">vetoed</Badge>}
              {trace.cio.overrode && <Badge tone="warning">overrode</Badge>}
            </span>
            <p className="mt-xxs text-caption text-mute">{trace.cio.rationale}</p>
          </Step>
        )}

        {trace.validation && (
          <Step label="Validation">
            <Badge tone={trace.validation.approved ? "up" : "down"}>
              {trace.validation.approved ? "passed" : "blocked"}
            </Badge>
            <p className="mt-xxs text-caption text-mute">{trace.validation.reason}</p>
          </Step>
        )}
      </div>
    </Card>
  );
}

export default function ReasoningPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["reasoning"],
    queryFn: () => reasoning.list(25),
  });
  const traces = data?.traces ?? [];

  return (
    <div className="px-xl py-lg">
      <PageHeader
        eyebrow="Decision trace"
        title="Agent Reasoning."
        description="The full chain behind each decision — a plain-English account of why, the evidence behind it, and why not the alternatives, over the signal-to-validation pipeline."
      />

      {isLoading && <p className="text-body-sm text-body">Loading reasoning traces…</p>}

      {error && (
        <Card className="border-down/40">
          <p className="text-body-sm text-down">Could not load reasoning traces.</p>
        </Card>
      )}

      {data && traces.length === 0 && (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-hairline-strong bg-canvas-soft">
          <p className="font-mono text-body-sm text-mute">
            No reasoning traces yet — they appear as the agent processes events.
          </p>
        </div>
      )}

      <div className="space-y-md">
        {traces.map((t, i) => (
          <TraceCard key={t._id ?? i} trace={t} />
        ))}
      </div>
    </div>
  );
}
