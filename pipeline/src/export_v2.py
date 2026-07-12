"""Export the isolated, confidence-aware v2 analysis contract."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

from .hn_comments_v2 import SELECTION_VERSION
from .store.v2 import connect_rows, init_v2_schema
from .v2_models import (
    AGGREGATION_VERSION,
    ANALYSIS_VERSION,
    DIMENSIONS,
    combine_sources,
    composite_score,
)


DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent / "src" / "lib" / "data" / "v2"
ARTICLE_WEIGHT = 0.4
COMMUNITY_WEIGHT = 0.6
VERDICT_MONTHS = 12


def influence(hn_score: int, timestamp: int) -> float:
    age_months = max(0, time.time() - timestamp) / (30.44 * 24 * 3600)
    return math.pow(max(1, hn_score), 0.85) * math.pow(0.5, age_months / 24)


def display_score(score: float) -> float:
    return round((max(-2, min(2, score)) + 2) * 25, 1)


def verdict(score: float) -> str:
    displayed = display_score(score)
    if displayed >= 55:
        return "YES"
    if displayed < 45:
        return "NO"
    return "NOT_YET"


def get_run(conn: Any, story_id: int, source: str, selection_version: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM v2_analysis_runs
        WHERE hn_story_id = ? AND source = ? AND analysis_version = ?
          AND selection_version = ? AND status = 'accepted'
        """,
        (story_id, source, ANALYSIS_VERSION, selection_version),
    ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["result_json"] = json.loads(result["result_json"])
    result["parameters_json"] = json.loads(result["parameters_json"])
    result["metrics_json"] = json.loads(result["metrics_json"] or "{}")
    return result


def get_dimensions(
    conn: Any, story_id: int, source: str, selection_version: str,
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT dimension, applicability, score, confidence, disagreement, evidence_count,
               diagnostics_json
        FROM v2_dimension_analyses
        WHERE hn_story_id = ? AND source = ? AND analysis_version = ?
          AND selection_version = ?
        """,
        (story_id, source, ANALYSIS_VERSION, selection_version),
    )
    dimensions = {}
    for row in rows:
        value = dict(row)
        diagnostics = json.loads(value.pop("diagnostics_json") or "{}")
        dimensions[row["dimension"]] = {**value, **diagnostics}
    return dimensions


def export_articles() -> list[dict[str, Any]]:
    conn = connect_rows()
    try:
        stories = conn.execute(
            """
            SELECT u.hn_id, u.hn_title, u.hn_score, u.hn_comments, u.hn_timestamp, u.url
            FROM urls u
            WHERE EXISTS (
                SELECT 1 FROM v2_analysis_runs a
                WHERE a.hn_story_id = u.hn_id AND a.source = 'article'
                  AND a.analysis_version = ? AND a.status = 'accepted'
            )
            ORDER BY u.hn_timestamp DESC
            """,
            (ANALYSIS_VERSION,),
        )
        articles = []
        for story_row in stories:
            story = dict(story_row)
            article_run = get_run(conn, story["hn_id"], "article", "")
            if not article_run:
                continue
            community_run = get_run(conn, story["hn_id"], "community", SELECTION_VERSION)
            article_dimensions = get_dimensions(conn, story["hn_id"], "article", "")
            community_dimensions = (
                get_dimensions(conn, story["hn_id"], "community", SELECTION_VERSION)
                if community_run else {}
            )
            combined = {}
            source_divergence = {}
            for name in DIMENSIONS:
                article_value = article_dimensions[name]
                community_value = community_dimensions.get(
                    name,
                    {
                        "applicability": "not_addressed", "score": None,
                        "confidence": 0.0, "disagreement": None,
                    },
                )
                combined[name] = combine_sources(article_value, community_value, ARTICLE_WEIGHT)
                source_divergence[name] = (
                    abs(article_value["score"] - community_value["score"])
                    if article_value["score"] is not None and community_value["score"] is not None
                    else None
                )
            combined_scores = {name: value["score"] for name, value in combined.items()}
            articles.append(
                {
                    **story,
                    "versions": {
                        "analysis": ANALYSIS_VERSION,
                        "selection": SELECTION_VERSION,
                        "aggregation": AGGREGATION_VERSION,
                    },
                    "article": {
                        "dimensions": article_dimensions,
                        "result": article_run["result_json"],
                        "promptVersion": article_run["prompt_version"],
                        "promptHash": article_run["prompt_hash"],
                        "inputHash": article_run["input_hash"],
                    },
                    "community": (
                        {
                            "dimensions": community_dimensions,
                            "result": community_run["result_json"],
                            "promptVersion": community_run["prompt_version"],
                            "promptHash": community_run["prompt_hash"],
                            "inputHash": community_run["input_hash"],
                            "diagnostics": {
                                name: {
                                    key: community_dimensions[name].get(key)
                                    for key in (
                                        "visibility_weighted_score", "diversity_balanced_score",
                                        "ranking_sensitivity", "positive_share", "neutral_share",
                                        "negative_share", "disagreement", "polarization",
                                        "effective_sample_size", "applicable_comment_count",
                                        "applicable_author_count", "applicable_branch_count",
                                        "dimension_coverage", "clarity", "dissent",
                                    )
                                }
                                for name in DIMENSIONS
                            },
                        }
                        if community_run else None
                    ),
                    "combined": {
                        "dimensions": combined,
                        "composite": composite_score(combined_scores),
                        "addressedDimensions": [
                            name for name, score in combined_scores.items() if score is not None
                        ],
                    },
                    "sourceDivergence": source_divergence,
                }
            )
        return articles
    finally:
        conn.close()


def aggregate(articles: list[dict[str, Any]]) -> dict[str, Any]:
    cutoff = time.time() - (VERDICT_MONTHS * 30.44 * 24 * 3600)
    recent = [item for item in articles if item["hn_timestamp"] >= cutoff]
    totals = {dimension: 0.0 for dimension in DIMENSIONS}
    total_weights = {dimension: 0.0 for dimension in DIMENSIONS}
    counts = {dimension: 0 for dimension in DIMENSIONS}
    for item in recent:
        base_weight = influence(item["hn_score"], item["hn_timestamp"])
        for dimension in DIMENSIONS:
            value = item["combined"]["dimensions"][dimension]
            if value["score"] is None or value["confidence"] <= 0:
                continue
            weight = base_weight * value["confidence"]
            totals[dimension] += value["score"] * weight
            total_weights[dimension] += weight
            counts[dimension] += 1
    scores = {
        dimension: (
            totals[dimension] / total_weights[dimension]
            if total_weights[dimension] else None
        )
        for dimension in DIMENSIONS
    }
    composite = composite_score(scores)
    return {
        "analysisVersion": ANALYSIS_VERSION,
        "selectionVersion": SELECTION_VERSION,
        "aggregationVersion": AGGREGATION_VERSION,
        "sourcePriors": {"article": ARTICLE_WEIGHT, "community": COMMUNITY_WEIGHT},
        "windowMonths": VERDICT_MONTHS,
        "articleCount": len(recent),
        "dimensions": {
            dimension: (
                {
                    "rawScore": round(score, 4),
                    "score": display_score(score),
                    "verdict": verdict(score),
                    "articleCount": counts[dimension],
                }
                if score is not None else None
            )
            for dimension, score in scores.items()
        },
        "composite": (
            {
                "rawScore": round(composite, 4),
                "score": display_score(composite),
                "verdict": verdict(composite),
                "addressedDimensions": [name for name, score in scores.items() if score is not None],
            }
            if composite is not None else None
        ),
    }


def export(output: Path) -> dict[str, Any]:
    init_v2_schema()
    output.mkdir(parents=True, exist_ok=True)
    articles = export_articles()
    verdict_data = aggregate(articles)
    (output / "articles.json").write_text(
        json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output / "verdict.json").write_text(
        json.dumps(verdict_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"articles": len(articles), "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export static v2 sentiment data")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(export(args.output), indent=2))


if __name__ == "__main__":
    main()
