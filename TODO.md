# TODO

## ~~Phase 1 — Core models (`src/scohthwang/models.py`)~~ ✓ complete

## ~~Phase 2 — Assignment (`src/scohthwang/assign.py`)~~ ✓ complete

## ~~Phase 3 — Sequence alignment (`src/scohthwang/align.py`)~~ ✓ complete

## ~~Phase 4 — Scoring (`src/scohthwang/score.py`)~~ ✓ complete


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
