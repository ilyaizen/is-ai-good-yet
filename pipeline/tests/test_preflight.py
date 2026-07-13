from __future__ import annotations

import importlib
from pathlib import Path

from pipeline.src.preflight import (
    check_browser_launch,
    check_imports,
    check_residential_config,
    check_storage,
)


def test_import_preflight_preserves_actionable_loader_error() -> None:
    def failing_import(_name: str):
        raise ImportError("libstdc++.so.6: cannot open shared object file")

    result = check_imports(["playwright.async_api"], importer=failing_import)

    assert not result["ok"]
    assert "playwright.async_api" in result["reason"]
    assert "libstdc++.so.6" in result["reason"]


def test_browser_preflight_launches_binary_and_reports_runtime_library_errors() -> None:
    def failing_launch(_executable: str) -> str:
        raise RuntimeError("libglib-2.0.so.0: cannot open shared object file")

    result = check_browser_launch("/nix/store/chromium", launcher=failing_launch)

    assert not result["ok"]
    assert "libglib-2.0.so.0" in result["reason"]


def test_storage_preflight_reports_alignment_and_writability(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "pipeline.db"
    data_dir.mkdir()
    db_path.touch()

    result = check_storage(data_dir=data_dir, db_path=db_path)

    assert result["ok"]
    assert str(db_path.resolve()) in result["reason"]


def test_residential_preflight_rejects_short_secret(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_RESIDENTIAL_FETCHER_URL", "https://residential.example")
    monkeypatch.setenv("PIPELINE_RESIDENTIAL_FETCHER_SECRET", "too-short")

    result = check_residential_config()

    assert not result["ok"]
    assert "at least 24 characters" in result["reason"]
