# SSHplex

**Multiplex your SSH connections with style**

SSHplex is a Python-based SSH connection multiplexer that provides a modern Terminal User Interface (TUI) for selecting and connecting to multiple hosts simultaneously using tmux. Built with simplicity and extensibility in mind, SSHplex integrates with NetBox as a Source of Truth and creates organized tmux sessions for efficient multi-host management.

## ⚠️ Development Status

**SSHplex is currently in early development phase.** While the core functionality is working, this project is actively being developed and may have breaking changes between versions. Use at your own discretion in production environments.

## ✨ Features

### Current Features
- 🎯 **Interactive Host Selection**: Modern TUI built with Textual for intuitive host selection
- 🔗 **NetBox Integration**: Automatic host discovery from NetBox with configurable filters
- 🖥️ **tmux Integration**: Creates organized tmux sessions with panes or windows for each host
- ⚙️ **Flexible Configuration**: YAML-based configuration with automatic setup on first run
- 📁 **XDG Compliance**: Configuration stored in `~/.config/sshplex/` by default
- 🔧 **Multiple Layout Options**: Support for tiled, horizontal, and vertical tmux layouts
- 📊 **Broadcasting Support**: Sync input across multiple SSH connections (optional)
- 🎨 **Rich Terminal Output**: Beautiful, colored output with optional logging
- 🔍 **Host Filtering**: Search and filter hosts in the TUI interface
- ✅ **SSH Key Authentication**: Secure key-based authentication support

### Planned Features
- 🔌 **Plugin Architecture**: Support for additional Sources of Truth and multiplexers
- 🏢 **Multiple Sources of Truth**:
  - HashiCorp Consul integration
  - HashiCorp Bastion support
  - AWS EC2 instance discovery
  - Ansible inventory integration
  - Static YAML/JSON host files
- 🖥️ **Multiple Terminal Multiplexers**:
  - Terminator support
  - Hyper terminal integration
  - iTerm2 native support (macOS)
  - Custom multiplexer plugins
- 📈 **Performance Optimization**: Enhanced performance for large host lists

## 📋 Prerequisites

- **Python 3.8+**
- **tmux** (for terminal multiplexing)
- **NetBox** instance with API access
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

*Screenshots will be added as the UI stabilizes during development*

### TUI Host Selection Interface
```
Coming soon - Interactive host selection with search and filtering
```

### tmux Session with Multiple SSH Connections
```
Coming soon - Organized tmux layout with multiple host connections
```

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/sabrimjd/sshplex.git
cd sshplex
```

### 2. Install Python Dependencies

```bash
# Navigate to the sshplex directory
cd sshplex

# Install required packages
pip3 install -r requirements.txt

# For development (optional)
pip3 install -r requirements-dev.txt
```

### 3. First Run Configuration

On first run, SSHplex will automatically create the configuration directory and copy a template configuration file:

```bash
# First run - creates ~/.config/sshplex/sshplex.yaml
python3 sshplex.py
```

This will create:
- `~/.config/sshplex/` directory
- `~/.config/sshplex/sshplex.yaml` configuration file

### 4. Configure SSHplex

Edit the configuration file with your settings:

```bash
# Edit the configuration file
nano ~/.config/sshplex/sshplex.yaml
# or
vim ~/.config/sshplex/sshplex.yaml
```

**Key configuration sections:**

```yaml
# NetBox connection settings
netbox:
  url: "https://your-netbox-instance.com"
  token: "your-netbox-api-token"
  verify_ssl: true
  timeout: 30
  default_filters:
    status: "active"
    role: "virtual-machine"
    has_primary_ip: "true"

# SSH connection settings
ssh:
  username: "your-ssh-username"
  key_path: "~/.ssh/id_ed25519"  # Path to your SSH private key
  timeout: 10
  port: 22

# tmux session settings
tmux:
  layout: "tiled"  # tiled, even-horizontal, even-vertical
  broadcast: false
  window_name: "sshplex"

# Logging settings (can be disabled)
logging:
  enabled: true
  level: "INFO"
  file: "logs/sshplex.log"
```

### 5. Run SSHplex

```bash
# Start with TUI interface (default)
python3 sshplex.py

# Use custom configuration file
python3 sshplex.py --config /path/to/custom-config.yaml

# CLI mode (NetBox connectivity test)
python3 sshplex.py --no-tui

# Show version
python3 sshplex.py --version
```

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

2. **SSH Key Authentication Failed**
   - Verify SSH key path in configuration
   - Ensure key has proper permissions (`chmod 600`)
   - Test manual SSH connection to target hosts

3. **tmux Session Not Created**
   - Ensure tmux is installed and in PATH
   - Check SSH connectivity to at least one host
   - Verify tmux is not already running a session with the same name

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
