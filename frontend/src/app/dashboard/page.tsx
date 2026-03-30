"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { removals as removalsApi, profile as profileApi, type RemovalBatch, type RemovalSummary, ApiError } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

const BROKERS = [
  { slug: "spokeo", name: "Spokeo", url: "spokeo.com", active: true },
  { slug: "whitepages", name: "Whitepages", url: "whitepages.com", active: true },
  { slug: "beenverified", name: "BeenVerified", url: "beenverified.com", active: false },
  { slug: "intelius", name: "Intelius", url: "intelius.com", active: false },
  { slug: "peoplefinder", name: "PeopleFinder", url: "peoplefinder.com", active: false },
  { slug: "truepeoplesearch", name: "TruePeopleSearch", url: "truepeoplesearch.com", active: false },
  { slug: "fastpeoplesearch", name: "FastPeopleSearch", url: "fastpeoplesearch.com", active: false },
  { slug: "thatsthem", name: "ThatsThem", url: "thatsthem.com", active: false },
  { slug: "radaris", name: "Radaris", url: "radaris.com", active: false },
  { slug: "mylife", name: "MyLife", url: "mylife.com", active: false },
  { slug: "ussearch", name: "USSearch", url: "ussearch.com", active: false },
  { slug: "peekyou", name: "PeekYou", url: "peekyou.com", active: false },
  { slug: "instantcheckmate", name: "Instant Checkmate", url: "instantcheckmate.com", active: false },
  { slug: "usphonebook", name: "USPhoneBook", url: "usphonebook.com", active: false },
  { slug: "anywho", name: "AnyWho", url: "anywho.com", active: false },
  { slug: "addresses", name: "Addresses.com", url: "addresses.com", active: false },
  { slug: "cyberbackgroundchecks", name: "CyberBackgroundChecks", url: "cyberbackgroundchecks.com", active: false },
  { slug: "familytreenow", name: "FamilyTreeNow", url: "familytreenow.com", active: false },
  { slug: "nuwber", name: "Nuwber", url: "nuwber.com", active: false },
  { slug: "cocofinder", name: "CocoFinder", url: "cocofinder.com", active: false },
];

const BROKER_MAP = Object.fromEntries(BROKERS.map((b) => [b.slug, b]));

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
  const router = useRouter();
  const [batches, setBatches] = useState<RemovalBatch[]>([]);
  const [summary, setSummary] = useState<RemovalSummary | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [profileComplete, setProfileComplete] = useState(false);
  const [showBrokerSelect, setShowBrokerSelect] = useState(false);
  const [selectedBrokers, setSelectedBrokers] = useState<Set<string>>(
    new Set(BROKERS.filter((b) => b.active).map((b) => b.slug))
  );

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (token) {
      removalsApi.batches(token).then(setBatches).catch(() => {});
      removalsApi.summary(token).then(setSummary).catch(() => {});
      profileApi.get(token).then((p) => {
        setProfileComplete(!!p.full_name);
      }).catch(() => {});
    }
  }, [token]);

  function toggleBroker(slug: string) {
    setSelectedBrokers((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }

  function selectAll() {
    setSelectedBrokers(new Set(BROKERS.filter((b) => b.active).map((b) => b.slug)));
  }

  function selectNone() {
    setSelectedBrokers(new Set());
  }

  async function startRemovals() {
    if (!token || selectedBrokers.size === 0) return;
    setCreating(true);
    setError("");
    try {
      const batch = await removalsApi.create(token, Array.from(selectedBrokers));
      setShowBrokerSelect(false);
      router.push(`/removals/${batch.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === "BATCH_ALREADY_RUNNING") {
        setError("A removal batch is already running. Wait for it to finish.");
      } else {
        setError("Failed to start removals.");
      }
    } finally {
      setCreating(false);
    }
  }

  if (authLoading || !token) return null;

  const hasActivity = summary && summary.total > 0;

  return (
    <div>
      <Nav />
      <div className="mx-auto max-w-4xl p-4 sm:p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <Button
            size="sm"
            onClick={() => setShowBrokerSelect(!showBrokerSelect)}
            disabled={!profileComplete}
          >
            Submit Removals
          </Button>
        </div>

        {!profileComplete && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
            Add your <a href="/profile" className="underline font-medium">full name</a> to your profile before submitting removals.
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Broker selection panel */}
        {showBrokerSelect && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Select Sites for Opt-Out</h2>
              <div className="flex gap-2 text-xs">
                <button onClick={selectAll} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] underline">
                  Select active
                </button>
                <button onClick={selectNone} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] underline">
                  Clear
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {BROKERS.map((broker) => (
                <label
                  key={broker.slug}
                  className={`flex items-center gap-3 rounded-md border p-3 cursor-pointer transition-colors ${
                    !broker.active
                      ? "border-[var(--border)] opacity-50 cursor-not-allowed"
                      : selectedBrokers.has(broker.slug)
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-[var(--border)] hover:bg-[var(--accent)]"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedBrokers.has(broker.slug)}
                    onChange={() => toggleBroker(broker.slug)}
                    disabled={!broker.active}
                    className="rounded border-[var(--border)] accent-emerald-500"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium flex items-center gap-2">
                      {broker.name}
                      {!broker.active && (
                        <span className="text-[10px] rounded-full border border-[var(--border)] px-1.5 py-0.5 text-[var(--muted-foreground)]">
                          coming soon
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)]">{broker.url}</div>
                  </div>
                </label>
              ))}
            </div>
            <p className="mt-3 text-xs text-[var(--muted-foreground)]">
              A live browser session will open for each site. If any fields are missing from your profile, you can enter them directly in the browser.
            </p>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">
                {selectedBrokers.size} site{selectedBrokers.size !== 1 ? "s" : ""} selected
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setShowBrokerSelect(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={startRemovals} disabled={creating || selectedBrokers.size === 0}>
                  {creating ? "Starting..." : "Start Opt-Out"}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Removal summary */}
        {hasActivity && (
          <Card>
            <h2 className="text-lg font-semibold mb-3">Removal Status</h2>
            <div className="flex flex-wrap items-center gap-4 text-sm">
              {summary.confirmed > 0 && <span className="text-emerald-400 font-medium">{summary.confirmed} confirmed</span>}
              {summary.submitted > 0 && <span className="text-blue-400 font-medium">{summary.submitted} submitted</span>}
              {summary.needs_verification > 0 && <span className="text-amber-400 font-medium">{summary.needs_verification} needs verification</span>}
              {summary.in_progress > 0 && <span className="text-amber-400 font-medium">{summary.in_progress} in progress</span>}
              {summary.pending > 0 && <span className="text-[var(--muted-foreground)] font-medium">{summary.pending} pending</span>}
              {summary.failed > 0 && <span className="text-red-400 font-medium">{summary.failed} failed</span>}
            </div>
          </Card>
        )}

        {/* Past batches */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Removal History</h2>
          {batches.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">
              No removal requests yet. Select broker sites above to submit opt-out requests.
            </p>
          ) : (
            <div className="space-y-2">
              {batches.map((batch) => (
                <button
                  key={batch.id}
                  onClick={() => router.push(`/removals/${batch.id}`)}
                  className="w-full text-left rounded-md border border-[var(--border)] p-4 hover:bg-[var(--accent)] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-mono text-[var(--muted-foreground)]">
                      {new Date(batch.created_at).toLocaleString()}
                    </div>
                    {statusBadge(batch.status)}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {batch.brokers_targeted.map((slug) => {
                      const info = BROKER_MAP[slug] || { name: slug, url: slug };
                      const completed = batch.brokers_completed.includes(slug);
                      const failed = batch.brokers_failed.includes(slug);
                      return (
                        <span
                          key={slug}
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                            failed
                              ? "border-red-500/30 text-red-400"
                              : completed
                              ? "border-emerald-500/30 text-emerald-400"
                              : "border-[var(--border)] text-[var(--muted-foreground)]"
                          }`}
                        >
                          {info.name}
                          <span className="text-[10px] opacity-60">{info.url}</span>
                        </span>
                      );
                    })}
                  </div>
                  <div className="mt-1 text-sm text-[var(--muted-foreground)]">
                    {batch.total_removals} removal{batch.total_removals !== 1 ? "s" : ""}
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
