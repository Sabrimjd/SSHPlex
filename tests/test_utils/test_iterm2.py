"""Tests for SSHplex iTerm2 integration utilities."""

from unittest.mock import MagicMock, patch

import pytest

from sshplex.lib.utils.iterm2 import (
    TMUX_CONTROL_MODE_FLAG,
    ITerm2Error,
    check_iterm2_installed,
    check_iterm2_running,
    escape_applescript_string,
    generate_iterm2_applescript,
    get_iterm2_status,
    is_macos,
    launch_iterm2_session,
)


class TestIsMacos:
    """Tests for is_macos function."""

    @patch('sshplex.lib.utils.iterm2.platform.system')
    def test_is_macos_returns_true(self, mock_system):
        """Test returns True on macOS."""
        mock_system.return_value = "Darwin"
        assert is_macos() is True

    @patch('sshplex.lib.utils.iterm2.platform.system')
    def test_is_macos_returns_false_linux(self, mock_system):
        """Test returns False on Linux."""
        mock_system.return_value = "Linux"
        assert is_macos() is False

    @patch('sshplex.lib.utils.iterm2.platform.system')
    def test_is_macos_case_insensitive(self, mock_system):
        """Test is case insensitive."""
        mock_system.return_value = "DARWIN"
        assert is_macos() is True


class TestCheckITerm2Installed:
    """Tests for check_iterm2_installed function."""

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.subprocess.run')
    def test_installed_returns_true(self, mock_run, mock_is_macos):
        """Test returns True when iTerm2 is installed."""
        mock_is_macos.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="true")

        assert check_iterm2_installed() is True

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.subprocess.run')
    def test_not_installed_returns_false(self, mock_run, mock_is_macos):
        """Test returns False when iTerm2 is not installed."""
        mock_is_macos.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="false")

        assert check_iterm2_installed() is False

    @patch('sshplex.lib.utils.iterm2.is_macos')
    def test_returns_false_on_linux(self, mock_is_macos):
        """Test returns False on non-macOS systems."""
        mock_is_macos.return_value = False
        assert check_iterm2_installed() is False


class TestCheckITerm2Running:
    """Tests for check_iterm2_running function."""

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.subprocess.run')
    def test_running_returns_true(self, mock_run, mock_is_macos):
        """Test returns True when iTerm2 is running."""
        mock_is_macos.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="true")

        assert check_iterm2_running() is True

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.subprocess.run')
    def test_not_running_returns_false(self, mock_run, mock_is_macos):
        """Test returns False when iTerm2 is not running."""
        mock_is_macos.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="false")

        assert check_iterm2_running() is False


class TestEscapeAppleScriptString:
    """Tests for escape_applescript_string function."""

    def test_escape_quotes(self):
        """Test escaping double quotes."""
        assert escape_applescript_string('hello "world"') == 'hello \\"world\\"'

    def test_escape_backslashes(self):
        """Test escaping backslashes."""
        assert escape_applescript_string('path\\to\\file') == 'path\\\\to\\\\file'

    def test_escape_both(self):
        """Test escaping both quotes and backslashes."""
        assert escape_applescript_string('say "hello\\world"') == 'say \\"hello\\\\world\\"'

    def test_no_special_chars(self):
        """Test string with no special characters."""
        assert escape_applescript_string('simple-session') == 'simple-session'

    def test_injection_attempt(self):
        """Test escaping potential injection strings."""
        # Attempt to break out of AppleScript string
        malicious = 'session"; do shell script "rm -rf /'
        escaped = escape_applescript_string(malicious)
        assert '"' not in escaped or '\\"' in escaped


class TestGenerateITerm2AppleScript:
    """Tests for generate_iterm2_applescript function."""

    def test_new_window_script(self):
        """Test generating script for new window."""
        script = generate_iterm2_applescript("test-session", "new-window", "Default")

        assert "create window with profile" in script
        assert "test-session" in script
        assert TMUX_CONTROL_MODE_FLAG in script

    def test_new_tab_script(self):
        """Test generating script for new tab."""
        script = generate_iterm2_applescript("test-session", "new-tab", "Default")

        assert "create tab with profile" in script
        assert "tell current window" in script
        assert "test-session" in script

    def test_invalid_target_raises_error(self):
        """Test invalid target raises ITerm2Error."""
        with pytest.raises(ITerm2Error, match="Invalid iTerm2 target"):
            generate_iterm2_applescript("test", "invalid-target")

    def test_session_name_escaped(self):
        """Test session name is escaped in script."""
        script = generate_iterm2_applescript('session"; rm -rf /', "new-window")

        # Should not contain unescaped quotes
        assert 'session\\"' in script
        assert 'session"; rm -rf /' not in script

    def test_profile_name_escaped(self):
        """Test profile name is escaped in script."""
        script = generate_iterm2_applescript("test", "new-window", 'profile"; exit')

        # Should contain escaped quotes
        assert '\\"' in script


class TestLaunchITerm2Session:
    """Tests for launch_iterm2_session function."""

    @patch('sshplex.lib.utils.iterm2.is_macos')
    def test_fails_on_linux_with_fallback(self, mock_is_macos):
        """Test returns False on Linux with fallback enabled."""
        mock_is_macos.return_value = False

        result = launch_iterm2_session("test-session", fallback_to_standard=True)
        assert result is False

    @patch('sshplex.lib.utils.iterm2.is_macos')
    def test_raises_on_linux_without_fallback(self, mock_is_macos):
        """Test raises ITerm2Error on Linux without fallback."""
        mock_is_macos.return_value = False

        with pytest.raises(ITerm2Error, match="only supported on macOS"):
            launch_iterm2_session("test-session", fallback_to_standard=False)

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.check_iterm2_installed')
    def test_fails_if_not_installed_with_fallback(self, mock_installed, mock_is_macos):
        """Test returns False if iTerm2 not installed with fallback."""
        mock_is_macos.return_value = True
        mock_installed.return_value = False

        result = launch_iterm2_session("test-session", fallback_to_standard=True)
        assert result is False

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.check_iterm2_installed')
    @patch('sshplex.lib.utils.iterm2.subprocess.Popen')
    def test_success_launch(self, mock_popen, mock_installed, mock_is_macos):
        """Test successful iTerm2 launch."""
        mock_is_macos.return_value = True
        mock_installed.return_value = True
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process still running
        mock_popen.return_value = mock_process

        result = launch_iterm2_session("test-session", fallback_to_standard=True)
        assert result is True
        mock_popen.assert_called_once()

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.check_iterm2_installed')
    @patch('sshplex.lib.utils.iterm2.subprocess.Popen')
    def test_handles_immediate_failure(self, mock_popen, mock_installed, mock_is_macos):
        """Test handles immediate process failure."""
        mock_is_macos.return_value = True
        mock_installed.return_value = True
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process exited with error
        mock_process.communicate.return_value = (b"", b"osascript error")
        mock_popen.return_value = mock_process

        result = launch_iterm2_session("test-session", fallback_to_standard=True)
        assert result is False


class TestGetITerm2Status:
    """Tests for get_iterm2_status function."""

    @patch('sshplex.lib.utils.iterm2.is_macos')
    @patch('sshplex.lib.utils.iterm2.check_iterm2_installed')
    @patch('sshplex.lib.utils.iterm2.check_iterm2_running')
    def test_returns_status_dict(self, mock_running, mock_installed, mock_is_macos):
        """Test returns status dictionary."""
        mock_is_macos.return_value = True
        mock_installed.return_value = True
        mock_running.return_value = False

        status = get_iterm2_status()

        assert "platform" in status
        assert "is_macos" in status
        assert "installed" in status
        assert "running" in status
        assert status["is_macos"] is True
        assert status["installed"] is True
        assert status["running"] is False


class TestConstants:
    """Tests for module constants."""

    def test_tmux_control_mode_flag(self):
        """Test control mode flag is correct."""
        assert TMUX_CONTROL_MODE_FLAG == "-CC"
