"""SSHplex TUI Host Selector with Textual."""

from typing import List, Optional, Set
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import DataTable, Log, Static, Footer
from textual.binding import Binding
from textual.reactive import reactive
from textual import events

from ..logger import get_logger
from ..sot.netbox import NetBoxProvider
from ..sot.base import Host


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
    }

    DataTable {
        height: 1fr;
    }

    Log {
        height: 1fr;
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
        Binding("q", "quit", "Quit", show=True),
    ]

    selected_hosts: reactive[Set[str]] = reactive(set())

    def __init__(self, config):
        """Initialize the host selector.

        Args:
            config: SSHplex configuration object
        """
        super().__init__()
        self.config = config
        self.logger = get_logger()
        self.hosts: List[Host] = []
        self.netbox: Optional[NetBoxProvider] = None
        self.table: Optional[DataTable] = None
        self.log_widget: Optional[Log] = None
        self.status_widget: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""

        # Log panel at top (conditionally shown)
        if self.config.ui.show_log_panel:
            with Container(id="log-panel"):
                yield Log(id="log", auto_scroll=True)

        # Main content panel
        with Container(id="main-panel"):
            yield DataTable(id="host-table", cursor_type="row")

        # Status bar
        with Container(id="status-bar"):
            yield Static("SSHplex - Loading hosts...", id="status")

        # Footer with keybindings
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the UI and load hosts."""
        # Get widget references
        self.table = self.query_one("#host-table", DataTable)
        if self.config.ui.show_log_panel:
            self.log_widget = self.query_one("#log", Log)
        self.status_widget = self.query_one("#status", Static)

        # Setup table columns
        self.setup_table()

        # Focus on the table by default
        if self.table:
            self.table.focus()

        # Load hosts from NetBox
        self.call_later(self.load_hosts)

        self.log_message("SSHplex TUI started")

    def setup_table(self) -> None:
        """Setup the data table columns."""
        if not self.table:
            return

        # Add checkbox column with key
        self.table.add_column("✓", width=3, key="checkbox")

        # Add configured columns
        for column in self.config.ui.table_columns:
            if column == "name":
                self.table.add_column("Name", width=15, key="name")
            elif column == "ip":
                self.table.add_column("IP Address", width=15, key="ip")
            elif column == "cluster":
                self.table.add_column("Cluster", width=20, key="cluster")
            elif column == "role":
                self.table.add_column("Role", width=15, key="role")
            elif column == "tags":
                self.table.add_column("Tags", width=30, key="tags")
            elif column == "description":
                self.table.add_column("Description", width=40, key="description")

    async def load_hosts(self) -> None:
        """Load hosts from NetBox."""
        self.log_message("Connecting to NetBox...")
        self.update_status("Connecting to NetBox...")

        try:
            # Initialize NetBox provider
            self.netbox = NetBoxProvider(
                url=self.config.netbox.url,
                token=self.config.netbox.token,
                verify_ssl=self.config.netbox.verify_ssl,
                timeout=self.config.netbox.timeout
            )

            # Connect to NetBox
            if not self.netbox.connect():
                self.log_message("ERROR: Failed to connect to NetBox", level="error")
                self.update_status("Error: NetBox connection failed")
                return

            self.log_message("Successfully connected to NetBox")
            self.update_status("Loading hosts...")

            # Get hosts with filters
            self.hosts = self.netbox.get_hosts(filters=self.config.netbox.default_filters)

            if not self.hosts:
                self.log_message("WARNING: No hosts found matching filters", level="warning")
                self.update_status("No hosts found")
                return

            # Populate table
            self.populate_table()

            self.log_message(f"Loaded {len(self.hosts)} hosts successfully")
            self.update_status(f"Loaded {len(self.hosts)} hosts - Use SPACE to select, A to select all, D to deselect all")

        except Exception as e:
            self.log_message(f"ERROR: Failed to load hosts: {e}", level="error")
            self.update_status(f"Error: {e}")

    def populate_table(self) -> None:
        """Populate the table with host data."""
        if not self.table or not self.hosts:
            return

        for host in self.hosts:
            # Build row data based on configured columns
            row_data = ["[ ]"]  # Checkbox column

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
        if cursor_row >= 0 and cursor_row < len(self.hosts):
            host_name = self.hosts[cursor_row].name

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
        """Select all hosts."""
        if not self.hosts:
            return

        self.selected_hosts.clear()
        for host in self.hosts:
            self.selected_hosts.add(host.name)
            self.update_row_checkbox(host.name, True)

        self.log_message(f"Selected all {len(self.hosts)} hosts")
        self.update_status_selection()

    def action_deselect_all(self) -> None:
        """Deselect all hosts."""
        if not self.hosts:
            return

        self.selected_hosts.clear()
        for host in self.hosts:
            self.update_row_checkbox(host.name, False)

        self.log_message("Deselected all hosts")
        self.update_status_selection()

    def action_connect_selected(self) -> None:
        """Connect to selected hosts."""
        if not self.selected_hosts:
            self.log_message("WARNING: No hosts selected for connection", level="warning")
            return

        selected_host_objects = [h for h in self.hosts if h.name in self.selected_hosts]
        self.log_message(f"Connecting to {len(selected_host_objects)} selected hosts...")

        # For Phase 1, just log the selection - connection logic will be added later
        for host in selected_host_objects:
            self.log_message(f"Would connect to: {host.name} ({host.ip})")

        # Exit the app and return selected hosts
        self.exit(selected_host_objects)

    def update_row_checkbox(self, row_key: str, selected: bool) -> None:
        """Update the checkbox for a specific row."""
        if not self.table:
            return

        checkbox = "[X]" if selected else "[ ]"
        self.table.update_cell(row_key, "checkbox", checkbox)

    def update_status_selection(self) -> None:
        """Update status bar with selection count."""
        count = len(self.selected_hosts)
        total = len(self.hosts)

        if count == 0:
            status = f"Loaded {total} hosts - No hosts selected"
        elif count == 1:
            status = f"{count} host selected - Press ENTER to connect"
        else:
            status = f"{count} hosts selected - Press ENTER to connect"

        self.update_status(status)

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
