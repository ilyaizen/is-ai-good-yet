"""Safe, bounded HTML fetchers used before browser and archive fallbacks."""

from __future__ import annotations

import asyncio
import ipaddress
import json

import socket
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit


class FetchFailure(str, Enum):
    BLOCKED = "blocked"
    DISABLED = "disabled"
    DNS = "dns"
    EMPTY = "empty"
    HTTP = "http"
    INVALID_RESPONSE = "invalid_response"
    NETWORK = "network"
    NON_HTML = "non_html"
    TIMEOUT = "timeout"
    TOO_LARGE = "too_large"
    UNSAFE_URL = "unsafe_url"


@dataclass(frozen=True)
class HtmlFetchResult:
    html: str | None
    final_url: str | None
    method: str
    failure: FetchFailure | None = None
    detail: str | None = None

    @classmethod
    def failure_result(
        cls, *, method: str, failure: FetchFailure, detail: str
    ) -> "HtmlFetchResult":
        return cls(None, None, method, failure, detail)


def redact_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if parsed.port:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    except Exception:
        return "[REDACTED_URL]"


def resolve_safe_redirect(current_url: str, location: str) -> str | None:
    target = urljoin(current_url, location)
    return target if is_public_http_url(target) else None


def classify_fetch_exception(error: BaseException) -> FetchFailure:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status in {401, 403, 429, 503}:
        return FetchFailure.BLOCKED
    code = getattr(error, "code", None)
    if code == 28 or isinstance(error, asyncio.TimeoutError):
        return FetchFailure.TIMEOUT
    if code == 6:
        return FetchFailure.DNS
    return FetchFailure.NETWORK


def _is_private_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        )
    )


def is_public_http_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        hostname = parsed.hostname.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
            return False
        try:
            return not _is_private_address(hostname)
        except ValueError:
            pass
        try:
            addresses = socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror:
            return False
        return bool(addresses) and all(not _is_private_address(item[4][0]) for item in addresses)
    except (TypeError, ValueError):
        return False


def validate_html_response(
    *,
    url: str,
    final_url: str,
    status: int,
    headers: Mapping[str, str],
    body: bytes,
    max_bytes: int,
    method: str = "http",
) -> HtmlFetchResult:
    safe_url = redact_url(url)
    if not is_public_http_url(final_url):
        return HtmlFetchResult.failure_result(
            method=method,
            failure=FetchFailure.UNSAFE_URL,
            detail=f"Unsafe redirect target while fetching {safe_url}.",
        )
    if status in {401, 403, 429, 503}:
        return HtmlFetchResult.failure_result(
            method=method,
            failure=FetchFailure.BLOCKED,
            detail=f"HTTP {status} while fetching {safe_url}.",
        )
    if status < 200 or status >= 400:
        return HtmlFetchResult.failure_result(
            method=method,
            failure=FetchFailure.HTTP,
            detail=f"HTTP {status} while fetching {safe_url}.",
        )
    content_type = headers.get("content-type", headers.get("Content-Type", "")).lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return HtmlFetchResult.failure_result(
            method=method,
            failure=FetchFailure.NON_HTML,
            detail=f"Non-HTML response while fetching {safe_url}.",
        )
    content_length = headers.get("content-length", headers.get("Content-Length"))
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return HtmlFetchResult.failure_result(
                    method=method,
                    failure=FetchFailure.TOO_LARGE,
                    detail=f"HTML exceeds {max_bytes} bytes for {safe_url}.",
                )
        except ValueError:
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.INVALID_RESPONSE,
                detail=f"Invalid Content-Length while fetching {safe_url}.",
            )
    if len(body) > max_bytes:
        return HtmlFetchResult.failure_result(
            method=method,
            failure=FetchFailure.TOO_LARGE,
            detail=f"HTML exceeds {max_bytes} bytes for {safe_url}.",
        )
    if not body.strip():
        return HtmlFetchResult.failure_result(
            method=method,
            failure=FetchFailure.EMPTY,
            detail=f"Empty HTML response for {safe_url}.",
        )
    return HtmlFetchResult(body.decode("utf-8", errors="ignore"), final_url, method)


class CurlCffiHtmlFetcher:
    def __init__(self, *, timeout_seconds: float, max_bytes: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    async def fetch(self, url: str) -> HtmlFetchResult:
        method = "curl_cffi"
        if not is_public_http_url(url):
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.UNSAFE_URL,
                detail=f"Unsafe URL rejected: {redact_url(url)}.",
            )
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession(
                impersonate="chrome", timeout=self.timeout_seconds, verify=True
            ) as session:
                current_url = url
                for _redirect_count in range(6):
                    if not is_public_http_url(current_url):
                        return HtmlFetchResult.failure_result(
                            method=method,
                            failure=FetchFailure.UNSAFE_URL,
                            detail=f"Unsafe redirect rejected: {redact_url(current_url)}.",
                        )
                    response = await session.get(
                        current_url,
                        allow_redirects=False,
                        stream=True,
                    )
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        await response.aclose()
                        if not location:
                            return HtmlFetchResult.failure_result(
                                method=method,
                                failure=FetchFailure.INVALID_RESPONSE,
                                detail=f"Redirect without Location from {redact_url(current_url)}.",
                            )
                        next_url = resolve_safe_redirect(current_url, location)
                        if next_url is None:
                            return HtmlFetchResult.failure_result(
                                method=method,
                                failure=FetchFailure.UNSAFE_URL,
                                detail=f"Unsafe redirect rejected from {redact_url(current_url)}.",
                            )
                        current_url = next_url
                        continue

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_bytes:
                        await response.aclose()
                        return HtmlFetchResult.failure_result(
                            method=method,
                            failure=FetchFailure.TOO_LARGE,
                            detail=f"HTML exceeds {self.max_bytes} bytes for {redact_url(url)}.",
                        )
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_content():
                        total += len(chunk)
                        if total > self.max_bytes:
                            await response.aclose()
                            return HtmlFetchResult.failure_result(
                                method=method,
                                failure=FetchFailure.TOO_LARGE,
                                detail=f"HTML exceeds {self.max_bytes} bytes for {redact_url(url)}.",
                            )
                        chunks.append(chunk)
                    return validate_html_response(
                        url=url,
                        final_url=current_url,
                        status=response.status_code,
                        headers=response.headers,
                        body=b"".join(chunks),
                        max_bytes=self.max_bytes,
                        method=method,
                    )

                return HtmlFetchResult.failure_result(
                    method=method,
                    failure=FetchFailure.INVALID_RESPONSE,
                    detail=f"Too many redirects while fetching {redact_url(url)}.",
                )
        except asyncio.TimeoutError:
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.TIMEOUT,
                detail=f"HTTP fetch timed out for {redact_url(url)}.",
            )
        except Exception as error:
            response = getattr(error, "response", None)
            status = getattr(response, "status_code", None)
            failure = classify_fetch_exception(error)
            if status:
                detail = f"HTTP {status}"
            elif failure is FetchFailure.TIMEOUT:
                detail = "HTTP fetch timed out"
            elif failure is FetchFailure.DNS:
                detail = "DNS lookup failed"
            else:
                detail = type(error).__name__
            return HtmlFetchResult.failure_result(
                method=method,
                failure=failure,
                detail=f"{detail} while fetching {redact_url(url)}.",
            )


class ResidentialHtmlFetcher:
    def __init__(
        self,
        *,
        base_url: str,
        secret: str,
        timeout_seconds: float,
        max_bytes: int,
    ) -> None:
        self.base_url = base_url.strip()
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    async def fetch(self, url: str) -> HtmlFetchResult:
        method = "residential"
        if not self.base_url:
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.DISABLED,
                detail="Residential fetcher is disabled.",
            )
        if not is_public_http_url(url):
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.UNSAFE_URL,
                detail=f"Unsafe URL rejected: {redact_url(url)}.",
            )
        endpoint = self.base_url.rstrip("/") + "/fetch"
        headers = {"Content-Type": "application/json"}
        if self.secret:
            headers["X-Fetcher-Secret"] = self.secret
        try:
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json={"url": url}, headers=headers) as response:
                    cap = self.max_bytes * 2 + 65_536
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        total += len(chunk)
                        if total > cap:
                            return HtmlFetchResult.failure_result(
                                method=method,
                                failure=FetchFailure.TOO_LARGE,
                                detail="Residential response exceeded the configured byte cap.",
                            )
                        chunks.append(chunk)
                    if response.status != 200:
                        failure = FetchFailure.BLOCKED if response.status in {401, 403, 429, 503} else FetchFailure.HTTP
                        return HtmlFetchResult.failure_result(
                            method=method,
                            failure=failure,
                            detail=f"Residential fetcher returned HTTP {response.status}.",
                        )
            try:
                payload = json.loads(b"".join(chunks))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return HtmlFetchResult.failure_result(
                    method=method,
                    failure=FetchFailure.INVALID_RESPONSE,
                    detail="Residential fetcher returned invalid JSON.",
                )
            html = payload.get("html")
            final_url = payload.get("final_url") or url
            if not isinstance(html, str):
                return HtmlFetchResult.failure_result(
                    method=method,
                    failure=FetchFailure.EMPTY,
                    detail="Residential fetcher returned no HTML.",
                )
            return validate_html_response(
                url=url,
                final_url=final_url,
                status=200,
                headers={"content-type": "text/html"},
                body=html.encode("utf-8"),
                max_bytes=self.max_bytes,
                method=method,
            )
        except asyncio.TimeoutError:
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.TIMEOUT,
                detail="Residential fetcher timed out; optional fallback skipped.",
            )
        except Exception as error:
            return HtmlFetchResult.failure_result(
                method=method,
                failure=FetchFailure.NETWORK,
                detail=f"Residential fetcher unavailable: {type(error).__name__}.",
            )
