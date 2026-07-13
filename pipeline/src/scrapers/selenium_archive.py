"""
Selenium-based Archive.is scraper using undetected-chromedriver.

This module bypasses Cloudflare protection by using undetected-chromedriver,
which patches Chrome to avoid detection. This is significantly more effective
than Playwright for sites with aggressive bot protection like archive.is.

Features:
- PERSISTENT BROWSER SESSION: Single browser instance reused across all URLs
- Session persistence: Loads/saves cookies from archive_session.json
- CAPTCHA memory: Solved CAPTCHAs are remembered across runs
- Dynamic headful switching: Auto-switches to visible mode for CAPTCHA solving
- Smart session validation: Validates cookies before starting headless scraping

Usage:
    # Session-based usage (recommended):
    session = SeleniumArchiveScraper.start_session(headless=True)
    for url in urls:
        result = await session.fetch_from_archive(url)
    SeleniumArchiveScraper.end_session()
"""

import asyncio
import json
import logging
import random
import re
import time
import threading
from functools import partial

from typing import Optional, Dict, List, Any, Tuple, cast

try:
    import undetected_chromedriver as uc # type: ignore
    from selenium.webdriver.common.by import By # type: ignore
    from selenium.webdriver.support.ui import WebDriverWait # type: ignore
    from selenium.webdriver.support import expected_conditions as EC # type: ignore
    from selenium.common.exceptions import TimeoutException, WebDriverException # type: ignore
    SELENIUM_AVAILABLE = True

    # Patch undetected_chromedriver to suppress Windows handle errors during cleanup
    import sys
    if sys.platform == 'win32' and hasattr(uc, 'Chrome'):
        _original_chrome_del = uc.Chrome.__del__
        def _patched_chrome_del(self):
            try:
                _original_chrome_del(self)
            except OSError:
                pass  # Suppress WinError 6: The handle is invalid
        uc.Chrome.__del__ = _patched_chrome_del

except ImportError:
    SELENIUM_AVAILABLE = False
    uc = None  # type: ignore

import trafilatura
from store.paths import get_data_path

logger = logging.getLogger(__name__)


class SeleniumArchiveScraper:
    """
    Archive.is scraper using undetected-chromedriver (Selenium).

    This scraper bypasses Cloudflare by using a patched Chrome driver
    that removes automation fingerprints at a lower level than Playwright.

    Key Features:
    - PERSISTENT BROWSER: Uses a single browser instance for the entire batch
    - SESSION VALIDATION: Validates saved cookies before headless scraping
    - DYNAMIC HEADFUL SWITCHING: Auto-switches to visible mode when CAPTCHA detected
    - COOKIE PERSISTENCE: Saves/loads session cookies across runs
    """

    ARCHIVE_DOMAINS = ["archive.ph", "archive.is", "archive.today"]

    # Session file path for cookie persistence
    SESSION_FILE = get_data_path("archive_session.json")

    # Class-level rate limiting
    _last_request_time = 0.0
    _min_interval = 2.0  # Minimum seconds between requests (reduced for faster scraping)

    # Class-level PERSISTENT driver for browser reuse
    _persistent_driver = None
    _persistent_headless: bool = True  # Track current headless state
    _session_validated: bool = False  # Track if session has been validated
    _session_cookies_loaded: bool = False  # Track if we've loaded cookies to driver
    _disable_headful_switch: bool = False  # If True, never switch to headful mode for CAPTCHAs

    # Thread lock for browser operations (prevents concurrent driver creation/access)
    _driver_lock = threading.Lock()

    def __init__(self, headless: bool = True, timeout: int = 60):
        """
        Initialize the Selenium archive scraper.

        Args:
            headless: If True, run browser in headless mode. Set to False for manual CAPTCHA solving.
            timeout: Maximum wait time for page loads (seconds)
        """
        self.headless = headless
        self.timeout = timeout

    @classmethod
    def start_session(cls, headless: bool = True, validate: bool = True, disable_headful_switch: bool = False) -> "SeleniumArchiveScraper":
        """
        Start a persistent browser session for batch scraping.

        This validates the session upfront and switches to headful if needed.

        Args:
            headless: Preferred headless mode (may switch to headful for CAPTCHA)
            validate: If True, validate session cookies before starting
            disable_headful_switch: If True, never switch to headful mode automatically

        Returns:
            SeleniumArchiveScraper instance with persistent browser ready
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("undetected-chromedriver not installed")

        cls._disable_headful_switch = disable_headful_switch

        if disable_headful_switch:
            logger.info("[SESSION] Starting persistent browser session (headful switch DISABLED)...")
        else:
            logger.info("[SESSION] Starting persistent browser session...")

        instance = cls(headless=headless)

        if validate and not disable_headful_switch:
            # Validate session and possibly switch to headful for CAPTCHA
            # Skip validation if headful switch is disabled (we'll just run headless)
            instance._validate_and_prepare_session()
        elif validate and disable_headful_switch:
            # Just create the driver and load cookies, no switching
            instance._get_or_create_driver(force_headless=True)

        return instance

    @classmethod
    def end_session(cls):
        """End the persistent browser session and clean up."""
        if cls._persistent_driver:
            logger.info("[SESSION] Ending persistent browser session...")
            try:
                cls._safe_quit_driver_static(cls._persistent_driver)
            finally:
                cls._persistent_driver = None
                cls._session_validated = False
                cls._session_cookies_loaded = False

    @classmethod
    def _safe_quit_driver_static(cls, driver):
        """Static method to safely quit driver."""
        if driver is None:
            return
        try:
            import sys
            import os
            if sys.platform == 'win32':
                old_stderr = sys.stderr
                sys.stderr = open(os.devnull, 'w')
                try:
                    driver.quit()
                finally:
                    sys.stderr.close()
                    sys.stderr = old_stderr
            else:
                driver.quit()
        except Exception:
            pass

    def _get_or_create_driver(self, force_headless: Optional[bool] = None) -> Optional[Any]:
        """
        Get the persistent driver or create one if needed.

        Args:
            force_headless: Override headless setting (for switching modes)

        Returns:
            The Selenium WebDriver instance or None if creation failed
        """
        headless = force_headless if force_headless is not None else self.headless

        # If we have a driver but need different headless mode, restart it
        if SeleniumArchiveScraper._persistent_driver:
            if SeleniumArchiveScraper._persistent_headless != headless:
                logger.info(f"[SESSION] Switching browser mode: headless={headless}")
                self._restart_browser(headless=headless)
            return SeleniumArchiveScraper._persistent_driver

        # Create new driver
        return self._create_persistent_driver(headless=headless)

    def _create_persistent_driver(self, headless: bool = True) -> Any:
        """Create a new persistent driver."""
        if not SELENIUM_AVAILABLE:
            raise ImportError("undetected-chromedriver not installed")

        logger.info(f"[SESSION] Creating persistent browser (headless={headless})...")

        options = uc.ChromeOptions() # type: ignore

        # Basic stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--enable-javascript')

        # Window positioning for visibility when headful
        if not headless:
            options.add_argument('--start-maximized')
            options.add_argument('--window-position=100,100')
        else:
            # Randomize window size for fingerprint variance
            widths = [1920, 1680, 1440, 1366]
            heights = [1080, 900, 800, 768]
            options.add_argument(f'--window-size={random.choice(widths)},{random.choice(heights)}')

        # Set a realistic language
        options.add_argument('--lang=en-US')

        # Create the driver with undetected-chromedriver
        driver = uc.Chrome( # type: ignore
            options=options,
            headless=headless,
            use_subprocess=True,
            version_main=None  # Auto-detect Chrome version
        )

        # Set page load timeout
        driver.set_page_load_timeout(self.timeout)

        # Inject stealth scripts
        self._inject_stealth_scripts(driver)

        # Store as persistent driver
        SeleniumArchiveScraper._persistent_driver = driver
        SeleniumArchiveScraper._persistent_headless = headless
        SeleniumArchiveScraper._session_cookies_loaded = False

        # Load session cookies
        self._load_session_cookies(driver)

        return driver

    def _restart_browser(self, headless: bool):
        """Restart the browser with different headless setting."""
        # Save cookies before closing
        if SeleniumArchiveScraper._persistent_driver:
            self._save_session_cookies(SeleniumArchiveScraper._persistent_driver)
            self._safe_quit_driver(SeleniumArchiveScraper._persistent_driver)

        SeleniumArchiveScraper._persistent_driver = None
        SeleniumArchiveScraper._session_cookies_loaded = False

        # Create new driver with new headless setting
        self._create_persistent_driver(headless=headless)
        self.headless = headless

    def _validate_and_prepare_session(self):
        """
        Validate the saved session and prepare for scraping.

        If session is invalid or no cookies exist, switches to headful mode
        for CAPTCHA solving, then switches back to headless.
        """
        logger.info("[SESSION] Validating saved session...")

        # Check if session file exists and has cookies
        if not self.SESSION_FILE.exists():
            logger.info("[SESSION] No saved session found - will need CAPTCHA solve")
            self._prepare_for_captcha()
            return

        try:
            with open(self.SESSION_FILE, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            cookies = session_data.get("cookies", [])
            if not cookies:
                logger.info("[SESSION] Empty session file - will need CAPTCHA solve")
                self._prepare_for_captcha()
                return
        except Exception as e:
            logger.warning(f"[SESSION] Failed to read session: {e}")
            self._prepare_for_captcha()
            return

        # Create headless driver and test the session
        driver = self._get_or_create_driver(force_headless=True)

        # Check if driver was successfully created
        if driver is None:
            logger.error("[SESSION] Failed to create browser driver for session validation")
            return

        # Test if session is valid by loading archive.is
        try:
            logger.info("[SESSION] Testing session validity...")
            driver.get("https://archive.ph/")
            time.sleep(3)

            if self._is_cloudflare_challenge(driver):
                logger.warning("[SESSION] Cloudflare challenge detected - session invalid")
                self._prepare_for_captcha()
            else:
                logger.info("[SESSION] Session is valid! Proceeding with headless scraping.")
                SeleniumArchiveScraper._session_validated = True

        except Exception as e:
            logger.warning(f"[SESSION] Session test failed: {e}")
            self._prepare_for_captcha()

    def _prepare_for_captcha(self):
        """Switch to headful mode and wait for CAPTCHA to be solved."""
        logger.info("[SESSION] Switching to headful mode for CAPTCHA solving...")

        # Restart in headful mode
        if SeleniumArchiveScraper._persistent_driver:
            self._restart_browser(headless=False)
        else:
            self._create_persistent_driver(headless=False)

        driver = SeleniumArchiveScraper._persistent_driver

        # Check if driver was successfully created
        if driver is None:
            logger.error("[SESSION] Failed to create browser driver for CAPTCHA solving")
            return

        # Bring browser window to foreground for visibility
        try:
            driver.switch_to.window(driver.current_window_handle)
            driver.maximize_window()
            # Force window to front using JavaScript
            driver.execute_script("window.focus();")
            logger.info("[SESSION] Browser window brought to foreground")
        except Exception as e:
            logger.debug(f"Could not focus browser window: {e}")

        # Navigate to archive.is to trigger CAPTCHA
        try:
            driver.get("https://archive.ph/")
            time.sleep(1)  # Reduced from 2s

            if self._is_cloudflare_challenge(driver):
                logger.warning(">>> MANUAL ACTION REQUIRED: Solve the CAPTCHA in the browser window! <<<")

                # Wait for CAPTCHA to be solved (up to 180 seconds)
                solved = self._wait_for_cloudflare(driver, timeout=180)

                if solved:
                    logger.info("[SESSION] CAPTCHA solved! Saving session...")
                    self._save_session_cookies(driver)
                    SeleniumArchiveScraper._session_validated = True
                else:
                    logger.error("[SESSION] CAPTCHA was not solved within timeout")
            else:
                logger.info("[SESSION] No CAPTCHA needed - session works")
                self._save_session_cookies(driver)
                SeleniumArchiveScraper._session_validated = True

        except Exception as e:
            logger.error(f"[SESSION] Error during CAPTCHA preparation: {e}")

    def _switch_to_headful_for_captcha(self, driver) -> bool:
        """
        Switch to headful mode when Cloudflare is detected during headless scraping.

        Returns:
            True if CAPTCHA was solved, False otherwise
        """
        if not SeleniumArchiveScraper._persistent_headless:
            # Already headful, just wait for solve
            return self._wait_for_cloudflare(driver, timeout=180)

        logger.info("[CLOUDFLARE] Detected in headless mode - switching to headful...")

        # Save current URL
        current_url = driver.current_url

        # Restart in headful mode
        self._restart_browser(headless=False)
        driver = SeleniumArchiveScraper._persistent_driver

        # Check if driver was successfully created
        if driver is None:
            logger.error("[CLOUDFLARE] Failed to create browser driver for CAPTCHA solving")
            return False

        # Bring browser window to foreground for visibility
        try:
            driver.switch_to.window(driver.current_window_handle)
            driver.maximize_window()
            driver.execute_script("window.focus();")
            logger.info("[SESSION] Browser window brought to foreground")
        except Exception as e:
            logger.debug(f"Could not focus browser window: {e}")

        # Navigate back to the URL
        driver.get(current_url)
        time.sleep(1)  # Reduced from 2s

        logger.warning(">>> MANUAL ACTION REQUIRED: Solve the CAPTCHA in the browser window! <<<")

        # Wait for CAPTCHA
        solved = self._wait_for_cloudflare(driver, timeout=180)

        if solved:
            logger.info("[SESSION] CAPTCHA solved! Saving session...")
            self._save_session_cookies(driver)

        return solved

    def _load_session_cookies(self, driver) -> bool:
        """
        Load cookies from the session file into the driver.

        Returns True if cookies were loaded successfully.
        """
        if SeleniumArchiveScraper._session_cookies_loaded:
            return True

        if not self.SESSION_FILE.exists():
            logger.debug("No session file found - starting fresh session")
            return False

        try:
            with open(self.SESSION_FILE, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            cookies = session_data.get("cookies", [])
            if not cookies:
                logger.debug("Session file has no cookies")
                return False

            # Navigate to a domain first to set cookies
            loaded_count = 0
            for domain in self.ARCHIVE_DOMAINS:
                try:
                    # Filter cookies for this domain
                    domain_cookies = [
                        c for c in cookies
                        if domain in c.get("domain", "") or c.get("domain", "").endswith(domain)
                    ]

                    if domain_cookies:
                        # Navigate to domain first
                        driver.get(f"https://{domain}/")
                        time.sleep(1)

                        for cookie in domain_cookies:
                            try:
                                # Clean cookie for Selenium format
                                selenium_cookie = {
                                    "name": cookie["name"],
                                    "value": cookie["value"],
                                    "domain": cookie.get("domain", f".{domain}"),
                                    "path": cookie.get("path", "/"),
                                }
                                # Optional fields
                                if "expiry" in cookie:
                                    selenium_cookie["expiry"] = int(cookie["expiry"])
                                elif "expires" in cookie:
                                    selenium_cookie["expiry"] = int(cookie["expires"])
                                if cookie.get("secure"):
                                    selenium_cookie["secure"] = True
                                if cookie.get("httpOnly"):
                                    selenium_cookie["httpOnly"] = True

                                driver.add_cookie(selenium_cookie)
                                loaded_count += 1
                            except Exception as e:
                                logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")
                                continue
                except Exception as e:
                    logger.debug(f"Error loading cookies for {domain}: {e}")
                    continue

            if loaded_count > 0:
                logger.info(f"[SESSION] Loaded {loaded_count} cookies from saved session")
                SeleniumArchiveScraper._session_cookies_loaded = True
                return True

            return False

        except Exception as e:
            logger.warning(f"Failed to load session cookies: {e}")
            return False

    def _save_session_cookies(self, driver) -> bool:
        """
        Save cookies from the driver to the session file.

        This persists CAPTCHA solutions so they can be reused.
        Returns True if cookies were saved successfully.
        """
        try:
            # Get all cookies from the driver
            cookies = driver.get_cookies()

            if not cookies:
                logger.debug("No cookies to save")
                return False

            # Load existing session data to preserve localStorage (if any)
            existing_data: Dict[str, Any] = {"cookies": [], "origins": []}
            if self.SESSION_FILE.exists():
                try:
                    with open(self.SESSION_FILE, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            # Convert cookies to Playwright-compatible format for consistency
            formatted_cookies: List[Dict[str, Any]] = []
            for cookie in cookies:
                formatted_cookie: Dict[str, Any] = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie.get("domain", ""),
                    "path": cookie.get("path", "/"),
                    "httpOnly": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", False),
                    "sameSite": cookie.get("sameSite", "Lax"),
                }
                if "expiry" in cookie:
                    formatted_cookie["expires"] = cookie["expiry"]
                formatted_cookies.append(formatted_cookie)

            # Merge with existing cookies (newer cookies take precedence)
            existing_cookies = {(c["name"], c.get("domain", "")): c for c in existing_data.get("cookies", [])}
            for cookie in formatted_cookies:
                existing_cookies[(cookie["name"], cookie.get("domain", ""))] = cookie

            # Write back
            session_data = {
                "cookies": list(existing_cookies.values()),
                "origins": existing_data.get("origins", []),
            }

            # Ensure data directory exists
            self.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(self.SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)

            logger.info(f"[SESSION] Saved {len(formatted_cookies)} cookies to session file")
            return True

        except Exception as e:
            logger.warning(f"Failed to save session cookies: {e}")
            return False

    def _inject_stealth_scripts(self, driver):
        """Inject JavaScript to help bypass Cloudflare detection and auto-click challenges."""
        try:
            # Comprehensive stealth script
            stealth_js = """
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

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
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // Override permissions query to avoid detection
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );

            // Mock WebGL vendor and renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, arguments);
            };

            // Disable automation flags in window object
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_js})
        except Exception as e:
            logger.debug(f"Could not inject stealth scripts: {e}")

    def _is_cloudflare_challenge(self, driver, wait_for_auto_solve: bool = False) -> bool:
        """
        Check if we're on a Cloudflare challenge page.

        Args:
            wait_for_auto_solve: If True, wait a few seconds and re-check to allow
                                 automatic challenge resolution (JS challenges, cookies)
        """
        try:
            page_source = driver.page_source.lower()
            indicators = [
                "just a moment",
                "checking your browser",
                "cloudflare",
                "ray id",
                "security check",
                "challenge-platform",
                "cf-spinner",
            ]
            is_challenge = any(indicator in page_source for indicator in indicators)

            if is_challenge and wait_for_auto_solve:
                # Wait a bit and check again - many challenges auto-solve via JS or cookies
                logger.debug("[CLOUDFLARE] Challenge detected, waiting for auto-solve...")
                for _ in range(3):  # Wait up to 6 seconds total
                    time.sleep(2)
                    page_source = driver.page_source.lower()
                    if not any(indicator in page_source for indicator in indicators):
                        logger.info("[CLOUDFLARE] Challenge auto-solved!")
                        return False
                    # Try auto-click while waiting
                    self._try_cloudflare_auto_click(driver)

            return is_challenge
        except Exception:
            return False

    def _wait_for_cloudflare(self, driver, timeout: int = 120) -> bool:
        """
        Wait for Cloudflare challenge to be solved.

        In headless mode, this waits for automatic JavaScript challenges.
        In headful mode, this allows time for manual CAPTCHA solving.

        Returns True if challenge was solved, False if timeout.
        """
        logger.info("Cloudflare challenge detected. Waiting for resolution...")

        if not SeleniumArchiveScraper._persistent_headless:
            logger.info(">>> MANUAL ACTION REQUIRED: Solve the CAPTCHA in the browser window! <<<")

        start_time = time.time()
        auto_click_attempted = False

        while time.time() - start_time < timeout:
            # Try to auto-click Cloudflare Turnstile challenge
            if not auto_click_attempted:
                auto_click_attempted = self._try_cloudflare_auto_click(driver)
                if auto_click_attempted:
                    logger.info("Attempted Cloudflare Turnstile auto-click...")
                    time.sleep(3)  # Wait for response after click

            if not self._is_cloudflare_challenge(driver):
                # Check if we've navigated to actual content
                current_url = driver.current_url
                if re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}', current_url):
                    logger.info("Cloudflare challenge solved! Continuing...")
                    return True

                # Also check if page has substantial content
                try:
                    body_text = driver.find_element(By.TAG_NAME, 'body').text
                    if len(body_text) > 500:
                        logger.info("Page loaded with content. Continuing...")
                        return True
                except Exception:
                    pass

            time.sleep(2)

        logger.warning("Timeout waiting for Cloudflare challenge resolution")
        return False

    def _try_cloudflare_auto_click(self, driver) -> bool:
        """
        Attempt to automatically click Cloudflare Turnstile checkbox.

        Returns True if click was attempted, False otherwise.
        """
        try:
            # JavaScript to find and click Cloudflare Turnstile elements
            auto_click_js = """
            (function() {
                // Try to find Turnstile iframe
                const iframes = document.querySelectorAll('iframe[src*="challenges.cloudflare.com"]');
                for (const iframe of iframes) {
                    try {
                        // Make iframe visible if hidden
                        iframe.style.display = 'block';
                        iframe.style.visibility = 'visible';
                        iframe.style.opacity = '1';

                        // Try to access the checkbox inside (same-origin only)
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (iframeDoc) {
                            const checkbox = iframeDoc.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                checkbox.click();
                                return true;
                            }

                            // Try clicking any clickable element that looks like a verify button
                            const clickables = iframeDoc.querySelectorAll('[class*="verify"], [class*="checkbox"], [role="checkbox"]');
                            for (const el of clickables) {
                                el.click();
                                return true;
                            }
                        }
                    } catch (e) {
                        // Cross-origin access denied - that's expected
                    }
                }

                // Try direct page elements
                const selectors = [
                    '#challenge-stage input[type="checkbox"]',
                    '.cf-turnstile input',
                    'input[name="cf-turnstile-response"]',
                    '[data-callback="onTurnstileCallback"]',
                    '.challenge-form button',
                    '#challenge-form button[type="submit"]'
                ];

                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el) {
                        el.click();
                        return true;
                    }
                }

                return false;
            })();
            """

            result = driver.execute_script(auto_click_js)
            if result:
                return True

            # Also try direct element clicking with Selenium
            clickable_selectors = [
                (By.CSS_SELECTOR, 'iframe[src*="challenges.cloudflare"]'),
                (By.CSS_SELECTOR, '.cf-turnstile'),
                (By.CSS_SELECTOR, '#challenge-stage'),
                (By.XPATH, '//input[@type="checkbox"]'),
            ]

            for by, selector in clickable_selectors:
                try:
                    elements = driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed():
                            # Move to element first (human-like behavior)
                            from selenium.webdriver.common.action_chains import ActionChains
                            actions = ActionChains(driver)
                            actions.move_to_element(element).pause(random.uniform(0.1, 0.3)).click().perform()
                            return True
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.debug(f"Cloudflare auto-click failed: {e}")
            return False

    def _is_valid_archive_page(self, driver, url: str) -> bool:
        """Check if we're on a valid archived page (not search results or error page)."""
        try:
            current_url = driver.current_url

            # Check URL pattern for archived pages
            if re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}$', current_url):
                return True

            # Check for "no results" indicators
            page_source = driver.page_source.lower()
            no_results_indicators = [
                "no results",
                "0 results",
                "not in the archive",
                "hasn't been archived",
                "has not been archived",
                "save this url",
                "enter the url",
            ]

            if any(indicator in page_source for indicator in no_results_indicators):
                return False

            # If we're still on /newest/ URL with search results, try to find and click the first result
            if '/newest/' in current_url or '/search/' in current_url:
                try:
                    # Look for archive result links
                    links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="archive."]')
                    for link in links:
                        href = link.get_attribute('href')
                        if href and re.match(r'https?://archive\.(is|today|ph|li|md)/[a-zA-Z0-9]{5,}$', href):
                            logger.info(f"Found archive link in results: {href}")
                            link.click()
                            time.sleep(3)  # Wait for navigation
                            return True
                except Exception as e:
                    logger.debug(f"Error clicking archive link: {e}")

                return False

            # Default to checking if there's substantial body content
            try:
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                return len(body_text) > 1000
            except Exception:
                return False

        except Exception as e:
            logger.debug(f"Error validating archive page: {e}")
            return False

    def _extract_content(self, html: str, original_url: str) -> Optional[Dict]:
        """Extract article content from HTML using trafilatura."""
        try:
            # Clean archive.is header elements
            patterns = [
                r'<div[^>]*id="HEADER"[^>]*>.*?</div>',
                r'<form[^>]*id="SAVEFORM"[^>]*>.*?</form>',
                r'<div[^>]*class="HEADER"[^>]*>.*?</div>',
                r'<input[^>]*type="hidden"[^>]*name="url"[^>]*>',
            ]

            for pattern in patterns:
                html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)

            # Extract with trafilatura - use favor_recall for more complete content
            doc = trafilatura.bare_extraction(
                html,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
                no_fallback=False,
                with_metadata=True,
                url=original_url
            )

            if not doc:
                return None

            text = doc.get("text", "").strip()  # type: ignore

            if len(text) < 100:
                return None

            # Verify content isn't garbage
            text_lower = text.lower()
            garbage_indicators = [
                "we use cookies", "accept all cookies", "cookie policy",
                "subscribe now", "create a free account", "already a subscriber",
                "please enable javascript"
            ]
            garbage_count = sum(1 for indicator in garbage_indicators if indicator in text_lower)
            if garbage_count >= 3 or (len(text) < 500 and garbage_count >= 2):
                logger.debug("Content appears to be garbage (cookie notices, etc.)")
                return None

            return {
                "title": doc.get("title", ""),  # type: ignore
                "author": doc.get("author", ""),  # type: ignore
                "publish_date": doc.get("date", ""),  # type: ignore
                "text": text,
                "word_count": len(text.split()),
            }

        except Exception as e:
            logger.debug(f"Trafilatura extraction error: {e}")
            return None

    def _fetch_sync(self, url: str) -> Optional[Dict]:
        """
        Synchronous method to fetch from archive.is using PERSISTENT BROWSER.
        This is run in a thread pool executor from the async wrapper.

        Uses the persistent browser session for efficiency and cookie reuse.
        SERIALIZED via _driver_lock to prevent concurrent browser access.
        """
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium/undetected-chromedriver not available")
            return None

        # Acquire lock - only ONE thread can use the Selenium browser at a time
        # This prevents race conditions in browser creation and concurrent tab access
        with SeleniumArchiveScraper._driver_lock:
            # Rate limiting
            now = time.time()
            time_since_last = now - SeleniumArchiveScraper._last_request_time
            if time_since_last < SeleniumArchiveScraper._min_interval:
                sleep_time = SeleniumArchiveScraper._min_interval - time_since_last
                logger.debug(f"Rate limiting: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)

            SeleniumArchiveScraper._last_request_time = time.time()

            # Get or create persistent driver (now thread-safe)
            driver = self._get_or_create_driver()

            # Check if driver was successfully created
            if driver is None:
                logger.error("Failed to get or create browser driver")
                return None

            # Use a local variable with type assertion for Pylance
            # This helps the type checker understand driver is not None
            active_driver: Any = driver

            try:
                # Try each archive domain
                for domain in self.ARCHIVE_DOMAINS:
                    archive_url = f"https://{domain}/newest/{url}"
                    logger.info(f"[SELENIUM] Trying: {archive_url[:70]}...")

                    try:
                        # Add human-like delay (shorter since we reuse browser)
                        time.sleep(random.uniform(0.5, 1.0))

                        active_driver.get(archive_url)

                        # Wait for page to load
                        time.sleep(1)

                        # Check for Cloudflare - use wait_for_auto_solve to give cookies/JS time to work
                        if self._is_cloudflare_challenge(active_driver, wait_for_auto_solve=True):
                            logger.warning(f"[CLOUDFLARE] Challenge persists on {domain}")

                            # If headful switching is disabled, just skip this domain
                            if SeleniumArchiveScraper._disable_headful_switch:
                                logger.info(f"[CLOUDFLARE] Headful switch disabled, skipping {domain}")
                                continue

                            # If headless, switch to headful for CAPTCHA
                            if SeleniumArchiveScraper._persistent_headless:
                                solved = self._switch_to_headful_for_captcha(active_driver)
                                if not solved:
                                    logger.warning(f"Cloudflare not solved on {domain}")
                                    continue
                                # Get the driver again (it was replaced during switch)
                                active_driver = SeleniumArchiveScraper._persistent_driver
                                # Check if driver is still valid after switch
                                if active_driver is None:
                                    logger.error(f"Driver became None after switching to headful for {domain}")
                                    continue
                                # Re-navigate after switch
                                active_driver.get(archive_url)
                                time.sleep(2)
                            else:
                                # Already headful, just wait
                                if not self._wait_for_cloudflare(active_driver, timeout=180):
                                    logger.warning(f"Cloudflare timeout on {domain}")
                                    continue

                            # Save cookies after solving
                            self._save_session_cookies(active_driver)

                        # Check for rate limiting
                        page_source = active_driver.page_source
                        if "429" in active_driver.title or "rate limit" in page_source.lower():
                            logger.warning(f"Rate limited on {domain}")
                            SeleniumArchiveScraper._min_interval = min(60, SeleniumArchiveScraper._min_interval * 1.5)
                            continue

                        # Verify we're on a valid archive page
                        if not self._is_valid_archive_page(active_driver, url):
                            logger.debug(f"Not a valid archive page on {domain}")
                            continue

                        # Scroll to load lazy content
                        try:
                            active_driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(0.5)
                            active_driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(0.3)
                            active_driver.execute_script("window.scrollTo(0, 0);")
                        except Exception:
                            pass

                        # Get the final HTML
                        html = active_driver.page_source

                        if not html or len(html) < 1000:
                            continue

                        # Try to get iframe content if present
                        try:
                            iframes = active_driver.find_elements(By.TAG_NAME, 'iframe')
                            for iframe in iframes:
                                try:
                                    active_driver.switch_to.frame(iframe)
                                    frame_html = active_driver.page_source
                                    if len(frame_html) > len(html):
                                        html = frame_html
                                    active_driver.switch_to.default_content()
                                except Exception:
                                    active_driver.switch_to.default_content()
                        except Exception:
                            pass

                        # Extract content
                        result = self._extract_content(html, url)
                        if result:
                            logger.info(f"[SELENIUM SUCCESS] {domain}: {result.get('word_count', 0)} words")
                            # Save session cookies on success
                            self._save_session_cookies(active_driver)
                            return result

                    except TimeoutException:
                        logger.debug(f"Page load timeout on {domain}")
                        continue
                    except WebDriverException as e:
                        logger.debug(f"WebDriver error on {domain}: {e}")
                        continue
                    except Exception as e:
                        logger.debug(f"Error on {domain}: {e}")
                        continue

                    # Shorter backoff between domains (browser stays warm)
                    time.sleep(random.uniform(1, 3))

                return None

            except Exception as e:
                logger.error(f"Selenium archive scraper error: {e}")
                return None
            # NOTE: We do NOT quit the driver here - it's persistent!


    def _safe_quit_driver(self, driver):
        """Safely quit the driver, suppressing Windows handle errors."""
        if driver is None:
            return
        try:
            import sys
            import os
            if sys.platform == 'win32':
                old_stderr = sys.stderr
                sys.stderr = open(os.devnull, 'w')
                try:
                    driver.quit()
                finally:
                    sys.stderr.close()
                    sys.stderr = old_stderr
            else:
                driver.quit()
        except Exception:
            pass
        finally:
            # Force cleanup of any remaining references
            try:
                if hasattr(driver, 'service') and driver.service:
                    driver.service.stop()
            except Exception:
                pass

    async def fetch_from_archive(self, url: str) -> Optional[Dict]:
        """
        Fetch content from archive.is using undetected-chromedriver (async wrapper).

        Args:
            url: The original article URL to look up in archive.is

        Returns:
            Extracted article data or None if not found/failed
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available - skipping SeleniumArchiveScraper")
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(self._fetch_sync, url))


# Convenience function for quick testing
async def test_selenium_scraper():
    """Test the Selenium archive scraper with a sample URL."""
    test_url = "https://www.nytimes.com/2024/01/01/technology/ai-test-article.html"

    # Use session-based approach
    scraper = SeleniumArchiveScraper.start_session(headless=False)  # Start headful for testing
    try:
        result = await scraper.fetch_from_archive(test_url)

        if result:
            print(f"Success! Title: {result.get('title')}")
            print(f"Word count: {result.get('word_count')}")
            print(f"Text preview: {result.get('text', '')[:200]}...")
        else:
            print("Failed to fetch from archive")
    finally:
        SeleniumArchiveScraper.end_session()


if __name__ == "__main__":
    asyncio.run(test_selenium_scraper())
