"""Pair-cost scoring infrastructure.

Public API
----------
- :class:`PairCostFn` — Protocol for any callable ``(left, right) -> float``.
- :class:`ConstraintFn` — Protocol for any callable ``(left, right) -> bool``.
- :class:`WeightedFieldCost` — single numeric-field penalty term.
- :class:`CategoricalFieldCost` — categorical or synonym-aware penalty term.
- :class:`PairCostConfig` — full configuration for :func:`make_pair_cost_fn`.
- :func:`make_pair_cost_fn` — build a :class:`PairCostFn` from a config.
- :func:`make_nested_cost_fn` — build a :class:`PairCostFn` whose cost is the
  ``total_cost`` of an inner correspondence algorithm applied to sub-elements.

Design
------
A *pair cost* is a non-negative float assigned to a candidate (left, right)
pair.  It expresses how expensive it is to match those two elements.  Lower
cost means better match.

``make_pair_cost_fn`` turns a declarative :class:`PairCostConfig` into a
concrete function:

1. Any :class:`ConstraintFn` that returns ``False`` causes the pair to receive
   ``config.large_cost`` immediately (hard incompatibility).
2. Each :class:`WeightedFieldCost` contributes ``weight * |f(left) - f(right)|``
   to the total.  If the absolute difference exceeds ``max_diff`` the pair
   receives ``large_cost`` instead.
3. Each :class:`CategoricalFieldCost` contributes a configurable match,
   mismatch, or missing-value penalty, optionally using synonym-aware
   equivalence logic.
4. The sum of all soft penalties is returned when no hard stop is triggered.

``make_nested_cost_fn`` computes the cost of a pair by running an inner
matching algorithm on the sub-elements extracted from each side.  This enables
the hierarchical composability that is the core design goal of scohthwang:
the cost of matching two containers is the optimal total cost of matching their
contents.

Source
------
Generalised from ``bvp_cs.algorithms.matching.pair_cost`` and
``bvp_cs.settings.models.MatchingConfig`` in bvp/packages/bvp-cs.
Domain-specific fields (nucleus weights, atom synonyms, seq-id mismatch)
replaced with generic weighted-field and constraint abstractions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from scohthwang.models import MatchResult


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class PairCostFn(Protocol):
    """Callable that returns the cost of pairing two elements."""

    def __call__(self, left: Any, right: Any) -> float:  # noqa: ANN401 - protocol must remain generic across caller-defined element types.
        """Return non-negative cost; higher means less compatible."""
        ...


class ConstraintFn(Protocol):
    """Callable that returns ``True`` when a pair is *allowed*."""

    def __call__(self, left: Any, right: Any) -> bool:  # noqa: ANN401 - protocol must remain generic across caller-defined element types.
        """Return ``False`` to mark the pair as hard-incompatible."""
        ...


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedFieldCost:
    """A single numeric-field soft penalty term.

    Parameters
    ----------
    field_fn:
        Extracts a numeric value from an element.
    weight:
        Multiplier applied to ``|field_fn(left) - field_fn(right)|``.
    max_diff:
        If set, any pair whose absolute field difference exceeds this value
        receives ``large_cost`` instead of the soft penalty.
    """

    field_fn: Callable[[Any], float]
    weight: float
    max_diff: float | None = None


@dataclass(frozen=True)
class CategoricalFieldCost:
    """A categorical penalty term with optional synonym-aware equivalence.

    Parameters
    ----------
    field_fn:
        Extracts the categorical value from an element.
    mismatch_cost:
        Penalty applied when the extracted values are both present but not
        equivalent.
    match_cost:
        Penalty applied when the extracted values are equivalent. Defaults to
        ``0.0``.
    missing_cost:
        Penalty applied when either extracted value is ``None``. Defaults to
        ``0.0``.
    normalize_fn:
        Optional normalization applied before equivalence checks.
    equivalent_fn:
        Optional custom equivalence hook. When omitted, exact equality and
        ``synonym_groups`` are used.
    synonym_groups:
        Optional collection of category groups that should be treated as
        equivalent, for example ``[{"HB2", "HB3"}]``.
    """

    field_fn: Callable[[Any], object | None]
    mismatch_cost: float
    match_cost: float = 0.0
    missing_cost: float = 0.0
    normalize_fn: Callable[[object], object] | None = None
    equivalent_fn: Callable[[object, object], bool] | None = None
    synonym_groups: list[frozenset[object]] = field(default_factory=list)


@dataclass(frozen=True)
class PairCostConfig:
    """Full configuration for :func:`make_pair_cost_fn`.

    Parameters
    ----------
    constraints:
        Hard-compatibility predicates.  Any ``False`` result → ``large_cost``.
    field_costs:
        Soft penalty terms summed to form the total cost.
    categorical_costs:
        Categorical penalty terms summed after numeric field costs.
    unmatched_cost:
        Cost used as the dummy-row penalty when this config is used inside a
        matching algorithm (stored here for co-location with the cost function;
        not consumed by :func:`make_pair_cost_fn` itself).
    large_cost:
        Sentinel returned when a hard stop is triggered.  Should be larger
        than any realistic soft cost.  Defaults to ``1e9``.
    """

    constraints: list[ConstraintFn] = field(default_factory=list)
    field_costs: list[WeightedFieldCost] = field(default_factory=list)
    categorical_costs: list[CategoricalFieldCost] = field(default_factory=list)
    unmatched_cost: float = 0.0
    large_cost: float = 1e9


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def _categorical_values_equivalent(
    left_value: object,
    right_value: object,
    categorical_cost: CategoricalFieldCost,
) -> bool:
    """Return True when two categorical values should be treated as equivalent."""
    if categorical_cost.equivalent_fn is not None:
        return categorical_cost.equivalent_fn(left_value, right_value)
    if left_value == right_value:
        return True
    return any(
        left_value in synonym_group and right_value in synonym_group
        for synonym_group in categorical_cost.synonym_groups
    )


def make_pair_cost_fn(config: PairCostConfig) -> PairCostFn:
    """Build a pair-cost function from a declarative config.

    The returned function evaluates constraints first (returning
    ``config.large_cost`` on the first failure), then sums weighted field
    penalties (also returning ``config.large_cost`` if any ``max_diff`` is
    exceeded).

    Parameters
    ----------
    config:
        Configuration object specifying constraints and field costs.

    Returns
    -------
    PairCostFn
        A closure over ``config`` that computes the pair cost.
    """

    def pair_cost(left: Any, right: Any) -> float:  # noqa: ANN401 - closure implements PairCostFn for arbitrary caller element shapes.
        for constraint in config.constraints:
            if not constraint(left, right):
                return config.large_cost

        total = 0.0
        for wfc in config.field_costs:
            diff = abs(wfc.field_fn(left) - wfc.field_fn(right))
            if wfc.max_diff is not None and diff > wfc.max_diff:
                return config.large_cost
            total += wfc.weight * diff

        for categorical_cost in config.categorical_costs:
            left_value = categorical_cost.field_fn(left)
            right_value = categorical_cost.field_fn(right)
            if left_value is None or right_value is None:
                total += categorical_cost.missing_cost
                continue
            if categorical_cost.normalize_fn is not None:
                left_value = categorical_cost.normalize_fn(left_value)
                right_value = categorical_cost.normalize_fn(right_value)
            if _categorical_values_equivalent(left_value, right_value, categorical_cost):
                total += categorical_cost.match_cost
            else:
                total += categorical_cost.mismatch_cost

        return total

    return pair_cost


def make_nested_cost_fn(
    inner_match_fn: Callable[[list[Any], list[Any], float], MatchResult],
    left_items_fn: Callable[[Any], list[Any]],
    right_items_fn: Callable[[Any], list[Any]],
    unmatched_cost: float,
) -> PairCostFn:
    """Build a pair-cost function whose value is an inner match's total cost.

    The cost of pairing two container elements is computed by running
    ``inner_match_fn`` on the sub-elements extracted from each side.  This
    implements hierarchical composability: the cost of matching two groups is
    the optimal total cost of matching their members.

    Parameters
    ----------
    inner_match_fn:
        A callable ``(left_items, right_items, unmatched_cost) -> MatchResult``.
        Must accept ``unmatched_cost`` as its third positional argument so that
        the penalty propagates consistently through the hierarchy.
    left_items_fn:
        Extracts the sub-element list from a left-side element.
    right_items_fn:
        Extracts the sub-element list from a right-side element.
    unmatched_cost:
        Passed to ``inner_match_fn`` as the penalty for unmatched sub-elements.

    Returns
    -------
    PairCostFn
        A closure that returns ``inner_match_fn(...).total_cost``.
    """

    def nested_cost(left: Any, right: Any) -> float:  # noqa: ANN401 - nested matcher accepts arbitrary caller element/container types.
        result = inner_match_fn(left_items_fn(left), right_items_fn(right), unmatched_cost)
        return result.total_cost

    return nested_cost
