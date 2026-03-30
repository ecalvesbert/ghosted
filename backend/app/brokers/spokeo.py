"""
Spokeo broker adapter — submit opt-out requests.

Uses Browserbase for managed browser sessions. CSS selectors are based on
Spokeo's page structure as of early 2026 and may need updating after live testing.
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
        """Enforce rate_limit_rps = 0.5 -> sleep 2 seconds between requests."""
        await asyncio.sleep(1.0 / self.rate_limit_rps)

    async def submit_opt_out(
        self,
        profile: DecryptedProfile,
        on_session_created: Callable[[str], None] | None = None,
    ) -> dict:
        """Navigate to Spokeo opt-out page, fill in profile info, and submit."""
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

            await self._rate_limit()

            try:
                await page.goto(self.opt_out_url, timeout=self.timeout_seconds * 1000)
            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": "Timed out loading opt-out page",
                    "opt_out_url": self.opt_out_url,
                }

            # Check for CAPTCHA on opt-out page
            captcha_el = await page.query_selector(
                "[class*='captcha'], [id*='captcha'], iframe[src*='captcha']"
            )
            if captcha_el:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": "CAPTCHA detected on opt-out page",
                    "opt_out_url": self.opt_out_url,
                }

            # Spokeo opt-out flow:
            # 1. Search for the person on the opt-out page or paste profile URL
            # 2. Confirm the listing
            # 3. Enter email for verification
            # NOTE: Selectors are approximate -- update after live testing
            try:
                # Build search query from profile
                name = profile.full_name
                location_suffix = ""
                if profile.city and profile.state:
                    location_suffix = f", {profile.city}, {profile.state}"
                elif profile.city:
                    location_suffix = f", {profile.city}"
                elif profile.state:
                    location_suffix = f", {profile.state}"

                search_query = f"{name}{location_suffix}"

                # Step 1: Enter search query into the opt-out form
                url_input = await page.wait_for_selector(
                    "input[name='url'], input[placeholder*='listing'], input[type='text'], #url-input, input[name='search']",
                    timeout=15000,
                )
                await url_input.fill(search_query)

                await self._rate_limit()

                # Step 2: Submit the search
                submit_btn = await page.query_selector(
                    "button[type='submit'], input[type='submit'], .optout-submit, [data-testid='submit']"
                )
                if submit_btn:
                    await submit_btn.click()
                else:
                    await page.keyboard.press("Enter")

                # Step 3: Wait for results / confirmation
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Check for email verification prompt
                email_prompt = await page.query_selector(
                    "input[type='email'], input[name='email'], [class*='email-verify'], [data-testid='email-input']"
                )

                # Check if opt-out was submitted successfully
                success_el = await page.query_selector(
                    "[class*='success'], [class*='confirm'], [data-testid='success'], .optout-success"
                )

                if success_el or email_prompt:
                    status = "needs_verification" if email_prompt else "submitted"
                    return {
                        "status": status,
                        "method": "automated",
                        "notes": "Opt-out submitted via Spokeo opt-out page",
                        "opt_out_url": self.opt_out_url,
                    }
                else:
                    return {
                        "status": "failed",
                        "method": "manual",
                        "notes": "Could not confirm opt-out submission -- page structure may have changed",
                        "opt_out_url": self.opt_out_url,
                    }

            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": "Timed out interacting with opt-out form",
                    "opt_out_url": self.opt_out_url,
                }

        except BrokerError:
            raise
        except Exception as exc:
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
