"""
Unified Content Scraper with Archive Fallback Integration.

This module unifies the main Playwright scraper with the interactive archive.is
scraper, providing a seamless fallback chain:

1. Direct Playwright access (with stealth)
2. Archive fallback chain (Wayback, Google Cache, archive.is Playwright, Selenium)
3. Interactive archive.is session (for CAPTCHA-blocked content, optional)

The interactive session reuses cookies from manual CAPTCHA solving, allowing
subsequent automated requests to bypass Cloudflare protection.

Usage:
    python -m src.scraper [options]

Features:
- Unified fallback chain with all scraping strategies
- Session persistence for archive.is (cookies survive across runs)
- Optional interactive mode for CAPTCHA solving
- Batch processing with configurable concurrency
- Resume support for interrupted sessions
"""

import sys
import io
import asyncio
import logging
import argparse
import random
import os
import types
import warnings
from pathlib import Path
from typing import List, Tuple, Optional
from playwright.async_api import (
    async_playwright, BrowserContext, Page, Browser,
    TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
)

warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Workaround for pkg_resources import issues: ensure it's available before importing playwright_stealth
try:
    import pkg_resources  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    # Try to create a minimal mock module for pkg_resources
    try:
        from importlib.resources import files
        pkg_resources_mock = types.ModuleType('pkg_resources')

        def resource_string(package, resource_name):
            try:
                resource_files = files(package)
                resource_path = resource_files / resource_name
                if hasattr(resource_path, 'read_bytes'):
                    return resource_path.read_bytes()
                else:
                    with open(resource_path, 'rb') as f:
                        return f.read()
            except Exception:
                return b''

        class _MockDistribution:
            version = "1.0.0"

        def _get_distribution(name):
            return _MockDistribution()

        pkg_resources_mock.get_distribution = _get_distribution # pyright: ignore[reportAttributeAccessIssue]
        pkg_resources_mock.resource_string = resource_string # pyright: ignore[reportAttributeAccessIssue]
        sys.modules['pkg_resources'] = pkg_resources_mock
    except ImportError:
        # Fallback: just create a basic mock
        pkg_resources_mock = types.ModuleType('pkg_resources')
        pkg_resources_mock.get_distribution = lambda name: type('obj', (), {'version': '1.0.0'})() # pyright: ignore[reportAttributeAccessIssue]
        pkg_resources_mock.resource_string = lambda pkg, res: b'' # pyright: ignore[reportAttributeAccessIssue]
        sys.modules['pkg_resources'] = pkg_resources_mock

from playwright_stealth import stealth_async
from aiolimiter import AsyncLimiter
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    # Prepend so the pipeline's utils package wins over unrelated site packages.
    sys.path.insert(0, str(current_dir))

from store.db import (init_db, migrate_database, get_urls_to_scrape, update_scraped_status,
                      get_pending_scrape_count, get_pending_opinion_count)
from store.parquet import ParquetArticleStore
from scrapers import TrafilaturaScraper, NewspaperScraper, ArchiveScraper, SimpleScraper  # noqa: F401
from scrapers.selenium_archive import SeleniumArchiveScraper, SELENIUM_AVAILABLE as SELENIUM_ARCHIVE_AVAILABLE  # noqa: F401
from utils import (
    get_browser_context_options, apply_human_timing, scroll_randomly,
    get_random_delay_range, ProxyRotator, StealthConnector
)  # noqa: F401
from interactive import InteractiveSession  # noqa: F401

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # Patch asyncio to silence "ValueError: I/O operation on closed pipe" on Windows shutdown
    # This happens when ProactorEventLoop closes pipes while transports are being collected
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _original_proactor_del = _ProactorBasePipeTransport.__del__

        def _silenced_proactor_del(self):
            try:
                _original_proactor_del(self)
            except ValueError:
                pass  # Ignore closed pipe errors

        _ProactorBasePipeTransport.__del__ = _silenced_proactor_del
    except (ImportError, AttributeError):
        pass

console = Console()


# Domains that typically don't contain relevant articles for AI sentiment analysis
# (Duplicated from prefilter_content.py to avoid circular import)
IRRELEVANT_DOMAINS = [
    "github.com",
    "arxiv.org",
    "twitter.com",
    "x.com",
    "reddit.com",
    "youtube.com",
    "docs.google.com",
    "drive.google.com",
    "gist.github.com",
    "gitlab.com",
    "bitbucket.org",
    "stackoverflow.com",
    "stackexchange.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "discord.com",
    "slack.com",
    "notion.so",
    "figma.com",
    "miro.com",
    "trello.com",
    "jira.atlassian.com",
    "huggingface.co",
    "kaggle.com",
    "colab.research.google.com",
    "pypi.org",
    "npmjs.com",
    "crates.io",
    "cursor.com",
]


def is_relevant_url(url: str) -> bool:
    """Check if a URL is from a relevant domain (not in IRRELEVANT_DOMAINS)."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        hostname = hostname.replace("www.", "", 1)
        for domain in IRRELEVANT_DOMAINS:
            if hostname == domain or hostname.endswith("." + domain):
                return False
        return True
    except Exception:
        return True  # If parsing fails, consider it relevant







FORCE_ARCHIVE_DOMAINS = [
    "nytimes.com", "wsj.com", "ft.com", "techdirt.com", "thehill.com",
    "reuters.com", "telegraph.co.uk", "bloomberg.com", "sfgate.com"
]

STORAGE_STATE_FILE = Path(__file__).parent.parent / "data" / "archive_session.json"

BAD_PATTERNS = [
    "enable javascript", "please turn javascript on", "access denied",
    "security check", "cloudflare", "just a moment...", "pardinot"
]



# Rate Limiting / Timing Configuration
SCRAPE_TIMEOUT_MS = 45000        # Timeout for page loading (45s)
ARCHIVE_WAIT_MIN = 1.0           # Min wait before archive fallback (was 2.0)
ARCHIVE_WAIT_MAX = 3.0           # Max wait before archive fallback (was 5.0)
HUMAN_DELAY_MIN = 0.5            # Min human-like delay (was randomized ~2-4)
HUMAN_DELAY_MAX = 1.5            # Max human-like delay (was randomized ~4-7)
ARCHIVE_OP_TIMEOUT = 30          # Timeout for archive operations (30s)
INTERACTIVE_OP_TIMEOUT = 45      # Timeout for interactive operations (45s)

# Lean mode configuration overrides (balanced for retry-failed use case)
LEAN_SCRAPE_TIMEOUT_MS = 90000   # Page timeout in lean mode (90s - gives slow sites more time)
LEAN_ARCHIVE_OP_TIMEOUT = 120    # Archive timeout - needs time for Wayback/Playwright fallback chain
LEAN_MAX_RETRIES = 2             # Allow 2 attempts for failed sites

class UnifiedScraper:
    """
    Unified scraper that combines direct scraping with archive fallbacks.

    Fallback order:
    1. Direct Playwright with stealth patches
    2. ArchiveScraper (Wayback -> Google Cache -> archive.is Playwright -> Selenium)
    3. Interactive archive.is session (optional, for CAPTCHA solving)
    """

    def __init__(
        self,
        browser: Browser,
        context: BrowserContext,
        strategies: list,
        rate_limiter: AsyncLimiter,
        interactive_mode: bool = False,
        interactive_page: Optional[Page] = None,
        max_retries: int = 1,
        headful: bool = False,
        lean_mode: bool = False,
        use_selenium: bool = False
    ):
        self.browser = browser
        self.context = context
        self.strategies = strategies
        self.rate_limiter = rate_limiter
        self.interactive_mode = interactive_mode
        self.interactive_page = interactive_page
        self.max_retries = max_retries
        self.headful = headful
        self.lean_mode = lean_mode
        self.use_selenium = use_selenium
        self.archive_scraper = ArchiveScraper(headful=headful)

        # Apply lean mode overrides
        if lean_mode:
            self.scrape_timeout_ms = LEAN_SCRAPE_TIMEOUT_MS
            self.archive_op_timeout = LEAN_ARCHIVE_OP_TIMEOUT
            self.max_retries = LEAN_MAX_RETRIES
        else:
            self.scrape_timeout_ms = SCRAPE_TIMEOUT_MS
            self.archive_op_timeout = ARCHIVE_OP_TIMEOUT

    async def scrape_url(self, url: str) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
        """
        Scrape a URL using the full fallback chain.

        Returns: (content_dict, method_name, error_reason)
        """
        force_archive = any(d in url for d in FORCE_ARCHIVE_DOMAINS)

        content = None
        method = None
        error = None

        if not force_archive:
            async with self.rate_limiter:
                try:
                    content, method, error = await asyncio.wait_for(
                        self._scrape_with_playwright(url),
                        timeout=self.scrape_timeout_ms / 1000 + 5  # slightly higher than the page timeout
                    )
                except asyncio.TimeoutError:
                    content, method, error = None, None, "scraping_timeout_exceeded"
                except Exception as e:
                    # Lean mode: never crash on a single URL
                    if self.lean_mode:
                        content, method, error = None, None, f"skipped_exception_{type(e).__name__}"
                    else:
                        raise

        if force_archive or (not content and error and self._should_try_archive(error)):
            if force_archive:
                logging.info(f"Forcing archive fallback for {url}")
            else:
                logging.info(f"Playwright failed ({error}), trying archive fallback for {url}")

            await asyncio.sleep(random.uniform(ARCHIVE_WAIT_MIN, ARCHIVE_WAIT_MAX))

            try:
                # Use full fallback chain: Wayback -> Google Cache -> Playwright archive.is
                # Only use Selenium if explicitly enabled (it's heavy and often blocked)
                content = await asyncio.wait_for(
                    self.archive_scraper.extract(None, url, use_selenium=self.use_selenium),  # type: ignore
                    timeout=self.archive_op_timeout
                )
                if content:
                    method = "archive_automated"
                    error = None
                    if not self.lean_mode:
                        logging.info(f"[ARCHIVE AUTO SUCCESS] {url[:60]}...")
            except asyncio.TimeoutError:
                error = "archive_auto_timeout"
            except Exception as e:
                error = f"archive_auto_error_{str(e)[:50]}"

        if not content and self.interactive_mode and self.interactive_page:
            if self._should_try_interactive(error):
                logging.info(f"Automated methods failed, trying interactive archive for {url}")
                try:
                    content = await asyncio.wait_for(
                        self._scrape_with_interactive_archive(url),
                        timeout=INTERACTIVE_OP_TIMEOUT
                    )
                    if content:
                        method = "archive_interactive"
                        error = None
                        logging.info(f"[ARCHIVE INTERACTIVE SUCCESS] {url[:60]}...")
                except asyncio.TimeoutError:
                    error = "archive_interactive_timeout"
                except Exception as e:
                    logging.error(f"Interactive archive error: {e}")
                    error = f"archive_interactive_error_{str(e)[:50]}"

        return content, method, error

    def _should_try_archive(self, error: Optional[str]) -> bool:
        if not error:
            return False
        triggers = ["blocked", "http_error_403", "http_error_429", "empty_or_short_html",
                   "scraping_timeout_exceeded", "playwright_error", "all_retries_exhausted",
                   "extraction_failed_bad_patterns"]
        return any(t in str(error) for t in triggers)

    def _should_try_interactive(self, error: Optional[str]) -> bool:
        if not error:
            return True
        if "extraction_failed" in error:
            return False
        triggers = ["cloudflare", "captcha", "blocked", "403", "429", "timeout", "failed"]
        return any(t in str(error).lower() for t in triggers)

    async def _scrape_with_playwright(self, url: str) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
        """Direct Playwright scraping with stealth patches."""
        page: Optional[Page] = None
        retry_count = 0

        logging.info(f"[PLAYWRIGHT] Starting scrape: {url[:80]}...")
        logging.debug(f"[PLAYWRIGHT] Config: timeout={self.scrape_timeout_ms}ms, max_retries={self.max_retries}, lean={self.lean_mode}")

        while retry_count < self.max_retries:
            page = None
            attempt_num = retry_count + 1
            logging.info(f"[PLAYWRIGHT] Attempt {attempt_num}/{self.max_retries} for {url[:60]}...")

            try:
                # Step 1: Create new page
                logging.debug(f"[PLAYWRIGHT] Creating new page...")
                page = await self.context.new_page()

                # Step 2: Apply stealth patches
                logging.debug(f"[PLAYWRIGHT] Applying stealth patches...")
                await stealth_async(page)

                # Step 3: Setup resource blocking
                # Note: We ALLOW stylesheets because blocking them often breaks SPA rendering
                # or triggers anti-bot protections that check for computed styles.
                logging.debug(f"[PLAYWRIGHT] Setting up resource blocking (images, media, fonts)...")
                await page.route("**/*", lambda route: route.abort()
                    if route.request.resource_type in ["image", "media", "font"]
                    else route.continue_())

                # Step 4: Apply human timing
                delay_min, delay_max = HUMAN_DELAY_MIN, HUMAN_DELAY_MAX
                logging.debug(f"[PLAYWRIGHT] Applying human timing (delay: {delay_min}-{delay_max}s)...")
                await apply_human_timing(page, delay_min, delay_max)

                # Step 5: Navigate to URL
                logging.info(f"[PLAYWRIGHT] Navigating to URL (timeout: {self.scrape_timeout_ms}ms)...")
                try:
                    # Use 'commit' to return as soon as server responds, then wait smarter
                    response = await page.goto(url, wait_until="commit", timeout=self.scrape_timeout_ms)

                    # Smart wait for content
                    try:
                        # Wait for body to be populated
                        await page.wait_for_selector('body', timeout=15000)
                        # Wait for network idle (SPAs)
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        # Ignore wait errors, we'll try to scrape anyway
                        pass

                    if not response:
                        logging.warning(f"[PLAYWRIGHT] No response received - will retry")
                        retry_count += 1
                        continue

                    # Step 6: Check response status
                    status = response.status
                    logging.info(f"[PLAYWRIGHT] Response status: {status}")

                    if status >= 400:
                        if status in [403, 401, 429]:
                            logging.warning(f"[PLAYWRIGHT] BLOCKED (Status {status}) for {url}")
                            return None, None, f"blocked_{status}"
                        else:
                            logging.warning(f"[PLAYWRIGHT] HTTP Error {status} for {url}")
                            return None, None, f"http_error_{status}"

                except PlaywrightTimeoutError:
                    logging.warning(f"[PLAYWRIGHT] Navigation timeout after {self.scrape_timeout_ms}ms - attempting extraction anyway")
                except PlaywrightError as e:
                    logging.error(f"[PLAYWRIGHT] Playwright error: {e}")
                    return None, None, f"playwright_error: {str(e)}"

                # Step 7: Scroll page
                logging.debug(f"[PLAYWRIGHT] Scrolling page to trigger lazy loading...")
                await scroll_randomly(page)

                # Step 8: Get page content
                logging.debug(f"[PLAYWRIGHT] Getting page HTML content...")
                try:
                    html = await page.content()
                except Exception as e:
                    logging.warning(f"[PLAYWRIGHT] Failed to get page content: {e}")
                    html = ""

                html_len = len(html) if html else 0
                logging.info(f"[PLAYWRIGHT] Got HTML content: {html_len} bytes")

                if not html or html_len < 200:
                    logging.warning(f"[PLAYWRIGHT] HTML too short ({html_len} bytes < 200) - will retry")
                    retry_count += 1
                    continue

                # Step 9: Try extraction strategies
                logging.info(f"[PLAYWRIGHT] Attempting content extraction with {len(self.strategies)} strategies...")
                extraction_failed = True
                for i, strategy in enumerate(self.strategies):
                    strategy_name = strategy.name if hasattr(strategy, 'name') else type(strategy).__name__
                    logging.debug(f"[PLAYWRIGHT] Trying strategy {i+1}/{len(self.strategies)}: {strategy_name}")
                    try:
                        result = await strategy.extract(html, url)
                        if result:
                            text = result.get('text', '')
                            text_len = len(text)
                            logging.debug(f"[PLAYWRIGHT] Strategy {strategy_name} extracted {text_len} chars")

                            text_lower = text.lower()
                            if not text_lower:
                                logging.debug(f"[PLAYWRIGHT] Strategy {strategy_name} returned empty text - skipping")
                                continue

                            # Check for bad patterns
                            bad_pattern_match = None
                            for pattern in BAD_PATTERNS:
                                if pattern in text_lower[:500]:
                                    bad_pattern_match = pattern
                                    break

                            if bad_pattern_match:
                                logging.warning(f"[PLAYWRIGHT] Bad pattern '{bad_pattern_match}' found in {strategy_name} result - trying next strategy")
                                continue

                            extraction_failed = False
                            logging.info(f"[PLAYWRIGHT] SUCCESS: Extracted {text_len} chars using {strategy_name}")
                            return result, strategy_name, None
                        else:
                            logging.debug(f"[PLAYWRIGHT] Strategy {strategy_name} returned None")
                    except Exception as e:
                        logging.debug(f"[PLAYWRIGHT] Strategy {strategy_name} failed: {e}")
                        continue

                if extraction_failed:
                    logging.warning(f"[PLAYWRIGHT] All {len(self.strategies)} extraction strategies failed - returning extraction_failed_bad_patterns")
                    return None, None, "extraction_failed_bad_patterns"

            except Exception as e:
                retry_count += 1
                logging.error(f"[PLAYWRIGHT] Unexpected error (attempt {retry_count}/{self.max_retries}): {e}")
            finally:
                # ALWAYS close the page to prevent memory leaks
                if page:
                    try:
                        await page.close()
                        logging.debug(f"[PLAYWRIGHT] Page closed")
                    except Exception:
                        pass
                    page = None

        logging.warning(f"[PLAYWRIGHT] All {self.max_retries} retries exhausted for {url[:60]}...")
        return None, None, "all_retries_exhausted"

    async def _scrape_with_interactive_archive(self, url: str) -> Optional[dict]:
        """
        Scrape using the interactive archive.is page.
        This uses a shared page that preserves session cookies from manual CAPTCHA solving.
        """
        if not self.interactive_page:
            return None

        import re
        import trafilatura

        page = self.interactive_page
        archive_url = f"https://archive.ph/{url}"

        try:
            logging.info(f"  [INTERACTIVE] Navigating to archive.ph...")
            response = await page.goto(archive_url, wait_until="domcontentloaded", timeout=30000)

            if not response:
                return None

            status = response.status
            current_url = page.url
            content = await page.content()

            if status in [403, 429] or any(x in content.lower() for x in ["challenge", "captcha", "just a moment"]):
                logging.warning("  [INTERACTIVE] Cloudflare CAPTCHA detected!")
                logging.warning("  >>> SOLVE THE CAPTCHA IN THE BROWSER WINDOW <<<")

                solved = await self._wait_for_cloudflare(page, timeout=120)
                if not solved:
                    return None

                try:
                    await page.context.storage_state(path=str(STORAGE_STATE_FILE))
                    logging.info("  [INTERACTIVE] Session saved")
                except Exception as e:
                    logging.warning(f"  Warning: Could not save session: {e}")

                current_url = page.url
                content = await page.content()

            if re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}$', current_url):
                logging.info(f"  [INTERACTIVE] Direct archive page found")
            else:
                archive_links = await page.query_selector_all(
                    'a[href*="archive.ph/"], a[href*="archive.is/"], a[href*="archive.today/"]'
                )

                for link in archive_links:
                    href = await link.get_attribute('href')
                    if href and re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}$', href):
                        logging.info(f"  [INTERACTIVE] Found archive link: {href}")
                        await link.click()
                        await page.wait_for_load_state("domcontentloaded")
                        current_url = page.url
                        break
                else:
                    if "0 results" in content.lower() or "no results" in content.lower():
                        logging.info("  [INTERACTIVE] No archive found")
                        return None

            current_url = page.url
            if not re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}', current_url):
                return None

            try:
                await page.context.storage_state(path=str(STORAGE_STATE_FILE))
            except:
                pass

            await page.evaluate("() => { window.scrollBy(0, 500); }")
            await asyncio.sleep(1)

            html = ""
            iframes = page.frames
            for frame in iframes:
                if frame != page.main_frame:
                    try:
                        frame_html = await frame.content()
                        if len(frame_html) > len(html):
                            html = frame_html
                    except:
                        pass

            if len(html) < 1000:
                html = await page.content()

            html = self._clean_archive_html(html)

            text = ""
            title = ""
            author = ""
            date = ""

            try:
                # Use favor_recall for more complete content extraction
                doc = trafilatura.bare_extraction(html, include_comments=False, include_tables=True, favor_recall=True, no_fallback=False, with_metadata=True, url=url)
                if doc is not None:
                    if hasattr(doc, '__dict__'):
                        doc_dict = doc.__dict__
                    elif isinstance(doc, dict):
                        doc_dict = doc
                    else:
                        doc_dict = {"text": str(doc)}

                    text = doc_dict.get("text", "") or ""
                    title = doc_dict.get("title", "") or ""
                    author = doc_dict.get("author", "") or ""
                    date = doc_dict.get("date", "") or ""
            except Exception:
                pass

            if len(text) < 200:
                selectors = ['article', 'main', '[role="main"]', '.article-body', '.story-body',
                           '.post-content', '#article-body', '.entry-content']

                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            inner_text = await element.inner_text()
                            if inner_text and len(inner_text) > len(text):
                                text = inner_text
                                break
                    except:
                        continue

                if len(text) < 200:
                    try:
                        body_text = await page.inner_text('body')
                        if body_text:
                            lines = body_text.split('\n')
                            content_lines = [l.strip() for l in lines if len(l.strip()) > 50]
                            text = '\n'.join(content_lines)
                    except:
                        pass

                if not title:
                    try:
                        title_el = await page.query_selector('h1')
                        if title_el:
                            title = await title_el.inner_text()
                    except:
                        pass

            if len(text) > 100:
                if "static01.nyt.com is blocked" in title or "static01.nyt.com is blocked" in text:
                    logging.warning(f"  [INTERACTIVE] Detected NYT blocked content")
                    return None

                return {
                    "title": title,
                    "author": author,
                    "publish_date": date,
                    "text": text.strip(),
                    "word_count": len(text.split()),
                }

            return None

        except PlaywrightTimeoutError:
            return None
        except Exception as e:
            logging.error(f"  [INTERACTIVE] Error: {e}")
            return None

    async def _wait_for_cloudflare(self, page: Page, timeout: int = 120) -> bool:
        """Wait for Cloudflare challenge to be solved."""
        import re

        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            try:
                url = page.url
                content = await page.content()

                if re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}', url):
                    return True

                if "challenge" not in content.lower() and "captcha" not in content.lower():
                    if len(content) > 5000:
                        return True

                await asyncio.sleep(2)
            except:
                await asyncio.sleep(2)

        return False

    def _clean_archive_html(self, html: str) -> str:
        import re
        patterns = [r'<div[^>]*id="HEADER"[^>]*>.*?</div>', r'<form[^>]*id="SAVEFORM"[^>]*>.*?</form>']
        for p in patterns:
            html = re.sub(p, '', html, flags=re.DOTALL | re.IGNORECASE)
        return html


async def process_batch(
    scraper: UnifiedScraper,
    batch: List[Tuple],
    parquet_store: ParquetArticleStore,
    progress: Progress,
    task_id: int,
    pending_success_urls: List[str],
    session: InteractiveSession
):
    """Process a batch of URLs."""

    async def process_one(item):
        if not item:
            return

        try:
            url_id, url, hn_id, hn_score, hn_comments, hn_timestamp = item

            # Skip URLs from irrelevant domains (github, arxiv, twitter, etc.)
            if not is_relevant_url(url):
                logging.info(f"[SKIP] Irrelevant domain: {url}")
                update_scraped_status(url, 'skipped', 'irrelevant_domain', 'skipped')
                return

            content, method, error = await scraper.scrape_url(url)

            if content:
                text_content = content.get('text', '')
                if len(text_content) < 1000:
                    logging.warning(f"Discarding short content for {url} ({len(text_content)} bytes)")
                    update_scraped_status(url, 'failed', f"content_too_short_{len(text_content)}b", "empty_content")
                else:
                    parquet_store.add_article(
                        url_id, url,
                        content.get('title'), content.get('author'), content.get('publish_date'),
                        text_content, content.get('word_count', 0),
                        hn_id, hn_score, hn_comments, hn_timestamp
                    )

                    pending_success_urls.append(url)
                    logging.info(f"[SUCCESS] Scraped {url} ({len(text_content)} bytes)")
            else:
                failure_category = "unknown"
                if error:
                    if "extraction_failed" in error:
                        failure_category = "extraction_failed"
                    elif "archive" in error and "rate" in error.lower():
                        failure_category = "archive_rate_limited"
                    elif "archive" in error and ("failed" in error or "timeout" in error):
                        failure_category = "archive_failed"
                    elif "blocked" in error or "403" in error or "429" in error:
                        failure_category = "blocked"
                    elif "timeout" in error:
                        failure_category = "timeout"
                    elif "empty" in error or "short" in error:
                        failure_category = "empty_content"
                    elif "skipped" in error:
                        failure_category = "skipped"
                    elif "error" in error:
                        failure_category = "error"

                update_scraped_status(url, 'failed', error, failure_category)

        except Exception as e:
            # Never crash on a single URL - just mark as failed and move on
            try:
                url = item[1] if len(item) > 1 else "unknown"
                update_scraped_status(url, 'failed', f"process_exception_{type(e).__name__}", "error")
            except:
                pass  # Ultimate fallback - just skip

        progress.advance(task_id) # type: ignore

    # Process URLs truly concurrently with asyncio.gather
    tasks = []
    for item in batch:
        if session.check_shutdown():
            break
        tasks.append(process_one(item))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def main(
    verbose: bool,
    quiet: bool,
    batch_size: int,
    concurrency: int,
    rate_limit: float,
    info_only: bool,
    prioritize_opinion: bool,
    retry_failed: bool,
    use_proxy: bool = False,
    headful: bool = False,
    max_retries: int = 1,
    interactive: bool = False,
    stealth_mode: str = "seleniumbase",
    no_headful_switch: bool = False,
    lean_mode: bool = False,
    use_selenium: bool = False,
    oldest_first: bool = False
):
    # Logging level configuration:
    # - Default: INFO (detailed logs visible by default)
    # - With -v/--verbose: DEBUG (very verbose trace logs)
    # - With --quiet: WARNING (minimal output)
    # - Lean mode without verbose: ERROR (silent mode for automated runs)
    if quiet:
        level = logging.WARNING
    elif lean_mode and not verbose:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
    )

    init_db()
    migrate_database()

    strategies = [TrafilaturaScraper(), NewspaperScraper(), SimpleScraper()]

    if lean_mode:
        console.print("[bold cyan]🚀 LEAN MODE: Balanced retry settings enabled[/bold cyan]")
        console.print(f"[dim]  • Page timeout: {LEAN_SCRAPE_TIMEOUT_MS}ms | Archive timeout: {LEAN_ARCHIVE_OP_TIMEOUT}s | Max retries: {LEAN_MAX_RETRIES}[/dim]")

    # Show archive fallback mode
    if use_selenium:
        console.print("[bold yellow]📦 Selenium fallback: ENABLED (heavy, last resort)[/bold yellow]")
    else:
        console.print("[dim]📦 Archive fallback: Wayback → Google Cache → Playwright (no Selenium)[/dim]")

    shard_size_limit = max(batch_size * 2, 1000)
    parquet_store = ParquetArticleStore(shard_size=shard_size_limit)

    target_rate = rate_limit if rate_limit > 0 else float(concurrency)
    limiter = AsyncLimiter(target_rate, 1.0)

    proxy_rotator = ProxyRotator()

    session = InteractiveSession(console)
    session.start()

    console.print("[bold blue]Starting Scraper...[/bold blue]")

    if interactive:
        console.print("[bold green]Interactive mode enabled - CAPTCHA solving available[/bold green]")
        headful = True

    if use_proxy and proxy_rotator.is_enabled():
        console.print("[bold green]Proxy rotation enabled[/bold green]")
    elif use_proxy:
        console.print("[bold yellow]Proxy requested but not configured in .env[/bold yellow]")

    if headful:
        console.print("[bold yellow]Running in headful mode (browser visible)[/bold yellow]")

    console.print(f"[dim]Concurrency: {concurrency} | Rate Limit: {target_rate}/s | Max Retries: {max_retries}[/dim]")

    # Display ordering mode
    order_mode = "Oldest first (by HN score)" if oldest_first else "Newest first (by HN ID DESC)"
    console.print(f"[dim]Ordering: {order_mode}[/dim]")

    # Configuration summary box
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold]Scraper Configuration Summary:[/bold]")
    console.print(f"  • Batch Size: {batch_size}")
    console.print(f"  • Concurrency: {concurrency} tabs")
    console.print(f"  • Rate Limit: {target_rate}/s")
    console.print(f"  • Max Retries: {max_retries}")
    console.print(f"  • Order: {order_mode}")
    console.print(f"  • Retry Failed: {retry_failed}")
    console.print(f"  • Prioritize Opinion: {prioritize_opinion}")
    console.print(f"  • Headful: {headful}")
    console.print(f"  • Stealth Mode: {stealth_mode}")
    console.print(f"  • Lean Mode: {lean_mode}")
    console.print(f"  • Use Selenium: {use_selenium}")
    console.print(f"  • Use Proxy: {use_proxy}")
    console.print(f"  • Log Level: {logging.getLevelName(level)}")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/bold cyan]\n")

    # Initialize Selenium archive session for persistent browser (only if enabled)
    selenium_session_started = False
    if use_selenium and SELENIUM_ARCHIVE_AVAILABLE:
        if no_headful_switch:
            console.print("[dim]Initializing Selenium archive session (headful switch DISABLED)...[/dim]")
        else:
            console.print("[dim]Initializing Selenium archive session...[/dim]")
        try:
            # Start session - this validates cookies and switches to headful if CAPTCHA needed
            # If no_headful_switch is True, it will stay headless even if CAPTCHA is detected
            SeleniumArchiveScraper.start_session(
                headless=not headful,
                validate=True,
                disable_headful_switch=no_headful_switch
            )
            selenium_session_started = True
            console.print("[bold green]Selenium archive session ready[/bold green]")
        except Exception as e:
            console.print(f"[yellow]Selenium session init warning: {e}[/yellow]")

    async with async_playwright() as p:
        stealth_connector = None
        browser = None

        # Skip StealthConnector if Selenium archive session is already running
        # (they both try to use the same Chrome debugging port and conflict)
        if stealth_mode == "seleniumbase" and not selenium_session_started:
            console.print("[bold green]Attempting SeleniumBase Stealth Mode...[/bold green]")
            stealth_connector = StealthConnector()
            browser = await stealth_connector.launch_stealth_browser(p, headless=not headful)
            if not browser:
                console.print("[bold yellow]SeleniumBase failed - falling back to standard Playwright with stealth patches[/bold yellow]")
                stealth_connector = None  # Clear the failed connector
                stealth_mode = "standard"  # Switch to standard mode
        elif stealth_mode == "seleniumbase" and selenium_session_started:
            console.print("[dim]Skipping SeleniumBase for main browser (Selenium archive session active)[/dim]")
            stealth_mode = "standard"

        # Standard Playwright launch (used as primary or fallback)
        if not browser:
            browser = await p.chromium.launch(
                headless=not headful,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

        proxy_config = None
        if use_proxy and proxy_rotator.is_enabled():
            proxy_config = proxy_rotator.get_next_proxy()

        context_options = get_browser_context_options(use_proxy=use_proxy, proxy_config=proxy_config)  # type: ignore # noqa: F821
        context = await browser.new_context(**context_options)

        interactive_page = None
        if interactive:
            interactive_context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 800},
                "locale": "en-US",
            }

            if STORAGE_STATE_FILE.exists():
                try:
                    if STORAGE_STATE_FILE.stat().st_size > 0:
                        console.print(f"[dim]Loading saved archive.is session...[/dim]")
                        interactive_context_args["storage_state"] = str(STORAGE_STATE_FILE)
                except Exception as e:
                    console.print(f"[yellow]Could not load session: {e}[/yellow]")

            interactive_context = await browser.new_context(**interactive_context_args)
            interactive_page = await interactive_context.new_page()

            try:
                await stealth_async(interactive_page)
            except:
                pass

            # Validate session immediately if interactive
            console.print("[bold yellow]Validating archive.is session...[/bold yellow]")
            try:
                await interactive_page.goto("https://archive.ph/", wait_until="domcontentloaded", timeout=30000)
                content = await interactive_page.content()
                if "challenge" in content.lower() or "captcha" in content.lower() or "just a moment" in content.lower():
                    console.print("[bold red]CAPTCHA detected! Please solve it in the browser window.[/bold red]")
                    # Wait loop
                    while True:
                        if session.check_shutdown(): break
                        content = await interactive_page.content()
                        if "challenge" not in content.lower() and "captcha" not in content.lower():
                            console.print("[bold green]CAPTCHA solved![/bold green]")
                            await interactive_page.context.storage_state(path=str(STORAGE_STATE_FILE))
                            # Share the authenticated context with ArchiveScraper
                            ArchiveScraper.set_shared_context(browser, interactive_page.context, headful=headful)
                            break
                        await asyncio.sleep(1)
                else:
                    console.print("[bold green]Session appears valid.[/bold green]")
                    # Share the valid session context with ArchiveScraper
                    ArchiveScraper.set_shared_context(browser, interactive_page.context, headful=headful)
            except Exception as e:
                console.print(f"[yellow]Session validation warning: {e}[/yellow]")

        scraper = UnifiedScraper(
            browser=browser,
            context=context,
            strategies=strategies,
            rate_limiter=limiter,
            interactive_mode=interactive,
            interactive_page=interactive_page,
            max_retries=max_retries,
            headful=headful,
            lean_mode=lean_mode,
            use_selenium=use_selenium
        )

        total_processed = 0

        try:
            while True:
                if session.check_shutdown():
                    break

                await session.wait_if_paused()

                pending_count = get_pending_scrape_count()
                pending_opinions = get_pending_opinion_count()

                priority_msg = "[bold yellow]ON[/bold yellow]" if prioritize_opinion else "[dim]OFF[/dim]"
                console.print(
                    f"\n[dim]Total pending: {pending_count} | Suspected Opinions: {pending_opinions} "
                    f"| Priority: {priority_msg}[/dim]"
                )

                urls_to_process = get_urls_to_scrape(
                    batch_size=batch_size,
                    prioritize_opinion=prioritize_opinion,
                    retry_failed=retry_failed,
                    newest_first=not oldest_first
                )

                if not urls_to_process:
                    console.print("[bold green]No more URLs to scrape.[/bold green]")
                    break

                if info_only:
                    console.print(f"Found {len(urls_to_process)} URLs to scrape (Info Only).")
                    for u in urls_to_process:
                        print(f" - {u[1]} (Score: {u[3]})")
                    break

                console.print(f"Processing batch of {len(urls_to_process)} URLs...")

                pending_success_urls: List[str] = []

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Scraping...", total=len(urls_to_process))

                    for i in range(0, len(urls_to_process), concurrency):
                        if session.check_shutdown():
                            break

                        await session.wait_if_paused()

                        sub_batch = urls_to_process[i : i + concurrency]
                        await process_batch(
                            scraper, sub_batch, parquet_store,
                            progress, task, pending_success_urls, session
                        )

                if pending_success_urls:
                    console.print(f"[dim]Flushing {len(pending_success_urls)} articles to disk...[/dim]")
                    saved_path = parquet_store.flush()

                    if saved_path:
                        console.print(f"[dim]Updating DB status for {len(pending_success_urls)} items...[/dim]")
                        for url in pending_success_urls:
                            update_scraped_status(url, 'success', None)
                    else:
                        logging.error("Failed to flush to parquet despite successful scrapes. DB not updated.")

                total_processed += len(urls_to_process)

                if session.check_shutdown():
                    break

        finally:
            # Clear shared context before closing browser
            ArchiveScraper.clear_shared_context()
            await context.close()
            if interactive_page:
                await interactive_page.context.close()
            await browser.close()
            if stealth_connector:
                stealth_connector.close()
            # End Selenium archive session
            if selenium_session_started:
                console.print("[dim]Ending Selenium archive session...[/dim]")
                SeleniumArchiveScraper.end_session()
            parquet_store.close()

    console.print(f"\n[bold green]Scraping finished. Processed {total_processed} URLs.[/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified scraper with full fallback chain.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG level logging (default: INFO)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet mode (WARNING level logging)")
    parser.add_argument("-b", "--batch-size", type=int, default=50, help="Batch size for fetching from DB")
    parser.add_argument("-c", "--concurrency", type=int, default=4, help="Concurrent tabs")
    parser.add_argument("-r", "--rate-limit", type=float, default=0.0, help="Requests per second limit")
    parser.add_argument("--info", action="store_true", help="Just show what would be scraped")
    parser.add_argument("--prioritize-opinion", action="store_true", help="Prioritize opinion articles (default: random order)")
    parser.add_argument("--no-opinion-priority", action="store_true", dest="no_opinion_priority", help="(Deprecated) Same as default random order")
    parser.add_argument("--retry-failed", action="store_true", help="Retry previously failed URLs")
    parser.add_argument("--use-proxy", action="store_true", help="Enable proxy rotation (requires .env config)")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode (visible)")
    parser.add_argument("--max-retries", type=int, default=1, help="Maximum retry attempts per URL (default: 1)")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Enable interactive mode for CAPTCHA solving (implies --headful)")
    parser.add_argument("--stealth-mode", type=str, default="seleniumbase", choices=["standard", "seleniumbase"],
                       help="Stealth mode: 'standard' (Playwright-stealth) or 'seleniumbase' (UC Mode, default)")
    parser.add_argument("--no-headful-switch", action="store_true",
                       help="Disable dynamic headful switching for CAPTCHA (stay headless, use saved session)")
    parser.add_argument("--lean", action="store_true",
                       help="Lean mode: aggressive skip behavior with lower timeouts and minimal retries")
    parser.add_argument("--use-selenium", action="store_true",
                       help="Enable Selenium as final archive fallback (heavy, use sparingly)")
    parser.add_argument("--oldest-first", action="store_true",
                       help="Process oldest articles first by HN score (default: newest first by HN ID)")

    args = parser.parse_args()

    try:
        # Default is random order (no priority). --prioritize-opinion enables priority mode.
        prioritize = args.prioritize_opinion
        asyncio.run(main(
            args.verbose, args.quiet, args.batch_size, args.concurrency, args.rate_limit,
            args.info, prioritize, args.retry_failed, args.use_proxy, args.headful,
            args.max_retries, args.interactive, args.stealth_mode, args.no_headful_switch,
            args.lean, args.use_selenium, args.oldest_first
        ))
    except KeyboardInterrupt:
        pass
