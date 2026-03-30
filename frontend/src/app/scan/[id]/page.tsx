"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { scans, listings as listingsApi, type ScanJob, type FoundListing, ApiError } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

function priorityColor(p: number): "destructive" | "warning" | "default" {
  if (p >= 0.9) return "destructive";
  if (p >= 0.7) return "warning";
  return "default";
}

function priorityLabel(p: number): string {
  if (p >= 0.9) return "Critical";
  if (p >= 0.7) return "High";
  if (p >= 0.3) return "Medium";
  return "Low";
}

function statusVariant(status: string): "default" | "success" | "warning" | "destructive" {
  const map: Record<string, "default" | "success" | "warning" | "destructive"> = {
    pending: "default",
    running: "warning",
    done: "success",
    failed: "destructive",
  };
  return map[status] || "default";
}

function ListingCard({
  listing,
  onAction,
}: {
  listing: FoundListing;
  onAction: (id: string, action: "approved" | "skipped") => void;
}) {
  const [acting, setActing] = useState(false);

  async function handleAction(action: "approved" | "skipped") {
    setActing(true);
    try {
      onAction(listing.id, action);
    } finally {
      setActing(false);
    }
  }

  const hasPhone = listing.phones.length > 0;
  const hasEmail = listing.emails.length > 0;

  return (
    <Card className="relative overflow-hidden">
      {/* Priority indicator bar */}
      <div
        className={`absolute top-0 left-0 w-1 h-full ${
          listing.priority >= 0.9 ? "bg-red-500" : listing.priority >= 0.7 ? "bg-amber-500" : "bg-zinc-600"
        }`}
      />

      <div className="pl-3">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            {/* Header row */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{listing.name_on_listing}</span>
              <Badge variant={priorityColor(listing.priority)}>
                {priorityLabel(listing.priority)} ({(listing.priority * 100).toFixed(0)}%)
              </Badge>
              <Badge>{listing.broker}</Badge>
              {listing.status !== "pending_review" && (
                <Badge variant={listing.status === "approved" ? "success" : listing.status === "skipped" ? "default" : "warning"}>
                  {listing.status.replace("_", " ")}
                </Badge>
              )}
            </div>

            {/* PII details */}
            <div className="mt-2 text-sm space-y-1">
              {hasPhone && (
                <p className="text-red-400 font-medium">
                  <span className="text-red-500/70 text-xs uppercase tracking-wide mr-1.5">Phone</span>
                  {listing.phones.join(", ")}
                </p>
              )}
              {hasEmail && (
                <p className="text-red-400 font-medium">
                  <span className="text-red-500/70 text-xs uppercase tracking-wide mr-1.5">Email</span>
                  {listing.emails.join(", ")}
                </p>
              )}
              {listing.addresses.length > 0 && (
                <p className="text-[var(--muted-foreground)]">
                  <span className="text-xs uppercase tracking-wide mr-1.5">Address</span>
                  {listing.addresses.join("; ")}
                </p>
              )}
              {listing.age && (
                <p className="text-[var(--muted-foreground)]">
                  <span className="text-xs uppercase tracking-wide mr-1.5">Age</span>
                  {listing.age}
                </p>
              )}
              {listing.relatives.length > 0 && (
                <p className="text-[var(--muted-foreground)]">
                  <span className="text-xs uppercase tracking-wide mr-1.5">Relatives</span>
                  {listing.relatives.join(", ")}
                </p>
              )}
            </div>

            <a
              href={listing.listing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 text-xs underline text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              View on {listing.broker}
            </a>
          </div>

          {/* Action buttons */}
          {listing.status === "pending_review" && (
            <div className="flex flex-col gap-2 shrink-0">
              <Button
                size="sm"
                onClick={() => handleAction("approved")}
                disabled={acting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                Approve
              </Button>
              <Button size="sm" variant="ghost" onClick={() => handleAction("skipped")} disabled={acting}>
                Skip
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [scan, setScan] = useState<ScanJob | null>(null);
  const [listingList, setListingList] = useState<FoundListing[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (!token || !id) return;
    scans.get(token, id).then(setScan).catch(() => {});
    scans.listings(token, id).then(setListingList).catch(() => {});
  }, [token, id]);

  // Poll while pending/running
  useEffect(() => {
    if (!token || !id || !scan || (scan.status !== "pending" && scan.status !== "running")) return;
    const interval = setInterval(() => {
      scans.get(token, id).then(setScan).catch(() => {});
      scans.listings(token, id).then(setListingList).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [token, id, scan?.status]);

  const handleAction = useCallback(
    async (listingId: string, action: "approved" | "skipped") => {
      if (!token) return;
      const updated = await listingsApi.update(token, listingId, action);
      setListingList((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    },
    [token],
  );

  const counts = useMemo(() => {
    const pending = listingList.filter((l) => l.status === "pending_review").length;
    const approved = listingList.filter((l) => l.status === "approved").length;
    const skipped = listingList.filter((l) => l.status === "skipped").length;
    return { pending, approved, skipped };
  }, [listingList]);

  async function submitAllApproved() {
    if (!token) return;
    setSubmitting(true);
    setSubmitError("");
    const approved = listingList.filter((l) => l.status === "approved");
    try {
      for (const listing of approved) {
        await listingsApi.remove(token, listing.id);
        setListingList((prev) =>
          prev.map((l) => (l.id === listing.id ? { ...l, status: "removal_sent" } : l)),
        );
      }
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.message : "Failed to submit some removals.");
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading || !token) return null;

  const isActive = scan?.status === "pending" || scan?.status === "running";
  const isDone = scan?.status === "done";

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

        {/* Scan progress header */}
        {scan && (
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-xl font-bold">Scan</h1>
                  <Badge variant={statusVariant(scan.status)}>{scan.status}</Badge>
                  {isActive && (
                    <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  )}
                </div>
                <p className="text-sm text-[var(--muted-foreground)]">
                  {new Date(scan.created_at).toLocaleString()}
                </p>
              </div>
              <div className="text-right text-sm space-y-0.5">
                <p>
                  <span className="text-[var(--muted-foreground)]">Brokers:</span>{" "}
                  {scan.brokers_completed.length}/{scan.brokers_targeted.length}
                </p>
                <p>
                  <span className="text-[var(--muted-foreground)]">Listings:</span> {scan.listings_found}
                </p>
                {scan.brokers_failed.length > 0 && (
                  <p className="text-[var(--destructive)]">Failed: {scan.brokers_failed.join(", ")}</p>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {scan.brokers_targeted.length > 0 && (
              <div className="mt-3">
                <div className="h-1.5 rounded-full bg-[var(--muted)] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                    style={{
                      width: `${((scan.brokers_completed.length + scan.brokers_failed.length) / scan.brokers_targeted.length) * 100}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {scan.error && <p className="mt-2 text-sm text-[var(--destructive)]">{scan.error}</p>}
          </Card>
        )}

        {/* Summary bar + submit */}
        {isDone && listingList.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] px-4 py-3">
            <div className="flex gap-4 text-sm">
              <span>
                <span className="text-[var(--muted-foreground)]">Pending:</span>{" "}
                <span className="font-medium">{counts.pending}</span>
              </span>
              <span>
                <span className="text-emerald-500">Approved:</span>{" "}
                <span className="font-medium">{counts.approved}</span>
              </span>
              <span>
                <span className="text-[var(--muted-foreground)]">Skipped:</span>{" "}
                <span className="font-medium">{counts.skipped}</span>
              </span>
            </div>
            {counts.approved > 0 && (
              <Button
                size="sm"
                onClick={submitAllApproved}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {submitting ? "Submitting..." : `Submit ${counts.approved} Approved for Removal`}
              </Button>
            )}
          </div>
        )}

        {submitError && <p className="text-sm text-[var(--destructive)]">{submitError}</p>}

        {/* Listings */}
        {isDone && (
          <div className="space-y-3">
            {listingList.map((listing) => (
              <ListingCard key={listing.id} listing={listing} onAction={handleAction} />
            ))}
            {listingList.length === 0 && (
              <p className="text-sm text-[var(--muted-foreground)] text-center py-8">
                No listings found on any broker.
              </p>
            )}
          </div>
        )}

        {/* Loading state while scan runs */}
        {isActive && (
          <div className="text-center py-12">
            <div className="inline-block w-6 h-6 border-2 border-[var(--muted-foreground)] border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm text-[var(--muted-foreground)]">Scanning brokers for your data...</p>
            {listingList.length > 0 && (
              <p className="text-xs text-[var(--muted-foreground)] mt-1">
                {listingList.length} listing{listingList.length !== 1 ? "s" : ""} found so far
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
