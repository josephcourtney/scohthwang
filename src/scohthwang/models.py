"""Core data types shared across all scohthwang modules.

This module defines the primitive types used throughout the library.
Nothing here imports from other scohthwang modules.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Sentinel value
# ---------------------------------------------------------------------------

#: Cost sentinel indicating that two elements must not be matched.
#: Returned by cost functions to signal hard incompatibility.
#: Used as the padding value when extending a rectangular cost matrix
#: to square for the Hungarian algorithm.
LARGE_COST: float = 1e9

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

#: A rectangular cost matrix represented as a list of rows.
#: ``matrix[i][j]`` is the cost of pairing left element ``i`` with right
#: element ``j``.  Use :data:`LARGE_COST` to mark incompatible pairs.
CostMatrix = list[list[float]]

#: A single aligned position from a Needleman-Wunsch alignment.
#: Either index may be ``None`` to represent a gap on that side.
AlignedPair = tuple[int | None, int | None]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatchResult:
    """Output of a matching or assignment operation.

    Attributes
    ----------
    pairs:
        Matched ``(left_index, right_index)`` index pairs.
    unmatched_left:
        Indices of left elements that were not paired.
    unmatched_right:
        Indices of right elements that were not paired.
    total_cost:
        Sum of matched-pair costs plus any unmatched penalties.
    """

    pairs: list[tuple[int, int]]
    unmatched_left: list[int]
    unmatched_right: list[int]
    total_cost: float


@dataclass(frozen=True)
class OffsetInferenceResult:
    """Output of an offset-scan inference operation.

    Attributes
    ----------
    offset:
        Inferred integer offset ``Δ`` such that ``right_index + Δ ≈ left_index``
        for matching elements.  ``None`` if no offset could be determined
        (insufficient support, ambiguous result, or empty input).
    agreement:
        Fraction of compared pairs that agree with the inferred offset
        (in the range ``[0.0, 1.0]``).
    compared:
        Number of element pairs examined during the scan.
    ambiguous:
        ``True`` if a second offset was within ``ambiguous_delta`` of the best,
        making the result unreliable.
    """

    offset: int | None
    agreement: float
    compared: int
    ambiguous: bool
