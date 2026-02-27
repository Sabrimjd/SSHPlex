# Changelog

All notable changes to this project will be documented in this file.

## [1.6.2] - 2026-02-27

### Added
- tmux session manager now includes richer differentiation fields: broadcast state, pane count, session age, attached clients, and active command summary.
- Config editor adds table-column presets and a user-friendly shell-history registration toggle for iTerm2-native mode.

### Changed
- tmux and iTerm2 session manager modals now use larger responsive sizing for better visibility on real terminals.
- Demo GIF refreshed and compressed for lighter README/demo usage.

### Fixed
- Resolved tmux session manager reliability regressions for kill/broadcast/refresh actions.
- Improved libtmux compatibility for pane splitting across deprecated/new API variants.
- Suppressed benign iTerm2 websocket shutdown noise during mode switching.
- Config editor now saves and hot-reloads the active `--config` file path instead of always targeting the default config.
- Tightened settings validation and select safety to avoid crashes from invalid config values.

## [1.6.1] - 2026-02-26

### Added
- Demo assets for local multi-provider testing: `demo/docker-compose.consul-demo.yml`, `demo/seed-consul-demo.sh`, `demo/ansible-inventory-demo.yml`, and `demo/sshplex.demo.yaml`.

### Fixed
- iTerm2 native now preserves duplicate targets in queue (multiple hosts with same IP no longer collapse to one tab/pane).
- Connection routing now separates display label from SSH target to support same-IP hosts with distinct names.
- tmux pane creation compatibility with newer libtmux by using `Window.split()` fallback logic.
- tmux session manager compatibility and key handling regressions (`k`, `b`, `r`, refresh/session lookup/kill reliability).
- Config editor no longer crashes on invalid select values in config (safe defaults applied in UI).
- Connection summary now reports real success count (`X/Y`) instead of always showing selected host count.

## [1.6.0] - 2026-02-26

### Added
- iTerm2 native backend target selection with `tmux.iterm2_native_target` (`current-window` or `new-window`).
- iTerm2 native tab manager in the TUI (`s`) with refresh and kill actions for SSHplex-managed tabs.
- Kill-all shortcut for current native session in iTerm2 tab manager (`Shift+K`).
- New `tmux.iterm2_native_hide_from_history` option (default `true`) to prefix dispatched commands with a leading space.

### Changed
- Native iTerm2 mode now keeps SSHplex open after connecting, so additional sessions can be launched without restarting.
- Config editor now hot-reloads at runtime and applies updated UI/mux settings without restarting SSHplex.
- General settings layout consolidated (UI, Logging, and Cache sections moved under General).
- Improved status line to show backend target and in-progress connection state.

### Fixed
- iTerm2 native startup no longer passes shell command strings to iTerm2 `command=`, fixing `execvp` launch failures.
- Added robust tab/session recovery logic for iTerm2 native to avoid blank panes and missing first-session cases.
- Fixed iTerm2 native split/session delegate initialization issues that caused assertion errors.
- Fixed tabs mode honoring `use_panes: false` and preserving mode through config saves.
- Fixed iTerm2 native tab naming (tab title and session name now aligned with hostnames).
- Fixed session-manager Enter key leakage and event-loop crashes during iTerm2 tab kill flows.
- Improved iTerm2 native broadcast setup reliability in tab-heavy sessions by re-resolving session objects before enabling broadcast.

## [1.5.0] - 2026-02-25

### Security
- **SSH command injection prevention** with `shlex.quote()` for all user-controlled values
- Input validation for usernames, hostnames, and proxy credentials (regex-based)
- Absolute path requirement for SSH keys to prevent directory traversal
- Pane title sanitization in tmux to prevent escape sequence injection
- **Consul SSL verification now enabled by default** (breaking change: `verify: False` → `True`)

### Changed
- Refactored SoTFactory to remove ~50 lines of code duplication
- Improved proxy credential validation before use in SSH commands

---

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
