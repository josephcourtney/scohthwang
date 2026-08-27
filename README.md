# scohthwang

`scohthwang` is a Python library of composable algorithms for finding correspondences between elements of two sets, sequences, or containers.

It provides the building blocks — sequence alignment, optimal assignment, scoring, blocking, and canonicalization — needed to construct custom matching pipelines. Algorithms are designed to compose: the score for matching two container elements can itself be computed by running an inner matching algorithm on their contents, enabling hierarchical, multi-level correspondence finding.

## Name

**scohthwang** *n.*
From Old English scōhþwang meaning “shoe-thong” or “shoelace”, which matches up and binds together the two sides.

## What It Does

`scohthwang` provides:

- **Sequence alignment** — global (Needleman-Wunsch) alignment and integer-offset inference between indexed sequences
- **Optimal assignment** — Hungarian algorithm for minimum-cost bipartite matching, with support for leaving elements unmatched
- **Scoring infrastructure** — configurable, weighted cost functions with hard constraints and soft penalties
- **Blocking** — candidate-pair generation strategies to reduce the O(n²) comparison space
- **Matching** — composable pipelines for pairing elements at one or more levels of hierarchy
- **Canonicalization** — normalization utilities for bringing heterogeneous records into a stable comparable form

## Design Principle: Hierarchical Composability

The key property of `scohthwang` is that its algorithms compose across levels of structure. A "score" between two elements can be computed by running an inner correspondence algorithm on their sub-elements. For example:

```
compare(document_A, document_B)
  → score each section pair by running align(paragraphs_A, paragraphs_B)
      → score each paragraph pair by running match(sentences_A, sentences_B)
```

This pattern appears in many domains: comparing biological sequences at the residue level using atom-level matching as the residue similarity score; comparing structured records whose fields are themselves sequences; matching hierarchical taxonomies or nested data.

## Algorithms

### Sequence Alignment (`align`)

**Needleman-Wunsch global alignment** — standard dynamic-programming global alignment with configurable match, mismatch, and gap scores. Returns aligned index pairs and total score. Deterministic tie-breaking.

**Offset-scan inference** — infer an integer offset Δ such that `right_index + Δ ≈ left_index` for a pair of indexed sequences. Robust to small sequence differences; reports ambiguity when multiple offsets score similarly.

**Detailed offset-scan reporting** — inspect the full ranked candidate list, top-two offsets, and scanned range when reconciliation logic needs more than just the winning offset.

### Assignment (`assign`)

**Hungarian algorithm** — solve the minimum-cost bipartite assignment problem. Supports rectangular and square cost matrices, and lets either side leave elements unmatched via a configurable unmatched cost that acts as a true opt-out threshold.

### Scoring (`score`)

**Pair cost functions** — compute the cost of matching two elements. Hard constraints (incompatible elements receive a large sentinel cost) and soft penalties (difference in values, label mismatch, position difference) are combined with configurable weights.

**Categorical penalties** — express synonym-aware or normalized categorical comparisons, such as atom-name aliases, without rewriting the whole pair-cost function.

**Score composition** — a pair cost function can call a nested matching algorithm and return the optimal assignment cost as the score, enabling hierarchical matching.

### Blocking (`block`)

**Candidate-pair generation** — strategies for restricting which pairs are evaluated, including label equality, range overlap, and custom predicate blocking. Blocking is conservative: no true match is excluded.

### Matching (`match`)

**Hierarchical matching** — group elements by a key (e.g., sequence position and label), then match within each group. Operates across one or more levels of nesting.

**Strict and flexible modes** — strict mode requires key equality before matching. Flexible mode assigns groups by a cost objective: at the leaf it derives that objective from true element-level matching, and at intermediate levels it uses the level cost function directly.

**Result materialization** — convert the generic index-based `MatchResult` into domain records after orchestration, so callers can build their own matched-row types without reimplementing the hierarchy walk.

### Canonicalization (`canonicalize`)

**Record normalization** — convert raw elements into a stable canonical form before comparison. Supports fallback chains (use primary field if present, otherwise an authoritative alternative).

## Example

```python
from scohthwang.assign import hungarian_with_unmatched
from scohthwang.align import needleman_wunsch_alignment

# Minimum-cost bipartite assignment
costs = [
    [1.0, 3.0, 2.0],
    [2.0, 1.0, 4.0],
    [3.0, 2.0, 1.0],
]
match_for_left, total_cost = hungarian_with_unmatched(costs, unmatched_cost=5.0)
# match_for_left → [0, 1, 2], total_cost → 3.0

# Global sequence alignment
left  = ["A", "B", "C", "D"]
right = ["A", "C", "D"]
pairs, score = needleman_wunsch_alignment(
    left, right, match_score=2.0, mismatch_score=-1.0, gap_score=-2.0
)
# pairs → [(0, 0), (1, None), (2, 1), (3, 2)], score → 4.0
```

## Installation

This project uses `uv` for dependency management.

```bash
uv sync
```

To run the validation suite:

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/ruff format src/ tests/
.venv/bin/ty check src/ tests/
.venv/bin/pytest
```

## Project Status

Alpha — `0.2.1`.

The core matching, assignment, alignment, blocking, scoring, and
canonicalization APIs are implemented and tested. The package was extracted
and generalized from correspondence logic originally developed for BVP and is
now maintained as an independent support library.

The public API should be usable by downstream packages, but the project remains
pre-1.0 and may make incompatible API changes as additional use cases emerge.
