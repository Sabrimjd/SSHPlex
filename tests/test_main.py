"""Tests for lightweight main entrypoint helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from sshplex.main import check_system_dependencies


def _config_with_backend(backend: str) -> SimpleNamespace:
    return SimpleNamespace(tmux=SimpleNamespace(backend=backend))


def test_check_system_dependencies_skips_tmux_for_iterm2_native() -> None:
    """iTerm2-native backend should not require tmux binary."""
    config = _config_with_backend("iterm2-native")
    with patch("sshplex.main.shutil.which") as mock_which:
        assert check_system_dependencies(config) is True
        mock_which.assert_not_called()


def test_check_system_dependencies_requires_tmux_for_tmux_backend() -> None:
    """tmux backend should fail dependency check when tmux is missing."""
    config = _config_with_backend("tmux")
    with patch("sshplex.main.shutil.which", return_value=None):
        assert check_system_dependencies(config) is False
