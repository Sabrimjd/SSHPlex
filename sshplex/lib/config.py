"""SSHplex configuration management with pydantic validation"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from .. import __version__

SUPPORTED_SOT_PROVIDER_TYPES = ("static", "netbox", "ansible", "consul", "git")
SOT_PROVIDER_LABELS = {
    "static": "Static",
    "netbox": "NetBox",
    "ansible": "Ansible",
    "consul": "Consul",
    "git": "Git",
}

SUPPORTED_MUX_BACKENDS = ("tmux", "iterm2-native")
MUX_BACKEND_LABELS = {
    "tmux": "tmux",
    "iterm2-native": "iTerm2 Native",
}

SUPPORTED_GIT_INVENTORY_FORMATS = ("static", "ansible")


class SSHplexConfig(BaseModel):
    """SSHplex main configuration."""
    version: str = __version__
    session_prefix: str = "sshplex"


class LoggingConfig(BaseModel):
    """Logging configuration."""
    enabled: bool = True
    level: str = "INFO"
    file: str = "logs/sshplex.log"


class UIConfig(BaseModel):
    """User interface configuration."""
    theme: str = "textual-dark"
    show_log_panel: bool = True
    log_panel_height: int = 20  # Percentage of screen height
    table_columns: list = Field(default_factory=lambda: ["name", "ip", "cluster", "role", "tags"])

class Proxy(BaseModel):
    """ImportProxies configuration with defaults."""
    name: str = Field("", description="Proxy name")
    imports: list = Field(default_factory=list, description="List of imports that will use this proxy")
    host: str = Field("", description="Proxy host or ip")
    username: str = Field("", description="Proxy username")
    key_path: str = Field("", description="Proxy key")


class SSHRetryConfig(BaseModel):
    """SSH connection retry configuration."""
    enabled: bool = Field(default=True, description="Enable connection retry on failure")
    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    delay_seconds: float = Field(default=2.0, ge=0.5, le=60.0, description="Initial delay between retries")
    exponential_backoff: bool = Field(default=True, description="Double delay on each retry")


class SSHConfig(BaseModel):
    """SSH connection configuration."""
    username: str = Field(default="admin", description="Default SSH username")
    key_path: str = Field(default="~/.ssh/id_rsa", description="Path to SSH private key")
    timeout: int = 10
    port: int = 22
    # SSH security options
    strict_host_key_checking: bool = Field(default=False, description="Enable strict host key checking")
    user_known_hosts_file: str = Field(default="", description="Custom known_hosts file path (empty = default)")
    # Retry configuration
    retry: SSHRetryConfig = Field(default_factory=SSHRetryConfig, description="Connection retry settings")
    proxy: List[Proxy] = Field(alias='proxy', default_factory=list, description="List of proxies")

class TmuxConfig(BaseModel):
    """tmux/iTerm2 multiplexer configuration.

    Three backend options:
    1. tmux standalone: backend="tmux", control_with_iterm2=false
    2. tmux + iTerm2: backend="tmux", control_with_iterm2=true (macOS only)
    3. iTerm2 native: backend="iterm2-native" (macOS only)
    """
    # Backend selection
    backend: str = Field(
        default="tmux",
        description="Multiplexer backend: 'tmux' or 'iterm2-native'"
    )
    # Common options
    use_panes: bool = Field(default=True, description="Connection mode: true=panes, false=tabs")
    layout: str = "tiled"  # tiled, even-horizontal, even-vertical
    broadcast: bool = False  # Start with broadcast off
    window_name: str = "sshplex"
    max_panes_per_window: int = Field(default=5, description="Maximum panes per window before creating a new window")
    # iTerm2 + tmux integration (macOS only, for backend="tmux")
    control_with_iterm2: bool = Field(default=False, description="Use iTerm2 tmux -CC mode (macOS only)")
    iterm2_attach_target: str = Field(
        default="new-window",
        description="Where to open tmux session in iTerm2: new-window or new-tab"
    )
    # iTerm2 native specific (macOS only, for backend="iterm2-native")
    iterm2_profile: str = Field(default="Default", description="iTerm2 profile to use for new windows/tabs")
    iterm2_native_target: str = Field(
        default="current-window",
        description="Where to open iTerm2 native sessions: current-window or new-window"
    )
    iterm2_native_hide_from_history: bool = Field(
        default=True,
        description="Prefix native iTerm2 dispatched commands with a leading space"
    )
    iterm2_split_pattern: str = Field(
        default="alternate",
        description="Split pattern for iTerm2 native: alternate, vertical, horizontal"
    )

    @field_validator("backend")
    @classmethod
    def validate_backend_value(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in SUPPORTED_MUX_BACKENDS:
            raise ValueError(
                f"Invalid backend: {value}. Must be one of: {list(SUPPORTED_MUX_BACKENDS)}"
            )
        return normalized

    def validate_backend_config(self) -> bool:
        """Validate backend configuration.

        Returns:
            True if config is valid, raises ValueError otherwise
        """
        import platform

        # Validate backend option
        if self.backend not in SUPPORTED_MUX_BACKENDS:
            raise ValueError(
                f"Invalid backend: {self.backend}. Must be one of: {list(SUPPORTED_MUX_BACKENDS)}"
            )

        # Validate iTerm2 native mode on macOS only
        if self.backend == "iterm2-native" and platform.system().lower() != "darwin":
            raise ValueError(
                "backend: 'iterm2-native' is only supported on macOS. "
                "Use backend: 'tmux' on Linux/other systems."
            )

        if self.iterm2_native_target not in ["current-window", "new-window"]:
            raise ValueError(
                "tmux.iterm2_native_target must be one of: ['current-window', 'new-window']"
            )

        # Validate control_with_iterm2 on macOS only
        if self.control_with_iterm2 and platform.system().lower() != "darwin":
            raise ValueError(
                "tmux.control_with_iterm2 is only supported on macOS. "
                "Set this to false on Linux/other systems."
            )

        return True


class ConsulConfig(BaseModel):
    """Consul-specific configuration with defaults."""
    host: str = Field("consul.example.com", description="Consul host address")
    port: int = Field(443, description="Consul port number")
    token: str = Field("default_token", description="Consul token for authentication")
    scheme: str = Field("https", description="URL scheme (e.g., 'https')")
    verify: bool = Field(True, description="Whether to verify SSL certificates (default: True for security)")
    dc: str = Field("dc1", description="Datacenter name")
    cert: str = Field("", description="Path to SSL certificate")

class SoTImportConfig(BaseModel):
    """Individual SoT import configuration."""
    name: str = Field(..., description="Unique name for this import")
    type: str = Field(..., description=f"Provider type: {', '.join(SUPPORTED_SOT_PROVIDER_TYPES)}")

    # Static provider fields
    hosts: Optional[List[Dict[str, Any]]] = None

    # NetBox provider fields
    url: Optional[str] = None
    token: Optional[str] = None
    verify_ssl: Optional[bool] = True
    timeout: Optional[int] = 30
    default_filters: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Ansible provider fields
    inventory_paths: Optional[List[str]] = None

    # Consul provider fields
    config: Optional[ConsulConfig] = None

    # Git provider fields
    repo_url: Optional[str] = None
    branch: Optional[str] = "main"
    source_pattern: Optional[str] = "hosts/**/*.y*ml"
    auto_pull: Optional[bool] = True
    pull_interval_seconds: Optional[int] = 300
    priority: Optional[int] = 100
    pull_strategy: Optional[str] = "ff-only"
    inventory_format: Optional[str] = "static"

    @field_validator("type")
    @classmethod
    def validate_provider_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in SUPPORTED_SOT_PROVIDER_TYPES:
            raise ValueError(
                f"Unsupported provider type '{value}'. "
                f"Supported values: {list(SUPPORTED_SOT_PROVIDER_TYPES)}"
            )
        return normalized

    @field_validator("pull_strategy")
    @classmethod
    def validate_pull_strategy(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = str(value).strip().lower()
        if normalized and normalized != "ff-only":
            raise ValueError("git pull_strategy only supports 'ff-only'")
        return normalized or "ff-only"

    @field_validator("inventory_format")
    @classmethod
    def validate_inventory_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = str(value).strip().lower()
        if normalized not in SUPPORTED_GIT_INVENTORY_FORMATS:
            raise ValueError(
                f"Unsupported git inventory format '{value}'. "
                f"Supported values: {list(SUPPORTED_GIT_INVENTORY_FORMATS)}"
            )
        return normalized

class SoTConfig(BaseModel):
    """Source of Truth configuration."""
    providers: List[str] = Field(
        default_factory=list,
        description="List of SoT providers to use: static, netbox, ansible, consul, git",
    )
    import_: List[SoTImportConfig] = Field(alias='import', default_factory=list, description="List of import configurations")

    @field_validator("providers")
    @classmethod
    def validate_enabled_providers(cls, value: List[str]) -> List[str]:
        normalized: List[str] = []
        for provider in value or []:
            provider_name = str(provider or "").strip().lower()
            if not provider_name:
                continue
            if provider_name not in SUPPORTED_SOT_PROVIDER_TYPES:
                raise ValueError(
                    f"Unsupported provider '{provider_name}'. "
                    f"Supported values: {list(SUPPORTED_SOT_PROVIDER_TYPES)}"
                )
            if provider_name not in normalized:
                normalized.append(provider_name)
        return normalized


class CacheConfig(BaseModel):
    """Host cache configuration."""
    enabled: bool = True
    cache_dir: str = "~/.cache/sshplex"
    ttl_hours: int = Field(default=24, description="Cache time-to-live in hours")


class Config(BaseModel):
    """Main SSHplex configuration model."""
    sshplex: SSHplexConfig = Field(default_factory=SSHplexConfig)
    sot: SoTConfig = Field(default_factory=SoTConfig)
    ssh: SSHConfig = Field(default_factory=SSHConfig)
    tmux: TmuxConfig = Field(default_factory=TmuxConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)


def get_default_config_path() -> Path:
    """Get the default configuration file path in ~/.config/sshplex/sshplex.yaml"""
    return Path.home() / ".config" / "sshplex" / "sshplex.yaml"


def get_template_config_path() -> Path:
    """Get the path to the config template file."""
    # Get the directory where this config.py file is located
    lib_dir = Path(__file__).parent
    # Go up to sshplex directory and find config-template.yaml
    sshplex_dir = lib_dir.parent
    return sshplex_dir / "config-template.yaml"


def ensure_config_directory() -> Path:
    """Ensure the ~/.config/sshplex directory exists."""
    config_dir = Path.home() / ".config" / "sshplex"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def initialize_default_config() -> Path:
    """Initialize default configuration by copying template to ~/.config/sshplex/sshplex.yaml"""
    from .logger import get_logger

    logger = get_logger()
    config_path = get_default_config_path()
    template_path = get_template_config_path()

    # Ensure config directory exists
    ensure_config_directory()

    if not template_path.exists():
        raise FileNotFoundError(f"SSHplex: Template config file not found: {template_path}")

    # Copy template to default config location
    shutil.copy2(template_path, config_path)
    logger.info(f"SSHplex: Created default configuration at {config_path}")
    logger.info(f"SSHplex: Please edit {config_path} with your NetBox details")

    return config_path


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration from YAML file.

    Uses ~/.config/sshplex/sshplex.yaml as default location.
    Creates config directory and copies template on first run.

    Args:
        config_path: Path to configuration file (optional, defaults to ~/.config/sshplex/sshplex.yaml)

    Returns:
        Validated configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist and template can't be found
        ValueError: If config validation fails
    """
    from .logger import get_logger

    # Use default config path if none provided
    if config_path is None:
        config_file = get_default_config_path()

        # If default config doesn't exist, initialize it from template
        if not config_file.exists():
            try:
                config_file = initialize_default_config()
                print(f"✅ SSHplex: First run detected - created configuration at {config_file}")
                print(f"📝 Please edit {config_file} with your NetBox details before running SSHplex again")
                print("🔧 Key settings to configure:")
                print("   - netbox.url: Your NetBox instance URL")
                print("   - netbox.token: Your NetBox API token")
                print("   - ssh.username: Your SSH username")
                print("   - ssh.key_path: Path to your SSH private key")
                print("\n🚀 Continuing with generated defaults. You can adjust settings later in the Config editor (key: e).")
            except Exception as e:
                raise FileNotFoundError(f"SSHplex: Could not initialize default config: {e}") from e
    else:
        config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"SSHplex: Configuration file not found: {config_file}")

    try:
        logger = get_logger()
        logger.info(f"SSHplex: Loading configuration from {config_file}")

        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            raise ValueError("SSHplex: Configuration file is empty or invalid")

        config = Config(**config_data)
        logger.info("SSHplex: Configuration loaded and validated successfully")
        return config

    except yaml.YAMLError as e:
        raise ValueError(f"SSHplex: Invalid YAML in config file: {e}") from e
    except FileNotFoundError as e:
        raise FileNotFoundError(f"SSHplex: Configuration file not found: {e}") from e
    except PermissionError as e:
        raise ValueError(f"SSHplex: Permission denied reading config file: {e}") from e
    except Exception as e:
        # Provide more context for pydantic validation errors
        error_msg = str(e)
        if "validation" in error_msg.lower() or "field" in error_msg.lower():
            raise ValueError(f"SSHplex: Configuration validation failed: {error_msg}") from e
        raise ValueError(f"SSHplex: Configuration validation failed: {e}") from e


def get_config_info() -> Dict[str, Any]:
    """Get information about SSHplex configuration paths and status."""
    default_path = get_default_config_path()
    template_path = get_template_config_path()

    return {
        "default_config_path": str(default_path),
        "default_config_exists": default_path.exists(),
        "template_path": str(template_path),
        "template_exists": template_path.exists(),
        "config_dir_exists": default_path.parent.exists()
    }
