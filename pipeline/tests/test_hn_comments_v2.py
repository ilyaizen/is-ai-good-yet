from pipeline.src.hn_comments_v2 import (
    accepted_target, branch_cap, build_candidate_stream, candidate_is_eligible,
)


def comment(
    comment_id: int, author: str, root_rank: int, sibling_rank: int = 1,
    depth: int = 0, root_id: int | None = None, parent_id: int = 99, text: str = "AI",
) -> dict:
    root = root_id or comment_id
    return {
        "id": comment_id, "parent_id": parent_id, "root_id": root, "author": author,
        "text": text, "depth": depth, "root_rank": root_rank,
        "sibling_rank": sibling_rank, "ancestry_ids": [root, comment_id] if depth else [root],
    }


def test_adaptive_target_boundaries() -> None:
    assert accepted_target(0) == 0
    assert accepted_target(7) == 7
    assert accepted_target(12) == 12
    assert accepted_target(25) == 20
    assert accepted_target(10_000) == 32


def test_branch_cap_formula() -> None:
    assert branch_cap(12) == 3
    assert branch_cap(32) == 5


def test_local_ranks_and_short_comments_are_preserved() -> None:
    comments = [
        comment(1, "a", 1),
        comment(2, "b", 1, sibling_rank=2, depth=1, root_id=1, parent_id=1, text="No"),
        comment(3, "c", 2),
    ]
    selected = build_candidate_stream(10, comments)
    reply = next(item for item in selected if item.hn_comment_id == 2)
    assert reply.root_rank == 1
    assert reply.sibling_rank == 2
    assert reply.text == "No"


def test_candidate_stream_is_deterministic_and_branch_round_robin() -> None:
    comments = [comment(index, f"root{index}", index) for index in range(1, 4)]
    comments += [
        comment(10, "a", 1, 1, 1, 1, 1), comment(11, "b", 1, 2, 1, 1, 1),
        comment(20, "c", 2, 1, 1, 2, 2), comment(30, "d", 3, 1, 1, 3, 3),
    ]
    first = build_candidate_stream(10, comments)
    second = build_candidate_stream(10, comments)
    assert first == second
    reply_ids = [item.hn_comment_id for item in first if item.selection_pass == "reply_branch_diversity"]
    assert reply_ids == [10, 20]
    refill_ids = [item.hn_comment_id for item in first if item.selection_pass == "remaining_replies"]
    assert refill_ids[0] == 30


def test_caps_apply_to_accepted_comments_not_rejections() -> None:
    candidates = build_candidate_stream(
        10, [comment(1, "same", 1), comment(2, "same", 2), comment(3, "same", 3)],
    )
    assert candidate_is_eligible(candidates[2], [], 12)
    assert not candidate_is_eligible(candidates[2], candidates[:2], 12)
