"""
Spokeo broker adapter — search, submit opt-out, and verify removal.

Uses Browserbase for managed browser sessions. CSS selectors are based on
Spokeo's page structure as of early 2026 and may need updating after live testing.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from browserbase import Browserbase

from app.brokers.base import BrokerAdapter, BrokerError
from app.models.listing import FoundListing
from app.models.removal import RemovalRequest
from app.services.encryption import DecryptedProfile

logger = logging.getLogger(__name__)


def _compute_priority(phones: list[str], emails: list[str], addresses: list[str]) -> float:
    """Compute removal-urgency priority per CONTRACTS.md Priority Scoring."""
    has_phone = len(phones) > 0
    has_email = len(emails) > 0
    has_address = len(addresses) > 0

    if has_phone and has_email and has_address:
        return 1.0
    if has_phone and has_email:
        return 0.95
    if has_phone or has_email:
        return 0.9
    if has_address:
        return 0.75
    # Name + city/state only
    return 0.5


def _parse_city_state(address: str) -> Optional[tuple[str, str]]:
    """Try to extract city and state from an address string like '123 Main St, Austin, TX 78701'."""
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 2:
        # Last part likely has state (and maybe zip)
        state_part = parts[-1].split()
        city = parts[-2] if len(parts) >= 3 else parts[0]
        state = state_part[0] if state_part else ""
        if len(state) == 2 and state.isalpha():
            return city, state
    return None


class SpokeoAdapter(BrokerAdapter):
    slug = "spokeo"
    display_name = "Spokeo"
    opt_out_url = "https://www.spokeo.com/optout"
    timeout_seconds = 120
    rate_limit_rps = 0.5
    requires_email_verify = True

    def _get_browserbase(self) -> Browserbase:
        api_key = os.getenv("BROWSERBASE_API_KEY")
        if not api_key:
            raise BrokerError(
                broker=self.slug,
                reason="unknown",
                message="BROWSERBASE_API_KEY not configured",
            )
        return Browserbase(api_key=api_key)

    def _get_project_id(self) -> str:
        project_id = os.getenv("BROWSERBASE_PROJECT_ID")
        if not project_id:
            raise BrokerError(
                broker=self.slug,
                reason="unknown",
                message="BROWSERBASE_PROJECT_ID not configured",
            )
        return project_id

    async def _rate_limit(self) -> None:
        """Enforce rate_limit_rps = 0.5 → sleep 2 seconds between requests."""
        await asyncio.sleep(1.0 / self.rate_limit_rps)

    async def search(self, profile: DecryptedProfile) -> list[FoundListing]:
        """Search Spokeo for listings matching the decrypted profile."""
        bb = self._get_browserbase()
        project_id = self._get_project_id()
        session = bb.sessions.create(project_id=project_id)
        logger.info("Browserbase session created: https://browserbase.com/sessions/%s", session.id)

        playwright = await async_playwright().start()
        listings: list[FoundListing] = []

        try:
            browser = await playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

            # Build search query: "First Last" + city/state
            name = profile.full_name
            location_suffix = ""
            if profile.city and profile.state:
                location_suffix = f", {profile.city}, {profile.state}"
            elif profile.city:
                location_suffix = f", {profile.city}"
            elif profile.state:
                location_suffix = f", {profile.state}"

            search_url = f"https://www.spokeo.com/search?q={name.replace(' ', '+')}{location_suffix.replace(' ', '+').replace(',', '%2C')}"

            await self._rate_limit()
            try:
                await page.goto(search_url, timeout=self.timeout_seconds * 1000)
            except PlaywrightTimeout:
                raise BrokerError(
                    broker=self.slug,
                    reason="timeout",
                    message=f"Timed out loading Spokeo search after {self.timeout_seconds}s",
                )

            # Check for CAPTCHA
            # NOTE: Selector may need updating based on live testing
            captcha_el = await page.query_selector("[class*='captcha'], [id*='captcha'], iframe[src*='captcha']")
            if captcha_el:
                raise BrokerError(
                    broker=self.slug,
                    reason="captcha",
                    message="CAPTCHA detected on Spokeo search page",
                    fallback_instructions=(
                        "1. Go to https://www.spokeo.com\n"
                        "2. Search for your name manually\n"
                        "3. Note the listing URLs and submit them through the app"
                    ),
                )

            # Check for no results
            # NOTE: Selector may need updating based on live testing
            no_results = await page.query_selector(".no-results, [class*='NoResults'], [data-testid='no-results']")
            if no_results:
                return []

            # Parse result cards
            # NOTE: Selectors are approximate — update after live testing against Spokeo's DOM
            result_cards = await page.query_selector_all(
                ".result-card, [class*='PersonCard'], [data-testid='result-card'], .search-result"
            )

            for card in result_cards:
                try:
                    # Extract listing URL
                    link_el = await card.query_selector("a[href*='/people/'], a[href*='/search/']")
                    listing_url = ""
                    if link_el:
                        href = await link_el.get_attribute("href")
                        listing_url = f"https://www.spokeo.com{href}" if href and not href.startswith("http") else (href or "")

                    if not listing_url:
                        continue

                    # Extract name
                    name_el = await card.query_selector(
                        ".result-name, [class*='name'], [data-testid='result-name'], h2, h3"
                    )
                    name_on_listing = (await name_el.inner_text()).strip() if name_el else "Unknown"

                    # Extract age
                    age_el = await card.query_selector(
                        ".result-age, [class*='age'], [data-testid='age']"
                    )
                    age = None
                    if age_el:
                        age_text = (await age_el.inner_text()).strip()
                        # Extract just the number/range, e.g. "Age: 35" -> "35"
                        age = age_text.replace("Age:", "").replace("age:", "").strip()

                    # Extract location/addresses
                    addr_els = await card.query_selector_all(
                        ".result-location, [class*='location'], [class*='address'], [data-testid='location']"
                    )
                    found_addresses = []
                    for el in addr_els:
                        text = (await el.inner_text()).strip()
                        if text:
                            found_addresses.append(text)

                    # Extract phone numbers (often behind a paywall on Spokeo, but partial may show)
                    phone_els = await card.query_selector_all(
                        ".result-phone, [class*='phone'], [data-testid='phone']"
                    )
                    found_phones = []
                    for el in phone_els:
                        text = (await el.inner_text()).strip()
                        if text and any(c.isdigit() for c in text):
                            found_phones.append(text)

                    # Extract email addresses
                    email_els = await card.query_selector_all(
                        ".result-email, [class*='email'], [data-testid='email']"
                    )
                    found_emails = []
                    for el in email_els:
                        text = (await el.inner_text()).strip()
                        if text and "@" in text:
                            found_emails.append(text)

                    # Extract relatives
                    relative_els = await card.query_selector_all(
                        ".result-relative, [class*='relative'], [data-testid='relative']"
                    )
                    found_relatives = []
                    for el in relative_els:
                        text = (await el.inner_text()).strip()
                        if text:
                            found_relatives.append(text)

                    priority = _compute_priority(found_phones, found_emails, found_addresses)

                    listing = FoundListing(
                        id=uuid.uuid4(),
                        scan_job_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # Set by caller
                        user_id=profile.id,
                        broker=self.slug,
                        listing_url=listing_url,
                        name_on_listing=name_on_listing,
                        phones=found_phones,
                        emails=found_emails,
                        addresses=found_addresses,
                        age=age,
                        relatives=found_relatives,
                        priority=priority,
                        status="pending_review",
                    )
                    listings.append(listing)

                except Exception:
                    # Skip individual card parsing failures, continue with next
                    logger.warning("Failed to parse a Spokeo result card, skipping", exc_info=True)
                    continue

        except BrokerError:
            raise
        except PlaywrightTimeout:
            raise BrokerError(
                broker=self.slug,
                reason="timeout",
                message=f"Spokeo search timed out after {self.timeout_seconds}s",
            )
        except Exception as exc:
            raise BrokerError(
                broker=self.slug,
                reason="unknown",
                message=f"Unexpected error during Spokeo search: {exc}",
            )
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            await playwright.stop()

        return listings

    async def submit_removal(self, listing: FoundListing) -> RemovalRequest:
        """Submit an opt-out request via Spokeo's opt-out page."""
        bb = self._get_browserbase()
        project_id = self._get_project_id()
        session = bb.sessions.create(project_id=project_id)

        playwright = await async_playwright().start()
        now = datetime.now(timezone.utc)

        try:
            browser = await playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

            await self._rate_limit()

            try:
                await page.goto(self.opt_out_url, timeout=self.timeout_seconds * 1000)
            except PlaywrightTimeout:
                return RemovalRequest(
                    id=uuid.uuid4(),
                    listing_id=listing.id,
                    user_id=listing.user_id,
                    broker=self.slug,
                    method="manual",
                    submitted_at=now,
                    attempts=1,
                    last_error="Timed out loading opt-out page",
                    status="failed",
                )

            # Check for CAPTCHA on opt-out page
            captcha_el = await page.query_selector("[class*='captcha'], [id*='captcha'], iframe[src*='captcha']")
            if captcha_el:
                return RemovalRequest(
                    id=uuid.uuid4(),
                    listing_id=listing.id,
                    user_id=listing.user_id,
                    broker=self.slug,
                    method="manual",
                    submitted_at=now,
                    attempts=1,
                    last_error="CAPTCHA on opt-out page",
                    status="failed",
                )

            # Spokeo opt-out flow:
            # 1. Enter the listing URL into the search/input field
            # 2. Click search/submit
            # 3. Confirm the listing
            # 4. Enter email for verification
            # NOTE: Selectors are approximate — update after live testing
            try:
                # Step 1: Enter listing URL
                url_input = await page.wait_for_selector(
                    "input[name='url'], input[placeholder*='listing'], input[type='text'], #url-input",
                    timeout=15000,
                )
                await url_input.fill(listing.listing_url)

                await self._rate_limit()

                # Step 2: Submit the URL
                submit_btn = await page.query_selector(
                    "button[type='submit'], input[type='submit'], .optout-submit, [data-testid='submit']"
                )
                if submit_btn:
                    await submit_btn.click()
                else:
                    await page.keyboard.press("Enter")

                # Step 3: Wait for confirmation or email step
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Check for email verification prompt
                email_prompt = await page.query_selector(
                    "input[type='email'], input[name='email'], [class*='email-verify'], [data-testid='email-input']"
                )

                requires_email = email_prompt is not None

                # Check if removal was submitted successfully
                # Look for success messaging
                success_el = await page.query_selector(
                    "[class*='success'], [class*='confirm'], [data-testid='success'], .optout-success"
                )

                if success_el or email_prompt:
                    return RemovalRequest(
                        id=uuid.uuid4(),
                        listing_id=listing.id,
                        user_id=listing.user_id,
                        broker=self.slug,
                        method="automated",
                        submitted_at=now,
                        recheck_after=now + timedelta(days=3),
                        attempts=1,
                        status="removal_sent",
                    )
                else:
                    # Could not confirm submission — fall back to manual
                    return RemovalRequest(
                        id=uuid.uuid4(),
                        listing_id=listing.id,
                        user_id=listing.user_id,
                        broker=self.slug,
                        method="manual",
                        submitted_at=now,
                        attempts=1,
                        last_error="Could not confirm opt-out submission — page structure may have changed",
                        status="failed",
                    )

            except PlaywrightTimeout:
                # Opt-out form interaction timed out — provide manual instructions
                return RemovalRequest(
                    id=uuid.uuid4(),
                    listing_id=listing.id,
                    user_id=listing.user_id,
                    broker=self.slug,
                    method="manual",
                    submitted_at=now,
                    attempts=1,
                    last_error="Timed out interacting with opt-out form",
                    status="failed",
                )

        except Exception as exc:
            return RemovalRequest(
                id=uuid.uuid4(),
                listing_id=listing.id,
                user_id=listing.user_id,
                broker=self.slug,
                method="manual",
                submitted_at=now,
                attempts=1,
                last_error=f"Unexpected error: {exc}",
                status="failed",
            )
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            await playwright.stop()

    async def verify_removal(self, request: RemovalRequest) -> RemovalRequest:
        """Re-visit the original listing URL and check if it has been removed."""
        bb = self._get_browserbase()
        project_id = self._get_project_id()
        session = bb.sessions.create(project_id=project_id)

        playwright = await async_playwright().start()

        try:
            browser = await playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

            # Look up the listing URL from the associated FoundListing
            # The caller should ensure request has a reference; we need the listing URL.
            # For now we navigate using a URL constructed from the listing_id.
            # In practice, the scan engine should pass the FoundListing or attach the URL.
            # We'll use a helper query — but since we don't have DB access here,
            # the caller must set listing_url on the request or pass the listing.
            # Fallback: construct from Spokeo's URL pattern.
            listing_url = getattr(request, "_listing_url", None)
            if not listing_url:
                # Caller should attach this; raise if missing
                raise BrokerError(
                    broker=self.slug,
                    reason="unknown",
                    message="Cannot verify removal: listing URL not available on RemovalRequest. "
                            "The scan engine must attach _listing_url before calling verify_removal.",
                )

            await self._rate_limit()

            try:
                response = await page.goto(listing_url, timeout=self.timeout_seconds * 1000)
            except PlaywrightTimeout:
                # Can't verify — keep current status
                request.attempts = (request.attempts or 0) + 1
                request.last_error = "Timed out loading listing page for verification"
                request.recheck_after = datetime.now(timezone.utc) + timedelta(days=1)
                return request

            # Check if page returns 404 or shows "not found" message
            is_removed = False

            if response and response.status == 404:
                is_removed = True
            else:
                # Check for "profile not found" or "removed" messaging
                # NOTE: Selectors may need updating based on live testing
                not_found_el = await page.query_selector(
                    "[class*='not-found'], [class*='removed'], [data-testid='not-found'], .profile-removed"
                )
                if not_found_el:
                    is_removed = True

                # Also check if the page content indicates no listing
                body_text = await page.inner_text("body")
                removal_indicators = [
                    "this profile has been removed",
                    "no results found",
                    "page not found",
                    "this listing is no longer available",
                ]
                if any(indicator in body_text.lower() for indicator in removal_indicators):
                    is_removed = True

            now = datetime.now(timezone.utc)
            request.attempts = (request.attempts or 0) + 1

            if is_removed:
                request.status = "confirmed"
                request.confirmed_at = now
            else:
                # Still there — schedule another recheck
                request.recheck_after = now + timedelta(days=2)

            return request

        except BrokerError:
            raise
        except Exception as exc:
            request.attempts = (request.attempts or 0) + 1
            request.last_error = f"Verification error: {exc}"
            request.recheck_after = datetime.now(timezone.utc) + timedelta(days=1)
            return request
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            await playwright.stop()
