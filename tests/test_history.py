"""Tests for recent/favorites history management."""

from pathlib import Path

from sshplex.lib.history import HistoryManager


def test_add_recent_tracks_order(tmp_path: Path) -> None:
    manager = HistoryManager(config_dir=tmp_path)
    manager.add_recent("h1", "10.0.0.1", max_recent=5)
    manager.add_recent("h2", "10.0.0.2", max_recent=5)
    recent = manager.get_recent(limit=5)

    assert len(recent) == 2
    assert recent[0].name == "h2"


def test_set_and_get_favorite(tmp_path: Path) -> None:
    manager = HistoryManager(config_dir=tmp_path)
    manager.set_favorite("h1", "10.0.0.1", True)

    assert manager.is_favorite("h1", "10.0.0.1") is True
    favorites = manager.get_favorites()
    assert len(favorites) == 1
    assert favorites[0].ip == "10.0.0.1"


def test_max_recent_limit(tmp_path: Path) -> None:
    manager = HistoryManager(config_dir=tmp_path)
    manager.add_recent("h1", "10.0.0.1", max_recent=2)
    manager.add_recent("h2", "10.0.0.2", max_recent=2)
    manager.add_recent("h3", "10.0.0.3", max_recent=2)

    recent = manager.get_recent(limit=10)
    assert len(recent) == 2
