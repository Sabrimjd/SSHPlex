"""SSHplex TUI tmux session manager widget."""

import asyncio
from typing import Any, List, Optional

import libtmux
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from ..logger import get_logger


class ConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog for destructive actions."""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #confirm-dialog {
        width: 50;
        height: 10;
        border: thick $error;
        background: $surface;
        padding: 1;
    }

    #confirm-title {
        text-align: center;
        color: $text;
        margin-bottom: 1;
    }

    #confirm-text {
        text-align: center;
        color: $text;
        margin-bottom: 1;
    }

    #confirm-buttons {
        align: center middle;
        height: 3;
    }

    #confirm-yes {
        margin-right: 2;
    }

    #confirm-no {
        margin-left: 2;
    }
    """

    BINDINGS = [
        Binding("enter", "confirm_yes", "Yes", show=False),
        Binding("y", "confirm_yes", "Yes", show=True),
        Binding("n", "confirm_no", "No", show=True),
        Binding("escape", "confirm_no", "Cancel", show=False),
    ]

    def __init__(self, message: str, title: str = "Confirm") -> None:
        super().__init__()
        self.message = message
        self.title = title

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Static(f"⚠️  {self.title}", id="confirm-title")
            yield Static(self.message, id="confirm-text")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", id="confirm-yes", variant="error")
                yield Button("No", id="confirm-no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)


class TmuxSession:
    """Simple tmux session data structure."""

    def __init__(self, name: str, session_id: str, created: str, windows: int, attached: bool = False):
        self.name = name
        self.session_id = session_id
        self.created = created
        self.windows = windows
        self.attached = attached

    def __str__(self) -> str:
        status = "📎" if self.attached else "💤"
        return f"{status} {self.name} ({self.windows} windows)"


class ITerm2ManagedTab:
    """Simple iTerm2 managed tab data structure."""

    def __init__(
        self,
        tab_id: str,
        window_id: str,
        session_name: str,
        hostname: str,
        pane_count: int,
    ):
        self.tab_id = tab_id
        self.window_id = window_id
        self.session_name = session_name
        self.hostname = hostname
        self.pane_count = pane_count


class ITerm2SessionManager(ModalScreen):
    """Modal screen for managing SSHplex-managed iTerm2 native tabs."""

    CSS = """
    ITerm2SessionManager {
        align: center middle;
    }

    #session-dialog {
        width: 90;
        height: 22;
        border: thick $primary 60%;
        background: $surface;
    }

    #session-table {
        height: 1fr;
        margin: 1;
    }

    #session-header {
        height: 3;
        margin: 1;
        text-align: center;
        background: $primary;
        color: $text;
    }

    #session-footer {
        height: 3;
        margin: 1;
        text-align: center;
        background: $surface;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("k", "kill_session", "Kill Tab", show=True),
        Binding("shift+k", "kill_current_session", "Kill Current Session", show=True),
        Binding("r", "refresh_sessions", "Refresh", show=True),
        Binding("escape", "close_manager", "Close", show=True),
        Binding("q", "close_manager", "Close", show=False),
        Binding("up", "move_up", "Up", show=False),
        Binding("down,j", "move_down", "Down", show=False),
    ]

    def __init__(self, config: Any, current_session_name: Optional[str] = None) -> None:
        super().__init__()
        self.logger = get_logger()
        self.config = config
        self.tabs: List[ITerm2ManagedTab] = []
        self.table: Optional[DataTable] = None
        self.current_session_name = current_session_name

    def compose(self) -> ComposeResult:
        with Container(id="session-dialog"):
            yield Static("🖥️  SSHplex - iTerm2 Native Session Manager", id="session-header")
            yield DataTable(id="session-table", cursor_type="row")
            yield Static("K: Kill Tab | Shift+K: Kill Current Session | R: Refresh | ESC: Close", id="session-footer")

    def on_mount(self) -> None:
        self.table = self.query_one("#session-table", DataTable)
        self.table.add_column("Host", width=26)
        self.table.add_column("Session", width=24)
        self.table.add_column("Window", width=18)
        self.table.add_column("Panes", width=8)
        self.table.focus()
        self.run_worker(self.load_sessions(), name="iterm2_load_sessions")

    def _fetch_tabs_blocking(self) -> List[ITerm2ManagedTab]:
        """Fetch SSHplex-managed iTerm2 tabs in a background thread."""
        try:
            import iterm2
        except ImportError as e:
            raise RuntimeError("iterm2 API missing") from e

        loaded: List[ITerm2ManagedTab] = []

        async def _load(connection: Any) -> None:
            app = await iterm2.async_get_app(connection)
            if app is None:
                raise RuntimeError("Failed to load iTerm2 app")

            await app.async_refresh()
            for window in app.windows:
                for tab in window.tabs:
                    try:
                        managed = bool(await tab.async_get_variable("user.sshplex_managed"))
                    except Exception:
                        managed = False

                    if not managed:
                        continue

                    try:
                        session_name = str(await tab.async_get_variable("user.sshplex_session_name") or "unknown")
                    except Exception:
                        session_name = "unknown"

                    try:
                        hostname = str(await tab.async_get_variable("user.sshplex_hostname") or "unknown")
                    except Exception:
                        hostname = "unknown"

                    loaded.append(
                        ITerm2ManagedTab(
                            tab_id=tab.tab_id,
                            window_id=window.window_id,
                            session_name=session_name,
                            hostname=hostname,
                            pane_count=len(tab.sessions),
                        )
                    )

        try:
            iterm2.run_until_complete(_load)
        except SystemExit as e:
            raise RuntimeError("Failed to connect to iTerm2 API") from e
        return loaded

    async def load_sessions(self) -> None:
        try:
            self.tabs = await asyncio.to_thread(self._fetch_tabs_blocking)
            self.populate_table()
            if self.table and self.tabs:
                self.table.move_cursor(row=0)
            self.logger.info(f"SSHplex: Loaded {len(self.tabs)} managed iTerm2 tabs")
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to load iTerm2 managed tabs: {e}")
            if self.table is not None:
                self.table.clear()
                self.table.add_row("Error loading tabs", str(e), "-", "-")

    def populate_table(self) -> None:
        if not self.table:
            return

        self.table.clear()
        if not self.tabs:
            self.table.add_row("No SSHplex iTerm2 tabs", "-", "-", "-")
            return

        for tab in self.tabs:
            self.table.add_row(
                tab.hostname,
                tab.session_name,
                tab.window_id,
                str(tab.pane_count),
                key=tab.tab_id,
            )

    def action_move_up(self) -> None:
        if self.table and self.tabs:
            current_row = self.table.cursor_row
            if current_row > 0:
                self.table.move_cursor(row=current_row - 1)

    def action_move_down(self) -> None:
        if self.table and self.tabs:
            current_row = self.table.cursor_row
            if current_row < len(self.tabs) - 1:
                self.table.move_cursor(row=current_row + 1)

    def action_kill_session(self) -> None:
        if not self.table or not self.tabs:
            return

        cursor_row = self.table.cursor_row
        if cursor_row < 0 or cursor_row >= len(self.tabs):
            return

        tab = self.tabs[cursor_row]
        self._do_kill_tab(tab)

    def _do_kill_tab(self, tab_item: ITerm2ManagedTab) -> None:
        self.run_worker(self._do_kill_tab_async(tab_item), name="iterm2_kill_tab")

    def _close_tab_blocking(self, tab_item: ITerm2ManagedTab) -> None:
        """Close one iTerm2 tab in a background thread."""
        try:
            import iterm2
        except ImportError as e:
            raise RuntimeError("iterm2 API missing") from e

        result = {"closed": False}

        async def _kill(connection: Any) -> None:
            app = await iterm2.async_get_app(connection)
            if app is None:
                raise RuntimeError("Failed to load iTerm2 app")

            await app.async_refresh()
            for window in app.windows:
                for tab in window.tabs:
                    if tab.tab_id == tab_item.tab_id:
                        await tab.async_close(force=True)
                        result["closed"] = True
                        return

        try:
            iterm2.run_until_complete(_kill)
        except SystemExit as e:
            raise RuntimeError("Failed to connect to iTerm2 API") from e

        if not result["closed"]:
            raise RuntimeError("Tab not found")

    async def _do_kill_tab_async(self, tab_item: ITerm2ManagedTab) -> None:
        try:
            await asyncio.to_thread(self._close_tab_blocking, tab_item)
            self.logger.info(f"SSHplex: Closed managed iTerm2 tab '{tab_item.hostname}'")
            await self.load_sessions()
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to close iTerm2 tab '{tab_item.hostname}': {e}")

    def action_kill_current_session(self) -> None:
        """Kill all tabs belonging to the current SSHplex native session."""
        if not self.current_session_name:
            self.logger.warning("SSHplex: No current native session to kill")
            return

        self.run_worker(
            self._kill_current_session_async(self.current_session_name),
            name="iterm2_kill_current_session",
        )

    async def _kill_current_session_async(self, session_name: str) -> None:
        session_tabs = [tab for tab in self.tabs if tab.session_name == session_name]
        if not session_tabs:
            self.logger.warning(f"SSHplex: No tabs found for native session '{session_name}'")
            return

        closed_count = 0
        for tab in session_tabs:
            try:
                await asyncio.to_thread(self._close_tab_blocking, tab)
                closed_count += 1
            except Exception as e:
                self.logger.error(f"SSHplex: Failed to close tab '{tab.hostname}' in '{session_name}': {e}")

        self.logger.info(f"SSHplex: Closed {closed_count}/{len(session_tabs)} tabs for '{session_name}'")
        await self.load_sessions()

    def action_refresh_sessions(self) -> None:
        self.run_worker(self.load_sessions(), name="iterm2_refresh_sessions")

    def action_close_manager(self) -> None:
        self.dismiss()


class TmuxSessionManager(ModalScreen):
    """Modal screen for managing tmux sessions."""

    CSS = """
    TmuxSessionManager {
        align: center middle;
    }

    #session-dialog {
        width: 80;
        height: 20;
        border: thick $primary 60%;
        background: $surface;
    }

    #session-table {
        height: 1fr;
        margin: 1;
    }

    #session-header {
        height: 3;
        margin: 1;
        text-align: center;
        background: $primary;
        color: $text;
    }

    #broadcast-status {
        height: 2;
        margin: 1;
        text-align: center;
        background: $secondary;
        color: $text;
    }

    #session-footer {
        height: 3;
        margin: 1;
        text-align: center;
        background: $surface;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("enter", "connect_session", "Connect", show=True),
        Binding("k", "kill_session", "Kill", show=True),
        Binding("b", "toggle_broadcast", "Broadcast", show=True),
        Binding("p", "create_pane", "New Pane", show=True),
        Binding("shift+p", "create_window", "New Window", show=True),
        Binding("r", "refresh_sessions", "Refresh", show=True),
        Binding("escape", "close_manager", "Close", show=True),
        Binding("q", "close_manager", "Close", show=False),
        Binding("up", "move_up", "Up", show=False),
        Binding("down,j", "move_down", "Down", show=False),
    ]

    def __init__(self, config: Any) -> None:
        """Initialize the tmux session manager."""
        super().__init__()
        self.logger = get_logger()
        self.sessions: List[TmuxSession] = []
        self.table: Optional[DataTable] = None
        self.tmux_server: Optional[Any] = None
        self.broadcast_enabled = False  # Track broadcast state
        self.config = config

    def compose(self) -> ComposeResult:
        """Create the session manager layout."""
        with Container(id="session-dialog"):
            yield Static("🖥️  SSHplex - tmux Session Manager", id="session-header")
            yield Static("📡 Broadcast: OFF", id="broadcast-status")
            yield DataTable(id="session-table", cursor_type="row")
            yield Static("Enter: Connect | K: Kill | B: Broadcast | R: Refresh | ESC: Close", id="session-footer")

    def on_mount(self) -> None:
        """Initialize the session manager."""
        self.table = self.query_one("#session-table", DataTable)

        # Setup table columns
        self.table.add_column("Status", width=8)
        self.table.add_column("Session Name", width=25)
        self.table.add_column("Created", width=20)
        self.table.add_column("Windows", width=8)

        # Load sessions first
        self.load_sessions()

        # Focus on the table after loading data
        self.table.focus()

        # Move cursor to first row if we have sessions
        if self.sessions:
            self.table.move_cursor(row=0)

    def load_sessions(self) -> None:
        """Load tmux sessions from the server."""
        try:
            # Initialize tmux server
            self.tmux_server = libtmux.Server()

            # Get all sessions
            tmux_sessions = self.tmux_server.list_sessions()
            self.sessions.clear()

            for session in tmux_sessions:
                # Check if session is attached (use session.attached property or check windows)
                try:
                    # libtmux sessions have an 'attached' property or we can check if it has windows
                    attached = hasattr(session, 'attached') and session.attached
                    if not hasattr(session, 'attached'):
                        # Fallback: check if session has active windows/panes
                        attached = len(session.windows) > 0 and any(len(w.panes) > 0 for w in session.windows)
                except (AttributeError, RuntimeError):
                    attached = False

                # Get window count safely
                try:
                    window_count = len(session.windows) if hasattr(session, 'windows') else 0
                except (AttributeError, RuntimeError):
                    window_count = 0

                # Get creation time - libtmux doesn't provide session.created directly
                try:
                    # Try to get session creation time from tmux itself
                    result = session.cmd('display-message', '-p', '#{session_created}')
                    if result and hasattr(result, 'stdout') and result.stdout:
                        import datetime
                        timestamp = int(result.stdout[0])
                        created_dt = datetime.datetime.fromtimestamp(timestamp)
                        created = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        created = "Unknown"
                except (ValueError, AttributeError, IndexError, OSError):
                    created = "Unknown"

                tmux_session = TmuxSession(
                    name=session.session_name or "Unknown",
                    session_id=session.session_id or "Unknown",
                    created=created,
                    windows=window_count,
                    attached=attached
                )
                self.sessions.append(tmux_session)

            # Populate table
            self.populate_table()

            self.logger.info(f"SSHplex: Loaded {len(self.sessions)} tmux sessions")

        except libtmux.exc.LibTmuxException as e:
            self.logger.error(f"SSHplex: tmux error loading sessions: {e}")
            # Show error in table
            if self.table is not None:
                self.table.clear()
                self.table.add_row("❌", "tmux error", str(e), "0")
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to load tmux sessions: {e}")
            # Show error in table
            if self.table is not None:
                self.table.clear()
                self.table.add_row("❌", "Error loading sessions", str(e), "0")

    def populate_table(self) -> None:
        """Populate the table with session data."""
        if not self.table:
            return

        # Clear existing data
        self.table.clear()

        if not self.sessions:
            self.table.add_row("ℹ️", "No tmux sessions found", "Create one with SSHplex", "0")
            return

        # Add sessions to table
        for session in self.sessions:
            status_icon = "📎" if session.attached else "💤"
            status_text = "Active" if session.attached else "Detached"

            self.table.add_row(
                f"{status_icon} {status_text}",
                session.name,
                session.created,
                str(session.windows),
                key=session.name
            )

    def action_move_up(self) -> None:
        """Move cursor up in the table."""
        if self.table and self.sessions:
            current_row = self.table.cursor_row
            if current_row > 0:
                self.table.move_cursor(row=current_row - 1)

    def action_move_down(self) -> None:
        """Move cursor down in the table."""
        if self.table and self.sessions:
            current_row = self.table.cursor_row
            if current_row < len(self.sessions) - 1:
                self.table.move_cursor(row=current_row + 1)

    def action_connect_session(self) -> None:
        """Connect to the selected tmux session."""
        if not self.table or not self.sessions:
            self.logger.warning("SSHplex: No table or sessions available")
            return

        # Get the selected row from the table
        try:
            cursor_row = self.table.cursor_row
            self.logger.info(f"SSHplex: Cursor at row {cursor_row}, total sessions: {len(self.sessions)}")

            if cursor_row >= 0 and cursor_row < len(self.sessions):
                session = self.sessions[cursor_row]

                self.logger.info(f"SSHplex: Connecting to tmux session '{session.name}'")

                # Close the modal first
                self.dismiss()

                # Small delay to ensure modal is closed
                import time
                time.sleep(0.1)

                import platform
                system = platform.system().lower()
                try:
                    # Check if iTerm2 integration should be used
                    use_iterm2 = (
                        "darwin" in system and
                        self.config and
                        getattr(self.config.tmux, 'control_with_iterm2', False)
                    )

                    if use_iterm2:
                        # Use shared iTerm2 utility for consistent behavior
                        from ..utils.iterm2 import launch_iterm2_session
                        target = getattr(self.config.tmux, 'iterm2_attach_target', 'new-window')
                        profile = getattr(self.config.tmux, 'iterm2_profile', 'Default')

                        success = launch_iterm2_session(
                            session_name=session.name,
                            target=target,
                            profile=profile,
                            fallback_to_standard=True
                        )

                        if not success:
                            # Fallback to standard tmux attach
                            import os
                            self.logger.info("Falling back to standard tmux attach")
                            os.execlp("tmux", "tmux", "attach-session", "-t", session.name)
                    else:
                        # Auto-attach to the session by replacing current process
                        import os
                        os.execlp("tmux", "tmux", "attach-session", "-t", session.name)

                except Exception as e:
                    self.logger.info(f"⚠️ Failed to attach to tmux session: {e}")

            else:
                self.logger.warning(f"SSHplex: Invalid cursor row {cursor_row}")
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to connect to session: {e}")

    def action_kill_session(self) -> None:
        """Kill the selected tmux session."""
        if not self.table or not self.sessions:
            self.logger.warning("SSHplex: No table or sessions available for killing")
            return

        try:
            cursor_row = self.table.cursor_row
            self.logger.info(f"SSHplex: Kill cursor at row {cursor_row}, total sessions: {len(self.sessions)}")

            if cursor_row >= 0 and cursor_row < len(self.sessions):
                session = self.sessions[cursor_row]
                self._do_kill_session(session)
            else:
                self.logger.warning(f"SSHplex: Invalid cursor row {cursor_row} for killing session")

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to initiate session kill: {e}")

    def _do_kill_session(self, session: TmuxSession) -> None:
        """Actually kill the tmux session after confirmation."""
        try:
            self.logger.info(f"SSHplex: Attempting to kill tmux session '{session.name}'")

            # Find and kill the session
            if self.tmux_server:
                tmux_session = self.tmux_server.find_where({"session_name": session.name})
                if tmux_session:
                    tmux_session.kill_session()
                    self.logger.info(f"SSHplex: Successfully killed tmux session '{session.name}'")

                    # Refresh the session list
                    self.load_sessions()
                else:
                    self.logger.error(f"SSHplex: Session '{session.name}' not found for killing")
            else:
                self.logger.error("SSHplex: No tmux server connection available")

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to kill session: {e}")

    def action_refresh_sessions(self) -> None:
        """Refresh the session list."""
        self.logger.info("SSHplex: Refreshing tmux sessions")
        self.load_sessions()

    def action_close_manager(self) -> None:
        """Close the session manager."""
        self.dismiss()

    def action_toggle_broadcast(self) -> None:
        """Toggle broadcast mode for sending commands to all panes."""
        if not self.table or not self.sessions:
            self.logger.warning("SSHplex: No sessions available for broadcast")
            return

        cursor_row = self.table.cursor_row
        if cursor_row >= 0 and cursor_row < len(self.sessions):
            session = self.sessions[cursor_row]

            try:
                # Find the tmux session
                if self.tmux_server is None:
                    self.logger.error("SSHplex: tmux server not initialized")
                    return

                tmux_session = self.tmux_server.find_where({"session_name": session.name})
                if not tmux_session:
                    self.logger.error(f"SSHplex: Session '{session.name}' not found")
                    return

                # Toggle broadcast mode
                self.broadcast_enabled = not self.broadcast_enabled

                if self.broadcast_enabled:
                    # Enable synchronize-panes for all windows in the session
                    for window in tmux_session.windows:
                        window.cmd('set-window-option', 'synchronize-panes', 'on')

                    self.logger.info(f"SSHplex: Broadcast ENABLED for session '{session.name}'")
                    # Update broadcast status display
                    status_widget = self.query_one("#broadcast-status", Static)
                    status_widget.update("📡 Broadcast: ON")

                else:
                    # Disable synchronize-panes for all windows in the session
                    for window in tmux_session.windows:
                        window.cmd('set-window-option', 'synchronize-panes', 'off')

                    self.logger.info(f"SSHplex: Broadcast DISABLED for session '{session.name}'")
                    # Update broadcast status display
                    status_widget = self.query_one("#broadcast-status", Static)
                    status_widget.update("📡 Broadcast: OFF")

            except Exception as e:
                self.logger.error(f"SSHplex: Failed to toggle broadcast for session '{session.name}': {e}")
        else:
            self.logger.warning("SSHplex: No session selected for broadcast toggle")

    def action_create_pane(self) -> None:
        """Create a new pane in the selected tmux session."""
        if not self.table or not self.sessions:
            self.logger.warning("SSHplex: No sessions available for pane creation")
            return

        cursor_row = self.table.cursor_row
        if cursor_row >= 0 and cursor_row < len(self.sessions):
            session = self.sessions[cursor_row]

            try:
                # Find the tmux session
                if self.tmux_server is None:
                    self.logger.error("SSHplex: tmux server not initialized")
                    return

                tmux_session = self.tmux_server.find_where({"session_name": session.name})
                if not tmux_session:
                    self.logger.error(f"SSHplex: Session '{session.name}' not found")
                    return

                # Get the first window (or current window)
                if tmux_session.windows:
                    window = tmux_session.windows[0]  # Use first window

                    # Create a new pane by splitting the window vertically
                    new_pane = window.split_window(vertical=True)

                    if new_pane:
                        # Set a title for the new pane
                        new_pane.send_keys('printf "\\033]2;New Pane\\033\\\\"', enter=True)

                        # Apply tiled layout to organize all panes nicely
                        window.select_layout('tiled')

                        self.logger.info(f"SSHplex: Created new pane in session '{session.name}'")

                        # Refresh session list to update window/pane count
                        self.load_sessions()
                    else:
                        self.logger.error(f"SSHplex: Failed to create pane in session '{session.name}'")
                else:
                    self.logger.error(f"SSHplex: No windows found in session '{session.name}'")

            except Exception as e:
                self.logger.error(f"SSHplex: Failed to create pane in session '{session.name}': {e}")
        else:
            self.logger.warning("SSHplex: No session selected for pane creation")

    def action_create_window(self) -> None:
        """Create a new window (tab) in the selected tmux session."""
        if not self.table or not self.sessions:
            self.logger.warning("SSHplex: No sessions available for window creation")
            return

        cursor_row = self.table.cursor_row
        if cursor_row >= 0 and cursor_row < len(self.sessions):
            session = self.sessions[cursor_row]

            try:
                # Find the tmux session
                if self.tmux_server is None:
                    self.logger.error("SSHplex: tmux server not initialized")
                    return

                tmux_session = self.tmux_server.find_where({"session_name": session.name})
                if not tmux_session:
                    self.logger.error(f"SSHplex: Session '{session.name}' not found")
                    return

                # Create a new window in the session
                new_window = tmux_session.new_window(window_name="New Window")

                if new_window:
                    # Set the window name and send a welcome message
                    new_window.rename_window("SSHplex-Window")

                    # Get the first pane in the new window and set title
                    if new_window.panes:
                        first_pane = new_window.panes[0]
                        first_pane.send_keys('printf "\\033]2;New Window\\033\\\\"', enter=True)
                        first_pane.send_keys('echo "🪟 New SSHplex window created!"', enter=True)

                    self.logger.info(f"SSHplex: Created new window in session '{session.name}'")

                    # Refresh session list to update window count
                    self.load_sessions()
                else:
                    self.logger.error(f"SSHplex: Failed to create window in session '{session.name}'")

            except Exception as e:
                self.logger.error(f"SSHplex: Failed to create window in session '{session.name}': {e}")
        else:
            self.logger.warning("SSHplex: No session selected for window creation")

    def action_create_ssh_pane(self) -> None:
        """Create a new pane with SSH connection."""
        if not self.table or not self.sessions:
            self.logger.warning("SSHplex: No sessions available for SSH pane creation")
            return

        cursor_row = self.table.cursor_row
        if cursor_row >= 0 and cursor_row < len(self.sessions):
            session = self.sessions[cursor_row]

            try:
                # Find the tmux session
                if self.tmux_server is None:
                    self.logger.error("SSHplex: tmux server not initialized")
                    return

                tmux_session = self.tmux_server.find_where({"session_name": session.name})
                if not tmux_session:
                    self.logger.error(f"SSHplex: Session '{session.name}' not found")
                    return

                # Get the first window (or current window)
                if tmux_session.windows:
                    window = tmux_session.windows[0]  # Use first window

                    # Create a new pane by splitting the window vertically
                    new_pane = window.split_window(vertical=True)

                    if new_pane:
                        # Set a title for the new pane
                        hostname = "new-host"  # Default hostname
                        new_pane.send_keys(f'printf "\\033]2;{hostname}\\033\\\\"', enter=True)

                        # You could prompt for hostname here or use a default SSH command
                        # For now, just create an empty pane ready for SSH
                        new_pane.send_keys('echo "🔗 Ready for SSH connection..."', enter=True)
                        new_pane.send_keys('echo "Usage: ssh user@hostname"', enter=True)

                        # Apply tiled layout to organize all panes nicely
                        window.select_layout('tiled')

                        self.logger.info(f"SSHplex: Created new SSH-ready pane in session '{session.name}'")

                        # Refresh session list to update window/pane count
                        self.load_sessions()
                    else:
                        self.logger.error(f"SSHplex: Failed to create SSH pane in session '{session.name}'")
                else:
                    self.logger.error(f"SSHplex: No windows found in session '{session.name}'")

            except Exception as e:
                self.logger.error(f"SSHplex: Failed to create SSH pane in session '{session.name}': {e}")
        else:
            self.logger.warning("SSHplex: No session selected for SSH pane creation")

    def key_enter(self) -> None:
        """Handle enter key for connecting to session."""
        self.action_connect_session()
