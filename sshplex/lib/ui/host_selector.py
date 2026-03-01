"""SSHplex TUI Host Selector with Textual."""

import asyncio
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional, Set

import pyperclip
import yaml
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Input,
    Label,
    LoadingIndicator,
    Log,
    Static,
)

from ... import __version__
from ..config import get_default_config_path, load_config
from ..logger import get_logger
from ..sot.base import Host
from ..sot.factory import SoTFactory
from ..utils.ssh_config import (
    build_ssh_command_preview,
    mask_sensitive,
    resolve_ssh_effective_config,
)
from .config_editor import ConfigEditorScreen
from .session_manager import ITerm2SessionManager, TmuxSessionManager


class LoadingScreen(Screen):
    """Modal screen that displays loading progress while refreshing data sources."""

    CSS = """
    LoadingScreen {
        align: center middle;
    }

    #loading-dialog {
        layout: vertical;
        padding: 3;
        width: 60;
        height: 15;
        border: thick $primary;
        background: $surface;
        content-align: center middle;
    }

    #loading-message {
        text-align: center;
        color: $text;
        margin-bottom: 1;
        width: 100%;
    }

    #loading-indicator {
        margin-bottom: 1;
        width: 100%;
        content-align: center middle;
    }

    #loading-status {
        text-align: center;
        color: $text-muted;
        width: 100%;
    }
    """

    def __init__(self, message: str = "🔄 Refreshing Data Sources", status: str = "Initializing...") -> None:
        super().__init__()
        self.message = message
        self.status = status

    def compose(self) -> ComposeResult:
        with Vertical(id="loading-dialog"):
            yield Label(self.message, id="loading-message")
            yield LoadingIndicator(id="loading-indicator")
            yield Label(self.status, id="loading-status")

    def update_status(self, status: str) -> None:
        """Update the loading status message."""
        try:
            status_label = self.query_one("#loading-status", Label)
            status_label.update(status)
        except Exception:
            # If the widget isn't mounted yet, just ignore the update
            pass


class HelpScreen(Screen):
    """Modal screen showing keyboard shortcuts help."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        layout: vertical;
        padding: 3;
        width: 80;
        height: 40;
        border: thick $primary;
        background: $surface;
        overflow-y: auto;
    }

    Markdown {
        height: 1fr;
    }
    """

    def __init__(self, help_text: str) -> None:
        super().__init__()
        self.help_text = help_text

    def compose(self) -> ComposeResult:
        from textual.widgets import Markdown
        with Vertical(id="help-dialog"):
            yield Markdown(self.help_text)

    def on_key(self, event: Any) -> None:
        """Close help screen on any key press."""
        self.dismiss()


class HostSelector(App):
    """SSHplex TUI for selecting hosts to connect to."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #log-panel {
        height: 20%;
        border: solid $primary;
        margin: 0 1;
        margin-bottom: 1;
    }

    #main-panel {
        height: 1fr;
        border: solid $primary;
        margin: 0 1;
        margin-bottom: 1;
    }

    #status-bar {
        height: 2;
        background: $surface;
        color: $text;
        padding: 0 0;
        margin: 0 0;
        dock: bottom;
        layout: horizontal;
    }

    #status-content {
        width: 1fr;
    }

    #cache-display {
        width: 20;
        background: transparent;
        color: $text-muted;
        text-align: center;
        margin: 0 1;
    }

    #version-display {
        width: 15;
        background: transparent;
        color: $text-muted;
        text-align: right;
    }

    #search-container {
        height: 3;
        margin: 0 1;
        margin-bottom: 1;
        display: none;
    }

    #search-input {
        height: 3;
    }

    DataTable {
        height: 1fr;
        width: 100%;
    }

    Log {
        height: 1fr;
    }

    #log {
        overflow-y: auto;
        overflow-x: hidden;
    }

    #log Input {
        display: none;
    }

    Log > Input {
        display: none;
    }

    Log TextArea {
        display: none;
    }

    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_select", "Toggle Select", show=True),
        Binding("a", "select_all", "Select All", show=True),
        Binding("d", "deselect_all", "Deselect All", show=True),
        Binding("enter", "connect_selected", "Connect", show=True),
        Binding("/", "start_search", "Search", show=True),
        Binding("s", "show_sessions", "Sessions", show=True),
        Binding("p", "toggle_panes", "Panes/Tabs", show=True),
        Binding("b", "toggle_broadcast", "Broadcast", show=True),
        Binding("r", "refresh_hosts", "Refresh", show=True),
        Binding("escape", "focus_table", "Focus Table", show=False),
        Binding("h", "show_help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "copy_select", "Copy", show=True),
        Binding("e", "edit_config", "Config", show=True),
        Binding("o", "show_host_ssh", "SSH View", show=True),
        Binding("l", "toggle_log_panel", "Logs", show=True),
    ]

    selected_hosts: reactive[Set[str]] = reactive(set())
    search_filter: reactive[str] = reactive("")
    use_panes: reactive[bool] = reactive(True)  # True for panes, False for tabs
    use_broadcast: reactive[bool] = reactive(False)  # True for broadcast enabled, False for disabled

    def __init__(self, config: Any, config_path: str = "") -> None:
        """Initialize the host selector.

        Args:
            config: SSHplex configuration object
        """
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.logger = get_logger()
        self.hosts: List[Host] = []
        self.filtered_hosts: List[Host] = []
        self.sot_factory: Optional[SoTFactory] = None
        self.table: Optional[DataTable] = None
        self.log_widget: Optional[Log] = None
        self.status_widget: Optional[Static] = None
        self.search_input: Optional[Input] = None
        self.cache_widget: Optional[Static] = None
        self.loading_screen: Optional[LoadingScreen] = None
        self.sort_reverse = False
        self.connect_in_progress = False
        self.latest_native_session_name: Optional[str] = None
        self.native_sessions_created_count = 0
        self._log_max_lines = 1000

    def compose(self) -> ComposeResult:
        """Create the UI layout."""

        # Log panel at top (conditionally shown)
        if self.config.ui.show_log_panel:
            with Container(id="log-panel"):
                yield Log(id="log", auto_scroll=True, max_lines=self._log_max_lines)

        # Search input (hidden by default)
        with Container(id="search-container"):
            yield Input(placeholder="Search hosts...", id="search-input")

        # Main content panel
        with Container(id="main-panel"):
            yield DataTable(id="host-table", cursor_type="row")

        # Status bar with cache info and version display
        with Container(id="status-bar"):
            yield Static("SSHplex - Loading hosts...", id="status-content")
            yield Static("Cache: --", id="cache-display")
            yield Static(f"SSHplex v{__version__}", id="version-display")

        # Footer with keybindings
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the UI and load hosts."""
        configured_theme = str(getattr(self.config.ui, "theme", "textual-dark") or "textual-dark")
        if configured_theme in self.available_themes:
            self.theme = configured_theme

        self.use_panes = bool(getattr(self.config.tmux, "use_panes", True))
        self.use_broadcast = bool(getattr(self.config.tmux, "broadcast", False))

        # Get widget references
        self.table = self.query_one("#host-table", DataTable)
        if self.config.ui.show_log_panel:
            self.log_widget = self.query_one("#log", Log)
        self.status_widget = self.query_one("#status-content", Static)
        self.search_input = self.query_one("#search-input", Input)
        self.cache_widget = self.query_one("#cache-display", Static)

        # Setup table columns
        self.setup_table()

        # Focus on the table by default
        if self.table:
            self.table.focus()

        # Load hosts from SoT providers
        self.run_worker(self.load_hosts(), name="initial_load")

        self.log_message("SSHplex TUI started")

    def watch_theme(self, theme: str) -> None:
        """Persist selected theme changes from command palette or settings."""
        if not getattr(self, "config", None):
            return
        if not hasattr(self.config, "ui"):
            return

        if getattr(self.config.ui, "theme", "") == theme:
            return

        self.config.ui.theme = theme
        self.log_message(f"Theme changed to '{theme}'")
        self._persist_theme_setting(theme)

    def _persist_theme_setting(self, theme: str) -> None:
        """Write current theme to active config file."""
        config_path = Path(self.config_path).expanduser() if self.config_path else get_default_config_path()
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}

            if not isinstance(config_data, dict):
                config_data = {}

            ui_data = config_data.get("ui", {})
            if not isinstance(ui_data, dict):
                ui_data = {}
            ui_data["theme"] = theme
            config_data["ui"] = ui_data

            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            self.logger.info(f"SSHplex: Persisted theme '{theme}' to {config_path}")
        except Exception as e:
            self.logger.debug(f"SSHplex: Could not persist theme setting: {e}")

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Add SSHplex commands to command palette while keeping built-ins."""
        yield from super().get_system_commands(screen)
        yield SystemCommand("Connect Selected", "Connect to selected hosts", self.action_connect_selected)
        yield SystemCommand("Refresh Hosts", "Reload hosts from sources", self.action_refresh_hosts)
        yield SystemCommand("Force Refresh Hosts", "Bypass cache and reload hosts", lambda: self.run_worker(self.load_hosts(force_refresh=True), name="cmd_force_refresh"))
        yield SystemCommand("Sessions", "Open session manager", self.action_show_sessions)
        yield SystemCommand("Settings", "Open configuration editor", self.action_edit_config)
        yield SystemCommand("Reload Config", "Reload config from disk", lambda: self.run_worker(self._reload_config_runtime(), name="cmd_reload_config"))
        yield SystemCommand("Toggle Panes/Tabs", "Switch connection mode", self.action_toggle_panes)
        yield SystemCommand("Toggle Broadcast", "Toggle broadcast mode", self.action_toggle_broadcast)
        yield SystemCommand("Toggle Log Panel", "Show or hide the log panel", self.action_toggle_log_panel)
        yield SystemCommand("Clear Logs", "Clear in-app log panel", self.action_clear_logs)
        yield SystemCommand("Show Host SSH", "Show resolved SSH values for current host", self.action_show_host_ssh)
        yield SystemCommand("Search", "Focus search input", self.action_start_search)
        yield SystemCommand("Help", "Show keyboard shortcuts", self.action_show_help)
        yield SystemCommand("Copy Selection", "Copy selected hosts to clipboard", self.action_copy_select)

    def setup_table(self) -> None:
        """Setup the data table columns with responsive widths."""
        if not self.table:
            return

        # Add checkbox column (fixed small width)
        self.table.add_column("✓", width=3, key="checkbox")

        # Add configured columns with proportional widths
        for column in self.config.ui.table_columns:
            self.table.add_column(column, width=None, key=column)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col = event.column_key.value
        if col is None:
            return
        self.sort_reverse = not self.sort_reverse
        hosts_to_display = self.get_hosts_to_display()
        hosts_to_display.sort(
            key=lambda r: getattr(r, col, ""),
            reverse=self.sort_reverse
        )
        self.populate_table(hosts_to_display)

    def show_loading_screen(self, message: str = "🔄 Refreshing Data Sources", status: str = "Initializing...") -> None:
        """Show the loading screen modal."""
        self.loading_screen = LoadingScreen(message=message, status=status)
        self.push_screen(self.loading_screen)

    def hide_loading_screen(self) -> None:
        """Hide the loading screen modal."""
        if self.loading_screen:
            self.pop_screen()
            self.loading_screen = None

    def update_cache_display(self) -> None:
        """Update the cache display with current cache information."""
        if not self.cache_widget or not self.sot_factory:
            return

        try:
            cache_info = self.sot_factory.get_cache_info()
            if cache_info:
                age_hours = cache_info.get('age_hours', 0)
                if age_hours < 1:
                    age_minutes = int(age_hours * 60)
                    cache_text = f"Cache: {age_minutes}m"
                elif age_hours < 24:
                    cache_text = f"Cache: {age_hours:.1f}h"
                else:
                    age_days = int(age_hours / 24)
                    cache_text = f"Cache: {age_days}d"

                # Add TTL info
                ttl_hours = getattr(self.config.cache, 'ttl_hours', 24)
                cache_text += f" (TTL: {ttl_hours}h)"
            else:
                cache_text = "Cache: None"

            self.cache_widget.update(cache_text)
        except (KeyError, AttributeError, TypeError) as e:
            self.logger.debug(f"Could not update cache display: {e}")
            self.cache_widget.update("Cache: --")
        except Exception as e:
            self.logger.warning(f"Unexpected error updating cache display: {e}")
            self.cache_widget.update("Cache: --")

    def update_loading_status(self, status: str) -> None:
        """Update the loading status message.

        Args:
            status: Status message to display
        """
        if self.loading_screen:
            try:
                self.loading_screen.update_status(status)
            except (AttributeError, RuntimeError) as e:
                # Widget may not be mounted yet - log but don't crash
                self.log_message(f"Warning: Could not update loading status: {e}", level="warning")

    async def load_hosts(self, force_refresh: bool = False) -> None:
        """Load hosts from all configured SoT providers with caching support.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data from providers
        """
        # Determine if we need to show loading screen
        show_loading = force_refresh

        # Check if cache exists for initial load
        if not force_refresh:
            # Initialize SoT factory to check cache
            temp_factory = SoTFactory(self.config)
            cache_info = temp_factory.get_cache_info()
            if not cache_info:
                # No cache exists, this is first run - show loading screen
                show_loading = True

        # Show loading screen for refresh operations or initial load without cache
        if show_loading:
            if force_refresh:
                self.show_loading_screen("🔄 Refreshing Data Sources", "Initializing providers...")
            else:
                self.show_loading_screen("📡 Loading Data Sources", "Initializing providers...")
            await asyncio.sleep(0.2)  # Give the modal time to mount properly

        if force_refresh:
            self.log_message("Force refreshing hosts from all SoT providers...")
            self.update_status("Refreshing hosts from providers...")
        else:
            self.log_message("Loading hosts (checking cache first)...")
            self.update_status("Loading hosts...")

        try:
            # Initialize SoT factory
            if show_loading:
                self.update_loading_status("Initializing SoT factory...")
                await asyncio.sleep(0.1)  # Allow UI to update

            self.sot_factory = SoTFactory(self.config)

            # Check cache status first
            if not force_refresh:
                cache_info = self.sot_factory.get_cache_info()
                if cache_info:
                    cache_age = cache_info.get('age_hours', 0)
                    self.log_message(f"Found cache with {cache_info.get('host_count', 0)} hosts (age: {cache_age:.1f} hours)")

            # Initialize all providers (needed for refresh even if cache exists)
            if show_loading:
                self.update_loading_status("Connecting to providers...")
                await asyncio.sleep(0.1)  # Allow UI to update

            if not self.sot_factory.initialize_providers():
                self.log_message("ERROR: Failed to initialize any SoT providers", level="error")
                self.update_status("Error: SoT provider initialization failed")
                if show_loading:
                    self.hide_loading_screen()
                return

            provider_names = ', '.join(self.sot_factory.get_provider_names())
            self.log_message(f"Successfully initialized {self.sot_factory.get_provider_count()} provider(s): {provider_names}")

            # Get hosts (with caching support) - use parallel fetching for better performance
            if show_loading:
                if force_refresh:
                    self.update_loading_status("Fetching fresh host data (parallel)...")
                else:
                    self.update_loading_status("Loading host data (parallel)...")
                await asyncio.sleep(0.1)  # Allow UI to update

            # Use parallel fetching for better performance with multiple providers
            self.hosts = self.sot_factory.get_all_hosts_parallel(force_refresh=force_refresh)
            self.filtered_hosts = self.hosts.copy()  # Initialize filtered hosts

            if not self.hosts:
                self.log_message("WARNING: No hosts found matching filters", level="warning")
                self.update_status("No hosts found")
                if show_loading:
                    self.hide_loading_screen()
                return

            # Populate table
            if show_loading:
                self.update_loading_status("Updating display...")
                await asyncio.sleep(0.1)  # Allow UI to update

            self.populate_table(self.get_hosts_to_display())

            source_msg = "fresh data from providers" if force_refresh else "cache/providers"
            self.log_message(f"Loaded {len(self.hosts)} hosts successfully from {source_msg}")
            self.update_status_with_mode()
            self.update_cache_display()

            # Hide loading screen if it was shown
            if show_loading:
                self.hide_loading_screen()

        except Exception as e:
            self.log_message(f"ERROR: Failed to load hosts: {e}", level="error")
            self.update_status(f"Error: {e}")
            if show_loading:
                self.hide_loading_screen()

    def get_hosts_to_display(self) -> List[Host]:
        """Return filtered hosts if search is active, otherwise all hosts."""
        return self.filtered_hosts if self.search_filter else self.hosts

    def populate_table(self, hosts_to_display: List[Host]) -> None:
        """Populate the table with host data."""
        if not self.table:
            return

        previous_host_key = self._current_cursor_host_key()

        # Clear existing table data
        self.table.clear()

        if not hosts_to_display:
            return

        for host in hosts_to_display:
            # Build row data based on configured columns
            # Use colors for better visual feedback
            host_key = self._host_key(host)
            is_selected = host_key in self.selected_hosts
            row_data = ["[green]✓[/green]" if is_selected else "[dim] [/dim]"]  # Checkbox column

            # Highlight selected hosts with color
            for column in self.config.ui.table_columns:
                value = self._get_column_value(host, column)
                if is_selected:
                    # Highlight selected hosts
                    row_data.append(f"[bold]{value}[/bold]")
                else:
                    row_data.append(value)

            self.table.add_row(*row_data, key=host_key)

        if previous_host_key:
            for index, host in enumerate(hosts_to_display):
                if self._host_key(host) == previous_host_key:
                    self.table.move_cursor(row=index)
                    break

    @staticmethod
    def _host_key(host: Host) -> str:
        """Return stable host identity key for selection and row mapping."""
        return f"{host.name}|{host.ip}"

    def _current_cursor_host(self) -> Optional[Host]:
        """Get host currently under cursor in rendered table."""
        if not self.table:
            return None
        row = self.table.cursor_row
        hosts_to_use = self.get_hosts_to_display()
        if row < 0 or row >= len(hosts_to_use):
            return None
        return hosts_to_use[row]

    def _current_cursor_host_key(self) -> Optional[str]:
        """Get host key currently under cursor in rendered table."""
        host = self._current_cursor_host()
        if host is None:
            return None
        return self._host_key(host)

    @staticmethod
    def _normalize_column_name(column: str) -> str:
        """Normalize aliases used in table column config."""
        mapping = {
            "source": "provider",
            "alias": "ssh_alias",
            "user": "ssh_user",
            "port": "ssh_port",
            "key": "ssh_key_path",
            "key_path": "ssh_key_path",
            "hostname": "ip",
        }
        return mapping.get(column, column)

    def _get_column_value(self, host: Host, column: str) -> str:
        """Get display value for a table column from host attributes/metadata."""
        key = self._normalize_column_name(str(column).strip())
        value = getattr(host, key, None)
        if value in (None, "") and isinstance(getattr(host, "metadata", None), dict):
            value = host.metadata.get(key)

        if value in (None, ""):
            if key == "ssh_user":
                value = str(getattr(self.config.ssh, "username", ""))
            elif key == "ssh_port":
                value = str(getattr(self.config.ssh, "port", 22))
            else:
                value = "N/A"
        return str(value)

    def action_copy_select(self) -> None:

        hosts = self.get_hosts_to_display()
        columns = self.config.ui.table_columns

        # Build raw table (list of lists)
        table = []

        # Header
        table.append(columns)

        # Host rows
        for host in hosts:
            row = [self._get_column_value(host, col) for col in columns]
            table.append(row)

        # Compute max width for each column
        col_widths = [
            max(len(row[i]) for row in table)
            for i in range(len(columns))
        ]

        # Build aligned lines
        lines = []
        for row in table:
            line = "  ".join(  # two spaces between columns
                row[i].ljust(col_widths[i])
                for i in range(len(columns))
            )
            lines.append(line)

        # Final clipboard text
        text = "\n".join(lines)
        pyperclip.copy(text)


    def action_toggle_select(self) -> None:
        """Toggle selection of current row."""
        if not self.table or not self.hosts:
            return

        cursor_row = self.table.cursor_row
        hosts_to_use = self.filtered_hosts if self.search_filter else self.hosts

        if cursor_row >= 0 and cursor_row < len(hosts_to_use):
            host_key = self._host_key(hosts_to_use[cursor_row])
            host_label = hosts_to_use[cursor_row].name

            if host_key in self.selected_hosts:
                self.selected_hosts.discard(host_key)
                self.update_row_checkbox(host_key, False)
                self.log_message(f"Deselected: {host_label}")
            else:
                self.selected_hosts.add(host_key)
                self.update_row_checkbox(host_key, True)
                self.log_message(f"Selected: {host_label}")

            self.update_status_selection()

    def action_select_all(self) -> None:
        """Select all hosts (filtered if search is active)."""
        if not self.hosts:
            return

        hosts_to_select = self.filtered_hosts if self.search_filter else self.hosts

        for host in hosts_to_select:
            host_key = self._host_key(host)
            self.selected_hosts.add(host_key)
            self.update_row_checkbox(host_key, True)

        self.log_message(f"Selected all {len(hosts_to_select)} hosts")
        self.update_status_selection()

    def action_deselect_all(self) -> None:
        """Deselect all hosts (filtered if search is active)."""
        if not self.hosts:
            return

        hosts_to_deselect = self.filtered_hosts if self.search_filter else self.hosts

        for host in hosts_to_deselect:
            host_key = self._host_key(host)
            self.selected_hosts.discard(host_key)
            self.update_row_checkbox(host_key, False)

        self.log_message(f"Deselected all {len(hosts_to_deselect)} hosts")
        self.update_status_selection()

    def action_connect_selected(self) -> None:
        """Connect to selected hosts and exit the application."""
        if self._is_command_palette_open():
            return

        if self.connect_in_progress:
            self.log_message("Connection already in progress, please wait...", level="warning")
            return

        if not self.selected_hosts:
            self.log_message("No hosts selected for connection", level="warning")
            return

        selected_host_objects = [h for h in self.hosts if self._host_key(h) in self.selected_hosts]
        if not selected_host_objects:
            self.log_message("No hosts found matching selection", level="warning")
            return

        mode = "Panes" if self.use_panes else "Tabs"
        broadcast = "ON" if self.use_broadcast else "OFF"
        self.log_message(f"Connecting to {len(selected_host_objects)} hosts in {mode} mode, Broadcast {broadcast}")

        for host in selected_host_objects:
            self.log_message(f"  - {host.name} ({host.ip})")

        backend = getattr(self.config.tmux, "backend", "tmux")
        if backend == "iterm2-native":
            self.log_message("Starting iTerm2 native session (staying in SSHplex TUI)...")
            self.connect_in_progress = True
            self.update_status_with_mode()
            self.run_worker(
                self._connect_selected_iterm2_native(selected_host_objects),
                name="connect_iterm2_native",
            )
            return

        # Exit the TUI and return selected hosts for connection by main.py
        self.exit(selected_host_objects)

    async def _connect_selected_iterm2_native(self, selected_host_objects: List[Host]) -> None:
        """Create iTerm2 native sessions without exiting host selector."""

        def _connect() -> Optional[str]:
            from ...sshplex_connector import SSHplexConnector

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"
            connector = SSHplexConnector(session_name, config=self.config)

            ok = connector.connect_to_hosts(
                hosts=selected_host_objects,
                username=self.config.ssh.username,
                key_path=self.config.ssh.key_path,
                port=self.config.ssh.port,
                use_panes=self.use_panes,
                use_broadcast=self.use_broadcast,
            )
            if not ok:
                return None

            connector.attach_to_session(auto_attach=True)
            return connector.get_session_name()

        try:
            session_name = await asyncio.to_thread(_connect)
            if session_name:
                self.latest_native_session_name = session_name
                self.native_sessions_created_count += 1
                self.log_message(
                    f"iTerm2 native session created: {session_name} (SSHplex remains open)",
                    level="info",
                )
            else:
                self.log_message("Failed to create iTerm2 native session", level="error")
        except Exception as e:
            self.log_message(f"iTerm2 native connection failed: {e}", level="error")
        finally:
            self.connect_in_progress = False
            self.update_status_with_mode()

    def action_show_sessions(self) -> None:
        """Show the tmux session manager modal."""
        backend = getattr(self.config.tmux, "backend", "tmux")
        control_with_iterm2 = bool(getattr(self.config.tmux, "control_with_iterm2", False))
        if backend == "iterm2-native":
            self.log_message("Opening iTerm2 native session manager...")
            self.push_screen(ITerm2SessionManager(self.config, self.latest_native_session_name))
            return

        if control_with_iterm2:
            self.log_message(
                "Session manager is disabled in iTerm2 modes (use tmux standalone backend to manage sessions)",
                level="warning",
            )
            return

        self.log_message("Opening tmux session manager...")
        self.push_screen(TmuxSessionManager(self.config))

    def action_edit_config(self) -> None:
        """Open the configuration editor modal."""
        self.log_message("Opening configuration editor...")

        def _on_editor_close(saved: Optional[bool]) -> None:
            if saved:
                self.run_worker(self._reload_config_runtime(), name="reload_config_runtime")

        editor = ConfigEditorScreen(self.config, self.config_path, runtime_hosts=self.hosts)
        self.push_screen(editor, callback=_on_editor_close)

    async def _reload_config_runtime(self) -> None:
        """Reload configuration from disk and apply it live."""
        try:
            old_sot = self.config.sot.model_dump()
            new_config = load_config(self.config_path or None)
            await self._apply_runtime_config(new_config)
            self.log_message("Configuration reloaded successfully")
            if old_sot != new_config.sot.model_dump():
                self.log_message("SoT settings changed, refreshing hosts...", level="info")
                self.run_worker(self.load_hosts(force_refresh=True), name="reload_refresh_hosts")
        except Exception as e:
            self.log_message(f"Failed to hot-reload config: {e}", level="error")

    async def _apply_runtime_config(self, new_config: Any) -> None:
        """Apply config changes to current TUI session."""
        old_show_log_panel = bool(getattr(self.config.ui, "show_log_panel", True))
        new_show_log_panel = bool(getattr(new_config.ui, "show_log_panel", True))
        new_theme = str(getattr(new_config.ui, "theme", "textual-dark") or "textual-dark")

        self.config = new_config
        self.use_panes = bool(getattr(self.config.tmux, "use_panes", True))
        self.use_broadcast = bool(getattr(self.config.tmux, "broadcast", False))

        if new_theme in self.available_themes and self.theme != new_theme:
            self.theme = new_theme

        # Update log panel visibility without restarting the app.
        if old_show_log_panel and not new_show_log_panel:
            try:
                panel = self.query_one("#log-panel", Container)
                await panel.remove()
            except Exception:
                pass
            self.log_widget = None
        elif (not old_show_log_panel) and new_show_log_panel:
            try:
                log_panel = Container(id="log-panel")
                log_widget = Log(id="log", auto_scroll=True)
                await log_panel.mount(log_widget)
                search_container = self.query_one("#search-container", Container)
                await self.mount(log_panel, before=search_container)
                self.log_widget = log_widget
            except Exception as e:
                self.log_message(f"Could not enable log panel dynamically: {e}", level="warning")

        try:
            panel = self.query_one("#log-panel", Container)
            panel.styles.height = f"{int(getattr(self.config.ui, 'log_panel_height', 20))}%"
        except Exception:
            pass

        # Rebuild table columns from updated configuration.
        if self.table:
            for column in list(self.table.ordered_columns):
                self.table.remove_column(column.key)
            self.setup_table()
            self.populate_table(self.get_hosts_to_display())

        # Update dependent UI bits.
        self.update_cache_display()
        self.update_status_with_mode()

    def action_refresh_hosts(self) -> None:
        """Refresh hosts by fetching fresh data from all SoT providers."""
        self.log_message("Refreshing hosts from SoT providers...")
        self.run_worker(self.load_hosts(force_refresh=True), name="refresh_hosts")

    def action_clear_logs(self) -> None:
        """Clear in-app log panel content."""
        if self.log_widget:
            self.log_widget.clear()
            self.log_message("Log panel cleared")

    def action_toggle_log_panel(self) -> None:
        """Show/hide log panel without restarting."""
        try:
            panel = self.query_one("#log-panel", Container)
            if panel.styles.display == "none":
                panel.styles.display = "block"
                self.config.ui.show_log_panel = True
                self.log_message("Log panel enabled")
            else:
                panel.styles.display = "none"
                self.config.ui.show_log_panel = False
        except Exception:
            try:
                log_panel = Container(id="log-panel")
                log_widget = Log(id="log", auto_scroll=True, max_lines=self._log_max_lines)
                log_panel.mount(log_widget)
                search_container = self.query_one("#search-container", Container)
                self.mount(log_panel, before=search_container)
                self.log_widget = log_widget
                self.config.ui.show_log_panel = True
                self.log_message("Log panel enabled")
            except Exception as e:
                self.log_message(f"Could not toggle log panel: {e}", level="warning")

    def action_show_host_ssh(self) -> None:
        """Show resolved SSH settings for host under cursor."""
        host = self._current_cursor_host()
        if not host:
            self.log_message("No host selected", level="warning")
            return

        alias = str(getattr(host, "ssh_alias", "") or host.metadata.get("ssh_alias", "")).strip()
        user_override = str(getattr(host, "ssh_user", "") or host.metadata.get("ssh_user", "")).strip()
        port_override = str(getattr(host, "ssh_port", "") or host.metadata.get("ssh_port", "")).strip()
        key_override = str(getattr(host, "ssh_key_path", "") or host.metadata.get("ssh_key_path", "")).strip()

        target = alias or host.ip or host.name
        resolved = resolve_ssh_effective_config(target)

        hostname = resolved.get("hostname", target) if resolved else target
        user = user_override or resolved.get("user", "") or str(getattr(self.config.ssh, "username", ""))
        port = port_override or resolved.get("port", "22")
        identity = key_override or resolved.get("identityfile", "") or str(getattr(self.config.ssh, "key_path", ""))
        identity_display = mask_sensitive(str(identity).split()[0]) if identity else "-"
        proxy_jump = resolved.get("proxyjump", "-")
        try:
            port_int = int(port)
        except Exception:
            port_int = 22
        preview_cmd = build_ssh_command_preview(hostname, user, port_int, identity)

        self.log_message(
            f"SSH[{host.name}] cmd={preview_cmd} | host={hostname} user={user or '-'} port={port} key={identity_display} proxyjump={proxy_jump}"
        )
        self.notify(f"SSH {host.name}: {user}@{hostname}:{port}", timeout=3)

    def update_row_checkbox(self, row_key: str, selected: bool) -> None:
        """Update the checkbox for a specific row."""
        if not self.table:
            return

        checkbox = "[green]✓[/green]" if selected else "[dim] [/dim]"
        self.table.update_cell(row_key, "checkbox", checkbox)

        # Also update the row style for all columns
        for column in self.config.ui.table_columns:
            value = self.table.get_cell(row_key, column)
            if value:
                if selected:
                    self.table.update_cell(row_key, column, f"[bold]{value}[/bold]")
                else:
                    # Remove bold tags
                    self.table.update_cell(row_key, column, value.replace("[bold]", "").replace("[/bold]", ""))

    def update_status_selection(self) -> None:
        """Update status bar with selection count and mode."""
        self.update_status_with_mode()

    def update_status(self, message: str) -> None:
        """Update the status bar."""
        if self.status_widget:
            self.status_widget.update(message)

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message to both logger and UI log panel."""
        # Log to file
        if level == "error":
            self.logger.error(f"SSHplex TUI: {message}")
        elif level == "warning":
            self.logger.warning(f"SSHplex TUI: {message}")
        else:
            self.logger.info(f"SSHplex TUI: {message}")

        # Log to UI panel if enabled
        if self.log_widget and self.config.ui.show_log_panel:
            timestamp = datetime.now().strftime("%H:%M:%S")
            level_prefix = level.upper() if level != "info" else "INFO"
            self.log_widget.write_line(
                f"[{timestamp}] {level_prefix}: {message}",
                scroll_end=True,
            )
            with contextlib.suppress(Exception):
                self.log_widget.scroll_end(animate=False, immediate=True, x_axis=False)

    def action_show_help(self) -> None:
        """Show keyboard shortcuts help screen."""

        help_text = f"""
# SSHplex Keyboard Shortcuts

## Navigation & Selection
| Key | Action |
|-----|--------|
| `Space` | Toggle selection of current host |
| `a` | Select all hosts (or filtered) |
| `d` | Deselect all hosts (or filtered) |
| `Enter` | Connect to selected hosts |
| `q` | Quit SSHplex |

## Search & Filter
| Key | Action |
|-----|--------|
| `/` | Open search input |
| `r` | Refresh from sources (bypass cache) |
| `Escape` | Focus table / clear search |

## Connection Modes
| Key | Action |
|-----|--------|
| `p` | Toggle panes vs tabs mode |
| `b` | Toggle broadcast mode |

## Other
| Key | Action |
|-----|--------|
| `s` | {'iTerm2 tab manager' if (getattr(self.config.tmux, 'backend', 'tmux') == 'iterm2-native') else ('Session manager (disabled in iTerm2-CC)' if bool(getattr(self.config.tmux, 'control_with_iterm2', False)) else 'Session manager')} |
| `c` | Copy table to clipboard |
| `e` | Edit configuration |
| `o` | Show SSH resolution |
| `h` | Show this help |

## Current Settings
- **Backend**: {getattr(self.config.tmux, 'backend', 'tmux')}{('/' + getattr(self.config.tmux, 'iterm2_native_target', 'current-window')) if getattr(self.config.tmux, 'backend', 'tmux') == 'iterm2-native' else ''}
- **Mode**: {"Panes" if self.use_panes else "Tabs"}
- **Broadcast**: {"ON" if self.use_broadcast else "OFF"}
- **Hosts**: {len(self.hosts)} total

*Press any key to close this help*
        """

        help_screen = HelpScreen(help_text)
        self.push_screen(help_screen)

    def action_start_search(self) -> None:
        """Start search mode by showing and focusing the search input."""
        if self.search_input:
            # Show the search container
            search_container = self.query_one("#search-container")
            search_container.styles.display = "block"

            # Focus on the search input
            self.search_input.focus()
            self.log_message("Search mode activated - type to filter hosts, ESC to focus table")

    def action_focus_table(self) -> None:
        """Focus back on the table."""
        if self.table:
            self.table.focus()
            # If search is active, we keep the filter but just change focus
            if self.search_filter:
                self.log_message(f"Table focused - search filter '{self.search_filter}' still active")
            else:
                self.log_message("Table focused")

            self.update_status_selection()

    def action_toggle_panes(self) -> None:
        """Toggle between panes and tabs mode for SSH connections."""
        self.use_panes = not self.use_panes
        mode = "Panes" if self.use_panes else "Tabs"
        self.log_message(f"SSH connection mode switched to: {mode}")
        self.update_status_with_mode()

    def action_toggle_broadcast(self) -> None:
        """Toggle broadcast mode for synchronized input across connections."""
        self.use_broadcast = not self.use_broadcast
        broadcast_status = "ON" if self.use_broadcast else "OFF"
        self.log_message(f"Broadcast mode switched to: {broadcast_status}")
        self.update_status_with_mode()

    def update_status_with_mode(self) -> None:
        """Update status bar to include current connection mode and broadcast status."""
        mode = "Panes" if self.use_panes else "Tabs"
        broadcast = "ON" if self.use_broadcast else "OFF"
        backend = getattr(self.config.tmux, "backend", "tmux")
        if backend == "iterm2-native":
            target = getattr(self.config.tmux, "iterm2_native_target", "current-window")
            backend_display = f"iterm2-native/{target}"
        else:
            backend_display = "tmux"

        busy = " | Busy:connect" if self.connect_in_progress else ""
        selected_count = len(self.selected_hosts)
        total_hosts = len(self.filtered_hosts) if self.search_filter else len(self.hosts)
        if self.search_filter:
            self.update_status(
                f"sel {selected_count}/{total_hosts} (filter '{self.search_filter}') | "
                f"{backend_display} | {mode} | bcast:{broadcast}"
                f"{busy}"
            )
        else:
            self.update_status(
                f"sel {selected_count}/{total_hosts} | {backend_display} | {mode} | bcast:{broadcast}"
                f"{busy}"
            )

    def key_enter(self) -> None:
        """Handle Enter key press directly."""
        if self._is_command_palette_open():
            return
        self.action_connect_selected()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input == self.search_input:
            self.search_filter = event.value.lower().strip()

            # If search is cleared, hide the search container
            if not self.search_filter:
                search_container = self.query_one("#search-container")
                search_container.styles.display = "none"
                self.log_message("Search cleared")

            self.filter_hosts()

    def filter_hosts(self) -> None:
        """Filter hosts based on search term with explicit wildcard support."""
        import fnmatch

        term = (self.search_filter or "").strip()

        # Only add wildcards if user hasn't explicitly added them
        # This gives users control over exact vs fuzzy matching
        if term and not term.startswith("*") and not term.endswith("*"):
            # Implicit fuzzy match - match anywhere in the value
            term = f"*{term}*"
        elif not term:
            # Empty search - show all hosts
            self.filtered_hosts = self.hosts
            self.populate_table(self.get_hosts_to_display())
            self.update_status_selection()
            return

        self.filtered_hosts = [
            host for host in self.hosts
            if any(
                fnmatch.fnmatchcase(self._get_column_value(host, attr).lower(), term.lower())
                for attr in self.config.ui.table_columns
            )
        ]

        # Re-populate table with filtered results
        self.populate_table(self.get_hosts_to_display())

        # Update status
        self.update_status_selection()

    def on_key(self, event: Any) -> None:
        """Handle key presses - specifically check for Enter on DataTable."""
        if self._is_command_palette_open():
            return

        # Check if Enter was pressed while DataTable has focus
        if event.key == "enter" and hasattr(self, 'table') and self.table and self.table.has_focus:
            self.action_connect_selected()
            event.prevent_default()
            event.stop()
            return

    def _is_command_palette_open(self) -> bool:
        """Return True when Textual command palette modal is active."""
        try:
            return self.app.screen.__class__.__name__ == "CommandPalette"
        except Exception:
            return False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key pressed in search input."""
        if event.input == self.search_input and self.table:
            # Focus back on the table when Enter is pressed in search
            self.table.focus()
            if self.search_filter:
                self.log_message(f"Search complete - table focused with filter '{self.search_filter}'")
            else:
                self.log_message("Search complete - table focused")
