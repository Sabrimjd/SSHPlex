# Multiplexer Backends

SSHplex supports **3 multiplexer backends** for different use cases and platforms.

## Backend Comparison

| Backend | Config | Platform | Dependency | Persistence |
|---------|--------|----------|------------|-------------|
| **tmux standalone** | `backend: tmux` | Linux, macOS | tmux | tmux session |
| **tmux + iTerm2** | `backend: tmux` + `control_with_iterm2: true` | macOS | tmux + iTerm2 | tmux session |
| **iTerm2 native** | `backend: iterm2-native` | macOS | iTerm2 | iTerm2 window |

## 1. tmux Standalone

Pure tmux with no external terminal integration. Works on Linux and macOS.

```yaml
tmux:
  backend: "tmux"
  control_with_iterm2: false
  layout: "tiled"
  max_panes_per_window: 5
```

**Features:**
- Works everywhere tmux runs
- Full tmux feature set
- Session persistence (reattach after disconnect)

**tmux Commands:**
| Shortcut | Action |
|----------|--------|
| `Ctrl+b + Arrow` | Switch panes |
| `Ctrl+b + n/p` | Next/Previous window |
| `Ctrl+b + b` | Toggle broadcast (SSHplex custom) |
| `Ctrl+b + d` | Detach from session |
| `Ctrl+b + z` | Zoom/unzoom pane |

## 2. tmux + iTerm2 (macOS)

tmux with iTerm2's native UI via `-CC` control mode. Best of both worlds.

```yaml
tmux:
  backend: "tmux"
  control_with_iterm2: true
  iterm2_attach_target: "new-tab"
  iterm2_profile: "Default"
```

**iTerm2 Settings Required:**

1. Open **iTerm2 → Settings → General → tmux**
2. Set **"When attaching, restore windows as:"** to **"Tabs in the attaching window"**

**Features:**
- Native macOS UI (fonts, scrolling, copy/paste)
- Session persistence via tmux
- iTerm2's search (`Cmd+F`)
- Native split panes

**Understanding the 3-Tab Layout:**

| Tab | Purpose |
|-----|---------|
| **Controller** | tmux control menu (press `esc` to detach) |
| **Tmux Pane** | SSH session (text-based rendering) |
| **iTerm2 Native** | SSH session (native rendering) |

The **Tmux Pane** and **iTerm2 Native** tabs show the same session - you can close either one.

**Keyboard Shortcuts:**
| Shortcut | Action |
|----------|--------|
| `esc` (controller) | Detach cleanly |
| `X` (controller) | Force-quit tmux mode |
| `Cmd+W` | Close tab |
| `Cmd+D` | Split pane |

## 3. iTerm2 Native (macOS only)

Pure iTerm2 Python API with no tmux dependency. Best for simple use cases.

```yaml
tmux:
  backend: "iterm2-native"
  use_panes: true
  iterm2_native_target: "current-window"  # current-window, new-window
  iterm2_profile: "Default"
  iterm2_split_pattern: "alternate"  # alternate, vertical, horizontal
  iterm2_native_hide_from_history: true
  max_panes_per_window: 5
```

**Installation:**
```bash
pip install "sshplex[iterm2]"
```

**Features:**
- No tmux dependency
- Native iTerm2 tabs and splits
- Real broadcast input via iTerm2 broadcast domains
- SSHplex-controlled tab/session naming
- Open in current iTerm2 window or dedicated new window
- iTerm2 tab manager from SSHplex (`s`) to refresh/kill managed native tabs

**Naming Convention:**
| Element | Format | Example |
|---------|--------|---------|
| Window | `SSHplex: <session>` | `SSHplex: sshplex-20260226` |
| Tab | `<hostname>` | `web-server-01` |
| Session | `<hostname>` | `web-server-01` |

**Broadcast Control:**
- iTerm2 native uses real broadcast domains
- Toggle with iTerm2's `Cmd+Option+I` shortcut
- Or enable in config: `broadcast: true`

**Shell History Behavior:**
- By default, SSHplex prefixes native dispatched commands with a leading space (`iterm2_native_hide_from_history: true`).
- This works when your shell is configured to ignore commands starting with a space (for example: `HIST_IGNORE_SPACE` in zsh or `HISTCONTROL=ignorespace` in bash).

## Choosing a Backend

| Use Case | Recommended Backend |
|----------|---------------------|
| Linux server | tmux standalone |
| macOS, want persistence | tmux + iTerm2 |
| macOS, simple use | iTerm2 native |
| Multiple environments | tmux standalone |

## See Also

- [Configuration Guide](configuration.md) - Full config reference
- [Troubleshooting](troubleshooting.md) - Backend-specific issues
