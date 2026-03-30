"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { scans, removals as removalsApi, profile as profileApi, type ScanJob, type RemovalSummary, ApiError } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

function statusBadge(status: string) {
  const map: Record<string, "default" | "success" | "warning" | "destructive"> = {
    pending: "default",
    running: "warning",
    done: "success",
    failed: "destructive",
  };
  return <Badge variant={map[status] || "default"}>{status}</Badge>;
}

export default function DashboardPage() {
  const { token, loading: authLoading } = useAuth();
  const [scanList, setScanList] = useState<ScanJob[]>([]);
  const [removalSummary, setRemovalSummary] = useState<RemovalSummary | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [profileComplete, setProfileComplete] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (token) {
      scans.list(token).then(setScanList).catch(() => {});
      removalsApi.summary(token).then(setRemovalSummary).catch(() => {});
      profileApi.get(token).then((p) => {
        setProfileComplete(
          !!p.full_name && p.phone_numbers.length > 0 && p.email_addresses.length > 0
        );
      }).catch(() => {});
    }
  }, [token]);

  async function startScan() {
    if (!token) return;
    setCreating(true);
    setError("");
    try {
      const scan = await scans.create(token);
      router.push(`/scan/${scan.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === "SCAN_ALREADY_RUNNING") {
        setError("A scan is already running. Wait for it to finish before starting a new one.");
      } else {
        setError("Failed to start scan.");
      }
    } finally {
      setCreating(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div>
      <Nav />
      <div className="mx-auto max-w-4xl p-4 sm:p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <Button size="sm" onClick={startScan} disabled={creating || !profileComplete}>
            {creating ? "Starting..." : "New Scan"}
          </Button>
        </div>

        {!profileComplete && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
            Complete your <a href="/profile" className="underline font-medium">profile</a> (name, phone, and email are required) before starting a scan.
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Removal status summary */}
        {removalSummary && removalSummary.total > 0 && (
          <button
            onClick={() => router.push("/removals")}
            className="w-full text-left"
          >
            <Card className="hover:bg-[var(--accent)] transition-colors">
              <h2 className="text-lg font-semibold mb-3">Removal Status</h2>
              <div className="flex items-center gap-6 text-sm">
                <span className="text-emerald-400 font-medium">{removalSummary.confirmed} confirmed</span>
                <span className="text-amber-400 font-medium">{removalSummary.pending} pending</span>
                <span className="text-red-400 font-medium">{removalSummary.failed} failed</span>
              </div>
            </Card>
          </button>
        )}

        <Card>
          <h2 className="text-lg font-semibold mb-4">Past Scans</h2>
          {scanList.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">
              No scans yet. Start one to find your data on broker sites.
            </p>
          ) : (
            <div className="space-y-2">
              {scanList.map((scan) => (
                <button
                  key={scan.id}
                  onClick={() => router.push(`/scan/${scan.id}`)}
                  className="w-full text-left rounded-md border border-[var(--border)] p-4 hover:bg-[var(--accent)] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-mono text-[var(--muted-foreground)]">
                      {new Date(scan.created_at).toLocaleString()}
                    </div>
                    {statusBadge(scan.status)}
                  </div>
                  <div className="mt-1 text-sm flex gap-4">
                    <span>{scan.listings_found} listings found</span>
                    <span className="text-[var(--muted-foreground)]">
                      {scan.brokers_completed.length}/{scan.brokers_targeted.length} brokers
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
