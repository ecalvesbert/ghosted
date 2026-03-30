"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { profile as profileApi, type UserProfile } from "@/lib/api";
import { Button, Card, Input } from "@/components/ui";
import { Nav } from "@/components/nav";

export default function ProfilePage() {
  const { token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [profileData, setProfileData] = useState<UserProfile | null>(null);
  const [fullName, setFullName] = useState("");
  const [phones, setPhones] = useState("");
  const [emails, setEmails] = useState("");
  const [addresses, setAddresses] = useState("");
  const [ageRange, setAgeRange] = useState("");
  const [relatives, setRelatives] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (token) {
      profileApi.get(token).then((p) => {
        setProfileData(p);
        setFullName(p.full_name || "");
        setPhones(p.phone_numbers.join(", "));
        setEmails(p.email_addresses.join(", "));
        setAddresses(p.addresses.join("\n"));
        setAgeRange(p.age_range || "");
        setRelatives(p.relatives.join(", "));
        setTelegramChatId(p.telegram_chat_id || "");
      }).catch(() => {});
    }
  }, [token]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setMessage("");
    try {
      const updated = await profileApi.update(token, {
        full_name: fullName,
        phone_numbers: phones.split(",").map((s) => s.trim()).filter(Boolean),
        email_addresses: emails.split(",").map((s) => s.trim()).filter(Boolean),
        addresses: addresses.split("\n").map((s) => s.trim()).filter(Boolean),
        age_range: ageRange || undefined,
        relatives: relatives.split(",").map((s) => s.trim()).filter(Boolean),
        telegram_chat_id: telegramChatId || undefined,
      });
      setProfileData(updated);
      setMessage("Profile saved.");
    } catch {
      setMessage("Failed to save profile.");
    } finally {
      setSaving(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div>
      <Nav />
      <div className="mx-auto max-w-2xl p-4 sm:p-6 space-y-6">
      <h1 className="text-2xl font-bold">Profile</h1>

      <Card>
        <form onSubmit={handleSave} className="space-y-4">
          <Input id="fullName" label="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <Input id="phones" label="Phone Numbers (comma-separated)" value={phones} onChange={(e) => setPhones(e.target.value)} />
          <Input id="emails" label="Email Addresses (comma-separated)" value={emails} onChange={(e) => setEmails(e.target.value)} />
          <div className="space-y-1.5">
            <label htmlFor="addresses" className="text-sm text-[var(--muted-foreground)]">Addresses (one per line)</label>
            <textarea
              id="addresses"
              value={addresses}
              onChange={(e) => setAddresses(e.target.value)}
              rows={3}
              className="flex w-full rounded-md border border-[var(--border)] bg-[var(--input)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            />
          </div>
          <Input id="ageRange" label="Age Range (e.g. 35-40)" value={ageRange} onChange={(e) => setAgeRange(e.target.value)} />
          <Input id="relatives" label="Relatives (comma-separated)" value={relatives} onChange={(e) => setRelatives(e.target.value)} />

          <div className="pt-4 border-t border-[var(--border)]">
            <h2 className="text-lg font-semibold mb-2">Telegram Notifications</h2>
            <Input
              id="telegramChatId"
              label="Telegram Chat ID"
              value={telegramChatId}
              onChange={(e) => setTelegramChatId(e.target.value)}
            />
            <p className="text-xs text-[var(--muted-foreground)] mt-1">
              Send /start to @GhostedBot on Telegram, then paste your chat ID here
            </p>
          </div>

          {message && <p className="text-sm text-[var(--muted-foreground)]">{message}</p>}
          <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save Profile"}</Button>
        </form>
      </Card>
      </div>
    </div>
  );
}
