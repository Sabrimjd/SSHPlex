# Configuration Guide

SSHplex configuration is stored at `~/.config/sshplex/sshplex.yaml`. You can edit it directly or use the built-in config editor (press `e` in the TUI).

## Quick Start

Run `sshplex --onboarding` for an interactive setup wizard that will:
- Auto-detect your SSH keys and system dependencies
- Guide you through configuring inventory sources (including Git)
- Let you choose backend on macOS (tmux or iTerm2 native)
- Test connections before saving

## Config Editor (Built-in)

Press `e` in the TUI to open the configuration editor with:
- **5 tabbed sections**: General, SSH, Mux, Sources, Config YAML
- **Grouped sections in General**: SSHplex, UI, Logging, Cache
- **Dynamic lists**: Add/remove proxies and imports
- **Validation**: Pydantic validation before saving
- **Auto-reload**: Changes are applied live after saving

## Configuration Sections

### General

```yaml
sshplex:
  session_prefix: "sshplex"  # Prefix for tmux session names
```

### SSH

```yaml
ssh:
  username: "admin"
  key_path: "~/.ssh/id_ed25519"
  timeout: 10
  port: 22

  # Security options
  strict_host_key_checking: false  # true (strict), false (accept-new)
  user_known_hosts_file: ""       # Empty = default ~/.ssh/known_hosts

  # Connection retry
  retry:
    enabled: true
    max_attempts: 3
    delay_seconds: 2
    exponential_backoff: true
```

### Tmux / Multiplexer

```yaml
tmux:
  backend: "tmux"              # "tmux" or "iterm2-native" (macOS only)
  use_panes: true               # true = panes, false = tabs
  layout: "tiled"              # tiled, even-horizontal, even-vertical
  broadcast: false             # Start with broadcast enabled
  window_name: "sshplex"
  max_panes_per_window: 5      # Max panes before creating new tab

  # iTerm2 integration (macOS, backend=tmux)
  control_with_iterm2: false   # Enable iTerm2 -CC mode
  iterm2_attach_target: "new-window"  # "new-window" or "new-tab"
  iterm2_profile: "Default"

  # iTerm2 native (macOS, backend=iterm2-native)
  iterm2_native_target: "current-window"  # current-window, new-window
  iterm2_split_pattern: "alternate"  # alternate, vertical, horizontal
  iterm2_native_hide_from_history: true  # prefix command with leading space
```

### Sources of Truth

#### Provider Overview

| Provider | `type` | Activation | Required Fields |
|----------|--------|------------|-----------------|
| Static | `static` | Add `static` to `sot.providers` | `hosts` |
| NetBox | `netbox` | Add `netbox` to `sot.providers` | `url`, `token` |
| Ansible | `ansible` | Add `ansible` to `sot.providers` | `inventory_paths` |
| Consul | `consul` | Add `consul` to `sot.providers` | `config.host`, `config.token` |
| Git | `git` | Add `git` to `sot.providers` | `repo_url` |

Only imports whose `type` is listed in `sot.providers` are loaded.

```yaml
sot:
  providers: ["static", "netbox", "ansible", "consul", "git"]
```

#### Static Hosts

```yaml
sot:
  import:
    - name: "my-servers"
      type: static
      hosts:
        - name: "web-01"
          ip: "192.168.1.10"
          description: "Web server"
          tags: ["web", "production"]
        - name: "db-01"
          ip: "192.168.1.20"
          description: "Database server"
          tags: ["database", "production"]
```

#### NetBox

```yaml
sot:
  import:
    - name: "prod-netbox"
      type: netbox
      url: "https://netbox.example.com/"
      token: "your-api-token"
      verify_ssl: true
      timeout: 30
      default_filters:
        status: "active"
        role: "virtual-machine"
        has_primary_ip: "true"
```

#### Ansible Inventory

```yaml
sot:
  import:
    - name: "production-hosts"
      type: ansible
      inventory_paths:
        - "/path/to/inventory.yml"
      default_filters:
        groups: ["webservers", "databases"]
        exclude_groups: ["maintenance"]
```

#### Consul

Requires `pip install "sshplex[consul]"`.

```yaml
sot:
  import:
    - name: "consul-dc1"
      type: consul
      config:
        host: "consul.example.com"
        port: 443
        token: "your-consul-token"
        scheme: "https"
        verify: true
        dc: "dc1"
```

#### Git

Use git-backed inventory for solo or shared host catalogs. SSHplex keeps a local mirror under `~/.cache/sshplex/git` and can auto-pull updates.

`source_pattern` combines path + glob in one field, for example `hosts/**/*.y*ml`.

`inventory_format` supports:
- `static` (default): static host rows (`name` + `ip`)
- `ansible`: Ansible YAML inventory trees (`all/children/hosts`)

```yaml
sot:
  providers: ["git", "static"]
  import:
    - name: "personal-hosts"
      type: git
      repo_url: "git@github.com:your-user/sshplex-hosts.git"
      branch: "main"
      source_pattern: "hosts/**/*.y*ml"
      inventory_format: "static"
      auto_pull: true
      pull_interval_seconds: 300
      profile: "solo"
      priority: 100
      pull_strategy: "ff-only"
```

Git + Ansible remote inventory example (read-only):

```yaml
sot:
  providers: ["git"]
  import:
    - name: "team-ansible"
      type: git
      repo_url: "git@github.com:org/ansible-inventory.git"
      branch: "main"
      source_pattern: "inventory/**/*.y*ml"
      inventory_format: "ansible"
      default_filters:
        groups: ["webservers", "databases"]
      auto_pull: true
      pull_interval_seconds: 300
      profile: "team"
      priority: 50
      pull_strategy: "ff-only"
```

Team-ready layering example (same provider type, different imports):

```yaml
sot:
  providers: ["git"]
  import:
    - name: "team-hosts"
      type: git
      repo_url: "git@github.com:org/team-hosts.git"
      profile: "team"
      priority: 50
    - name: "my-overrides"
      type: git
      repo_url: "git@github.com:you/my-hosts.git"
      profile: "solo"
      priority: 100
```

In host selector:
- `r` forces git pull for git imports, then refreshes all providers

### SSH Proxy / Jump Host

Configure per-provider proxy routing:

```yaml
ssh:
  proxy:
    - name: "prod-proxy"
      imports: ["consul-dc1", "prod-netbox"]  # Which providers use this proxy
      host: "jumphost.example.com"
      username: "admin"
      key_path: "~/.ssh/jump_key"
```

### UI

```yaml
ui:
  show_log_panel: false
  log_panel_height: 20  # Percentage
  table_columns: ["name", "ip", "cluster", "role", "tags"]
```

### Logging

```yaml
logging:
  enabled: true
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/sshplex.log"
```

### Cache

```yaml
cache:
  enabled: true
  cache_dir: "~/.cache/sshplex"
  ttl_hours: 24  # Refresh daily
```

## Security Best Practices

1. **Host Key Checking**: For production, set `strict_host_key_checking: true`
2. **API Tokens**: Store sensitive tokens in environment variables
3. **File Permissions**: Keep config file readable only by you (`chmod 600`)
4. **SSH Keys**: Use ed25519 keys with passphrases

## Hot Reload Notes

- Most TUI-visible settings reload immediately after saving in the config editor.
- Changes affecting active SSH sessions (for example, existing iTerm2 tabs/panes) apply to new connections, not already-open sessions.

## Environment Variables

SSHplex respects these environment variables:

| Variable | Description |
|----------|-------------|
| `SSHPLEX_CONFIG` | Custom config file path |
| `SSHPLEX_CACHE_DIR` | Override cache directory |
| `SSHPLEX_LOG_LEVEL` | Override log level |

## See Also

- [Backends Guide](backends.md) - Multiplexer backend options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
