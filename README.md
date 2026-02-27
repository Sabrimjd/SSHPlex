![SSHPlex Demo](demo/demo.gif)

**Multiplex your SSH connections with style**

SSHplex is a Python-based SSH connection multiplexer with a modern TUI. Connect to multiple hosts simultaneously using tmux or iTerm2, with sources from NetBox, Ansible, Consul, or static lists.

## Features

- 🖥️ **Modern TUI** - Textual-based host selector with search, sort, and multi-select
- 🔌 **Multiple Sources** - NetBox, Ansible, Consul, static lists - use them together
- 📦 **3 Mux Backends** - tmux standalone, tmux + iTerm2, or iTerm2 native (macOS)
- ✏️ **Config Editor** - Built-in YAML editor with validation 
- 🔄 **Broadcast Input** - Sync commands across multiple SSH sessions
- 🔐 **SSH Security** - Configurable host key checking and retry logic
- 🚀 **Fast Startup** - Intelligent caching with configurable TTL

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

- Python 3.8+
- tmux (Linux/macOS) and/or iTerm2 (macOS)
- SSH key configured for target hosts

## Multiplexer Backends

| Backend | Platform | Best For |
|---------|----------|----------|
| **tmux** | Linux, macOS | Maximum compatibility, persistence |
| **tmux + iTerm2** | macOS | Native UI + persistence |
| **iTerm2 native** | macOS | Simple setup, no tmux dependency |


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
