import asyncio
import logging
import sys
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.stealth_connector import StealthConnector

# Configure logging
logging.basicConfig(level=logging.INFO)

@pytest.mark.asyncio
async def test_stealth_browser():
    async with async_playwright() as p:
        connector = StealthConnector()
        try:
            print("Launching stealth browser...")
            browser = await connector.launch_stealth_browser(p, headless=True)

            if not browser:
                print("Failed to launch browser")
                return

            print("Browser connected! creating page...")
            page = await browser.new_page()

            print("Navigating to bot check...")
            await page.goto("https://nowsecure.nl")
            await page.wait_for_timeout(5000)

            title = await page.title()
            print(f"Page title: {title}")

            await page.screenshot(path="stealth_test.png")
            print("Screenshot saved to stealth_test.png")

            await browser.close()
            print("Browser closed")

        finally:
            connector.close()
            print("Connector closed")

if __name__ == "__main__":
    asyncio.run(test_stealth_browser())
