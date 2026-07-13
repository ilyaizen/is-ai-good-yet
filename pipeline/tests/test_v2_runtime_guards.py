import asyncio
import json
from types import SimpleNamespace

from pipeline.src import sentiment_v2
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
