import logging
import asyncio
import time

from typing import Optional, Tuple
from playwright.async_api import Playwright, Browser

try:
    from seleniumbase import Driver
    SELENIUMBASE_AVAILABLE = True
except ImportError:
    SELENIUMBASE_AVAILABLE = False

logger = logging.getLogger(__name__)

class StealthConnector:
    """
    Connects Playwright to a stealth Chrome instance launched by SeleniumBase.

    This combines the stealth capabilities of SeleniumBase/undetected-chromedriver
    with the API ergonomics of Playwright.
    """

    def __init__(self):
        self._driver = None
        self._cdp_endpoint = None

    async def launch_stealth_browser(self, p: Playwright, headless: bool = True) -> Optional[Browser]:
        """
        Launch a stealth browser and connect Playwright to it.
        """
        if not SELENIUMBASE_AVAILABLE:
            logger.error("SeleniumBase not installed. Cannot launch stealth browser.")
            return None

        logger.info("Launching stealth browser with SeleniumBase Driver...")

        try:
            # Use SeleniumBase Driver class directly (simpler than SB context manager)
            # uc=True enables undetected-chromedriver mode
            # incognito=True helps bypass some detection
            self._driver = Driver(
                uc=True,
                headless=headless,
                incognito=True,
            )

            # Give the browser a moment to fully initialize
            time.sleep(1)

            # Navigate to a blank page to start
            self._driver.get("about:blank")

            # Get CDP Endpoint from capabilities
            # undetected-chromedriver exposes debuggerAddress in capabilities
            caps = self._driver.capabilities
            debugger_address = caps.get("goog:chromeOptions", {}).get("debuggerAddress")

            if not debugger_address:
                # Try alternative location
                debugger_address = caps.get("chrome", {}).get("debuggerAddress")

            if not debugger_address:
                logger.error("Could not find debuggerAddress in Selenium capabilities")
                logger.debug(f"Capabilities: {caps}")
                self.close()
                return None

            self._cdp_endpoint = f"http://{debugger_address}"
            logger.info(f"Stealth browser listening at {self._cdp_endpoint}")

            # Connect Playwright via CDP
            try:
                browser = await p.chromium.connect_over_cdp(self._cdp_endpoint)
                return browser
            except Exception as e:
                logger.error(f"Failed to connect Playwright to CDP: {e}")
                self.close()
                return None

        except Exception as e:
            logger.error(f"Failed to launch SeleniumBase: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.close()
            return None

    def close(self):
        """Clean up the SeleniumBase driver."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception as e:
                logger.error(f"Error closing SeleniumBase driver: {e}")
            finally:
                self._driver = None
                self._cdp_endpoint = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
