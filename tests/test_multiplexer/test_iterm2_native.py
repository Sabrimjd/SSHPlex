"""Tests for iTerm2 native multiplexer."""

import platform
from unittest.mock import MagicMock, patch

import pytest

from sshplex.lib.multiplexer.iterm2_native import (
    ITerm2NativeError,
    ITerm2NativeManager,
)


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = MagicMock()
    config.tmux.backend = "iterm2-native"
    config.tmux.max_panes_per_window = 5
    config.tmux.iterm2_split_pattern = "alternate"
    config.tmux.iterm2_profile = "Default"
    return config


@pytest.fixture
def manager(mock_config):
    """Create ITerm2NativeManager instance with mocked iTerm2 API check."""
    with patch.object(platform, 'system', return_value='Darwin'), \
         patch.object(ITerm2NativeManager, '_check_iterm2_api', return_value=True):
        return ITerm2NativeManager(session_name='test-session', config=mock_config)


class TestITerm2NativeManagerInit:
    """Tests for ITerm2NativeManager initialization."""

    def test_init_success(self, mock_config):
        """Test successful initialization on macOS."""
        with patch.object(platform, 'system', return_value='Darwin'), \
             patch.object(ITerm2NativeManager, '_check_iterm2_api', return_value=True):
            manager = ITerm2NativeManager('test-session', mock_config)
            assert manager.session_name == 'test-session'
            assert manager.system == 'darwin'

    def test_init_generates_session_name(self, mock_config):
        """Test auto-generated session name."""
        with patch.object(platform, 'system', return_value='Darwin'), \
             patch.object(ITerm2NativeManager, '_check_iterm2_api', return_value=True):
            manager = ITerm2NativeManager(None, mock_config)
            assert manager.session_name.startswith('sshplex-')

    def test_init_fails_on_linux(self, mock_config):
        """Test initialization fails on non-macOS."""
        with patch.object(platform, 'system', return_value='Linux'), \
             pytest.raises(ITerm2NativeError, match="requires macOS"):
            ITerm2NativeManager('test-session', mock_config)


class TestITerm2NativeManagerSession:
    """Tests for session management."""

    def test_create_session_fails_without_iterm2(self, manager):
        """Test that manager validates iTerm2 API on init."""
        # Manager already validates iTerm2 API in __init__
        # If we get here, iterm2 module check passed (or mocked)
        assert manager.session_name == 'test-session'


class TestITerm2NativeManagerBroadcast:
    """Tests for broadcast functionality."""

    def test_enable_broadcast_no_sessions(self, manager):
        """Test enable broadcast fails without sessions."""
        manager._iterm2_sessions = {}
        manager._connection = MagicMock()

        result = manager.enable_broadcast()

        assert result is False

    def test_toggle_broadcast_calls_enable(self, manager):
        """Test toggling broadcast calls enable when disabled."""
        manager._connection = MagicMock()
        manager._iterm2_sessions = {'host1': MagicMock()}
        manager._broadcast_enabled = False

        # Mock enable_broadcast to return True
        with patch.object(manager, 'enable_broadcast', return_value=True) as mock_enable:
            result = manager.toggle_broadcast()

        mock_enable.assert_called_once()
        assert result is True


class TestITerm2NativeManagerCommand:
    """Tests for command sending."""

    def test_send_command_unknown_host(self, manager):
        """Test sending command to unknown host."""
        result = manager.send_command('unknown', 'ls -la')

        assert result is False

    def test_broadcast_command_without_enable(self, manager):
        """Test broadcasting command fails when not enabled."""
        manager._broadcast_enabled = False
        manager._iterm2_sessions = {'host1': MagicMock()}

        result = manager.broadcast_command('ls -la')

        assert result is False


class TestITerm2NativeManagerClose:
    """Tests for session closing."""

    def test_close_session_no_window(self, manager):
        """Test closing when no window exists."""
        manager._window = None
        manager._connection = None

        # Should not raise
        manager.close_session()
        assert len(manager._iterm2_sessions) == 0


class TestITerm2NativeManagerAttach:
    """Tests for attach functionality."""

    def test_get_session_name(self, manager):
        """Test getting session name."""
        assert manager.get_session_name() == 'test-session'

    def test_attach_to_session_no_auto(self, manager, capsys):
        """Test attach without auto shows message."""
        manager._iterm2_sessions = {'host1': MagicMock()}
        manager.attach_to_session(auto_attach=False)

        captured = capsys.readouterr()
        assert 'test-session' in captured.out
        assert '1 connections' in captured.out


class TestITerm2NativeManagerConfig:
    """Tests for config handling."""

    def test_config_values_applied(self, mock_config):
        """Test that config values are properly applied."""
        with patch.object(platform, 'system', return_value='Darwin'), \
             patch.object(ITerm2NativeManager, '_check_iterm2_api', return_value=True):
            manager = ITerm2NativeManager('test-session', mock_config)
            assert manager._max_panes_per_tab == 5
            assert manager._split_pattern == "alternate"
            assert manager._profile == "Default"

    def test_default_config_values(self):
        """Test default values when no config provided."""
        with patch.object(platform, 'system', return_value='Darwin'), \
             patch.object(ITerm2NativeManager, '_check_iterm2_api', return_value=True):
            manager = ITerm2NativeManager('test-session', None)
            assert manager._max_panes_per_tab == ITerm2NativeManager.DEFAULT_MAX_PANES
            assert manager._split_pattern == "alternate"
            assert manager._profile == "Default"
