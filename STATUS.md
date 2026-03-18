# STATUS

## Current focus

Project scope and architecture have just been defined. The immediate work is Phase 1 of PLAN.md: define core models in `models.py` and write the first unit tests, establishing the baseline structure that all subsequent modules depend on.

## Current state summary

- Version `0.0.0`, alpha.
- All source modules (`models.py`, `canonicalize.py`, `block.py`, `score.py`, `align.py`, `match.py`, `assign.py`) are empty stubs.
- No tests exist beyond conftest scaffolding and `tests/__init__.py`.
- Tooling (ruff, ty, pytest, uv) is fully configured and functional.
- DESIGN.md, PLAN.md, TODO.md, and README.md have been written and reflect the current intended design.
- Algorithm designs are informed by working implementations in `bvp/packages/bvp-cs/src/bvp_cs/algorithms/`; that code is the primary reference for Phases 2–7.

## Known gaps and risks

- **`docs/adr/README.md` is stale**: it indexes six ADRs that belong to a different project. No actual ADR files exist. The index should be cleared and rebuilt when architectural decisions are made.
- **No public API**: `__init__.py` is empty; nothing is importable yet.
- **No tests**: coverage baseline is zero; Phase 1 will establish it.
- **bvp-cs is not a declared dependency**: the reference implementations live in `bvp/packages/bvp-cs`, which is not importable from this package. Code must be transcribed and generalized by hand, not imported.

## Continuity notes

- Module names and responsibilities are stable per DESIGN.md (§ Architectural decomposition).
- Implementation order is Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 per PLAN.md. Phases 2 and 3 are independent and may proceed in parallel after Phase 1.
- The bvp-cs reference file for each phase is noted in PLAN.md under each phase's "Source" heading.
- README.md examples are aspirational; do not treat them as authoritative for signatures until Phase 7 is complete.
- The ADR index in `docs/adr/README.md` reflects a different project and should be ignored until rebuilt.
