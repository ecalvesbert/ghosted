"use client";

import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "./ui";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/removals", label: "Removals" },
  { href: "/profile", label: "Profile" },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <nav className="border-b border-[var(--border)] bg-[var(--card)]">
      <div className="mx-auto max-w-4xl flex items-center justify-between px-4 h-14">
        <div className="flex items-center gap-1">
          <span className="font-bold text-sm mr-4 tracking-tight">Ghosted</span>
          {links.map((link) => {
            const active = pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <button
                key={link.href}
                onClick={() => router.push(link.href)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  active
                    ? "bg-[var(--accent)] text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)]"
                }`}
              >
                {link.label}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--muted-foreground)] hidden sm:inline">{user.email}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </div>
    </nav>
  );
}
