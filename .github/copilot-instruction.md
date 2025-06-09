# SSHplex Project - Copilot Instructions

## Project Overview

SSHplex is a Python-based SSH connection multiplexer that provides a Terminal User Interface (TUI) for selecting and connecting to multiple hosts simultaneously using tmux. The project is designed with extensibility in mind to support multiple Sources of Truth (SoT) and terminal multiplexers.

**Author**: MJAHED Sabri
**Contact**: contact@sabrimjahed.com
**Current Version**: 1.0.10
**Created**: 2025-05-23
**Repository**: `sabrimjd/sshplex`
**License**: MIT
**Principle**: KISS (Keep It Simple, Stupid) - Focus on simplicity and debuggability

### Current Implementation Status
- ✅ **Package Structure**: Modern Python packaging with pyproject.toml
- ✅ **Entry Points**: Both main TUI (`sshplex`) and debug CLI (`sshplex-cli`)
- ✅ **Configuration**: YAML-based configuration with Pydantic validation
- ✅ **NetBox Integration**: Complete NetBox API integration for host discovery
- ✅ **TUI Interface**: Textual-based modern terminal interface
- ✅ **tmux Integration**: Full tmux session management with libtmux
- ✅ **SSH Connections**: Robust SSH connection handling
- ✅ **Logging**: Structured logging with loguru and file rotation
- ✅ **Testing**: Pytest-based test suite with coverage
- ✅ **Development Tools**: Black, flake8, mypy for code quality

### Key Features
- **Host Discovery**: Fetch hosts from NetBox with filtering capabilities
- **Interactive Selection**: Modern TUI for selecting multiple hosts
- **tmux Integration**: Automatic tmux session creation and management
- **SSH Multiplexing**: Connect to multiple hosts in a single tmux session
- **Broadcast Mode**: Optional synchronized input across all connections
- **Configuration Management**: YAML configuration with validation
- **Extensible Architecture**: Plugin-based design for future SoTs and multiplexers

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

## Required Libraries (Current Dependencies)

### Production Dependencies (from pyproject.toml)
```txt
# Core functionality
pynetbox==7.5.0      # NetBox API client - official NetBox client
textual==3.3.0       # Modern TUI framework - replaces curses
pyyaml==6.0.2        # YAML configuration parsing
pydantic==2.11.0     # Data validation and settings management
libtmux==0.46.1      # tmux session management library

# Logging and output
loguru==0.7.3        # Simple, powerful logging with rotation
rich==13.9.4         # Enhanced terminal output (integrates with textual)
```

### Development Dependencies
```txt
# Testing and development tools
pytest>=7.0.0        # Testing framework - industry standard
pytest-cov>=4.0.0    # Test coverage reporting
black>=22.0.0        # Code formatting - PEP 8 compliant
flake8>=5.0.0        # Linting and style checking
mypy>=1.0.0          # Static type checking
types-PyYAML>=6.0.0  # Type stubs for PyYAML
```

### Package Configuration
- **Python Version**: Requires Python 3.8+ (supports 3.8-3.12)
- **Entry Points**:
  - `sshplex` → `sshplex.main:main` (main TUI application)
  - `sshplex-cli` → `sshplex.cli:main` (debug CLI interface)
- **Package Data**: Includes YAML configuration templates

### Why These Libraries?
- **pynetbox**: Official NetBox client, well-maintained with full API support
- **textual**: Modern alternative to curses, easier to test and develop with
- **loguru**: Simple logging with file rotation, better than stdlib logging
- **pydantic**: Excellent for configuration validation and data models
- **libtmux**: Pythonic tmux control, simpler than subprocess calls
- **rich**: Beautiful terminal output that integrates seamlessly with textual
- **pytest**: Industry standard for testing with excellent debugging capabilities

## Directory Structure with Descriptions

```
sshplex/                       # Project root directory
├── .github/                   # GitHub configuration and workflows
│   └── copilot-instruction.md # This file - AI assistant instructions
├── .gitignore                # Git ignore file
├── .vscode/                   # VS Code workspace settings
├── .mypy_cache/              # MyPy type checker cache
├── LICENSE                    # MIT license file
├── MANIFEST.in               # Python package manifest for source distribution
├── PACKAGING.md              # Packaging documentation and instructions
├── README.md                 # Project documentation and usage guide
├── pyproject.toml            # Modern Python packaging configuration (PEP 518)
├── sshplex.py                # Development wrapper script for easy source usage
├── __pycache__/              # Python bytecode cache (auto-generated)
├── logs/                     # Log files directory
│   └── sshplex.log          # Application logs (auto-created)
├── sshplex/                  # Main package directory
│   ├── __init__.py          # Package initialization with version info
│   ├── main.py              # Main entry point for pip-installed package
│   ├── cli.py               # CLI debug interface for NetBox connectivity testing
│   ├── sshplex_connector.py # SSH connection manager - handles tmux and SSH
│   ├── config-template.yaml # Configuration template file
│   ├── __pycache__/         # Package bytecode cache
│   └── lib/                 # Core library modules
│       ├── __init__.py      # Library package initialization
│       ├── config.py        # Configuration management with pydantic
│       ├── logger.py        # Logging setup and configuration
│       ├── __pycache__/     # Library bytecode cache
│       ├── sot/             # Source of Truth providers
│       │   ├── __init__.py  # SoT package init
│       │   ├── base.py      # Abstract base class for SoT providers
│       │   ├── netbox.py    # NetBox implementation (simple, focused)
│       │   └── __pycache__/ # SoT bytecode cache
│       ├── multiplexer/     # Terminal multiplexer handlers
│       │   ├── __init__.py  # Multiplexer package init
│       │   ├── base.py      # Abstract base class for multiplexers
│       │   ├── tmux.py      # tmux implementation (simple operations only)
│       │   └── __pycache__/ # Multiplexer bytecode cache
│       ├── ui/              # User interface components
│       │   ├── __init__.py  # UI package init
│       │   ├── host_selector.py # Main TUI for host selection (single responsibility)
│       │   ├── session_manager.py # Session management UI components
│       │   └── __pycache__/ # UI bytecode cache
│       └── ssh/             # SSH connection handling
│           ├── __init__.py  # SSH package init
│           ├── connection.py # SSH connection wrapper (simple, debuggable)
│           └── manager.py   # Connection pool manager (basic implementation)
├── sshplex.egg-info/        # Package metadata (auto-generated during development)
│   ├── dependency_links.txt # Package dependency links
│   ├── entry_points.txt     # Console script entry points
│   ├── PKG-INFO            # Package metadata
│   ├── requires.txt        # Package requirements
│   ├── SOURCES.txt         # Source file listing
│   └── top_level.txt       # Top-level package names
└── tests/                   # Test suite
    ├── __init__.py         # Test package init
    ├── conftest.py         # pytest configuration and fixtures
    ├── test_config.py      # Configuration testing
    ├── __pycache__/        # Test bytecode cache
    ├── test_sot/           # SoT provider tests
    │   ├── __init__.py     # SoT test package init
    │   └── test_netbox.py  # NetBox provider tests with mocks
    ├── test_ssh/           # SSH functionality tests
    │   ├── __init__.py     # SSH test package init
    │   └── test_connection.py # SSH connection tests
    └── test_ui/            # UI component tests
        ├── __init__.py     # UI test package init
        └── test_host_selector.py # Host selector TUI tests
```

## Project Name and Branding

### SSHplex Name Usage
- **CLI Command**: `sshplex` (main executable - pip installed)
- **Development Script**: `python sshplex.py` (development wrapper)
- **Package Name**: `sshplex` (PyPI package)
- **Repository**: `sabrimjd/sshplex`
- **Module Prefix**: Use `sshplex_` for main modules
- **Log Files**: `sshplex.log`
- **Config File**: `sshplex.yaml` or `config-template.yaml`
- **tmux Sessions**: `sshplex-{timestamp}` format

### CLI Command Examples
```bash
# Production usage (pip installed)
sshplex                      # Start TUI host selector
sshplex --config custom.yaml # Use custom config
sshplex --version           # Show version info
sshplex --help              # Show help

# Development usage (source)
python sshplex.py            # Start TUI via development wrapper
python -m sshplex.main       # Direct package main
python -m sshplex.cli        # CLI debug interface

# Debug and testing
sshplex-cli                  # CLI debug mode (tests NetBox connectivity)
sshplex-cli --config custom.yaml # CLI debug with custom config
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
# SSHplex Configuration - tmux support
sshplex:
  session_prefix: "sshplex"

netbox:
  url: "https://netbox.lan/"
  token: "CHANGE_TOKEN_HERE"
  verify_ssl: false
  timeout: 30
  default_filters:
    status: "active"
    role: "virtual-machine"
    has_primary_ip: "true"

ssh:
  username: "admin"
  key_path: "~/.ssh/id_ed25519"
  timeout: 10
  port: 22

tmux:
  layout: "tiled" # tiled, even-horizontal, even-vertical
  broadcast: false # Start with broadcast off
  window_name: "sshplex"

ui:
  show_log_panel: false
  log_panel_height: 20
  table_columns: ["name", "ip", "cluster", "tags", "description"]

logging:
  enabled: false
  level: "DEBUG" # DEBUG, INFO, WARNING, ERROR
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

### 1. `sshplex.py` (Development Wrapper)
- **Purpose**: Development wrapper for easy source usage during development
- **Responsibilities**:
  - Add sshplex package to Python path for development
  - Import and call main function from sshplex.main
  - Provide development-friendly entry point
  - Handle import errors gracefully

### 2. `sshplex/main.py` (Main Application Entry Point)
- **Purpose**: Main entry point for pip-installed package
- **Responsibilities**:
  - Parse command line arguments
  - Check system dependencies (tmux availability)
  - Load configuration from YAML
  - Initialize logging system
  - Start TUI host selector
  - Handle graceful shutdown and error reporting

### 3. `sshplex/cli.py` (CLI Debug Interface)
- **Purpose**: CLI debug interface for NetBox connectivity testing
- **Responsibilities**:
  - Provide command-line debugging capabilities
  - Test NetBox API connectivity
  - Validate configuration without starting TUI
  - Display connection status and troubleshooting info

### 4. `sshplex/sshplex_connector.py` (Connection Manager)
- **Purpose**: Handle SSH connections and tmux session management
- **Responsibilities**:
  - Create and manage tmux sessions with sshplex naming
  - Establish SSH connections to selected hosts
  - Handle pane/tab creation and layout
  - Provide broadcasting capabilities (sync input across panes)
  - Manage connection lifecycle and cleanup

### 5. Core Library Modules
- **config.py**: Configuration validation and management with pydantic
- **logger.py**: Logging setup and configuration
- **sot/base.py**: Abstract base class for Source of Truth providers
- **sot/netbox.py**: NetBox integration for host discovery
- **ui/host_selector.py**: Main TUI for host selection and filtering
- **ui/session_manager.py**: Session management UI components
- **ssh/connection.py**: SSH connection handling and wrapper
- **ssh/manager.py**: Connection pool management
- **multiplexer/base.py**: Abstract base class for terminal multiplexers
- **multiplexer/tmux.py**: tmux session management implementation

### 6. Package Configuration
- **pyproject.toml**: Modern Python packaging configuration (PEP 518)
- **config-template.yaml**: Configuration template file for users
- **MANIFEST.in**: Source distribution file inclusion rules
- **PACKAGING.md**: Packaging documentation and release instructions

## Development Workflow

### VS Code Tasks
The project includes pre-configured VS Code tasks for development:

```json
{
  "label": "Run SSHplex",
  "type": "shell",
  "command": "cd sshplex && python sshplex.py",
  "group": "test",
  "isBackground": false
}
```

**Usage**: Use `Cmd+Shift+P` → "Tasks: Run Task" → "Run SSHplex" to start the application in development mode.

### Development Commands
```bash
# Development execution
python sshplex.py              # Run via development wrapper
python -m sshplex.main         # Run main application directly
python -m sshplex.cli          # Run CLI debug interface

# Testing
pytest                         # Run all tests
pytest -v                      # Verbose test output
pytest --cov=sshplex          # Run with coverage

# Code quality
black .                        # Format code
flake8 .                       # Lint code
mypy sshplex/                  # Type checking

# Package building
python -m build                # Build distribution packages
pip install -e .               # Install in development mode
```

**Remember**: Always choose the simplest solution that works. If you're writing complex code, step back and find a simpler approach. Every feature should be easy to test, debug, and understand by someone seeing the code for the first time. All components should be clearly branded with the SSHplex name for consistency.

**Project Tagline**: "Multiplex your SSH connections with style"
