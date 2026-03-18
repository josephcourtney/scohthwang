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
