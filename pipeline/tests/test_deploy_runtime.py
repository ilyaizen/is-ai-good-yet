from __future__ import annotations

from pathlib import Path


def test_nixpacks_exposes_cpp_runtime_to_python_extensions() -> None:
    config = Path(__file__).resolve().parents[2] / "nixpacks.toml"
    text = config.read_text(encoding="utf-8")
    assert '"stdenv.cc.cc.lib"' in text


def test_newspaper_clean_html_dependency_is_explicit() -> None:
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    names = {
        line.split("#", 1)[0].strip().lower().replace("_", "-")
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    }
    assert "lxml-html-clean" in names
    assert "setuptools<81" in names
