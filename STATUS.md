# STATUS

## Current focus

Maintain the published 0.2.x API surface while keeping typing/lint suppressions
narrow, justified, and documented.

## Current state summary

- Version `0.2.1` patch release preparation in progress.
- Core matching, scoring, canonicalization, and public API modules are complete
  and covered by contract/unit tests.
- The latest maintenance pass tightened suppression hygiene by removing
  avoidable directives and adding explicit rationale comments where suppressions
  are intentionally retained (generic protocols, frozen-dataclass negative
  tests, and controlled `exec`/subprocess test cases).
- Tooling (ruff, ty, pytest, uv) is configured and operational.

## Known gaps and risks

- API-level evolution is stable, but future generic-typing refactors could
  narrow accepted callable signatures if not validated against existing contract
  tests.
- Suppression rationale comments must stay aligned with implementation details
  as tests and protocols evolve.

## Continuity notes

- Treat `src/scohthwang/score.py` and `src/scohthwang/canonicalize.py` as
  primary locations for generic typing/suppression decisions.
- Treat `tests/contract/` as the authoritative public-surface behavior lock.
