# PLAN

> This document describes how DESIGN.md will be realized: implementation phases, ordering, dependencies, and non-obvious considerations. It does not track status (see STATUS.md) or enumerate detailed per-file tasks (see TODO.md).

---

## Guiding constraints

- Each phase produces independently usable, tested code. Later phases depend on earlier ones but not vice versa.
- The bvp-cs source (`bvp/packages/bvp-cs/src/bvp_cs/algorithms/`) is the primary reference implementation. The task is generalization, not invention — read that code first when implementing each module.
- No runtime dependencies outside the standard library. Optional numpy-backed paths may be added later but are strictly conditional imports.
- Tests must exist for each phase before that phase is considered done. Unit tests only at this stage.

---

## Phase 1 — Core models (`models.py`)

Define the shared types that all other modules use. Everything else depends on this.

**Deliverables:**
- `CostMatrix` — type alias for `list[list[float]]`; document the sentinel convention (`LARGE_COST = 1e9`)
- `MatchResult` — frozen dataclass: `pairs: list[tuple[int, int]]`, `unmatched_left: list[int]`, `unmatched_right: list[int]`, `total_cost: float`
- `AlignedPair` — type alias for `tuple[int | None, int | None]`; used by alignment functions
- `OffsetInferenceResult` — frozen dataclass: `offset: int | None`, `agreement: float`, `compared: int`, `ambiguous: bool`

**Non-obvious considerations:**
- Keep models minimal. Avoid pulling domain concepts (residues, nuclei, chains) in here.
- `MatchResult` should carry enough information to reconstruct which elements were paired without re-running the algorithm.

---

## Phase 2 — Assignment (`assign.py`)

Implement the Hungarian algorithm. This is the innermost algorithmic primitive and has no dependencies beyond `models.py`.

**Source:** `bvp-cs/algorithms/hungarian.py` — `hungarian_square` and `hungarian_with_unmatched`.

**Deliverables:**
- `hungarian_square(cost: CostMatrix) -> list[int]` — solve square assignment; Kuhn-Munkres shortest-augmenting-path implementation
- `hungarian_with_unmatched(cost: CostMatrix, unmatched_cost: float) -> tuple[list[int | None], float]` — pad to square with `unmatched_cost`, run `hungarian_square`, strip dummy assignments, return `(match_for_left, total_cost)`

**Key generalization steps from bvp-cs:**
- Remove the implicit assumption that inputs are non-empty; return trivially for empty inputs
- Add explicit precondition checks with `ValueError` for malformed inputs (non-rectangular matrix, negative costs)
- Document tie-breaking rule (prefer diagonal in case of equal augmenting-path cost)

**Ordering constraint:** Must come before `score.py` (which may call `assign` for nested matching) and `match.py`.

---

## Phase 3 — Sequence alignment (`align.py`)

Implement Needleman-Wunsch and offset-scan. Independent of `assign.py`.

**Source:** `bvp-cs/algorithms/align.py` — `needleman_wunsch_alignment`, `infer_best_offset_from_sequences`, `infer_seq_offset`.

**Deliverables:**
- `needleman_wunsch_alignment(left, right, *, match_score, mismatch_score, gap_score) -> tuple[list[AlignedPair], float]`
  - Sequences are `list[Hashable]`; comparison is `==`
  - Tie-breaking: prefer diagonal > up > left
  - Returns aligned index pairs (either index may be `None` for a gap) and total score
- `infer_offset_from_sequences(left, right, *, max_span, ambiguous_delta) -> OffsetInferenceResult`
  - `left` and `right` are `list[tuple[int, Hashable]]` (index, label) pairs
  - Scans all offsets in range; scores each by agreement fraction
  - Marks ambiguous if second-best agreement is within `ambiguous_delta` of best
- `infer_seq_offset(left_rows, right_rows, key_fn, *, max_span, min_support) -> OffsetInferenceResult`
  - Higher-level wrapper: accepts arbitrary element lists, uses `key_fn(element) -> tuple[int, Hashable]` to extract (index, label), then delegates to `infer_offset_from_sequences`

**Key generalization steps from bvp-cs:**
- Replace `ShiftRow`-specific field extraction with a generic `key_fn` parameter
- Accept `list[Hashable]` in NW rather than `list[str]`

---

## Phase 4 — Scoring (`score.py`)

Define the cost-function infrastructure. Depends on `models.py`; referenced by `match.py` and `assign.py` callers.

**Source:** `bvp-cs/algorithms/matching.py` — `pair_cost` and `MatchingConfig`.

**Deliverables:**
- `PairCostFn` — `Protocol`: `(left: Any, right: Any) -> float`
- `ConstraintFn` — `Protocol`: `(left: Any, right: Any) -> bool` — `True` if the pair is admissible
- `WeightedFieldCost` — dataclass: `field_fn: Callable`, `weight: float`, `max_diff: float | None`
- `PairCostConfig` — dataclass:
  - `constraints: list[ConstraintFn]` — any failing constraint returns `large_cost`
  - `field_costs: list[WeightedFieldCost]` — summed soft penalties
  - `unmatched_cost: float`
  - `large_cost: float = 1e9`
- `make_pair_cost_fn(config: PairCostConfig) -> PairCostFn` — return a closure over the config
- `make_nested_cost_fn(inner_match_fn, left_items_fn, right_items_fn, unmatched_cost) -> PairCostFn` — return a cost function that calls an inner matching algorithm on the sub-elements of two container elements and returns the optimal assignment cost

**Key generalization steps from bvp-cs:**
- `MatchingConfig` in bvp-cs is domain-specific. Replace with generic `PairCostConfig` assembled from a list of `WeightedFieldCost` and `ConstraintFn` components.
- The nested-cost function is new — bvp-cs computes nested costs implicitly through its hierarchy. Making it first-class enables arbitrary-depth composability.

---

## Phase 5 — Blocking (`block.py`)

Implement candidate-pair generators. Depends on `models.py` only.

**No direct bvp-cs source** — blocking is implicit in bvp-cs (residue grouping, hard constraints in `pair_cost`). This module makes blocking explicit and composable.

**Deliverables:**
- `BlockingFn` — `Protocol`: `(left: Sequence[Any], right: Sequence[Any]) -> Iterable[tuple[int, int]]`
- `all_pairs(left, right) -> Iterable[tuple[int, int]]` — O(n²) pass-through
- `key_equality_block(key_fn) -> BlockingFn` — yield pairs where `key_fn(left[i]) == key_fn(right[j])`
- `predicate_block(pred_fn) -> BlockingFn` — yield pairs where `pred_fn(left[i], right[j])` is True
- `compose_blocks(*block_fns, mode="union") -> BlockingFn` — combine multiple blocking functions

**Invariant to enforce in tests:** for each `BlockingFn`, verify that for a reference set of known-correct pairs, all known-correct pairs appear in the candidate set (i.e., blocking has recall 1.0 on the fixture set).

---

## Phase 6 — Matching (`match.py`)

Implement the hierarchical matching pipeline. Depends on all previous phases.

**Source:** `bvp-cs/algorithms/matching.py` — `match_atoms_in_residue`, `optimal_shift_matching_all_residues`, and group-by-residue logic.

**Deliverables:**
- `match_within_group(left, right, cost_fn, unmatched_cost) -> MatchResult` — build cost matrix over `(left[i], right[j])` pairs, call `hungarian_with_unmatched`, wrap as `MatchResult`
- `group_and_match(left, right, key_fn, cost_fn, unmatched_cost) -> dict[key, MatchResult]` — group both lists by `key_fn`, match within each group pair
- `hierarchical_match(left, right, levels: list[Level]) -> MatchResult`
  - `Level` bundles: `key_fn`, `cost_fn`, `unmatched_cost`, optional `block_fn`
  - Strict mode (default): group by key, require exact key equality, treat unmatched groups as fully unmatched
  - Flexible mode: when strict fails or cost is high, use `cost_fn` to score group-to-group pairs and `assign` to pick the best pairing before within-group matching

**Key generalization steps from bvp-cs:**
- The hard-coded chain→residue→atom hierarchy becomes a `list[Level]` configuration
- Domain concepts (chain identity, comp_id grouping) become generic `key_fn` callables
- The reconciliation fallback becomes the flexible mode of the same `hierarchical_match` call

**Ordering constraint:** Depends on `assign`, `score`, `block`, `models`. Last among the algorithm modules.

---

## Phase 7 — Canonicalization (`canonicalize.py`)

Implement normalization utilities. Depends on `models.py` only; logically a pre-processing step.

**Source:** `bvp-cs/algorithms/canonicalize.py`.

**Deliverables:**
- `CanonicalizeRule` — named pair: `field_name: str`, `fallback_chain: list[str]`
- `make_canonicalizer(rules: list[CanonicalizeRule]) -> Callable[[T], T]` — return a function that fills `None` primary fields from the first non-`None` fallback, for any dataclass `T`
- `normalize_str(v: str | None, *, lower: bool, strip: bool) -> str | None` — string normalization helper
- `sort_key_none_last(v: Any) -> tuple` — sort helper: `None` last, comparable values sort naturally

**Key generalization steps from bvp-cs:**
- `canonicalize_row` in bvp-cs is a monolithic function specific to `ShiftRow`. Here `make_canonicalizer` generates the equivalent from a rule list for any dataclass.

---

## Non-obvious implementation considerations

- **Empty inputs**: all algorithms handle empty lists gracefully (return empty/zero result, not raise).
- **Rectangular Hungarian**: pad to square by adding dummy rows/columns at `unmatched_cost`; strip dummy assignments; ensure returned indices map back to original inputs correctly.
- **Offset-scan edge cases**: empty sequences or `max_span` exceeding natural range → `OffsetInferenceResult(offset=None, ...)`.
- **Composability and cycles**: `make_nested_cost_fn` wraps an inner matching call. The library does not detect infinite recursion; callers are responsible for finite nesting.
- **Type annotations**: use `Protocol` for `PairCostFn`, `ConstraintFn`, and `BlockingFn` to preserve IDE inference through composition.
- **`__init__.py` exports**: defer defining the public API in `__init__.py` until Phase 6 is complete, so the exported surface reflects the full composed pipeline rather than individual fragments.
