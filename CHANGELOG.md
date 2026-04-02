# CHANGELOG.md

Curated, user-facing record, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/)

Items should be categorized under these headings:

- **Added** - new features
- **Changed** - changes in existing functionality
- **Deprecated** - soon-to-be removed features
- **Removed** - now removed features
- **Fixed** - any bug fixes
- **Security** - in case of vulnerabilities

## Unreleased

### Added

### Changed

### Deprecated

### Removed
- remove obsolete check-command tests that still targeted the retired `scohthwang.app` and `scohthwang.cli.root` package layout

### Fixed
- fix lint violations across sync, locator, query, status, and transport helpers by extracting smaller helper routines and cleaning import/docstring issues
- fix pytest warning noise by installing `pytest-test-categories`, adding explicit size markers to the unit suite, and aligning pytest category enforcement settings with the current medium-sized test mix

### Security

## [0.2.1] - 2026-04-02

### Added

### Changed
- clarify retained suppression directives with explicit rationale across score,
  canonicalize, and contract/unit tests so generic typing boundaries and
  intentional negative-test violations are documented inline

### Deprecated

### Removed
- remove an unnecessary `# noqa: E731` by replacing a lambda in unit tests with
  a named local function

### Fixed

### Security

## [0.2.0] - 2026-03-19

### Added
- add `OffsetScanCandidate`, `OffsetScanReport`, `infer_offset_from_sequences_detailed()`, and `infer_best_offset_from_sequences_detailed()` for detailed offset-scan reporting
- add `CategoricalFieldCost` so pair scoring can express categorical, synonym-aware, and normalized mismatch penalties alongside numeric field costs
- add `MaterializedMatchResult`, `materialize_match_result()`, and `hierarchical_match_materialized()` so callers can map generic matches into domain result rows without reimplementing orchestration

### Changed
- change the public facade to export the new detailed offset, categorical scoring, and materialized matching APIs

### Deprecated

### Removed

### Fixed

### Security

## [0.1.0] - 2026-03-19

### Added
- add a minimal `scohthwang` CLI entry point with version and public-API listing commands so the published console script resolves correctly
- add contract tests for square-matrix unmatched assignment, blocked-group unmatched behavior, zero-support offset inference, and `__all__` export coverage
- add a packaging smoke test that builds a wheel, installs it into a fresh virtual environment, imports the package, and runs the published console script

### Changed
- change `hungarian_with_unmatched()` to model unmatched elements explicitly on both sides so square matrices can opt out when real pair costs exceed `unmatched_cost`
- change flexible leaf matching to score candidate group pairs via true inner element matching instead of positional pairing
- change flexible intermediate matching to report the same cost objective it uses to choose group assignments
- change package metadata to version `0.1.0` and remove unused runtime dependencies from the published install surface

### Deprecated

### Removed

### Fixed
- fix `infer_offset_from_sequences()` so scans with zero comparable pairs return `offset=None`, matching the public contract
- fix `make_canonicalizer()` to raise `ValueError` for missing fields, matching its documented contract
- fix `tool.mutmut.paths_to_mutate` to target `src/scohthwang`

### Security

## [0.0.0] - 2026-02-23

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
