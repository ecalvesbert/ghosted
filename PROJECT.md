# Ghosted — Project Memory

> Semi-automated personal data removal from data brokers.
> Repo: https://github.com/ecalvesbert/ghosted
> Planning: [PLANNING.md](./PLANNING.md)

---

## What It Does

Searches the major people-search and data broker sites for your personal information, shows you exactly what was found, and submits opt-out/removal requests on your behalf — after you approve each listing. Phone and email removal prioritized. Built for Edward + close friends/family.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16 + TypeScript + Tailwind (dark theme) |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| Browser automation | Browserbase + Playwright SDK (managed Chromium, stealth/proxy) |
| Auth | JWT + bcrypt |
| Encryption | Python cryptography (Fernet) — all PII at rest |
| Task queue | Celery + Redis |
| Hosting | Vercel (frontend) + Railway Pro (backend/DB/Redis, 8GB RAM) |

---

## Current Status

### ✅ Completed Phases

| Phase | Description |
|---|---|
| 0 | GitHub repo, PLANNING.md, CONTRACTS.md, gap analysis |
| 1 | Foundation — FastAPI backend, Next.js 16 frontend, Alembic, Fernet encryption, JWT auth, Celery |
| 2 | Spokeo adapter — search, submit_removal, verify_removal via Browserbase + Playwright |
| 3 | Scan engine — sequential execution, live progress, 1-scan-per-user limit, Celery tasks |
| 4 | Review UI — listing cards with priority indicators, approve/skip flow, submit-all |
| 5 | Removal engine — Celery tasks for submission + verification, manual fallback |
| 6 | Status tracking — summary endpoint, stale detection, recheck-all, dashboard card |
| 7 | Notifications — Telegram alerts on scan complete, removal confirmed/failed |
| 8 | Hardening — race condition fixes, auth fixes, error format compliance, security audit |

### 🔲 Remaining

| Item | Description |
|---|---|
| Deploy | Backend to Railway Pro, frontend to Vercel, env vars, Alembic migration |
| Live test | Test Spokeo adapter against live site, tune CSS selectors |
| Tier 2 brokers | Whitepages, BeenVerified, Intelius, PeopleFinder adapters |
| ENCRYPTION_KEY rotation | Utility to re-encrypt all PII with a new key |

---

## 🔜 Next Steps

1. **Deploy** — Railway Pro (backend + Postgres + Redis) + Vercel (frontend), set all env vars
2. **Live test Spokeo** — run against real site, fix selectors, handle edge cases
3. **Add more brokers** — Whitepages next, then BeenVerified, Intelius, PeopleFinder

---

## 🔴 Blocked on Edward

| # | What's needed | Why it's blocking |
|---|---|---|
| ~~1~~ | ~~Decision: scheduled re-scans or manual-only for MVP?~~ | ✅ Manual-only |
| ~~2~~ | ~~Decision: invite-only or open registration?~~ | ✅ Invite-only |
| 3 | Decision: custom domain? | Needed before production deploy |

---

## 🐛 Known Issues

None yet — project just started.

---

## Architecture

```
User provides: name, email, phone, address (encrypted at rest)
                    ↓
         Scan engine → Playwright via Browserbase → Broker sites
                    ↓
         Found listings returned → Review UI
                    ↓
         User approves listings → Removal engine
                    ↓
         Opt-out submitted per broker → Status tracked
                    ↓
         Re-check in X days → Telegram notification on confirmation
```

---

## Key Files

```
~/Projects/ghosted/
├── backend/          # FastAPI + Celery workers
├── frontend/         # Next.js UI
├── brokers/          # Per-broker Playwright adapters
├── PLANNING.md       # Planning record
└── PROJECT.md        # This file
```

---

## Required Environment Variables

```bash
DATABASE_URL=                 # auto-injected by Railway
REDIS_URL=                    # auto-injected by Railway
JWT_SECRET=                   # random hex string
ENCRYPTION_KEY=               # Fernet key — back this up, loss = unrecoverable PII
ADMIN_BOOTSTRAP_SECRET=       # one-time secret for first admin user creation
BROWSERBASE_API_KEY=          # Browserbase managed browser sessions
BROWSERBASE_PROJECT_ID=       # Browserbase project ID
TELEGRAM_BOT_TOKEN=           # bot token for scan/removal notifications
TELEGRAM_CHAT_ID=             # per-user — stored in user profile, not global env var
# Vercel (frontend):
NEXT_PUBLIC_API_URL=          # Railway backend URL
```

---

## Decisions & Context

- **Semi-auto** — user reviews every found listing before removal is submitted. Prevents false positives.
- **Fernet encryption** — all PII (name, email, phone, address) encrypted at rest. Never stored or logged in plaintext.
- **Per-broker adapters** — each broker is an isolated module. One site changing its flow doesn't break others.
- **Phone + email first** — highest-value removal targets. Address/relatives as secondary.
- **Manual fallback** — if Playwright automation hits a CAPTCHA or fails, generate human-readable step-by-step removal instructions instead of silently failing.
- **Manual scans only** — no scheduled/cron re-scans in MVP. User triggers each scan.
- **Invite-only** — no open registration. Admin creates invite codes for trusted users.
- **Straight to prod** — no local dev environment. Railway + Vercel from day one, CI/CD on every push.

---

_Last updated: 2026-03-29_
