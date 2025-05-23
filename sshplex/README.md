# SSHplex Project

SSHplex is a Python-based SSH connection multiplexer that provides a Terminal User Interface (TUI) for selecting and connecting to multiple hosts simultaneously using tmux. The project is designed with extensibility in mind to support multiple Sources of Truth (SoT) and terminal multiplexers.

## Current Status - Phase 1

This is Phase 1 of the SSHplex project, focusing on:

1. ✅ Configuration loading and validation with pydantic
2. ✅ Simple NetBox connection and VM listing
3. ✅ Basic TUI for host selection
4. ⬜ Simple SSH connection to single host (coming in next update)
5. ✅ Basic logging setup

## Features

- **NetBox Integration**: Retrieve host information directly from NetBox
- **Modern TUI**: Clean, keyboard-driven interface for host selection
- **Configuration**: YAML-based configuration with validation
- **Logging**: Comprehensive logging with rotation

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/sabrimjd/sshplex.git
   cd sshplex
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. (Optional) For development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```

## Configuration

The configuration for SSHplex is managed through a YAML file named `config.yaml`. This file contains settings for connecting to NetBox and retrieving the VM list. An example configuration is provided below:

```yaml
sshplex:
  version: "1.0.0"
  session_prefix: "sshplex"

netbox:
  url: "https://netbox.example.com"
  token: "your-api-token"
  verify_ssl: true
  timeout: 30
  filters:
    status: "active"
    platform: "linux"

ssh:
  username: "admin"
  key_path: "~/.ssh/id_rsa"
  timeout: 10
  port: 22

tmux:
  layout: "tiled"
  broadcast: false
  window_name: "sshplex"

logging:
  level: "INFO"
  file: "logs/sshplex.log"
```

## Usage

### Configuration

First, edit the `config.yaml` file with your NetBox details:

```yaml
netbox:
  url: "https://your-netbox-instance.com/"
  token: "your-api-token"
  verify_ssl: true  # Set to false if using self-signed certificates
  timeout: 30
  default_filters:
    status: "active"
    role: "server"
```

### Running SSHplex

```bash
# Start the TUI interface
python3 sshplex.py

# Run in CLI mode (no TUI)
python3 sshplex.py --no-tui

# Use a custom config file
python3 sshplex.py --config my-config.yaml

# Show version information
python3 sshplex.py --version
```

### TUI Keyboard Shortcuts

- `q` - Quit the application
- `r` - Refresh hosts from NetBox
- `c` - Connect to selected hosts (Phase 1: just logs the selection)
- `f` - Focus on the filter input
- `Enter` on a row - Select/deselect a host

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
