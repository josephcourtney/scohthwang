"""Optimal assignment via the Hungarian (Kuhn-Munkres) algorithm.

Public API
----------
- :func:`hungarian_square` — solve a square minimum-cost assignment problem.
- :func:`hungarian_with_unmatched` — solve a rectangular assignment allowing
  any element to go unmatched at a configurable penalty.

Algorithm
---------
The implementation uses the shortest-augmenting-path (Jonker-Volgenant style)
variant of the Kuhn-Munkres algorithm with Johnson potentials.  Time complexity
is O(n^3) for an n x n matrix.

Tie-breaking
------------
When two augmenting paths have equal reduced cost, the algorithm prefers the
column with the smaller index (i.e., left-to-right scan order is preserved).
This produces deterministic results for any given input.

Source
------
Generalised from ``bvp_cs.algorithms.hungarian`` in bvp/packages/bvp-cs.
Domain-specific assumptions removed; precondition checks added.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scohthwang.models import CostMatrix

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _init_arrays(size: int) -> tuple[list[float], list[float], list[int], list[int]]:
    """Allocate potential and pointer arrays for a size x size problem."""
    return [0.0] * (size + 1), [0.0] * (size + 1), [0] * (size + 1), [0] * (size + 1)


def _search_iteration(
    cost: CostMatrix,
    *,
    u: list[float],
    v: list[float],
    p: list[int],
    way: list[int],
    j0: int,
    used: list[bool],
    minv: list[float],
) -> int:
    """One iteration of the shortest-augmenting-path search (Kuhn-Munkres potentials).

    Scans all unused columns, updates reduced-cost minima, adjusts potentials
    by delta (the minimum reduced cost among unused columns), and returns the
    column that achieves the minimum.
    """
    n = len(cost)
    used[j0] = True
    i0 = p[j0]

    delta = float("inf")
    j1 = 0
    for j in range(1, n + 1):
        if used[j]:
            continue
        cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
        if cur < minv[j]:
            minv[j] = cur
            way[j] = j0
        if minv[j] < delta:
            delta = minv[j]
            j1 = j

    for j in range(n + 1):
        if used[j]:
            u[p[j]] += delta
            v[j] -= delta
        else:
            minv[j] -= delta

    return j1


def _shortest_augmenting_path(
    cost: CostMatrix,
    *,
    start_i: int,
    u: list[float],
    v: list[float],
    p: list[int],
    way: list[int],
) -> int:
    """Run shortest-augmenting-path search starting from row ``start_i``.

    Returns the index of the free column found at the end of the path.
    """
    n = len(cost)
    p[0] = start_i
    j0 = 0
    minv = [float("inf")] * (n + 1)
    used = [False] * (n + 1)

    while True:
        j0 = _search_iteration(cost, u=u, v=v, p=p, way=way, j0=j0, used=used, minv=minv)
        if p[j0] == 0:
            return j0


def _apply_augmenting_path(*, free_col: int, p: list[int], way: list[int]) -> None:
    """Flip assignment pointers along the augmenting path ending at ``free_col``."""
    j0 = free_col
    while True:
        j1 = way[j0]
        p[j0] = p[j1]
        j0 = j1
        if j0 == 0:
            return


def _build_assignment(p: list[int], n: int) -> list[int]:
    """Convert the pointer array ``p`` into a flat assignment list.

    Returns a list of length ``n`` where ``result[i]`` is the column assigned
    to row ``i`` (0-indexed).
    """
    assignment = [0] * n
    for j in range(1, n + 1):
        assignment[p[j] - 1] = j - 1
    return assignment


def _pad_to_square(
    cost: CostMatrix,
    unmatched_cost: float,
) -> tuple[CostMatrix, int, int, int]:
    """Pad a rectangular cost matrix to square by filling dummy rows/columns.

    Real entries (``i < m``, ``j < n``) are copied verbatim.
    Dummy entries (one real index, one dummy index) are set to ``unmatched_cost``.
    Dummy-to-dummy entries are set to ``0.0`` (cost-free pairing of dummies).

    Returns ``(square_matrix, n_left, n_right, size)``.
    """
    m = len(cost)
    n = len(cost[0]) if cost else 0
    size = max(m, n)
    square: CostMatrix = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            if i < m and j < n:
                square[i][j] = cost[i][j]
            elif i < m or j < n:
                square[i][j] = unmatched_cost
            else:
                square[i][j] = 0.0
    return square, m, n, size


def _extract_row_matching(
    assignment: list[int],
    *,
    m: int,
    n: int,
) -> tuple[list[int | None], set[int]]:
    """Strip dummy assignments from a square assignment result.

    Returns ``(match_for_left, matched_right)`` where ``match_for_left[i]``
    is the right index paired with left element ``i``, or ``None`` if
    element ``i`` was matched to a dummy column.
    """
    match_for_left: list[int | None] = [None] * m
    matched_right: set[int] = set()
    for i in range(m):
        j = assignment[i]
        if j < n:
            match_for_left[i] = j
            matched_right.add(j)
    return match_for_left, matched_right


def _total_matching_cost(
    match_for_left: list[int | None],
    matched_right: set[int],
    *,
    cost: CostMatrix,
    unmatched_cost: float,
) -> float:
    """Sum matched-pair costs plus ``unmatched_cost`` for each unmatched element."""
    m = len(match_for_left)
    n = len(cost[0]) if cost else 0
    total = 0.0
    for i in range(m):
        j = match_for_left[i]
        total += unmatched_cost if j is None else cost[i][j]
    for j in range(n):
        if j not in matched_right:
            total += unmatched_cost
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def hungarian_square(cost: CostMatrix) -> list[int]:
    """Solve a square minimum-cost assignment problem.

    Parameters
    ----------
    cost:
        Square cost matrix.  ``cost[i][j]`` is the cost of assigning row ``i``
        to column ``j``.  All rows must have the same length as there are rows.

    Returns
    -------
    list[int]
        Assignment list of length ``n`` where ``result[i]`` is the column
        assigned to row ``i`` (0-indexed).

    Raises
    ------
    ValueError
        If ``cost`` is empty, non-square, or has rows of unequal length.
    """
    if not cost:
        msg = "cost matrix must not be empty; use hungarian_with_unmatched for variable-size inputs"
        raise ValueError(msg)
    n = len(cost)
    if any(len(row) != n for row in cost):
        msg = f"cost matrix must be square (got {n} rows with lengths {[len(r) for r in cost]})"
        raise ValueError(msg)

    u, v, p, way = _init_arrays(n)
    for i in range(1, n + 1):
        free_col = _shortest_augmenting_path(cost, start_i=i, u=u, v=v, p=p, way=way)
        _apply_augmenting_path(free_col=free_col, p=p, way=way)

    return _build_assignment(p, n)


def hungarian_with_unmatched(
    cost: CostMatrix,
    unmatched_cost: float,
) -> tuple[list[int | None], float]:
    """Solve a rectangular assignment allowing unmatched elements.

    Either side may have more elements than the other; unmatched elements
    incur ``unmatched_cost`` each.  Internally pads ``cost`` to square, runs
    :func:`hungarian_square`, then strips dummy assignments.

    Parameters
    ----------
    cost:
        Rectangular cost matrix.  ``cost[i][j]`` is the cost of pairing left
        element ``i`` with right element ``j``.  May be empty (0 rows or 0
        columns).
    unmatched_cost:
        Penalty applied to each element left without a partner.  This value is
        used as the cost of dummy (padding) assignments introduced to equalise
        the matrix dimensions.  It does **not** act as an opt-out threshold:
        when ``len(cost) == len(cost[0])``, no dummies are added and all
        elements are matched regardless of pair costs.

    Returns
    -------
    tuple[list[int | None], float]
        ``(match_for_left, total_cost)`` where ``match_for_left[i]`` is the
        right-side index paired with left element ``i``, or ``None`` if it was
        left unmatched.  ``total_cost`` is the sum of all matched-pair costs
        plus ``unmatched_cost`` for every unmatched element on either side.

    Raises
    ------
    ValueError
        If ``cost`` has rows of unequal length.
    """
    if cost and len({len(row) for row in cost}) > 1:
        lengths = [len(row) for row in cost]
        msg = f"cost matrix rows must all have the same length (got {lengths})"
        raise ValueError(msg)

    square, m, n, size = _pad_to_square(cost, unmatched_cost)
    if size == 0:
        return [], 0.0

    assignment = hungarian_square(square)
    match_for_left, matched_right = _extract_row_matching(assignment, m=m, n=n)
    total_cost = _total_matching_cost(
        match_for_left,
        matched_right,
        cost=cost,
        unmatched_cost=unmatched_cost,
    )
    return match_for_left, total_cost
