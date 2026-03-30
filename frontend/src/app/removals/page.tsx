"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { removals as removalsApi, type RemovalRequest, type RemovalSummary } from "@/lib/api";
import { Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

const BROKER_NAMES: Record<string, string> = {
  spokeo: "Spokeo",
  whitepages: "Whitepages",
  beenverified: "BeenVerified",
  intelius: "Intelius",
  peoplefinder: "PeopleFinder",
};

function statusVariant(status: string): "default" | "success" | "warning" | "destructive" {
  const map: Record<string, "default" | "success" | "warning" | "destructive"> = {
    pending: "default",
    in_progress: "warning",
    submitted: "success",
    needs_verification: "warning",
    confirmed: "success",
    failed: "destructive",
  };
  return map[status] || "default";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: "Pending",
    in_progress: "In Progress",
    submitted: "Submitted",
    needs_verification: "Needs Verification",
    confirmed: "Confirmed",
    failed: "Failed",
  };
  return map[status] || status;
}

export default function RemovalsPage() {
  const { token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [removalList, setRemovalList] = useState<RemovalRequest[]>([]);
  const [summary, setSummary] = useState<RemovalSummary | null>(null);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (token) {
      removalsApi.list(token).then(setRemovalList).catch(() => {});
      removalsApi.summary(token).then(setSummary).catch(() => {});
    }
  }, [token]);

  if (authLoading || !token) return null;

  return (
    <div>
      <Nav />
      <div className="mx-auto max-w-4xl p-4 sm:p-6 space-y-6">
        <h1 className="text-2xl font-bold">All Removals</h1>

        {summary && summary.total > 0 && (
          <Card>
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <span className="text-[var(--muted-foreground)]">{summary.total} total</span>
              {summary.confirmed > 0 && <span className="text-emerald-400 font-medium">{summary.confirmed} confirmed</span>}
              {summary.submitted > 0 && <span className="text-blue-400 font-medium">{summary.submitted} submitted</span>}
              {summary.needs_verification > 0 && <span className="text-amber-400 font-medium">{summary.needs_verification} needs verification</span>}
              {summary.pending > 0 && <span className="text-[var(--muted-foreground)] font-medium">{summary.pending} pending</span>}
              {summary.failed > 0 && <span className="text-red-400 font-medium">{summary.failed} failed</span>}
            </div>
          </Card>
        )}

        <div className="space-y-2">
          {removalList.map((removal) => (
            <Card key={removal.id}>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{BROKER_NAMES[removal.broker] || removal.broker}</span>
                    <Badge variant={statusVariant(removal.status)}>{statusLabel(removal.status)}</Badge>
                  </div>
                  {removal.opt_out_url && (
                    <a
                      href={removal.opt_out_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs underline text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                    >
                      {removal.opt_out_url}
                    </a>
                  )}
                  {removal.last_error && (
                    <p className="text-xs text-red-400 mt-1">{removal.last_error}</p>
                  )}
                  <p className="text-xs text-[var(--muted-foreground)] mt-1">
                    {new Date(removal.created_at).toLocaleString()}
                    {removal.attempts > 0 && <> &middot; {removal.attempts} attempt{removal.attempts !== 1 ? "s" : ""}</>}
                  </p>
                </div>
              </div>
            </Card>
          ))}
          {removalList.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)] text-center py-8">
              No removal requests yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
