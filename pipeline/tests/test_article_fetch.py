from __future__ import annotations

import socket

import pytest

from pipeline.src.article_fetch import (
    FetchFailure,
    ResidentialHtmlFetcher,
    classify_fetch_exception,
    is_public_http_url,
    redact_url,
    resolve_safe_redirect,
    validate_html_response,
)


def test_ssrf_guard_rejects_private_and_non_http_targets(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )
    assert not is_public_http_url("http://example.test/article")
    assert not is_public_http_url("file:///etc/passwd")
    assert not is_public_http_url("http://localhost/admin")


def test_html_validation_rejects_wrong_type_and_oversize() -> None:
    wrong_type = validate_html_response(
        url="https://example.com/file.pdf",
        final_url="https://example.com/file.pdf",
        status=200,
        headers={"content-type": "application/pdf"},
        body=b"%PDF",
        max_bytes=1024,
    )
    assert wrong_type.failure == FetchFailure.NON_HTML

    oversized = validate_html_response(
        url="https://example.com/article",
        final_url="https://example.com/article",
        status=200,
        headers={"content-type": "text/html"},
        body=b"x" * 1025,
        max_bytes=1024,
    )
    assert oversized.failure == FetchFailure.TOO_LARGE


def test_redaction_removes_url_credentials_and_query_secrets() -> None:
    value = redact_url("https://user:password@example.com/a?token=secret&x=1")
    assert "password" not in value
    assert "secret" not in value
    assert value == "https://example.com/a"


def test_redirect_to_private_address_is_rejected_before_fetch() -> None:
    assert resolve_safe_redirect("https://example.com/start", "http://127.0.0.1/admin") is None


def test_curl_errors_are_classified_without_exposing_exception_text() -> None:
    timeout = type("CurlError", (Exception,), {"code": 28})()
    dns = type("CurlError", (Exception,), {"code": 6})()
    assert classify_fetch_exception(timeout) is FetchFailure.TIMEOUT
    assert classify_fetch_exception(dns) is FetchFailure.DNS


@pytest.mark.asyncio
async def test_disabled_residential_fetcher_degrades_without_network() -> None:
    fetcher = ResidentialHtmlFetcher(base_url="", secret="", timeout_seconds=1, max_bytes=1024)
    result = await fetcher.fetch("https://example.com")
    assert result.failure is FetchFailure.DISABLED


@pytest.mark.asyncio
async def test_residential_fetcher_sends_secret_and_accepts_rendered_html() -> None:
    from aiohttp import web

    async def handle(request: web.Request) -> web.Response:
        assert request.headers["X-Fetcher-Secret"] == "expected-secret-is-long-enough"
        payload = await request.json()
        assert payload == {"url": "https://example.com"}
        return web.json_response(
            {
                "html": "<html><body>Rendered article text</body></html>",
                "final_url": "https://example.com/article",
            }
        )

    app = web.Application()
    app.router.add_post("/fetch", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        fetcher = ResidentialHtmlFetcher(
            base_url=f"http://127.0.0.1:{port}",
            secret="expected-secret-is-long-enough",
            timeout_seconds=2,
            max_bytes=4096,
        )
        result = await fetcher.fetch("https://example.com")
    finally:
        await runner.cleanup()

    assert result.failure is None
    assert result.method == "residential"
    assert result.final_url == "https://example.com/article"
    assert "Rendered article text" in (result.html or "")
