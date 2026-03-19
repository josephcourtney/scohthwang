"""Unit tests for scohthwang.score."""

from __future__ import annotations

import operator

import pytest

from scohthwang.models import MatchResult
from scohthwang.score import (
    CategoricalFieldCost,
    ConstraintFn,
    PairCostConfig,
    PairCostFn,
    WeightedFieldCost,
    make_nested_cost_fn,
    make_pair_cost_fn,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _val(x: float) -> float:
    """Identity field extractor — element is the value itself."""
    return float(x)


def _always_true(left: object, right: object) -> bool:
    return True


def _always_false(left: object, right: object) -> bool:
    return False


def _same_type(left: object, right: object) -> bool:
    return type(left) is type(right)


# ---------------------------------------------------------------------------
# make_pair_cost_fn — constraint failure
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_constraint_failure_returns_large_cost() -> None:
    config = PairCostConfig(
        constraints=[_always_false],
        field_costs=[WeightedFieldCost(field_fn=_val, weight=1.0)],
        large_cost=1e9,
    )
    fn = make_pair_cost_fn(config)
    assert fn(1.0, 2.0) == pytest.approx(1e9)


@pytest.mark.unit
@pytest.mark.small
def test_second_constraint_failure_returns_large_cost() -> None:
    config = PairCostConfig(
        constraints=[_always_true, _always_false],
        field_costs=[],
        large_cost=999.0,
    )
    fn = make_pair_cost_fn(config)
    assert fn(0, 0) == pytest.approx(999.0)


@pytest.mark.unit
@pytest.mark.small
def test_no_constraints_no_fields_returns_zero() -> None:
    config = PairCostConfig()
    fn = make_pair_cost_fn(config)
    assert fn("a", "b") == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_passing_constraint_does_not_short_circuit() -> None:
    config = PairCostConfig(
        constraints=[_always_true],
        field_costs=[WeightedFieldCost(field_fn=_val, weight=2.0)],
    )
    fn = make_pair_cost_fn(config)
    # 2.0 * |3.0 - 1.0| = 4.0
    assert fn(3.0, 1.0) == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# make_pair_cost_fn — soft penalties
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_single_field_cost_correct() -> None:
    config = PairCostConfig(
        field_costs=[WeightedFieldCost(field_fn=_val, weight=3.0)],
    )
    fn = make_pair_cost_fn(config)
    # 3.0 * |5.0 - 2.0| = 9.0
    assert fn(5.0, 2.0) == pytest.approx(9.0)


@pytest.mark.unit
@pytest.mark.small
def test_multiple_field_costs_accumulate() -> None:
    config = PairCostConfig(
        field_costs=[
            WeightedFieldCost(field_fn=operator.itemgetter(0), weight=1.0),
            WeightedFieldCost(field_fn=operator.itemgetter(1), weight=2.0),
        ],
    )
    fn = make_pair_cost_fn(config)
    left = (10.0, 5.0)
    right = (7.0, 3.0)
    # 1.0 * |10-7| + 2.0 * |5-3| = 3.0 + 4.0 = 7.0
    assert fn(left, right) == pytest.approx(7.0)


@pytest.mark.unit
@pytest.mark.small
def test_identical_elements_cost_zero() -> None:
    config = PairCostConfig(
        field_costs=[WeightedFieldCost(field_fn=_val, weight=5.0)],
    )
    fn = make_pair_cost_fn(config)
    assert fn(4.0, 4.0) == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_zero_weight_contributes_nothing() -> None:
    config = PairCostConfig(
        field_costs=[WeightedFieldCost(field_fn=_val, weight=0.0)],
    )
    fn = make_pair_cost_fn(config)
    assert fn(100.0, 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# make_pair_cost_fn — max_diff exceeded
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_max_diff_exceeded_returns_large_cost() -> None:
    config = PairCostConfig(
        field_costs=[WeightedFieldCost(field_fn=_val, weight=1.0, max_diff=1.0)],
        large_cost=1e9,
    )
    fn = make_pair_cost_fn(config)
    assert fn(0.0, 2.0) == pytest.approx(1e9)


@pytest.mark.unit
@pytest.mark.small
def test_max_diff_exactly_at_limit_allowed() -> None:
    config = PairCostConfig(
        field_costs=[WeightedFieldCost(field_fn=_val, weight=1.0, max_diff=2.0)],
        large_cost=1e9,
    )
    fn = make_pair_cost_fn(config)
    # diff == max_diff → allowed; cost = 1.0 * 2.0 = 2.0
    assert fn(0.0, 2.0) == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_max_diff_first_field_exceeded_short_circuits() -> None:
    call_count = 0

    def counting_field(x: float) -> float:
        nonlocal call_count
        call_count += 1
        return x

    config = PairCostConfig(
        field_costs=[
            WeightedFieldCost(field_fn=_val, weight=1.0, max_diff=0.5),
            WeightedFieldCost(field_fn=counting_field, weight=1.0),
        ],
        large_cost=1e9,
    )
    fn = make_pair_cost_fn(config)
    result = fn(0.0, 1.0)
    assert result == pytest.approx(1e9)
    # The second field should not have been evaluated after max_diff triggered
    assert call_count == 0


@pytest.mark.unit
@pytest.mark.small
def test_none_max_diff_never_triggers_large_cost() -> None:
    config = PairCostConfig(
        field_costs=[WeightedFieldCost(field_fn=_val, weight=1.0, max_diff=None)],
        large_cost=1e9,
    )
    fn = make_pair_cost_fn(config)
    # Very large difference — no cap applied
    assert fn(0.0, 1_000_000.0) == pytest.approx(1_000_000.0)


@pytest.mark.unit
@pytest.mark.small
def test_categorical_cost_mismatch_penalty() -> None:
    config = PairCostConfig(
        categorical_costs=[
            CategoricalFieldCost(
                field_fn=operator.itemgetter("atom"),
                mismatch_cost=4.0,
            )
        ]
    )
    fn = make_pair_cost_fn(config)
    assert fn({"atom": "HA"}, {"atom": "HB"}) == pytest.approx(4.0)


@pytest.mark.unit
@pytest.mark.small
def test_categorical_cost_synonym_group_treated_as_match() -> None:
    config = PairCostConfig(
        categorical_costs=[
            CategoricalFieldCost(
                field_fn=operator.itemgetter("atom"),
                mismatch_cost=10.0,
                synonym_groups=[frozenset({"HB2", "HB3"})],
            )
        ]
    )
    fn = make_pair_cost_fn(config)
    assert fn({"atom": "HB2"}, {"atom": "HB3"}) == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_categorical_cost_normalizer_and_missing_penalty() -> None:
    config = PairCostConfig(
        categorical_costs=[
            CategoricalFieldCost(
                field_fn=operator.itemgetter("comp"),
                mismatch_cost=5.0,
                missing_cost=1.5,
                normalize_fn=lambda value: str(value).strip().upper(),
            )
        ]
    )
    fn = make_pair_cost_fn(config)
    assert fn({"comp": " ala "}, {"comp": "ALA"}) == pytest.approx(0.0)
    assert fn({"comp": None}, {"comp": "ALA"}) == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# make_pair_cost_fn — return type and protocol compliance
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_make_pair_cost_fn_returns_callable() -> None:
    fn = make_pair_cost_fn(PairCostConfig())
    assert callable(fn)


@pytest.mark.unit
@pytest.mark.small
def test_returned_fn_satisfies_pair_cost_protocol() -> None:
    fn = make_pair_cost_fn(PairCostConfig())
    # Runtime duck-type check: must accept two args and return float
    result = fn(1, 2)
    assert isinstance(result, float)


@pytest.mark.unit
@pytest.mark.small
def test_protocols_are_callable() -> None:
    """PairCostFn and ConstraintFn are Protocols and callable."""
    assert callable(PairCostFn)
    assert callable(ConstraintFn)


# ---------------------------------------------------------------------------
# make_nested_cost_fn
# ---------------------------------------------------------------------------


def _make_trivial_match_result(
    left: list[object],
    right: list[object],
    unmatched_cost: float,
) -> MatchResult:
    """Match equal-length lists index-by-index at zero cost."""
    n = min(len(left), len(right))
    pairs = [(i, i) for i in range(n)]
    unmatched_left = list(range(n, len(left)))
    unmatched_right = list(range(n, len(right)))
    cost = (len(unmatched_left) + len(unmatched_right)) * unmatched_cost
    return MatchResult(
        pairs=pairs,
        unmatched_left=unmatched_left,
        unmatched_right=unmatched_right,
        total_cost=cost,
    )


@pytest.mark.unit
@pytest.mark.small
def test_nested_cost_returns_inner_total_cost() -> None:
    fn = make_nested_cost_fn(
        inner_match_fn=_make_trivial_match_result,
        left_items_fn=lambda x: x,
        right_items_fn=lambda x: x,
        unmatched_cost=5.0,
    )
    # Both sides have 3 elements; no unmatched → total_cost = 0.0
    assert fn([1, 2, 3], [4, 5, 6]) == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_nested_cost_propagates_unmatched_cost() -> None:
    fn = make_nested_cost_fn(
        inner_match_fn=_make_trivial_match_result,
        left_items_fn=lambda x: x,
        right_items_fn=lambda x: x,
        unmatched_cost=7.0,
    )
    # Left has 4 elements, right has 2 → 2 unmatched left at cost 7.0 each
    assert fn([1, 2, 3, 4], [5, 6]) == pytest.approx(14.0)


@pytest.mark.unit
@pytest.mark.small
def test_nested_cost_uses_item_extractors() -> None:
    fn = make_nested_cost_fn(
        inner_match_fn=_make_trivial_match_result,
        left_items_fn=operator.itemgetter("items"),
        right_items_fn=operator.itemgetter("items"),
        unmatched_cost=3.0,
    )
    left = {"items": [1, 2]}
    right = {"items": [3]}
    # 1 match + 1 unmatched left at cost 3.0
    assert fn(left, right) == pytest.approx(3.0)


@pytest.mark.unit
@pytest.mark.small
def test_nested_cost_empty_subelements() -> None:
    fn = make_nested_cost_fn(
        inner_match_fn=_make_trivial_match_result,
        left_items_fn=lambda x: [],
        right_items_fn=lambda x: [],
        unmatched_cost=99.0,
    )
    assert fn("a", "b") == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_nested_cost_fn_returns_callable() -> None:
    fn = make_nested_cost_fn(
        inner_match_fn=_make_trivial_match_result,
        left_items_fn=lambda x: x,
        right_items_fn=lambda x: x,
        unmatched_cost=1.0,
    )
    assert callable(fn)
