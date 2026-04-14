"""
scraper.py — Core scraping engine for Google Maps Business Leads.

Uses Playwright to automate Google Maps, scroll through results, and extract
structured business data with full anti-detection and retry logic.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from fake_useragent import UserAgent
from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import (
    BROWSER_TIMEOUT,
    GEOLOCATION,
    HEADLESS,
    LOCALE,
    MAX_RESULTS,
    PROXY_SERVER,
    SELECTORS,
    SLOW_MO,
    TIMEZONE,
    USE_STEALTH,
    VIEWPORT,
)
from utils.helpers import (
    clean_text,
    extract_number,
    extract_rating,
    human_delay,
    inject_stealth,
    log,
    random_scroll,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BusinessLead:
    """Represents a single scraped business listing."""

    business_name: str = ""
    address: str = ""
    phone: str = ""
    website: str = ""
    rating: float | None = None
    reviews_count: int | None = None
    category: str = ""
    plus_code: str = ""
    google_maps_url: str = ""

    def is_valid(self) -> bool:
        return bool(self.business_name.strip())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Scraper class
# ---------------------------------------------------------------------------

class GoogleMapsScraper:
    """
    Async Playwright-based scraper for Google Maps business listings.

    Usage:
        async with GoogleMapsScraper() as scraper:
            leads = await scraper.scrape("plumbers in Chicago")
    """

    MAPS_URL = "https://www.google.com/maps"

    def __init__(
        self,
        search_query: str | None = None,
        max_results: int = MAX_RESULTS,
        headless: bool = HEADLESS,
    ) -> None:
        self.search_query = search_query
        self.max_results = max_results
        self.headless = headless

        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._leads: list[BusinessLead] = []

    # -- async context manager -----------------------------------------------

    async def __aenter__(self) -> "GoogleMapsScraper":
        self._playwright = await async_playwright().start()
        await self._launch_browser()
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        log.info("Browser closed")

    # -- browser setup -------------------------------------------------------

    async def _launch_browser(self) -> None:
        """Launch Chromium with stealth and anti-detection settings."""
        ua = UserAgent(browsers=["chrome"])

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        browser_kwargs: dict[str, Any] = {
            "headless": self.headless,
            "slow_mo": SLOW_MO,
            "args": launch_args,
        }

        if PROXY_SERVER:
            browser_kwargs["proxy"] = {"server": PROXY_SERVER}

        browser = await self._playwright.chromium.launch(**browser_kwargs)  # type: ignore[union-attr]

        context_kwargs: dict[str, Any] = {
            "viewport": VIEWPORT,
            "user_agent": ua.random,
            "locale": LOCALE,
            "timezone_id": TIMEZONE,
            "permissions": ["geolocation"],
            "java_script_enabled": True,
        }

        if GEOLOCATION:
            context_kwargs["geolocation"] = GEOLOCATION

        self._context = await browser.new_context(**context_kwargs)
        self._context.set_default_timeout(BROWSER_TIMEOUT)

        self._page = await self._context.new_page()

        if USE_STEALTH:
            await inject_stealth(self._page)

        log.info(
            f"[cyan]Browser launched[/cyan] · headless={self.headless} "
            f"· viewport={VIEWPORT['width']}×{VIEWPORT['height']}"
        )

    # -- navigation ----------------------------------------------------------

    async def _navigate_to_maps(self) -> None:
        """Navigate to Google Maps and wait for readiness."""
        page = self._page
        assert page is not None

        await page.goto(self.MAPS_URL, wait_until="networkidle")
        await human_delay(1.0, 2.0)

        # Dismiss the consent dialog if it appears (GDPR regions)
        try:
            accept_btn = page.locator("button", has_text="Accept all")
            if await accept_btn.count() > 0:
                await accept_btn.first.click()
                await human_delay(0.5, 1.0)
                log.debug("Consent dialog dismissed")
        except Exception:
            pass

    async def _perform_search(self, query: str) -> None:
        """Type the query into the search box and submit."""
        page = self._page
        assert page is not None

        search_box = page.locator(SELECTORS["search_box"])
        await search_box.click()
        await human_delay(0.3, 0.6)

        # Clear existing text
        await search_box.fill("")
        await human_delay(0.2, 0.4)

        # Type like a human
        await search_box.type(query, delay=random_typing_delay())
        await human_delay(0.5, 1.0)

        await page.locator(SELECTORS["search_button"]).click()
        await human_delay(2.0, 3.5)

        log.info(f"[yellow]Searching:[/yellow] {query}")

    # -- scrolling & collecting URLs -----------------------------------------

    async def _scroll_results(self) -> list[str]:
        """
        Scroll the results feed until we collect enough listing URLs
        or reach the end of the feed.
        """
        page = self._page
        assert page is not None

        collected_urls: list[str] = []
        previous_count = 0
        stale_rounds = 0
        max_stale = 8  # stop after 8 rounds with no new results

        log.info(f"Scrolling for up to {self.max_results} results …")

        while len(collected_urls) < self.max_results:
            # Scroll the feed container
            feed = page.locator(SELECTORS["result_feed"])
            if await feed.count() == 0:
                log.warning("Result feed not found — stopping scroll")
                break

            await feed.evaluate(
                "el => el.scrollTo(0, el.scrollHeight)"
            )
            await human_delay(1.5, 2.5)

            # Check for "end of list" marker
            end_marker = page.locator("span.HlvSq")
            if await end_marker.count() > 0:
                log.info("Reached end of results list")
                break

            # Collect hrefs from result links
            links = page.locator(SELECTORS["result_item"])
            count = await links.count()

            for i in range(count):
                href = await links.nth(i).get_attribute("href")
                if href and href not in collected_urls:
                    collected_urls.append(href)

            if len(collected_urls) == previous_count:
                stale_rounds += 1
                if stale_rounds >= max_stale:
                    log.info("No new results after multiple scrolls — stopping")
                    break
            else:
                stale_rounds = 0

            previous_count = len(collected_urls)
            log.debug(f"Collected {len(collected_urls)} URLs so far")

        # Trim to max_results
        return collected_urls[: self.max_results]

    # -- detail extraction ---------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _extract_lead(self, url: str) -> BusinessLead | None:
        """
        Navigate to a single listing page and scrape all available fields.
        """
        page = self._page
        assert page is not None

        await page.goto(url, wait_until="domcontentloaded")
        await human_delay(1.5, 2.5)

        lead = BusinessLead(google_maps_url=url)

        # Business name
        try:
            name_el = page.locator(SELECTORS["business_name"])
            if await name_el.count() > 0:
                lead.business_name = clean_text(await name_el.first.inner_text())
        except Exception:
            pass

        # Rating
        try:
            rating_el = page.locator(SELECTORS["rating"])
            if await rating_el.count() > 0:
                lead.rating = extract_rating(await rating_el.first.inner_text())
        except Exception:
            pass

        # Reviews count
        try:
            reviews_el = page.locator(SELECTORS["reviews_count"])
            if await reviews_el.count() > 0:
                aria = await reviews_el.first.get_attribute("aria-label")
                lead.reviews_count = extract_number(aria)
        except Exception:
            pass

        # Category
        try:
            cat_el = page.locator(SELECTORS["category"])
            if await cat_el.count() > 0:
                lead.category = clean_text(await cat_el.first.inner_text())
        except Exception:
            pass

        # Address
        try:
            addr_el = page.locator(SELECTORS["address"])
            if await addr_el.count() > 0:
                lead.address = clean_text(await addr_el.first.inner_text())
        except Exception:
            pass

        # Phone
        try:
            phone_el = page.locator(SELECTORS["phone"])
            if await phone_el.count() > 0:
                lead.phone = clean_text(await phone_el.first.inner_text())
        except Exception:
            pass

        # Website
        try:
            web_el = page.locator(SELECTORS["website"])
            if await web_el.count() > 0:
                lead.website = clean_text(await web_el.first.inner_text())
        except Exception:
            pass

        # Plus code
        try:
            plus_el = page.locator(SELECTORS["plus_code"])
            if await plus_el.count() > 0:
                lead.plus_code = clean_text(await plus_el.first.inner_text())
        except Exception:
            pass

        if lead.is_valid():
            return lead

        log.debug(f"Skipping invalid lead at {url}")
        return None

    # -- public API ----------------------------------------------------------

    async def scrape(self, query: str | None = None) -> list[dict[str, Any]]:
        """
        Run the full scrape pipeline:
        1. Navigate to Maps
        2. Search query
        3. Scroll & collect listing URLs
        4. Visit each listing and extract data
        5. Return deduplicated list of dicts
        """
        query = query or self.search_query
        if not query:
            raise ValueError("No search query provided")

        await self._navigate_to_maps()
        await self._perform_search(query)

        urls = await self._scroll_results()
        log.info(f"Found [bold]{len(urls)}[/bold] listing URLs to scrape")

        results: list[dict[str, Any]] = []

        for idx, url in enumerate(urls, 1):
            try:
                lead = await self._extract_lead(url)
                if lead:
                    results.append(lead.to_dict())
                    log.info(
                        f"[{idx}/{len(urls)}] ✔ {lead.business_name}"
                    )
                else:
                    log.warning(f"[{idx}/{len(urls)}] ✘ No data extracted")
            except Exception as exc:
                log.error(f"[{idx}/{len(urls)}] ✘ Error: {exc}")

            # Navigate back to results list for the next one
            await self._page.go_back(wait_until="domcontentloaded")  # type: ignore[union-attr]
            await human_delay(1.0, 2.0)

        log.info(f"Scrape complete — {len(results)} leads collected")
        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_typing_delay() -> int:
    """Return a per-keystroke delay in ms to mimic human typing."""
    return random.randint(40, 120)


# Quick standalone test
if __name__ == "__main__":
    import random

    async def _test():
        async with GoogleMapsScraper(headless=False) as scraper:
            data = await scraper.scrape("coffee shops in San Francisco")
            print(f"Collected {len(data)} leads")
            for d in data[:3]:
                print(d)

    asyncio.run(_test())
