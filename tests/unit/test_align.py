"""Unit tests for scohthwang.align."""

from __future__ import annotations

import operator

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.database import InMemoryExampleDatabase

from scohthwang.align import infer_offset_from_sequences, infer_seq_offset, needleman_wunsch_alignment
from scohthwang.models import OffsetInferenceResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _left_indices(pairs: list) -> list[int]:
    return [p[0] for p in pairs if p[0] is not None]


def _right_indices(pairs: list) -> list[int]:
    return [p[1] for p in pairs if p[1] is not None]


# ---------------------------------------------------------------------------
# needleman_wunsch_alignment — basic correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_nw_both_empty() -> None:
    pairs, score = needleman_wunsch_alignment([], [], match_score=2.0, mismatch_score=-1.0, gap_score=-2.0)
    assert pairs == []
    assert score == pytest.approx(0.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_left_empty() -> None:
    pairs, score = needleman_wunsch_alignment(
        [], ["A", "B"], match_score=2.0, mismatch_score=-1.0, gap_score=-2.0
    )
    assert pairs == [(None, 0), (None, 1)]
    assert score == pytest.approx(-4.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_right_empty() -> None:
    pairs, score = needleman_wunsch_alignment(
        ["A", "B"], [], match_score=2.0, mismatch_score=-1.0, gap_score=-2.0
    )
    assert pairs == [(0, None), (1, None)]
    assert score == pytest.approx(-4.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_identical_sequences() -> None:
    seq = ["A", "B", "C"]
    pairs, score = needleman_wunsch_alignment(seq, seq, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0)
    assert pairs == [(0, 0), (1, 1), (2, 2)]
    assert score == pytest.approx(6.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_complete_mismatch() -> None:
    # No matches; optimal is to align diagonally at mismatch cost
    pairs, score = needleman_wunsch_alignment(
        ["A", "B"], ["C", "D"], match_score=2.0, mismatch_score=-1.0, gap_score=-2.0
    )
    # Diagonal alignment: -1 + -1 = -2 vs gap-heavy alternatives (-6)
    assert pairs == [(0, 0), (1, 1)]
    assert score == pytest.approx(-2.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_single_deletion() -> None:
    # left has extra element "B"; right skips it
    left = ["A", "B", "C"]
    right = ["A", "C"]
    pairs, score = needleman_wunsch_alignment(
        left, right, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0
    )
    # Optimal: match A-A, gap B, match C-C  -> score = 2 + -2 + 2 = 2
    assert (0, 0) in pairs
    assert (2, 1) in pairs
    assert (1, None) in pairs
    assert score == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_single_insertion() -> None:
    # right has extra element "B"
    left = ["A", "C"]
    right = ["A", "B", "C"]
    pairs, score = needleman_wunsch_alignment(
        left, right, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0
    )
    # Optimal: match A-A, gap B (on left side), match C-C  -> 2 + -2 + 2 = 2
    assert (0, 0) in pairs
    assert (1, 2) in pairs
    assert (None, 1) in pairs
    assert score == pytest.approx(2.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_single_element_match() -> None:
    pairs, score = needleman_wunsch_alignment(
        ["X"], ["X"], match_score=3.0, mismatch_score=-1.0, gap_score=-1.0
    )
    assert pairs == [(0, 0)]
    assert score == pytest.approx(3.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_single_element_mismatch() -> None:
    pairs, score = needleman_wunsch_alignment(
        ["X"], ["Y"], match_score=3.0, mismatch_score=-1.0, gap_score=-1.5
    )
    # Diagonal costs -1, two gaps would cost -3; diagonal wins
    assert pairs == [(0, 0)]
    assert score == pytest.approx(-1.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_integer_elements() -> None:
    """Accepts any Hashable -- not just strings."""
    pairs, score = needleman_wunsch_alignment(
        [1, 2, 3], [1, 2, 3], match_score=1.0, mismatch_score=-1.0, gap_score=-1.0
    )
    assert pairs == [(0, 0), (1, 1), (2, 2)]
    assert score == pytest.approx(3.0)


@pytest.mark.unit
@pytest.mark.small
def test_nw_deterministic() -> None:
    left = ["A", "B", "C"]
    right = ["A", "C"]
    r1, s1 = needleman_wunsch_alignment(left, right, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0)
    r2, s2 = needleman_wunsch_alignment(left, right, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0)
    assert r1 == r2
    assert s1 == pytest.approx(s2)


# ---------------------------------------------------------------------------
# needleman_wunsch_alignment — property-based
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.medium
@pytest.mark.property_based
@settings(max_examples=200, database=InMemoryExampleDatabase())
@given(
    left=st.lists(st.integers(min_value=0, max_value=4), max_size=10),
    right=st.lists(st.integers(min_value=0, max_value=4), max_size=10),
)
def test_nw_covers_all_indices(left: list[int], right: list[int]) -> None:
    """Every index in both sequences appears exactly once in the alignment."""
    pairs, _ = needleman_wunsch_alignment(left, right, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0)
    assert sorted(_left_indices(pairs)) == list(range(len(left)))
    assert sorted(_right_indices(pairs)) == list(range(len(right)))


# ---------------------------------------------------------------------------
# infer_offset_from_sequences — basic correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_offset_empty_left() -> None:
    result = infer_offset_from_sequences([], [(1, "A"), (2, "B")])
    assert isinstance(result, OffsetInferenceResult)
    assert result.offset is None
    assert result.ambiguous is True
    assert result.compared == 0


@pytest.mark.unit
@pytest.mark.small
def test_offset_empty_right() -> None:
    result = infer_offset_from_sequences([(1, "A")], [])
    assert result.offset is None
    assert result.compared == 0


@pytest.mark.unit
@pytest.mark.small
def test_offset_zero_perfect_agreement() -> None:
    seq = [(1, "A"), (2, "B"), (3, "C")]
    result = infer_offset_from_sequences(seq, seq)
    assert result.offset == 0
    assert result.agreement == pytest.approx(1.0)
    assert result.compared == 3
    assert result.ambiguous is False


@pytest.mark.unit
@pytest.mark.small
def test_offset_nonzero_exact() -> None:
    # left has seq_ids 3, 4; right has seq_ids 1, 2; offset = 2
    left = [(3, "A"), (4, "B")]
    right = [(1, "A"), (2, "B")]
    result = infer_offset_from_sequences(left, right)
    assert result.offset == 2
    assert result.agreement == pytest.approx(1.0)
    assert result.compared == 2
    assert result.ambiguous is False


@pytest.mark.unit
@pytest.mark.small
def test_offset_negative_offset() -> None:
    # left has seq_ids 1, 2; right has seq_ids 3, 4; offset = -2
    left = [(1, "A"), (2, "B")]
    right = [(3, "A"), (4, "B")]
    result = infer_offset_from_sequences(left, right)
    assert result.offset == -2
    assert result.agreement == pytest.approx(1.0)


@pytest.mark.unit
@pytest.mark.small
def test_offset_partial_agreement() -> None:
    # offset=0 gives agreement 2/3; no other offset does better
    left = [(1, "A"), (2, "B"), (3, "C")]
    right = [(1, "A"), (2, "X"), (3, "C")]
    result = infer_offset_from_sequences(left, right)
    assert result.offset == 0
    assert result.agreement == pytest.approx(2 / 3)
    assert result.compared == 3


@pytest.mark.unit
@pytest.mark.small
def test_offset_none_labels_excluded() -> None:
    # None labels should not count toward compared or matches
    left = [(1, "A"), (2, None), (3, "C")]
    right = [(1, "A"), (2, "B"), (3, "C")]
    result = infer_offset_from_sequences(left, right)
    assert result.offset == 0
    assert result.compared == 2  # position 2 skipped (left label is None)
    assert result.agreement == pytest.approx(1.0)


@pytest.mark.unit
@pytest.mark.small
def test_offset_max_span_restricts_range() -> None:
    # True offset is 10, but max_span=3 prevents finding it
    left = [(11, "A"), (12, "B")]
    right = [(1, "A"), (2, "B")]
    result = infer_offset_from_sequences(left, right, max_span=3)
    # No overlapping positions exist within max_span.
    assert result.offset is None
    assert result.compared == 0


@pytest.mark.unit
@pytest.mark.small
def test_offset_returns_offset_inference_result() -> None:
    result = infer_offset_from_sequences([(1, "A")], [(1, "A")])
    assert isinstance(result, OffsetInferenceResult)


# ---------------------------------------------------------------------------
# infer_offset_from_sequences — ambiguity
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_offset_ambiguous_when_two_offsets_tie() -> None:
    # Construct left/right so that offset=0 and offset=1 both achieve 1.0 agreement.
    # At offset=0: left[1]="A" matches right[1]="A" (1/1).
    # At offset=1: left[2]="A" matches right[1]="A" (1/1).
    left = [(1, "A"), (2, "A")]
    right = [(1, "A")]
    result = infer_offset_from_sequences(left, right, ambiguous_delta=0.05)
    # Both offsets compare 1 pair each with agreement 1.0 → ambiguous
    assert result.ambiguous is True


@pytest.mark.unit
@pytest.mark.small
def test_offset_not_ambiguous_when_gap_is_large() -> None:
    # offset=0 gets agreement=1.0; offset=1 gets agreement=0.0
    left = [(1, "A"), (2, "B"), (3, "C")]
    right = [(1, "A"), (2, "B"), (3, "C")]
    result = infer_offset_from_sequences(left, right, ambiguous_delta=0.05)
    assert result.ambiguous is False
    assert result.offset == 0


# ---------------------------------------------------------------------------
# infer_seq_offset — basic correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.small
def test_seq_offset_delegates_correctly() -> None:
    elements = [{"seq": 1, "label": "A"}, {"seq": 2, "label": "B"}, {"seq": 3, "label": "C"}]
    key_fn = operator.itemgetter("seq", "label")
    left = elements
    right = [{"seq": idx - 2, "label": lbl} for idx, lbl in [(1, "A"), (2, "B"), (3, "C")]]
    result = infer_seq_offset(left, right, key_fn)
    assert result.offset == 2
    assert result.agreement == pytest.approx(1.0)


@pytest.mark.unit
@pytest.mark.small
def test_seq_offset_min_support_triggers_none() -> None:
    # Only 1 compared pair; min_support=3 should force offset=None
    left = [{"seq": 1, "label": "A"}]
    right = [{"seq": 1, "label": "A"}]
    key_fn = operator.itemgetter("seq", "label")
    result = infer_seq_offset(left, right, key_fn, min_support=3)
    assert result.offset is None
    assert result.compared == 1  # observed, but below threshold
    assert result.agreement == pytest.approx(1.0)


@pytest.mark.unit
@pytest.mark.small
def test_seq_offset_min_support_met() -> None:
    elements = [{"seq": i, "label": chr(65 + i)} for i in range(5)]
    key_fn = operator.itemgetter("seq", "label")
    result = infer_seq_offset(elements, elements, key_fn, min_support=3)
    assert result.offset == 0
    assert result.compared == 5
    assert result.offset is not None


@pytest.mark.unit
@pytest.mark.small
def test_seq_offset_empty_elements() -> None:
    key_fn = operator.itemgetter("seq", "label")
    result = infer_seq_offset([], [], key_fn)
    assert result.offset is None


@pytest.mark.unit
@pytest.mark.small
def test_seq_offset_returns_offset_inference_result() -> None:
    def key_fn(e: int) -> tuple[int, int]:
        return e, e

    result = infer_seq_offset([1, 2, 3], [1, 2, 3], key_fn)
    assert isinstance(result, OffsetInferenceResult)
