# 👻 Ghosted

> Semi-automated personal data removal from data brokers.

Ghosted searches the major people-search and data broker sites for your personal information, shows you exactly what it found, and submits opt-out/removal requests on your behalf — after **you approve each listing**.

📋 **For current status, next steps, and known issues:** see [PROJECT.md](./PROJECT.md)
📐 **For planning record, stack decisions, and risk assessment:** see [PLANNING.md](./PLANNING.md)
🔌 **For all subsystem interface contracts:** see [CONTRACTS.md](./CONTRACTS.md)

---

## What It Does

1. **Scan** — Ghosted searches Tier 1 data brokers for your name, phone, email, and address
2. **Review** — You see every listing found and decide: approve for removal or skip
3. **Remove** — Ghosted submits opt-out requests for approved listings automatically
4. **Track** — Ghosted re-checks removed listings and notifies you when confirmed

No listings are ever removed without your explicit approval.

---

## Architecture

```
User provides PII (encrypted at rest)
          ↓
   POST /api/scans
          ↓
   Scan Engine → asyncio.gather()
   ┌──────────────────────────────────┐
   │  Spokeo adapter   (Playwright)   │
   │  Whitepages adapter              │
   │  BeenVerified adapter            │
   │  Intelius adapter                │
   │  PeopleFinder adapter            │
   └──────────────────────────────────┘
          ↓
   FoundListings → Review UI
          ↓
   User approves listings
          ↓
   Removal Engine → Celery workers
          ↓
   Opt-out submitted per broker
          ↓
   Status tracked → Telegram notification on confirmation
```

---

## Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Automation model | Semi-auto | User reviews every listing — no false removals |
| PII storage | Fernet encrypted at rest | No plaintext PII ever in DB or logs |
| Broker failures | Manual fallback | CAPTCHA/blocks → step-by-step instructions instead |
| Broker execution | Concurrent (`asyncio.gather`) | 5 brokers in parallel, each with 120s timeout |
| Auth | Invite-only + JWT | Small trusted group, no open registration |
| Scans | Manual trigger | User-initiated, 1 active scan per user |
| Migrations | Alembic | Schema changes without data loss |

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind |
| Backend | Python + FastAPI |
| Database | PostgreSQL + Alembic |
| Browser automation | Playwright (Chromium) |
| Task queue | Celery + Redis |
| Auth | JWT + bcrypt |
| Encryption | Python cryptography (Fernet) |
| Hosting | Railway (backend) + Vercel (frontend) |

---

## Target Brokers

### Tier 1 (MVP)
| Broker | URL |
|---|---|
| Spokeo | spokeo.com |
| Whitepages | whitepages.com |
| BeenVerified | beenverified.com |
| Intelius | intelius.com |
| PeopleFinder | peoplefinder.com |

### Tier 2 (Phase 8+)
PeopleLookup, Radaris, MyLife, ZabaSearch, TruthFinder, Instant Checkmate, FamilyTreeNow, and more.

---

## Privacy & Security

- **All PII is encrypted at rest** using Fernet symmetric encryption. Name, email, phone, and address are never stored in plaintext.
- **No PII in logs** — ever.
- **Per-user data isolation** — strictly enforced at the database query level.
- **Invite-only** — no open registration. Access controlled by the admin.
- **You approve every removal** — Ghosted never submits an opt-out without your explicit sign-off.

---

## Required Environment Variables

```bash
# Railway (backend)
DATABASE_URL=             # PostgreSQL connection string (auto-injected by Railway)
REDIS_URL=                # Redis connection string (auto-injected by Railway)
JWT_SECRET=               # Random hex string for JWT signing
ENCRYPTION_KEY=           # Fernet key for PII encryption — back this up
ADMIN_BOOTSTRAP_SECRET=   # One-time secret for creating the first admin user
TELEGRAM_BOT_TOKEN=       # For scan completion / removal confirmation alerts
TELEGRAM_CHAT_ID=         # Your Telegram chat ID

# Vercel (frontend)
NEXT_PUBLIC_API_URL=      # Railway backend URL
```

---

## Project Status

See [PROJECT.md](./PROJECT.md) for live phase status, next steps, and blockers.

---

## ⚠️ Disclaimer

Ghosted is a personal privacy tool. Automated opt-out submissions may conflict with some data brokers' Terms of Service. Use responsibly. Rate limiting, robots.txt respect, and manual fallbacks are built in to minimize risk.
