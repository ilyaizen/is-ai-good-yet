"""Fetch and deterministically rank Hacker News comment candidates for v2."""

from __future__ import annotations

import argparse
import asyncio
import html
import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .store.db import get_db_connection
from .store.v2 import init_v2_schema, replace_selection, replace_story_comments
from .v2_models import SelectedComment, raw_visibility_weight


HN_API = "https://hacker-news.firebaseio.com/v0"
SELECTION_VERSION = "ranked-tree-v2.2.0"
AUTHOR_CAP = 2
TAG_RE = re.compile(r"<[^>]+>")


def clean_comment_text(value: str) -> str:
    with_breaks = re.sub(r"<p\s*/?>", "\n\n", value, flags=re.IGNORECASE)
    return " ".join(html.unescape(TAG_RE.sub("", with_breaks)).split())


def accepted_target(eligible_count: int) -> int:
    if eligible_count <= 0:
        return 0
    adaptive = max(12, min(32, math.ceil(4 * math.sqrt(eligible_count))))
    return min(eligible_count, adaptive)


def branch_cap(target: int) -> int:
    return max(3, math.ceil(0.15 * target))


async def fetch_json(session: aiohttp.ClientSession, path: str) -> dict[str, Any] | None:
    async with session.get(f"{HN_API}/{path}.json") as response:
        response.raise_for_status()
        return await response.json()


async def fetch_story_comments(story_id: int) -> list[dict[str, Any]]:
    """Fetch the tree and retain each item's actual local sibling rank and ancestry."""
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        story = await fetch_json(session, f"item/{story_id}")
        if not story or story.get("type") != "story":
            raise ValueError(f"HN item {story_id} is not a story")

        async def walk(
            comment_id: int, depth: int, root_id: int, root_rank: int,
            sibling_rank: int, ancestry_ids: tuple[int, ...],
        ) -> list[dict[str, Any]]:
            item = await fetch_json(session, f"item/{comment_id}")
            if not item:
                return []
            text = clean_comment_text(item.get("text", ""))
            current_ancestry = (*ancestry_ids, comment_id)
            subtree: list[dict[str, Any]] = []
            if not item.get("deleted") and not item.get("dead") and item.get("by") and text:
                subtree.append(
                    {
                        "id": comment_id, "parent_id": item.get("parent", story_id),
                        "root_id": root_id, "author": item["by"], "text": text,
                        "depth": depth, "root_rank": root_rank,
                        "sibling_rank": sibling_rank, "ancestry_ids": current_ancestry,
                        "created_at": item.get("time"),
                    }
                )
            children = await asyncio.gather(
                *(
                    walk(child_id, depth + 1, root_id, root_rank, child_rank, current_ancestry)
                    for child_rank, child_id in enumerate(item.get("kids", []), start=1)
                )
            )
            for child_subtree in children:
                subtree.extend(child_subtree)
            return subtree

        trees = await asyncio.gather(
            *(
                walk(root_id, 0, root_id, root_rank, root_rank, ())
                for root_rank, root_id in enumerate(story.get("kids", []), start=1)
            )
        )
        return [comment for tree in trees for comment in tree]


def _round_robin_replies(replies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_branch: dict[int, list[dict[str, Any]]] = {}
    for item in replies:
        by_branch.setdefault(item["root_id"], []).append(item)
    for values in by_branch.values():
        values.sort(key=lambda item: (item["depth"], item["sibling_rank"], item["id"]))
    branch_order = sorted(by_branch, key=lambda root_id: by_branch[root_id][0]["root_rank"])
    ordered = []
    indexes = {root_id: 0 for root_id in branch_order}
    while True:
        added = False
        for root_id in branch_order:
            index = indexes[root_id]
            if index < len(by_branch[root_id]):
                ordered.append(by_branch[root_id][index])
                indexes[root_id] += 1
                added = True
        if not added:
            return ordered


def build_candidate_stream(story_id: int, comments: list[dict[str, Any]]) -> list[SelectedComment]:
    """Return deterministic waves; model outcomes decide which candidates consume the target."""
    eligible = [item for item in comments if item.get("text", "").strip()]
    roots = sorted(
        (item for item in eligible if item["depth"] == 0),
        key=lambda item: (item["root_rank"], item["id"]),
    )
    replies = _round_robin_replies([item for item in eligible if item["depth"] > 0])
    target = accepted_target(len(eligible))
    top_quota = math.ceil(0.6 * target)
    reply_quota = target - top_quota
    waves: list[tuple[dict[str, Any], str, str]] = []
    used: set[int] = set()
    first_authors: set[str] = set()

    for item in roots:
        if len([x for x in waves if x[1] == "top_level_diversity"]) >= top_quota:
            break
        if item["author"] in first_authors:
            continue
        waves.append((item, "top_level_diversity", "one_top_level_per_author"))
        used.add(item["id"])
        first_authors.add(item["author"])
    for item in replies[:reply_quota]:
        waves.append((item, "reply_branch_diversity", "one_reply_per_branch_round_robin"))
        used.add(item["id"])
    for item in roots:
        if item["id"] not in used:
            waves.append((item, "remaining_top_level", "ranked_top_level_refill"))
            used.add(item["id"])
    for item in replies:
        if item["id"] not in used:
            waves.append((item, "remaining_replies", "ranked_branch_refill"))
            used.add(item["id"])

    return [
        SelectedComment(
            hn_comment_id=item["id"], hn_story_id=story_id,
            parent_id=item["parent_id"], root_id=item["root_id"], author=item["author"],
            text=item["text"], depth=item["depth"], root_rank=item["root_rank"],
            sibling_rank=item["sibling_rank"], ancestry_ids=tuple(item["ancestry_ids"]),
            candidate_rank=rank, selection_pass=selection_pass,
            selection_reason=reason,
            raw_visibility_weight=raw_visibility_weight(
                item["root_rank"], item["sibling_rank"], item["depth"]
            ),
        )
        for rank, (item, selection_pass, reason) in enumerate(waves, start=1)
    ]


def candidate_is_eligible(
    candidate: SelectedComment, accepted: list[SelectedComment], target: int,
) -> bool:
    """Apply caps to accepted comments only, so rejected candidates cannot consume capacity."""
    author_count = sum(item.author == candidate.author for item in accepted)
    branch_count = sum(item.root_id == candidate.root_id for item in accepted)
    return author_count < AUTHOR_CAP and branch_count < branch_cap(target)


def get_story_ids(limit: int | None, min_score: int, min_comments: int) -> list[int]:
    conn = get_db_connection()
    try:
        query = """
            SELECT hn_id FROM urls
            WHERE hn_id IS NOT NULL AND scraped_status = 'success'
              AND hn_score >= ? AND hn_comments >= ?
            ORDER BY hn_score DESC
        """
        params: list[int] = [min_score, min_comments]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return [row[0] for row in conn.execute(query, params)]
    finally:
        conn.close()


async def collect_story(story_id: int) -> int:
    comments = await fetch_story_comments(story_id)
    fetched_at = datetime.now(timezone.utc).isoformat()
    replace_story_comments(story_id, comments, fetched_at)
    candidates = build_candidate_stream(story_id, comments)
    replace_selection(story_id, SELECTION_VERSION, candidates, fetched_at)
    return len(candidates)


async def collect_all(story_ids: list[int]) -> None:
    init_v2_schema()
    for story_id in story_ids:
        try:
            count = await collect_story(story_id)
            logging.info("Stored %s comment candidates for HN story %s", count, story_id)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            logging.error("Failed to collect HN story %s: %s", story_id, error)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect ranked HN comment candidates for v2")
    parser.add_argument("--hn-id", type=int, help="Collect a single HN story")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-score", type=int, default=20)
    parser.add_argument("--min-comments", type=int, default=5)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    story_ids = [args.hn_id] if args.hn_id else get_story_ids(args.limit, args.min_score, args.min_comments)
    asyncio.run(collect_all(story_ids))


if __name__ == "__main__":
    main()
