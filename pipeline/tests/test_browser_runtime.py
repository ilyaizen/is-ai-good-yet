from __future__ import annotations

from pipeline.src.browser_runtime import resolve_chromium_executable


def test_explicit_chromium_path_wins() -> None:
    executable = resolve_chromium_executable(
        environ={"PIPELINE_CHROMIUM_EXECUTABLE": "/custom/chromium"},
        which=lambda _name: "/path/chromium",
        is_file=lambda candidate: candidate == "/custom/chromium",
    )

    assert executable == "/custom/chromium"


def test_system_chromium_is_used_without_playwright_download() -> None:
    executable = resolve_chromium_executable(
        environ={},
        which=lambda name: "/root/.nix-profile/bin/chromium" if name == "chromium" else None,
        is_file=lambda candidate: candidate == "/root/.nix-profile/bin/chromium",
    )

    assert executable == "/root/.nix-profile/bin/chromium"
