# STATUS

## Current focus

Phase 4 complete. Next: Phase 5 (`block.py`) and Phase 6 (`match.py`) — independent after Phase 5 defines `BlockingFn`.

## Current state summary

- Version `0.0.0`, alpha.
- `models.py` implemented and fully tested (16 unit tests).
- `assign.py` implemented and fully tested (22 unit tests).
- `align.py` implemented and fully tested (28 unit tests including 1 property-based); bvp-cs migration notes updated.
- `score.py` implemented and fully tested (20 unit tests); bvp-cs migration notes updated.
- Remaining source modules (`canonicalize.py`, `block.py`, `match.py`) are empty stubs.
- Tooling (ruff, ty, pytest, uv) fully configured and functional.
- DESIGN.md, PLAN.md, TODO.md, and README.md reflect the current intended design.

## Known gaps and risks

- **`docs/adr/README.md` is stale**: indexes six ADRs from a different project; no actual ADR files exist. Clear and rebuild when architectural decisions are made.
- **No public API yet**: `__init__.py` is empty; deferred to Phase 7 per PLAN.md.
- **bvp-cs is not a declared dependency**: reference implementations in `bvp/packages/bvp-cs` must be transcribed and generalized by hand, not imported.

## Continuity notes

- Module names and responsibilities are stable per DESIGN.md (§ Architectural decomposition).
- Implementation order is Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 per PLAN.md. Phases 2 and 3 are independent and may proceed in parallel after Phase 1.
- The bvp-cs reference file for each phase is noted in PLAN.md under each phase's "Source" heading.
- README.md examples are aspirational; do not treat them as authoritative for signatures until Phase 7 is complete.
- The ADR index in `docs/adr/README.md` reflects a different project and should be ignored until rebuilt.
