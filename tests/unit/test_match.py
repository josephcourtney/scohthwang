"""Unit tests for scohthwang.match."""

from __future__ import annotations

import operator

import pytest

from scohthwang.match import Level, group_and_match, hierarchical_match, match_within_group
from scohthwang.models import LARGE_COST, MatchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LARGE = LARGE_COST


def _identity_cost(left_value: float, right_value: float) -> float:
    return float(abs(left_value - right_value))


def _zero_cost(_left_value: object, _right_value: object) -> float:
    return 0.0


def _all_large(_left_value: object, _right_value: object) -> float:
    return _LARGE


def _char_cost(left_value: str, right_value: str) -> float:
    return 0.0 if left_value == right_value else _LARGE


def _matched_pairs(result: MatchResult) -> set[tuple[int, int]]:
    return set(result.pairs)


def _total_elements(result: MatchResult) -> int:
    return len(result.pairs) * 2 + len(result.unmatched_left) + len(result.unmatched_right)


# ---------------------------------------------------------------------------
# match_within_group — empty inputs
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_match_both_empty() -> None:
    r = match_within_group([], [], _identity_cost, unmatched_cost=5.0)
    assert r == MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_empty_left() -> None:
    r = match_within_group([], [1.0, 2.0], _identity_cost, unmatched_cost=5.0)
    assert r.pairs == []
    assert r.unmatched_left == []
    assert set(r.unmatched_right) == {0, 1}
    assert r.total_cost == pytest.approx(10.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_empty_right() -> None:
    r = match_within_group([1.0, 2.0], [], _identity_cost, unmatched_cost=5.0)
    assert r.pairs == []
    assert set(r.unmatched_left) == {0, 1}
    assert r.unmatched_right == []
    assert r.total_cost == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# match_within_group — correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_match_perfect_1to1() -> None:
    left = [1.0, 2.0, 3.0]
    right = [1.0, 2.0, 3.0]
    r = match_within_group(left, right, _identity_cost, unmatched_cost=10.0)
    assert _matched_pairs(r) == {(0, 0), (1, 1), (2, 2)}
    assert r.unmatched_left == []
    assert r.unmatched_right == []
    assert r.total_cost == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_optimal_assignment() -> None:
    # left=[0, 10], right=[1, 9].  Best: 0↔1 (cost 1), 10↔9 (cost 1), total 2.
    left = [0.0, 10.0]
    right = [1.0, 9.0]
    r = match_within_group(left, right, _identity_cost, unmatched_cost=100.0)
    assert _matched_pairs(r) == {(0, 0), (1, 1)}
    assert r.total_cost == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_extra_left_elements_become_unmatched() -> None:
    # If every real pair is more expensive than unmatched_cost, both sides opt out.
    left = ["a", "b", "c"]
    right = ["x", "y"]
    r = match_within_group(left, right, _all_large, unmatched_cost=1.0)
    assert r.pairs == []
    assert r.unmatched_left == [0, 1, 2]
    assert r.unmatched_right == [0, 1]
    assert r.total_cost == pytest.approx(5.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_rectangular_more_left() -> None:
    left = [1.0, 2.0, 100.0]
    right = [1.0, 2.0]
    r = match_within_group(left, right, _identity_cost, unmatched_cost=5.0)
    assert len(r.pairs) == 2
    assert len(r.unmatched_left) == 1
    assert r.unmatched_right == []
    assert 100 in left  # sanity: 100.0 is the odd one out
    unmatched_values = [left[i] for i in r.unmatched_left]
    assert 2 in unmatched_values or 100.0 in unmatched_values


@pytest.mark.unit
@pytest.mark.small
def test_match_rectangular_more_right() -> None:
    left = [1.0, 2.0]
    right = [1.0, 2.0, 100.0]
    r = match_within_group(left, right, _identity_cost, unmatched_cost=5.0)
    assert len(r.pairs) == 2
    assert r.unmatched_left == []
    assert len(r.unmatched_right) == 1


@pytest.mark.unit
@pytest.mark.small
def test_match_total_cost_includes_unmatched_penalties() -> None:
    # 1 matched pair at cost 0.5, 1 unmatched left at cost 3.0, 1 unmatched right at cost 3.0.
    left = [1.0, 999.0]
    right = [1.5]
    r = match_within_group(left, right, _identity_cost, unmatched_cost=3.0)
    assert r.total_cost == pytest.approx(0.5 + 3.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_result_covers_all_indices() -> None:
    left = list(range(4))
    right = list(range(3))
    r = match_within_group(left, right, _zero_cost, unmatched_cost=1.0)
    paired_left = {li for li, _ in r.pairs}
    all_left = paired_left | set(r.unmatched_left)
    paired_right = {ri for _, ri in r.pairs}
    all_right = paired_right | set(r.unmatched_right)
    assert all_left == set(range(len(left)))
    assert all_right == set(range(len(right)))


# ---------------------------------------------------------------------------
# match_within_group — blocking
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_match_with_block_fn_filters_pairs() -> None:
    # block_fn only allows (0,0) and (1,1) — no cross pairs.
    from scohthwang.block import predicate_block

    left = [0.0, 10.0]
    right = [0.0, 10.0]
    block_fn = predicate_block(operator.eq)
    r = match_within_group(left, right, _identity_cost, unmatched_cost=100.0, block_fn=block_fn)
    assert _matched_pairs(r) == {(0, 0), (1, 1)}
    assert r.total_cost == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_block_fn_avoids_wrong_pairs() -> None:
    # Only allow left[0]↔right[1] and left[1]↔right[0].
    from scohthwang.block import predicate_block

    left = [1.0, 10.0]
    right = [10.0, 1.0]
    block_fn = predicate_block(operator.eq)
    r = match_within_group(left, right, _identity_cost, unmatched_cost=100.0, block_fn=block_fn)
    assert _matched_pairs(r) == {(0, 1), (1, 0)}
    assert r.total_cost == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# group_and_match
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_group_and_match_same_keys() -> None:
    left = [("A", 1.0), ("B", 2.0), ("A", 3.0)]
    right = [("A", 1.5), ("B", 2.5)]
    cost_fn = lambda left_item, right_item: abs(left_item[1] - right_item[1])  # noqa: E731

    results = group_and_match(
        left,
        right,
        key_fn=operator.itemgetter(0),
        cost_fn=cost_fn,
        unmatched_cost=10.0,
    )

    assert set(results.keys()) == {"A", "B"}
    # Group A: left=[0->(A,1), 1->(A,3)], right=[0->(A,1.5)]; one match, one unmatched_left.
    a_result = results["A"]
    assert len(a_result.pairs) == 1
    assert len(a_result.unmatched_left) == 1


@pytest.mark.unit
@pytest.mark.small
def test_group_and_match_disjoint_keys() -> None:
    left = [("A", 1.0)]
    right = [("B", 2.0)]
    results = group_and_match(
        left,
        right,
        key_fn=operator.itemgetter(0),
        cost_fn=_zero_cost,
        unmatched_cost=5.0,
    )

    assert set(results.keys()) == {"A", "B"}
    assert results["A"].pairs == []
    assert results["A"].unmatched_left == [0]
    assert results["B"].pairs == []
    assert results["B"].unmatched_right == [0]


@pytest.mark.unit
@pytest.mark.small
def test_group_and_match_empty_inputs() -> None:
    results = group_and_match([], [], key_fn=lambda x: x, cost_fn=_zero_cost, unmatched_cost=1.0)
    assert results == {}


@pytest.mark.unit
@pytest.mark.small
def test_group_and_match_indices_are_group_relative() -> None:
    # Group "A" has 2 left elements.  Indices should be 0 and 1, not original list indices.
    left = [("A", 10.0), ("A", 20.0)]
    right = [("A", 10.5), ("A", 20.5)]
    results = group_and_match(
        left,
        right,
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=5.0,
    )
    a = results["A"]
    for li, ri in a.pairs:
        assert 0 <= li < 2
        assert 0 <= ri < 2


# ---------------------------------------------------------------------------
# hierarchical_match — errors
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_empty_levels_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        hierarchical_match([1, 2], [3, 4], [])


# ---------------------------------------------------------------------------
# hierarchical_match — single level (leaf)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_single_level_strict_perfect_match() -> None:
    left = [("A", 1.0), ("B", 2.0)]
    right = [("A", 1.0), ("B", 2.0)]
    level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=10.0,
        mode="strict",
    )
    r = hierarchical_match(left, right, [level])
    assert len(r.pairs) == 2
    assert r.total_cost == pytest.approx(0.0)
    assert r.unmatched_left == []
    assert r.unmatched_right == []


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_single_level_strict_unmatched_key() -> None:
    left = [("A", 1.0), ("C", 3.0)]
    right = [("A", 1.0), ("B", 2.0)]
    level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=5.0,
        mode="strict",
    )
    r = hierarchical_match(left, right, [level])
    # ("C", 3.0) and ("B", 2.0) have no counterpart — both unmatched.
    assert len(r.unmatched_left) == 1  # the "C" element
    assert len(r.unmatched_right) == 1  # the "B" element
    assert len(r.pairs) == 1  # the "A" match
    assert r.total_cost == pytest.approx(0.0 + 5.0 + 5.0)


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_single_level_strict_empty() -> None:
    level = Level(key_fn=lambda x: x, cost_fn=_zero_cost, unmatched_cost=1.0)
    r = hierarchical_match([], [], [level])
    assert r == MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_single_level_strict_only_left() -> None:
    left = [("A", 1.0), ("A", 2.0)]
    right: list = []
    level = Level(key_fn=operator.itemgetter(0), cost_fn=_zero_cost, unmatched_cost=3.0)
    r = hierarchical_match(left, right, [level])
    assert r.pairs == []
    assert set(r.unmatched_left) == {0, 1}
    assert r.total_cost == pytest.approx(6.0)


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_single_level_flexible_assigns_groups() -> None:
    # Two left groups (keyed "A" and "B") and two right groups (keyed "X" and "Y").
    # In flexible leaf mode, cost_fn is element-level; group costs are derived
    # by matching the elements inside each candidate group pair.
    left = [("A", 1.0), ("B", 10.0)]
    right = [("X", 1.1), ("Y", 50.0)]

    level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=50.0,
        mode="flexible",
    )
    r = hierarchical_match(left, right, [level])
    # All 4 elements must be accounted for (2 pairs, 0 unmatched each side).
    assert _total_elements(r) == 4
    assert len(r.pairs) == 2
    assert r.unmatched_left == []
    assert r.unmatched_right == []
    # "A"↔"X" cost = |1.0-1.1|=0.1 should be preferred over "A"↔"Y" cost=49.
    assert r.total_cost == pytest.approx(0.1 + 40.0)


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_single_level_flexible_uses_true_inner_matching() -> None:
    left = [("A", "x", 1.0), ("A", "y", 9.0), ("B", "z", 50.0)]
    right = [("X", "y", 9.0), ("X", "x", 1.0), ("Y", "z", 49.0)]
    level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_item, right_item: abs(left_item[2] - right_item[2]),
        unmatched_cost=10.0,
        mode="flexible",
    )

    result = hierarchical_match(left, right, [level])

    assert set(result.pairs) == {(0, 1), (1, 0), (2, 2)}
    assert result.unmatched_left == []
    assert result.unmatched_right == []
    assert result.total_cost == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# hierarchical_match — two levels (chain → atom analogy)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_two_levels_strict_strict() -> None:
    # Simulate chain → atom matching.
    # Each element is (chain, atom_type, value).
    left = [
        ("A", "H", 7.0),
        ("A", "C", 120.0),
        ("B", "H", 8.0),
    ]
    right = [
        ("A", "H", 7.2),
        ("A", "C", 120.5),
        ("B", "H", 8.1),
    ]
    chain_level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=_zero_cost,  # unused at intermediate strict level
        unmatched_cost=100.0,
        mode="strict",
    )
    atom_level = Level(
        key_fn=operator.itemgetter(1),
        cost_fn=lambda left_item, right_item: abs(left_item[2] - right_item[2]),
        unmatched_cost=10.0,
        mode="strict",
    )
    r = hierarchical_match(left, right, [chain_level, atom_level])
    assert len(r.pairs) == 3
    assert r.unmatched_left == []
    assert r.unmatched_right == []
    assert r.total_cost == pytest.approx(0.2 + 0.5 + 0.1)


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_two_levels_strict_unmatched_chain() -> None:
    left = [("A", "H", 7.0), ("C", "H", 9.0)]
    right = [("A", "H", 7.5), ("B", "H", 8.0)]

    chain_level = Level(key_fn=operator.itemgetter(0), cost_fn=_zero_cost, unmatched_cost=20.0)
    atom_level = Level(
        key_fn=operator.itemgetter(1),
        cost_fn=lambda left_item, right_item: abs(left_item[2] - right_item[2]),
        unmatched_cost=10.0,
    )
    r = hierarchical_match(left, right, [chain_level, atom_level])
    # ("C", ...) and ("B", ...) are unmatched chains → their H atoms are unmatched.
    assert len(r.unmatched_left) == 1  # "C"'s H
    assert len(r.unmatched_right) == 1  # "B"'s H
    assert len(r.pairs) == 1  # "A"'s H
    assert r.total_cost == pytest.approx(0.5 + 20.0 + 20.0)


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_two_levels_inner_atom_mismatch() -> None:
    # Both chains match but one chain has a missing atom on one side.
    left = [("A", "H", 7.0), ("A", "C", 120.0)]
    right = [("A", "H", 7.1)]

    chain_level = Level(key_fn=operator.itemgetter(0), cost_fn=_zero_cost, unmatched_cost=100.0)
    atom_level = Level(
        key_fn=operator.itemgetter(1),
        cost_fn=lambda left_item, right_item: abs(left_item[2] - right_item[2]),
        unmatched_cost=5.0,
    )
    r = hierarchical_match(left, right, [chain_level, atom_level])
    assert len(r.pairs) == 1  # H matched
    assert len(r.unmatched_left) == 1  # C unmatched
    assert r.unmatched_right == []
    assert r.total_cost == pytest.approx(0.1 + 5.0)


# ---------------------------------------------------------------------------
# hierarchical_match — result coverage invariant
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_covers_all_indices() -> None:
    left = [("A", i) for i in range(3)]
    right = [("A", i) for i in range(4)]
    level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=1.0,
    )
    r = hierarchical_match(left, right, [level])
    paired_l = {li for li, _ in r.pairs}
    paired_r = {ri for _, ri in r.pairs}
    all_l = paired_l | set(r.unmatched_left)
    all_r = paired_r | set(r.unmatched_right)
    assert all_l == set(range(len(left)))
    assert all_r == set(range(len(right)))


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_two_levels_covers_all_indices() -> None:
    left = [("A", "H", i) for i in range(3)] + [("B", "C", i) for i in range(2)]
    right = [("A", "H", i) for i in range(2)] + [("B", "N", i) for i in range(2)]
    chain_level = Level(key_fn=operator.itemgetter(0), cost_fn=_zero_cost, unmatched_cost=5.0)
    atom_level = Level(
        key_fn=operator.itemgetter(1),
        cost_fn=lambda left_item, right_item: abs(left_item[2] - right_item[2]),
        unmatched_cost=2.0,
    )
    r = hierarchical_match(left, right, [chain_level, atom_level])
    paired_l = {li for li, _ in r.pairs}
    paired_r = {ri for _, ri in r.pairs}
    all_l = paired_l | set(r.unmatched_left)
    all_r = paired_r | set(r.unmatched_right)
    assert all_l == set(range(len(left)))
    assert all_r == set(range(len(right)))


# ---------------------------------------------------------------------------
# hierarchical_match — flexible intermediate level
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_flexible_intermediate_cross_key_assignment() -> None:
    # Two chains with different keys on each side. Flexible mode should
    # assign left-chain "X" to whichever right chain is cheapest.
    left = [("X", 1.0), ("X", 2.0), ("Y", 10.0)]
    right = [("A", 1.1), ("A", 2.1), ("B", 10.1)]

    def group_cost(l_group: list, r_group: list) -> float:
        """Sum of nearest-neighbour absolute differences (a cheap proxy)."""
        total = 0.0
        for le in l_group:
            nearest = min(abs(le[1] - re[1]) for re in r_group)
            total += nearest
        return total

    chain_level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=group_cost,
        unmatched_cost=100.0,
        mode="flexible",
    )
    atom_level = Level(
        key_fn=lambda _: 0,  # all atoms in same sub-group
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=5.0,
    )
    r = hierarchical_match(left, right, [chain_level, atom_level])
    # All 6 elements must be accounted for.
    assert _total_elements(r) == 6
    assert r.total_cost >= 0.0


@pytest.mark.unit
@pytest.mark.small
def test_hierarchical_flexible_intermediate_reports_objective_cost() -> None:
    left = [("A", 0.0), ("B", 100.0)]
    right = [("X", 1.0), ("Y", 99.0)]
    chain_level = Level(
        key_fn=operator.itemgetter(0),
        cost_fn=lambda left_group, right_group: abs(left_group[0][1] - right_group[0][1]) + 5.0,
        unmatched_cost=50.0,
        mode="flexible",
    )
    atom_level = Level(
        key_fn=lambda _item: 0,
        cost_fn=lambda left_item, right_item: abs(left_item[1] - right_item[1]),
        unmatched_cost=10.0,
    )

    result = hierarchical_match(left, right, [chain_level, atom_level])

    assert set(result.pairs) == {(0, 0), (1, 1)}
    assert result.unmatched_left == []
    assert result.unmatched_right == []
    assert result.total_cost == pytest.approx(6.0 + 6.0)
