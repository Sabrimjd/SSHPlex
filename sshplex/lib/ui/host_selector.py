"""SSHplex TUI Host Selector with Textual."""

from typing import List, Optional, Set, Any
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import DataTable, Log, Static, Footer, Input
from textual.binding import Binding
from textual.reactive import reactive
from textual import events

from ... import __version__
from ..logger import get_logger
from ..sot.factory import SoTFactory
from ..sot.base import Host
from .session_manager import TmuxSessionManager


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
        height: 3;
        background: $surface;
        color: $text;
        padding: 0 1;
        margin: 0 1;
        dock: bottom;
        layout: horizontal;
    }

    #status-content {
        width: 1fr;
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
        Binding("p", "toggle_panes", "Toggle Panes/Tabs", show=True),
        Binding("b", "toggle_broadcast", "Toggle Broadcast", show=True),
        Binding("escape", "focus_table", "Focus Table", show=False),
        Binding("q", "quit", "Quit", show=True),
    ]

    selected_hosts: reactive[Set[str]] = reactive(set())
    search_filter: reactive[str] = reactive("")
    use_panes: reactive[bool] = reactive(True)  # True for panes, False for tabs
    use_broadcast: reactive[bool] = reactive(False)  # True for broadcast enabled, False for disabled

    def __init__(self, config: Any) -> None:
        """Initialize the host selector.

        Args:
            config: SSHplex configuration object
        """
        super().__init__()
        self.config = config
        self.logger = get_logger()
        self.hosts: List[Host] = []
        self.filtered_hosts: List[Host] = []
        self.sot_factory: Optional[SoTFactory] = None
        self.table: Optional[DataTable] = None
        self.log_widget: Optional[Log] = None
        self.status_widget: Optional[Static] = None
        self.search_input: Optional[Input] = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""

        # Log panel at top (conditionally shown)
        if self.config.ui.show_log_panel:
            with Container(id="log-panel"):
                yield Log(id="log", auto_scroll=True)

        # Search input (hidden by default)
        with Container(id="search-container"):
            yield Input(placeholder="Search hosts by name...", id="search-input")

        # Main content panel
        with Container(id="main-panel"):
            yield DataTable(id="host-table", cursor_type="row")

        # Status bar with version display
        with Container(id="status-bar"):
            yield Static("SSHplex - Loading hosts...", id="status-content")
            yield Static(f"SSHplex v{__version__}", id="version-display")

        # Footer with keybindings
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the UI and load hosts."""
        # Get widget references
        self.table = self.query_one("#host-table", DataTable)
        if self.config.ui.show_log_panel:
            self.log_widget = self.query_one("#log", Log)
        self.status_widget = self.query_one("#status-content", Static)
        self.search_input = self.query_one("#search-input", Input)

        # Setup table columns
        self.setup_table()

        # Focus on the table by default
        if self.table:
            self.table.focus()

        # Load hosts from SoT providers
        self.call_later(self.load_hosts)

        self.log_message("SSHplex TUI started")

    def setup_table(self) -> None:
        """Setup the data table columns with responsive widths."""
        if not self.table:
            return

        # Calculate total columns to distribute width proportionally
        total_columns = len(self.config.ui.table_columns) + 1  # +1 for checkbox
        
        # Add checkbox column (fixed small width)
        self.table.add_column("✓", width=3, key="checkbox")

        # Add configured columns with proportional widths
        for column in self.config.ui.table_columns:
            if column == "name":
                # Name gets more space as it's usually important
                self.table.add_column("Name", width=None, key="name")
            elif column == "ip":
                # IP addresses have predictable length, can be smaller
                self.table.add_column("IP Address", width=None, key="ip")
            elif column == "cluster":
                self.table.add_column("Cluster", width=None, key="cluster")
            elif column == "role":
                self.table.add_column("Role", width=None, key="role")
            elif column == "tags":
                # Tags might be longer, give more space
                self.table.add_column("Tags", width=None, key="tags")
            elif column == "description":
                # Description usually needs the most space
                self.table.add_column("Description", width=None, key="description")

    async def load_hosts(self) -> None:
        """Load hosts from all configured SoT providers."""
        self.log_message("Initializing SoT providers...")
        self.update_status("Initializing SoT providers...")

        try:
            # Initialize SoT factory
            self.sot_factory = SoTFactory(self.config)

            # Initialize all providers
            if not self.sot_factory.initialize_providers():
                self.log_message("ERROR: Failed to initialize any SoT providers", level="error")
                self.update_status("Error: SoT provider initialization failed")
                return

            provider_names = ', '.join(self.sot_factory.get_provider_names())
            self.log_message(f"Successfully initialized {self.sot_factory.get_provider_count()} provider(s): {provider_names}")
            self.update_status("Loading hosts...")

            # Get hosts from all providers
            self.hosts = self.sot_factory.get_all_hosts()
            self.filtered_hosts = self.hosts.copy()  # Initialize filtered hosts

            if not self.hosts:
                self.log_message("WARNING: No hosts found matching filters", level="warning")
                self.update_status("No hosts found")
                return

            # Populate table
            self.populate_table()

            self.log_message(f"Loaded {len(self.hosts)} hosts successfully from {self.sot_factory.get_provider_count()} provider(s)")
            self.update_status_with_mode()

        except Exception as e:
            self.log_message(f"ERROR: Failed to load hosts: {e}", level="error")
            self.update_status(f"Error: {e}")

    def populate_table(self) -> None:
        """Populate the table with host data."""
        if not self.table:
            return

        # Clear existing table data
        self.table.clear()

        # Use filtered hosts if search is active, otherwise use all hosts
        hosts_to_display = self.filtered_hosts if self.search_filter else self.hosts

        if not hosts_to_display:
            return

        for host in hosts_to_display:
            # Build row data based on configured columns
            row_data = ["[ ]"]  # Checkbox column

            # Check if this host is selected and update checkbox
            if host.name in self.selected_hosts:
                row_data[0] = "[x]"

            for column in self.config.ui.table_columns:
                if column == "name":
                    row_data.append(host.name)
                elif column == "ip":
                    row_data.append(host.ip)
                elif column == "cluster":
                    row_data.append(getattr(host, 'cluster', 'N/A'))
                elif column == "role":
                    row_data.append(getattr(host, 'role', 'N/A'))
                elif column == "tags":
                    row_data.append(getattr(host, 'tags', ''))
                elif column == "description":
                    row_data.append(getattr(host, 'description', ''))

            self.table.add_row(*row_data, key=host.name)

    def action_toggle_select(self) -> None:
        """Toggle selection of current row."""
        if not self.table or not self.hosts:
            return

        cursor_row = self.table.cursor_row
        hosts_to_use = self.filtered_hosts if self.search_filter else self.hosts

        if cursor_row >= 0 and cursor_row < len(hosts_to_use):
            host_name = hosts_to_use[cursor_row].name

            if host_name in self.selected_hosts:
                self.selected_hosts.discard(host_name)
                self.update_row_checkbox(host_name, False)
                self.log_message(f"Deselected: {host_name}")
            else:
                self.selected_hosts.add(host_name)
                self.update_row_checkbox(host_name, True)
                self.log_message(f"Selected: {host_name}")

            self.update_status_selection()

    def action_select_all(self) -> None:
        """Select all hosts (filtered if search is active)."""
        if not self.hosts:
            return

        hosts_to_select = self.filtered_hosts if self.search_filter else self.hosts

        for host in hosts_to_select:
            self.selected_hosts.add(host.name)
            self.update_row_checkbox(host.name, True)

        self.log_message(f"Selected all {len(hosts_to_select)} hosts")
        self.update_status_selection()

    def action_deselect_all(self) -> None:
        """Deselect all hosts (filtered if search is active)."""
        if not self.hosts:
            return

        hosts_to_deselect = self.filtered_hosts if self.search_filter else self.hosts

        for host in hosts_to_deselect:
            self.selected_hosts.discard(host.name)
            self.update_row_checkbox(host.name, False)

        self.log_message(f"Deselected all {len(hosts_to_deselect)} hosts")
        self.update_status_selection()

    def action_connect_selected(self) -> None:
        """Connect to selected hosts and exit the application."""
        self.log_message("INFO: Enter key pressed - processing connection request", level="info")

        if not self.selected_hosts:
            self.log_message("WARNING: No hosts selected for connection", level="warning")
            return

        selected_host_objects = [h for h in self.hosts if h.name in self.selected_hosts]
        mode = "Panes" if self.use_panes else "Tabs"
        broadcast = "ON" if self.use_broadcast else "OFF"
        self.log_message(f"INFO: Connecting to {len(selected_host_objects)} selected hosts in {mode} mode with Broadcast {broadcast}...", level="info")

        # just log the selection
        for host in selected_host_objects:
            self.log_message(f"INFO: Would connect to: {host.name} ({host.ip}) - Cluster: {getattr(host, 'cluster', 'N/A')}", level="info")

        self.log_message(f"INFO: Connection request complete. Mode: {mode}, Broadcast: {broadcast}, Hosts: {len(selected_host_objects)}", level="info")
        self.log_message("INFO: Exiting SSHplex TUI application...", level="info")

        # Exit the app and return selected hosts
        self.app.exit(selected_host_objects)

    def action_show_sessions(self) -> None:
        """Show the tmux session manager modal."""
        self.log_message("Opening tmux session manager...")
        session_manager = TmuxSessionManager()
        self.push_screen(session_manager)

    def update_row_checkbox(self, row_key: str, selected: bool) -> None:
        """Update the checkbox for a specific row."""
        if not self.table:
            return

        checkbox = "[X]" if selected else "[ ]"
        self.table.update_cell(row_key, "checkbox", checkbox)

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
            self.log_widget.write_line(f"[{timestamp}] {level_prefix}: {message}")

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

            self.log_message("Search cleared - showing all hosts")
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
        selected_count = len(self.selected_hosts)
        total_hosts = len(self.filtered_hosts) if self.search_filter else len(self.hosts)

        if self.search_filter:
            self.update_status(f"Filter: '{self.search_filter}' - {total_hosts}/{len(self.hosts)} hosts, {selected_count} selected | Mode: {mode} | Broadcast: {broadcast}")
        else:
            self.update_status(f"{total_hosts} hosts loaded, {selected_count} selected | Mode: {mode} | Broadcast: {broadcast}")

    def key_enter(self) -> None:
        """Handle Enter key press directly."""
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
        """Filter hosts based on search term."""
        if not self.search_filter:
            self.filtered_hosts = self.hosts.copy()
        else:
            self.filtered_hosts = [
                host for host in self.hosts
                if self.search_filter in host.name.lower()
            ]

        # Re-populate table with filtered results
        self.populate_table()

        # Update status
        if self.search_filter:
            filtered_count = len(self.filtered_hosts)
            total_count = len(self.hosts)
            selected_count = len(self.selected_hosts)
            self.update_status(f"Filter: '{self.search_filter}' - {filtered_count}/{total_count} hosts shown, {selected_count} selected")
        else:
            self.update_status_selection()

    def on_key(self, event: Any) -> None:
        """Handle key presses - specifically check for Enter on DataTable."""
        self.log_message(f"DEBUG: Key pressed: {event.key}", level="info")

        # Check if Enter was pressed while DataTable has focus
        if event.key == "enter" and hasattr(self, 'table') and self.table and self.table.has_focus:
            self.log_message("DEBUG: Enter key pressed on focused DataTable - calling connect action", level="info")
            self.action_connect_selected()
            event.prevent_default()
            event.stop()
            return

        # Let the event bubble up for normal processing
        event.prevent_default = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key pressed in search input."""
        if event.input == self.search_input:
            # Focus back on the table when Enter is pressed in search
            if self.table:
                self.table.focus()
                if self.search_filter:
                    self.log_message(f"Search complete - table focused with filter '{self.search_filter}'")
                else:
                    self.log_message("Search complete - table focused")
