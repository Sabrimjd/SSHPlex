"""SSHplex configuration management with pydantic validation"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import shutil
import os
from pydantic import BaseModel, Field, model_validator

from .. import __version__


class SSHplexConfig(BaseModel):
    """SSHplex main configuration."""
    version: str = __version__
    session_prefix: str = "sshplex"


class NetBoxConfig(BaseModel):
    """NetBox connection configuration."""
    url: str = Field(..., description="NetBox instance URL")
    token: str = Field(..., description="NetBox API token")
    verify_ssl: bool = True
    timeout: int = 30
    default_filters: Dict[str, str] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    enabled: bool = True
    level: str = "INFO"
    file: str = "logs/sshplex.log"


class UIConfig(BaseModel):
    """User interface configuration."""
    show_log_panel: bool = True
    log_panel_height: int = 20  # Percentage of screen height
    table_columns: list = Field(default_factory=lambda: ["name", "ip", "cluster", "role", "tags"])


class SSHConfig(BaseModel):
    """SSH connection configuration."""
    username: str = Field(default="admin", description="Default SSH username")
    key_path: str = Field(default="~/.ssh/id_rsa", description="Path to SSH private key")
    timeout: int = 10
    port: int = 22


class TmuxConfig(BaseModel):
    """tmux configuration."""
    layout: str = "tiled"  # tiled, even-horizontal, even-vertical
    broadcast: bool = False  # Start with broadcast off
    window_name: str = "sshplex"
    max_panes_per_window: int = Field(default=5, description="Maximum panes per window before creating a new window")


class AnsibleConfig(BaseModel):
    """Ansible inventory configuration."""
    inventory_paths: List[str] = Field(default_factory=list, description="List of paths to Ansible inventory YAML files")
    default_filters: Dict[str, Any] = Field(default_factory=dict)


class SoTImportConfig(BaseModel):
    """Individual SoT import configuration."""
    name: str = Field(..., description="Unique name for this import")
    type: str = Field(..., description="Provider type: static, netbox, ansible")

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


class SoTConfig(BaseModel):
    """Source of Truth configuration."""
    providers: List[str] = Field(default_factory=lambda: ["static"], description="List of SoT providers to use: static, netbox, ansible")
    import_: List[SoTImportConfig] = Field(alias='import', default_factory=list, description="List of import configurations")


class CacheConfig(BaseModel):
    """Host cache configuration."""
    enabled: bool = True
    cache_dir: str = "~/cache/sshplex"
    ttl_hours: int = Field(default=24, description="Cache time-to-live in hours")


class Config(BaseModel):
    """Main SSHplex configuration model."""
    sshplex: SSHplexConfig = Field(default_factory=SSHplexConfig)
    sot: SoTConfig = Field(default_factory=SoTConfig)
    netbox: Optional[NetBoxConfig] = None
    ansible_inventory: Optional[AnsibleConfig] = None
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
                print(f"🔧 Key settings to configure:")
                print(f"   - netbox.url: Your NetBox instance URL")
                print(f"   - netbox.token: Your NetBox API token")
                print(f"   - ssh.username: Your SSH username")
                print(f"   - ssh.key_path: Path to your SSH private key")
                print(f"\n🚀 Run 'sshplex' again after configuration is complete!")
                # Exit gracefully to let user configure
                import sys
                sys.exit(0)
            except Exception as e:
                raise FileNotFoundError(f"SSHplex: Could not initialize default config: {e}")
    else:
        config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"SSHplex: Configuration file not found: {config_file}")

    try:
        logger = get_logger()
        logger.info(f"SSHplex: Loading configuration from {config_file}")

        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        config = Config(**config_data)
        logger.info("SSHplex: Configuration loaded and validated successfully")
        return config

    except yaml.YAMLError as e:
        raise ValueError(f"SSHplex: Invalid YAML in config file: {e}")
    except Exception as e:
        raise ValueError(f"SSHplex: Configuration validation failed: {e}")


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
