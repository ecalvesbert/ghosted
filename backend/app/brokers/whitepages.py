"""
Whitepages broker adapter — submit opt-out requests.

Flow:
1. Navigate to whitepages.com/suppression-requests
2. Search for the person by name + city/state
3. Find matching profile in results and select it
4. Confirm removal request

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


class WhitepagesAdapter(BrokerAdapter):
    slug = "whitepages"
    display_name = "Whitepages"
    opt_out_url = "https://www.whitepages.com/suppression-requests"
    timeout_seconds = 180
    rate_limit_rps = 0.5
    requires_email_verify = False

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
        bb = self._get_browserbase()
        project_id = self._get_project_id()
        session = bb.sessions.create(project_id=project_id)

        # Get interactive debug URL (not the passive dashboard viewer)
        try:
            debug_info = bb.sessions.debug(session.id)
            live_url = debug_info.debugger_fullscreen_url
        except Exception:
            live_url = f"https://www.browserbase.com/sessions/{session.id}"
        logger.info("Browserbase session created: %s", live_url)
        if on_session_created:
            on_session_created(live_url)

        playwright = await async_playwright().start()

        try:
            browser = await playwright.chromium.connect_over_cdp(session.connect_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

            # --- Step 1: Navigate to suppression request page ---
            await self._rate_limit()

            try:
                await page.goto(self.opt_out_url, timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": "Timed out loading Whitepages suppression page",
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
                    "notes": f"CAPTCHA detected — submit manually at {self.opt_out_url}",
                    "opt_out_url": self.opt_out_url,
                }

            # --- Step 2: Fill the search form ---
            name = profile.full_name
            location = ""
            if profile.city and profile.state:
                location = f"{profile.city}, {profile.state}"
            elif profile.city:
                location = profile.city
            elif profile.state:
                location = profile.state

            # Whitepages suppression page typically has name + location fields
            try:
                # Try to find the name input
                name_input = await page.wait_for_selector(
                    "input[name='firstName'], input[name='name'], input[placeholder*='name' i], input[placeholder*='Name'], input[aria-label*='name' i], input[type='text']:first-of-type",
                    timeout=15000,
                )

                # Check if there are separate first/last name fields
                first_name_input = await page.query_selector(
                    "input[name='firstName'], input[placeholder*='first' i], input[aria-label*='first' i]"
                )
                last_name_input = await page.query_selector(
                    "input[name='lastName'], input[placeholder*='last' i], input[aria-label*='last' i]"
                )

                name_parts = name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                if first_name_input and last_name_input:
                    await first_name_input.fill(first_name)
                    await last_name_input.fill(last_name)
                    logger.info("Filled first/last name fields")
                else:
                    await name_input.fill(name)
                    logger.info("Filled single name field")

                # Fill location/city/state
                location_input = await page.query_selector(
                    "input[name='city'], input[name='location'], input[placeholder*='city' i], input[placeholder*='location' i], input[aria-label*='city' i], input[aria-label*='location' i]"
                )
                if location_input and location:
                    await location_input.fill(location)
                    logger.info("Filled location field: %s", location)

                # Also check for separate state field
                state_input = await page.query_selector(
                    "select[name='state'], input[name='state'], select[aria-label*='state' i]"
                )
                if state_input and profile.state:
                    tag = await state_input.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        await state_input.select_option(label=profile.state)
                    else:
                        await state_input.fill(profile.state)
                    logger.info("Filled state field")

            except PlaywrightTimeout:
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": f"Could not find search form on suppression page",
                    "opt_out_url": self.opt_out_url,
                }

            await self._rate_limit()

            # Submit the search
            submit_btn = await page.query_selector(
                "button[type='submit'], input[type='submit'], button:has-text('Search'), button:has-text('Find'), button:has-text('Submit'), button:has-text('Go')"
            )
            if submit_btn:
                await submit_btn.click()
                logger.info("Clicked search button")
            else:
                await page.keyboard.press("Enter")
                logger.info("Pressed Enter to search")

            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeout:
                pass  # Continue anyway, page may still be usable

            # --- Step 3: Find matching profile in results ---
            await asyncio.sleep(2)  # Brief pause for dynamic content

            page_text = (await page.inner_text("body")).lower()

            # Check if we landed on results or a confirmation
            error_indicators = [
                "no results",
                "no records found",
                "we couldn't find",
                "0 results",
            ]
            if any(indicator in page_text for indicator in error_indicators):
                return {
                    "status": "failed",
                    "method": "manual",
                    "notes": f"No Whitepages listing found for {name}. Try different name variations at {self.opt_out_url}",
                    "opt_out_url": self.opt_out_url,
                }

            # Look for remove/opt-out buttons in search results
            remove_btn = await page.query_selector(
                "button:has-text('Remove'), a:has-text('Remove'), button:has-text('Opt out'), a:has-text('Opt out'), "
                "button:has-text('Select'), a:has-text('Select'), "
                "button:has-text('This is me'), a:has-text('This is me'), "
                "[data-testid*='remove'], [data-testid*='select']"
            )

            if remove_btn:
                await self._rate_limit()
                await remove_btn.click()
                logger.info("Clicked remove/select button on result")

                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except PlaywrightTimeout:
                    pass

                await asyncio.sleep(2)
            else:
                # Try clicking the first result link
                result_link = await page.query_selector(
                    "a[href*='/suppression'], a[href*='remove'], .result a, .listing a, [class*='result'] a"
                )
                if result_link:
                    await self._rate_limit()
                    await result_link.click()
                    logger.info("Clicked first result link")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=30000)
                    except PlaywrightTimeout:
                        pass
                    await asyncio.sleep(2)

            # --- Step 4: Handle removal confirmation/phone verification ---
            # Whitepages may ask for phone number to verify identity
            phone_input = await page.query_selector(
                "input[type='tel'], input[name='phone'], input[placeholder*='phone' i], input[aria-label*='phone' i]"
            )
            if phone_input and profile.phone_numbers:
                await phone_input.fill(profile.phone_numbers[0])
                logger.info("Filled phone verification field")
                confirm_btn = await page.query_selector(
                    "button[type='submit'], button:has-text('Verify'), button:has-text('Submit'), button:has-text('Confirm'), button:has-text('Continue')"
                )
                if confirm_btn:
                    await confirm_btn.click()
                    try:
                        await page.wait_for_load_state("networkidle", timeout=30000)
                    except PlaywrightTimeout:
                        pass

            # Check for email input
            email_input = await page.query_selector(
                "input[type='email'], input[name='email'], input[placeholder*='email' i]"
            )
            if email_input and profile.email_addresses:
                await email_input.fill(profile.email_addresses[0])
                logger.info("Filled email field")
                confirm_btn = await page.query_selector(
                    "button[type='submit'], button:has-text('Submit'), button:has-text('Confirm'), button:has-text('Continue')"
                )
                if confirm_btn:
                    await confirm_btn.click()
                    try:
                        await page.wait_for_load_state("networkidle", timeout=30000)
                    except PlaywrightTimeout:
                        pass

            # Look for any remaining confirmation buttons
            final_confirm = await page.query_selector(
                "button:has-text('Confirm'), button:has-text('Remove'), button:has-text('Yes'), "
                "button:has-text('Submit'), button:has-text('Complete')"
            )
            if final_confirm:
                await final_confirm.click()
                logger.info("Clicked final confirmation button")
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeout:
                    pass

            # --- Step 5: Check for success ---
            page_text = (await page.inner_text("body")).lower()
            success_indicators = [
                "successfully",
                "has been submitted",
                "request received",
                "opt-out request",
                "removal request",
                "we will process",
                "been removed",
                "suppression request",
                "check your email",
                "verification email",
                "within 24 hours",
                "within 48 hours",
                "thank you",
            ]
            has_success = any(indicator in page_text for indicator in success_indicators)

            if has_success:
                logger.info("Whitepages opt-out confirmed: success indicator found")
                return {
                    "status": "submitted",
                    "method": "automated",
                    "notes": f"Removal request submitted for {name} on Whitepages.",
                    "opt_out_url": self.opt_out_url,
                }

            # If we got through without errors, assume partial success
            current_url = page.url
            current_title = await page.title()
            logger.info("Final page: %s - %s", current_url, current_title)
            logger.info("Final page text (first 300): %s", page_text[:300])

            return {
                "status": "submitted",
                "method": "automated",
                "notes": f"Opt-out form navigated for {name}. Verify removal in a few days.",
                "opt_out_url": self.opt_out_url,
            }

        except BrokerError:
            raise
        except Exception as exc:
            logger.exception("Whitepages opt-out error")
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
