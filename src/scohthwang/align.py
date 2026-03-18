"""Sequence alignment and offset-scan inference.

Public API
----------
- :func:`needleman_wunsch_alignment` — global alignment via Needleman-Wunsch DP.
- :func:`infer_offset_from_sequences` — infer integer offset Δ from indexed sequences.
- :func:`infer_seq_offset` — higher-level wrapper accepting arbitrary element lists.

Algorithms
----------
**Needleman-Wunsch** uses a standard linear-gap-penalty DP with deterministic
tie-breaking: diagonal > up > left.  Returns aligned index pairs (either index
may be ``None`` for a gap) and the total alignment score.

**Offset-scan** scans all integer offsets Δ in the natural range
``(min_left - max_right) ... (max_left - min_right)`` (optionally bounded by
``max_span``) and picks the Δ that maximises agreement between labels at
overlapping positions.  Ambiguity is detected when the runner-up candidate is
within ``ambiguous_delta`` of the best and has sufficient support.

Source
------
Generalised from ``bvp_cs.algorithms.align`` in bvp/packages/bvp-cs.
Domain-specific ``ShiftRow`` extraction replaced with a generic ``key_fn``
parameter.  Return types changed from raw tuples to :class:`OffsetInferenceResult`.
Logging removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from scohthwang.models import OffsetInferenceResult

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Sequence

    from scohthwang.models import AlignedPair

# ---------------------------------------------------------------------------
# Module-level defaults (match bvp-cs constants; overridable per call)
# ---------------------------------------------------------------------------

#: Default ambiguity threshold: if second-best agreement is within this delta
#: of the best, the result is flagged as ambiguous.
AMBIGUOUS_OFFSET_DELTA: float = 0.05

_MIN_SECOND_BEST_COMPARABLE: int = 3
_MIN_SECOND_BEST_SUPPORT_DENOMINATOR: int = 4


# ---------------------------------------------------------------------------
# Private types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _OffsetCandidate:
    """Internal scored candidate from the offset scan."""

    offset: int
    agreement: float
    compared: int


# ---------------------------------------------------------------------------
# Private helpers — Needleman-Wunsch
# ---------------------------------------------------------------------------


def _initialize_alignment_matrices(
    n: int,
    m: int,
    gap_score: float,
) -> tuple[list[list[float]], list[list[int]]]:
    """Allocate and initialise the DP score and traceback matrices.

    ``trace[i][j]`` encodes direction: 0 = diagonal, 1 = up, 2 = left.
    Border cells are filled with cumulative gap penalties.
    """
    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    trace = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0] = i * gap_score
        trace[i][0] = 1  # up (gap in right)
    for j in range(1, m + 1):
        scores[0][j] = j * gap_score
        trace[0][j] = 2  # left (gap in left)
    return scores, trace


def _fill_alignment_matrices(
    scores: list[list[float]],
    trace: list[list[int]],
    left: list[Hashable],
    right: list[Hashable],
    match_score: float,
    mismatch_score: float,
    gap_score: float,
) -> None:
    """Fill the DP matrices using Needleman-Wunsch recurrence.

    Tie-breaking without fragile float equality: prefer diagonal, then up,
    then left.  This is deterministic and stable under equal scores.
    """
    n = len(left)
    m = len(right)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = scores[i - 1][j - 1] + (
                match_score if left[i - 1] == right[j - 1] else mismatch_score
            )
            up = scores[i - 1][j] + gap_score
            left_score = scores[i][j - 1] + gap_score
            if diag >= up and diag >= left_score:
                trace[i][j] = 0
                scores[i][j] = diag
            elif up >= left_score:
                trace[i][j] = 1
                scores[i][j] = up
            else:
                trace[i][j] = 2
                scores[i][j] = left_score


def _traceback_alignment(
    trace: list[list[int]],
    n: int,
    m: int,
) -> list[AlignedPair]:
    """Traceback from ``trace[n][m]`` to build the aligned index-pair list."""
    aligned: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        direction = trace[i][j]
        if direction == 0 and i > 0 and j > 0:
            aligned.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif direction == 1 and i > 0:
            aligned.append((i - 1, None))
            i -= 1
        else:
            aligned.append((None, j - 1))
            j -= 1
    aligned.reverse()
    return aligned


# ---------------------------------------------------------------------------
# Private helpers — offset scan
# ---------------------------------------------------------------------------


def _is_ambiguous(
    *,
    best: _OffsetCandidate | None,
    second: _OffsetCandidate | None,
    ambiguous_delta: float,
) -> bool:
    """Return True when the runner-up offset is close enough to be concerning.

    Conditions (both must hold):
    - Score gap between best and second is ≤ ``ambiguous_delta``.
    - Second candidate has enough compared pairs to be credible.
    """
    if best is None or second is None:
        return False
    if (best.agreement - second.agreement) > ambiguous_delta:
        return False
    min_relative = (
        best.compared + _MIN_SECOND_BEST_SUPPORT_DENOMINATOR - 1
    ) // _MIN_SECOND_BEST_SUPPORT_DENOMINATOR
    required = min(best.compared, max(_MIN_SECOND_BEST_COMPARABLE, min_relative))
    return second.compared >= required


def _score_one_offset(
    left_map: dict[int, Hashable | None],
    right_map: dict[int, Hashable | None],
    offset: int,
) -> _OffsetCandidate:
    """Score a single candidate offset by agreement fraction over comparable pairs.

    Pairs where either label is ``None`` are excluded from scoring.
    """
    matches = 0
    total = 0
    for seq_id, label in left_map.items():
        if label is None:
            continue
        right_label = right_map.get(seq_id - offset)
        if right_label is None:
            continue
        total += 1
        if right_label == label:
            matches += 1
    score = matches / total if total else 0.0
    return _OffsetCandidate(offset=offset, agreement=score, compared=total)


def _candidate_is_better(a: _OffsetCandidate, b: _OffsetCandidate | None) -> bool:
    """Return True when candidate ``a`` is preferred over ``b``.

    Preference order: higher agreement, then larger compared, then smaller offset.
    """
    if b is None:
        return True
    if a.agreement != b.agreement:
        return a.agreement > b.agreement
    if a.compared != b.compared:
        return a.compared > b.compared
    return a.offset < b.offset


def _score_offsets_top2(
    left_map: dict[int, Hashable | None],
    right_map: dict[int, Hashable | None],
    offset_min: int,
    offset_max: int,
) -> tuple[_OffsetCandidate | None, _OffsetCandidate | None]:
    """Return the best and second-best candidates for the given offset range."""
    best: _OffsetCandidate | None = None
    second: _OffsetCandidate | None = None

    for offset in range(offset_min, offset_max + 1):
        cand = _score_one_offset(left_map, right_map, offset)

        if _candidate_is_better(cand, best):
            if best is not None and _candidate_is_better(best, second):
                second = best
            best = cand
            continue

        if best is not None and cand.offset == best.offset:
            continue

        if _candidate_is_better(cand, second):
            second = cand

    return best, second


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def needleman_wunsch_alignment(
    left: list[Hashable],
    right: list[Hashable],
    *,
    match_score: float,
    mismatch_score: float,
    gap_score: float,
) -> tuple[list[AlignedPair], float]:
    """Return a global alignment between two sequences.

    Implements the Needleman-Wunsch algorithm with a linear gap penalty.
    Elements are compared using ``==``; any :class:`~collections.abc.Hashable`
    type is supported.

    Parameters
    ----------
    left:
        First sequence.
    right:
        Second sequence.
    match_score:
        Score added when ``left[i] == right[j]``.
    mismatch_score:
        Score added (typically negative) when ``left[i] != right[j]``.
    gap_score:
        Score added (typically negative) for each gap position.

    Returns
    -------
    tuple[list[AlignedPair], float]
        ``(pairs, total_score)`` where each ``(left_idx, right_idx)`` pair has
        either index potentially ``None`` to represent a gap.  ``total_score``
        is the sum of match/mismatch/gap scores along the aligned path.

    Notes
    -----
    If both sequences are empty, returns ``([], 0.0)``.
    If only one is empty, the result consists entirely of gap pairs.
    Tie-breaking: diagonal > up > left.
    """
    n = len(left)
    m = len(right)
    if n == 0 and m == 0:
        return [], 0.0

    scores, trace = _initialize_alignment_matrices(n, m, gap_score)
    _fill_alignment_matrices(scores, trace, left, right, match_score, mismatch_score, gap_score)
    aligned = _traceback_alignment(trace, n, m)
    return aligned, scores[n][m]


def infer_offset_from_sequences(
    left: Sequence[tuple[int, Hashable | None]],
    right: Sequence[tuple[int, Hashable | None]],
    *,
    max_span: int | None = None,
    ambiguous_delta: float = AMBIGUOUS_OFFSET_DELTA,
) -> OffsetInferenceResult:
    """Infer integer offset Δ such that ``right_index + Δ ≈ left_index``.

    Both sequences are lists of ``(index, label)`` pairs.  The offset that
    maximises label agreement at overlapping positions is chosen.

    Parameters
    ----------
    left:
        Indexed sequence: ``[(index, label), ...]``.  ``label=None`` means the
        label is unknown and the pair is excluded from scoring.
    right:
        Same structure as ``left``.
    max_span:
        If given, restricts the scanned offset range to ``[-max_span, max_span]``.
    ambiguous_delta:
        Threshold for flagging the result as ambiguous.  If the second-best
        candidate's agreement is within this delta of the best (and it has
        sufficient support), the result is marked :attr:`OffsetInferenceResult.ambiguous`.

    Returns
    -------
    OffsetInferenceResult
        ``offset=None`` when either sequence is empty or when no offset
        achieves any agreement (zero compared pairs for every offset).
        ``ambiguous=True`` when a credible runner-up exists.
    """
    if not left or not right:
        return OffsetInferenceResult(offset=None, agreement=0.0, compared=0, ambiguous=True)

    left_map: dict[int, Hashable | None] = dict(left)
    right_map: dict[int, Hashable | None] = dict(right)

    min_left, max_left = min(left_map), max(left_map)
    min_right, max_right = min(right_map), max(right_map)

    offset_min = min_left - max_right
    offset_max = max_left - min_right
    if max_span is not None:
        offset_min = max(offset_min, -max_span)
        offset_max = min(offset_max, max_span)

    best, second = _score_offsets_top2(left_map, right_map, offset_min, offset_max)
    if best is None:
        return OffsetInferenceResult(offset=None, agreement=0.0, compared=0, ambiguous=True)

    ambiguous = _is_ambiguous(best=best, second=second, ambiguous_delta=ambiguous_delta)
    return OffsetInferenceResult(
        offset=best.offset,
        agreement=best.agreement,
        compared=best.compared,
        ambiguous=ambiguous,
    )


def infer_seq_offset(
    left_elements: list[Any],
    right_elements: list[Any],
    key_fn: Callable[[Any], tuple[int, Hashable | None]],
    *,
    max_span: int | None = None,
    min_support: int = 3,
) -> OffsetInferenceResult:
    """Infer integer offset Δ from arbitrary element lists.

    A higher-level wrapper around :func:`infer_offset_from_sequences`.
    Applies ``key_fn`` to each element to extract ``(index, label)`` pairs,
    then delegates to the sequence-based inference function.

    Parameters
    ----------
    left_elements:
        Arbitrary elements to form the left sequence.
    right_elements:
        Arbitrary elements to form the right sequence.
    key_fn:
        Extracts ``(index, label)`` from an element.  ``label=None`` marks the
        position as unknown (excluded from agreement scoring).
    max_span:
        Passed through to :func:`infer_offset_from_sequences`.
    min_support:
        Minimum number of compared pairs required to trust the inferred offset.
        If ``result.compared < min_support``, the returned result has
        ``offset=None`` (other fields are preserved for inspection).

    Returns
    -------
    OffsetInferenceResult
        ``offset=None`` if sequences are empty, no overlap exists, or the best
        candidate has fewer than ``min_support`` compared pairs.
    """
    left_seq = [key_fn(e) for e in left_elements]
    right_seq = [key_fn(e) for e in right_elements]
    result = infer_offset_from_sequences(left_seq, right_seq, max_span=max_span)
    if result.compared < min_support:
        return OffsetInferenceResult(
            offset=None,
            agreement=result.agreement,
            compared=result.compared,
            ambiguous=result.ambiguous,
        )
    return result
