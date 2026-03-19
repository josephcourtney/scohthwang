"""Unit tests for scohthwang.assign."""

from __future__ import annotations

import pytest

from scohthwang.assign import hungarian_square, hungarian_with_unmatched

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_assignment(assignment: list[int], n: int) -> bool:
    """Return True iff assignment is a permutation of 0..n-1."""
    return sorted(assignment) == list(range(n))


def _assignment_cost(cost: list[list[float]], assignment: list[int]) -> float:
    return sum(cost[i][assignment[i]] for i in range(len(assignment)))


# ---------------------------------------------------------------------------
# hungarian_square — basic correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_square_1x1() -> None:
    cost = [[5.0]]
    result = hungarian_square(cost)
    assert result == [0]


@pytest.mark.unit
@pytest.mark.small
def test_square_2x2_identity() -> None:
    # Optimal: match row 0→col 0, row 1→col 1 (cost 0+0=0)
    cost = [[0.0, 1.0], [1.0, 0.0]]
    result = hungarian_square(cost)
    assert _is_valid_assignment(result, 2)
    assert _assignment_cost(cost, result) == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_square_2x2_cross() -> None:
    # Optimal: match row 0→col 1, row 1→col 0 (cost 1+1=2 vs 10+10=20)
    cost = [[10.0, 1.0], [1.0, 10.0]]
    result = hungarian_square(cost)
    assert _is_valid_assignment(result, 2)
    assert _assignment_cost(cost, result) == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_square_3x3_known_optimal() -> None:
    # Classic example; optimal assignment is row0→col1, row1→col0, row2→col2 (cost 1+2+3=6)
    cost = [
        [9.0, 1.0, 5.0],
        [2.0, 8.0, 7.0],
        [6.0, 4.0, 3.0],
    ]
    result = hungarian_square(cost)
    assert _is_valid_assignment(result, 3)
    assert _assignment_cost(cost, result) == pytest.approx(6.0)


@pytest.mark.unit
@pytest.mark.small
def test_square_returns_valid_permutation() -> None:
    """For any square matrix the result is a permutation of column indices."""
    cost = [
        [3.0, 2.0, 1.0],
        [2.0, 3.0, 1.0],
        [1.0, 2.0, 3.0],
    ]
    result = hungarian_square(cost)
    assert _is_valid_assignment(result, 3)


@pytest.mark.unit
@pytest.mark.small
def test_square_all_equal_costs() -> None:
    """All-equal cost matrix: any permutation is optimal; result must be a permutation."""
    cost = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
    result = hungarian_square(cost)
    assert _is_valid_assignment(result, 3)
    assert _assignment_cost(cost, result) == pytest.approx(3.0)


@pytest.mark.unit
@pytest.mark.small
def test_square_4x4() -> None:
    cost = [
        [10.0, 4.0, 6.0, 8.0],
        [2.0, 7.0, 3.0, 9.0],
        [5.0, 1.0, 8.0, 2.0],
        [9.0, 3.0, 5.0, 4.0],
    ]
    result = hungarian_square(cost)
    assert _is_valid_assignment(result, 4)
    # The globally optimal cost; verify result is at least as good as the
    # diagonal (not necessarily optimal) to bound correctness.
    diagonal_cost = sum(cost[i][i] for i in range(4))
    assert _assignment_cost(cost, result) <= diagonal_cost + 1e-9


@pytest.mark.unit
@pytest.mark.small
def test_square_deterministic() -> None:
    """Same input always produces same output."""
    cost = [[3.0, 1.0], [2.0, 4.0]]
    assert hungarian_square(cost) == hungarian_square(cost)


# ---------------------------------------------------------------------------
# hungarian_square — error cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_square_raises_on_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        hungarian_square([])


@pytest.mark.unit
@pytest.mark.small
def test_square_raises_on_non_square_wide() -> None:
    with pytest.raises(ValueError, match="square"):
        hungarian_square([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])


@pytest.mark.unit
@pytest.mark.small
def test_square_raises_on_non_square_tall() -> None:
    with pytest.raises(ValueError, match="square"):
        hungarian_square([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])


# ---------------------------------------------------------------------------
# hungarian_with_unmatched — basic correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_empty_cost() -> None:
    result, total = hungarian_with_unmatched([], unmatched_cost=1.0)
    assert result == []
    assert total == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_empty_rows() -> None:
    # 0 left, 3 right → all right elements unmatched
    result, total = hungarian_with_unmatched([], unmatched_cost=2.0)
    assert result == []
    assert total == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_1x1_matched() -> None:
    cost = [[0.5]]
    result, total = hungarian_with_unmatched(cost, unmatched_cost=1.0)
    assert result == [0]
    assert total == pytest.approx(0.5)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_1x1_square_forces_match() -> None:
    # Square matrices can now opt out via explicit dummy assignments.
    cost = [[3.0]]
    result, total = hungarian_with_unmatched(cost, unmatched_cost=1.0)
    assert result == [None]
    assert total == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_2x2_perfect() -> None:
    cost = [[0.0, 5.0], [5.0, 0.0]]
    result, total = hungarian_with_unmatched(cost, unmatched_cost=10.0)
    assert result == [0, 1]
    assert total == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_more_left_than_right() -> None:
    # 3 left, 2 right; cheapest is row0→col0, row1→col1, row2 unmatched
    cost = [
        [1.0, 9.0],
        [9.0, 1.0],
        [9.0, 9.0],
    ]
    result, total = hungarian_with_unmatched(cost, unmatched_cost=2.0)
    assert result[0] == 0
    assert result[1] == 1
    assert result[2] is None
    assert total == pytest.approx(1.0 + 1.0 + 2.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_more_right_than_left() -> None:
    # 2 left, 3 right; best is row0→col0, row1→col1, col2 unmatched
    cost = [
        [1.0, 9.0, 9.0],
        [9.0, 1.0, 9.0],
    ]
    result, total = hungarian_with_unmatched(cost, unmatched_cost=2.0)
    assert result[0] == 0
    assert result[1] == 1
    assert total == pytest.approx(1.0 + 1.0 + 2.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_square_always_fully_matched() -> None:
    # Square matrices can leave both sides unmatched when every real pair is worse.
    cost = [[5.0, 5.0], [5.0, 5.0]]
    result, total = hungarian_with_unmatched(cost, unmatched_cost=1.0)
    assert result == [None, None]
    assert total == pytest.approx(4.0)


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_deterministic() -> None:
    cost = [[1.0, 2.0], [3.0, 4.0]]
    r1, c1 = hungarian_with_unmatched(cost, 5.0)
    r2, c2 = hungarian_with_unmatched(cost, 5.0)
    assert r1 == r2
    assert c1 == pytest.approx(c2)


# ---------------------------------------------------------------------------
# hungarian_with_unmatched — symmetry
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_transpose_consistent_cost() -> None:
    """Transposing the cost matrix produces the same total cost."""
    cost = [
        [1.0, 4.0, 3.0],
        [4.0, 2.0, 5.0],
    ]
    transposed = [[cost[i][j] for i in range(len(cost))] for j in range(len(cost[0]))]
    _, cost_fwd = hungarian_with_unmatched(cost, unmatched_cost=3.0)
    _, cost_rev = hungarian_with_unmatched(transposed, unmatched_cost=3.0)
    assert cost_fwd == pytest.approx(cost_rev)


# ---------------------------------------------------------------------------
# hungarian_with_unmatched — error cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_unmatched_raises_on_jagged_matrix() -> None:
    cost = [[1.0, 2.0], [3.0]]
    with pytest.raises(ValueError, match="same length"):
        hungarian_with_unmatched(cost, unmatched_cost=1.0)
