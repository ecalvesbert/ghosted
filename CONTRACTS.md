# Ghosted — Interface Contracts

> Version: 1.0
> Last updated: 2026-03-29
>
> **This is the single source of truth for all subsystem interfaces.**
> All agents and developers implement to this spec. Do not invent your own field names, status values, or response shapes.
> If a contract needs to change, update this file first, then notify affected implementors.

---

## Enums & Constants

```python
class ScanStatus(str, Enum):
    PENDING   = "pending"     # queued, not started
    RUNNING   = "running"     # actively scanning brokers
    DONE      = "done"        # scan complete, listings ready for review
    FAILED    = "failed"      # scan errored out

class ListingStatus(str, Enum):
    PENDING_REVIEW = "pending_review"  # found, awaiting user decision
    APPROVED       = "approved"        # user approved — submit removal
    SKIPPED        = "skipped"         # user chose to skip
    REMOVAL_SENT   = "removal_sent"    # opt-out submitted
    CONFIRMED      = "confirmed"       # broker confirmed removal
    FAILED         = "failed"          # removal attempt failed

class RemovalMethod(str, Enum):
    AUTOMATED  = "automated"   # Playwright submitted the form
    MANUAL     = "manual"      # User must do it; instructions provided

class BrokerStatus(str, Enum):
    ACTIVE    = "active"
    DISABLED  = "disabled"
    CAPTCHA   = "captcha"     # temporarily blocked by CAPTCHA
```

---

## Data Models

### UserProfile
Stored in DB. All PII fields are encrypted at rest (Fernet).

```python
class UserProfile(BaseModel):
    id: UUID
    email: str                      # [ENCRYPTED]
    hashed_password: str
    invite_code_used: str
    # PII used for broker searches — all encrypted
    full_name: str                  # [ENCRYPTED]
    phone_numbers: list[str]        # [ENCRYPTED] — prioritized for removal
    email_addresses: list[str]      # [ENCRYPTED] — prioritized for removal
    addresses: list[str]            # [ENCRYPTED] — street, city, state, zip
    age_range: Optional[str]        # [ENCRYPTED] — e.g. "35-40"
    relatives: list[str]            # [ENCRYPTED] — optional, helps disambiguate
    created_at: datetime
    updated_at: datetime
```

### ScanJob
One scan run = one ScanJob. Contains all results.

```python
class ScanJob(BaseModel):
    id: UUID
    user_id: UUID
    status: ScanStatus
    brokers_targeted: list[str]     # broker slugs e.g. ["spokeo", "whitepages"]
    brokers_completed: list[str]
    brokers_failed: list[str]
    listings_found: int             # total across all brokers
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    created_at: datetime
```

### FoundListing
One record per listing found on a broker. This is what broker adapters return.

```python
class FoundListing(BaseModel):
    id: UUID
    scan_job_id: UUID
    user_id: UUID
    broker: str                     # broker slug e.g. "spokeo"
    listing_url: str                # direct URL to the listing on the broker site
    name_on_listing: str            # name as it appears on the broker
    phones: list[str]               # phone numbers on the listing
    emails: list[str]               # email addresses on the listing
    addresses: list[str]            # addresses on the listing
    age: Optional[str]
    relatives: list[str]
    priority: float                 # 0.0–1.0 — removal urgency based on PII exposure (see Priority Scoring)
    status: ListingStatus           # starts as "pending_review"
    removal_method: Optional[RemovalMethod]
    manual_instructions: Optional[str]  # populated if method=manual
    created_at: datetime
    updated_at: datetime
```

### Priority Scoring

The `priority` field on `FoundListing` indicates removal urgency based on what PII the listing exposes. Broker adapters must compute this using the following rules:

| PII Exposed | Score |
|---|---|
| Phone number or email address | 0.9–1.0 |
| Physical address (no phone/email) | 0.7–0.8 |
| Name + city/state only | 0.3–0.6 |

Scores stack toward 1.0: a listing with phone + email + address = 1.0.

The Review UI sorts listings by `priority` descending — phone/email matches are shown first.

---

### RemovalRequest
Created when user approves a listing for removal.

```python
class RemovalRequest(BaseModel):
    id: UUID
    listing_id: UUID
    user_id: UUID
    broker: str
    method: RemovalMethod
    submitted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    recheck_after: Optional[datetime]  # when to re-verify removal
    attempts: int                       # retry count
    last_error: Optional[str]
    status: ListingStatus               # mirrors listing status
```

### UserProfilePublic
What the API returns — PII decrypted for the authenticated user only. Never returned for other users.

```python
class UserProfilePublic(BaseModel):
    id: UUID
    email: str                      # decrypted, only returned to the owning user
    full_name: str                  # decrypted
    phone_numbers: list[str]        # decrypted
    email_addresses: list[str]      # decrypted
    addresses: list[str]            # decrypted
    age_range: Optional[str]        # decrypted
    relatives: list[str]            # decrypted
    created_at: datetime
    updated_at: datetime
    # Never returned: hashed_password, invite_code_used
```

### UserProfileUpdate
Fields accepted on PUT /api/profile. All optional — partial updates allowed.

```python
class UserProfileUpdate(BaseModel):
    full_name: Optional[str]
    phone_numbers: Optional[list[str]]
    email_addresses: Optional[list[str]]
    addresses: Optional[list[str]]
    age_range: Optional[str]
    relatives: Optional[list[str]]
```

### InviteCode

```python
class InviteCode(BaseModel):
    code: str                       # random 8-char alphanumeric
    created_by: UUID                # admin user id
    used_by: Optional[UUID]
    used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_used: bool
```

---

## Broker Adapter Interface

Every broker adapter must implement this interface. No exceptions.

Adapters connect to Browserbase for managed browser sessions (no local Chromium):
```python
browser = await playwright.chromium.connect_over_cdp(browserbase_ws_url)
```

```python
class BrokerAdapter:
    slug: str                       # e.g. "spokeo" — matches DB broker slug
    display_name: str               # e.g. "Spokeo"
    opt_out_url: str                # base opt-out URL for reference

    async def search(self, profile: UserProfile) -> list[FoundListing]:
        """
        Search broker for user's info.
        Returns list of FoundListing (status=pending_review).
        Returns empty list if no results found.
        Raises BrokerError on hard failure.
        Sets removal_method and manual_instructions if automation not possible.
        """
        ...

    async def submit_removal(self, listing: FoundListing) -> RemovalRequest:
        """
        Submit opt-out request for a listing.
        Returns RemovalRequest with status=removal_sent or failed.
        If CAPTCHA detected: set method=manual, populate manual_instructions.
        """
        ...

    async def verify_removal(self, request: RemovalRequest) -> RemovalRequest:
        """
        Re-check if listing has been removed.
        Updates status to confirmed or keeps as removal_sent.
        """
        ...

    # Class-level constants (set per adapter)
    timeout_seconds: int = 120      # per-operation timeout — MUST be respected
    rate_limit_rps: float = 0.5     # max requests per second to this broker
    requires_email_verify: bool     # True if broker sends a verification email
```

### BrokerError

```python
class BrokerError(Exception):
    broker: str
    reason: Literal["captcha", "blocked", "not_found", "timeout", "unknown"]
    message: str
    fallback_instructions: Optional[str]
```

---

## API Endpoints

### Auth

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password, invite_code}` | `{token: str, user: UserPublic}` |
| POST | `/api/auth/token` | `{email, password}` | `{token: str}` |
| GET | `/api/auth/me` | — | `UserPublic` |

### User Profile (PII)

| Method | Path | Request Body | Response |
|---|---|---|---|
| GET | `/api/profile` | — | `UserProfilePublic` |
| PUT | `/api/profile` | `UserProfileUpdate` | `UserProfilePublic` |

### Scans

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | `/api/scans` | `{brokers?: list[str]}` | `ScanJob` |
| GET | `/api/scans` | — | `list[ScanJob]` |
| GET | `/api/scans/{id}` | — | `ScanJob` |
| GET | `/api/scans/{id}/listings` | — | `list[FoundListing]` |

### Listings (Review Flow)

| Method | Path | Request Body | Response |
|---|---|---|---|
| PATCH | `/api/listings/{id}` | `{status: "approved" \| "skipped"}` | `FoundListing` |
| POST | `/api/listings/{id}/remove` | — | `RemovalRequest` |

### Removals

| Method | Path | Request Body | Response |
|---|---|---|---|
| GET | `/api/removals` | — | `list[RemovalRequest]` |
| GET | `/api/removals/{id}` | — | `RemovalRequest` |
| POST | `/api/removals/{id}/recheck` | — | `RemovalRequest` |

### Admin

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | `/api/admin/bootstrap` | `{email, password, admin_secret}` | `{token: str}` — **one-time use only, disabled after first call** |
| POST | `/api/admin/invites` | `{expires_in_days?: int}` | `{code: str}` |
| GET | `/api/admin/invites` | — | `list[InviteCode]` |
| GET | `/api/admin/brokers` | — | `list[BrokerStatus]` |

`/api/admin/bootstrap` requirements:
- Requires `ADMIN_BOOTSTRAP_SECRET` env var to match `admin_secret` in request
- Returns 410 Gone if an admin user already exists
- Creates first admin user and disables itself permanently

### Error Response (all endpoints)

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

Common codes: `UNAUTHORIZED`, `NOT_FOUND`, `INVALID_INVITE`, `BROKER_ERROR`, `CAPTCHA_REQUIRED`, `SCAN_ALREADY_RUNNING`, `BOOTSTRAP_ALREADY_DONE`

---

## Encryption Conventions

Fields marked `[ENCRYPTED]` in the models above are stored as Fernet ciphertext.

- Encryption key: `ENCRYPTION_KEY` env var (32-byte URL-safe base64 Fernet key)
- Encrypt on write, decrypt on read — never in SQL, never in logs
- `UserProfilePublic` (returned by API) decrypts fields for the authenticated user only
- No other user can ever receive another user's decrypted PII

---

## Scan Concurrency Rules

- Max 1 active scan per user at a time — enforced at `POST /api/scans` (returns 409 + `SCAN_ALREADY_RUNNING` if one is in progress)
- Broker adapters run concurrently within a scan: `asyncio.gather(*[adapter.search(profile) for adapter in adapters], return_exceptions=True)`
- Default concurrency limit: all Tier 1 brokers in parallel (max 5)
- Each adapter has its own `timeout_seconds` — a hung broker does not block others

---

## Versioning

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-03-29 | Initial contracts |
| 1.1 | 2026-03-29 | Added UserProfilePublic, UserProfileUpdate, per-broker timeout + rate_limit_rps, bootstrap endpoint, scan concurrency rules, SCAN_ALREADY_RUNNING error code |
| 1.2 | 2026-03-29 | Renamed `confidence` → `priority` on FoundListing; added Priority Scoring section (PII-exposure-based urgency) |
| 1.3 | 2026-03-29 | Broker adapters use Browserbase (managed Chromium) instead of local Playwright |
