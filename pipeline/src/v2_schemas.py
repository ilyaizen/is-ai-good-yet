"""Strict Groq JSON schemas for the immutable V2 model contracts."""

from __future__ import annotations

from typing import Any

from .v2_models import (
    ARTICLE_CONTRACT_VERSION,
    ARTICLE_SUMMARY_MAX_WORDS,
    COMMENT_CONTRACT_VERSION,
    COMMENT_SUMMARY_MAX_WORDS,
    DIMENSIONS,
    PREFILTER_CONTRACT_VERSION,
    VALID_APPLICABILITY,
    VALID_ARTICLE_RELATIONS,
    VALID_ARTICLE_TARGETS,
    VALID_ATTRIBUTIONS,
    VALID_PARENT_RELATIONS,
    VALID_REJECTION_CODES,
    VALID_SCOPES,
    VALID_STANCE_BASES,
)


def closed(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def enum(values: set[str] | tuple[str, ...] | list[Any]) -> dict[str, Any]:
    return {"type": "string", "enum": sorted(values)}


def rejection_schema(contract_version: str, comment: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "contract_version": {"type": "string", "enum": [contract_version]},
    }
    if comment:
        properties["comment_id"] = {"type": "integer"}
    properties.update(
        {
            "reject": {"type": "boolean", "enum": [True]},
            "reason_code": enum(VALID_REJECTION_CODES),
            "reason": {"type": "string", "minLength": 1},
        }
    )
    return closed(properties)


def dimension_schema(evidence: bool, stance: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "applicability": enum(VALID_APPLICABILITY),
        "score": {
            "anyOf": [
                {"type": "integer", "enum": [-2, -1, 0, 1, 2]},
                {"type": "null"},
            ]
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string", "minLength": 1},
    }
    if evidence:
        properties["evidence_ids"] = {
            "type": "array", "items": {"type": "string", "minLength": 1},
        }
    if stance:
        properties["stance_basis"] = enum(VALID_STANCE_BASES)
    return closed(properties)


ARTICLE_DIMENSIONS_SCHEMA = closed({name: dimension_schema(True, False) for name in DIMENSIONS})
ARTICLE_EVIDENCE_SCHEMA = {
    "type": "array",
    "items": closed(
        {
            "id": {"type": "string", "minLength": 1},
            "quote": {"type": "string", "minLength": 1, "maxLength": 1000},
            "attribution": enum(VALID_ATTRIBUTIONS),
            "supports": {
                "type": "array", "items": enum(DIMENSIONS), "minItems": 1,
            },
        }
    ),
}
ARTICLE_SCHEMA = closed(
    {
        "contract_version": {"type": "string", "enum": [ARTICLE_CONTRACT_VERSION]},
        "reject": {"type": "boolean"},
        "scopes": {
            "type": "array", "items": enum(VALID_SCOPES),
        },
        "dimensions": {"anyOf": [ARTICLE_DIMENSIONS_SCHEMA, {"type": "null"}]},
        "evidence": ARTICLE_EVIDENCE_SCHEMA,
        "summary": {"type": ["string", "null"]},
        "reason_code": {"anyOf": [enum(VALID_REJECTION_CODES), {"type": "null"}]},
        "reason": {"type": ["string", "null"]},
    }
)

ARTICLE_RELATION_SCHEMA = closed(
    {
        "relation": enum(VALID_ARTICLE_RELATIONS),
        "targets": {"type": "array", "items": enum(VALID_ARTICLE_TARGETS)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string", "minLength": 1},
    }
)
PARENT_RELATION_SCHEMA = closed(
    {
        "relation": enum(VALID_PARENT_RELATIONS),
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string", "minLength": 1},
    }
)
COMMENT_DIMENSIONS_SCHEMA = closed({name: dimension_schema(False, True) for name in DIMENSIONS})
COMMENT_SCHEMA = closed(
    {
        "contract_version": {"type": "string", "enum": [COMMENT_CONTRACT_VERSION]},
        "comment_id": {"type": "integer"},
        "reject": {"type": "boolean"},
        "ai_dimensions": {"anyOf": [COMMENT_DIMENSIONS_SCHEMA, {"type": "null"}]},
        "article_relation": {"anyOf": [ARTICLE_RELATION_SCHEMA, {"type": "null"}]},
        "parent_relation": {"anyOf": [PARENT_RELATION_SCHEMA, {"type": "null"}]},
        "summary": {"type": ["string", "null"]},
        "reason_code": {"anyOf": [enum(VALID_REJECTION_CODES), {"type": "null"}]},
        "reason": {"type": ["string", "null"]},
    }
)

PREFILTER_PROPERTIES = {
    "contract_version": {"type": "string", "enum": [PREFILTER_CONTRACT_VERSION]},
    "eligible": {"type": "boolean"},
    "scopes": {"type": "array", "items": enum(VALID_SCOPES)},
    "reason_code": {"type": "string", "minLength": 1},
    "reason": {"type": "string", "minLength": 1},
}
PREFILTER_SCHEMA = closed(PREFILTER_PROPERTIES)


def normalize_article_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("reject"):
        keys = ("contract_version", "reject", "reason_code", "reason")
        return {key: result.get(key) for key in keys}

    keys = ("contract_version", "reject", "scopes", "dimensions", "evidence", "summary")
    normalized = {key: result.get(key) for key in keys}
    if isinstance(normalized["summary"], str):
        normalized["summary"] = " ".join(
            normalized["summary"].split()[:ARTICLE_SUMMARY_MAX_WORDS]
        )
    for item in normalized["evidence"] or []:
        if isinstance(item.get("quote"), str):
            item["quote"] = item["quote"][:240]
    return normalized


def normalize_comment_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("reject"):
        keys = ("contract_version", "comment_id", "reject", "reason_code", "reason")
        return {key: result.get(key) for key in keys}

    normalized = {
        key: result.get(key)
        for key in (
            "contract_version", "comment_id", "reject", "ai_dimensions",
            "article_relation", "parent_relation", "summary",
        )
    }
    if normalized["article_relation"] is None:
        normalized["article_relation"] = {
            "relation": "not_applicable", "targets": [], "confidence": 0,
            "rationale": "No article relation provided.",
        }
    if normalized["parent_relation"] is None:
        normalized["parent_relation"] = {
            "relation": "not_applicable", "confidence": 0,
            "rationale": "No parent relation provided.",
        }
    if isinstance(normalized["summary"], str):
        normalized["summary"] = " ".join(
            normalized["summary"].split()[:COMMENT_SUMMARY_MAX_WORDS]
        )
    return normalized
