"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { approvals, type ApprovalRequest } from "@/lib/api";
import { Card, Eyebrow } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function ApprovalCard({ approval }: { approval: ApprovalRequest }) {
  const qc = useQueryClient();
  const decide = useMutation({
    mutationFn: ({ approved }: { approved: boolean }) =>
      approvals.decide(approval._id, approved),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["approvals", "pending"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });

  const d = approval.decision;
  const conf = approval.confidence?.overall;
  const actionTone = d.action === "BUY" ? "up" : d.action === "SELL" ? "down" : "neutral";

  return (
    <Card>
      <div className="flex items-start justify-between gap-md">
        <div>
          <div className="flex items-center gap-xs">
            <Badge tone={actionTone}>{d.action}</Badge>
            <span className="font-mono text-display-sm tnum text-ink">
              {d.quantity} {d.ticker}
            </span>
          </div>
          <p className="mt-xs max-w-prose text-body-sm text-body">{d.reasoning}</p>
        </div>
        {conf != null && (
          <div className="text-right">
            <Eyebrow>Confidence</Eyebrow>
            <div className="mt-xxs font-mono text-display-sm tnum text-ink">
              {Math.round(conf * 100)}%
            </div>
          </div>
        )}
      </div>

      <div className="mt-md flex items-center gap-xs">
        <Button
          variant="primary"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ approved: true })}
        >
          Approve
        </Button>
        <Button
          variant="danger"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ approved: false })}
        >
          Reject
        </Button>
        {decide.isError && (
          <span className="text-caption text-down">Failed — try again.</span>
        )}
      </div>
    </Card>
  );
}

export default function ExecutionPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => approvals.list("pending"),
  });

  const pending = data?.approvals ?? [];

  return (
    <div className="px-xl py-lg">
      <PageHeader
        eyebrow="Human-in-the-loop"
        title="Execution Center."
        description="Trades awaiting your approval before they execute."
      />

      {isLoading && <p className="text-body-sm text-body">Loading approvals…</p>}

      {error && (
        <Card className="border-down/40">
          <p className="text-body-sm text-down">Could not load approvals.</p>
        </Card>
      )}

      {data && pending.length === 0 && (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-hairline-strong bg-canvas-soft">
          <p className="font-mono text-body-sm text-mute">No pending approvals.</p>
        </div>
      )}

      <div className="space-y-md">
        {pending.map((a) => (
          <ApprovalCard key={a._id} approval={a} />
        ))}
      </div>
    </div>
  );
}
