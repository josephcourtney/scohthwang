"""Contract tests for the published scohthwang API."""

from __future__ import annotations

import pytest

import scohthwang
from scohthwang.block import predicate_block
from scohthwang.match import match_within_group


def _contract_cost(left_item: str, right_item: str) -> float:
    return 0.0 if left_item == right_item else 99.0


@pytest.mark.contract
@pytest.mark.unit
@pytest.mark.small
def test_square_assignment_can_leave_both_sides_unmatched() -> None:
    match_for_left, total_cost = scohthwang.hungarian_with_unmatched(
        [[10.0, 10.0], [10.0, 10.0]],
        unmatched_cost=1.5,
    )

    assert match_for_left == [None, None]
    assert total_cost == pytest.approx(6.0)


@pytest.mark.contract
@pytest.mark.unit
@pytest.mark.small
def test_blocked_square_group_returns_unmatched_instead_of_large_cost_pairs() -> None:
    result = match_within_group(
        left=["A", "B"],
        right=["A", "B"],
        cost_fn=_contract_cost,
        unmatched_cost=1.0,
        block_fn=predicate_block(lambda _left_item, _right_item: False),
    )

    assert result.pairs == []
    assert result.unmatched_left == [0, 1]
    assert result.unmatched_right == [0, 1]
    assert result.total_cost == pytest.approx(4.0)


@pytest.mark.contract
@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_returns_none_when_all_candidates_have_zero_support() -> None:
    result = scohthwang.infer_offset_from_sequences(
        [(10, "A"), (11, "B")],
        [(1, "A"), (2, "B")],
        max_span=3,
    )

    assert result.offset is None
    assert result.compared == 0
    assert result.agreement == pytest.approx(0.0)


@pytest.mark.contract
@pytest.mark.unit
@pytest.mark.small
def test_star_import_matches_module_all() -> None:
    namespace: dict[str, object] = {}
    exec("from scohthwang import *", {}, namespace)  # ruff: ignore[exec-builtin] - this test explicitly verifies the package's star-import public contract.
    assert set(namespace) == set(scohthwang.__all__)
