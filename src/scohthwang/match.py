"""Hierarchical matching pipeline.

Public API
----------
- :class:`Level` — configuration bundle for one level of a hierarchical match.
- :func:`match_within_group` — flat optimal assignment within a single candidate set.
- :func:`group_and_match` — group both sides by a key function then match within groups.
- :func:`hierarchical_match` — multi-level recursive grouping and matching.

Design
------
Matching is built in three layers, each composable:

1. **Flat matching** (:func:`match_within_group`): build a cost matrix over all
   candidate pairs, call :func:`~scohthwang.assign.hungarian_with_unmatched`, and
   wrap the result as a :class:`~scohthwang.models.MatchResult`.  A
   :class:`~scohthwang.block.BlockingFn` may be supplied to skip expensive cost
   evaluations for pairs that are definitely incompatible; blocked pairs receive
   :data:`~scohthwang.models.LARGE_COST` and will be avoided by the algorithm.

2. **Group matching** (:func:`group_and_match`): partition both sides by a key
   function, then call :func:`match_within_group` for each key that appears on
   both sides.  Keys present on only one side produce fully-unmatched results.

3. **Hierarchical matching** (:func:`hierarchical_match`): a list of
   :class:`Level` objects drives recursive grouping.  Each level groups both
   sides by ``key_fn``, pairs the groups (strict or flexible), and then
   recurses with the remaining levels.  The leaf level calls
   :func:`match_within_group` directly.

   - *Strict mode* (default): groups are paired by key equality.  Groups with
     no counterpart on the other side have all their elements marked unmatched.
   - *Flexible mode*: groups are treated as elements at the group level.
     The level's ``cost_fn`` is called with the full group element lists as
     arguments (typically built with
     :func:`~scohthwang.score.make_nested_cost_fn`).  The Hungarian algorithm
     then assigns groups optimally before within-group recursion proceeds.

``cost_fn`` conventions by mode and position
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Last :class:`Level` (leaf) — any mode: ``cost_fn`` is an element-to-element
  function passed directly to :func:`match_within_group`.
- Intermediate :class:`Level` + strict: ``cost_fn`` is forwarded to inner
  levels; it is *not used* at the current level.
- Intermediate :class:`Level` + flexible: ``cost_fn`` receives the raw element
  lists of each group as ``left`` / ``right`` arguments.  Use
  :func:`~scohthwang.score.make_nested_cost_fn` to build such a function from
  an inner matching function.

Source
------
Generalised from ``bvp_cs.algorithms.matching.match_atoms_in_residue``,
``bvp_cs.algorithms.matching.optimal_shift_matching_all_residues``, and the
group-by-residue logic in ``bvp/packages/bvp-cs``.  The hard-coded
chain→residue→atom hierarchy is replaced with a generic :class:`Level` list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from scohthwang.assign import hungarian_with_unmatched
from scohthwang.models import LARGE_COST, MatchResult

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Sequence

    from scohthwang.block import BlockingFn
    from scohthwang.models import CostMatrix
    from scohthwang.score import PairCostFn


# ---------------------------------------------------------------------------
# Level configuration
# ---------------------------------------------------------------------------


@dataclass
class Level:
    """Configuration for one level of a hierarchical match.

    Parameters
    ----------
    key_fn:
        Extracts a grouping key from an element.  Elements that share a key
        are placed in the same group.
    cost_fn:
        Cost function for pairs within this level.  At the **leaf** level
        (last in the ``levels`` list), this is an element-to-element function.
        At **intermediate + flexible** levels, it is a group-to-group function
        that receives the full element lists as arguments.
    unmatched_cost:
        Penalty applied to each unmatched element (or group, in flexible mode
        at intermediate levels).
    block_fn:
        Optional blocking function.  At the leaf level, it filters element
        pairs; at intermediate flexible levels, it filters group pairs.
        Ignored in strict mode at intermediate levels.
    mode:
        ``"strict"`` (default): pair groups by key equality.
        ``"flexible"``: score all group pairs with ``cost_fn`` and assign
        optimally with the Hungarian algorithm.
    """

    key_fn: Callable[[Any], Hashable]
    cost_fn: PairCostFn
    unmatched_cost: float
    block_fn: BlockingFn | None = field(default=None)
    mode: Literal["strict", "flexible"] = "strict"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _group_with_indices(
    elements: Sequence[Any],
    key_fn: Callable[[Any], Hashable],
) -> dict[Any, tuple[list[int], list[Any]]]:
    """Group elements by key, preserving original indices.

    Returns a dict mapping each key to ``(orig_indices, elems)``.
    """
    groups: dict[Any, tuple[list[int], list[Any]]] = {}
    for i, elem in enumerate(elements):
        k = key_fn(elem)
        if k not in groups:
            groups[k] = ([], [])
        groups[k][0].append(i)
        groups[k][1].append(elem)
    return groups


def _unmatched_result(
    left_indices: list[int],
    right_indices: list[int],
    unmatched_cost: float,
) -> MatchResult:
    """Return a MatchResult where all supplied elements are unmatched."""
    total = unmatched_cost * (len(left_indices) + len(right_indices))
    return MatchResult(
        pairs=[],
        unmatched_left=list(left_indices),
        unmatched_right=list(right_indices),
        total_cost=total,
    )


def _merge_results(results: list[MatchResult]) -> MatchResult:
    """Concatenate a list of MatchResult objects into one flat result."""
    pairs: list[tuple[int, int]] = []
    unmatched_left: list[int] = []
    unmatched_right: list[int] = []
    total_cost = 0.0
    for r in results:
        pairs.extend(r.pairs)
        unmatched_left.extend(r.unmatched_left)
        unmatched_right.extend(r.unmatched_right)
        total_cost += r.total_cost
    return MatchResult(
        pairs=pairs,
        unmatched_left=unmatched_left,
        unmatched_right=unmatched_right,
        total_cost=total_cost,
    )


def _remap_result(
    inner: MatchResult,
    l_indices: list[int],
    r_indices: list[int],
) -> MatchResult:
    """Map group-relative indices in ``inner`` back to original indices."""
    return MatchResult(
        pairs=[(l_indices[li], r_indices[ri]) for li, ri in inner.pairs],
        unmatched_left=[l_indices[li] for li in inner.unmatched_left],
        unmatched_right=[r_indices[ri] for ri in inner.unmatched_right],
        total_cost=inner.total_cost,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_within_group(
    left: Sequence[Any],
    right: Sequence[Any],
    cost_fn: PairCostFn,
    unmatched_cost: float,
    *,
    block_fn: BlockingFn | None = None,
) -> MatchResult:
    """Optimally assign elements of ``right`` to elements of ``left``.

    Builds a cost matrix over candidate pairs, calls
    :func:`~scohthwang.assign.hungarian_with_unmatched`, and wraps the
    result as a :class:`~scohthwang.models.MatchResult`.

    When ``block_fn`` is provided, only candidate pairs yielded by the blocker
    have their cost evaluated; all other pairs are pre-filled with
    :data:`~scohthwang.models.LARGE_COST` so the algorithm avoids them.

    Parameters
    ----------
    left:
        Left-side elements.
    right:
        Right-side elements.
    cost_fn:
        Element-to-element cost function; lower means better match.
    unmatched_cost:
        Penalty per unmatched element on either side.
    block_fn:
        Optional candidate-pair filter.

    Returns
    -------
    MatchResult
        Matched pairs (using indices into ``left`` and ``right``), lists of
        unmatched indices, and the total cost.
    """
    m = len(left)
    n = len(right)

    if m == 0 and n == 0:
        return MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)
    if m == 0:
        return MatchResult(
            pairs=[],
            unmatched_left=[],
            unmatched_right=list(range(n)),
            total_cost=unmatched_cost * n,
        )
    if n == 0:
        return MatchResult(
            pairs=[],
            unmatched_left=list(range(m)),
            unmatched_right=[],
            total_cost=unmatched_cost * m,
        )

    if block_fn is not None:
        cost_matrix: CostMatrix = [[LARGE_COST] * n for _ in range(m)]
        for i, j in block_fn(left, right):
            cost_matrix[i][j] = cost_fn(left[i], right[j])
    else:
        cost_matrix = [[cost_fn(left[i], right[j]) for j in range(n)] for i in range(m)]

    match_for_left, total_cost = hungarian_with_unmatched(cost_matrix, unmatched_cost)

    pairs: list[tuple[int, int]] = []
    unmatched_left: list[int] = []
    matched_right: set[int] = set()

    for i, j in enumerate(match_for_left):
        if j is None:
            unmatched_left.append(i)
        else:
            pairs.append((i, j))
            matched_right.add(j)

    unmatched_right = [j for j in range(n) if j not in matched_right]

    return MatchResult(
        pairs=pairs,
        unmatched_left=unmatched_left,
        unmatched_right=unmatched_right,
        total_cost=total_cost,
    )


def group_and_match(
    left: Sequence[Any],
    right: Sequence[Any],
    key_fn: Callable[[Any], Hashable],
    cost_fn: PairCostFn,
    unmatched_cost: float,
    *,
    block_fn: BlockingFn | None = None,
) -> dict[Any, MatchResult]:
    """Group both sides by ``key_fn`` and match within each shared key.

    Elements whose key has no counterpart on the other side are placed in a
    :class:`~scohthwang.models.MatchResult` where all are unmatched.

    The indices inside each returned :class:`~scohthwang.models.MatchResult`
    are *group-relative* (i.e. ``0 … len(group) - 1``), not original-list
    indices.

    Parameters
    ----------
    left:
        Left-side elements.
    right:
        Right-side elements.
    key_fn:
        Extracts a grouping key from an element.
    cost_fn:
        Element-to-element cost function.
    unmatched_cost:
        Penalty per unmatched element.
    block_fn:
        Optional blocking function applied within each group pair.

    Returns
    -------
    dict[key, MatchResult]
        One entry per key that appears on at least one side.
    """
    left_groups = _group_with_indices(left, key_fn)
    right_groups = _group_with_indices(right, key_fn)

    results: dict[Any, MatchResult] = {}
    all_keys = set(left_groups) | set(right_groups)

    for key in all_keys:
        l_indices, l_elems = left_groups.get(key, ([], []))
        r_indices, r_elems = right_groups.get(key, ([], []))
        results[key] = match_within_group(
            l_elems, r_elems, cost_fn, unmatched_cost, block_fn=block_fn
        )

    return results


def hierarchical_match(
    left: Sequence[Any],
    right: Sequence[Any],
    levels: Sequence[Level],
) -> MatchResult:
    """Match ``left`` and ``right`` through a recursive grouping hierarchy.

    Each :class:`Level` groups both sides by ``key_fn``, assigns groups
    (strict or flexible), and recurses.  The leaf level calls
    :func:`match_within_group` directly.

    Parameters
    ----------
    left:
        Left-side elements.
    right:
        Right-side elements.
    levels:
        Ordered sequence of :class:`Level` objects defining the hierarchy.
        Must be non-empty.  The first element applies outermost grouping; the
        last provides the element-level ``cost_fn``.

    Returns
    -------
    MatchResult
        Matched pairs (original indices), unmatched element lists, and total
        cost.

    Raises
    ------
    ValueError
        If ``levels`` is empty.
    """
    if not levels:
        msg = "hierarchical_match requires at least one Level"
        raise ValueError(msg)

    level = levels[0]
    remaining = levels[1:]

    if not remaining:
        # Leaf: group by key_fn, then match within each group using cost_fn.
        return _hierarchical_leaf(list(left), list(right), level)

    # Intermediate: group, assign groups, recurse with remaining levels.
    left_groups = _group_with_indices(left, level.key_fn)
    right_groups = _group_with_indices(right, level.key_fn)

    if level.mode == "strict":
        return _strict_intermediate(left_groups, right_groups, remaining, level.unmatched_cost)
    else:
        return _flexible_intermediate(left_groups, right_groups, level, remaining)


# ---------------------------------------------------------------------------
# Private implementation helpers
# ---------------------------------------------------------------------------


def _hierarchical_leaf(
    left: list[Any],
    right: list[Any],
    level: Level,
) -> MatchResult:
    """Apply the leaf level: group by key, match within groups using cost_fn."""
    left_groups = _group_with_indices(left, level.key_fn)
    right_groups = _group_with_indices(right, level.key_fn)

    if level.mode == "strict":
        return _strict_leaf(left_groups, right_groups, level)
    else:
        return _flexible_leaf(left_groups, right_groups, level)


def _strict_leaf(
    left_groups: dict[Any, tuple[list[int], list[Any]]],
    right_groups: dict[Any, tuple[list[int], list[Any]]],
    level: Level,
) -> MatchResult:
    """Strict leaf: pair groups by key, match elements within each pair."""
    parts: list[MatchResult] = []
    all_keys = set(left_groups) | set(right_groups)

    for key in all_keys:
        l_indices, l_elems = left_groups.get(key, ([], []))
        r_indices, r_elems = right_groups.get(key, ([], []))

        if not l_indices:
            parts.append(_unmatched_result([], r_indices, level.unmatched_cost))
            continue
        if not r_indices:
            parts.append(_unmatched_result(l_indices, [], level.unmatched_cost))
            continue

        inner = match_within_group(
            l_elems, r_elems, level.cost_fn, level.unmatched_cost, block_fn=level.block_fn
        )
        parts.append(_remap_result(inner, l_indices, r_indices))

    return _merge_results(parts)


def _flexible_leaf(
    left_groups: dict[Any, tuple[list[int], list[Any]]],
    right_groups: dict[Any, tuple[list[int], list[Any]]],
    level: Level,
) -> MatchResult:
    """Flexible leaf: assign groups via cost_fn (group-to-group), pair elements greedily.

    At the leaf level, ``cost_fn`` is a group-level function (takes element lists).
    After optimal group assignment via the Hungarian algorithm, elements within each
    matched group pair are paired positionally (index 0 ↔ index 0, etc.).  Excess
    elements in either group are marked unmatched at ``unmatched_cost`` each.

    The returned ``total_cost`` is the sum of group-assignment costs for matched
    group pairs plus ``unmatched_cost`` for every unmatched element.
    """
    left_keys = list(left_groups)
    right_keys = list(right_groups)
    m_g = len(left_keys)
    n_g = len(right_keys)

    if m_g == 0 and n_g == 0:
        return MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)

    all_l_indices = [idx for k in left_keys for idx in left_groups[k][0]]
    all_r_indices = [idx for k in right_keys for idx in right_groups[k][0]]

    if m_g == 0:
        return _unmatched_result([], all_r_indices, level.unmatched_cost)
    if n_g == 0:
        return _unmatched_result(all_l_indices, [], level.unmatched_cost)

    left_group_elems = [left_groups[k][1] for k in left_keys]
    right_group_elems = [right_groups[k][1] for k in right_keys]

    # Build group-to-group cost matrix using the group-level cost_fn.
    if level.block_fn is not None:
        group_cost: CostMatrix = [[LARGE_COST] * n_g for _ in range(m_g)]
        for gi, gj in level.block_fn(left_group_elems, right_group_elems):
            group_cost[gi][gj] = level.cost_fn(left_group_elems[gi], right_group_elems[gj])
    else:
        group_cost = [
            [level.cost_fn(left_group_elems[gi], right_group_elems[gj]) for gj in range(n_g)]
            for gi in range(m_g)
        ]

    match_for_left_group, _ = hungarian_with_unmatched(group_cost, level.unmatched_cost)

    parts: list[MatchResult] = []
    matched_right_groups: set[int] = set()

    for gi, gj in enumerate(match_for_left_group):
        lk = left_keys[gi]
        l_indices, _ = left_groups[lk]

        if gj is None:
            parts.append(_unmatched_result(l_indices, [], level.unmatched_cost))
            continue

        matched_right_groups.add(gj)
        rk = right_keys[gj]
        r_indices, _ = right_groups[rk]

        # Pair elements positionally within the matched group pair.
        min_len = min(len(l_indices), len(r_indices))
        elem_pairs = [(l_indices[i], r_indices[i]) for i in range(min_len)]
        excess_l = l_indices[min_len:]
        excess_r = r_indices[min_len:]
        gc = group_cost[gi][gj]
        elem_cost = gc + level.unmatched_cost * (len(excess_l) + len(excess_r))
        parts.append(MatchResult(
            pairs=elem_pairs,
            unmatched_left=excess_l,
            unmatched_right=excess_r,
            total_cost=elem_cost,
        ))

    for gj, rk in enumerate(right_keys):
        if gj in matched_right_groups:
            continue
        r_indices, _ = right_groups[rk]
        parts.append(_unmatched_result([], r_indices, level.unmatched_cost))

    return _merge_results(parts)


def _strict_intermediate(
    left_groups: dict[Any, tuple[list[int], list[Any]]],
    right_groups: dict[Any, tuple[list[int], list[Any]]],
    remaining: Sequence[Level],
    unmatched_cost: float,
) -> MatchResult:
    """Strict intermediate: pair groups by key, recurse for each matched pair."""
    parts: list[MatchResult] = []
    all_keys = set(left_groups) | set(right_groups)

    for key in all_keys:
        l_indices, l_elems = left_groups.get(key, ([], []))
        r_indices, r_elems = right_groups.get(key, ([], []))

        if not l_indices:
            parts.append(_unmatched_result([], r_indices, unmatched_cost))
            continue
        if not r_indices:
            parts.append(_unmatched_result(l_indices, [], unmatched_cost))
            continue

        inner = hierarchical_match(l_elems, r_elems, remaining)
        parts.append(_remap_result(inner, l_indices, r_indices))

    return _merge_results(parts)


def _flexible_intermediate(
    left_groups: dict[Any, tuple[list[int], list[Any]]],
    right_groups: dict[Any, tuple[list[int], list[Any]]],
    level: Level,
    remaining: Sequence[Level],
) -> MatchResult:
    """Flexible intermediate: score group pairs with cost_fn, assign, recurse."""
    left_keys = list(left_groups)
    right_keys = list(right_groups)
    m_g = len(left_keys)
    n_g = len(right_keys)

    if m_g == 0 and n_g == 0:
        return MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)

    all_l_indices = [idx for k in left_keys for idx in left_groups[k][0]]
    all_r_indices = [idx for k in right_keys for idx in right_groups[k][0]]

    if m_g == 0:
        return _unmatched_result([], all_r_indices, level.unmatched_cost)
    if n_g == 0:
        return _unmatched_result(all_l_indices, [], level.unmatched_cost)

    left_group_elems = [left_groups[k][1] for k in left_keys]
    right_group_elems = [right_groups[k][1] for k in right_keys]

    # Build group-to-group cost matrix using level.cost_fn.
    # For flexible intermediate levels, cost_fn is a group-level function.
    if level.block_fn is not None:
        group_cost: CostMatrix = [[LARGE_COST] * n_g for _ in range(m_g)]
        for gi, gj in level.block_fn(left_group_elems, right_group_elems):
            group_cost[gi][gj] = level.cost_fn(left_group_elems[gi], right_group_elems[gj])
    else:
        group_cost = [
            [level.cost_fn(left_group_elems[gi], right_group_elems[gj]) for gj in range(n_g)]
            for gi in range(m_g)
        ]

    match_for_left_group, _ = hungarian_with_unmatched(group_cost, level.unmatched_cost)

    parts: list[MatchResult] = []
    matched_right_groups: set[int] = set()

    for gi, gj in enumerate(match_for_left_group):
        lk = left_keys[gi]
        l_indices, l_elems = left_groups[lk]

        if gj is None:
            parts.append(_unmatched_result(l_indices, [], level.unmatched_cost))
            continue

        matched_right_groups.add(gj)
        rk = right_keys[gj]
        r_indices, r_elems = right_groups[rk]

        inner = hierarchical_match(l_elems, r_elems, remaining)
        parts.append(_remap_result(inner, l_indices, r_indices))

    for gj, rk in enumerate(right_keys):
        if gj in matched_right_groups:
            continue
        r_indices, _ = right_groups[rk]
        parts.append(_unmatched_result([], r_indices, level.unmatched_cost))

    return _merge_results(parts)
