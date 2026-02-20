# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0] - 2026-02-20

### Added
- **Interactive onboarding wizard** (`sshplex --onboarding`) for first-time setup
  - Auto-detects SSH keys and system dependencies (tmux, etc.)
  - Guides through configuring inventory sources (NetBox, Ansible, Consul, static hosts)
  - Connection testing for each provider type before saving
  - Validates configuration with Pydantic and saves to `~/.config/sshplex/sshplex.yaml`
  - Intelligent fallback defaults when SSH keys not found
- Enhanced inventory connection logging with timing information
- Development runner script (`run.sh`) for quick local testing with venv setup

### Changed
- Improved error messages and validation in onboarding flow
- Better handling of missing python3-venv with helpful installation hints

---

## [1.3.0] - 2026-02-18

### Added
- TUI configuration editor (`e`) with 7 tabbed panes for editing sshplex.yaml directly from the app, including Pydantic validation and dynamic proxy/import lists.
- TUI keyboard shortcuts help modal (`h`) with contextual state hints.
- Parallel source-of-truth host loading path for faster multi-provider fetches.
- Detailed quality-upgrade summary document: `QUALITY_UPGRADE_SUMMARY.md`.

### Removed
- Quick filter modal (`f`) - use the search (`/`) instead for host filtering.

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
