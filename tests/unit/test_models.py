"""Unit tests for scohthwang.models."""

from __future__ import annotations

import dataclasses

import pytest

from scohthwang.models import (
    LARGE_COST,
    AlignedPair,
    CostMatrix,
    MatchResult,
    MaterializedMatchResult,
    OffsetInferenceResult,
    OffsetScanCandidate,
    OffsetScanReport,
)

# ---------------------------------------------------------------------------
# LARGE_COST
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_large_cost_value() -> None:
    assert pytest.approx(1e9) == LARGE_COST


@pytest.mark.unit
@pytest.mark.small
def test_large_cost_is_float() -> None:
    assert isinstance(LARGE_COST, float)


# ---------------------------------------------------------------------------
# Type aliases (smoke checks — the aliases are just types, not classes)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_cost_matrix_alias_is_list_of_list() -> None:
    matrix: CostMatrix = [[1.0, 2.0], [3.0, 4.0]]
    assert matrix[0][1] == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_aligned_pair_alias_accepts_none() -> None:
    gap_left: AlignedPair = (None, 3)
    gap_right: AlignedPair = (2, None)
    both_present: AlignedPair = (0, 1)
    assert gap_left == (None, 3)
    assert gap_right == (2, None)
    assert both_present == (0, 1)


# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_match_result_construction() -> None:
    result = MatchResult(
        pairs=[(0, 1), (1, 0)],
        unmatched_left=[2],
        unmatched_right=[2],
        total_cost=3.5,
    )
    assert result.pairs == [(0, 1), (1, 0)]
    assert result.unmatched_left == [2]
    assert result.unmatched_right == [2]
    assert result.total_cost == pytest.approx(3.5)


@pytest.mark.unit
@pytest.mark.small
def test_match_result_is_frozen() -> None:
    result = MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.total_cost = 1.0  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.small
def test_match_result_is_dataclass() -> None:
    assert dataclasses.is_dataclass(MatchResult)


@pytest.mark.unit
@pytest.mark.small
def test_match_result_empty() -> None:
    result = MatchResult(pairs=[], unmatched_left=[], unmatched_right=[], total_cost=0.0)
    assert result.pairs == []
    assert result.unmatched_left == []
    assert result.unmatched_right == []
    assert result.total_cost == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_match_result_equality() -> None:
    a = MatchResult(pairs=[(0, 0)], unmatched_left=[], unmatched_right=[1], total_cost=1.0)
    b = MatchResult(pairs=[(0, 0)], unmatched_left=[], unmatched_right=[1], total_cost=1.0)
    assert a == b


@pytest.mark.unit
@pytest.mark.small
def test_match_result_inequality() -> None:
    a = MatchResult(pairs=[(0, 0)], unmatched_left=[], unmatched_right=[], total_cost=1.0)
    b = MatchResult(pairs=[(0, 0)], unmatched_left=[], unmatched_right=[], total_cost=2.0)
    assert a != b


# ---------------------------------------------------------------------------
# OffsetInferenceResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_result_construction() -> None:
    result = OffsetInferenceResult(offset=2, agreement=0.8, compared=10, ambiguous=False)
    assert result.offset == 2
    assert result.agreement == pytest.approx(0.8)
    assert result.compared == 10
    assert result.ambiguous is False


@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_result_none_offset() -> None:
    result = OffsetInferenceResult(offset=None, agreement=0.0, compared=0, ambiguous=False)
    assert result.offset is None


@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_result_is_frozen() -> None:
    result = OffsetInferenceResult(offset=0, agreement=1.0, compared=5, ambiguous=False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.offset = 1  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_result_is_dataclass() -> None:
    assert dataclasses.is_dataclass(OffsetInferenceResult)


@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_result_ambiguous_flag() -> None:
    result = OffsetInferenceResult(offset=None, agreement=0.5, compared=6, ambiguous=True)
    assert result.ambiguous is True


@pytest.mark.unit
@pytest.mark.small
def test_offset_inference_result_equality() -> None:
    a = OffsetInferenceResult(offset=1, agreement=0.9, compared=10, ambiguous=False)
    b = OffsetInferenceResult(offset=1, agreement=0.9, compared=10, ambiguous=False)
    assert a == b


@pytest.mark.unit
@pytest.mark.small
def test_offset_scan_candidate_construction() -> None:
    candidate = OffsetScanCandidate(offset=2, agreement=0.75, compared=8)
    assert candidate.offset == 2
    assert candidate.agreement == pytest.approx(0.75)
    assert candidate.compared == 8


@pytest.mark.unit
@pytest.mark.small
def test_offset_scan_report_construction() -> None:
    candidate = OffsetScanCandidate(offset=0, agreement=1.0, compared=3)
    report = OffsetScanReport(
        result=OffsetInferenceResult(offset=0, agreement=1.0, compared=3, ambiguous=False),
        candidates=[candidate],
        best=candidate,
        second_best=None,
        offset_min=0,
        offset_max=0,
    )
    assert report.best == candidate
    assert report.offset_min == 0
    assert report.offset_max == 0


@pytest.mark.unit
@pytest.mark.small
def test_materialized_match_result_construction() -> None:
    result = MaterializedMatchResult(
        matched=["matched"],
        unmatched_left=["left"],
        unmatched_right=["right"],
        total_cost=2.5,
    )
    assert result.matched == ["matched"]
    assert result.unmatched_left == ["left"]
    assert result.unmatched_right == ["right"]
    assert result.total_cost == pytest.approx(2.5)
