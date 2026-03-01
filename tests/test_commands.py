"""Tests for shared command helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sshplex.lib.commands import clear_cache


def _minimal_config() -> SimpleNamespace:
    return SimpleNamespace(cache=SimpleNamespace(cache_dir="~/.cache/sshplex", ttl_hours=24))


def test_clear_cache_still_attempts_delete_when_metadata_missing(capsys) -> None:
    """clear_cache should delete files even when metadata can't be read."""
    config = _minimal_config()
    logger = MagicMock()

    fake_cache = MagicMock()
    fake_cache.get_cache_info.return_value = None
    fake_cache.clear_cache.return_value = True

    with patch("sshplex.lib.commands.HostCache", return_value=fake_cache):
        result = clear_cache(config, logger, no_cache_message="Clearing cache...")

    assert result == 0
    fake_cache.clear_cache.assert_called_once()
    captured = capsys.readouterr().out
    assert "Clearing cache" in captured
    assert "Cache cleared successfully" in captured


def test_clear_cache_returns_failure_when_delete_fails(capsys) -> None:
    """clear_cache should return non-zero when file deletion fails."""
    config = _minimal_config()
    logger = MagicMock()

    fake_cache = MagicMock()
    fake_cache.get_cache_info.return_value = None
    fake_cache.clear_cache.return_value = False

    with patch("sshplex.lib.commands.HostCache", return_value=fake_cache):
        result = clear_cache(config, logger, no_cache_message="Clearing cache...")

    assert result == 1
    fake_cache.clear_cache.assert_called_once()
    captured = capsys.readouterr().out
    assert "Failed to clear cache" in captured
