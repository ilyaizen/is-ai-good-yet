#!/usr/bin/env python3
"""
Phase 5: Export pipeline for static frontend deployment.

Exports filtered article data and verdict calculations to JSON files
for static site generation (Vercel deployment).

Filters mirror the frontend's getTopArticles() and getVerdictScore() logic:
- content_category = 'AI_DISCOURSE'
- hn_score >= 20
- topic != 'business' (v4) OR subtopic != 'business' (v3)
- sentiment_score IS NOT NULL
"""

import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .store.db import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default output path (is-ai-good-yet/src/lib/data/)
DEFAULT_OUTPUT_PATH = Path(__file__).parent.parent.parent / "is-ai-good-yet" / "src" / "lib" / "data"

# Verdict window (matches frontend constants)
VERDICT_WINDOW_MONTHS = 12
TIMELINE_DISPLAY_MONTHS = 48

# Neutral multiplier for verdict calculation (matches frontend $lib/constants.ts)
# Negative value means neutral articles contribute negatively to the verdict
NEUTRAL_MULTIPLIER = -0.5

# Ground truth text files directory (articles-text/*.txt)
# Articles deleted from here are excluded from export
GROUND_TRUTH_DIR = Path(__file__).parent.parent / "data" / "articles-text"


def get_decay_factor(timestamp_seconds: int) -> float:
    """
    Calculate decay factor for articles based on age.
    Half-life is 24 months: articles from 2 years ago have 50% influence.
    Formula: decay_factor = 0.5^(months_ago / 24)
    """
    now = time.time()
    age_seconds = now - timestamp_seconds
    age_months = age_seconds / (30.44 * 24 * 3600)  # 30.44 = avg days per month
    return math.pow(0.5, age_months / 24)


def calculate_influence_score(hn_score: int, timestamp_seconds: int) -> float:
    """
    Calculate influence score using power law + decay.
    Formula: influence = hn_score^0.85 × decay_factor
    """
    power_law = math.pow(hn_score, 0.85)
    decay_factor = get_decay_factor(timestamp_seconds)
    return power_law * decay_factor


def get_sentiment_label(score: float) -> str:
    """Map sentiment score to label."""
    if score > 0.2:
        return "positive"
    elif score < -0.2:
        return "negative"
    return "neutral"


def get_verdict(score: float) -> str:
    """Map score (0-100) to verdict."""
    if score >= 55:
        return "YES"
    elif score < 45:
        return "NO"
    return "NOT_YET"


def parse_classification_json(json_str: str | None) -> dict[str, Any]:
    """Parse and normalize classification JSON from v3 or v4 schema."""
    if not json_str:
        return {}
    try:
        data = json.loads(json_str)
        # Normalize v3 schema (subtopic) to v4 (topic)
        if "topic" not in data and "subtopic" in data:
            data["topic"] = data["subtopic"]
        return data
    except json.JSONDecodeError:
        return {}


def export_articles(cursor) -> list[dict]:
    """
    Export all verdict-included articles with analysis data.
    Matches the frontend's getTopArticles() filtering.

    Ground truth sync: Articles are only included if their ground truth
    text file exists in GROUND_TRUTH_DIR. This allows manual curation by
    deleting text files to remove articles from the verdict.
    """
    query = """
        SELECT
            id,
            hn_id,
            hn_title,
            hn_score,
            hn_comments,
            hn_timestamp,
            hn_author,
            sentiment_score,
            classification_json,
            content_category,
            url
        FROM urls
        WHERE sentiment_score IS NOT NULL
          AND content_category = 'AI_DISCOURSE'
          AND hn_score IS NOT NULL
          AND hn_score >= 20
          AND hn_timestamp IS NOT NULL
          AND (
            -- New schema (v4.0+): exclude if topic = 'business'
            (json_extract(classification_json, '$.topic') IS NOT NULL AND json_extract(classification_json, '$.topic') != 'business')
            OR
            -- Old schema (v3): exclude if subtopic = 'business'
            (json_extract(classification_json, '$.topic') IS NULL AND json_extract(classification_json, '$.subtopic') IS NOT NULL AND json_extract(classification_json, '$.subtopic') != 'business')
            OR
            -- No classification JSON yet
            classification_json IS NULL
          )
        ORDER BY hn_timestamp DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    # Build set of hn_ids that have ground truth text files
    ground_truth_ids = set()
    if GROUND_TRUTH_DIR.exists():
        for txt_file in GROUND_TRUTH_DIR.glob("*.txt"):
            try:
                hn_id = int(txt_file.stem)
                ground_truth_ids.add(hn_id)
            except ValueError:
                pass  # Skip non-numeric filenames
        logger.debug(f"  Found {len(ground_truth_ids)} ground truth text files")
    else:
        logger.warning(f"Ground truth directory not found: {GROUND_TRUTH_DIR}")

    articles = []
    skipped_count = 0

    for row in rows:
        url_id, hn_id, hn_title, hn_score, hn_comments, hn_timestamp, hn_author, sentiment_score, classification_json, content_category, url = row

        # Skip articles without ground truth text files (deleted from curation)
        if ground_truth_ids and hn_id not in ground_truth_ids:
            skipped_count += 1
            continue

        classification = parse_classification_json(classification_json)
        influence_score = round(calculate_influence_score(hn_score, hn_timestamp), 2)

        article = {
            "hn_id": hn_id,
            "hn_title": hn_title or "Untitled",
            "hn_score": hn_score,
            "hn_comments": hn_comments,
            "hn_timestamp": hn_timestamp,
            "hn_author": hn_author or "",
            "sentiment_score": sentiment_score,
            "sentiment_label": get_sentiment_label(sentiment_score),
            "influenceScore": influence_score,
            "url": url,
            "summary": classification.get("summary", ""),
            "topic": classification.get("topic", ""),
            "utility": classification.get("utility", "mixed"),
            "trajectory": classification.get("trajectory", "uncertain"),
            "quotes": classification.get("quotes", []),
        }
        articles.append(article)

    if skipped_count > 0:
        logger.info(f"  Skipped {skipped_count} articles without ground truth text files")

    return articles


def calculate_verdict_score(articles: list[dict]) -> dict:
    """
    Calculate verdict score matching frontend logic.
    Uses contribution ratio: |positive| / (|positive| + |negative|) × 100
    """
    now = time.time()
    cutoff = now - (VERDICT_WINDOW_MONTHS * 30.44 * 24 * 3600)

    # Filter to verdict window
    window_articles = [a for a in articles if a["hn_timestamp"] >= cutoff]

    positive_contribution = 0.0
    negative_contribution = 0.0
    neutral_contribution = 0.0
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_influence = 0.0

    for article in window_articles:
        influence = article["influenceScore"]
        sentiment = article["sentiment_score"]
        total_influence += influence

        if sentiment > 0.2:
            positive_contribution += sentiment * influence
            positive_count += 1
        elif sentiment < -0.2:
            negative_contribution += sentiment * influence
            negative_count += 1
        else:
            neutral_contribution += influence * NEUTRAL_MULTIPLIER
            neutral_count += 1

    # Calculate score using contribution ratio
    abs_positive = abs(positive_contribution)
    abs_negative = abs(negative_contribution)
    total_abs = abs_positive + abs_negative

    if total_abs > 0:
        score = (abs_positive / total_abs) * 100
    else:
        score = 50.0

    # Raw sentiment (weighted average)
    weighted_sum = positive_contribution + negative_contribution + neutral_contribution
    raw_sentiment = weighted_sum / total_influence if total_influence > 0 else 0

    verdict = get_verdict(score)

    return {
        "verdict": verdict,
        "score": round(score, 2),
        "rawSentiment": round(raw_sentiment, 4),
        "totalArticles": len(window_articles),
        "positiveCount": positive_count,
        "negativeCount": negative_count,
        "neutralCount": neutral_count,
        "positiveContribution": round(positive_contribution, 2),
        "negativeContribution": round(negative_contribution, 2),
        "neutralContribution": round(neutral_contribution, 2),
        "windowMonths": VERDICT_WINDOW_MONTHS,
        "exportedAt": datetime.now().isoformat(),
    }


def calculate_permanent_record(articles: list[dict]) -> dict:
    """
    Calculate all-time verdict with no time decay.
    Uses only upvote weighting (power law, no decay).
    """
    positive_contribution = 0.0
    negative_contribution = 0.0
    neutral_contribution = 0.0
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for article in articles:
        # Use power law only, no decay (all-time score)
        power_weight = math.pow(article["hn_score"], 0.85)
        sentiment = article["sentiment_score"]

        if sentiment > 0.2:
            positive_contribution += sentiment * power_weight
            positive_count += 1
        elif sentiment < -0.2:
            negative_contribution += sentiment * power_weight
            negative_count += 1
        else:
            neutral_contribution += power_weight * NEUTRAL_MULTIPLIER
            neutral_count += 1

    abs_positive = abs(positive_contribution)
    abs_negative = abs(negative_contribution)
    total_abs = abs_positive + abs_negative

    score = (abs_positive / total_abs) * 100 if total_abs > 0 else 50.0

    return {
        "score": round(score, 2),
        "verdict": get_verdict(score),
        "totalArticles": len(articles),
        "positiveCount": positive_count,
        "negativeCount": negative_count,
        "neutralCount": neutral_count,
    }


def calculate_historical_snapshots(articles: list[dict]) -> list[dict]:
    """
    Calculate what the verdict would have been at each month.
    Returns monthly snapshots for the history chart.
    """
    if not articles:
        return []

    # Get date range
    oldest = min(a["hn_timestamp"] for a in articles)
    newest = max(a["hn_timestamp"] for a in articles)

    # Generate monthly snapshots from oldest to now
    snapshots = []
    current = datetime.fromtimestamp(oldest).replace(day=1)
    now = datetime.now()

    while current <= now:
        month_end = current.replace(day=28)  # Safe end of month approximation
        month_end_ts = month_end.timestamp()

        # Get articles up to this month (point-in-time calculation)
        eligible = [a for a in articles if a["hn_timestamp"] <= month_end_ts]

        if eligible:
            # Calculate verdict at this point in time
            positive_contrib = 0.0
            negative_contrib = 0.0

            for article in eligible:
                # Use power law only (simulating no decay at that point in time)
                power_weight = math.pow(article["hn_score"], 0.85)
                sentiment = article["sentiment_score"]

                if sentiment > 0.2:
                    positive_contrib += sentiment * power_weight
                elif sentiment < -0.2:
                    negative_contrib += sentiment * power_weight

            abs_pos = abs(positive_contrib)
            abs_neg = abs(negative_contrib)
            total = abs_pos + abs_neg
            score = (abs_pos / total) * 100 if total > 0 else 50.0

            snapshots.append({
                "month": current.strftime("%Y-%m"),
                "score": round(score, 2),
                "verdict": get_verdict(score),
                "articleCount": len(eligible),
            })

        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return snapshots


def calculate_weekly_snapshots(articles: list[dict]) -> list[dict]:
    """
    Calculate rolling weekly snapshots for the history chart.
    Uses a 6-month rolling window like the frontend's getWeeklyRollingSnapshots().
    """
    if not articles:
        return []

    # Constants - use same 12-month window as the current verdict
    ROLLING_WINDOW_MONTHS = 12
    TIMELINE_DISPLAY_MONTHS = 48
    rolling_window_seconds = ROLLING_WINDOW_MONTHS * 30.44 * 24 * 3600

    # Get display cutoff
    now = time.time()
    display_cutoff_ts = now - (TIMELINE_DISPLAY_MONTHS * 30.44 * 24 * 3600)

    # Group articles by ISO week
    from collections import defaultdict
    week_articles = defaultdict(list)

    for article in articles:
        ts = article["hn_timestamp"]
        dt = datetime.fromtimestamp(ts)
        iso_year, iso_week, _ = dt.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        # Get Monday of this week
        monday = dt - timedelta(days=dt.weekday())
        week_start = monday.strftime("%Y-%m-%d")
        week_articles[week_key].append({
            **article,
            "week": week_key,
            "week_start": week_start,
        })

    # Get unique weeks in chronological order
    sorted_weeks = sorted(week_articles.keys())

    snapshots = []

    for week_key in sorted_weeks:
        week_data = week_articles[week_key]
        if not week_data:
            continue

        # Get the week's end timestamp (latest article in this week)
        week_end_ts = max(a["hn_timestamp"] for a in week_data)
        week_start_ts = week_end_ts - rolling_window_seconds
        week_start_date = week_data[0]["week_start"]

        # Skip weeks before display cutoff
        if week_end_ts < display_cutoff_ts:
            continue

        # Get all articles within the rolling window ending at this week
        window_articles = [a for a in articles
                          if week_start_ts <= a["hn_timestamp"] <= week_end_ts]

        if not window_articles:
            continue

        # Calculate contributions
        positive_contribution = 0.0
        negative_contribution = 0.0
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for article in window_articles:
            power_weight = math.pow(article["hn_score"], 0.85)
            sentiment = article["sentiment_score"]

            if sentiment > 0.2:
                positive_contribution += sentiment * power_weight
                positive_count += 1
            elif sentiment < -0.2:
                negative_contribution += sentiment * power_weight
                negative_count += 1
            else:
                neutral_count += 1

        # Calculate score using contribution ratio
        abs_positive = abs(positive_contribution)
        abs_negative = abs(negative_contribution)
        total_abs = abs_positive + abs_negative

        score = (abs_positive / total_abs) * 100 if total_abs > 0 else 50.0

        # Calculate neutral contribution
        neutral_contribution = 0.0
        for article in window_articles:
            if -0.2 <= article["sentiment_score"] <= 0.2:
                power_weight = math.pow(article["hn_score"], 0.85)
                neutral_contribution += power_weight * NEUTRAL_MULTIPLIER

        snapshots.append({
            "week": week_key,
            "weekStart": week_start_date,
            "verdictScore": round(score, 2),
            "verdict": get_verdict(score),
            "articleCount": len(window_articles),
            "rawSentiment": 0,  # Not calculated for simplicity
            "positiveCount": positive_count,
            "neutralCount": neutral_count,
            "negativeCount": negative_count,
            "positiveContribution": round(positive_contribution, 2),
            "negativeContribution": round(negative_contribution, 2),
            "neutralContribution": round(neutral_contribution, 2),
        })

    return snapshots


def export_llm_metrics(cursor, exported_hn_ids: set[int]) -> dict:
    """
    Export LLM analysis metrics for all exported articles.

    Returns a dict keyed by hn_id containing:
    - prefilter: The content prefilter LLM response (category, confidence, reasoning) + speed metrics
    - sentiment: The sentiment analysis LLM response (utility, trajectory, topic, summary, quotes) + speed metrics

    Speed metrics include tokens_per_second for visualizing LLM inference speed.
    """
    query = """
        SELECT
            hn_id,
            classification_json,
            content_filter_json,
            groq_metrics_json
        FROM urls
        WHERE hn_id IS NOT NULL
          AND sentiment_score IS NOT NULL
          AND content_category = 'AI_DISCOURSE'
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    metrics_by_hn_id = {}

    for row in rows:
        hn_id, classification_json, content_filter_json, groq_metrics_json = row

        # Only include metrics for articles that were exported
        if hn_id not in exported_hn_ids:
            continue

        entry = {}

        # Parse and include prefilter response (remove nested metrics if present)
        if content_filter_json:
            try:
                prefilter_response = json.loads(content_filter_json)
                # Extract just the LLM response fields, not nested metrics
                clean_response = {
                    k: v for k, v in prefilter_response.items()
                    if k != "metrics"
                }
                entry["prefilter"] = {
                    "response": clean_response,
                }
            except json.JSONDecodeError:
                pass

        # Parse and include sentiment analysis response
        if classification_json:
            try:
                sentiment_response = json.loads(classification_json)
                entry["sentiment"] = {
                    "response": sentiment_response,
                }
            except json.JSONDecodeError:
                pass

        # Parse and merge speed metrics into respective sections
        if groq_metrics_json:
            try:
                metrics = json.loads(groq_metrics_json)

                # Add prefilter speed metrics
                if "prefilter" in metrics and "prefilter" in entry:
                    entry["prefilter"]["metrics"] = metrics["prefilter"]

                # Add sentiment/classifier speed metrics
                if "classifier" in metrics and "sentiment" in entry:
                    entry["sentiment"]["metrics"] = metrics["classifier"]

            except json.JSONDecodeError:
                pass

        # Only add if we have at least some data
        if entry:
            metrics_by_hn_id[hn_id] = entry

    return metrics_by_hn_id


def export_pipeline_stats(cursor) -> dict:
    """
    Export pipeline-wide stats matching the frontend's getPipelineStats().
    Counts total URLs, resolved, scraped, relevant, analyzed, and failed.
    """
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN scraped_status = 'success' THEN 1 ELSE 0 END) as scraped,
            SUM(CASE
                WHEN hn_score >= 20
                AND hn_comments >= 5
                AND scraped_status = 'success'
                AND content_category = 'AI_DISCOURSE'
                THEN 1 ELSE 0
            END) as relevant,
            SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as analyzed
        FROM urls
    """
    cursor.execute(query)
    row = cursor.fetchone()
    return {
        "totalUrls": row[0] or 0,
        "scraped": row[1] or 0,
        "relevant": row[2] or 0,
        "analyzed": row[3] or 0,
    }


def export_data(output_path: Path, verbose: bool = False) -> dict:
    """
    Main export function. Generates all JSON files.
    Returns stats about the export.
    """
    output_path.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Export articles
        if verbose:
            logger.info("Exporting articles...")
        articles = export_articles(cursor)

        articles_path = output_path / "articles.json"
        with open(articles_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        if verbose:
            logger.info(f"  Exported {len(articles)} articles to {articles_path}")

        # Calculate and export verdict
        if verbose:
            logger.info("Calculating verdict...")
        verdict = calculate_verdict_score(articles)
        permanent = calculate_permanent_record(articles)

        # Export pipeline stats (mirrors getPipelineStats() in db.ts)
        if verbose:
            logger.info("Calculating pipeline stats...")
        pipeline_stats = export_pipeline_stats(cursor)

        verdict_data = {
            "current": verdict,
            "permanent": permanent,
            "pipeline": pipeline_stats,
        }

        verdict_path = output_path / "verdict.json"
        with open(verdict_path, "w", encoding="utf-8") as f:
            json.dump(verdict_data, f, indent=2)
        if verbose:
            logger.info(f"  Verdict: {verdict['verdict']} (score: {verdict['score']:.1f})")

        # Calculate and export historical snapshots
        if verbose:
            logger.info("Generating historical snapshots...")
        historical = calculate_historical_snapshots(articles)

        historical_path = output_path / "historical.json"
        with open(historical_path, "w", encoding="utf-8") as f:
            json.dump(historical, f, indent=2)
        if verbose:
            logger.info(f"  Exported {len(historical)} monthly snapshots")

        # Calculate and export weekly snapshots (for history chart)
        if verbose:
            logger.info("Generating weekly snapshots...")
        weekly = calculate_weekly_snapshots(articles)

        weekly_path = output_path / "weekly.json"
        with open(weekly_path, "w", encoding="utf-8") as f:
            json.dump(weekly, f, indent=2)
        if verbose:
            logger.info(f"  Exported {len(weekly)} weekly snapshots")

        # Export LLM metrics (prefilter + sentiment responses with speed metrics)
        if verbose:
            logger.info("Exporting LLM metrics...")
        exported_hn_ids = {article["hn_id"] for article in articles}
        llm_metrics = export_llm_metrics(cursor, exported_hn_ids)

        llm_metrics_path = output_path / "llm-metrics.json"
        with open(llm_metrics_path, "w", encoding="utf-8") as f:
            json.dump(llm_metrics, f, indent=2, ensure_ascii=False)
        if verbose:
            logger.info(f"  Exported LLM metrics for {len(llm_metrics)} articles")

        # Export Themes (Phase 5)
        if verbose:
            logger.info("Exporting themes...")
        cursor.execute("SELECT sentiment_group, theme_title, theme_description, sentiment_verdict, article_count FROM themes ORDER BY article_count DESC")
        theme_rows = cursor.fetchall()

        themes_data = {
            "positive": [],
            "neutral": [],
            "negative": []
        }

        for row in theme_rows:
            sentiment_group, title, description, theme_verdict, count = row
            if sentiment_group in themes_data:
                themes_data[sentiment_group].append({
                    "title": title,
                    "description": description,
                    "verdict": theme_verdict,
                    "count": count
                })

        themes_path = output_path / "themes.json"
        with open(themes_path, "w", encoding="utf-8") as f:
            json.dump(themes_data, f, indent=2, ensure_ascii=False)
        if verbose:
            logger.info(f"  Exported {len(theme_rows)} themes")

        # Return stats
        return {
            "articles": len(articles),
            "verdict": verdict["verdict"],
            "score": verdict["score"],
            "snapshots": len(historical),
            "llm_metrics": len(llm_metrics),
            "themes": len(theme_rows),
            "output_path": str(output_path),
        }

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export pipeline data for static frontend deployment"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output directory (default: {DEFAULT_OUTPUT_PATH})"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show export statistics and exit"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        stats = export_data(args.output, verbose=args.verbose)

        print("\n" + "=" * 50)
        print("EXPORT COMPLETE")
        print("=" * 50)
        print(f"Articles exported:  {stats['articles']}")
        print(f"LLM metrics:        {stats['llm_metrics']}")
        print(f"Current verdict:    {stats['verdict']} ({stats['score']:.1f}%)")
        print(f"Monthly snapshots:  {stats['snapshots']}")
        print(f"Output directory:   {stats['output_path']}")
        print("=" * 50)

        return 0

    except Exception as e:
        logger.error(f"Export failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
