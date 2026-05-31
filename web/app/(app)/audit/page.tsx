"use client";

import { useQuery } from "@tanstack/react-query";
import { audit } from "@/lib/api";
import { Card, Eyebrow } from "@/components/ui/card";

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
              </tr>
            </thead>
            <tbody>
              {data.logs.map((log) => (
                <tr key={log._id} className="border-b border-hairline/50">
                  <td className="px-md py-sm font-mono text-body-sm text-ink">{log.agent_name}</td>
                  <td className="px-md py-sm text-body-sm text-body">{log.action}</td>
                </tr>
              ))}
              {data.logs.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-md py-md text-body-sm text-mute">
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
