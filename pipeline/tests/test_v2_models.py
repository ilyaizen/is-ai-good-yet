import math

from pipeline.src.v2_models import (
    COMMENT_CONTRACT_VERSION, PREFILTER_CONTRACT_VERSION, SelectedComment,
    aggregate_comment_dimension, combine_sources, raw_visibility_weight,
    validate_comment_analysis, validate_prefilter_result,
)


def dimension(score: int | None, confidence: float = 1.0) -> dict:
    return {
        "applicability": "not_addressed" if score is None else "explicit",
        "score": score, "confidence": 0 if score is None else confidence,
        "stance_basis": "none" if score is None else "direct", "rationale": "Clear.",
    }


def annotation(comment_id: int, score: int | None, confidence: float = 1.0) -> dict:
    return {
        "contract_version": COMMENT_CONTRACT_VERSION, "comment_id": comment_id,
        "reject": False,
        "ai_dimensions": {name: dimension(score, confidence) for name in ("capability", "trajectory", "impact")},
        "article_relation": {"relation": "not_applicable", "targets": [], "confidence": 0, "rationale": "None."},
        "parent_relation": {"relation": "not_applicable", "confidence": 0, "rationale": "None."},
        "summary": "Clear stance.",
    }


def selected(comment_id: int, author: str, root_id: int, root_rank: int) -> SelectedComment:
    return SelectedComment(
        comment_id, 1, 1, root_id, author, "text", 0, root_rank, root_rank,
        (comment_id,), comment_id, "pass", "reason", raw_visibility_weight(root_rank, root_rank, 0),
    )


def test_single_comment_contract_separates_stance_and_relations() -> None:
    result = annotation(7, -1)
    assert validate_comment_analysis(result, 7) == (True, "")
    result["ai_dimensions"]["impact"]["stance_basis"] = "none"
    valid, error = validate_comment_analysis(result, 7)
    assert not valid
    assert "stance_basis" in error


def test_not_addressed_requires_null_zero_none() -> None:
    result = annotation(7, None)
    result["ai_dimensions"]["capability"]["score"] = 0
    assert not validate_comment_analysis(result, 7)[0]


def test_visibility_and_diversity_are_distinct_hand_calculation() -> None:
    comments = {1: selected(1, "a", 1, 1), 2: selected(2, "b", 2, 2)}
    result = aggregate_comment_dimension([annotation(1, 2), annotation(2, -2)], comments, "capability")
    second_weight = 1 / math.log2(3)
    expected_visibility = (2 - (2 * second_weight)) / (1 + second_weight)
    assert math.isclose(result["visibility_weighted_score"], expected_visibility, abs_tol=1e-6)
    assert result["diversity_balanced_score"] == 0
    assert result["ranking_sensitivity"] == round(abs(expected_visibility), 6)


def test_equal_extremes_are_neutral_polarized_and_disagreeing() -> None:
    comments = {1: selected(1, "a", 1, 1), 2: selected(2, "b", 1, 1)}
    result = aggregate_comment_dimension([annotation(1, 2), annotation(2, -2)], comments, "capability")
    assert result["score"] == 0
    assert result["disagreement"] == 1
    assert result["polarization"] == 1


def test_disagreement_does_not_change_confidence() -> None:
    comments = {1: selected(1, "a", 1, 1), 2: selected(2, "b", 1, 1)}
    divided = aggregate_comment_dimension([annotation(1, 2), annotation(2, -2)], comments, "capability")
    unanimous = aggregate_comment_dimension([annotation(1, 2), annotation(2, 2)], comments, "capability")
    assert divided["confidence"] == unanimous["confidence"]


def test_relation_confidence_does_not_enter_aggregation() -> None:
    item = annotation(1, 1)
    comments = {1: selected(1, "a", 1, 1)}
    first = aggregate_comment_dimension([item], comments, "capability")
    item["article_relation"]["confidence"] = 1
    item["parent_relation"]["confidence"] = 1
    assert aggregate_comment_dimension([item], comments, "capability") == first


def test_source_combination_keeps_confidence_as_influence() -> None:
    result = combine_sources(
        {"applicability": "explicit", "score": 2, "confidence": 0.5},
        {"applicability": "explicit", "score": -1, "confidence": 1},
    )
    assert math.isclose(result["score"], -0.25)
    assert math.isclose(result["confidence"], 0.8)


def test_v2_prefilter_requires_scopes_only_for_eligible_content() -> None:
    eligible = {
        "contract_version": PREFILTER_CONTRACT_VERSION,
        "eligible": True,
        "scopes": ["research", "general"],
        "reason_code": "substantive_ai_claim",
        "reason": "The source evaluates an AI research system.",
    }
    assert validate_prefilter_result(eligible) == (True, "")
    eligible["scopes"] = []
    assert not validate_prefilter_result(eligible)[0]


def test_v2_prefilter_rejects_unknown_scope() -> None:
    result = {
        "contract_version": PREFILTER_CONTRACT_VERSION,
        "eligible": True,
        "scopes": ["marketing"],
        "reason_code": "substantive_ai_claim",
        "reason": "Invalid scope should fail.",
    }
    assert not validate_prefilter_result(result)[0]
