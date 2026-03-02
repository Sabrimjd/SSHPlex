# Troubleshooting

## Debug Mode

Test provider connectivity and list all discovered hosts:

```bash
sshplex --debug
```

## Enable Logging

```yaml
logging:
  enabled: true
  level: "DEBUG"
  file: "logs/sshplex.log"
```

## Common Issues

### tmux Issues

| Issue | Solution |
|-------|----------|
| `tmux is not installed` | `brew install tmux` (macOS) or `apt install tmux` (Linux) |
| Session already exists | Use session manager (`s` key) to kill or attach |
| Broadcast not working | Press `Ctrl+b + b` to toggle, or check `broadcast: true` in config |
| Panes too small | Reduce `max_panes_per_window` or use larger terminal |

### iTerm2 Issues

| Issue | Solution |
|-------|----------|
| iTerm2 not detected | Ensure iTerm2 is running and Python API is enabled in preferences |
| `-CC` mode not working | Check iTerm2 → Settings → General → tmux settings |
| 3 tabs confusing | Close "Tmux Pane" tab, use "iTerm2 Native" tab |
| Broadcast toggle not working | Use iTerm2's native `Cmd+Option+I` shortcut |

### iTerm2 Native Backend

| Issue | Solution |
|-------|----------|
| `iTerm2 Python API not installed` | `pip install "sshplex[iterm2]"` |
| Connection refused / Connect call failed | Enable Python API in iTerm2 Settings → General → Magic |
| Broadcast not working | Press `Cmd+Option+I` or set `broadcast: true` |
| Tabs open in a new window unexpectedly | Set `tmux.iterm2_native_target: current-window` |
| SSH command appears in shell history | Keep `iterm2_native_hide_from_history: true` and configure shell ignorespace |
| Session manager shows no native tabs | Recreate sessions after upgrading (only SSHplex-managed tabs are listed) |

**Enabling iTerm2 Python API:**
1. Open iTerm2
2. Go to **iTerm2 → Settings → General → Magic**
3. Enable **"Python API"**
4. Restart iTerm2

### Provider Issues

| Issue | Solution |
|-------|----------|
| NetBox connection failed | Check URL, token, and network connectivity |
| Ansible inventory not loading | Verify file paths exist and YAML syntax is valid |
| Import configured but hosts never appear | Ensure import `type` is enabled in `sot.providers` (or leave providers empty to auto-infer from imports) |
| No hosts found | Remove filters temporarily, check provider logs |
| Consul import error | Install with `pip install "sshplex[consul]"` |
| Git import clone/pull fails | Verify `git` is installed, repo URL/auth, and branch exists |
| Git source is stale | Press `r` in the TUI to sync git and refresh providers |
| Git + Ansible repo loads no hosts | Set `inventory_format: ansible` and ensure hosts define `ansible_host` |

### SSH Issues

| Issue | Solution |
|-------|----------|
| SSH key auth failed | Check key path and permissions (`chmod 600`) |
| Connection timeout | Increase `timeout` value or check network |
| Host key verification failed | Set `strict_host_key_checking: false` for testing |
| Jump host not working | Verify proxy config and key permissions |

### Config Editor Issues

| Issue | Solution |
|-------|----------|
| Validation error | Check field types (string vs number) and required fields |
| Config not saving | Check file permissions on `~/.config/sshplex/` |
| Changes not applied | Most settings hot-reload; reconnect existing SSH sessions for connection-level changes |

## Diagnostic Commands

```bash
# Show config paths and status
sshplex --show-config

# Clear host cache
sshplex --clear-cache

# Test with verbose logging
sshplex --debug --verbose

# Check tmux sessions
tmux list-sessions

# Kill all SSHplex sessions
tmux kill-session -t sshplex 2>/dev/null || true
tmux list-sessions | grep sshplex | cut -d: -f1 | xargs -I{} tmux kill-session -t {}
```

## Log Locations

| Platform | Location |
|----------|----------|
| Config | `~/.config/sshplex/sshplex.yaml` |
| Cache | `~/.cache/sshplex/` |
| Logs | `logs/sshplex.log` (relative to CWD) |

## Getting Help

1. Run `sshplex --debug` and check output
2. Enable DEBUG logging and check log file
3. Check [GitHub Issues](https://github.com/Sabrimjd/SSHPlex/issues)
4. Open a new issue with debug output and config (redact sensitive data)

## See Also

- [Configuration Guide](configuration.md) - Full config reference
- [Backends Guide](backends.md) - Multiplexer options
