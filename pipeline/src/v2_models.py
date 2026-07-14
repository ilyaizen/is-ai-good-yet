"""Versioned contracts and deterministic scoring helpers for v2 sentiment."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


ANALYSIS_VERSION = "v2.2.0"
ARTICLE_CONTRACT_VERSION = "article-v2.2.0"
COMMENT_CONTRACT_VERSION = "comment-v2.2.0"
PREFILTER_CONTRACT_VERSION = "prefilter-v2.0.0"
AGGREGATION_VERSION = "community-aggregation-v2.2.0"
GLOBAL_INFLUENCE_VERSION = "hn-score-0.85_decay-24m_v1"
PARSER_VERSION = "v2.2.1"

ARTICLE_SUMMARY_MAX_WORDS = 50
COMMENT_SUMMARY_MAX_WORDS = 30

DIMENSIONS = ("capability", "trajectory", "impact")
VALID_APPLICABILITY = {"explicit", "implicit", "not_addressed"}
VALID_SCOPES = {
    "coding", "research", "education", "labor", "economy", "creativity",
    "safety", "governance", "environment", "general",
}
VALID_REJECTION_CODES = {
    "not_ai", "no_ai_judgment", "unusable_content", "insufficient_context",
}
VALID_ATTRIBUTIONS = {"author", "reported_finding", "quoted_source", "headline"}
VALID_STANCE_BASES = {
    "direct", "endorsed_article_thesis", "endorsed_parent_claim",
    "rejected_contextual_claim", "inferred_from_sarcasm", "none",
}
VALID_ARTICLE_RELATIONS = {
    "supports", "challenges", "qualifies", "mixed", "unclear", "not_applicable",
}
VALID_ARTICLE_TARGETS = {
    *DIMENSIONS, "factual_detail", "framing", "method", "article_quality",
}
VALID_PARENT_RELATIONS = {
    "agrees", "disagrees", "clarifies", "questions", "corrects", "other",
    "not_applicable",
}


def validate_prefilter_result(result: dict[str, Any]) -> tuple[bool, str]:
    """Validate the isolated broad-scope prefilter contract."""
    required = {"contract_version", "eligible", "scopes", "reason_code", "reason"}
    errors = []
    if set(result) != required:
        errors.append(f"Prefilter result must contain exactly {sorted(required)}")
    if result.get("contract_version") != PREFILTER_CONTRACT_VERSION:
        errors.append(f"Invalid contract_version: {result.get('contract_version')}")
    if not isinstance(result.get("eligible"), bool):
        errors.append("eligible must be boolean")
    scopes = result.get("scopes")
    if not isinstance(scopes, list) or len(scopes) != len(set(scopes)) or not all(
        scope in VALID_SCOPES for scope in scopes
    ):
        errors.append("scopes must contain unique approved V2 scopes")
    elif result.get("eligible") and not scopes:
        errors.append("eligible content requires at least one scope")
    elif not result.get("eligible") and scopes:
        errors.append("ineligible content requires an empty scopes list")
    if not isinstance(result.get("reason_code"), str) or not result["reason_code"].strip():
        errors.append("reason_code must be non-empty")
    if not isinstance(result.get("reason"), str) or not result["reason"].strip():
        errors.append("reason must be non-empty")
    return not errors, "; ".join(errors)


@dataclass(frozen=True)
class SelectedComment:
    hn_comment_id: int
    hn_story_id: int
    parent_id: int
    root_id: int
    author: str
    text: str
    depth: int
    root_rank: int
    sibling_rank: int
    ancestry_ids: tuple[int, ...]
    candidate_rank: int
    selection_pass: str
    selection_reason: str
    raw_visibility_weight: float


def _validate_rejection(result: dict[str, Any], contract_version: str) -> list[str]:
    allowed = {"contract_version", "comment_id", "reject", "reason_code", "reason"}
    if "comment_id" not in result:
        allowed.remove("comment_id")
    errors = []
    if set(result) != allowed:
        errors.append(f"Rejection must contain exactly {sorted(allowed)}")
    if result.get("contract_version") != contract_version:
        errors.append(f"Invalid contract_version: {result.get('contract_version')}")
    if result.get("reject") is not True:
        errors.append("Rejection requires reject=true")
    if result.get("reason_code") not in VALID_REJECTION_CODES:
        errors.append(f"Invalid reason_code: {result.get('reason_code')}")
    if not isinstance(result.get("reason"), str) or not result["reason"].strip():
        errors.append("Rejection requires a non-empty reason")
    return errors


def _validate_dimension(
    value: Any, evidence_ids_required: bool, stance_basis_required: bool = False,
) -> list[str]:
    if not isinstance(value, dict):
        return ["dimension must be an object"]
    required = {"applicability", "score", "confidence", "rationale"}
    if evidence_ids_required:
        required.add("evidence_ids")
    if stance_basis_required:
        required.add("stance_basis")
    if set(value) != required:
        return [f"dimension must contain exactly {sorted(required)}"]
    errors = []
    applicability = value.get("applicability")
    score = value.get("score")
    confidence = value.get("confidence")
    if applicability not in VALID_APPLICABILITY:
        errors.append(f"invalid applicability: {applicability}")
    if applicability == "not_addressed":
        if score is not None or confidence != 0:
            errors.append("not_addressed requires score=null and confidence=0")
        if stance_basis_required and value.get("stance_basis") != "none":
            errors.append("not_addressed requires stance_basis=none")
    else:
        if isinstance(score, bool) or score not in {-2, -1, 0, 1, 2}:
            errors.append(f"invalid score: {score}")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            errors.append("confidence must be numeric")
        elif not 0 < confidence <= 1:
            errors.append("addressed confidence must be in (0, 1]")
        if stance_basis_required and value.get("stance_basis") not in VALID_STANCE_BASES - {"none"}:
            errors.append(f"invalid stance_basis: {value.get('stance_basis')}")
    if not isinstance(value.get("rationale"), str) or not value["rationale"].strip():
        errors.append("rationale must be a non-empty string")
    if evidence_ids_required:
        evidence_ids = value.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not all(isinstance(x, str) and x for x in evidence_ids):
            errors.append("evidence_ids must be a list of non-empty strings")
        elif applicability == "not_addressed" and evidence_ids:
            errors.append("not_addressed requires empty evidence_ids")
        elif applicability != "not_addressed" and not evidence_ids:
            errors.append("addressed dimensions require evidence")
    return errors


def validate_article_analysis(result: dict[str, Any]) -> tuple[bool, str]:
    """Validate the strict article thesis contract."""
    if result.get("reject") is True:
        errors = _validate_rejection(result, ARTICLE_CONTRACT_VERSION)
        return not errors, "; ".join(errors)
    required = {"contract_version", "reject", "scopes", "dimensions", "evidence", "summary"}
    errors = []
    if set(result) != required:
        errors.append(f"Article result must contain exactly {sorted(required)}")
    if result.get("contract_version") != ARTICLE_CONTRACT_VERSION:
        errors.append(f"Invalid contract_version: {result.get('contract_version')}")
    if result.get("reject") is not False:
        errors.append("Accepted article requires reject=false")
    scopes = result.get("scopes")
    if not isinstance(scopes, list) or not scopes or not all(x in VALID_SCOPES for x in scopes):
        errors.append("scopes must be a non-empty list of valid unique values")
    elif len(scopes) != len(set(scopes)):
        errors.append("scopes must be unique")
    dimensions = result.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        errors.append("dimensions must contain capability, trajectory, and impact")
    else:
        for name in DIMENSIONS:
            errors.extend(f"{name}: {error}" for error in _validate_dimension(dimensions[name], True))
    evidence = result.get("evidence")
    evidence_ids: set[str] = set()
    evidence_supports: dict[str, set[str]] = {}
    if not isinstance(evidence, list):
        errors.append("evidence must be a list")
    else:
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"id", "quote", "attribution", "supports"}:
                errors.append("each evidence item has an invalid shape")
                continue
            evidence_id = item.get("id")
            if not isinstance(evidence_id, str) or not evidence_id or evidence_id in evidence_ids:
                errors.append("evidence IDs must be non-empty and unique")
            else:
                evidence_ids.add(evidence_id)
            if not isinstance(item.get("quote"), str) or not item["quote"].strip() or len(item["quote"]) > 240:
                errors.append("evidence quote must contain 1-240 characters")
            if item.get("attribution") not in VALID_ATTRIBUTIONS:
                errors.append(f"invalid evidence attribution: {item.get('attribution')}")
            supports = item.get("supports")
            if not isinstance(supports, list) or not supports or not all(x in DIMENSIONS for x in supports):
                errors.append("evidence supports must contain valid dimensions")
            elif isinstance(evidence_id, str):
                evidence_supports[evidence_id] = set(supports)
    if isinstance(dimensions, dict) and set(dimensions) == set(DIMENSIONS):
        referenced = {x for value in dimensions.values() for x in value.get("evidence_ids", [])}
        if referenced != evidence_ids:
            errors.append("evidence IDs and dimension references must match exactly")
        expected = {
            evidence_id: {name for name, value in dimensions.items() if evidence_id in value.get("evidence_ids", [])}
            for evidence_id in referenced
        }
        if expected != evidence_supports:
            errors.append("evidence supports must match dimension references exactly")
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary.split()) > ARTICLE_SUMMARY_MAX_WORDS:
        errors.append(f"summary must contain 1-{ARTICLE_SUMMARY_MAX_WORDS} words")
    return not errors, "; ".join(errors)


def _validate_relation(value: Any, parent: bool) -> list[str]:
    if not isinstance(value, dict):
        return ["relation must be an object"]
    required = {"relation", "confidence", "rationale"} if parent else {
        "relation", "targets", "confidence", "rationale",
    }
    if set(value) != required:
        return [f"relation must contain exactly {sorted(required)}"]
    errors = []
    allowed = VALID_PARENT_RELATIONS if parent else VALID_ARTICLE_RELATIONS
    if value.get("relation") not in allowed:
        errors.append(f"invalid relation: {value.get('relation')}")
    confidence = value.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("relation confidence must be in [0, 1]")
    if not isinstance(value.get("rationale"), str) or not value["rationale"].strip():
        errors.append("relation rationale must be non-empty")
    if not parent:
        targets = value.get("targets")
        if not isinstance(targets, list) or len(targets) != len(set(targets)) or not all(x in VALID_ARTICLE_TARGETS for x in targets):
            errors.append("article relation targets must be valid and unique")
    return errors


def validate_comment_analysis(result: dict[str, Any], expected_id: int) -> tuple[bool, str]:
    """Validate one isolated voting-comment result."""
    if result.get("reject") is True:
        errors = _validate_rejection(result, COMMENT_CONTRACT_VERSION)
        if result.get("comment_id") != expected_id:
            errors.append("comment ID must match the isolated input")
        return not errors, "; ".join(errors)
    required = {
        "contract_version", "comment_id", "reject", "ai_dimensions",
        "article_relation", "parent_relation", "summary",
    }
    errors = []
    if set(result) != required:
        errors.append(f"Comment result must contain exactly {sorted(required)}")
    if result.get("contract_version") != COMMENT_CONTRACT_VERSION:
        errors.append(f"Invalid contract_version: {result.get('contract_version')}")
    if result.get("comment_id") != expected_id:
        errors.append("comment ID must match the isolated input")
    if result.get("reject") is not False:
        errors.append("Accepted comment requires reject=false")
    dimensions = result.get("ai_dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        errors.append("ai_dimensions must contain capability, trajectory, and impact")
    else:
        for name in DIMENSIONS:
            errors.extend(f"{name}: {error}" for error in _validate_dimension(dimensions[name], False, True))
    errors.extend(f"article_relation: {error}" for error in _validate_relation(result.get("article_relation"), False))
    errors.extend(f"parent_relation: {error}" for error in _validate_relation(result.get("parent_relation"), True))
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary.split()) > COMMENT_SUMMARY_MAX_WORDS:
        errors.append(f"summary must contain 1-{COMMENT_SUMMARY_MAX_WORDS} words")
    return not errors, "; ".join(errors)


def composite_score(scores: dict[str, float | None]) -> float | None:
    addressed = [score for score in scores.values() if score is not None]
    return sum(addressed) / len(addressed) if addressed else None


def raw_visibility_weight(root_rank: int, sibling_rank: int, depth: int) -> float:
    branch = 1 / math.log2(root_rank + 1)
    within = 1.0 if depth == 0 else math.pow(0.85, depth) / math.log2(sibling_rank + 1)
    return branch * within


def effective_sample_size(weights: list[float]) -> float:
    total = sum(weights)
    return math.pow(total, 2) / sum(math.pow(weight, 2) for weight in weights) if weights else 0.0


def aggregate_comment_dimension(
    annotations: list[dict[str, Any]], comments: dict[int, SelectedComment], dimension: str,
) -> dict[str, Any]:
    applicable = []
    for annotation in annotations:
        if annotation.get("reject"):
            continue
        value = annotation["ai_dimensions"][dimension]
        if value["applicability"] != "not_addressed":
            applicable.append((annotation, comments[annotation["comment_id"]], value))
    analyzed_count = sum(not item.get("reject") for item in annotations)
    if not applicable:
        return {
            "applicability": "not_addressed", "score": None, "confidence": 0.0,
            "visibility_weighted_score": None, "diversity_balanced_score": None,
            "ranking_sensitivity": None, "positive_share": 0.0, "neutral_share": 0.0,
            "negative_share": 0.0, "disagreement": None, "polarization": 0.0,
            "effective_sample_size": 0.0, "applicable_comment_count": 0,
            "applicable_author_count": 0, "applicable_branch_count": 0,
            "dimension_coverage": 0.0, "clarity": 0.0, "dissent": None,
        }
    author_counts: dict[str, int] = {}
    branch_authors: dict[int, set[str]] = {}
    for _, comment, _ in applicable:
        author_counts[comment.author] = author_counts.get(comment.author, 0) + 1
        branch_authors.setdefault(comment.root_id, set()).add(comment.author)
    rows = []
    for annotation, comment, value in applicable:
        concentration = (1 / author_counts[comment.author]) / math.sqrt(len(branch_authors[comment.root_id]))
        structural = comment.raw_visibility_weight * concentration
        visibility = structural * value["confidence"]
        diversity = concentration * value["confidence"]
        rows.append((annotation, comment, float(value["score"]), structural, visibility, diversity, float(value["confidence"])))
    visibility_total = sum(row[4] for row in rows)
    diversity_total = sum(row[5] for row in rows)
    score = sum(row[2] * row[4] for row in rows) / visibility_total
    diversity_score = sum(row[2] * row[5] for row in rows) / diversity_total
    positive = sum(row[4] for row in rows if row[2] > 0) / visibility_total
    neutral = sum(row[4] for row in rows if row[2] == 0) / visibility_total
    negative = sum(row[4] for row in rows if row[2] < 0) / visibility_total
    disagreement = sum(row[4] * abs(row[2] - score) for row in rows) / visibility_total / 2
    positive_rows = [row for row in rows if row[2] > 0]
    negative_rows = [row for row in rows if row[2] < 0]
    polarization = 0.0
    if positive_rows and negative_rows:
        mean_positive = sum(row[2] * row[4] for row in positive_rows) / sum(row[4] for row in positive_rows)
        mean_negative = sum(row[2] * row[4] for row in negative_rows) / sum(row[4] for row in negative_rows)
        polarization = 4 * positive * negative * ((mean_positive - mean_negative) / 4)
    structural_weights = [row[3] for row in rows]
    ess = effective_sample_size([row[4] for row in rows])
    clarity = sum(row[3] * row[6] for row in rows) / sum(structural_weights)
    coverage = len(rows) / max(1, analyzed_count)
    branch_count = len(branch_authors)
    confidence = clarity * math.sqrt(min(1, ess / 12) * min(1, branch_count / 6) * coverage)
    opposing = [row for row in rows if score != 0 and row[2] * score < 0]
    dissent = None
    if opposing:
        row = max(opposing, key=lambda item: (item[4], -item[0]["comment_id"]))
        dissent = {
            "comment_id": row[0]["comment_id"], "summary": row[0]["summary"],
            "opposing_influence_share": row[4] / visibility_total,
        }
    return {
        "applicability": "explicit", "score": round(score, 6),
        "confidence": round(min(1, confidence), 6),
        "visibility_weighted_score": round(score, 6),
        "diversity_balanced_score": round(diversity_score, 6),
        "ranking_sensitivity": round(abs(score - diversity_score), 6),
        "positive_share": round(min(1, positive), 6),
        "neutral_share": round(min(1, neutral), 6),
        "negative_share": round(min(1, negative), 6),
        "disagreement": round(min(1, disagreement), 6),
        "polarization": round(min(1, polarization), 6),
        "effective_sample_size": round(ess, 6),
        "applicable_comment_count": len(rows),
        "applicable_author_count": len(author_counts),
        "applicable_branch_count": branch_count,
        "dimension_coverage": round(coverage, 6), "clarity": round(clarity, 6),
        "dissent": dissent,
    }


def combine_sources(
    article: dict[str, Any], community: dict[str, Any], article_prior: float = 0.4,
) -> dict[str, Any]:
    sources = []
    if article["applicability"] != "not_addressed":
        sources.append((article["score"], article_prior * article["confidence"], "article"))
    if community["applicability"] != "not_addressed":
        sources.append((community["score"], (1 - article_prior) * community["confidence"], "community"))
    if not sources:
        return {"score": None, "confidence": 0.0, "sources": []}
    influence = sum(weight for _, weight, _ in sources)
    return {
        "score": sum(score * weight for score, weight, _ in sources) / influence,
        "confidence": min(1.0, influence), "sources": [name for _, _, name in sources],
    }
