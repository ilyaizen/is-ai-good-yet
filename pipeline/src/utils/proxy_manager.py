"""Proxy rotation and management for scraping."""

import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
import random


@dataclass
class ProxyConfig:
    """Proxy configuration data."""
    server: str
    username: Optional[str] = None
    password: Optional[str] = None


class ProxyRotator:
    """Manages proxy rotation and health tracking."""

    def __init__(self):
        """Initialize proxy rotator from environment variables."""
        self.proxies: List[ProxyConfig] = []
        self.current_index = 0
        self.request_count = 0
        self.rotation_interval = int(os.getenv("PROXY_ROTATION_INTERVAL", "10"))
        self.failed_proxies: Dict[str, int] = {}  # Track failures per proxy
        self.max_failures = 3

        self._load_proxies_from_env()

    def _load_proxies_from_env(self) -> None:
        """Load proxy configuration from environment variables."""
        proxy_server = os.getenv("PROXY_SERVER", "").strip()

        if not proxy_server:
            logging.info("No proxy configuration found in environment variables")
            return

        proxy_username = os.getenv("PROXY_USERNAME", "").strip() or None
        proxy_password = os.getenv("PROXY_PASSWORD", "").strip() or None

        # Single proxy configuration
        proxy = ProxyConfig(
            server=proxy_server,
            username=proxy_username,
            password=proxy_password
        )
        self.proxies.append(proxy)

        logging.info(f"Loaded 1 proxy configuration: {proxy_server}")

    def is_enabled(self) -> bool:
        """Check if proxy rotation is enabled.

        Returns:
            True if proxies are configured
        """
        return len(self.proxies) > 0

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy in rotation.

        Returns:
            Proxy configuration dict for Playwright, or None if no proxies available
        """
        if not self.proxies:
            return None

        # Increment request count
        self.request_count += 1

        # Rotate proxy if needed
        if self.request_count % self.rotation_interval == 0:
            self.current_index = (self.current_index + 1) % len(self.proxies)
            logging.debug(f"Rotating to proxy index {self.current_index}")

        proxy = self.proxies[self.current_index]

        # Check if proxy has too many failures
        if self.failed_proxies.get(proxy.server, 0) >= self.max_failures:
            logging.warning(f"Proxy {proxy.server} has exceeded max failures, skipping")
            # Try next proxy
            self.current_index = (self.current_index + 1) % len(self.proxies)
            proxy = self.proxies[self.current_index]

        # Build Playwright proxy dict
        proxy_dict: Dict[str, str] = {
            "server": proxy.server
        }

        if proxy.username and proxy.password:
            proxy_dict["username"] = proxy.username
            proxy_dict["password"] = proxy.password

        return proxy_dict

    def report_failure(self, proxy_server: str) -> None:
        """Report a proxy failure for health tracking.

        Args:
            proxy_server: The proxy server that failed
        """
        if proxy_server not in self.failed_proxies:
            self.failed_proxies[proxy_server] = 0

        self.failed_proxies[proxy_server] += 1
        logging.warning(f"Proxy {proxy_server} failure count: {self.failed_proxies[proxy_server]}")

    def report_success(self, proxy_server: str) -> None:
        """Report a successful proxy use (resets failure count).

        Args:
            proxy_server: The proxy server that succeeded
        """
        if proxy_server in self.failed_proxies:
            self.failed_proxies[proxy_server] = max(0, self.failed_proxies[proxy_server] - 1)

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get a random proxy (instead of sequential rotation).

        Returns:
            Proxy configuration dict for Playwright, or None if no proxies available
        """
        if not self.proxies:
            return None

        # Filter out proxies with too many failures
        healthy_proxies = [
            p for p in self.proxies
            if self.failed_proxies.get(p.server, 0) < self.max_failures
        ]

        if not healthy_proxies:
            logging.warning("All proxies have failed, using any available proxy")
            healthy_proxies = self.proxies

        proxy = random.choice(healthy_proxies)

        # Build Playwright proxy dict
        proxy_dict: Dict[str, str] = {
            "server": proxy.server
        }

        if proxy.username and proxy.password:
            proxy_dict["username"] = proxy.username
            proxy_dict["password"] = proxy.password

        return proxy_dict
