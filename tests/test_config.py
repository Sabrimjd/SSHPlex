"""Tests for SSHplex configuration management."""

import pytest
import yaml
from unittest.mock import patch

from sshplex.lib.config import (
    Config,
    SSHConfig,
    SSHRetryConfig,
    TmuxConfig,
    UIConfig,
    CacheConfig,
    SoTImportConfig,
    Proxy,
    load_config,
    get_default_config_path,
    get_template_config_path,
    ensure_config_directory,
)


class TestSSHRetryConfig:
    """Tests for SSHRetryConfig model."""

    def test_default_values(self):
        """Test default retry configuration."""
        config = SSHRetryConfig()
        assert config.enabled is True
        assert config.max_attempts == 3
        assert config.delay_seconds == 2.0
        assert config.exponential_backoff is True

    def test_custom_values(self):
        """Test custom retry configuration."""
        config = SSHRetryConfig(
            enabled=False,
            max_attempts=5,
            delay_seconds=5.0,
            exponential_backoff=False
        )
        assert config.enabled is False
        assert config.max_attempts == 5
        assert config.delay_seconds == 5.0
        assert config.exponential_backoff is False

    def test_validation_max_attempts(self):
        """Test max_attempts validation."""
        with pytest.raises(Exception):  # ValidationError
            SSHRetryConfig(max_attempts=0)
        with pytest.raises(Exception):  # ValidationError
            SSHRetryConfig(max_attempts=11)

    def test_validation_delay(self):
        """Test delay_seconds validation."""
        with pytest.raises(Exception):  # ValidationError
            SSHRetryConfig(delay_seconds=0.1)
        with pytest.raises(Exception):  # ValidationError
            SSHRetryConfig(delay_seconds=61.0)


class TestSSHConfig:
    """Tests for SSHConfig model."""

    def test_default_values(self):
        """Test default SSH configuration."""
        config = SSHConfig()
        assert config.username == "admin"
        assert config.key_path == "~/.ssh/id_rsa"
        assert config.timeout == 10
        assert config.port == 22
        assert config.strict_host_key_checking is False
        assert config.retry.enabled is True
        assert config.proxy == []

    def test_custom_values(self):
        """Test custom SSH configuration."""
        config = SSHConfig(
            username="testuser",
            key_path="~/.ssh/test_key",
            timeout=30,
            port=2222,
            strict_host_key_checking=True,
            user_known_hosts_file="/custom/known_hosts"
        )
        assert config.username == "testuser"
        assert config.key_path == "~/.ssh/test_key"
        assert config.timeout == 30
        assert config.port == 2222
        assert config.strict_host_key_checking is True
        assert config.user_known_hosts_file == "/custom/known_hosts"

    def test_retry_config_nested(self):
        """Test nested retry configuration."""
        retry = SSHRetryConfig(max_attempts=5, delay_seconds=3.0)
        config = SSHConfig(retry=retry)
        assert config.retry.max_attempts == 5
        assert config.retry.delay_seconds == 3.0


class TestProxy:
    """Tests for Proxy model."""

    def test_default_values(self):
        """Test default proxy configuration."""
        proxy = Proxy()
        assert proxy.name == ""
        assert proxy.imports == []
        assert proxy.host == ""
        assert proxy.username == ""
        assert proxy.key_path == ""

    def test_custom_values(self):
        """Test custom proxy configuration."""
        proxy = Proxy(
            name="test-proxy",
            imports=["provider1", "provider2"],
            host="proxy.example.com",
            username="proxyuser",
            key_path="~/.ssh/proxy_key"
        )
        assert proxy.name == "test-proxy"
        assert proxy.imports == ["provider1", "provider2"]
        assert proxy.host == "proxy.example.com"


class TestTmuxConfig:
    """Tests for TmuxConfig model."""

    def test_default_values(self):
        """Test default tmux configuration."""
        config = TmuxConfig()
        assert config.layout == "tiled"
        assert config.broadcast is False
        assert config.window_name == "sshplex"
        assert config.max_panes_per_window == 5
        assert config.control_with_iterm2 is False


class TestUIConfig:
    """Tests for UIConfig model."""

    def test_default_values(self):
        """Test default UI configuration."""
        config = UIConfig()
        assert config.show_log_panel is True
        assert config.log_panel_height == 20
        assert "name" in config.table_columns
        assert "ip" in config.table_columns


class TestCacheConfig:
    """Tests for CacheConfig model."""

    def test_default_values(self):
        """Test default cache configuration."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_hours == 24

    def test_custom_values(self):
        """Test custom cache configuration."""
        config = CacheConfig(
            enabled=False,
            cache_dir="/custom/cache",
            ttl_hours=48
        )
        assert config.enabled is False
        assert config.cache_dir == "/custom/cache"
        assert config.ttl_hours == 48


class TestSoTImportConfig:
    """Tests for SoTImportConfig model."""

    def test_static_provider(self):
        """Test static provider configuration."""
        config = SoTImportConfig(
            name="test-static",
            type="static",
            hosts=[
                {"name": "host1", "ip": "10.0.0.1"}
            ]
        )
        assert config.name == "test-static"
        assert config.type == "static"
        assert len(config.hosts) == 1

    def test_netbox_provider(self):
        """Test NetBox provider configuration."""
        config = SoTImportConfig(
            name="test-netbox",
            type="netbox",
            url="https://netbox.example.com",
            token="test-token",
            verify_ssl=False
        )
        assert config.name == "test-netbox"
        assert config.type == "netbox"
        assert config.url == "https://netbox.example.com"


class TestConfig:
    """Tests for main Config model."""

    def test_default_values(self):
        """Test default main configuration."""
        config = Config()
        assert config.sshplex.session_prefix == "sshplex"
        assert config.ssh.username == "admin"
        assert config.tmux.layout == "tiled"
        assert config.cache.enabled is True

    def test_from_dict(self, sample_config_dict):
        """Test creating config from dictionary."""
        config = Config(**sample_config_dict)
        assert config.ssh.username == "testuser"
        assert config.ssh.retry.max_attempts == 3

    def test_nested_access(self, sample_config_dict):
        """Test accessing nested configuration values."""
        config = Config(**sample_config_dict)
        assert config.sot.import_[0].name == "test-static"
        assert config.sot.import_[0].type == "static"


class TestConfigPaths:
    """Tests for configuration path functions."""

    def test_get_default_config_path(self):
        """Test default config path."""
        path = get_default_config_path()
        assert str(path).endswith(".config/sshplex/sshplex.yaml")

    def test_get_template_config_path(self):
        """Test template config path."""
        path = get_template_config_path()
        assert path.name == "config-template.yaml"

    def test_ensure_config_directory(self, temp_config_dir):
        """Test config directory creation."""
        with patch('sshplex.lib.config.Path.home') as mock_home:
            mock_home.return_value = temp_config_dir
            result = ensure_config_directory()
            assert result.exists()
            assert result.name == "sshplex"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, temp_config_dir, sample_config_dict):
        """Test loading a valid configuration file."""
        config_file = temp_config_dir / "sshplex.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_dict, f)
        
        with patch('sshplex.lib.config.get_default_config_path') as mock_path:
            mock_path.return_value = config_file
            config = load_config(str(config_file))
            assert config.ssh.username == "testuser"

    def test_load_missing_config(self, temp_config_dir):
        """Test error handling for missing config file."""
        with pytest.raises(FileNotFoundError):
            load_config(str(temp_config_dir / "nonexistent.yaml"))

    def test_load_invalid_yaml(self, temp_config_dir):
        """Test error handling for invalid YAML."""
        config_file = temp_config_dir / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ValueError):
            load_config(str(config_file))

    def test_load_missing_required_field(self, temp_config_dir):
        """Test validation for missing required fields."""
        config_file = temp_config_dir / "incomplete.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({'sot': {'import': [{'type': 'netbox'}]}}, f)
        
        with pytest.raises(ValueError):
            load_config(str(config_file))
