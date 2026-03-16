# Mission: Implement 3 New Features for SSHPlex

## M1: Feature 1 - Command Snippets | status:in_progress
### T1.1: Create snippets module | agent:Worker
- [ ] S1.1.1: Create sshplex/lib/snippets.py with Snippet dataclass | size:M
- [ ] S1.1.2: Implement SnippetManager class with load/save | size:M
- [ ] S1.1.3: Add default snippets on first run | size:S

### T1.2: Add snippets to config | agent:Worker
- [ ] S1.2.1: Add SnippetsConfig to config.py | size:S
- [ ] S1.2.2: Update Config model | size:S
- [ ] S1.2.3: Add snippets.enabled and snippets.show_preview | size:S

### T1.3: Add snippets UI to TUI | agent:Worker
- [ ] S1.3.1: Add 'S' key binding in host_selector | size:S
- [ ] S1.3.2: Create snippet picker modal | size:L
- [ ] S1.3.3: Implement broadcast/preview logic | size:M
- [ ] S1.3.4: Add visual feedback when command sent | size:S

### T1.4: Verify snippets feature | agent:Reviewer
- [ ] S1.4.1: Run ruff check | size:S
- [ ] S1.4.2: Run mypy | size:S
- [ ] S1.4.3: Test snippets functionality | size:M

## M2: Feature 2 - Host Health Check | status:pending
### T2.1: Create health module | agent:Worker
- [ ] S2.1.1: Create sshplex/lib/health.py | size:M
- [ ] S2.1.2: Implement HealthStatus enum | size:S
- [ ] S2.1.3: Add async check_host function | size:M

### T2.2: Add health to config | agent:Worker
- [ ] S2.2.1: Add HealthConfig to config.py | size:S
- [ ] S2.2.2: Add health.enabled, health.timeout, health.cache_ttl_minutes | size:S

### T2.3: Add health UI to TUI | agent:Worker
- [ ] S2.3.1: Add Status column to table | size:S
- [ ] S2.3.2: Add 'H' key binding for health check | size:S
- [ ] S2.3.3: Add progress indicator | size:M
- [ ] S2.3.4: Implement result caching with TTL | size:M

### T2.4: Verify health feature | agent:Reviewer
- [ ] S2.4.1: Run ruff check | size:S
- [ ] S2.4.2: Run mypy | size:S
- [ ] S2.4.3: Test health check functionality | size:M

## M3: Feature 3 - Recent & Favorites | status:pending
### T3.1: Create history module | agent:Worker
- [ ] S3.1.1: Create sshplex/lib/history.py | size:M
- [ ] S3.1.2: Implement HistoryManager class | size:M
- [ ] S3.1.3: Add recent connections tracking | size:S
- [ ] S3.1.4: Add favorites management | size:S

### T3.2: Add history to config | agent:Worker
- [ ] S3.2.1: Add HistoryConfig to config.py | size:S
- [ ] S3.2.2: Add history.enabled, history.max_recent, history.remember_favorites | size:S

### T3.3: Add history UI to TUI | agent:Worker
- [ ] S3.3.1: Add Recent filter/tab | size:M
- [ ] S3.3.2: Add 'F' key binding for favorites | size:S
- [ ] S3.3.3: Add 'V' key for favorites filter | size:S
- [ ] S3.3.4: Add star icon for favorites | size:S
- [ ] S3.3.5: Auto-add to recent on connect | size:S

### T3.4: Verify history feature | agent:Reviewer
- [ ] S3.4.1: Run ruff check | size:S
- [ ] S3.4.2: Run mypy | size:S
- [ ] S3.4.3: Test history functionality | size:M

## M4: Quality & Documentation | status:pending
### T4.1: Add tests | agent:Worker
- [ ] S4.1.1: Add tests for snippets module | size:M
- [ ] S4.1.2: Add tests for health module | size:M
- [ ] S4.1.3: Add tests for history module | size:M

### T4.2: Update documentation | agent:Worker
- [ ] S4.2.1: Update CHANGELOG.md | size:S
- [ ] S4.2.2: Update README.md with new keybindings | size:M

### T4.3: Final verification | agent:Reviewer
- [ ] S4.3.1: Run full ruff check | size:S
- [ ] S4.3.2: Run full mypy | size:S
- [ ] S4.3.3: Run pytest | size:S

## M5: Create PR | status:pending
### T5.1: Create pull request | agent:Worker
- [ ] S5.1.1: Commit all changes | size:S
- [ ] S5.1.2: Push branch | size:S
- [ ] S5.1.3: Create PR | size:S
