"""Build and atomically publish the isolated V2 public static generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .hn_comments_v2 import SELECTION_VERSION
from .store.v2 import connect_rows, init_v2_schema
from .store.paths import get_data_path
from .v2_models import (
    AGGREGATION_VERSION,
    ANALYSIS_VERSION,
    DIMENSIONS,
    GLOBAL_INFLUENCE_VERSION,
    PREFILTER_CONTRACT_VERSION,
    combine_sources,
    composite_score,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent.parent / "src" / "lib" / "data" / "v2"
DEFAULT_BOT_INPUT = get_data_path("bot_feed.json")
ARTICLE_WEIGHT = 0.4
COMMUNITY_WEIGHT = 0.6
VERDICT_MONTHS = 12
MANIFEST_VERSION = "v2-manifest-1"
FILE_CONTRACTS = {
    "verdict.json": "verdict-v2.0.0",
    "stories.json": "stories-v2.0.0",
    "history.json": "history-v2.0.0",
    "bot-feed.json": "bot-feed-v2.0.0",
    "pipeline-status.json": "pipeline-status-v2.0.0",
}


def influence(hn_score: int, timestamp: int, now: float | None = None) -> float:
    age_months = max(0, (now or time.time()) - timestamp) / (30.44 * 24 * 3600)
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
    dimensions: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = dict(row)
        diagnostics = json.loads(value.pop("diagnostics_json") or "{}")
        dimensions[row["dimension"]] = {**value, **diagnostics}
    return dimensions


def missing_dimension() -> dict[str, Any]:
    return {
        "applicability": "not_addressed", "score": None, "confidence": 0.0,
        "disagreement": None, "rationale": "Source did not address this dimension.",
    }


def attach_public_dissent_excerpt(conn: Any, dimensions: dict[str, dict[str, Any]]) -> None:
    for value in dimensions.values():
        dissent = value.get("dissent")
        if not dissent or not dissent.get("comment_id"):
            continue
        row = conn.execute(
            "SELECT text FROM hn_comments WHERE hn_comment_id = ?", (dissent["comment_id"],),
        ).fetchone()
        if row and row["text"]:
            dissent["excerpt"] = row["text"][:360]


def export_stories() -> list[dict[str, Any]]:
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
        exported = []
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
            attach_public_dissent_excerpt(conn, community_dimensions)
            combined = {}
            source_divergence = {}
            for name in DIMENSIONS:
                article_value = article_dimensions.get(name, missing_dimension())
                community_value = community_dimensions.get(name, missing_dimension())
                combined[name] = combine_sources(article_value, community_value, ARTICLE_WEIGHT)
                source_divergence[name] = (
                    abs(article_value["score"] - community_value["score"])
                    if article_value["score"] is not None and community_value["score"] is not None
                    else None
                )
            combined_scores = {name: value["score"] for name, value in combined.items()}
            exported.append({
                **story,
                "versions": {
                    "analysis": ANALYSIS_VERSION,
                    "selection": SELECTION_VERSION,
                    "aggregation": AGGREGATION_VERSION,
                    "influence": GLOBAL_INFLUENCE_VERSION,
                },
                "article": {
                    "dimensions": article_dimensions,
                    "result": article_run["result_json"],
                    "promptVersion": article_run["prompt_version"],
                    "promptHash": article_run["prompt_hash"],
                    "inputHash": article_run["input_hash"],
                },
                "community": ({
                    "dimensions": community_dimensions,
                    "result": community_run["result_json"],
                    "promptVersion": community_run["prompt_version"],
                    "promptHash": community_run["prompt_hash"],
                    "inputHash": community_run["input_hash"],
                } if community_run else None),
                "combined": {
                    "dimensions": combined,
                    "composite": composite_score(combined_scores),
                    "addressedDimensions": [name for name, score in combined_scores.items() if score is not None],
                },
                "sourceDivergence": source_divergence,
            })
        return exported
    finally:
        conn.close()


def aggregate(stories: list[dict[str, Any]], now: float | None = None) -> dict[str, Any]:
    generated_at = datetime.fromtimestamp(now or time.time(), timezone.utc).isoformat()
    cutoff = (now or time.time()) - (VERDICT_MONTHS * 30.44 * 24 * 3600)
    recent = [item for item in stories if item["hn_timestamp"] >= cutoff]
    totals = {dimension: 0.0 for dimension in DIMENSIONS}
    total_weights = {dimension: 0.0 for dimension in DIMENSIONS}
    confidence_totals = {dimension: 0.0 for dimension in DIMENSIONS}
    base_weights = {dimension: 0.0 for dimension in DIMENSIONS}
    counts = {dimension: 0 for dimension in DIMENSIONS}
    for item in recent:
        base_weight = influence(item["hn_score"], item["hn_timestamp"], now)
        for dimension in DIMENSIONS:
            value = item["combined"]["dimensions"][dimension]
            if value["score"] is None or value["confidence"] <= 0:
                continue
            weight = base_weight * value["confidence"]
            totals[dimension] += value["score"] * weight
            total_weights[dimension] += weight
            confidence_totals[dimension] += value["confidence"] * base_weight
            base_weights[dimension] += base_weight
            counts[dimension] += 1
    scores = {
        dimension: totals[dimension] / total_weights[dimension] if total_weights[dimension] else None
        for dimension in DIMENSIONS
    }
    composite = composite_score(scores)
    return {
        "contractVersion": "verdict-v2.0.0",
        "generatedAt": generated_at,
        "analysisVersion": ANALYSIS_VERSION,
        "prefilterVersion": PREFILTER_CONTRACT_VERSION,
        "selectionVersion": SELECTION_VERSION,
        "aggregationVersion": AGGREGATION_VERSION,
        "influenceVersion": GLOBAL_INFLUENCE_VERSION,
        "sourcePriors": {"article": ARTICLE_WEIGHT, "community": COMMUNITY_WEIGHT},
        "windowMonths": VERDICT_MONTHS,
        "articleCount": len(recent),
        "dimensions": {
            dimension: ({
                "rawScore": round(score, 4),
                "score": display_score(score),
                "verdict": verdict(score),
                "confidence": round(confidence_totals[dimension] / base_weights[dimension], 4),
                "articleCount": counts[dimension],
            } if score is not None else None)
            for dimension, score in scores.items()
        },
        "composite": ({
            "rawScore": round(composite, 4),
            "score": display_score(composite),
            "verdict": verdict(composite),
            "addressedDimensions": [name for name, score in scores.items() if score is not None],
        } if composite is not None else None),
    }


def build_history(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for story in stories:
        key = datetime.fromtimestamp(story["hn_timestamp"], timezone.utc).strftime("%Y-%m")
        grouped.setdefault(key, []).append(story)
    points = []
    for key, group in sorted(grouped.items()):
        dimensions = {}
        for name in DIMENSIONS:
            values = [
                story["combined"]["dimensions"][name] for story in group
                if story["combined"]["dimensions"][name]["score"] is not None
            ]
            total = sum(value["confidence"] for value in values)
            dimensions[name] = {
                "score": round(sum(value["score"] * value["confidence"] for value in values) / total, 4) if total else None,
                "confidence": round(total / len(values), 4) if values else 0,
                "addressedCount": len(values),
            }
        points.append({"date": f"{key}-01", "storyCount": len(group), "dimensions": dimensions})
    return points


def load_bot_feed(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Bot feed input must be a JSON list")
    allowed = {"aipostsbot", "aimediabot", "ainewsbot"}
    result = []
    for item in data:
        if item.get("contractVersion") != "bot-feed-v2.0.0" or item.get("bot") not in allowed:
            raise ValueError("Invalid bot feed record")
        result.append(item)
    return result


def next_scheduled_run(now: datetime) -> datetime:
    base = now.replace(minute=0, second=0, microsecond=0)
    next_hour = ((base.hour // 6) + 1) * 6
    if next_hour >= 24:
        return (base + timedelta(days=1)).replace(hour=0)
    return base.replace(hour=next_hour)


def pipeline_status(bot_feed: list[dict[str, Any]]) -> dict[str, Any]:
    conn = connect_rows()
    now = datetime.now(timezone.utc)
    try:
        current = conn.execute(
            "SELECT * FROM v2_orchestration_runs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        last = conn.execute(
            "SELECT * FROM v2_orchestration_runs WHERE status != 'running' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        corpus = conn.execute(
            "SELECT COUNT(*) FROM v2_prefilter_decisions WHERE contract_version = ? AND eligible = 1",
            (PREFILTER_CONTRACT_VERSION,),
        ).fetchone()[0]
        article = conn.execute(
            "SELECT COUNT(DISTINCT hn_story_id) FROM v2_analysis_runs WHERE source = 'article' AND status = 'accepted' AND analysis_version = ?",
            (ANALYSIS_VERSION,),
        ).fetchone()[0]
        community = conn.execute(
            "SELECT COUNT(DISTINCT hn_story_id) FROM v2_analysis_runs WHERE source = 'community' AND status = 'accepted' AND analysis_version = ?",
            (ANALYSIS_VERSION,),
        ).fetchone()[0]
    finally:
        conn.close()
    percent = lambda value: round(value / corpus * 100, 1) if corpus else 0.0
    last_data = dict(last) if last else None
    current_data = dict(current) if current else None
    if last_data and last_data.get("finished_at"):
        duration = (
            datetime.fromisoformat(last_data["finished_at"]) - datetime.fromisoformat(last_data["started_at"])
        ).total_seconds()
    else:
        duration = 0
    return {
        "contractVersion": "pipeline-status-v2.0.0",
        "generatedAt": now.isoformat(),
        "schedule": {
            "expression": "0 */6 * * *", "timezone": "UTC", "human": "every 6 hours",
            "nextRunAt": next_scheduled_run(now).isoformat(), "graceMinutes": 60,
        },
        "currentRun": ({
            "runId": current_data["run_id"], "startedAt": current_data["started_at"],
            "stage": current_data["stage"],
        } if current_data else None),
        "lastRun": ({
            "runId": last_data["run_id"], "status": last_data["status"],
            "startedAt": last_data["started_at"], "finishedAt": last_data["finished_at"],
            "durationSeconds": round(duration), "storiesDiscovered": last_data["stories_discovered"],
            "articlesProcessed": last_data["articles_processed"],
            "commentsAnalyzed": last_data["comments_analyzed"], "errorCode": last_data["error_code"],
        } if last_data else None),
        "coverage": {
            "corpusEligible": corpus, "articleAnalyzed": article, "communityAnalyzed": community,
            "botPreviewReady": len(bot_feed), "articlePercent": percent(article),
            "communityPercent": percent(community),
            "botPreviewPercent": round(sum(item.get("previewStatus") == "complete" for item in bot_feed) / len(bot_feed) * 100, 1) if bot_feed else 0.0,
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_generation(directory: Path, bot_input: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    stories = export_stories()
    bot_feed = load_bot_feed(bot_input)
    generated = datetime.now(timezone.utc).isoformat()
    payloads = {
        "verdict.json": aggregate(stories),
        "stories.json": stories,
        "history.json": build_history(stories),
        "bot-feed.json": bot_feed,
        "pipeline-status.json": pipeline_status(bot_feed),
    }
    for filename, payload in payloads.items():
        write_json(directory / filename, payload)
    manifest = {
        "contractVersion": MANIFEST_VERSION,
        "generatedAt": generated,
        "influenceVersion": GLOBAL_INFLUENCE_VERSION,
        "files": {
            filename: {
                "contractVersion": FILE_CONTRACTS[filename],
                "recordCount": len(payload) if isinstance(payload, list) else 1,
                "sha256": sha256(directory / filename),
            }
            for filename, payload in payloads.items()
        },
    }
    write_json(directory / "manifest.json", manifest)
    return {"stories": len(stories), "botFeed": len(bot_feed), "manifest": manifest}


def publish_atomic(output: Path, bot_input: Path) -> dict[str, Any]:
    init_v2_schema()
    output.parent.mkdir(parents=True, exist_ok=True)
    generation = output.parent / f".{output.name}-generation-{uuid.uuid4().hex}"
    backup = output.parent / f".{output.name}-previous"
    result = write_generation(generation, bot_input)
    if backup.exists():
        shutil.rmtree(backup)
    try:
        if output.exists():
            output.rename(backup)
        generation.rename(output)
    except Exception:
        if not output.exists() and backup.exists():
            backup.rename(output)
        shutil.rmtree(generation, ignore_errors=True)
        raise
    result["output"] = str(output)
    result["rollback"] = str(backup) if backup.exists() else None
    return result


def update_status_export(output: Path) -> None:
    """Refresh allowlisted public telemetry after a failed run without clearing good data."""
    if not output.exists():
        return
    status_path = output / "pipeline-status.json"
    temporary = output / ".pipeline-status.json.tmp"
    write_json(temporary, pipeline_status(load_bot_feed(DEFAULT_BOT_INPUT)))
    temporary.replace(status_path)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"]["pipeline-status.json"] = {
            "contractVersion": FILE_CONTRACTS["pipeline-status.json"],
            "recordCount": 1,
            "sha256": sha256(status_path),
        }
        manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
        manifest_temp = output / ".manifest.json.tmp"
        write_json(manifest_temp, manifest)
        manifest_temp.replace(manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Atomically publish static V2 sentiment data")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bot-input", type=Path, default=DEFAULT_BOT_INPUT)
    args = parser.parse_args()
    print(json.dumps(publish_atomic(args.output, args.bot_input), indent=2))


if __name__ == "__main__":
    main()
