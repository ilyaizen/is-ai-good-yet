"""Stealth and anti-bot utilities for Playwright scraping."""

import random
from typing import Dict, Any, Tuple


# Pool of real browser user agents (Chrome, Firefox, Edge - updated 2025)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Mobile Chrome (for variety)
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# Common desktop viewport resolutions
VIEWPORTS = [
    {"width": 1920, "height": 1080},  # Full HD
    {"width": 1366, "height": 768},   # Laptop standard
    {"width": 1440, "height": 900},   # MacBook
    {"width": 1536, "height": 864},   # Common laptop
    {"width": 2560, "height": 1440},  # 2K
    {"width": 1680, "height": 1050},  # 16:10
]

# Language preferences (weighted towards English)
LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
]


def get_random_user_agent() -> str:
    """Get a random user agent from the pool.

    Returns:
        Random user agent string
    """
    return random.choice(USER_AGENTS)


def get_random_viewport() -> Dict[str, int]:
    """Get a random viewport dimension.

    Returns:
        Dict with 'width' and 'height' keys
    """
    return random.choice(VIEWPORTS).copy()


def get_browser_context_options(use_proxy: bool = False, proxy_config: Dict[str, str] = None) -> Dict[str, Any]: # type: ignore
    """Generate randomized browser context options.

    Args:
        use_proxy: Whether to include proxy configuration
        proxy_config: Proxy configuration dict with 'server', 'username', 'password'

    Returns:
        Dict of context options for Playwright
    """
    options: Dict[str, Any] = {
        "viewport": get_random_viewport(),
        "user_agent": get_random_user_agent(),
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "permissions": [],
        "geolocation": None,
        "color_scheme": random.choice(["light", "dark"]),
        "extra_http_headers": {
            "Accept-Language": random.choice(LANGUAGES),
        },
    }

    # Add proxy if enabled
    if use_proxy and proxy_config:
        options["proxy"] = proxy_config

    return options


async def apply_human_timing(page: Any, min_delay: float = 2.0, max_delay: float = 5.0) -> None:
    """Apply human-like timing delays and mouse movements.

    Args:
        page: Playwright page object
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    import asyncio

    # Random delay
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)

    # Random mouse movements (simulate reading/browsing)
    try:
        viewport = page.viewport_size
        if viewport:
            # Move to random positions (3-5 movements)
            movements = random.randint(3, 5)
            for _ in range(movements):
                x = random.randint(100, viewport["width"] - 100)
                y = random.randint(100, viewport["height"] - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception:
        # If mouse movement fails, just continue
        pass


async def scroll_randomly(page: Any) -> None:
    """Scroll the page randomly to simulate human reading behavior.

    Args:
        page: Playwright page object
    """
    import asyncio

    try:
        # Get page height
        scroll_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = page.viewport_size["height"] if page.viewport_size else 1080

        # Scroll down in random increments
        current_position = 0
        max_scroll = min(scroll_height, viewport_height * 3)  # Don't scroll too far

        while current_position < max_scroll:
            # Random scroll increment
            scroll_by = random.randint(100, 400)
            current_position += scroll_by

            await page.evaluate(f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(random.uniform(0.2, 0.5))

            # 30% chance to stop early (like skimming)
            if random.random() < 0.3:
                break

        # Scroll back to top before extraction
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(random.uniform(0.3, 0.6))

    except Exception:
        # If scrolling fails, just continue
        pass


def get_random_delay_range() -> Tuple[float, float]:
    """Get a random delay range for timing variation.

    Returns:
        Tuple of (min_delay, max_delay) in seconds
    """
    # Vary the delay ranges to avoid patterns
    ranges = [
        (2.0, 5.0),
        (3.0, 6.0),
        (2.5, 5.5),
        (1.5, 4.0),
        (2.0, 8.0),  # Occasionally longer delays
    ]
    return random.choice(ranges)
