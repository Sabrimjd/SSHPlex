"""Tests for SSHplex tmux multiplexer manager."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from sshplex.lib.multiplexer.tmux import TmuxManager, TmuxError


class TestTmuxManager:
    """Tests for TmuxManager class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock()
        config.tmux.max_panes_per_window = 5
        config.tmux.control_with_iterm2 = False
        return config

    @pytest.fixture
    def mock_libtmux(self):
        """Mock libtmux module."""
        with patch('sshplex.lib.multiplexer.tmux.libtmux') as mock:
            yield mock

    @pytest.fixture
    def manager(self, mock_config):
        """Create a TmuxManager instance."""
        return TmuxManager(session_name='test-session', config=mock_config)

    def test_init_with_session_name(self, mock_config):
        """Test initialization with custom session name."""
        manager = TmuxManager(session_name='custom-session', config=mock_config)
        assert manager.session_name == 'custom-session'
        assert manager.config == mock_config

    def test_init_without_session_name(self, mock_config):
        """Test initialization generates default session name."""
        manager = TmuxManager(session_name=None, config=mock_config)
        assert manager.session_name.startswith('sshplex-')

    def test_init_default_max_panes(self, mock_config):
        """Test default max panes constant."""
        assert TmuxManager.DEFAULT_MAX_PANES == 5

    def test_generate_unique_session_name_available(self, manager, mock_libtmux):
        """Test unique name generation when name is available."""
        mock_server = MagicMock()
        mock_server.has_session.return_value = False
        manager.server = mock_server
        
        result = manager._generate_unique_session_name('test-session')
        assert result == 'test-session'

    def test_generate_unique_session_name_exists(self, manager, mock_libtmux):
        """Test unique name generation when name exists."""
        mock_server = MagicMock()
        mock_server.has_session.side_effect = lambda name: name == 'test-session'
        manager.server = mock_server
        
        result = manager._generate_unique_session_name('test-session')
        assert result == 'test-session-1'
        assert result != 'test-session'

    def test_generate_unique_session_name_multiple_exists(self, manager, mock_libtmux):
        """Test unique name generation when multiple names exist."""
        mock_server = MagicMock()
        existing = ['test-session', 'test-session-1', 'test-session-2']
        mock_server.has_session.side_effect = lambda name: name in existing
        manager.server = mock_server
        
        result = manager._generate_unique_session_name('test-session')
        assert result == 'test-session-3'

    def test_init_server_success(self, manager, mock_libtmux):
        """Test successful server initialization."""
        result = manager._init_server()
        assert result is True
        assert manager.server is not None

    def test_init_server_already_initialized(self, manager, mock_libtmux):
        """Test server init when already initialized."""
        manager.server = MagicMock()
        result = manager._init_server()
        assert result is True

    def test_create_session_success(self, manager, mock_libtmux):
        """Test successful session creation."""
        mock_server = MagicMock()
        mock_server.has_session.return_value = False
        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_session.attached_window = mock_window
        mock_server.new_session.return_value = mock_session
        mock_libtmux.Server.return_value = mock_server
        
        result = manager.create_session()
        
        assert result is True
        assert manager.session is not None
        assert manager._initialized is True

    def test_create_session_already_exists(self, manager, mock_libtmux):
        """Test session creation when session already exists."""
        mock_server = MagicMock()
        mock_server.has_session.return_value = True
        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_session.attached_window = mock_window
        mock_server.sessions.get.return_value = mock_session
        mock_libtmux.Server.return_value = mock_server
        
        result = manager.create_session()
        
        assert result is True

    def test_get_session_name(self, manager):
        """Test getting session name."""
        assert manager.get_session_name() == 'test-session'

    def test_send_command_no_pane(self, manager):
        """Test sending command when pane doesn't exist."""
        result = manager.send_command('nonexistent-host', 'ls')
        assert result is False

    def test_send_command_success(self, manager):
        """Test successful command sending."""
        mock_pane = MagicMock()
        manager.panes['test-host'] = mock_pane
        
        result = manager.send_command('test-host', 'ls -la')
        
        assert result is True
        mock_pane.send_keys.assert_called_once_with('ls -la', enter=True)

    def test_set_pane_title_no_pane(self, manager):
        """Test setting title when pane doesn't exist."""
        result = manager.set_pane_title('nonexistent-host', 'My Title')
        assert result is False

    def test_set_pane_title_success(self, manager):
        """Test successful pane title setting."""
        mock_pane = MagicMock()
        manager.panes['test-host'] = mock_pane
        
        result = manager.set_pane_title('test-host', 'My Title')
        
        assert result is True
        mock_pane.send_keys.assert_called_once()

    def test_broadcast_command(self, manager):
        """Test broadcasting command to all panes."""
        mock_pane1 = MagicMock()
        mock_pane2 = MagicMock()
        manager.panes['host1'] = mock_pane1
        manager.panes['host2'] = mock_pane2
        
        result = manager.broadcast_command('uptime')
        
        assert result is True
        mock_pane1.send_keys.assert_called_once()
        mock_pane2.send_keys.assert_called_once()

    def test_broadcast_command_partial_failure(self, manager):
        """Test broadcast when some panes fail."""
        mock_pane1 = MagicMock()
        mock_pane2 = MagicMock()
        mock_pane2.send_keys.side_effect = Exception('Failed')
        
        manager.panes['host1'] = mock_pane1
        manager.panes['host2'] = mock_pane2
        
        result = manager.broadcast_command('uptime')
        
        assert result is False

    def test_close_session(self, manager, mock_libtmux):
        """Test session closing."""
        mock_session = MagicMock()
        manager.session = mock_session
        manager.panes['host1'] = MagicMock()
        manager.windows[0] = MagicMock()
        manager.current_window_pane_count = 3
        
        manager.close_session()
        
        mock_session.kill_session.assert_called_once()
        assert manager.session is None
        assert len(manager.panes) == 0
        assert len(manager.windows) == 0
        assert manager.current_window_pane_count == 0

    def test_setup_broadcast_keybinding_success(self, manager):
        """Test successful broadcast keybinding setup."""
        mock_session = MagicMock()
        manager.session = mock_session
        
        result = manager.setup_broadcast_keybinding()
        
        assert result is True
        mock_session.cmd.assert_called_once()

    def test_setup_broadcast_keybinding_no_session(self, manager):
        """Test keybinding setup without session."""
        manager.session = None
        result = manager.setup_broadcast_keybinding()
        assert result is False

    def test_enable_broadcast_success(self, manager):
        """Test enabling broadcast mode."""
        mock_window = MagicMock()
        mock_window.panes = [MagicMock(), MagicMock()]
        manager.session = MagicMock()
        manager.windows[0] = mock_window
        
        result = manager.enable_broadcast()
        
        assert result is True
        mock_window.cmd.assert_called()

    def test_disable_broadcast_success(self, manager):
        """Test disabling broadcast mode."""
        mock_window = MagicMock()
        manager.session = MagicMock()
        manager.windows[0] = mock_window
        
        result = manager.disable_broadcast()
        
        assert result is True

    def test_setup_tiled_layout_success(self, manager):
        """Test setting up tiled layout."""
        mock_window = MagicMock()
        mock_window.panes = [MagicMock(), MagicMock(), MagicMock()]
        manager.windows[0] = mock_window
        
        result = manager.setup_tiled_layout()
        
        assert result is True
        mock_window.select_layout.assert_called_with('tiled')

    def test_setup_tiled_layout_single_pane(self, manager):
        """Test tiled layout with single pane (no effect)."""
        mock_window = MagicMock()
        mock_window.panes = [MagicMock()]
        manager.windows[0] = mock_window
        
        result = manager.setup_tiled_layout()
        
        assert result is False


class TestTmuxManagerAttach:
    """Tests for tmux session attachment."""

    @pytest.fixture
    def manager(self):
        """Create a TmuxManager instance for attach tests."""
        config = MagicMock()
        config.tmux.control_with_iterm2 = False
        manager = TmuxManager(session_name='test-session', config=config)
        manager.session = MagicMock()
        return manager

    def test_attach_standard_calls_execlp(self, manager):
        """Test standard attach uses os.execlp."""
        with patch('os.execlp') as mock_execlp:
            manager._attach_standard()
            mock_execlp.assert_called_once_with('tmux', 'tmux', 'attach-session', '-t', 'test-session')

    def test_attach_iterm2_running(self, manager):
        """Test iTerm2 attach when iTerm2 is running."""
        manager.config.tmux.control_with_iterm2 = True
        manager.system = 'darwin'
        
        with patch('subprocess.run') as mock_run:
            with patch('subprocess.Popen') as mock_popen:
                mock_run.return_value = MagicMock(returncode=0, stdout='true')
                
                manager._attach_iterm2()
                
                mock_popen.assert_called_once()
                args = mock_popen.call_args[0][0]
                assert 'osascript' in args

    def test_attach_iterm2_not_running(self, manager):
        """Test iTerm2 attach when iTerm2 is not running."""
        manager.config.tmux.control_with_iterm2 = True
        manager.system = 'darwin'
        
        with patch('subprocess.run') as mock_run:
            with patch('subprocess.Popen') as mock_popen:
                mock_run.return_value = MagicMock(returncode=1, stdout='')
                
                manager._attach_iterm2()
                
                mock_popen.assert_called_once()


class TestTmuxError:
    """Tests for TmuxError exception."""

    def test_tmux_error_message(self):
        """Test TmuxError exception message."""
        error = TmuxError("Session creation failed")
        assert str(error) == "Session creation failed"
