# TODO

## ~~Phase 1 — Core models (`src/scohthwang/models.py`)~~ ✓ complete

## Phase 2 — Assignment (`src/scohthwang/assign.py`)

Reference: `bvp/packages/bvp-cs/src/bvp_cs/algorithms/hungarian.py`

- [ ] Implement `hungarian_square(cost: CostMatrix) -> list[int]`
  - Kuhn-Munkres shortest-augmenting-path; input must be square and non-empty
  - Raise `ValueError` if non-square or empty
  - Document tie-breaking rule (prefer diagonal on equal cost)
- [ ] Implement `hungarian_with_unmatched(cost: CostMatrix, unmatched_cost: float) -> tuple[list[int | None], float]`
  - Empty cost (0 rows or 0 columns) → return `([], 0.0)`
  - Pad to square with `unmatched_cost`; call `hungarian_square`; strip dummy assignments
  - Return `(match_for_left, total_cost)`
- [ ] Write `tests/unit/test_assign.py`:
  - 1×1, 2×2, 3×3 square cases with known optimal solutions
  - Rectangular (more left than right, and vice versa)
  - All elements better off unmatched (all costs > unmatched_cost)
  - Empty inputs (0×0, 0×n, n×0)
  - Symmetry: transposing cost matrix produces consistent pairing

## Phase 3 — Sequence alignment (`src/scohthwang/align.py`)

Reference: `bvp/packages/bvp-cs/src/bvp_cs/algorithms/align.py`

- [ ] Implement `needleman_wunsch_alignment(left, right, *, match_score, mismatch_score, gap_score) -> tuple[list[AlignedPair], float]`
  - `left`, `right`: `list[Hashable]`; comparison via `==`
  - Tie-breaking: diagonal > up > left
  - Empty inputs → `([], 0.0)`
- [ ] Implement `infer_offset_from_sequences(left, right, *, max_span, ambiguous_delta) -> OffsetInferenceResult`
  - `left`, `right`: `list[tuple[int, Hashable]]`
  - Scan all offsets in natural range (clipped to `max_span` if provided)
  - `offset=None` if no support or ambiguous within `ambiguous_delta`
- [ ] Implement `infer_seq_offset(left_elements, right_elements, key_fn, *, max_span, min_support) -> OffsetInferenceResult`
  - `key_fn(element) -> tuple[int, Hashable]`; delegates to `infer_offset_from_sequences`
  - Returns `offset=None` if `compared < min_support`
- [ ] Write `tests/unit/test_align.py`:
  - NW: identical sequences, single deletion, single insertion, complete mismatch, empty inputs
  - Offset inference: exact offset 0, exact non-zero offset, ambiguous case, under-supported case
  - Property-based test (hypothesis): aligned pairs span full length of both sequences

## Phase 4 — Scoring (`src/scohthwang/score.py`)

Reference: `bvp/packages/bvp-cs/src/bvp_cs/algorithms/matching.py` (`pair_cost`, `MatchingConfig`)

- [ ] Define `PairCostFn` Protocol: `__call__(self, left: Any, right: Any) -> float`
- [ ] Define `ConstraintFn` Protocol: `__call__(self, left: Any, right: Any) -> bool`
- [ ] Define `WeightedFieldCost` dataclass: `field_fn: Callable[[Any], float]`, `weight: float`, `max_diff: float | None`
- [ ] Define `PairCostConfig` dataclass: `constraints: list[ConstraintFn]`, `field_costs: list[WeightedFieldCost]`, `unmatched_cost: float`, `large_cost: float = 1e9`
- [ ] Implement `make_pair_cost_fn(config: PairCostConfig) -> PairCostFn`
  - Any failing constraint → return `config.large_cost`
  - Sum `weight * abs(field_fn(left) - field_fn(right))` for each field cost
  - If `max_diff` exceeded for any field → return `config.large_cost`
- [ ] Implement `make_nested_cost_fn(inner_match_fn, left_items_fn, right_items_fn, unmatched_cost) -> PairCostFn`
  - Calls `inner_match_fn(left_items_fn(left), right_items_fn(right))` and returns `result.total_cost`
- [ ] Write `tests/unit/test_score.py`:
  - Constraint failure returns `large_cost`
  - Soft penalties accumulate correctly
  - `max_diff` exceeded returns `large_cost`
  - Nested cost function calls inner match and returns its `total_cost`

## Phase 5 — Blocking (`src/scohthwang/block.py`)

- [ ] Define `BlockingFn` Protocol: `__call__(self, left: Sequence[Any], right: Sequence[Any]) -> Iterable[tuple[int, int]]`
- [ ] Implement `all_pairs(left, right) -> Iterable[tuple[int, int]]`
- [ ] Implement `key_equality_block(key_fn: Callable[[Any], Hashable]) -> BlockingFn`
  - Build inverted index on right side; yield `(i, j)` where `key_fn(left[i]) == key_fn(right[j])`
- [ ] Implement `predicate_block(pred_fn: Callable[[Any, Any], bool]) -> BlockingFn`
- [ ] Implement `compose_blocks(*block_fns: BlockingFn, mode: Literal["union", "intersection"] = "union") -> BlockingFn`
- [ ] Write `tests/unit/test_block.py`:
  - `all_pairs` produces n×m pairs
  - `key_equality_block` never misses a pair with matching keys (recall invariant)
  - `predicate_block` never includes a pair failing the predicate
  - Union is superset of each component; intersection is subset
  - Empty inputs produce no pairs

## Phase 6 — Matching (`src/scohthwang/match.py`)

Reference: `bvp/packages/bvp-cs/src/bvp_cs/algorithms/matching.py`

- [ ] Define `Level` dataclass: `key_fn: Callable`, `cost_fn: PairCostFn`, `unmatched_cost: float`, `block_fn: BlockingFn | None = None`
- [ ] Implement `match_within_group(left, right, cost_fn, unmatched_cost) -> MatchResult`
  - Build cost matrix; call `hungarian_with_unmatched`; return `MatchResult`
- [ ] Implement `group_and_match(left, right, key_fn, cost_fn, unmatched_cost) -> dict[Any, MatchResult]`
  - Group by `key_fn`; call `match_within_group` for each shared-key group
  - Unmatched groups → all elements unmatched
- [ ] Implement `hierarchical_match(left, right, levels: list[Level]) -> MatchResult`
  - Strict mode: group by `levels[0].key_fn`, recurse with `levels[1:]`
  - Flexible fallback: use `cost_fn` to score groups, `assign` to pair them, then recurse
  - Flatten group results into a single `MatchResult` with re-indexed pairs
- [ ] Write `tests/unit/test_match.py`:
  - Single-level perfect matching
  - Single-level with unmatched elements on both sides
  - Two-level hierarchical: outer groups match, inner elements match
  - Flexible fallback when no groups share keys
  - Empty inputs at each level

## Phase 7 — Canonicalization (`src/scohthwang/canonicalize.py`)

Reference: `bvp/packages/bvp-cs/src/bvp_cs/algorithms/canonicalize.py`

- [ ] Define `CanonicalizeRule` dataclass: `field_name: str`, `fallback_chain: list[str]`
- [ ] Implement `make_canonicalizer(rules: list[CanonicalizeRule]) -> Callable[[T], T]`
  - Uses `dataclasses.replace` to fill `None` primary fields from first non-`None` fallback
  - Must be idempotent: `f(f(x)) == f(x)`
- [ ] Implement `normalize_str(v: str | None, *, lower: bool = False, strip: bool = True) -> str | None`
- [ ] Implement `sort_key_none_last(v: Any) -> tuple`
- [ ] Write `tests/unit/test_canonicalize.py`:
  - Rule fills `None` primary from first non-`None` fallback
  - Non-`None` primary is not overwritten
  - `make_canonicalizer` is idempotent
  - `normalize_str` with all flag combinations

## Final step — Public API (`src/scohthwang/__init__.py`)

- [ ] Export commonly used public symbols from each module
- [ ] Verify `from scohthwang import hungarian_with_unmatched, needleman_wunsch_alignment` works
- [ ] Update README.md example to match final implemented signatures
