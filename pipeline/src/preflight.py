"""Deterministic production preflight for pipeline command readiness."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlsplit

from .store.paths import get_pipeline_data_dir, get_pipeline_db_path

Check = dict[str, object]


def _ok(reason: str) -> Check:
    return {"ok": True, "reason": reason}


def _failed(reason: str) -> Check:
    return {"ok": False, "reason": reason}


def check_imports(
    modules: Iterable[str], importer: Callable[[str], object] = importlib.import_module
) -> Check:
    for module in modules:
        try:
            importer(module)
        except Exception as error:
            return _failed(f"Python import {module} failed: {type(error).__name__}: {error}")
    return _ok("Required Python imports succeeded.")


def _check_directory_writable(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    descriptor, probe = tempfile.mkstemp(prefix=".pipeline-preflight-", dir=path)
    os.close(descriptor)
    Path(probe).unlink(missing_ok=True)


def check_storage(*, data_dir: Path, db_path: Path) -> Check:
    try:
        data_dir = data_dir.resolve()
        db_path = db_path.resolve()
        _check_directory_writable(data_dir)
        _check_directory_writable(db_path.parent)
        _check_directory_writable(data_dir / "articles")
        if db_path.exists() and not os.access(db_path, os.R_OK | os.W_OK):
            return _failed(f"Pipeline DB is not readable and writable: {db_path}")
        return _ok(f"Pipeline storage is writable; DB path: {db_path}; data dir: {data_dir}.")
    except Exception as error:
        return _failed(f"Pipeline storage check failed: {type(error).__name__}: {error}")


def check_scraper() -> Check:
    scraper_module = f"{__package__}.scraper"
    imports = check_imports(
        [
            "playwright.async_api",
            "playwright_stealth",
            "curl_cffi.requests",
            "trafilatura",
            "newspaper",
            scraper_module,
        ]
    )
    if not imports["ok"]:
        return imports
    stealth_module = importlib.import_module("playwright_stealth")
    if not callable(getattr(stealth_module, "stealth_async", None)):
        return _failed(
            "playwright_stealth imported but does not expose the required stealth_async API."
        )
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executable = Path(playwright.chromium.executable_path)
        if not executable.is_file():
            return _failed(
                "Playwright Chromium is missing. Run: python -m playwright install chromium"
            )
        return _ok(f"Scraper imports succeeded; Chromium found at {executable}.")
    except Exception as error:
        return _failed(f"Playwright browser check failed: {type(error).__name__}: {error}")


def check_residential_config() -> Check:
    base_url = os.getenv("PIPELINE_RESIDENTIAL_FETCHER_URL", "").strip()
    secret = os.getenv("PIPELINE_RESIDENTIAL_FETCHER_SECRET", "").strip()
    if not base_url:
        return _ok("Optional residential fetcher is disabled.")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return _failed("PIPELINE_RESIDENTIAL_FETCHER_URL must be an absolute HTTP(S) URL.")
    if not secret:
        return _failed(
            "Residential fetcher is configured without PIPELINE_RESIDENTIAL_FETCHER_SECRET."
        )
    return _ok(f"Residential fetcher is configured for {parsed.scheme}://{parsed.hostname}.")


def build_snapshot() -> dict[str, Check]:
    core = check_imports(["sqlite3", "polars", "aiohttp", "groq"])
    storage = check_storage(
        data_dir=get_pipeline_data_dir(), db_path=get_pipeline_db_path()
    )
    groq = (
        _ok("GROQ_API_KEY is configured.")
        if os.getenv("GROQ_API_KEY", "").strip()
        else _failed("GROQ_API_KEY is not configured in the application environment.")
    )
    return {
        "python": core,
        "storage": storage,
        "scraper": check_scraper() if core["ok"] else core,
        "groq": groq,
        "residential": check_residential_config(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check pipeline production readiness")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    snapshot = build_snapshot()
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False))
    else:
        for name, result in snapshot.items():
            print(f"{name}: {'OK' if result['ok'] else 'FAILED'} - {result['reason']}")
    raise SystemExit(0 if all(result["ok"] for result in snapshot.values()) else 1)


if __name__ == "__main__":
    main()
