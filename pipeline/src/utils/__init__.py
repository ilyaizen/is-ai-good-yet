"""Utility modules for scraping."""

import logging
import sys

def setup_logging():
    """
    Configures the root logger.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

from .stealth_utils import (
    get_random_user_agent,
    get_random_viewport,
    get_browser_context_options,
    apply_human_timing,
    scroll_randomly,
    get_random_delay_range
)

from .proxy_manager import ProxyRotator
from .stealth_connector import StealthConnector

__all__ = [
    "setup_logging",
    "get_random_user_agent",
    "get_random_viewport",
    "get_browser_context_options",
    "apply_human_timing",
    "scroll_randomly",
    "get_random_delay_range",
    "ProxyRotator",
    "StealthConnector",
]
