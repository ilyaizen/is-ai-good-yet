"""Archive/Cache fallback extraction strategy.

This module provides robust fallback scraping using:
1. Archive.is with Selenium/undetected-chromedriver (best for Cloudflare bypass)

Enhanced with proper rate limiting, retry logic, and availability checking.
Note: The Playwright-based archive.is method is deprecated in favor of Selenium
which has much better success with Cloudflare protection.
"""

import asyncio
import random
import logging
import re
import json
from typing import Optional, Dict, List
from urllib.parse import quote, urljoin, urlparse


from playwright.async_api import async_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None  # type: ignore
import aiohttp
import trafilatura

from .base import ScraperStrategy
from browser_runtime import resolve_chromium_executable
from store.paths import get_data_path

# Import Selenium-based scraper (optional, used as fallback)
try:
    from .selenium_archive import SeleniumArchiveScraper, SELENIUM_AVAILABLE
except ImportError:
    SeleniumArchiveScraper = None  # type: ignore
    SELENIUM_AVAILABLE = False

try:
    from .simple_scraper import SimpleScraper
except ImportError:
    SimpleScraper = None  # type: ignore

logger = logging.getLogger(__name__)


class ArchiveScraper(ScraperStrategy):
    """Fetch archived version from archive.is and extract content.

    Uses Selenium/undetected-chromedriver for reliable Cloudflare bypass.
    The Playwright method is deprecated and kept for reference only.
    """

    # Modern User-Agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    # Archive.is domains to try (in order of preference)
    ARCHIVE_IS_DOMAINS = [
        "archive.ph",
        "archive.is",
        "archive.today",
    ]

    # Class-level rate limiting for archive.is (increased from 10s to 20s)
    _last_archive_is_request = 0.0
    _archive_is_min_interval = 20.0  # Minimum 20 seconds between archive.is requests
    _archive_lock = asyncio.Lock()  # Ensure only one archive.is request at a time

    # Class-level shared browser/context for session reuse
    _shared_browser = None
    _shared_context = None
    _shared_page = None

    # Class-level headful setting
    _headful_mode = False

    def __init__(self, shared_context: Optional[BrowserContext] = None, headful: bool = False):
        """Initialize ArchiveScraper with optional shared browser context.

        Args:
            shared_context: Optional Playwright BrowserContext with pre-authenticated session.
                           If provided, this context (with cookies) will be used for archive.is.
            headful: If True, run browsers in visible mode for CAPTCHA solving.
        """
        self._instance_context = shared_context
        self._headful = headful

    @classmethod
    def set_shared_context(cls, browser, context: BrowserContext, headful: bool = False):
        """Set a shared browser context for all ArchiveScraper instances.

        This allows the interactive session's solved CAPTCHA cookies to be reused
        by automated archive fallbacks.

        Args:
            browser: Shared Playwright browser instance
            context: Shared BrowserContext with pre-authenticated session
            headful: If True, run browsers in visible mode for CAPTCHA solving
        """
        cls._shared_browser = browser
        cls._shared_context = context
        cls._headful_mode = headful
        logger.info(f"ArchiveScraper: Shared browser context set - cookies will be reused (headful={headful})")

    @classmethod
    def clear_shared_context(cls):
        """Clear the shared browser context."""
        cls._shared_browser = None
        cls._shared_context = None
        cls._shared_page = None

    @property
    def name(self) -> str:
        return "archive.is"

    async def extract(self, html: str, url: str, session: Optional[aiohttp.ClientSession] = None, use_selenium: bool = False) -> Optional[dict]:
        """Fetch from archive sources and extract using trafilatura.

        Fallback chain:
        1. Wayback Machine (fast, no browser needed)
        2. Google Cache (fast, no browser needed)
        3. archive.is with Playwright (lighter than Selenium)
        4. archive.is with Selenium (last resort, if use_selenium=True)

        Args:
            html: Original HTML (unused - we fetch from archive)
            url: Article URL to look up in archive
            session: Shared aiohttp session (optional, will create one if needed)
            use_selenium: If True, try Selenium as final fallback (default False)

        Returns:
            Extracted article data or None
        """
        logger.info(f"[ARCHIVE] Starting archive fallback chain for: {url[:70]}...")
        own_session = False
        if session is None:
            session = aiohttp.ClientSession()
            own_session = True

        try:
            # Step 1: Try Wayback Machine first (fastest, most reliable)
            logger.info(f"[ARCHIVE] Step 1/4: Trying Wayback Machine...")
            result = await self._try_wayback_machine(url, session)
            if result:
                logger.info(f"[ARCHIVE] SUCCESS via Wayback Machine ({len(result.get('text', ''))} chars)")
                return result
            logger.info(f"[ARCHIVE] Wayback Machine: No archive found")

            # Step 2: Try Google Cache
            logger.info(f"[ARCHIVE] Step 2/4: Trying Google Cache...")
            result = await self._try_google_cache(url, session)
            if result:
                logger.info(f"[ARCHIVE] SUCCESS via Google Cache ({len(result.get('text', ''))} chars)")
                return result
            logger.info(f"[ARCHIVE] Google Cache: No cache found")

            # Step 3: Try archive.is with Playwright (lighter than Selenium)
            logger.info(f"[ARCHIVE] Step 3/4: Trying archive.is (Playwright)...")
            result = await self._try_archive_is_playwright(url)
            if result:
                logger.info(f"[ARCHIVE] SUCCESS via archive.is Playwright ({len(result.get('text', ''))} chars)")
                return result
            logger.info(f"[ARCHIVE] archive.is (Playwright): Failed or no archive")

            # Step 4: Try Selenium only if explicitly requested (heavy, last resort)
            if use_selenium and SELENIUM_AVAILABLE and SeleniumArchiveScraper:
                use_headful = self._headful or ArchiveScraper._headful_mode
                logger.info(f"[ARCHIVE] Step 4/4: Trying archive.is (Selenium, headful={use_headful})...")
                try:
                    selenium_scraper = SeleniumArchiveScraper(headless=not use_headful)
                    result = await selenium_scraper.fetch_from_archive(url)
                    if result:
                        logger.info(f"[ARCHIVE] SUCCESS via archive.is Selenium ({len(result.get('text', ''))} chars)")
                        return result
                    logger.info(f"[ARCHIVE] archive.is (Selenium): Failed or no archive")
                except Exception as e:
                    logger.warning(f"[ARCHIVE] Selenium archive scraper error: {e}")
            elif use_selenium:
                logger.info(f"[ARCHIVE] Step 4/4: Selenium requested but not available (SELENIUM_AVAILABLE={SELENIUM_AVAILABLE})")

            logger.warning(f"[ARCHIVE] All archive fallbacks exhausted for: {url[:70]}...")
            return None

        finally:
            if own_session:
                await session.close()


    async def _try_wayback_machine(self, url: str, session: aiohttp.ClientSession) -> Optional[dict]:
        """Try to fetch content from Wayback Machine (archive.org).

        Uses the Wayback Availability API to find archived versions,
        then fetches and extracts the content.
        """
        try:
            # Step 1: Check if URL is archived using the CDX API (more reliable than availability API)
            cdx_url = f"https://web.archive.org/cdx/search/cdx?url={quote(url, safe='')}&output=json&limit=1&fl=timestamp,statuscode"

            async with session.get(
                cdx_url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": random.choice(self.USER_AGENTS)}
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"Wayback CDX API returned {resp.status}")
                    # Fall back to availability API
                    return await self._try_wayback_availability_api(url, session)

                data = await resp.json()

            # CDX returns: [[field_names], [values]] or just [[field_names]] if not found
            if len(data) < 2:
                logger.debug(f"No Wayback archive found for {url[:60]}...")
                return None

            timestamp, statuscode = data[1]

            # Only use 2xx status codes
            if not str(statuscode).startswith('2'):
                logger.debug(f"Wayback snapshot has error status {statuscode}")
                return None

            # Construct archive URL using the timestamp
            archive_url = f"https://web.archive.org/web/{timestamp}/{url}"

            logger.debug(f"Found Wayback snapshot: {archive_url[:80]}...")

            # Step 2: Fetch the archived page
            await asyncio.sleep(random.uniform(0.5, 1.5))  # Rate limiting

            async with session.get(
                archive_url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": random.choice(self.USER_AGENTS)},
                allow_redirects=True
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"Wayback fetch returned {resp.status}")
                    return None

                html = await resp.text()

            if not html or len(html) < 500:
                return None

            # Remove Wayback Machine toolbar/header
            html = self._clean_wayback_html(html)

            # Step 3: Extract content using trafilatura
            return await self._extract_with_trafilatura(html, url)

        except asyncio.TimeoutError:
            logger.debug(f"Wayback Machine timeout for {url[:60]}...")
            return None
        except aiohttp.ClientError as e:
            logger.debug(f"Wayback Machine client error: {e}")
            return None
        except Exception as e:
            logger.debug(f"Wayback Machine error: {e}")
            return None

    async def _try_wayback_availability_api(self, url: str, session: aiohttp.ClientSession) -> Optional[dict]:
        """Fallback to Wayback Availability API."""
        try:
            api_url = f"https://archive.org/wayback/available?url={quote(url, safe='')}"

            async with session.get(
                api_url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": random.choice(self.USER_AGENTS)}
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            snapshots = data.get("archived_snapshots", {})
            closest = snapshots.get("closest")

            if not closest or not closest.get("available"):
                return None

            archive_url = closest.get("url", "").replace("http://", "https://")
            if not archive_url:
                return None

            await asyncio.sleep(random.uniform(0.5, 1.5))

            async with session.get(
                archive_url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": random.choice(self.USER_AGENTS)},
                allow_redirects=True
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

            if not html or len(html) < 500:
                return None

            html = self._clean_wayback_html(html)
            return await self._extract_with_trafilatura(html, url)

        except Exception as e:
            logger.debug(f"Wayback availability API error: {e}")
            return None

    def _clean_wayback_html(self, html: str) -> str:
        """Remove Wayback Machine navigation elements."""
        # Remove Wayback Machine toolbar
        patterns = [
            r'<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->',
            r'<script[^>]*type="text/javascript"[^>]*src="[^"]*web\.archive\.org[^"]*"[^>]*></script>',
            r'<link[^>]*href="[^"]*web\.archive\.org[^"]*"[^>]*>',
            r'<div[^>]*id="wm-ipp-base"[^>]*>.*?</div>',
            r'<div[^>]*id="wm-ipp"[^>]*>.*?</div>',
        ]

        for pattern in patterns:
            html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)

        return html

    async def _try_google_cache(self, url: str, session: aiohttp.ClientSession) -> Optional[dict]:
        """Try to fetch content from Google Cache.

        Note: Google Cache is being deprecated, but still works for some URLs.
        """
        try:
            # Google's webcache URL format
            cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{quote(url, safe='')}"

            await asyncio.sleep(random.uniform(1, 2))  # Rate limiting

            async with session.get(
                cache_url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": random.choice(self.USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                allow_redirects=True
            ) as resp:
                if resp.status == 404:
                    logger.debug(f"Google Cache: not cached")
                    return None
                if resp.status != 200:
                    logger.debug(f"Google Cache returned {resp.status}")
                    return None

                html = await resp.text()

            if not html or len(html) < 500:
                return None

            # Check if it's actually cached content (not a captcha/block page)
            if "unusual traffic" in html.lower() or "recaptcha" in html.lower():
                logger.debug("Google Cache: captcha/block detected")
                return None

            # Remove Google Cache header
            html = self._clean_google_cache_html(html)

            return await self._extract_with_trafilatura(html, url)

        except asyncio.TimeoutError:
            logger.debug(f"Google Cache timeout")
            return None
        except aiohttp.ClientError as e:
            logger.debug(f"Google Cache client error: {e}")
            return None
        except Exception as e:
            logger.debug(f"Google Cache error: {e}")
            return None

    def _clean_google_cache_html(self, html: str) -> str:
        """Remove Google Cache header/navigation."""
        # Remove the Google Cache header div
        patterns = [
            r'<div[^>]*style="[^"]*BACKGROUND:\s*#ccc[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*google-cache[^"]*"[^>]*>.*?</div>',
        ]

        for pattern in patterns:
            html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)

        return html

    async def _try_archive_is_playwright(self, url: str) -> Optional[dict]:
        """Try to fetch content from archive.is using Playwright with stealth.

        Uses browser automation to bypass archive.is bot detection.
        Implements class-level rate limiting and locking to avoid 429 errors.
        Reuses shared browser context when available for cookie persistence.
        """
        import time

        # Use lock to ensure only one archive.is request at a time (avoid 429s)
        async with ArchiveScraper._archive_lock:
            # Class-level rate limiting for archive.is
            now = time.time()
            time_since_last = now - ArchiveScraper._last_archive_is_request
            if time_since_last < ArchiveScraper._archive_is_min_interval:
                wait_time = ArchiveScraper._archive_is_min_interval - time_since_last
                logger.debug(f"Archive.is rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            ArchiveScraper._last_archive_is_request = time.time()

            # Check for shared context (from interactive session or external)
            context = self._instance_context or ArchiveScraper._shared_context
            browser = ArchiveScraper._shared_browser

            # Track if we need to clean up resources
            should_close_browser = False
            should_close_context = False

            try:
                if context:
                    # Use the shared context with pre-authenticated cookies
                    logger.debug("Using shared browser context for archive.is")
                    page = await context.new_page()
                else:
                    # Fall back to launching a new browser
                    logger.debug("No shared context - launching new browser for archive.is")
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(
                            executable_path=resolve_chromium_executable(),
                            headless=True,
                            args=[
                                '--disable-blink-features=AutomationControlled',
                                '--disable-dev-shm-usage',
                                '--no-sandbox',
                                '--disable-gpu',
                                '--disable-extensions',
                                '--disable-plugins-discovery',
                            ]
                        )
                        should_close_browser = True

                        # Create context with realistic settings
                        context_args = {
                            "user_agent": random.choice(self.USER_AGENTS),
                            "viewport": {"width": random.choice([1920, 1680, 1440]), "height": random.choice([1080, 900, 800])},
                            "locale": "en-US",
                            "timezone_id": "America/New_York",
                            "java_script_enabled": True,
                        }

                        # Load saved session if available
                        storage_state_path = get_data_path("archive_session.json")
                        if storage_state_path.exists() and storage_state_path.stat().st_size > 0:
                            logger.info(f"Loading session from {storage_state_path}")
                            context_args["storage_state"] = str(storage_state_path)
                            context_args["user_agent"] = self.USER_AGENTS[0]

                        context = await browser.new_context(**context_args)
                        should_close_context = True

                        if "storage_state" not in context_args:
                            await context.add_cookies([
                                {"name": "cf_clearance", "value": f"some_clearance_value_{random.randint(1000, 9999)}", "domain": ".archive.is", "path": "/"},
                            ])

                        page = await context.new_page()

                        # Apply stealth patches
                        if stealth_async:
                            await stealth_async(page)

                        # Enhanced stealth init script for Cloudflare bypass
                        await page.add_init_script("""
                            // Override webdriver property
                            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

                            // Mock chrome runtime
                            window.chrome = {
                                runtime: {},
                                loadTimes: function() {},
                                csi: function() {},
                                app: {}
                            };

                            // Override plugins to look like real browser
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => {
                                    const plugins = [
                                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                                    ];
                                    plugins.item = (index) => plugins[index];
                                    plugins.namedItem = (name) => plugins.find(p => p.name === name);
                                    plugins.refresh = () => {};
                                    return plugins;
                                }
                            });

                            // Override languages
                            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});

                            // Override platform
                            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});

                            // Override permissions query
                            const originalQuery = window.navigator.permissions.query;
                            window.navigator.permissions.query = (parameters) => (
                                parameters.name === 'notifications'
                                    ? Promise.resolve({ state: Notification.permission })
                                    : originalQuery(parameters)
                            );

                            // Mock WebGL vendor/renderer
                            const getParameter = WebGLRenderingContext.prototype.getParameter;
                            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                                if (parameter === 37445) return 'Intel Inc.';
                                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                                return getParameter.apply(this, arguments);
                            };
                        """)

                        # Run the domain fetch loop inside the async with block
                        try:
                            for i, domain in enumerate(self.ARCHIVE_IS_DOMAINS):
                                result = await self._fetch_from_archive_domain(page, domain, url)
                                if result:
                                    return result

                                wait_time = (2 ** i) + random.uniform(1, 3)
                                logger.debug(f"Waiting {wait_time:.1f}s before next archive.is domain")
                                await asyncio.sleep(wait_time)

                            return None
                        finally:
                            await page.close()
                            if should_close_context and context:
                                await context.close()
                            if should_close_browser and browser:
                                await browser.close()

                # If using shared context, try domains here
                try:
                    if stealth_async:
                        await stealth_async(page)

                    for i, domain in enumerate(self.ARCHIVE_IS_DOMAINS):
                        result = await self._fetch_from_archive_domain(page, domain, url)
                        if result:
                            return result

                        wait_time = (2 ** i) + random.uniform(1, 3)
                        logger.debug(f"Waiting {wait_time:.1f}s before next archive.is domain")
                        await asyncio.sleep(wait_time)

                    return None
                finally:
                    await page.close()

            except Exception as e:
                logger.error(f"Playwright archive.is error: {e}")
                return None

    async def _fetch_from_archive_domain(self, page: Page, domain: str, url: str) -> Optional[dict]:
        """Fetch from a specific archive.is domain."""
        archive_url = f"https://{domain}/newest/{url}"

        try:
            logger.debug(f"Trying archive URL: {archive_url[:80]}...")

            # Random human-like delay before navigation
            await asyncio.sleep(random.uniform(2, 5))

            # Simulate human-like navigation pattern
            await page.mouse.move(random.randint(100, 500), random.randint(100, 300))

            response = await page.goto(archive_url, wait_until="networkidle", timeout=60000)

            if not response:
                logger.debug(f"No response from {domain}")
                return None

            status = response.status
            final_url = page.url

            logger.debug(f"Archive.is response: status={status}, url={final_url[:60]}...")

            # Check for rate limiting or errors
            if status == 429:
                logger.warning(f"Archive.is {domain} rate limited (status 429)")
                # Increase the global rate limit interval
                ArchiveScraper._archive_is_min_interval = min(60.0, ArchiveScraper._archive_is_min_interval * 1.5)
                return None

            if status in [503, 502]:
                logger.debug(f"Archive.is {domain} service error (status {status})")
                return None

            if status == 404:
                logger.debug(f"Not archived on {domain}")
                return None

            if status != 200:
                logger.debug(f"Archive.is returned {status}")
                return None

            # Check if we're on an actual archived page (not a search/no results page)
            is_archived = await self._verify_archive_page(page, domain)
            if not is_archived:
                logger.debug(f"Not a valid archived page on {domain}")
                return None

            # Scroll to load any lazy content
            await self._scroll_page(page)

            # Wait a bit for dynamic content
            await asyncio.sleep(1)

            # Get the HTML
            html = await page.content()

            if not html or len(html) < 1000:
                return None

            # Clean the archive frame if needed
            html = self._clean_archive_html(html)

            # Extract content
            return await self._extract_with_trafilatura(html, url)

        except PlaywrightTimeoutError:
            logger.debug(f"Timeout on {domain}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching from {domain}: {e}")
            return None

    async def _verify_archive_page(self, page: Page, domain: str) -> bool:
        """Verify that we're on an actual archived page, not a search/error page."""
        try:
            content = await page.content()
            content_lower = content.lower()

            # Check for common "not archived" indicators
            not_archived_indicators = [
                "no results",
                "не найдено",  # Russian: "not found"
                "not in the archive",
                "hasn't been archived yet",
                "has not been archived",
                "0 results found",
                "no se encontr",  # Spanish
                "keine ergebnisse",  # German
                "save this url",
                "enter the url",
            ]

            for indicator in not_archived_indicators:
                if indicator in content_lower:
                    return False

            # Check URL pattern - archived pages have a specific format
            current_url = page.url
            # Valid archive URLs look like: https://archive.ph/XXXXX
            if re.match(r'https?://archive\.(is|today|ph|li)/[a-zA-Z0-9]{5,}', current_url):
                return True

            # If we're still on the /newest/ URL, it means there's no archive
            if '/newest/' in current_url:
                return False

            # If the page has substantial content, consider it valid
            try:
                text = await page.inner_text('body')
                if text and len(text) > 500:
                    return True
            except Exception:
                pass

            return False

        except Exception:
            return False

    async def _scroll_page(self, page: Page):
        """Scroll the page to trigger lazy loading with human-like behavior."""
        try:
            await page.evaluate("""
                async () => {
                    const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
                    const randomDelay = () => Math.floor(Math.random() * 300) + 100;

                    for (let i = 0; i < 3; i++) {
                        const scrollAmount = Math.floor(Math.random() * 300) + 200;
                        window.scrollBy(0, scrollAmount);
                        await delay(randomDelay());
                    }
                    window.scrollTo(0, 0);
                }
            """)
        except Exception:
            pass

    def _clean_archive_html(self, html: str) -> str:
        """Remove archive.is navigation/header elements that might interfere with extraction."""
        patterns = [
            r'<div[^>]*id="HEADER"[^>]*>.*?</div>',
            r'<div[^>]*class="HEADER"[^>]*>.*?</div>',
            r'<form[^>]*id="SAVEFORM"[^>]*>.*?</form>',
            r'<script[^>]*>.*?archive\.(is|today|ph|li).*?</script>',
            r'<input[^>]*type="hidden"[^>]*name="url"[^>]*>',
            r'<div[^>]*id="WOMBAT"[^>]*>.*?</div>',
        ]

        for pattern in patterns:
            html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)

        return html

    async def _extract_with_trafilatura(self, html: str, url: str) -> Optional[dict]:
        """Extract article content using trafilatura."""
        def _run_trafilatura():
            try:
                doc = trafilatura.bare_extraction(
                    html,
                    include_comments=False,
                    include_tables=True,
                    favor_recall=True,
                    no_fallback=False,
                    with_metadata=True,
                    url=url
                )

                if not doc or not doc.get("text"): # type: ignore
                    return None

                text = doc["text"].strip() # type: ignore

                # Minimum content length requirement
                if len(text) < 100:
                    return None

                # Verify it's not garbage (like cookie notices, nav menus, etc.)
                if self._is_garbage_content(text):
                    return None

                title = doc.get("title", "") or "" # type: ignore
                if "static01.nyt.com is blocked" in title:
                    return None

                return {
                    "title": doc.get("title", ""), # type: ignore
                    "author": doc.get("author", ""), # type: ignore
                    "publish_date": doc.get("date", ""), # type: ignore
                    "text": text,
                    "word_count": len(text.split()),
                }
            except Exception as e:
                logger.debug(f"Trafilatura extraction error: {e}")
                return None

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_trafilatura)

        if result:
            return result

        # Fallback to SimpleScraper if available
        if SimpleScraper:
            logger.debug("Trafilatura extraction failed/empty, trying SimpleScraper fallback...")
            simple = SimpleScraper()
            return await simple.extract(html, url)

        return None

    def _is_garbage_content(self, text: str) -> bool:
        """Check if extracted content is garbage (cookie notices, etc.)."""
        text_lower = text.lower()

        garbage_indicators = [
            "we use cookies",
            "accept all cookies",
            "cookie policy",
            "privacy policy",
            "subscribe now",
            "sign up for",
            "create a free account",
            "already a subscriber",
            "please enable javascript",
            "static01.nyt.com is blocked",
        ]

        # If most of the content matches garbage indicators
        matches = sum(1 for indicator in garbage_indicators if indicator in text_lower)
        if matches >= 3 or (len(text) < 500 and matches >= 2):
            return True

        return False


class WaybackMachineScraper(ScraperStrategy):
    """Dedicated Wayback Machine scraper for direct API usage."""

    @property
    def name(self) -> str:
        return "wayback"

    async def extract(self, html: str, url: str) -> Optional[dict]:
        """Extract from Wayback Machine only."""
        async with aiohttp.ClientSession() as session:
            archive_scraper = ArchiveScraper()
            return await archive_scraper._try_wayback_machine(url, session)
