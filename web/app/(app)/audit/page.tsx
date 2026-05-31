"use client";

import { useQuery } from "@tanstack/react-query";
import { audit } from "@/lib/api";
import { Card, Eyebrow } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/** Pull execution evidence (Phase 3) out of an audit payload, if present. */
function evidenceOf(payload: Record<string, unknown>): {
  mode: string;
  confirmation_id?: string | null;
  screenshot?: string | null;
} | null {
  const execution = payload?.execution as Record<string, unknown> | undefined;
  const evidence = execution?.evidence as
    | { mode: string; confirmation_id?: string | null; screenshot?: string | null }
    | undefined;
  return evidence ?? null;
}

export default function AuditPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit"],
    queryFn: () => audit.list(100),
  });

  return (
    <div className="px-xl py-lg">
      <div className="mb-lg">
        <Eyebrow>Trace</Eyebrow>
        <h1 className="mt-xxs text-display-lg text-ink">Audit.</h1>
      </div>

      {isLoading && <p className="text-body text-body-sm">Loading audit log…</p>}
      {error && (
        <Card className="border-error/40">
          <p className="text-body-sm text-down">Could not load audit log.</p>
        </Card>
      )}

      {data && (
        <Card className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-hairline text-left">
                <th className="px-md py-sm font-mono text-caption uppercase text-mute">Agent</th>
                <th className="px-md py-sm font-mono text-caption uppercase text-mute">Action</th>
                <th className="px-md py-sm font-mono text-caption uppercase text-mute">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {data.logs.map((log) => {
                const ev = evidenceOf(log.payload);
                return (
                  <tr key={log._id} className="border-b border-hairline/50">
                    <td className="px-md py-sm font-mono text-body-sm text-ink">{log.agent_name}</td>
                    <td className="px-md py-sm text-body-sm text-body">{log.action}</td>
                    <td className="px-md py-sm">
                      {ev ? (
                        <span className="flex items-center gap-xs">
                          <Badge tone={ev.mode === "paper" ? "neutral" : "info"}>{ev.mode}</Badge>
                          {ev.confirmation_id && (
                            <span className="font-mono text-caption text-mute">{ev.confirmation_id}</span>
                          )}
                          {ev.screenshot && (
                            <span className="font-mono text-caption text-link">screenshot</span>
                          )}
                        </span>
                      ) : (
                        <span className="text-caption text-mute">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {data.logs.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-md py-md text-body-sm text-mute">
                    No agent actions recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
