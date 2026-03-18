# DESIGN

> Rationale for major architectural choices is captured in ADRs under `docs/adr/`.
> This document is **normative**: it specifies intended architecture, invariants, and contracts.

## Related ADRs

*(No ADRs written yet. The `docs/adr/README.md` index was inherited from a template and does not reflect this project's design decisions; it must be rebuilt as decisions are made.)*

---

## Intent and scope

### High-level goals

`scohthwang` is a Python library of composable algorithms for finding correspondences between elements of two sets, sequences, or containers.

Core goals:

- Provide general-purpose, reusable implementations of canonical correspondence algorithms: Needleman-Wunsch global alignment, Hungarian optimal assignment, offset-scan inference, and configurable pair-cost scoring.
- Support hierarchical composability: the cost of matching two elements at one level can be computed by running an inner matching algorithm on their contents, so multi-level matching schemes can be built from the same primitives.
- Produce deterministic outputs: given the same inputs and configuration, the same result is always produced.
- Be library-first: algorithms are plain functions or lightweight classes; no global state, no I/O, no required runtime services.

### Non-goals

- Domain-specific data models (biological sequences, NMR shifts, database IDs, etc.) — callers supply those.
- Persistence, serialization, or I/O infrastructure.
- Statistical model fitting or parameter learning — the library consumes pre-configured cost functions and thresholds.
- Interactive tooling or standalone CLI application.
- Approximate nearest-neighbor search or embedding-based similarity — the library operates on explicit cost matrices or explicit pair-cost functions.

---

## Architectural decomposition

The library is organized as six modules. Each has a narrow, well-defined responsibility and can be used independently or composed with the others.

| Module            | Responsibility                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| `models.py`       | Shared types: element containers, candidate pairs, match results, cost matrix representations                 |
| `canonicalize.py` | Normalize heterogeneous input records into a stable canonical form suitable for comparison                    |
| `block.py`        | Generate the candidate pair set, reducing the O(n²) space to a tractable subset                               |
| `score.py`        | Compute costs/scores for candidate pairs; supports hard constraints, soft penalties, and composition          |
| `align.py`        | Sequence alignment: Needleman-Wunsch global alignment and offset-scan inference                               |
| `match.py`        | Hierarchical matching pipelines: group elements by key, match within groups, handle strict and flexible modes |
| `assign.py`       | Optimal assignment: Hungarian algorithm for minimum-cost bipartite matching with unmatched support            |

### Data flow

```
raw elements
    │
    ▼
canonicalize()          ← normalize into stable form
    │
    ▼
block()                 ← generate candidate pairs
    │
    ▼
score()  ─────────────► [optional: inner match() on sub-elements]
    │
    ▼
assign() / align()      ← resolve optimal correspondence
    │
    ▼
MatchResult             ← matched pairs + unmatched elements + total cost
```

Each stage is a pure function (or configurable callable) with no side effects. Callers may enter the pipeline at any stage or substitute any stage with a domain-specific implementation.

---

## Key abstractions and invariants

### Element

An `Element` is an opaque value that the library pairs with another. Elements carry a comparable key for grouping and blocking, and a value used for scoring. The library imposes no structure on element values beyond what individual scoring functions require.

### CostMatrix

A `CostMatrix` is a rectangular `list[list[float]]` where `matrix[i][j]` is the cost of pairing element `i` from the left set with element `j` from the right set. A sentinel value (default `1e9`) represents incompatible pairs that must not be matched.

### MatchResult

A `MatchResult` records the output of a matching operation:
- `pairs`: the matched `(left_index, right_index)` assignments
- `unmatched_left` / `unmatched_right`: indices of elements left without a partner
- `total_cost`: sum of matched pair costs plus unmatched penalties

### Invariants

- **Canonicalization is pure and idempotent**: `canonicalize(canonicalize(x)) == canonicalize(x)`.
- **Blocking is conservative**: the blocking step never excludes a pair that would be the optimal match. Precision may be sacrificed; recall over the candidate set must be 1.0.
- **Scoring is symmetric for commutative cost functions**: `score(a, b) == score(b, a)` whenever the underlying cost function is commutative.
- **Assignment is valid**: the Hungarian result is a valid matching — each left element is paired with at most one right element and vice versa.
- **Determinism**: all algorithms are deterministic. Tie-breaking follows explicit, documented rules (e.g., prefer diagonal over up/left in dynamic-programming tables; prefer smaller index on equal cost in Hungarian).
- **Composability**: any function that returns a `float` cost can serve as a `score` argument to `assign` or `match`, including a function that internally calls `match` or `assign` on sub-elements.

---

## Requirements

### Functional requirements

- **FR-1** `assign.hungarian_with_unmatched(costs, unmatched_cost)` solves the minimum-cost bipartite assignment on a rectangular cost matrix, allowing any element to go unmatched at the given penalty. Returns a list of right-side indices (or `None`) for each left element, and the total cost.
- **FR-2** `align.needleman_wunsch_alignment(left, right, ...)` computes a global alignment between two sequences of labels, returning aligned index pairs and total score.
- **FR-3** `align.infer_seq_offset(left, right, ...)` infers an integer offset Δ such that `right_index + Δ ≈ left_index` for a pair of indexed sequences, with ambiguity detection.
- **FR-4** `score` provides a configurable cost-function construction mechanism: callers specify per-field weights, hard-constraint predicates, and an optional nested matching call.
- **FR-5** `block` provides at minimum key-equality blocking and a pass-through (all-pairs) mode.
- **FR-6** `match` provides a hierarchical matching function that groups elements by a key function, applies blocking and scoring within each group, and calls `assign` to resolve optimal pairs.
- **FR-7** All algorithms accept plain Python data structures (lists, dicts, dataclasses). No third-party data-frame library is required at the algorithm layer.

### Non-functional requirements

- **NFR-1** All public functions are fully type-annotated.
- **NFR-2** All algorithms are deterministic for a given input and configuration.
- **NFR-3** The library has no required runtime dependencies beyond the Python standard library.
- **NFR-4** The Hungarian implementation handles matrices up to ~500×500 in under one second on typical hardware.
- **NFR-5** All public functions are covered by unit tests with deterministic fixtures.

---

## Policies

### Dependency policy

The library layer (`src/scohthwang/`) must have no required runtime dependencies outside the Python standard library. Optional acceleration (e.g., numpy-backed cost matrix) may be provided behind a conditional import, but the pure-Python path must always work.

### Determinism policy

Non-deterministic behavior (random seeding, hash-order iteration, time-dependent values) is prohibited in algorithm implementations. Where Python dict iteration order matters, inputs are sorted before use.

### Error handling policy

- Invalid inputs (e.g., non-square matrix passed to `hungarian_square`, mismatched dimensions) raise `ValueError` with a descriptive message.
- Cost functions may return the sentinel `large_cost` value to indicate an incompatible pair; they must not raise.
- All public functions validate their preconditions at the boundary.

---

## Source of algorithmic designs

The implementations are informed by, and generalize, working domain-specific code in `bvp/packages/bvp-cs`:

| scohthwang module | Origin in bvp-cs                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------ |
| `assign.py`       | `algorithms/hungarian.py`: `hungarian_with_unmatched`, `hungarian_square`                                   |
| `align.py`        | `algorithms/align.py`: `needleman_wunsch_alignment`, `infer_best_offset_from_sequences`, `infer_seq_offset` |
| `score.py`        | `algorithms/matching.py`: `pair_cost`, `MatchingConfig`                                                     |
| `match.py`        | `algorithms/matching.py`: `match_atoms_in_residue`, `optimal_shift_matching_all_residues`                   |
| `canonicalize.py` | `algorithms/canonicalize.py`: `canonicalize_row`, `chain_like_id`, `residue_key`                            |
| `block.py`        | Implicit in `matching.py` grouping logic; no standalone equivalent exists in bvp-cs                          |

The domain-specific data models (`ShiftRow`, `MatchedRow`, nucleus weighting, chain/residue grouping logic) are **not** carried over — callers supply their own element types and cost functions.
