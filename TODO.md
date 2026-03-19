# TODO

## ~~Phase 1 — Core models (`src/scohthwang/models.py`)~~ ✓ complete

## ~~Phase 2 — Assignment (`src/scohthwang/assign.py`)~~ ✓ complete

## ~~Phase 3 — Sequence alignment (`src/scohthwang/align.py`)~~ ✓ complete

## ~~Phase 4 — Scoring (`src/scohthwang/score.py`)~~ ✓ complete


## ~~Phase 5 — Blocking (`src/scohthwang/block.py`)~~ ✓ complete

## ~~Phase 6 — Matching (`src/scohthwang/match.py`)~~ ✓ complete

## ~~Phase 7 — Canonicalization (`src/scohthwang/canonicalize.py`)~~ ✓ complete

## ~~Final step — Public API (`src/scohthwang/__init__.py`)~~ ✓ complete

## Follow-up — Contract and Release Gaps

- [ ] resolve packaging metadata drift: either add `src/scohthwang/cli.py` for the published `scohthwang` console script or remove the broken entry point from `pyproject.toml`
- [ ] fix `tool.mutmut.paths_to_mutate` in `pyproject.toml`; it still points at stale `src/wrixlere` instead of this package
- [ ] decide and codify `hungarian_with_unmatched()` semantics for square matrices: either implement true opt-out unmatched behavior or narrow the public contract and README to the current dummy-padding behavior
- [ ] add contract tests for assignment semantics, including square-matrix unmatched behavior and blocked `match_within_group()` cases that currently force `LARGE_COST` pairings in square groups
- [ ] fix `infer_offset_from_sequences()` so zero-comparison scans return `offset=None`, matching its docstring and public contract
- [ ] add contract tests for offset inference when every candidate offset has zero comparable pairs
- [ ] define flexible matching cost semantics explicitly: ensure `_flexible_intermediate()` reports costs consistent with the objective used to choose group assignments
- [ ] decide whether flexible leaf matching should keep positional element pairing or switch to true inner matching; document and test the chosen behavior
- [ ] align `make_canonicalizer()` error behavior and docs so missing fields raise the documented exception type, or update the docs to match `AttributeError`
- [ ] add a public-surface contract test that `scohthwang.__init__` exports exactly the symbols listed in `__all__`
- [ ] add a packaging smoke test that builds/installs the wheel, imports `scohthwang`, and exercises any published console entry points
- [ ] audit runtime dependencies in `pyproject.toml`; move test-only packages such as `pytest-asyncio` out of `[project.dependencies]` if they are not part of the library runtime
