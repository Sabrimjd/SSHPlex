"""Regression tests for iTerm2 session manager row targeting."""

from __future__ import annotations

from types import SimpleNamespace

from sshplex.lib.ui.session_manager import ITerm2ManagedTab, ITerm2SessionManager


class FakeTable:
    """Simple DataTable test double with the subset we need."""

    def __init__(self) -> None:
        self.cursor_row = 0
        self.rows: list[tuple[tuple[str, ...], str | None]] = []

    def clear(self) -> None:
        self.rows.clear()

    def add_row(self, *values: str, key: str | None = None) -> None:
        self.rows.append((values, key))

    def move_cursor(self, row: int) -> None:
        self.cursor_row = row


def test_kill_session_targets_visible_filtered_tab() -> None:
    """Kill action should map to the visible filtered row, not raw tabs index."""
    manager = ITerm2SessionManager(config=SimpleNamespace(), current_session_name="current")
    manager.table = FakeTable()
    manager.tabs = [
        ITerm2ManagedTab(
            tab_id="tab-other",
            window_id="w1",
            session_name="other",
            hostname="other-host",
            pane_count=1,
        ),
        ITerm2ManagedTab(
            tab_id="tab-current",
            window_id="w1",
            session_name="current",
            hostname="current-host",
            pane_count=2,
        ),
    ]

    killed: dict[str, ITerm2ManagedTab] = {}

    def _capture_kill(tab: ITerm2ManagedTab) -> None:
        killed["tab"] = tab

    manager._do_kill_tab = _capture_kill  # type: ignore[method-assign]
    manager.populate_table()

    assert [tab.tab_id for tab in manager.visible_tabs] == ["tab-current"]
    manager.table.cursor_row = 0

    manager.action_kill_session()

    assert killed["tab"].tab_id == "tab-current"
