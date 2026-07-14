import asyncio
import errno
import json
from pathlib import Path
from types import SimpleNamespace

from pipeline.src import export_v2, sentiment_v2
from pipeline.src.v2_prefilter import classify
from pipeline.src.v2_schemas import normalize_article_result, normalize_comment_result


def test_candidate_attempt_limit_bounds_deterministic_refill() -> None:
    assert sentiment_v2.candidate_attempt_limit(0, 100) == 0
    assert sentiment_v2.candidate_attempt_limit(7, 7) == 7
    assert sentiment_v2.candidate_attempt_limit(32, 2_507) == 64


def test_call_model_requests_strict_structured_output() -> None:
    captured = {}

    class Completions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"ok": True})))],
                usage=None,
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }

    result = asyncio.run(
        sentiment_v2.call_model(client, "system", "user", lambda value: (value == {"ok": True}, ""), "test", schema)
    )

    assert result is not None
    assert captured["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "test", "strict": True, "schema": schema},
    }


def test_strict_superset_results_normalize_to_immutable_contracts() -> None:
    article = {
        "contract_version": "article-v2.2.0", "reject": True, "scopes": [],
        "dimensions": None, "evidence": [], "summary": None,
        "reason_code": "not_ai", "reason": "Not about AI.",
    }
    comment = {
        "contract_version": "comment-v2.2.0", "comment_id": 7, "reject": True,
        "ai_dimensions": None, "article_relation": None, "parent_relation": None,
        "summary": None, "reason_code": "no_ai_judgment", "reason": "No stance.",
    }

    assert normalize_article_result(article) == {
        "contract_version": "article-v2.2.0", "reject": True,
        "reason_code": "not_ai", "reason": "Not about AI.",
    }
    assert normalize_comment_result(comment) == {
        "contract_version": "comment-v2.2.0", "comment_id": 7, "reject": True,
        "reason_code": "no_ai_judgment", "reason": "No stance.",
    }


def test_prefilter_retries_transient_generation_failure() -> None:
    calls = 0

    class Completions:
        async def create(self, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("json generation failed")
            value = {
                "contract_version": "prefilter-v2.0.0", "eligible": True,
                "scopes": ["research"], "reason_code": "eligible",
                "reason": "Contains an attributable AI claim.",
            }
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))]
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    result = asyncio.run(
        classify(client, {"hn_id": 1, "hn_title": "AI research"}, "AI improves research.")
    )

    assert calls == 2
    assert result is not None


def test_comment_normalizer_repairs_nullable_context_and_long_summary() -> None:
    result = normalize_comment_result(
        {
            "contract_version": "comment-v2.2.0", "comment_id": 7, "reject": False,
            "ai_dimensions": {"capability": {}, "trajectory": {}, "impact": {}},
            "article_relation": None, "parent_relation": None,
            "summary": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twenty-one",
            "reason_code": None, "reason": None,
        }
    )

    assert result["article_relation"] == {
        "relation": "not_applicable", "targets": [], "confidence": 0,
        "rationale": "No article relation provided.",
    }
    assert result["parent_relation"] == {
        "relation": "not_applicable", "confidence": 0,
        "rationale": "No parent relation provided.",
    }
    assert len(result["summary"].split()) == 20


def test_export_publication_survives_overlayfs_directory_rename_exdev(
    tmp_path: Path, monkeypatch,
) -> None:
    output = tmp_path / "v2"
    output.mkdir()
    (output / "stories.json").write_text("old", encoding="utf-8")
    bot_input = tmp_path / "bot-feed.json"
    bot_input.write_text("[]", encoding="utf-8")

    def fake_generation(directory: Path, _bot_input: Path) -> dict:
        directory.mkdir()
        (directory / "stories.json").write_text("new", encoding="utf-8")
        (directory / "manifest.json").write_text("manifest", encoding="utf-8")
        return {"stories": 1}

    def reject_directory_rename(_self: Path, _target: Path) -> Path:
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(export_v2, "init_v2_schema", lambda: None)
    monkeypatch.setattr(export_v2, "write_generation", fake_generation)
    monkeypatch.setattr(Path, "rename", reject_directory_rename)

    result = export_v2.publish_atomic(output, bot_input)

    assert (output / "stories.json").read_text(encoding="utf-8") == "new"
    assert (output / "manifest.json").read_text(encoding="utf-8") == "manifest"
    assert Path(result["rollback"], "stories.json").read_text(encoding="utf-8") == "old"
