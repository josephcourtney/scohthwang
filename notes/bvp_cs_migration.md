# bvp-cs → scohthwang migration notes

This file records the changes needed in `bvp/packages/bvp-cs` to switch from its
internal algorithm implementations to the generalised equivalents in `scohthwang`.

Notes are accumulated phase-by-phase as scohthwang implementations are written.

---

## Phase 2 — `assign.py` (Hungarian algorithm)

### What was transferred

`bvp_cs/algorithms/hungarian.py` → `scohthwang/assign.py`

All private helpers (`_init_arrays`, `_search_iteration`,
`_shortest_augmenting_path`, `_apply_augmenting_path`, `_build_assignment`,
`_pad_to_square`, `_extract_row_matching`, `_total_matching_cost`) were copied
verbatim and remain private in scohthwang.

### API differences

| bvp-cs | scohthwang | Note |
|---|---|---|
| `hungarian_with_unmatched(pair_costs, unmatched_cost)` | `hungarian_with_unmatched(cost, unmatched_cost)` | First parameter renamed `pair_costs` → `cost` |
| `hungarian_square([])` returns `[]` | `hungarian_square([])` raises `ValueError` | Callers that pass an empty matrix must guard with an emptiness check before calling, or switch to `hungarian_with_unmatched` which handles empty gracefully |
| No non-rectangular check | `hungarian_with_unmatched` raises `ValueError` on jagged input | No behaviour change for well-formed inputs |
| (implicit) square matrix forces all elements to be matched | **same behaviour** — documented explicitly | `unmatched_cost` is a dummy-padding cost, not an opt-out threshold; for equal-sized inputs all elements are always matched |

### Call sites to update in bvp-cs

#### `bvp_cs/algorithms/matching.py`

Three call sites import and use `hungarian_with_unmatched`:

```python
# current
from .hungarian import hungarian_with_unmatched

# replace with
from scohthwang.assign import hungarian_with_unmatched
```

The three call signatures are already compatible after the parameter rename
(all three pass `pair_costs` as a positional argument, so renaming the
parameter in scohthwang does not affect them):

- Line 113: `hungarian_with_unmatched(pair_costs, cfg.unmatched_cost)` — no change needed
- Line 241: `hungarian_with_unmatched(pair_costs, unmatched_cost=0.0)` — keyword argument
  `unmatched_cost` is unchanged; no change needed
- Line 424: `hungarian_with_unmatched(pair_costs, cfg.residue_unmatched_penalty)` — no change needed

#### `bvp_cs/engine/reconcile.py`

Imports and calls `hungarian_square` directly:

```python
# current
from bvp_cs.algorithms.hungarian import hungarian_square
# line 681:
assignment = hungarian_square(cost_matrix)
```

`cost_matrix` is already padded to square by `_build_shift_set_cost_matrix`
before being passed here, so `hungarian_square` is appropriate.

**Option A — minimal change**: replace import only:
```python
from scohthwang.assign import hungarian_square
```

**Option B — preferred**: replace the manual padding in
`_build_shift_set_cost_matrix` with a call to `hungarian_with_unmatched`,
letting scohthwang own the padding logic:
```python
from scohthwang.assign import hungarian_with_unmatched
# replace hungarian_square(cost_matrix) with:
assignment_list, _ = hungarian_with_unmatched(cost_matrix_unpadded, unpaired_cost)
```
This removes the manual padding code in `_build_shift_set_cost_matrix` and
makes the caller simpler, but requires refactoring that function's return value.

#### `bvp_cs/engine/strict.py`

Same pattern as `reconcile.py`:

```python
# current
from bvp_cs.algorithms.hungarian import hungarian_square
# line 655:
assignment = hungarian_square(cost_matrix)
```

Same two options apply. The surrounding code (lines 628–668) manually builds
a padded square matrix with `unpaired_cost`, then strips dummy assignments
after calling `hungarian_square`. Switching to `hungarian_with_unmatched`
would let scohthwang handle both the padding and the stripping, simplifying
roughly 30 lines to ~5.

### bvp-cs internal `hungarian.py` after migration

Once all call sites are updated, `bvp_cs/algorithms/hungarian.py` can be
deleted entirely. Until then it should remain to avoid a hard dependency on
scohthwang during the transition.

---

## Phase 3 — `align.py` (Needleman-Wunsch + offset scan)

### What was transferred

`bvp_cs/algorithms/align.py` → `scohthwang/align.py`

Private helpers carried over: `_initialize_alignment_matrices`,
`_fill_alignment_matrices`, `_traceback_alignment`, `_is_ambiguous_offset_choice`
(renamed `_is_ambiguous`), `_score_offsets_for_range_top2` (renamed
`_score_offsets_top2`).

Not carried over (domain-specific):
- `OffsetScanCandidate`, `OffsetScanReport` — internal types replaced by
  private `_OffsetCandidate` and public `OffsetInferenceResult` from models
- `infer_best_offset_from_sequences_detailed` — detail reporting; callers
  that need top-2 candidates must be refactored or keep a local copy
- `_coalesce_seq_id`, `_coalesce_comp_id`, `_rows_to_seq_comp_pairs`,
  `seq_comp_pairs_from_rows` — `ShiftRow`-specific; replaced by generic
  `key_fn` in `infer_seq_offset`
- `_score_offsets_for_range` — superseded by the top-2 variant

### API differences

| bvp-cs | scohthwang | Note |
|---|---|---|
| `needleman_wunsch_alignment(left: list[str], right: list[str], ...)` | `needleman_wunsch_alignment(left: list[Hashable], right: list[Hashable], ...)` | Type widened from `str` to any `Hashable`; same parameters and return shape |
| `infer_best_offset_from_sequences(left_seq, right_seq, ...) -> tuple[int|None, float, int, bool]` | `infer_offset_from_sequences(left, right, ...) -> OffsetInferenceResult` | Renamed; returns structured result instead of 4-tuple |
| `infer_seq_offset(left_rows: list[ShiftRow], right_rows: list[ShiftRow], ...) -> int | None` | `infer_seq_offset(left_elements, right_elements, key_fn, ...) -> OffsetInferenceResult` | `ShiftRow` extraction replaced with generic `key_fn`; returns `OffsetInferenceResult` instead of `int \| None`; ambiguity no longer forces `offset=None` (returned as flag for callers to act on) |
| `infer_best_offset_from_sequences_detailed(...)` | **not carried over** | Callers needing top-2 detail must keep local copy or use bvp-cs version |

### Call sites to update in bvp-cs

#### `bvp_cs/engine/reconcile.py`

Line 12 imports:
```python
from bvp_cs.algorithms.align import infer_best_offset_from_sequences, needleman_wunsch_alignment
```

Replace with:
```python
from scohthwang.align import infer_offset_from_sequences, needleman_wunsch_alignment
```

**`needleman_wunsch_alignment`** (line 387): signature-compatible; update import only.

**`infer_best_offset_from_sequences`** (line 517): destructuring tuple must change:
```python
# before
offset, residue_overlap, compared, ambiguous = infer_best_offset_from_sequences(left_seq, right_seq)

# after
_r = infer_offset_from_sequences(left_seq, right_seq)
offset, residue_overlap, compared, ambiguous = _r.offset, _r.agreement, _r.compared, _r.ambiguous
```

#### `bvp_cs/engine/strict.py`

Line 10 imports `infer_best_offset_from_sequences`; line 721 destructs the result:
```python
offset, residue_overlap, compared, _ambiguous = infer_best_offset_from_sequences(left_seq, right_seq)
```
Same fix as reconcile.py above.

#### `bvp_cs/engine/merge_reports.py`

Lines 13–14 import both `infer_best_offset_from_sequences_detailed` and
`infer_seq_offset`.

- `infer_best_offset_from_sequences_detailed` is **not available** in scohthwang;
  this call site needs a separate refactor (either keep using bvp-cs's version,
  or expand scohthwang to expose the top-2 detail if needed).
- `infer_seq_offset` (line 136): signature and return type both change. The call
  currently passes `list[ShiftRow]`; after migration it must supply a `key_fn`:
  ```python
  # before
  applied = infer_seq_offset(left_rows, right_rows, max_span=max_span, min_support=min_support)
  # applied is int | None

  # after
  from bvp_cs.algorithms.canonicalize import seq_comp_pairs_from_rows  # keep local helper
  result = infer_seq_offset(
      left_rows, right_rows,
      key_fn=lambda row: (seq_id_of(row), comp_id_of(row)),
      max_span=max_span, min_support=min_support,
  )
  applied = result.offset  # int | None
  ```
  The ambiguity-rejection that bvp-cs `infer_seq_offset` applied implicitly is
  now the caller's responsibility; check `result.ambiguous` if needed.

---

## Phase 4 — `score.py` (pair-cost scoring)

### What was transferred

`bvp_cs/algorithms/matching.py` (`pair_cost`, `_atom_name_cost`) and
`bvp_cs/settings/models.py` (`MatchingConfig`) → `scohthwang/score.py`

The domain-specific structure (`MatchingConfig` with `nucleus_weights`,
`atom_name_synonyms`, `max_shift_diff_by_nucleus`, `seq_id_mismatch_weight`,
etc.) was replaced with generic abstractions:

| bvp-cs concept | scohthwang equivalent |
|---|---|
| `MatchingConfig.nucleus_weights` + `max_shift_diff_by_nucleus` | `WeightedFieldCost(field_fn=..., weight=..., max_diff=...)` |
| `MatchingConfig.unmatched_cost` | `PairCostConfig.unmatched_cost` |
| `MatchingConfig.large_cost` | `PairCostConfig.large_cost` |
| Nucleus/comp-id equality guards (`return cfg.large_cost`) | `ConstraintFn` in `PairCostConfig.constraints` |
| `_atom_name_cost` (synonym lookup, partial match) | Caller-defined `WeightedFieldCost` or `ConstraintFn` |
| `pair_cost(pdb_row, bmrb_row, cfg) -> float` | `make_pair_cost_fn(config)` returning a `PairCostFn` |

Not carried over (domain-specific, no generic equivalent):
- `_atom_name_cost` synonym lookup — callers who need synonym mapping must
  supply a custom `ConstraintFn` or `WeightedFieldCost.field_fn`.
- `MatchingConfig.seq_id_mismatch_weight` — a plain `WeightedFieldCost` term
  covers this once the caller supplies `field_fn=lambda row: row.seq_id`.

### API differences

`make_nested_cost_fn` is new with no direct bvp-cs counterpart.  In bvp-cs,
`match_atoms_in_residue` computes the inner cost directly; scohthwang
separates the "what is the cost of this pair" question from the "how do I run
a sub-match" question via the `inner_match_fn` callback parameter.

### Call sites to update in bvp-cs

#### `bvp_cs/algorithms/matching.py`

`pair_cost` and `MatchingConfig` are tightly coupled to the
`ShiftRow`/`MatchedRow` domain types.  Migration requires:

1. Define one or more `ConstraintFn` closures for nucleus/comp-id equality:
   ```python
   def same_nucleus(left: ShiftRow, right: ShiftRow) -> bool:
       nuc_p = (left.atom_type or "").upper()
       nuc_b = (right.atom_type or "").upper()
       return not (nuc_p and nuc_b and nuc_p != nuc_b)

   def same_comp(left: ShiftRow, right: ShiftRow) -> bool:
       return not (left.comp_id and right.comp_id and left.comp_id != right.comp_id)
   ```

2. Define `WeightedFieldCost` terms for each numeric penalty:
   ```python
   from scohthwang.score import WeightedFieldCost

   def shift_diff(row: ShiftRow) -> float:
       return float(row.shift or 0.0)

   shift_cost = WeightedFieldCost(
       field_fn=shift_diff,
       weight=cfg.nucleus_weights.get(nuc, 1.0),
       max_diff=cfg.max_shift_diff_by_nucleus.get(nuc),
   )
   ```
   Note: nucleus-specific weight and max_diff vary per nucleus, so the
   `WeightedFieldCost` must be constructed per-nucleus or use a lambda that
   closes over the nucleus.

3. The atom-name synonym lookup in `_atom_name_cost` has no generic equivalent;
   keep it as a local helper and wrap it in a `WeightedFieldCost.field_fn`, or
   retain the bvp-cs implementation for that term.

4. Assemble the config and build the function:
   ```python
   from scohthwang.score import PairCostConfig, make_pair_cost_fn

   config = PairCostConfig(
       constraints=[same_comp, same_nucleus],
       field_costs=[shift_cost, seq_cost, atom_name_cost],
       unmatched_cost=cfg.unmatched_cost,
       large_cost=cfg.large_cost,
   )
   pair_cost_fn = make_pair_cost_fn(config)
   # replaces: pair_cost(pdb_row, bmrb_row, cfg)
   # with:     pair_cost_fn(pdb_row, bmrb_row)
   ```

`match_atoms_in_residue` callers can be updated after Phase 6 (`match.py`) is
implemented, since the outer matching loop is part of that phase.
