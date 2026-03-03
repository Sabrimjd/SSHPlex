![SSHPlex Demo](demo/demo.gif)

**Multiplex your SSH connections with style**

SSHplex is a Python-based SSH connection multiplexer with a modern TUI. Connect to multiple hosts simultaneously using tmux or iTerm2, with sources from NetBox, Ansible, Consul, or static lists.

## Features

- 🖥️ **Modern TUI** - Textual-based host selector with search, sort, and multi-select
- 🔌 **Multiple Sources** - NetBox, Ansible, Consul, static lists - use them together
- 📦 **3 Mux Backends** - tmux standalone, tmux + iTerm2, or iTerm2 native (macOS)
- ✏️ **Config Editor** - Built-in editor with compact source cards, static host rows, and full YAML pane
- 🔄 **Broadcast Input** - Sync commands across multiple SSH sessions
- 🔐 **SSH Security** - Configurable host key checking and retry logic
- 🚀 **Fast Startup** - Intelligent caching with configurable TTL

## What Is New in QoL v2

- **Static host manager in UI** - Add and edit static hosts as rows (`name`, `ip`, `alias`, `user`, `port`, `key_path`) instead of raw YAML blobs.
- **Per-host SSH preview** - Preview effective SSH values from `ssh -G` in settings and from host selector (`o`).
- **Smarter table columns** - Detect columns from live hosts/cache/imports, including SSH-oriented fields like `alias`, `user`, `port`, and `key_path`.
- **Better Sources UX** - Provider toggles and collapsible import cards make large source configs easier to navigate.
- **Rich YAML view** - Side-by-side YAML edit + syntax-highlight preview for full config inspection.

## Quick Start

```bash
# Install
pip install sshplex

# First-time setup (interactive wizard)
sshplex --onboarding

# Launch TUI
sshplex
```

### Prerequisites

- Python 3.10+
- tmux (Linux/macOS) and/or iTerm2 (macOS)
- SSH key configured for target hosts

## Multiplexer Backends

| Backend | Platform | Best For |
|---------|----------|----------|
| **tmux** | Linux, macOS | Maximum compatibility, persistence |
| **tmux + iTerm2** | macOS | Native UI + persistence |
| **iTerm2 native** | macOS | Simple setup, no tmux dependency |

## Sources of Truth

| Provider | `type` | Extra Dependency | Best For |
|----------|--------|------------------|----------|
| **Static** | `static` | None | Small lists, lab hosts, quick manual entries |
| **NetBox** | `netbox` | None (included in base install) | Inventory-driven infrastructure with metadata |
| **Ansible** | `ansible` | None | Reusing existing Ansible inventory files |
| **Consul** | `consul` | `pip install "sshplex[consul]"` | Service discovery and dynamic node catalogs |
| **Git** | `git` | `git` binary in PATH | Git-backed inventories with auto-pull (`static` or `ansible` YAML) |

Provider activation is controlled by `sot.providers`, and each source is configured as an item in `sot.import`.

Use multiple `git` imports and tune `priority` for deterministic overrides.


## Local Demo (Consul + Ansible)

This repo includes a small demo setup that uses the same IP (`192.168.31.216`) with different host names.

```bash
# Start Consul + seed 3 demo nodes
docker compose -f demo/docker-compose.consul-demo.yml up -d

# Optional: inspect nodes
curl -s http://localhost:8500/v1/catalog/nodes | jq
```

Demo files:
- `demo/ansible-inventory-demo.yml`
- `demo/docker-compose.consul-demo.yml`
- `demo/sshplex.demo.yaml`

Run with the bundled demo config:

```bash
sshplex --config demo/sshplex.demo.yaml
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Configuration](docs/configuration.md) | Full config reference with examples |
| [Backends](docs/backends.md) | Multiplexer backend options and setup |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and solutions |

## TUI Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Connect to selected hosts |
| `Space` | Toggle host selection |
| `s` | Open session manager |
| `S` | Open snippets picker and send command |
| `H` | Run host health checks |
| `f` | Toggle favorite on current host |
| `v` | Toggle favorites filter |
| `n` | Toggle recent-hosts filter |
| `r` | Refresh hosts from sources |
| `h` | Open in-app help |

## Installation Options

```bash
# Basic (tmux only)
pip install sshplex

# With Consul,DEV,Iterm2 support
pip install "sshplex[dev,consul,iterm2]"
```

## Development

```bash
git clone https://github.com/sabrimjd/sshplex.git
cd sshplex
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Quality checks
ruff check sshplex tests
mypy sshplex
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Sabrimjd** - [@sabrimjd](https://github.com/sabrimjd)

---

**SSHplex** - Because managing multiple SSH connections should be simple.
