"""V2 prompt voice and anti-hedging contract.

The v2.4.0 prompts port V1's blunt verdict voice onto the broader capability/trajectory/impact
scope. This test guards the normative contract: the prompts must (a) adopt the blunt-analyst
persona, (b) include signal words and decision examples, and (c) explicitly forbid hedging
phrases ("seems to", "possibly", "may suggest") so summaries read as verdicts, not descriptions.
It reads the pipeline source directly so it runs without the LLM or heavy pipeline deps.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SENTIMENT_SRC = (REPO_ROOT / "pipeline" / "src" / "sentiment_v2.py").read_text(encoding="utf-8")
MODELS_SRC = (REPO_ROOT / "pipeline" / "src" / "v2_models.py").read_text(encoding="utf-8")


def _triple_quoted(name: str, source: str) -> str:
    match = re.search(name + r'\s*=\s*f?"""([\s\S]*?)"""', source)
    assert match, f"{name} not found in pipeline source"
    return match.group(1)


ARTICLE_PROMPT = _triple_quoted("ARTICLE_PROMPT", SENTIMENT_SRC)
COMMENT_PROMPT = _triple_quoted("COMMENT_PROMPT", SENTIMENT_SRC)

HEDGING_PHRASES = ("seems to", "possibly", "may suggest")


def test_pinned_versions() -> None:
    # Analysis stays v2.3.0: an ANALYSIS_VERSION bump would invalidate every prior run and empty the
    # dashboard. Only the prompt texts move to v2.4.0.
    assert re.search(r'ANALYSIS_VERSION\s*=\s*"v2\.3\.0"', MODELS_SRC)
    assert re.search(r'PARSER_VERSION\s*=\s*"v2\.3\.1"', MODELS_SRC)
    assert 'ARTICLE_PROMPT_VERSION = "article-prompt-v2.4.0"' in SENTIMENT_SRC
    assert 'COMMENT_PROMPT_VERSION = "comment-prompt-v2.4.0"' in SENTIMENT_SRC


def test_prompts_adopt_blunt_analyst_voice() -> None:
    for prompt in (ARTICLE_PROMPT, COMMENT_PROMPT):
        assert "blunt, skeptical analyst" in prompt
        assert "verdict" in prompt.lower()


def test_prompts_include_signal_words_and_decision_examples() -> None:
    for prompt in (ARTICLE_PROMPT, COMMENT_PROMPT):
        assert "signal words" in prompt.lower()
        assert "decision examples" in prompt.lower()


def test_comment_prompt_forbids_hedging_rationales() -> None:
    """A known fixture: the comment prompt must reject hedging in favor of a position."""
    forbidden_present = [phrase for phrase in HEDGING_PHRASES if phrase in COMMENT_PROMPT]
    assert forbidden_present == list(HEDGING_PHRASES), (
        "comment prompt must name the hedging phrases it forbids"
    )
    assert re.search(r"forbid hedging", COMMENT_PROMPT, re.IGNORECASE)


def test_article_summary_must_be_a_verdict_not_a_description() -> None:
    assert "discusses" in ARTICLE_PROMPT or "covers" in ARTICLE_PROMPT
    assert re.search(r"reject any summary that only describes", ARTICLE_PROMPT, re.IGNORECASE)


def test_article_summary_cap_is_40_words() -> None:
    assert re.search(r"ARTICLE_SUMMARY_MAX_WORDS\s*=\s*40", MODELS_SRC)
    # The prompt references the cap by placeholder, which renders to 40 at runtime.
    assert "ARTICLE_SUMMARY_MAX_WORDS" in ARTICLE_PROMPT
