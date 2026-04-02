"""Unit tests for scohthwang.block."""

from __future__ import annotations

import operator

import pytest

from scohthwang.block import (
    BlockingFn,
    all_pairs,
    compose_blocks,
    key_equality_block,
    predicate_block,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pairs(fn: BlockingFn, left: list, right: list) -> set[tuple[int, int]]:
    """Collect blocking output into a set for easy comparison."""
    return set(fn(left, right))


def _all_index_pairs(left: list, right: list) -> set[tuple[int, int]]:
    return {(i, j) for i in range(len(left)) for j in range(len(right))}


def _recall_ok(
    candidates: set[tuple[int, int]],
    known_correct: set[tuple[int, int]],
) -> bool:
    """Return True when every known-correct pair is in the candidate set."""
    return known_correct <= candidates


# ---------------------------------------------------------------------------
# all_pairs
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_empty_left() -> None:
    assert list(all_pairs([], [1, 2])) == []


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_empty_right() -> None:
    assert list(all_pairs([1, 2], [])) == []


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_both_empty() -> None:
    assert list(all_pairs([], [])) == []


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_singleton() -> None:
    assert list(all_pairs(["a"], ["b"])) == [(0, 0)]


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_2x2() -> None:
    result = set(all_pairs(["a", "b"], ["x", "y"]))
    assert result == {(0, 0), (0, 1), (1, 0), (1, 1)}


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_3x2() -> None:
    result = set(all_pairs([0, 1, 2], ["x", "y"]))
    assert result == {(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)}


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_recall() -> None:
    left = ["a", "b", "c"]
    right = ["x", "y"]
    known_correct = {(0, 1), (2, 0)}
    candidates = set(all_pairs(left, right))
    assert _recall_ok(candidates, known_correct)


# ---------------------------------------------------------------------------
# key_equality_block
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_empty_sequences() -> None:
    fn = key_equality_block(lambda x: x)
    assert list(fn([], [])) == []


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_no_matches() -> None:
    fn = key_equality_block(lambda x: x)
    assert list(fn([1, 2], [3, 4])) == []


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_all_match() -> None:
    fn = key_equality_block(lambda x: x)
    result = set(fn(["a", "b"], ["a", "b"]))
    assert result == {(0, 0), (1, 1)}


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_one_shared_key() -> None:
    fn = key_equality_block(lambda x: x)
    result = set(fn(["a", "b"], ["b", "c"]))
    assert result == {(1, 0)}


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_field_extractor() -> None:
    left = [{"chain": "A"}, {"chain": "B"}, {"chain": "C"}]
    right = [{"chain": "B"}, {"chain": "D"}]
    fn = key_equality_block(operator.itemgetter("chain"))
    result = set(fn(left, right))
    assert result == {(1, 0)}


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_multiple_right_matches() -> None:
    # Two right elements share the same key as one left element.
    fn = key_equality_block(lambda x: x % 3)
    left = [0, 1, 2]
    right = [0, 3, 6, 1]  # keys: 0, 0, 0, 1
    result = set(fn(left, right))
    assert (0, 0) in result
    assert (0, 1) in result
    assert (0, 2) in result
    assert (1, 3) in result


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_recall() -> None:
    left = [{"type": "CA"}, {"type": "CB"}, {"type": "CA"}]
    right = [{"type": "CB"}, {"type": "CA"}]
    fn = key_equality_block(operator.itemgetter("type"))
    known_correct = {(0, 1), (1, 0), (2, 1)}
    candidates = set(fn(left, right))
    assert _recall_ok(candidates, known_correct)


# ---------------------------------------------------------------------------
# predicate_block
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_predicate_empty_sequences() -> None:
    fn = predicate_block(lambda _left_item, _right_item: True)
    assert list(fn([], [])) == []


@pytest.mark.unit
@pytest.mark.small
def test_predicate_always_false() -> None:
    fn = predicate_block(lambda _left_item, _right_item: False)
    assert list(fn([1, 2, 3], [4, 5])) == []


@pytest.mark.unit
@pytest.mark.small
def test_predicate_always_true_equals_all_pairs() -> None:
    left = [1, 2, 3]
    right = [4, 5]
    fn = predicate_block(lambda _left_item, _right_item: True)
    result = set(fn(left, right))
    assert result == _all_index_pairs(left, right)


@pytest.mark.unit
@pytest.mark.small
def test_predicate_equality() -> None:
    fn = predicate_block(operator.eq)
    result = set(fn([1, 2, 3], [3, 1, 4]))
    assert result == {(0, 1), (2, 0)}


@pytest.mark.unit
@pytest.mark.small
def test_predicate_numeric_range() -> None:
    fn = predicate_block(lambda left_item, right_item: abs(left_item - right_item) <= 1)
    left = [0, 5, 10]
    right = [1, 6, 20]
    result = set(fn(left, right))
    assert (0, 0) in result  # |0-1| = 1 ✓
    assert (1, 1) in result  # |5-6| = 1 ✓
    assert (2, 2) not in result  # |10-20| = 10 ✗


@pytest.mark.unit
@pytest.mark.small
def test_predicate_recall() -> None:
    # Predicate: same parity.  left=[1,2,3,4], right=[2,4,6]
    # Odd left (1,3) → no odd right elements; even left (2,4) → all right elements.
    # Spot-check a known-correct subset: (1,0), (1,2), (3,1).
    left = [1, 2, 3, 4]
    right = [2, 4, 6]
    fn = predicate_block(lambda left_item, right_item: left_item % 2 == right_item % 2)
    known_correct = {(1, 0), (1, 2), (3, 1)}
    candidates = set(fn(left, right))
    assert _recall_ok(candidates, known_correct)


# ---------------------------------------------------------------------------
# compose_blocks — union
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_compose_union_single_fn_identity() -> None:
    fn = key_equality_block(lambda x: x)
    composed = compose_blocks(fn, mode="union")
    left = ["a", "b", "c"]
    right = ["b", "d"]
    assert _pairs(composed, left, right) == _pairs(fn, left, right)


@pytest.mark.unit
@pytest.mark.small
def test_compose_union_two_fns_superset() -> None:
    fn_a = key_equality_block(operator.itemgetter(0))  # first character
    fn_b = key_equality_block(operator.itemgetter(-1))  # last character
    composed = compose_blocks(fn_a, fn_b, mode="union")
    left = ["ab", "cd"]
    right = ["ad", "cb"]
    result = _pairs(composed, left, right)
    # Union must be at least as large as either individual blocker.
    assert _pairs(fn_a, left, right) <= result
    assert _pairs(fn_b, left, right) <= result


@pytest.mark.unit
@pytest.mark.small
def test_compose_union_no_duplicates() -> None:
    # Both blockers yield the same pairs; union should deduplicate.
    fn = key_equality_block(lambda x: x)
    compose_blocks(fn, fn, mode="union")
    left = ["a", "b"]
    right = ["a", "b"]
    result = list(compose_blocks(fn, fn, mode="union")(left, right))
    assert len(result) == len(set(result))


@pytest.mark.unit
@pytest.mark.small
def test_compose_union_recall() -> None:
    fn_a = key_equality_block(lambda x: x % 2)
    fn_b = predicate_block(operator.eq)
    composed = compose_blocks(fn_a, fn_b, mode="union")
    left = [1, 2, 3]
    right = [1, 3, 5]
    known_correct = {(0, 0), (2, 1)}
    candidates = _pairs(composed, left, right)
    assert _recall_ok(candidates, known_correct)


# ---------------------------------------------------------------------------
# compose_blocks — intersection
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_compose_intersection_single_fn_identity() -> None:
    fn = key_equality_block(lambda x: x)
    composed = compose_blocks(fn, mode="intersection")
    left = ["a", "b"]
    right = ["a", "c"]
    assert _pairs(composed, left, right) == _pairs(fn, left, right)


@pytest.mark.unit
@pytest.mark.small
def test_compose_intersection_is_subset_of_each() -> None:
    fn_a = key_equality_block(lambda x: x % 2)
    fn_b = predicate_block(lambda left_item, right_item: abs(left_item - right_item) <= 2)
    composed = compose_blocks(fn_a, fn_b, mode="intersection")
    left = [1, 2, 3, 4]
    right = [1, 2, 5]
    result = _pairs(composed, left, right)
    assert result <= _pairs(fn_a, left, right)
    assert result <= _pairs(fn_b, left, right)


@pytest.mark.unit
@pytest.mark.small
def test_compose_intersection_empty_when_disjoint() -> None:
    fn_a = key_equality_block(lambda x: x)  # identity key
    fn_b = predicate_block(lambda _left_item, _right_item: False)  # never
    composed = compose_blocks(fn_a, fn_b, mode="intersection")
    assert _pairs(composed, [1, 2], [1, 2]) == set()


# ---------------------------------------------------------------------------
# compose_blocks — error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_compose_empty_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        compose_blocks(mode="union")


@pytest.mark.unit
@pytest.mark.small
def test_compose_invalid_mode_raises() -> None:
    fn = key_equality_block(lambda x: x)
    with pytest.raises(ValueError, match="mode"):
        compose_blocks(fn, mode="invalid")  # type: ignore[arg-type]  # intentional invalid literal to assert runtime validation path.


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_all_pairs_is_blocking_fn() -> None:
    fn: BlockingFn = all_pairs
    assert callable(fn)


@pytest.mark.unit
@pytest.mark.small
def test_key_equality_returns_blocking_fn() -> None:
    fn: BlockingFn = key_equality_block(lambda x: x)
    assert callable(fn)


@pytest.mark.unit
@pytest.mark.small
def test_predicate_returns_blocking_fn() -> None:
    fn: BlockingFn = predicate_block(operator.eq)
    assert callable(fn)


@pytest.mark.unit
@pytest.mark.small
def test_compose_returns_blocking_fn() -> None:
    fn: BlockingFn = compose_blocks(all_pairs, mode="union")
    assert callable(fn)
