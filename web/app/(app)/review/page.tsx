"use client";

import { useQuery } from "@tanstack/react-query";
import { review, type DecisionReviewEntry, type TimelineEvent } from "@/lib/api";
import { Card, Eyebrow, Stat } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

function statusTone(s: TimelineEvent["status"]): "up" | "down" | "warning" | "neutral" {
  if (s === "worked") return "up";
  if (s === "failed") return "down";
  if (s === "pending") return "warning";
  return "neutral";
}

function actionTone(action: string): "up" | "down" | "neutral" {
  if (action === "BUY") return "up";
  if (action === "SELL") return "down";
  return "neutral";
}

function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

/** One ticker's track record: tallies + a win-rate bar + plain-English note. */
function TickerRow({ entry }: { entry: DecisionReviewEntry }) {
  const decided = entry.worked + entry.failed;
  return (
    <div className="border-l border-hairline py-xs pl-sm">
      <div className="flex items-center justify-between gap-md">
        <span className="font-mono text-body-sm-strong text-ink">{entry.ticker}</span>
        <span className="flex items-center gap-xs font-mono text-caption text-mute">
          {entry.worked > 0 && <Badge tone="up">{entry.worked}W</Badge>}
          {entry.failed > 0 && <Badge tone="down">{entry.failed}L</Badge>}
          {entry.pending > 0 && <Badge tone="warning">{entry.pending}P</Badge>}
        </span>
      </div>
      {decided > 0 && (
        <Progress value={entry.win_rate * 100} tone={entry.win_rate >= 0.5 ? "up" : "down"} className="mt-xxs" />
      )}
      <p className="mt-xxs text-caption text-mute">{entry.note}</p>
    </div>
  );
}

/** The investor timeline — oldest-first, reads as a story. */
function TimelineRow({ event }: { event: TimelineEvent }) {
  const date = event.ts
    ? new Date(event.ts).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
    : "—";
  return (
    <div className="flex items-baseline gap-sm border-l border-hairline py-xs pl-sm">
      <span className="w-24 shrink-0 font-mono text-caption text-mute">{date}</span>
      <Badge tone={actionTone(event.action)}>{event.action}</Badge>
      <span className="flex-1 text-body-sm text-body">{event.description}</span>
      <Badge tone={statusTone(event.status)}>{event.status}</Badge>
    </div>
  );
}

export default function ReviewPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["review"],
    queryFn: () => review.get(200),
  });

  const decided = (data?.completed ?? 0) + (data?.losses ?? 0);

  return (
    <div className="px-xl py-lg">
      <PageHeader
        eyebrow="Learning loop"
        title="Decision Review."
        description="What worked, what failed, and why — a periodic look back over every decision the agent made, with the full investor timeline."
      />

      {isLoading && <p className="text-body-sm text-body">Loading review…</p>}

      {error && (
        <Card className="border-down/40">
          <p className="text-body-sm text-down">Could not load the decision review.</p>
        </Card>
      )}

      {data && data.total === 0 && (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-hairline-strong bg-canvas-soft">
          <p className="font-mono text-body-sm text-mute">
            No decisions to review yet — they accumulate as the agent acts on events.
          </p>
        </div>
      )}

      {data && data.total > 0 && (
        <>
          {/* Top-line tallies */}
          <div className="grid grid-cols-2 gap-md lg:grid-cols-4">
            <Stat label="Decisions" value={String(data.total)} />
            <Stat
              label="Win Rate"
              value={decided ? pct(data.win_rate) : "—"}
              hint={`${decided} decided`}
              tone={data.win_rate >= 0.5 ? "up" : data.win_rate > 0 ? "down" : "default"}
            />
            <Stat label="Worked" value={String(data.completed)} tone="up" />
            <Stat label="Failed" value={String(data.losses)} tone={data.losses > 0 ? "down" : "default"} />
          </div>

          {/* Highlights */}
          {data.highlights.length > 0 && (
            <Card className="mt-lg">
              <Eyebrow>Highlights</Eyebrow>
              <ul className="mt-xs space-y-xxs">
                {data.highlights.map((h, i) => (
                  <li key={i} className="text-body-sm text-body">
                    {h}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <div className="mt-lg grid grid-cols-1 gap-md lg:grid-cols-2">
            {/* Per-ticker attribution */}
            <Card>
              <Eyebrow>By Ticker</Eyebrow>
              <div className="mt-sm space-y-sm">
                {data.by_ticker.map((e) => (
                  <TickerRow key={e.ticker} entry={e} />
                ))}
              </div>
            </Card>

            {/* Investor timeline */}
            <Card>
              <Eyebrow>Investor Timeline</Eyebrow>
              <div className="mt-sm space-y-xxs">
                {data.timeline.map((e, i) => (
                  <TimelineRow key={`${e.ts}-${i}`} event={e} />
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
