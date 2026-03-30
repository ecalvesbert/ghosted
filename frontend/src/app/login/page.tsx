"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button, Card, Input } from "@/components/ui";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await auth.login(email, password);
      login(res.token);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">Ghosted</h1>
          <p className="text-sm text-[var(--muted-foreground)]">Sign in to your account</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input id="email" label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input id="password" label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p className="text-sm text-[var(--destructive)]">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        <p className="text-center text-sm text-[var(--muted-foreground)]">
          Have an invite? <a href="/register" className="underline hover:text-[var(--foreground)]">Register</a>
        </p>
      </Card>
    </div>
  );
}
