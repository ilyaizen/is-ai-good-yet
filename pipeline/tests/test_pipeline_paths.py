from __future__ import annotations

from pathlib import Path

from pipeline.src.store.paths import (
    get_articles_dir,
    get_articles_text_dir,
    get_pipeline_data_dir,
    get_pipeline_db_path,
)


def test_explicit_database_path_controls_shared_storage(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "volume" / "pipeline.db"
    monkeypatch.setenv("PIPELINE_DB_PATH", str(db_path))
    monkeypatch.delenv("PIPELINE_DATA_DIR", raising=False)
    monkeypatch.delenv("PIPELINE_STORAGE_DIR", raising=False)

    assert get_pipeline_db_path() == db_path.resolve()
    assert get_pipeline_data_dir() == db_path.parent.resolve()
    assert get_articles_dir() == (db_path.parent / "articles").resolve()
    assert get_articles_text_dir() == (db_path.parent / "articles-text").resolve()


def test_explicit_data_dir_controls_database_and_articles(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "pipeline-data"
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(data_dir))
    monkeypatch.delenv("PIPELINE_DB_PATH", raising=False)

    assert get_pipeline_data_dir() == data_dir.resolve()
    assert get_pipeline_db_path() == (data_dir / "pipeline.db").resolve()
    assert get_articles_dir() == (data_dir / "articles").resolve()
    assert get_articles_text_dir() == (data_dir / "articles-text").resolve()
