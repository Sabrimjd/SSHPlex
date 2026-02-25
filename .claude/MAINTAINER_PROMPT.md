# SSHPlex Maintainer Context

## Project Overview
**SSHPlex** is a Python-based SSH connection multiplexer with a modern TUI (Textual). It integrates with multiple Sources of Truth (NetBox, Ansible, Consul, static lists) and creates organized tmux sessions for multi-host management.

- **Repo:** https://github.com/Sabrimjd/SSHPlex
- **Local Path:** `/home/sab/projects/SSHPlex`
- **Current Version:** 1.4.0
- **Python:** 3.8+ (tested on 3.10, 3.11, 3.12, 3.13)
- **License:** MIT

## Architecture
```
sshplex/
├── main.py              # Entry point
├── cli.py               # CLI argument parsing
├── sshplex_connector.py # SSH connection logic
├── lib/
│   ├── config.py        # Pydantic config models
│   ├── sot/             # Sources of Truth (NetBox, Ansible, Consul, static)
│   │   └── factory.py   # Aggregates hosts from all providers
│   └── multiplexer/
│       └── tmux.py      # tmux session management
└── tui/                 # Textual TUI components
```

## CI/CD Pipeline
**Workflow:** `.github/workflows/ci.yml`

**Triggers:**
- Push to any branch
- PRs to `main` or `develop`

**Jobs:**
1. **test** (matrix: Python 3.10, 3.11, 3.12, 3.13)
   - `ruff check sshplex tests` (linting)
   - `mypy sshplex --ignore-missing-imports` (type checking)
   - `pytest tests/ -v` (unit tests)
2. **build** (after test passes)
   - Build package with `python -m build`
   - Check with `twine check dist/*`

**Current Test Count:** 120 tests

## Versioning
- Version defined in `pyproject.toml` → `[project].version`
- No automated versioning - manual bumps
- Semantic versioning (MAJOR.MINOR.PATCH)

## Code Quality Tools
| Tool | Config | Purpose |
|------|--------|---------|
| ruff | `[tool.ruff]` | Linting (E, F, I, B, UP, SIM rules) |
| mypy | `[tool.mypy]` | Type checking (strict mode) |
| pytest | `[tool.pytest]` | Unit tests |
| vulture | `[tool.vulture]` | Dead code detection |

## Key Dependencies
- **textual** (8.0.0) - TUI framework
- **pynetbox** (7.6.1) - NetBox API
- **pydantic** (2.12.5) - Config validation
- **libtmux** (0.53.1) - tmux automation
- **python-consul2** (optional) - Consul support

## Common Maintenance Tasks

### Running Tests Locally
```bash
cd /home/sab/projects/SSHPlex
pip install -e ".[dev]"
pytest tests/ -v
```

### Quality Checks
```bash
ruff check sshplex tests
mypy sshplex --ignore-missing-imports
vulture sshplex tests --min-confidence 80
```

### Building Package
```bash
python -m build
twine check dist/*
```

### Checking PR Status
```bash
gh pr list --state open
gh pr view <number> --json title,state,mergeable,statusCheckRollup
```

## Security Considerations
- SSH command injection prevention via `shlex.quote()` and regex validation
- Input validation on usernames, hostnames, proxy credentials
- Absolute path requirement for SSH keys
- SSL verification enabled by default for Consul

## Release Process (Manual)
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite + quality checks
4. Merge to `main`
5. Tag release: `git tag v1.x.x && git push --tags`
6. GitHub Actions handles PyPI publish (if configured)

## Useful Commands
```bash
# View open PRs with CI status
gh pr list --state open --json number,title,mergeable,statusCheckRollup

# Check specific PR
gh pr view 28 --json title,state,mergeable,reviewDecision

# Get PR diff for review
gh pr diff <number>

# Run CI locally (simulate)
pytest tests/ -v && ruff check sshplex tests && mypy sshplex
```

## Notes
- PRs require passing CI on all 4 Python versions
- Codex auto-reviews PRs when opened/ready
- Consul support is optional (`pip install "sshplex[consul]"`)
- iTerm2 integration available on macOS (`tmux.control_with_iterm2: true`)
