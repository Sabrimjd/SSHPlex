"""Tests for command snippets management."""

from pathlib import Path

from sshplex.lib.snippets import Snippet, SnippetManager


def test_get_default_snippets_has_expected_items() -> None:
    snippets = SnippetManager.get_default_snippets()
    assert len(snippets) == 10
    assert snippets[0].name == "Disk Usage"
    assert snippets[-1].name == "Service Status"


def test_ensure_snippets_file_writes_defaults(tmp_path: Path) -> None:
    manager = SnippetManager(config_dir=tmp_path)
    manager.ensure_snippets_file()
    assert manager.snippets_file.exists()

    loaded = manager.load_snippets()
    assert len(loaded) == 10
    assert loaded[1].command == "free -h"


def test_save_and_load_snippets_round_trip(tmp_path: Path) -> None:
    manager = SnippetManager(config_dir=tmp_path)
    snippets = [
        Snippet(
            name="Custom",
            description="Custom snippet",
            command="echo ok",
            tags=["custom"],
        )
    ]

    manager.save_snippets(snippets)
    loaded = manager.load_snippets()
    assert len(loaded) == 1
    assert loaded[0].name == "Custom"
    assert loaded[0].tags == ["custom"]
