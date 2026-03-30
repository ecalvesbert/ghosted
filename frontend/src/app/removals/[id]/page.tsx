"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { removals as removalsApi, type RemovalBatch, type RemovalRequest } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

const BROKER_NAMES: Record<string, string> = {
  spokeo: "Spokeo",
  whitepages: "Whitepages",
  beenverified: "BeenVerified",
  intelius: "Intelius",
  peoplefinder: "PeopleFinder",
  truepeoplesearch: "TruePeopleSearch",
  fastpeoplesearch: "FastPeopleSearch",
  thatsthem: "ThatsThem",
  radaris: "Radaris",
  mylife: "MyLife",
};

function statusVariant(status: string): "default" | "success" | "warning" | "destructive" {
  const map: Record<string, "default" | "success" | "warning" | "destructive"> = {
    pending: "default",
    in_progress: "warning",
    running: "warning",
    submitted: "success",
    needs_verification: "warning",
    confirmed: "success",
    done: "success",
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

function RemovalCard({ removal }: { removal: RemovalRequest }) {
  const brokerName = BROKER_NAMES[removal.broker] || removal.broker;

  return (
    <Card className="relative overflow-hidden">
      <div
        className={`absolute top-0 left-0 w-1 h-full ${
          removal.status === "confirmed"
            ? "bg-emerald-500"
            : removal.status === "failed"
            ? "bg-red-500"
            : removal.status === "submitted" || removal.status === "needs_verification"
            ? "bg-blue-500"
            : "bg-zinc-600"
        }`}
      />
      <div className="pl-3">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{brokerName}</span>
              <Badge variant={statusVariant(removal.status)}>
                {statusLabel(removal.status)}
              </Badge>
              {removal.method && (
                <span className="text-xs text-[var(--muted-foreground)]">{removal.method}</span>
              )}
            </div>

            {removal.opt_out_url && (
              <a
                href={removal.opt_out_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-1 text-xs underline text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              >
                {removal.opt_out_url}
              </a>
            )}

            {removal.notes && removal.status !== "failed" && (
              <p className="mt-1 text-xs text-emerald-400">{removal.notes}</p>
            )}
            {removal.last_error && (
              <p className="mt-1 text-xs text-red-400">{removal.last_error}</p>
            )}

            <div className="mt-1 text-xs text-[var(--muted-foreground)]">
              {removal.attempts} attempt{removal.attempts !== 1 ? "s" : ""}
              {removal.submitted_at && (
                <> &middot; Submitted {new Date(removal.submitted_at).toLocaleString()}</>
              )}
              {removal.confirmed_at && (
                <> &middot; Confirmed {new Date(removal.confirmed_at).toLocaleString()}</>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-2 shrink-0">
            {removal.live_view_url && (removal.status === "pending" || removal.status === "in_progress") && (
              <a
                href={removal.live_view_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button size="sm" variant="ghost">
                  Watch Live
                </Button>
              </a>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function BatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [batch, setBatch] = useState<RemovalBatch | null>(null);
  const [removalList, setRemovalList] = useState<RemovalRequest[]>([]);
  const [liveViewOpened, setLiveViewOpened] = useState(false);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (!token || !id) return;
    removalsApi.batch(token, id).then(setBatch).catch(() => {});
    removalsApi.list(token).then((all) => {
      setRemovalList(all.filter((r) => r.batch_id === id));
    }).catch(() => {});
  }, [token, id]);

  // Poll while active
  useEffect(() => {
    if (!token || !id || !batch || (batch.status !== "pending" && batch.status !== "running")) return;
    const interval = setInterval(() => {
      removalsApi.batch(token, id).then(setBatch).catch(() => {});
      removalsApi.list(token).then((all) => {
        setRemovalList(all.filter((r) => r.batch_id === id));
      }).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [token, id, batch?.status]);

  // Auto-open live view
  useEffect(() => {
    if (liveViewOpened) return;
    const activeRemoval = removalList.find(
      (r) => r.live_view_url && (r.status === "pending" || r.status === "in_progress")
    );
    if (activeRemoval?.live_view_url) {
      setLiveViewOpened(true);
      window.open(activeRemoval.live_view_url, "_blank");
    }
  }, [removalList, liveViewOpened]);

  if (authLoading || !token) return null;

  const isActive = batch?.status === "pending" || batch?.status === "running";

  return (
    <div>
      <Nav />
      <div className="mx-auto max-w-4xl p-4 sm:p-6 space-y-6">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
        >
          &larr; Back to Dashboard
        </button>

        {/* Batch progress header */}
        {batch && (
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-xl font-bold">Removal Batch</h1>
                  <Badge variant={statusVariant(batch.status)}>{batch.status}</Badge>
                  {isActive && (
                    <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  )}
                </div>
                <p className="text-sm text-[var(--muted-foreground)]">
                  {new Date(batch.created_at).toLocaleString()}
                </p>
              </div>
              <div className="text-right text-sm space-y-0.5">
                <p>
                  <span className="text-[var(--muted-foreground)]">Sites:</span>{" "}
                  {batch.brokers_completed.length}/{batch.brokers_targeted.length}
                </p>
                {batch.brokers_failed.length > 0 && (
                  <p className="text-red-400">Failed: {batch.brokers_failed.join(", ")}</p>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {batch.brokers_targeted.length > 0 && (
              <div className="mt-3">
                <div className="h-1.5 rounded-full bg-[var(--muted)] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                    style={{
                      width: `${((batch.brokers_completed.length + batch.brokers_failed.length) / batch.brokers_targeted.length) * 100}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </Card>
        )}

        {/* Individual removal requests */}
        <div className="space-y-3">
          {removalList.map((removal) => (
            <RemovalCard key={removal.id} removal={removal} />
          ))}
        </div>

        {/* Loading state */}
        {isActive && removalList.length === 0 && (
          <div className="text-center py-12">
            <div className="inline-block w-6 h-6 border-2 border-[var(--muted-foreground)] border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm text-[var(--muted-foreground)]">Submitting opt-out requests...</p>
          </div>
        )}

        {isActive && removalList.length > 0 && (
          <div className="text-center py-4">
            <div className="inline-block w-4 h-4 border-2 border-[var(--muted-foreground)] border-t-transparent rounded-full animate-spin mb-2" />
            <p className="text-xs text-[var(--muted-foreground)]">Processing remaining sites...</p>
          </div>
        )}
      </div>
    </div>
  );
}
