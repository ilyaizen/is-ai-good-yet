"""Throwaway v2.4.0 prompt probe: real Groq call + real validators on fuzzy/OOD inputs.

Validates that the rewritten article/comment prompts produce valid contract JSON and sound verdicts
on hard, out-of-distribution inputs NOT present in the prompt's own examples. No DB, no upstream
pipeline. Costs a handful of gpt-oss-20b calls. Delete after use.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from groq import AsyncGroq

from src.sentiment_v2 import (
    ARTICLE_PROMPT, COMMENT_PROMPT, MODEL, MODEL_PARAMETERS, call_model,
)
from src.v2_models import validate_article_analysis, validate_comment_analysis
from src.v2_schemas import (
    ARTICLE_SCHEMA, COMMENT_SCHEMA, normalize_article_result, normalize_comment_result,
)

load_dotenv()

ARTICLES = [
    {
        "title": "Hospital deploys tumor-screening AI after pilot",
        "body": (
            "Mercy General rolled out an AI screening tool across its radiology wing this month. "
            "In an internal pilot the model flagged 12% more early-stage tumors than the prior "
            "human-only workflow, though clinicians noted it systematically under-performed on "
            "denser tissue scans common in younger patients, missing roughly one in eight lesions "
            "there. The hospital says the net effect is more cancers caught overall, but its own "
            "ethics board warned the gap could widen existing age-based disparities in detection. "
            "The vendor declined to release the held-out evaluation set. Nurses reported the "
            "integrated workflow saved roughly 40 minutes per shift once staff trusted it."
        ),
    },
    {
        "title": "AI datacenter buildout strains regional grids",
        "body": (
            "Three utility operators told regulators that new AI training clusters have pushed "
            "peak winter demand past forecasts for the second year running, delaying coal-plant "
            "retirements that were meant to shore up emissions targets. The operators stress the "
            "clusters themselves are unremarkable engineering; the friction is purely grid capacity "
            "and the carbon accounting of deferred clean-energy milestones. A county commissioner "
            "called the economic influx from construction jobs real but 'front-loaded and thin', "
            "and questioned whether the long-horizon tax base would outlast the hardware refresh "
            "cycle. No one disputes the clusters run the models they claim to run."
        ),
    },
]

COMMENTS = [
    {
        "id": 100001,
        "text": (
            "Wow, only took me three hours of prompt-wrangling to get it to print 'hello world' "
            "without hallucinating an import. Truly the dawn of a new era."
        ),
    },
    {
        "id": 100002,
        "text": "Unrelated, but does anyone have a dentist recommendation in the East Bay?",
    },
    {
        "id": 100003,
        "text": (
            "The article's 99% accuracy headline is marketing. The actual paper reports 71% on the "
            "held-out set, and that's before domain shift. I've seen the same gap in our own evals."
        ),
    },
]


def comment_packet(title: str, comment_id: int, text: str) -> str:
    thesis = {"status": "unavailable"}
    voting = {"comment_id": comment_id, "text": text}
    return (
        f"[ARTICLE TITLE — CONTEXT ONLY]\n{title}\n\n"
        f"[STRUCTURED ARTICLE THESIS — CONTEXT ONLY]\n"
        f"{json.dumps(thesis, ensure_ascii=False, sort_keys=True)}\n\n"
        f"[ROOT COMMENT — CONTEXT ONLY]\n{json.dumps(None, ensure_ascii=False)}\n\n"
        f"[PARENT COMMENT — CONTEXT ONLY]\n{json.dumps(None, ensure_ascii=False)}\n\n"
        f"[VOTING COMMENT — ONLY TEXT TO ANNOTATE]\n"
        f"{json.dumps(voting, ensure_ascii=False)}"
    )


async def probe_article(client: AsyncGroq, title: str, body: str) -> None:
    user_prompt = f"Title: {title}\n\n<UNTRUSTED_ARTICLE>\n{body}\n</UNTRUSTED_ARTICLE>"
    # Harness checks contract validity + judgment only; skip the evidence-substring guard.
    resp = await call_model(
        client, ARTICLE_PROMPT, user_prompt, validate_article_analysis,
        "v2_article_analysis", ARTICLE_SCHEMA, normalize_article_result,
    )
    print(f"\n===== ARTICLE: {title} =====")
    if not resp:
        print("  !! NO VALID RESPONSE (both attempts failed validation)")
        return
    result, metrics = resp
    print(f"  reject={result.get('reject')}  scopes={result.get('scopes')}")
    for name, dim in (result.get("dimensions") or {}).items():
        print(f"  {name:11s} score={dim['score']} conf={dim['confidence']} "
              f"applicability={dim['applicability']} :: {dim['rationale']}")
    print(f"  summary: {result.get('summary')}")
    print(f"  tokens: in={metrics['input_tokens']} out={metrics['output_tokens']}")


async def probe_comment(client: AsyncGroq, title: str, comment_id: int, text: str) -> None:
    user_prompt = comment_packet(title, comment_id, text)
    resp = await call_model(
        client, COMMENT_PROMPT, user_prompt,
        lambda r: validate_comment_analysis(r, comment_id),
        "v2_comment_analysis", COMMENT_SCHEMA, normalize_comment_result,
    )
    print(f"\n----- COMMENT #{comment_id}: {text[:70]!r} -----")
    if not resp:
        print("  !! NO VALID RESPONSE (both attempts failed validation)")
        return
    result, metrics = resp
    if result.get("reject"):
        print(f"  REJECTED reason_code={result.get('reason_code')}: {result.get('reason')}")
    else:
        for name, dim in (result.get("ai_dimensions") or {}).items():
            print(f"  {name:11s} score={dim['score']} conf={dim['confidence']} "
                  f"basis={dim.get('stance_basis')} :: {dim['rationale']}")
        ar = result.get("article_relation") or {}
        pr = result.get("parent_relation") or {}
        print(f"  article_relation={ar.get('relation')} parent_relation={pr.get('relation')}")
        print(f"  summary: {result.get('summary')}")
    print(f"  tokens: in={metrics['input_tokens']} out={metrics['output_tokens']}")


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ponytail: Windows cp1252 console chokes on model em-dashes/hyphens
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY missing", file=sys.stderr)
        sys.exit(1)
    comments_only = "--comments-only" in sys.argv
    print(f"model={MODEL} params={MODEL_PARAMETERS}")
    client = AsyncGroq(api_key=api_key)
    if not comments_only:
        for art in ARTICLES:
            await probe_article(client, art["title"], art["body"])
    for com in COMMENTS:
        await probe_comment(client, ARTICLES[0]["title"], com["id"], com["text"])


if __name__ == "__main__":
    asyncio.run(main())
