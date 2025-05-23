# SSHplex Project - Copilot Instructions

## Project Overview

SSHplex is a Python-based SSH connection multiplexer that provides a Terminal User Interface (TUI) for selecting and connecting to multiple hosts simultaneously using tmux. The project is designed with extensibility in mind to support multiple Sources of Truth (SoT) and terminal multiplexers.

**Author**: Sabrimjd
**Created**: 2025-05-23
**Repository**: `sabrimjd/sshplex`
**Principle**: KISS (Keep It Simple, Stupid) - Focus on simplicity and debuggability

## Architecture Philosophy

### KISS Principle
- **Simple over Complex**: Choose the simplest solution that works
- **Debuggable**: Every component should be easy to test and debug
- **Minimal Dependencies**: Only include libraries that are absolutely necessary
- **Clear Logic Flow**: Straightforward, linear code paths
- **Fail Fast**: Clear error messages and early failure detection

### Core Design
- **Separation of Concerns**: UI/selection logic separate from connection logic
- **Extensibility**: Plugin-based for future SoTs and multiplexers
- **Modularity**: Small, focused modules with single responsibilities

## Required Libraries (Minimal Set)

### Essential Dependencies
```txt
# Core functionality
pynetbox==7.3.3          # NetBox API client
textual==0.47.1          # Modern TUI framework
pyyaml==6.0.1            # YAML configuration
pydantic==2.5.0          # Data validation
libtmux==0.25.0          # tmux session management
paramiko==3.4.0          # SSH connections

# Logging and debugging
rich==13.7.0             # Enhanced terminal output (works with textual)
loguru==0.7.2            # Simple, powerful logging

# Testing and development
pytest==7.4.4           # Testing framework
pytest-mock==3.12.0     # Mocking for tests
pytest-asyncio==0.23.0  # Async testing support
```

### Why These Libraries?
- **pynetbox**: Official NetBox client, well-maintained
- **textual**: Modern alternative to curses, easier to test
- **loguru**: Simple logging with file rotation, better than stdlib logging
- **pytest**: Industry standard for testing, excellent debugging
- **paramiko**: Pure Python SSH, easier to debug than subprocess calls

## Directory Structure with Descriptions

```
sshplex/
├── sshplex.py                  # Main entry point - CLI argument parsing and app startup
├── sshplex_connector.py        # SSH connection manager - handles tmux and SSH
├── config.yaml                 # Default configuration file
├── logs/                       # Log files directory
│   └── sshplex.log            # Application logs (auto-created)
├── lib/                       # Core library modules
│   ├── __init__.py            # Package initialization
│   ├── config.py              # Configuration management with pydantic
│   ├── logger.py              # Logging setup and configuration
│   ├── sot/                   # Source of Truth providers
│   │   ├── __init__.py        # SoT package init
│   │   ├── base.py            # Abstract base class for SoT providers
│   │   └── netbox.py          # NetBox implementation (simple, focused)
│   ├── multiplexer/           # Terminal multiplexer handlers
│   │   ├── __init__.py        # Multiplexer package init
│   │   ├── base.py            # Abstract base class for multiplexers
│   │   └── tmux.py            # tmux implementation (simple operations only)
│   ├── ui/                    # User interface components
│   │   ├── __init__.py        # UI package init
│   │   ├── host_selector.py   # Main TUI for host selection (single responsibility)
│   │   └── widgets.py         # Reusable textual widgets (minimal set)
│   └── ssh/                   # SSH connection handling
│       ├── __init__.py        # SSH package init
│       ├── connection.py      # SSH connection wrapper (simple, debuggable)
│       └── manager.py         # Connection pool manager (basic implementation)
├── tests/                     # Test suite
│   ├── __init__.py            # Test package init
│   ├── conftest.py            # pytest configuration and fixtures
│   ├── test_config.py         # Configuration testing
│   ├── test_sot/              # SoT provider tests
│   │   ├── __init__.py
│   │   └── test_netbox.py     # NetBox provider tests with mocks
│   ├── test_ui/               # UI component tests
│   │   ├── __init__.py
│   │   └── test_host_selector.py
│   └── test_ssh/              # SSH functionality tests
│       ├── __init__.py
│       └── test_connection.py
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies (pytest, etc.)
├── .gitignore                # Git ignore file
└── README.md                 # Project documentation
```

## Project Name and Branding

### SSHplex Name Usage
- **CLI Command**: `sshplex` (main executable)
- **Package Name**: `sshplex` (PyPI package)
- **Repository**: `sabrimjd/sshplex`
- **Module Prefix**: Use `sshplex_` for main modules
- **Log Files**: `sshplex.log`
- **Config File**: `sshplex.yaml` or `config.yaml`
- **tmux Sessions**: `sshplex-{timestamp}` format

### CLI Command Examples
```bash
sshplex                      # Start TUI host selector
sshplex --config custom.yaml # Use custom config
sshplex --version           # Show version
sshplex --help              # Show help
```

## Logging Strategy (Simple & Effective)

### Log Configuration
```python
# Use loguru for simple, powerful logging
from loguru import logger

# Simple file logging with rotation
logger.add("logs/sshplex.log",
          rotation="10 MB",    # Rotate when file reaches 10MB
          retention="30 days", # Keep logs for 30 days
          level="INFO",        # Info level and above
          format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} | {message}")
```

### Logging Guidelines
- **INFO**: Normal operations (connections, selections)
- **WARNING**: Recoverable issues (timeouts, retries)
- **ERROR**: Failed operations (connection failures, config errors)
- **DEBUG**: Detailed troubleshooting info (only in dev mode)

## Testing Strategy (Simple & Comprehensive)

### Test Structure
```python
# Use pytest with simple, focused tests
def test_netbox_connection():
    """Test NetBox API connection with mock."""
    pass

def test_ssh_connection():
    """Test SSH connection handling."""
    pass

def test_config_validation():
    """Test configuration validation."""
    pass
```

### Testing Guidelines
- **Unit Tests**: Each module tested in isolation
- **Mocks**: Mock external dependencies (NetBox API, SSH)
- **Integration Tests**: Test component interactions
- **TUI Tests**: Use textual's testing framework
- **Simple Assertions**: Clear, readable test expectations

## Configuration Schema (Simple)

```yaml
# config.yaml - Keep it simple and well-documented
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
  layout: "tiled"          # tiled, even-horizontal, even-vertical
  broadcast: false         # Start with broadcast off
  window_name: "sshplex"

logging:
  level: "INFO"           # DEBUG, INFO, WARNING, ERROR
  file: "logs/sshplex.log"
```

## Development Guidelines (KISS Focused)

### Code Style
- **Simple Functions**: Single responsibility, max 20 lines when possible
- **Clear Names**: Self-documenting variable and function names
- **Type Hints**: Use them, but keep simple (avoid complex generics)
- **Error Handling**: Explicit, early failure with clear messages
- **Comments**: Explain WHY, not WHAT (code should be self-explanatory)

### KISS Implementation Rules
1. **No Premature Optimization**: Make it work first, optimize later
2. **Linear Flow**: Avoid deep nesting, prefer early returns
3. **Explicit Over Implicit**: Clear, obvious code over clever shortcuts
4. **Simple Data Structures**: Use basic types, avoid complex hierarchies
5. **One Thing Well**: Each function/class does one thing excellently

### Debugging Support
```python
# Example of debuggable code structure
def connect_to_host(hostname: str, username: str) -> bool:
    """Connect to a single host with clear error reporting."""
    logger.info(f"SSHplex: Attempting connection to {hostname}")

    try:
        # Simple, traceable steps
        client = create_ssh_client()
        client.connect(hostname, username=username)
        logger.info(f"SSHplex: Successfully connected to {hostname}")
        return True
    except ConnectionError as e:
        logger.error(f"SSHplex: Failed to connect to {hostname}: {e}")
        return False
    except Exception as e:
        logger.error(f"SSHplex: Unexpected error connecting to {hostname}: {e}")
        raise  # Re-raise for debugging
```

## Error Handling Strategy

### Simple Error Categories
```python
class SSHplexError(Exception):
    """Base exception for SSHplex."""
    pass

class ConfigError(SSHplexError):
    """Configuration-related errors."""
    pass

class ConnectionError(SSHplexError):
    """SSH connection errors."""
    pass

class SoTError(SSHplexError):
    """Source of Truth errors."""
    pass
```

### Error Logging
- Log all errors with context and SSHplex prefix
- Include relevant data (hostname, config values)
- Provide actionable error messages
- Use structured logging for easy parsing

## Main Architecture Components

### 1. `sshplex.py` (Main Entry Point)
- **Purpose**: CLI interface and application startup
- **Responsibilities**:
  - Parse command line arguments
  - Load configuration from YAML
  - Initialize logging
  - Start TUI or direct connection mode
  - Handle graceful shutdown

### 2. `sshplex_connector.py` (Connection Manager)
- **Purpose**: Handle SSH connections and tmux session management
- **Responsibilities**:
  - Create and manage tmux sessions with sshplex naming
  - Establish SSH connections to selected hosts
  - Handle pane/tab creation and layout
  - Provide broadcasting capabilities (sync input across panes)
  - Manage connection lifecycle

### 3. Core Library Modules
- **config.py**: Configuration validation and management
- **sot/netbox.py**: NetBox integration for host discovery
- **ui/host_selector.py**: TUI for host selection and filtering
- **ssh/connection.py**: SSH connection handling
- **multiplexer/tmux.py**: tmux session management

---

## Implementation Priorities (KISS Order)

### Phase 1: Basic Functionality
1. Configuration loading and validation with sshplex namespace
2. Simple NetBox connection and VM listing
3. Basic TUI for host selection
4. Simple SSH connection to single host
5. Basic logging setup with sshplex prefix

### Phase 2: Core Features
1. Multi-select in TUI
2. tmux session creation with multiple panes (sshplex-prefixed sessions)
3. Connection error handling and retry
4. Search/filter functionality

### Phase 3: Polish
1. Broadcasting between panes
2. Session persistence
3. Advanced error recovery
4. Performance optimization

---

**Project Tagline**: "Multiplex your SSH connections with style"

**Remember**: Always choose the simplest solution that works. If you're writing complex code, step back and find a simpler approach. Every feature should be easy to test, debug, and understand by someone seeing the code for the first time. All components should be clearly branded with the SSHplex name for consistency.
