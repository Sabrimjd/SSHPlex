# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2026-02-18

### Added
- TUI quick filter modal (`f`) with wildcard matching for host name/IP.
- TUI keyboard shortcuts help modal (`h`) with contextual state hints.
- Parallel source-of-truth host loading path for faster multi-provider fetches.
- Detailed quality-upgrade summary document: `QUALITY_UPGRADE_SUMMARY.md`.

### Changed
- iTerm2 integration behavior and messaging improved for clearer install/running-state detection and fallback guidance.
- Cache validity checks optimized with faster pre-check path before full metadata parse.
- TUI selection rendering polished for better readability and accessibility.
- Main runtime and config-loading error handling improved.

### Fixed
- Validation hardening for config and connection inputs (e.g., username, host presence, port ranges).
- Better handling of empty/invalid config and permission-related file errors.
- Cleaner main entrypoint signal/error handling and production logging behavior.

---

## [1.2.0] - Previous
- Existing feature baseline before quality-upgrade cycle.
