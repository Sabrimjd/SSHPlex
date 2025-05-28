"""SSHplex configuration management with pydantic validation."""

from pathlib import Path
from typing import Dict, Any
import yaml
from pydantic import BaseModel, Field, validator


class SSHplexConfig(BaseModel):
    """SSHplex main configuration."""
    version: str = "1.0.0"
    session_prefix: str = "sshplex"


class NetBoxConfig(BaseModel):
    """NetBox connection configuration."""
    url: str = Field(..., description="NetBox instance URL")
    token: str = Field(..., description="NetBox API token")
    verify_ssl: bool = True
    timeout: int = 30
    default_filters: Dict[str, str] = Field(default_factory=dict)

    @validator('url')
    def validate_url(cls, v):
        """Validate NetBox URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('NetBox URL must start with http:// or https://')
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/sshplex.log"

    @validator('level')
    def validate_level(cls, v):
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class UIConfig(BaseModel):
    """User interface configuration."""
    show_log_panel: bool = True
    log_panel_height: int = 20  # Percentage of screen height
    table_columns: list = Field(default_factory=lambda: ["name", "ip", "cluster", "role", "tags"])


class Config(BaseModel):
    """Main SSHplex configuration model."""
    sshplex: SSHplexConfig = Field(default_factory=SSHplexConfig)
    netbox: NetBoxConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ui: UIConfig = Field(default_factory=UIConfig)


def load_config(config_path: str = "config.yaml") -> Config:
    """Load and validate configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Validated configuration object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config validation fails
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"SSHplex: Configuration file not found: {config_path}")

    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        config = Config(**config_data)
        return config

    except yaml.YAMLError as e:
        raise ValueError(f"SSHplex: Invalid YAML in config file: {e}")
    except Exception as e:
        raise ValueError(f"SSHplex: Configuration validation failed: {e}")
