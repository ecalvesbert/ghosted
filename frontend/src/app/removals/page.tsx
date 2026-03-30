"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { removals as removalsApi, type RemovalRequest, type RemovalSummary } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

function statusVariant(status: string): "default" | "success" | "warning" | "destructive" {
  switch (status) {
    case "removal_sent": return "warning";
    case "confirmed": return "success";
    case "failed": return "destructive";
    default: return "default";
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "removal_sent": return "Pending";
    case "confirmed": return "Confirmed";
    case "failed": return "Failed";
    default: return status.replace("_", " ");
  }
}

function isStale(removal: RemovalRequest): boolean {
  if (removal.status !== "removal_sent" || !removal.submitted_at) return false;
  const submittedAt = new Date(removal.submitted_at).getTime();
  const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return submittedAt < sevenDaysAgo;
}

export default function RemovalsPage() {
  const { token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [removalList, setRemovalList] = useState<RemovalRequest[]>([]);
  const [summary, setSummary] = useState<RemovalSummary | null>(null);
  const [recheckingId, setRecheckingId] = useState<string | null>(null);
  const [recheckingAll, setRecheckingAll] = useState(false);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  const loadData = useCallback(async () => {
    if (!token) return;
    const [list, sum] = await Promise.all([
      removalsApi.list(token).catch(() => []),
      removalsApi.summary(token).catch(() => null),
    ]);
    setRemovalList(list);
    setSummary(sum);
  }, [token]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleRecheck(id: string) {
    if (!token) return;
    setRecheckingId(id);
    try {
      const updated = await removalsApi.recheck(token, id);
      setRemovalList((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch {
      // silently fail
    } finally {
      setRecheckingId(null);
    }
  }

  async function handleRecheckAllStale() {
    if (!token) return;
    setRecheckingAll(true);
    try {
      await removalsApi.recheckStale(token);
      // Reload data after a short delay to allow tasks to start
      setTimeout(loadData, 2000);
    } catch {
      // silently fail
    } finally {
      setRecheckingAll(false);
    }
  }

  if (authLoading || !token) return null;

  // Group removals: confirmed, then pending, then failed
  const statusOrder: Record<string, number> = { confirmed: 0, removal_sent: 1, failed: 2 };
  const sorted = [...removalList].sort(
    (a, b) => (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3)
  );

  const staleCount = removalList.filter(isStale).length;

  return (
    <div>
      <Nav />
      <div className="mx-auto max-w-4xl p-4 sm:p-6 space-y-6">
        <h1 className="text-2xl font-bold">Removals</h1>

        {/* Summary header */}
        {summary && summary.total > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="text-center">
              <div className="text-2xl font-bold">{summary.total}</div>
              <div className="text-xs text-[var(--muted-foreground)]">Total</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-bold text-emerald-400">{summary.confirmed}</div>
              <div className="text-xs text-[var(--muted-foreground)]">Confirmed</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-bold text-amber-400">{summary.pending}</div>
              <div className="text-xs text-[var(--muted-foreground)]">Pending</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-bold text-red-400">{summary.failed}</div>
              <div className="text-xs text-[var(--muted-foreground)]">Failed</div>
            </Card>
          </div>
        )}

        {/* Recheck All Stale button */}
        {staleCount > 0 && (
          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="secondary"
              onClick={handleRecheckAllStale}
              disabled={recheckingAll}
            >
              {recheckingAll ? "Rechecking..." : `Recheck All Stale (${staleCount})`}
            </Button>
            <span className="text-xs text-amber-400">
              {staleCount} removal{staleCount !== 1 ? "s" : ""} pending for 7+ days
            </span>
          </div>
        )}

        {removalList.length === 0 ? (
          <Card>
            <p className="text-sm text-[var(--muted-foreground)]">
              No removal requests yet. Approve listings from a scan to start removing your data.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {sorted.map((removal) => {
              const stale = isStale(removal);
              return (
                <Card key={removal.id}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold">{removal.broker}</span>
                        <Badge variant={statusVariant(removal.status)}>
                          {statusLabel(removal.status)}
                        </Badge>
                        <Badge>{removal.method}</Badge>
                        {stale && (
                          <Badge variant="warning">Stale — recheck recommended</Badge>
                        )}
                      </div>
                      <div className="mt-1.5 text-sm text-[var(--muted-foreground)] space-y-0.5">
                        {removal.submitted_at && (
                          <p>Submitted: {new Date(removal.submitted_at).toLocaleString()}</p>
                        )}
                        {removal.status === "confirmed" && removal.confirmed_at && (
                          <p className="text-emerald-400">
                            Confirmed: {new Date(removal.confirmed_at).toLocaleString()}
                          </p>
                        )}
                        {removal.attempts > 1 && <p>Attempts: {removal.attempts}</p>}
                        {removal.status === "failed" && removal.last_error && (
                          <p className="text-red-400">{removal.last_error}</p>
                        )}
                      </div>
                    </div>
                    {removal.status !== "confirmed" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleRecheck(removal.id)}
                        disabled={recheckingId === removal.id}
                      >
                        {recheckingId === removal.id ? "Checking..." : "Recheck"}
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
