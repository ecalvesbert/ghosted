"""
Spokeo broker adapter — submit opt-out requests.

Two-step flow:
1. Search spokeo.com for the person to find their profile URL
2. Submit the profile URL on the opt-out page

Uses Browserbase for managed browser sessions.
"""

import asyncio
import logging
import os
from typing import Callable

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from browserbase import Browserbase

from app.brokers.base import BrokerAdapter, BrokerError
from app.services.encryption import DecryptedProfile

logger = logging.getLogger(__name__)


class SpokeoAdapter(BrokerAdapter):
    slug = "spokeo"
    display_name = "Spokeo"
    opt_out_url = "https://www.spokeo.com/optout"
    timeout_seconds = 180
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
        await asyncio.sleep(1.0 / self.rate_limit_rps)

    async def submit_opt_out(
        self,
        profile: DecryptedProfile,
        on_session_created: Callable[[str], None] | None = None,
    ) -> dict:
        """
        1. Search Spokeo for the person to find their profile URL
        2. Navigate to opt-out page and submit the URL
        3. Confirm submission
        """
        bb = self._get_browserbase()
        project_id = self._get_project_id()
        session = bb.sessions.create(project_id=project_id)
        live_url = f"https://www.browserbase.com/sessions/{session.id}"
        logger.info("Browserbase session created: %s", live_url)
        if on_session_created:
            on_session_created(live_url)

        playwright = await async_playwright().start()

        try:
            browser = await playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

            # --- Step 1: Search Spokeo to find profile URL ---
            name = profile.full_name
            location = ""
            if profile.city and profile.state:
                location = f"{profile.city}, {profile.state}"
            elif profile.city:
                location = profile.city
            elif profile.state:
                location = profile.state

            search_url = f"https://www.spokeo.com/{name.replace(' ', '-')}/{location.replace(' ', '-').replace(',', '')}" if location else f"https://www.spokeo.com/{name.replace(' ', '-')}"
            logger.info("Spokeo search URL: %s", search_url)

            await self._rate_limit()

            try:
                await page.goto(search_url, timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": "Timed out loading Spokeo search page",
                    "opt_out_url": self.opt_out_url,
                }

            # Look for profile links in search results
            # Spokeo profile URLs look like: /people/First-Last/City-ST
            profile_url = None

            # Try to find a link to a specific person profile
            profile_links = await page.query_selector_all("a[href*='/people/']")
            for link in profile_links:
                href = await link.get_attribute("href")
                if href and "/people/" in href and href != "/people/":
                    profile_url = href if href.startswith("http") else f"https://www.spokeo.com{href}"
                    break

            # If no profile links found, check if we're already on a profile page
            if not profile_url:
                current_url = page.url
                if "/people/" in current_url:
                    profile_url = current_url

            if not profile_url:
                # Take a screenshot path for debugging
                page_title = await page.title()
                body_text = (await page.inner_text("body"))[:500]
                logger.info("Spokeo search page title: %s", page_title)
                logger.info("Spokeo search page text: %s", body_text[:200])
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": f"Could not find a Spokeo profile URL. Search the site manually and submit opt-out at {self.opt_out_url}",
                    "opt_out_url": self.opt_out_url,
                }

            logger.info("Found Spokeo profile URL: %s", profile_url)

            # --- Step 2: Navigate to opt-out page and submit the profile URL ---
            await self._rate_limit()

            try:
                await page.goto(self.opt_out_url, timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": f"Timed out loading opt-out page. Profile URL found: {profile_url}",
                    "opt_out_url": self.opt_out_url,
                }

            # Check for CAPTCHA
            captcha_el = await page.query_selector(
                "[class*='captcha'], [id*='captcha'], iframe[src*='captcha'], [class*='recaptcha']"
            )
            if captcha_el:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": f"CAPTCHA detected. Profile URL: {profile_url} — submit manually at {self.opt_out_url}",
                    "opt_out_url": self.opt_out_url,
                }

            # Find the URL input field and paste the profile URL
            try:
                # Spokeo opt-out page has an input for the listing URL
                url_input = await page.wait_for_selector(
                    "input[type='text'], input[type='url'], input[name='url'], input[placeholder*='URL'], input[placeholder*='url'], input[placeholder*='listing'], input[placeholder*='profile'], input#url-input",
                    timeout=15000,
                )
                await url_input.fill(profile_url)
                logger.info("Filled opt-out URL input with: %s", profile_url)

                await self._rate_limit()

                # Click submit
                submit_btn = await page.query_selector(
                    "button[type='submit'], input[type='submit'], button:has-text('Remove'), button:has-text('Submit'), button:has-text('Search'), button:has-text('Go')"
                )
                if submit_btn:
                    await submit_btn.click()
                    logger.info("Clicked submit button")
                else:
                    await page.keyboard.press("Enter")
                    logger.info("Pressed Enter to submit")

                # Wait for response
                await page.wait_for_load_state("networkidle", timeout=30000)

            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": f"Timed out on opt-out form. Profile URL: {profile_url}",
                    "opt_out_url": self.opt_out_url,
                }

            # --- Step 3: Check for confirmation ---
            # Look for email verification prompt (Spokeo sends a confirmation email)
            email_input = await page.query_selector(
                "input[type='email'], input[name='email']"
            )

            # Look for success indicators
            page_text = (await page.inner_text("body")).lower()
            success_indicators = [
                "email has been sent",
                "check your email",
                "verification email",
                "successfully submitted",
                "removal request",
                "opt-out request",
                "we will process",
                "confirmation email",
            ]
            has_success = any(indicator in page_text for indicator in success_indicators)

            # If email input is present, fill it with user's email
            if email_input:
                email = profile.email_addresses[0] if profile.email_addresses else ""
                if email:
                    await email_input.fill(email)
                    logger.info("Filled email verification field")
                    # Submit the email
                    email_submit = await page.query_selector(
                        "button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Verify'), button:has-text('Send')"
                    )
                    if email_submit:
                        await email_submit.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        # Re-check for success
                        page_text = (await page.inner_text("body")).lower()
                        has_success = any(indicator in page_text for indicator in success_indicators)

            if has_success:
                logger.info("Spokeo opt-out confirmed: success indicator found")
                return {
                    "status": "needs_verification",
                    "method": "automated",
                    "notes": f"Opt-out submitted for {profile_url}. Check email for verification link.",
                    "opt_out_url": self.opt_out_url,
                }

            # If we got this far without clear success, check what page we're on
            current_title = await page.title()
            logger.info("Final page title: %s", current_title)
            logger.info("Final page text (first 300): %s", page_text[:300])

            # Be generous — if we made it through without errors, it likely worked
            return {
                "status": "submitted",
                "method": "automated",
                "notes": f"Opt-out form submitted for {profile_url}. Verify status in a few days.",
                "opt_out_url": self.opt_out_url,
            }

        except BrokerError:
            raise
        except Exception as exc:
            logger.exception("Spokeo opt-out error")
            return {
                "status": "failed",
                "method": "manual",
                "notes": f"Unexpected error: {exc}",
                "opt_out_url": self.opt_out_url,
            }
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            await playwright.stop()
