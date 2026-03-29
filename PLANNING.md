# Ghosted — Planning Record

> Created: 2026-03-29
> Repo: https://github.com/ecalvesbert/ghosted

This file captures all planning activities from project initiation. It is a permanent record — update if decisions change, but never delete prior decisions (strike through instead).

---

## Scoping

**What it does:**
Semi-automated personal data removal from data brokers. Searches the major people-search/data broker sites for your personal information, shows you what it found, and submits opt-out/removal requests on your behalf after you approve each listing.

**Who uses it:**
Edward + friends and family (small trusted group). No heavy auth but PII must be secured.

**Tech preferences:**
No strong preference — using same proven stack as SuPM.

**Hosting preference:**
Railway (backend) + Vercel (frontend). **Build straight to prod — no local dev setup.**

**Domain:**
Not decided yet.

**Priority:**
Phone and email removal first. Name/address as secondary.

---

## Stack Decision

| Layer | Choice | Why | Cost |
|---|---|---|---|
| Frontend | Next.js + TypeScript + Tailwind | Proven stack, dark theme, fast | Free (Vercel) |
| Backend | Python + FastAPI | Async, fits automation workflows | Free (Railway) |
| Database | PostgreSQL | User profiles, scan results, removal history | Free tier (Railway) |
| Browser automation | Playwright | JS-heavy broker sites, form fills, clicks | Free (open source) |
| Auth | JWT + bcrypt | Simple, no third-party, keeps PII local | Free |
| Encryption | Python cryptography (Fernet) | Encrypt all PII at rest in DB | Free |
| Task queue | Celery + Redis | Background scans, non-blocking | Free |
| Hosting | Railway + Vercel | Proven from SuPM | ~$5/mo |

**Monthly cost estimate:**
- Solo: ~$5/mo (Railway hobby)
- Small group (5-10 users): ~$5-10/mo
- No AI API costs — pure automation

---

## Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Data brokers block automated removals | High | Rotate user-agents, rate limit, manual fallback instructions |
| Broker opt-out flows change frequently | High | Modular per-broker adapters — one break doesn't cascade |
| PII stored in DB gets exposed | Critical | Fernet symmetric encryption for all PII at rest, never log raw data |
| Email verification required by brokers | Medium | Flag step, prompt user to confirm manually |
| CAPTCHAs block automation | Medium | Detect → fall back to manual step-by-step instructions |
| Multi-user data leakage | High | Strict per-user data isolation, no cross-user queries |
| False positives (wrong person removed) | Medium | Semi-auto: user reviews every found listing before removal submitted |

### Mitigations Baked In From Day One

- [x] All PII encrypted at rest (Fernet) — name, email, phone, address stored as ciphertext
- [x] Per-broker adapter pattern — each broker isolated in its own module
- [x] Semi-auto review flow — user approves every listing before opt-out submitted
- [x] Manual fallback — if automation fails, generate human-readable removal instructions
- [x] No raw PII in logs — ever
- [x] Per-user data isolation enforced at DB query level
- [x] Per-broker timeout (120s default) — hung broker doesn't block scan
- [x] Per-broker rate limit (0.5 req/s default) — reduce detection/blocking risk
- [x] Concurrent broker execution — `asyncio.gather()` across all adapters
- [x] 1 active scan per user limit — enforced at API level (409 if already running)
- [x] Alembic for DB migrations — schema changes without data loss
- [x] Admin bootstrap endpoint — one-time, secret-gated, self-disabling
- [x] Celery job results persisted in PostgreSQL — survive Redis restarts
- [x] Custom Railway Dockerfile with Playwright/Chromium pre-installed — avoid build timeouts

---

## Phased Plan

| Phase | Description | Est. Time | Status |
|---|---|---|---|
| 0 | GitHub repo creation, PLANNING.md, CONTRACTS.md | Done | ✅ |
| 1 | Foundation — scaffold, Alembic migrations, CI, custom Dockerfile (Playwright), Railway + Vercel wired up, encrypted user profiles, admin bootstrap | 2 days | 🔲 |
| 2 | Broker adapters (Spokeo, Whitepages, BeenVerified, Intelius, PeopleFinder) — concurrent, with timeouts + rate limits | 3 days | 🔲 |
| 3 | Scan engine — concurrent broker execution, 1-scan-per-user limit, results to PostgreSQL | 2 days | 🔲 |
| 4 | Review UI — show findings, approve/skip per listing | 2 days | 🔲 |
| 5 | Removal engine — submit opt-out for approved listings, Celery tasks persisted in Postgres | 2 days | 🔲 |
| 6 | Status tracking — re-check removed listings, confirm deletion | 1 day | 🔲 |
| 7 | Notifications — Telegram alert on scan complete / removal confirmed | 1 day | 🔲 |
| 8 | Hardening — more brokers, ENCRYPTION_KEY rotation utility, manual fallbacks | 2 days | 🔲 |

**Total estimated time:** ~15 days

---

## Target Brokers (Phase 2)

### Tier 1 — Build First
- Spokeo (spokeo.com)
- Whitepages (whitepages.com)
- BeenVerified (beenverified.com)
- Intelius (intelius.com)
- PeopleFinder (peoplefinder.com)

### Tier 2 — Add in Phase 9
- PeopleLookup, Radaris, MyLife, Pipl, ZabaSearch, TruthFinder, Instant Checkmate, FamilyTreeNow, and others

---

## Known Risks & Mitigations

| Risk | Notes |
|---|---|
| **ToS / Legal** | Most brokers prohibit automated opt-outs. Mitigations: aggressive rate limiting (0.5 req/s), respect robots.txt, randomize request timing, manual fallback as primary path if detected. This is a personal/private tool — not a commercial service — which reduces but does not eliminate risk. |
| **ENCRYPTION_KEY loss** | If the Fernet key is lost, all PII is unrecoverable. Mitigation: document key backup in Railway env vars, add re-encryption utility in Phase 8. |
| **Railway Chromium build size** | Playwright + Chromium is ~400MB. Mitigations: custom Dockerfile, Railway persistent build cache. |
| **Redis restart = lost Celery jobs** | Mitigated by persisting Celery task results in PostgreSQL, not just Redis. |

## Open Questions at Planning Time

- [ ] What name to use? "Ghosted" — confirmed ✅
- [ ] Custom domain?
- [x] Should scan runs be scheduled (e.g., monthly re-scan) or manual-only for now? → **Manual-only for MVP**
- [x] Multi-user: invite-only or open registration? → **Invite-only**

---

## Changes to Plan

| Date | Change | Reason |
|---|---|---|
| | | |

---

## Additional Required Env Vars (discovered during gap analysis)

```bash
ADMIN_BOOTSTRAP_SECRET=   # one-time secret for creating first admin user
ENCRYPTION_KEY=           # Fernet key — back this up, loss = unrecoverable PII
```

_Last updated: 2026-03-29_
