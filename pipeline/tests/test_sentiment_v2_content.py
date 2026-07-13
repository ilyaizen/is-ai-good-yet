from pathlib import Path

import polars as pl

from pipeline.src.store.text_store import TextArticleStore
from pipeline.src import sentiment_v2


def test_get_article_content_falls_back_to_text_store_for_missing_parquet_url(
    tmp_path: Path, monkeypatch,
) -> None:
    text_store = TextArticleStore(tmp_path / "articles-text")
    text_store.save_article(
        202,
        "Text-only article",
        None,
        None,
        "https://example.com/text-only",
        "Body from the reconciled text store.",
    )
    parquet = pl.DataFrame(
        {
            "url": ["https://example.com/parquet"],
            "text": ["Body from Parquet."],
        }
    ).lazy()
    monkeypatch.setattr(sentiment_v2, "read_articles", lambda _directory: parquet)
    monkeypatch.setattr(sentiment_v2, "TextArticleStore", lambda: text_store)

    content = sentiment_v2.get_article_content(
        [
            {"hn_id": 101, "url": "https://example.com/parquet"},
            {"hn_id": 202, "url": "https://example.com/text-only"},
        ]
    )

    assert content == {
        "https://example.com/parquet": "Body from Parquet.",
        "https://example.com/text-only": "Body from the reconciled text store.",
    }
