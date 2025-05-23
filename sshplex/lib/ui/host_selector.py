"""Host selection TUI for SSHplex."""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from rich.panel import Panel

from ..logger import get_logger
from ..sot.netbox import NetBoxProvider
from .widgets import HostTable, FilterBar, StatusBar, ActionBar


class HostSelector(App):
    """Main TUI application for host selection."""

    # App bindings
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit"),
        Binding(key="r", action="refresh", description="Refresh hosts"),
        #Binding(key="c", action="connect", description="Connect to selected hosts"),
        #Binding(key="f", action="focus_filter", description="Focus filter"),
        Binding(key="a", action="select_all", description="Select all hosts"),
        Binding(key="d", action="deselect_all", description="Deselect all hosts"),
        #Binding(key="x", action="toggle_regex", description="Toggle regex mode"),
        Binding(key="/", action="focus_filter", description="Focus filter"),
        Binding(key="enter", action="connect", description="Connect to selected hosts"),
        Binding(key="tab", action="toggle_focus", description="Toggle focus"),
        Binding(key="escape", action="focus_table", description="Focus table"),
    ]

    def __init__(self, config):
        """Initialize the host selector with configuration.

        Args:
            config: SSHplex configuration object
        """
        super().__init__()

        self.config = config
        self.logger = get_logger()
        self.hosts = []

        # Initialize NetBox provider
        self.netbox = NetBoxProvider(
            url=config.netbox.url,
            token=config.netbox.token,
            verify_ssl=config.netbox.verify_ssl,
            timeout=config.netbox.timeout
        )

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header(show_clock=True)

        with Container():
            yield Static(Panel("SSHplex - SSH Connection Multiplexer", border_style="blue"))

            with Vertical():
                self.filter_bar = FilterBar()
                yield self.filter_bar

                self.host_table = HostTable()
                yield self.host_table

                self.action_bar = ActionBar()
                yield self.action_bar

                self.status_bar = StatusBar()
                yield self.status_bar

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app when mounted."""
        self.status_bar.update_status("Connecting to NetBox...")

        # Connect to the API
        if not self.netbox.connect():
            self.status_bar.update_status("Failed to connect to NetBox", "error")
            return

        # Fetch hosts
        self.refresh_hosts()

        # Connect button handler
        self.action_bar.connect_button.on_click = self.action_connect

        # Refresh button handler
        self.action_bar.refresh_button.on_click = self.action_refresh

        # Quit button handler
        self.action_bar.quit_button.on_click = self.action_quit

        # Filter button handler
        self.filter_bar.filter_button.on_click = self.action_filter

        # Clear button handler
        self.filter_bar.clear_button.on_click = self.action_clear_filter

        # Regex button handler
        self.filter_bar.regex_button.on_click = self.action_toggle_regex

        # Set initial focus to host table
        self.host_table.focus()
        self.status_bar.update_status("Ready. Press Space to select hosts, Enter to connect, Tab to toggle focus.")

    def action_refresh(self) -> None:
        """Refresh the host list."""
        self.refresh_hosts()

    def action_connect(self) -> None:
        """Connect to selected hosts."""
        try:
            selected_hosts = self.host_table.selected_hosts

            if not selected_hosts:
                self.status_bar.update_status("No hosts selected", "warning")
                return

            self.status_bar.update_status(f"Selected {len(selected_hosts)} hosts for connection", "success")

            # Phase 1: Just log the selected hosts
            self.logger.info(f"Selected {len(selected_hosts)} hosts:")
            for host in selected_hosts:
                self.logger.info(f"  - {host.name} ({host.ip})")

            # In Phase 1, we don't actually connect
            self.exit(result=selected_hosts)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.status_bar.update_status(f"Connection error: {e}", "error")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_filter(self) -> None:
        """Filter hosts based on input."""
        filter_text = self.filter_bar.filter_input.value

        if not filter_text:
            self.refresh_hosts()
            return

        # Check if we're using regex mode
        use_regex = self.filter_bar.use_regex

        try:
            # Apply filter to existing hosts
            if use_regex:
                import re
                pattern = re.compile(filter_text, re.IGNORECASE)

                filtered_hosts = []
                for host in self.hosts:
                    # Regex search in hostname, IP, or other fields
                    if (re.search(pattern, host.name) or
                        re.search(pattern, host.ip) or
                        re.search(pattern, host.metadata.get('status', '')) or
                        re.search(pattern, host.metadata.get('role', '')) or
                        re.search(pattern, host.metadata.get('platform', '')) or
                        re.search(pattern, host.metadata.get('cluster', '')) or
                        re.search(pattern, host.metadata.get('tags', ''))):
                        filtered_hosts.append(host)

                # Update table with filtered hosts
                self.host_table.populate(filtered_hosts)
                self.status_bar.update_status(
                    f"Regex filtered: showing {len(filtered_hosts)} of {len(self.hosts)} hosts"
                )
            else:
                # Standard substring search
                filtered_hosts = []
                for host in self.hosts:
                    # Simple substring search in hostname, IP or other fields
                    if (filter_text.lower() in host.name.lower() or
                        filter_text.lower() in host.ip.lower() or
                        filter_text.lower() in host.metadata.get('status', '').lower() or
                        filter_text.lower() in host.metadata.get('role', '').lower() or
                        filter_text.lower() in host.metadata.get('platform', '').lower() or
                        filter_text.lower() in host.metadata.get('cluster', '').lower() or
                        filter_text.lower() in host.metadata.get('tags', '').lower()):
                        filtered_hosts.append(host)

                # Update table with filtered hosts
                self.host_table.populate(filtered_hosts)
                self.status_bar.update_status(
                    f"Filtered: showing {len(filtered_hosts)} of {len(self.hosts)} hosts"
                )
        except re.error:
            # Handle invalid regex pattern
            self.status_bar.update_status(f"Invalid regex pattern: {filter_text}", "error")

    def action_clear_filter(self) -> None:
        """Clear the filter and show all hosts."""
        self.filter_bar.filter_input.value = ""
        self.refresh_hosts()

    def action_focus_filter(self) -> None:
        """Focus the filter input."""
        self.filter_bar.filter_input.focus()

    def refresh_hosts(self) -> None:
        """Refresh the host list from NetBox."""
        self.status_bar.update_status("Loading hosts from NetBox...")

        # Fetch hosts with filters from config
        hosts = self.netbox.get_hosts(filters=self.config.netbox.default_filters)
        self.hosts = hosts

        if not hosts:
            self.status_bar.update_status("No hosts found", "warning")
            return

        # Update the table
        self.host_table.populate(hosts)
        self.status_bar.update_status(f"Loaded {len(hosts)} hosts from NetBox", "success")

    def action_select_all(self) -> None:
        """Select all hosts."""
        self.host_table.select_all()
        self.status_bar.update_status(f"Selected all {len(self.hosts)} hosts", "success")

    def action_deselect_all(self) -> None:
        """Deselect all hosts."""
        self.host_table.deselect_all()
        self.status_bar.update_status("Cleared all selections", "info")

    def action_invert_selection(self) -> None:
        """Invert host selection."""
        self.host_table.invert_selection()
        self.status_bar.update_status("Selection inverted")

    def action_toggle_regex(self) -> None:
        """Toggle regex search mode."""
        self.filter_bar.toggle_regex_mode()

        if self.filter_bar.use_regex:
            self.status_bar.update_status("Regex search enabled", "success")
        else:
            self.status_bar.update_status("Regex search disabled")

    def action_apply_filter(self) -> None:
        """Apply the current filter."""
        self.action_filter()

    def action_toggle_focus(self) -> None:
        """Toggle focus between filter input and host table."""
        if self.focused is self.filter_bar.filter_input:
            # If filter is focused, switch to table
            self.host_table.focus()
            self.status_bar.update_status("Table focused. Use arrow keys to navigate, Space to select, Enter to connect.")
        else:
            # Otherwise switch to filter
            self.filter_bar.filter_input.focus()
            self.status_bar.update_status("Filter focused. Type to filter hosts in real-time.")

    def action_focus_table(self) -> None:
        """Focus the host table."""
        self.host_table.focus()
        self.status_bar.update_status("Table focused. Use arrow keys to navigate, Space to select, Enter to connect.")

    def on_key(self, event) -> None:
        """Handle keyboard events for selection."""
        # Check for keyboard shortcuts that aren't in bindings
        key = event.key
        self.logger.debug(f"Host selector received key: {key}")

        if key == "ctrl+a":
            # Select all hosts
            self.action_select_all()
        elif key == "ctrl+d":
            # Deselect all hosts
            self.action_deselect_all()
        elif key == "space" and self.focused is self.host_table:
            # Let the host table handle space selection
            self.logger.debug("Space pressed with table focused - delegating to table")
            pass
        elif key == "enter" and self.focused is self.host_table:
            # Connect to hosts when Enter is pressed while the host table has focus
            self.logger.debug("Enter pressed with table focused - connecting to hosts")
            self.action_connect()
            # Prevent further handling of this key
            event.stop()
            event.prevent_default()
