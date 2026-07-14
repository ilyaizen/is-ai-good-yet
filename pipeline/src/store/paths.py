"""Shared path resolution for pipeline metadata and article storage."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _resolve(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def get_pipeline_db_path() -> Path:
    explicit = os.getenv("PIPELINE_DB_PATH", "").strip()
    if explicit:
        return _resolve(explicit)
    return get_pipeline_data_dir() / "pipeline.db"


def get_pipeline_data_dir() -> Path:
    explicit = os.getenv("PIPELINE_DATA_DIR", "").strip() or os.getenv(
        "PIPELINE_STORAGE_DIR", ""
    ).strip()
    if explicit:
        return _resolve(explicit)
    explicit_db = os.getenv("PIPELINE_DB_PATH", "").strip()
    if explicit_db:
        return _resolve(explicit_db).parent
    return _DEFAULT_DATA_DIR.resolve()


def get_articles_dir() -> Path:
    return get_pipeline_data_dir() / "articles"


def get_articles_text_dir() -> Path:
    return get_pipeline_data_dir() / "articles-text"


def get_data_path(name: str) -> Path:
    return get_pipeline_data_dir() / name
