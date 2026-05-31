"use client";

import { useQuery } from "@tanstack/react-query";
import { observability, type NodeStat } from "@/lib/api";
import { Card, Eyebrow, Stat } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

function latencyTone(ms: number): "up" | "warning" | "down" {
  if (ms < 50) return "up";
  if (ms < 250) return "warning";
  return "down";
}

/** One node's row: run count, error rate, latency bar, last status. */
function NodeRow({ node, maxAvg }: { node: NodeStat; maxAvg: number }) {
  const barPct = maxAvg > 0 ? (node.avg_ms / maxAvg) * 100 : 0;
  return (
    <div className="border-l border-hairline py-xs pl-sm">
      <div className="flex items-center justify-between gap-md">
        <span className="flex items-center gap-xs">
          <span className="font-mono text-body-sm-strong text-ink">{node.node}</span>
          <Badge tone={node.last_status === "error" ? "down" : "up"}>{node.last_status}</Badge>
        </span>
        <span className="font-mono text-caption tnum text-mute">
          {node.runs} run{node.runs === 1 ? "" : "s"}
          {node.errors > 0 && <span className="ml-xs text-down">· {node.errors} err</span>}
        </span>
      </div>
      <Progress value={barPct} tone={latencyTone(node.avg_ms)} className="mt-xxs" />
      <p className="mt-xxs font-mono text-caption text-mute">
        avg {node.avg_ms}ms · max {node.max_ms}ms
        {node.error_rate > 0 && ` · ${Math.round(node.error_rate * 100)}% error rate`}
      </p>
    </div>
  );
}

export default function ObservabilityPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["observability"],
    queryFn: () => observability.get(500),
  });

  const maxAvg = Math.max(1, ...(data?.nodes.map((n) => n.avg_ms) ?? [1]));

  return (
    <div className="px-xl py-lg">
      <PageHeader
        eyebrow="System"
        title="Agent Observability."
        description="How the decision graph is performing — per-node execution count, error rate, and latency across recent runs."
      />

      {isLoading && <p className="text-body-sm text-body">Loading metrics…</p>}

      {error && (
        <Card className="border-down/40">
          <p className="text-body-sm text-down">Could not load observability metrics.</p>
        </Card>
      )}

      {data && data.total_runs === 0 && (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-hairline-strong bg-canvas-soft">
          <p className="font-mono text-body-sm text-mute">
            No node executions recorded yet — metrics appear as the agent processes events.
          </p>
        </div>
      )}

      {data && data.total_runs > 0 && (
        <>
          <div className="grid grid-cols-2 gap-md lg:grid-cols-4">
            <Stat label="Node Executions" value={String(data.total_runs)} />
            <Stat
              label="Error Rate"
              value={`${Math.round(data.error_rate * 100)}%`}
              hint={`${data.total_errors} error${data.total_errors === 1 ? "" : "s"}`}
              tone={data.error_rate > 0 ? "down" : "up"}
            />
            <Stat label="Avg Latency" value={`${data.avg_ms}ms`} />
            <Stat label="Slowest Node" value={data.slowest_node ?? "—"} />
          </div>

          <Card className="mt-lg">
            <Eyebrow>Per-Node Metrics</Eyebrow>
            <div className="mt-sm space-y-sm">
              {data.nodes.map((n) => (
                <NodeRow key={n.node} node={n} maxAvg={maxAvg} />
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
