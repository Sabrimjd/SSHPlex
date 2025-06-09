![logo.png](https://raw.githubusercontent.com/sabrimjd/sshplex/master/.github/images/logo.png)

**Multiplex your SSH connections with style**

SSHplex is a Python-based SSH connection multiplexer that provides a modern Terminal User Interface (TUI) for selecting and connecting to multiple hosts simultaneously using tmux. Built with simplicity and extensibility in mind, SSHplex integrates with NetBox as a Source of Truth and creates organized tmux sessions for efficient multi-host management.

## ⚠️ Development Status

**SSHplex is currently in early development phase.** While the core functionality is working, this project is actively being developed and may have breaking changes between versions. Use at your own discretion in production environments.

## ✨ Features

### Current Features
- 🎯 **Interactive Host Selection**: Modern TUI built with Textual for intuitive host selection
- 🔗 **NetBox Integration**: Automatic host discovery from NetBox with configurable filters
- � **Ansible Integration**: Support for Ansible YAML inventories with group filtering
- 🏢 **Multiple Sources of Truth**: Use NetBox and Ansible inventories together or separately
- ���️ **tmux Integration**: Creates organized tmux sessions with panes or windows for each host
- ⚙️ **Flexible Configuration**: YAML-based configuration with automatic setup on first run
- 📁 **XDG Compliance**: Configuration stored in `~/.config/sshplex/` by default
- 🔧 **Multiple Layout Options**: Support for tiled, horizontal, and vertical tmux layouts
- 📊 **Broadcasting Support**: Sync input across multiple SSH connections (optional)
- 🎨 **Rich Terminal Output**: Beautiful, colored output with optional logging
- 🔍 **Host Filtering**: Search and filter hosts in the TUI interface
- 🏷️ **Group-based Filtering**: Filter hosts by Ansible groups or NetBox roles/clusters
- ✅ **SSH Key Authentication**: Secure key-based authentication support
- 🔄 **Provider Fallback**: Graceful handling when one SoT provider fails

### Planned Features
- 🔌 **Plugin Architecture**: Support for additional Sources of Truth and multiplexers
- 🏢 **Additional Sources of Truth**:
  - HashiCorp Consul integration
  - HashiCorp Bastion support
  - AWS EC2 instance discovery
  - Static YAML/JSON host files
- 🖥️ **Multiple Terminal Multiplexers**:
  - Terminator support
  - Hyper terminal integration
  - iTerm2 native support (macOS)
  - Custom multiplexer plugins
- 📈 **Performance Optimization**: Enhanced performance for large host lists

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install sshplex
```

This installs SSHplex with all its dependencies and makes the `sshplex` and `sshplex-cli` commands available system-wide.

### From Source

```bash
git clone https://github.com/yourusername/sshplex.git
cd sshplex
pip install -e .
```

### Development Setup

```bash
git clone https://github.com/yourusername/sshplex.git
cd sshplex
./scripts/setup-dev.sh
```

## �📋 Prerequisites

- **Python 3.8+**
- **tmux** (for terminal multiplexing)
- **NetBox** instance with API access (optional, if using NetBox provider)
- **Ansible inventory files** (optional, if using Ansible provider)
- **SSH key** configured for target hosts
- **macOS or Linux** (Windows support via WSL)

### System Dependencies

```bash
# macOS (using Homebrew)
brew install tmux python3

# Ubuntu/Debian
sudo apt update && sudo apt install tmux python3 python3-pip

# RHEL/CentOS/Fedora
sudo dnf install tmux python3 python3-pip
```

## 📸 Screenshots

### TUI Host Selection Interface

![host_lists.png](https://raw.githubusercontent.com/sabrimjd/sshplex/master/.github/images/host_lists.png)

### TUI Session manager

![session_manager.png](https://raw.githubusercontent.com/sabrimjd/sshplex/master/.github/images/session_manager.png)

### TMUX Session with Multiple SSH Connections

![tmux.png](https://raw.githubusercontent.com/sabrimjd/sshplex/master/.github/images/tmux.png)


## 🚀 Quick Start

### Option 1: Full TUI Interface (Recommended)
```bash
# Clone repository for full functionality
git clone https://github.com/sabrimjd/sshplex.git
cd sshplex

# Install in development mode
pip3 install -e .

# Run main TUI application
python3 sshplex.py
```

### Option 2: CLI Debug Interface (Pip Install)
```bash
# Install from PyPI (once published)
pip install sshplex

# Use CLI debug interface
sshplex-cli              # NetBox connectivity test
sshplex-cli --help       # Show help
```

## 🚀 Installation

### From PyPI (CLI Debug Interface)

```bash
pip install sshplex
```

This installs the `sshplex-cli` command for NetBox connectivity testing and configuration validation.

### From Source (Full TUI Application)

```bash
git clone https://github.com/sabrimjd/sshplex.git
cd sshplex
pip install -e .
```

This gives you access to the full TUI interface with tmux integration.

## 📖 Usage

### Basic Workflow

1. **Start SSHplex**: Run `python3 sshplex.py`
2. **Select Hosts**: Use the TUI to browse and select hosts from NetBox
3. **Configure Session**: Choose between panes or windows, enable/disable broadcasting
4. **Connect**: SSHplex creates a tmux session and establishes SSH connections
5. **Work**: Use tmux commands to navigate between hosts
6. **Detach/Reattach**: Use `Ctrl+b d` to detach, `tmux attach` to reattach

### tmux Commands (once attached)

```bash
# Navigation
Ctrl+b + Arrow Keys    # Switch between panes
Ctrl+b + n/p          # Next/Previous window
Ctrl+b + 0-9          # Switch to window by number

# Session management
Ctrl+b + d            # Detach from session
tmux list-sessions    # List all tmux sessions
tmux attach -t <name> # Attach to specific session

# Pane management
Ctrl+b + x            # Close current pane
Ctrl+b + z            # Zoom/unzoom current pane
```

## ⚙️ Configuration Options

### Source of Truth Providers

SSHplex supports multiple Sources of Truth that can be used together or separately:

#### NetBox Configuration

```yaml
sot:
  providers: ["netbox"]  # Use NetBox only

netbox:
  url: "https://netbox.example.com"
  token: "your-api-token"
  verify_ssl: true
  timeout: 30
  default_filters:
    status: "active"           # Only active hosts
    role: "virtual-machine"    # Only VMs
    platform: "linux"         # Only Linux hosts
    cluster: "production"      # Specific cluster
    has_primary_ip: "true"     # Only hosts with IP addresses
```

#### Ansible Inventory Configuration

```yaml
sot:
  providers: ["ansible"]  # Use Ansible only

ansible_inventory:
  inventory_paths:
    - "/path/to/inventory.yml"
    - "/path/to/production.yml"
    - "/path/to/staging.yml"
  default_filters:
    groups: ["web_servers", "db_servers"]  # Filter by groups
```

#### Using Both Providers

```yaml
sot:
  providers: ["netbox", "ansible"]  # Use both together

netbox:
  url: "https://netbox.example.com"
  token: "your-api-token"
  default_filters:
    status: "active"

ansible_inventory:
  inventory_paths:
    - "/etc/ansible/inventory.yml"
  default_filters:
    groups: ["production"]
```

### NetBox Filters

Customize which hosts are retrieved from NetBox:

```yaml
netbox:
  default_filters:
    status: "active"           # Only active hosts
    role: "virtual-machine"    # Only VMs
    platform: "linux"         # Only Linux hosts
    cluster: "production"      # Specific cluster
    has_primary_ip: "true"     # Only hosts with IP addresses
```

### Ansible Inventory Format

SSHplex supports standard Ansible YAML inventory files:

```yaml
# Example inventory.yml
all:
  children:
    production:
      children:
        web_servers:
          hosts:
            web1:
              ansible_host: 192.168.1.10
              ansible_user: ubuntu
              ansible_port: 2222
              environment: prod
            web2:
              ansible_host: 192.168.1.11
              ansible_user: ubuntu
              environment: prod
        db_servers:
          hosts:
            db1:
              ansible_host: 192.168.2.10
              ansible_user: postgres
              environment: prod
    staging:
      hosts:
        staging-web:
          ansible_host: 192.168.100.10
          ansible_user: ubuntu
          environment: staging
```

### Group Filtering

Filter hosts by Ansible groups or parent groups:

```yaml
ansible_inventory:
  default_filters:
    groups: ["production"]        # All hosts in production group
    # groups: ["web_servers"]     # Only web servers
    # groups: ["db_servers"]      # Only database servers
```

### tmux Layouts

Choose how SSH connections are arranged:

- `tiled`: Automatic tiling layout (default)
- `even-horizontal`: Horizontal split
- `even-vertical`: Vertical split

### Logging Control

```yaml
logging:
  enabled: false  # Disable logging completely
  level: "ERROR"  # Only show errors
  file: "logs/sshplex.log"
```

## 🐛 Troubleshooting

### Common Issues

1. **NetBox Connection Failed**
   - Verify URL and API token
   - Check network connectivity
   - Ensure SSL settings match your NetBox instance

2. **Ansible Inventory Not Loading**
   - Verify inventory file paths exist and are readable
   - Check YAML syntax with `yamllint` or similar tool
   - Ensure inventory files follow Ansible format
   - Verify group names in filters match inventory structure

3. **No Hosts Found After Filtering**
   - Check that group filters match existing groups in inventory
   - Verify NetBox filters match available hosts
   - Try removing filters temporarily to see all available hosts

4. **SSH Key Authentication Failed**
   - Verify SSH key path in configuration
   - Ensure key has proper permissions (`chmod 600`)
   - Test manual SSH connection to target hosts

5. **tmux Session Not Created**
   - Ensure tmux is installed and in PATH
   - Check SSH connectivity to at least one host
   - Verify tmux is not already running a session with the same name

6. **Mixed Provider Issues**
   - SSHplex continues with available providers if one fails
   - Check logs to see which providers initialized successfully
   - Ensure at least one provider is properly configured

### Debug Mode

Enable detailed logging for troubleshooting:

```yaml
logging:
  enabled: true
  level: "DEBUG"
  file: "logs/sshplex.log"
```

## 🤝 Contributing

SSHplex is in early development and welcomes contributions! Please note that the codebase follows the KISS (Keep It Simple, Stupid) principle.

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/sabrimjd/sshplex.git
cd sshplex/sshplex
pip3 install -r requirements-dev.txt

# Run tests
python3 -m pytest tests/

# Run with development configuration
python3 sshplex.py --config config-template.yaml
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Sabrimjd**
- GitHub: [@sabrimjd](https://github.com/sabrimjd)
- Project: [sshplex](https://github.com/sabrimjd/sshplex)

## 🙏 Acknowledgments

- Built with [Textual](https://textual.textualize.io/) for the modern TUI experience
- [NetBox](https://netbox.dev/) integration for infrastructure as code
- [tmux](https://github.com/tmux/tmux) for reliable terminal multiplexing
- [loguru](https://github.com/Delgan/loguru) for simple and powerful logging

---

**SSHplex** - Because managing multiple SSH connections should be simple and elegant.
