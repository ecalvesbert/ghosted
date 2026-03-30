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
| Frontend | Next.js + TypeScript + Tailwind (dark theme) |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| Browser automation | Playwright |
| Auth | JWT + bcrypt |
| Encryption | Python cryptography (Fernet) — all PII at rest |
| Task queue | Celery + Redis |
| Hosting | Vercel (frontend) + Railway (backend/DB/Redis) |

---

## Current Status

### ✅ Completed Phases

| Phase | Description |
|---|---|
| 0 | GitHub repo, PLANNING.md, CONTRACTS.md, gap analysis |

### 🔲 Remaining Phases

| Phase | Description |
|---|---|
| 1 | Foundation — scaffold, Alembic, CI, Browserbase, Railway Pro + Vercel, encrypted user profiles, admin bootstrap |
| 2 | Broker adapters — Spokeo, Whitepages, BeenVerified, Intelius, PeopleFinder (sequential, with timeouts + rate limits) |
| 3 | Scan engine — sequential execution, live progress, 1-scan-per-user limit, results to PostgreSQL |
| 4 | Review UI — findings sorted by priority, approve/skip per listing |
| 5 | Removal engine — submit opt-out for approved listings, Celery tasks persisted in Postgres |
| 6 | Status tracking — re-check removed listings, confirm deletion |
| 7 | Notifications — Telegram alert on scan complete / removal confirmed |
| 8 | Hardening — more brokers, ENCRYPTION_KEY rotation utility, manual fallbacks |

---

## 🔜 Next Steps

1. **Scaffold Phase 1** — monorepo structure, encrypted user profile model, CI, Docker
2. **Research Tier 1 broker opt-out flows** — map each site's removal process before writing adapters
3. **Implement broker adapters** (Phase 2) — Spokeo first as the reference implementation

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
         Scan engine → Playwright adapters → Broker sites
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
DATABASE_URL=
REDIS_URL=
JWT_SECRET=
ENCRYPTION_KEY=       # Fernet key for PII encryption
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=267671508
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
