"""Authenticated single-browser rendered-HTML service for a residential node."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .article_fetch import is_public_http_url, redact_url

logger = logging.getLogger(__name__)


def verify_secret(configured: str, provided: str | None) -> None:
    if not configured:
        raise RuntimeError("Residential fetcher secret is not configured.")
    if len(configured) < 24:
        raise RuntimeError("Residential fetcher secret must be at least 24 characters.")
    if provided is None or not secrets.compare_digest(provided, configured):
        raise PermissionError("unauthorized")


@dataclass(frozen=True)
class ResidentialSettings:
    secret: str
    headless: bool
    navigation_timeout_ms: int
    settle_seconds: float
    max_html_bytes: int

    @classmethod
    def from_environment(cls) -> "ResidentialSettings":
        return cls(
            secret=os.getenv("RESIDENTIAL_FETCHER_SECRET", "").strip(),
            headless=os.getenv("RESIDENTIAL_FETCHER_HEADLESS", "0").lower()
            in {"1", "true", "yes"},
            navigation_timeout_ms=int(
                os.getenv("RESIDENTIAL_FETCHER_NAVIGATION_TIMEOUT_MS", "45000")
            ),
            settle_seconds=float(os.getenv("RESIDENTIAL_FETCHER_SETTLE_SECONDS", "2")),
            max_html_bytes=int(
                os.getenv("RESIDENTIAL_FETCHER_MAX_HTML_BYTES", str(2 * 1024 * 1024))
            ),
        )


class ResidentialBrowser:
    def __init__(self, settings: ResidentialSettings) -> None:
        self.settings = settings
        self._playwright: Any = None
        self._browser: Any = None
        self._launch_lock = asyncio.Lock()
        self._fetch_semaphore = asyncio.Semaphore(1)

    async def start(self) -> None:
        if self._browser and self._browser.is_connected():
            return
        async with self._launch_lock:
            if self._browser and self._browser.is_connected():
                return
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.settings.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                ],
            )

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def fetch(self, url: str) -> dict[str, str | None]:
        if not is_public_http_url(url):
            return {"status": "error", "html": None, "final_url": None, "error": "unsafe_url"}
        async with self._fetch_semaphore:
            await self.start()
            context = await self._browser.new_context(locale="en-US")
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()
            safe_origins: dict[tuple[str, str, int | None], bool] = {}

            async def guard_route(route: Any) -> None:
                request_url = route.request.url
                parsed = urlsplit(request_url)
                scheme = parsed.scheme
                if scheme in {"http", "https"}:
                    origin = (scheme, parsed.hostname or "", parsed.port)
                    safe = safe_origins.get(origin)
                    if safe is None:
                        safe = await asyncio.to_thread(is_public_http_url, request_url)
                        safe_origins[origin] = safe
                    if not safe:
                        await route.abort("blockedbyclient")
                        return
                await route.continue_()

            await page.route("**/*", guard_route)
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.navigation_timeout_ms,
                )
                try:
                    await page.wait_for_load_state(
                        "networkidle", timeout=min(20_000, self.settings.navigation_timeout_ms)
                    )
                except Exception:
                    pass
                await asyncio.sleep(self.settings.settle_seconds)
                final_url = page.url
                if not is_public_http_url(final_url):
                    return {
                        "status": "error",
                        "html": None,
                        "final_url": None,
                        "error": "unsafe_redirect",
                    }
                html = await page.content()
                encoded = html.encode("utf-8")
                if len(encoded) > self.settings.max_html_bytes:
                    return {
                        "status": "error",
                        "html": None,
                        "final_url": final_url,
                        "error": "response_too_large",
                    }
                logger.info("Residential fetch succeeded: %s", redact_url(final_url))
                return {"status": "ok", "html": html, "final_url": final_url, "error": None}
            except Exception as error:
                logger.warning(
                    "Residential fetch failed for %s: %s",
                    redact_url(url),
                    type(error).__name__,
                )
                return {
                    "status": "error",
                    "html": None,
                    "final_url": None,
                    "error": type(error).__name__,
                }
            finally:
                await context.close()


def create_app(settings: ResidentialSettings | None = None):
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel

    active_settings = settings or ResidentialSettings.from_environment()
    browser = ResidentialBrowser(active_settings)

    class FetchRequest(BaseModel):
        url: str

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if not active_settings.secret:
            logger.error("RESIDENTIAL_FETCHER_SECRET is required before /fetch can be used.")
        yield
        await browser.close()

    app = FastAPI(title="Pipeline Residential HTML Fetcher", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok" if active_settings.secret else "misconfigured",
            "authentication": "configured" if active_settings.secret else "missing",
        }

    @app.post("/fetch")
    async def fetch(
        request: FetchRequest,
        x_fetcher_secret: str | None = Header(default=None),
    ) -> dict[str, str | None]:
        try:
            verify_secret(active_settings.secret, x_fetcher_secret)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=403, detail="unauthorized") from error
        return await browser.fetch(request.url)

    return app
