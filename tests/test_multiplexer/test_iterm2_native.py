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

    def test_create_session_returns_true(self, manager):
        """Test that create_session returns True."""
        assert manager.create_session() is True

    def test_create_pane_queues_session(self, manager):
        """Test that create_pane queues a session."""
        result = manager.create_pane('host1', 'ssh user@host1')
        assert result is True
        assert ('host1', 'ssh user@host1') in manager._pending_sessions

    def test_create_pane_allows_duplicate_host_labels(self, manager):
        """Test that queue preserves duplicate host labels."""
        manager.create_pane('host1', 'ssh user@10.0.0.1')
        manager.create_pane('host1', 'ssh user@10.0.0.2')
        assert len(manager._pending_sessions) == 2


class TestITerm2NativeManagerBroadcast:
    """Tests for broadcast functionality."""

    def test_enable_broadcast(self, manager):
        """Test enable broadcast sets flag."""
        result = manager.enable_broadcast()
        assert result is True
        assert manager._broadcast_enabled is True

    def test_disable_broadcast(self, manager):
        """Test disable broadcast clears flag."""
        manager._broadcast_enabled = True
        result = manager.disable_broadcast()
        assert result is True
        assert manager._broadcast_enabled is False

    def test_broadcast_command_without_enable(self, manager):
        """Test broadcasting command fails when not enabled."""
        manager._broadcast_enabled = False
        result = manager.broadcast_command('ls -la')
        assert result is False


class TestITerm2NativeManagerCommand:
    """Tests for command sending."""

    def test_send_command_returns_false(self, manager):
        """Test sending command returns False (not supported after creation)."""
        result = manager.send_command('host1', 'ls -la')
        assert result is False


class TestITerm2NativeManagerClose:
    """Tests for session closing."""

    def test_close_session_clears_pending(self, manager):
        """Test closing session clears pending sessions."""
        manager._pending_sessions.append(('host1', 'ssh user@host1'))
        manager._broadcast_enabled = True
        manager.close_session()
        assert len(manager._pending_sessions) == 0
        assert manager._broadcast_enabled is False


class TestITerm2NativeManagerAttach:
    """Tests for attach functionality."""

    def test_get_session_name(self, manager):
        """Test getting session name."""
        assert manager.get_session_name() == 'test-session'

    def test_attach_to_session_no_sessions(self, manager, capsys):
        """Test attach with no sessions shows warning."""
        manager.attach_to_session(auto_attach=False)
        captured = capsys.readouterr()
        assert 'No SSH connections' in captured.out


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
