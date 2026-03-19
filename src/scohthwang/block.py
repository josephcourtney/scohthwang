"""Candidate-pair generators (blocking functions).

Public API
----------
- :class:`BlockingFn` — Protocol for any callable ``(left, right) -> Iterable[tuple[int, int]]``.
- :func:`all_pairs` — O(n²) cross-product of all index pairs.
- :func:`key_equality_block` — yield pairs where a key function agrees on both sides.
- :func:`predicate_block` — yield pairs satisfying an arbitrary binary predicate.
- :func:`compose_blocks` — combine multiple blocking functions via union or intersection.

Design
------
*Blocking* is a pre-filter that reduces the O(n²) candidate set before cost
evaluation.  A blocking function receives two sequences and returns an iterable
of ``(left_index, right_index)`` pairs that are *candidates* for matching.

The contract is: **every correct pair must appear in the candidate set**.
Blocking may admit false positives (extra pairs that will be rejected by the
cost function) but must not omit true positives.  Tests verify recall-1.0 on
fixture sets.

Blocking functions compose via :func:`compose_blocks`:
- ``mode="union"`` (default): a pair is a candidate if *any* blocker includes it.
  Maximises recall at the cost of more pairs to score.
- ``mode="intersection"``: a pair is a candidate only if *all* blockers include it.
  Maximises precision; only use when every blocker is recall-safe on its own.

Source
------
No direct bvp-cs analogue.  Blocking was implicit in bvp-cs through hard
constraints in ``pair_cost`` and residue grouping.  This module makes blocking
explicit and composable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class BlockingFn(Protocol):
    """Callable that yields candidate ``(left_index, right_index)`` pairs."""

    def __call__(
        self,
        left: Sequence[Any],
        right: Sequence[Any],
    ) -> Iterable[tuple[int, int]]:
        """Yield index pairs that are candidates for matching."""
        ...


# ---------------------------------------------------------------------------
# Built-in blocking functions
# ---------------------------------------------------------------------------


def all_pairs(
    left: Sequence[Any],
    right: Sequence[Any],
) -> Iterable[tuple[int, int]]:
    """Yield every ``(i, j)`` combination — the O(n²) baseline.

    This blocking function has perfect recall by definition and is the correct
    choice when no domain knowledge is available to prune candidates.

    Parameters
    ----------
    left:
        Left-side element sequence.
    right:
        Right-side element sequence.

    Yields
    ------
    tuple[int, int]
        Every ``(left_index, right_index)`` pair.
    """
    for i in range(len(left)):
        for j in range(len(right)):
            yield i, j


def key_equality_block(
    key_fn: Callable[[Any], object],
) -> BlockingFn:
    """Return a blocking function that yields pairs sharing the same key.

    Two elements are candidates when ``key_fn(left[i]) == key_fn(right[j])``.
    This is the most common blocking strategy: group by chain, residue name,
    atom type, etc.

    Parameters
    ----------
    key_fn:
        Extracts a hashable grouping key from an element.

    Returns
    -------
    BlockingFn
        A closure over ``key_fn`` that performs key-equality blocking.
    """

    def _block(
        left: Sequence[Any],
        right: Sequence[Any],
    ) -> Iterable[tuple[int, int]]:
        # Build an index from key → list of right-side positions.
        right_index: dict[object, list[int]] = {}
        for j, right_item in enumerate(right):
            k = key_fn(right_item)
            right_index.setdefault(k, []).append(j)

        for i, left_item in enumerate(left):
            for j in right_index.get(key_fn(left_item), []):
                yield i, j

    return _block


def predicate_block(
    pred_fn: Callable[[Any, Any], bool],
) -> BlockingFn:
    """Return a blocking function that yields pairs satisfying a predicate.

    Two elements are candidates when ``pred_fn(left[i], right[j])`` is ``True``.
    This is a flexible escape hatch for blocking rules that cannot be expressed
    as key equality.

    Parameters
    ----------
    pred_fn:
        Binary predicate; ``True`` means the pair is a candidate.

    Returns
    -------
    BlockingFn
        A closure over ``pred_fn`` that performs predicate-based blocking.
    """

    def _block(
        left: Sequence[Any],
        right: Sequence[Any],
    ) -> Iterable[tuple[int, int]]:
        for i, left_item in enumerate(left):
            for j, right_item in enumerate(right):
                if pred_fn(left_item, right_item):
                    yield i, j

    return _block


def compose_blocks(
    *block_fns: BlockingFn,
    mode: Literal["union", "intersection"] = "union",
) -> BlockingFn:
    """Combine multiple blocking functions into one.

    Parameters
    ----------
    *block_fns:
        One or more blocking functions to combine.
    mode:
        ``"union"`` (default): a pair is a candidate if *any* blocker yields it.
        ``"intersection"``: a pair is a candidate only if *all* blockers yield it.

    Returns
    -------
    BlockingFn
        A new blocking function that applies the composition rule.

    Raises
    ------
    ValueError
        If ``block_fns`` is empty or ``mode`` is not recognised.
    """
    if not block_fns:
        msg = "compose_blocks requires at least one blocking function"
        raise ValueError(msg)
    if mode not in {"union", "intersection"}:
        msg = f"mode must be 'union' or 'intersection', got {mode!r}"
        raise ValueError(msg)

    def _block(
        left: Sequence[Any],
        right: Sequence[Any],
    ) -> Iterable[tuple[int, int]]:
        if mode == "union":
            seen: set[tuple[int, int]] = set()
            for fn in block_fns:
                for pair in fn(left, right):
                    if pair not in seen:
                        seen.add(pair)
                        yield pair
        else:  # intersection
            # Start from the first blocker's candidate set, then filter.
            candidate_sets = [set(fn(left, right)) for fn in block_fns]
            common = candidate_sets[0]
            for s in candidate_sets[1:]:
                common &= s
            yield from sorted(common)

    return _block
