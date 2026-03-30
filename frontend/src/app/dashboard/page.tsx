"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { scans, removals as removalsApi, profile as profileApi, type ScanJob, type RemovalSummary, ApiError } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { Nav } from "@/components/nav";

const BROKERS = [
  { slug: "spokeo", name: "Spokeo", url: "spokeo.com", active: true },
  { slug: "whitepages", name: "Whitepages", url: "whitepages.com", active: false },
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
  const [scanList, setScanList] = useState<ScanJob[]>([]);
  const [removalSummary, setRemovalSummary] = useState<RemovalSummary | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [profileComplete, setProfileComplete] = useState(false);
  const [showBrokerSelect, setShowBrokerSelect] = useState(false);
  const [selectedBrokers, setSelectedBrokers] = useState<Set<string>>(
    new Set(BROKERS.filter((b) => b.active).map((b) => b.slug))
  );
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
          !!p.full_name && p.phone_numbers.length > 0 && p.email_addresses.length > 0 && !!p.city && !!p.state
        );
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

  async function startScan() {
    if (!token || selectedBrokers.size === 0) return;
    setCreating(true);
    setError("");
    try {
      const scan = await scans.create(token, Array.from(selectedBrokers));
      setShowBrokerSelect(false);
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
          <Button
            size="sm"
            onClick={() => setShowBrokerSelect(!showBrokerSelect)}
            disabled={!profileComplete}
          >
            New Scan
          </Button>
        </div>

        {!profileComplete && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
            Complete your <a href="/profile" className="underline font-medium">profile</a> (name, phone, email, city, and state are required) before starting a scan.
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
              <h2 className="text-lg font-semibold">Select Sites to Scan</h2>
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
            <div className="mt-4 flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">
                {selectedBrokers.size} site{selectedBrokers.size !== 1 ? "s" : ""} selected
              </span>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setShowBrokerSelect(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={startScan} disabled={creating || selectedBrokers.size === 0}>
                  {creating ? "Starting..." : "Start Scan"}
                </Button>
              </div>
            </div>
          </Card>
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
                  <div className="mt-2 flex flex-wrap gap-2">
                    {scan.brokers_targeted.map((slug) => {
                      const info = BROKER_MAP[slug] || { name: slug, url: slug };
                      const completed = scan.brokers_completed.includes(slug);
                      const failed = scan.brokers_failed.includes(slug);
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
                    {scan.listings_found} listings found
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
