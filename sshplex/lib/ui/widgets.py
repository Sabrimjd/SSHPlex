"""Custom widgets for SSHplex TUI."""

from textual.widgets import DataTable, Static, Input, Button, Label
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from rich.text import Text
from typing import List, Dict, Any


class HostTable(DataTable):
    """Host selection table with filtering and multi-select capabilities."""

    selected_hosts = reactive([])

    # Track if shift key is being held for multi-selection
    last_selected_row = None

    def __init__(self):
        """Initialize the host table with appropriate columns."""
        super().__init__()

        # Add columns
        self.add_columns(
            "Select",
            "Hostname",
            "IP Address",
            "Status",
            "Role",
            "Platform",
            "Cluster",
            "Tags"
        )

        # Set cursor type
        self.cursor_type = "row"

        # Enable row selection
        self.zebra_stripes = True

        # Initialize row_data dictionary to store host data
        self.row_data = {}

        # Track selection state
        self.selecting_multiple = False
        self.selection_start = None
        
        # Set up cell styling
        # Force the column to display text exactly as provided
        self.styles.text_style = "none"

    def populate(self, hosts: List[Any]) -> None:
        """Populate table with hosts from NetBox.

        Args:
            hosts: List of Host objects
        """
        # Clear existing rows
        self.clear()

        # Add rows for each host
        for idx, host in enumerate(hosts):
            self.add_row(
                "[ ]",
                host.name,
                host.ip,
                host.metadata.get("status", ""),
                host.metadata.get("role", ""),
                host.metadata.get("platform", ""),
                host.metadata.get("cluster", ""),
                host.metadata.get("tags", "")
            )

            # Store the host reference in the row data
            self.row_data[idx] = {"host": host, "selected": False}

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection event."""
        try:
            from ..logger import get_logger
            logger = get_logger()
            logger.debug(f"Row selection event: {event}")

            # Get the row index
            row_index = event.row_key.row
            logger.debug(f"Selected row: {row_index}")

            # Handle possible multi-select with shift key
            shift_pressed = False
            ctrl_pressed = False

            # Try to get modifiers from event - Textual might provide this info
            if hasattr(event, 'modifiers'):
                shift_pressed = 'shift' in event.modifiers
                ctrl_pressed = 'ctrl' in event.modifiers
                logger.debug(f"Modifiers: shift={shift_pressed}, ctrl={ctrl_pressed}")

            # If shift is pressed and we have a previously selected row
            if shift_pressed and self.last_selected_row is not None:
                # Select range from last selection to current
                logger.debug(f"Selecting range from {self.last_selected_row} to {row_index}")
                self.select_range(self.last_selected_row, row_index)
            else:
                # Normal toggle for single row
                if row_index in self.row_data:
                    # Toggle selection
                    new_state = not self.row_data[row_index]["selected"]
                    self.row_data[row_index]["selected"] = new_state
                    logger.debug(f"Toggled row {row_index} selection to {new_state}")

                    # Update cell with multiple methods for visual feedback
                    select_mark = "[X]" if new_state else "[ ]"
                    logger.debug(f"Updating cell {row_index} to {select_mark}")
                    try:
                        # First method
                        self.update_cell(row_index, 0, select_mark)
                        # Force a refresh to update the display
                        self.refresh()
                        logger.debug("Cell updated successfully")
                    except Exception as cell_error:
                        logger.error(f"Error updating cell: {cell_error}")
                        try:
                            # Alternative method as fallback
                            self.update_cell_at((row_index, 0), select_mark)
                            self.refresh()
                            logger.debug("Cell updated via update_cell_at")
                        except Exception as e:
                            logger.error(f"Failed to update cell with backup method: {e}")

            # Store this row as the last selected
            self.last_selected_row = row_index
            logger.debug(f"Last selected row updated to {row_index}")

            # Update selected hosts list
            self._update_selected_hosts()

        except Exception as e:
            # Log error but don't crash
            from ..logger import get_logger
            logger = get_logger()
            logger.error(f"Error in row selection: {e}")

    def _update_selected_hosts(self) -> None:
      """Update the list of selected hosts."""
      selected = []

      for idx, row_data in self.row_data.items():
          if row_data["selected"]:
              selected.append(row_data["host"])

      self.selected_hosts = selected

    def invert_selection(self) -> None:
        """Invert the current selection."""
        for idx in self.row_data:
            # Toggle selection state
            self.row_data[idx]["selected"] = not self.row_data[idx]["selected"]

            # Update cell
            select_mark = "[X]" if self.row_data[idx]["selected"] else "[ ]"
            self.update_cell(idx, 0, select_mark)

        self._update_selected_hosts()

    def select_range(self, start_index: int, end_index: int, selected: bool = True) -> None:
        """Select or deselect a range of hosts.

        Args:
            start_index: Starting row index
            end_index: Ending row index (inclusive)
            selected: True to select, False to deselect
        """
        # Ensure start_index <= end_index
        if start_index > end_index:
            start_index, end_index = end_index, start_index

        # Select/deselect the range
        for idx in range(start_index, end_index + 1):
            if idx in self.row_data:
                self.row_data[idx]["selected"] = selected

                # Update cell
                select_mark = "[X]" if selected else "[ ]"
                self.update_cell(idx, 0, select_mark)

        # Update selected hosts
        self._update_selected_hosts()

    def select_all(self, selected: bool = True) -> None:
        """Select or deselect all hosts.

        Args:
            selected: True to select all, False to deselect all
        """
        from ..logger import get_logger
        logger = get_logger()
        logger.debug(f"Selecting all hosts: {selected}")
        
        # Check if table is empty
        if not self.row_data:
            logger.debug("Table is empty, nothing to select")
            return

        # First update all data records
        for idx in self.row_data:
            self.row_data[idx]["selected"] = selected
        
        # Then rebuild the entire table display in one go
        rows = []
        for idx, row_data in sorted(self.row_data.items()):
            host = row_data["host"]
            select_mark = "[X]" if selected else "[ ]"
            
            # Create a row with the correct checkbox state
            row = [
                select_mark,
                host.name,
                host.ip,
                host.metadata.get("status", ""),
                host.metadata.get("role", ""),
                host.metadata.get("platform", ""),
                host.metadata.get("cluster", ""),
                host.metadata.get("tags", "")
            ]
            rows.append(row)
        
        # Clear and rebuild the entire table
        try:
            self.clear()
            for row in rows:
                self.add_row(*row)
            logger.debug(f"Rebuilt table with {len(rows)} rows, selection={selected}")
        except Exception as e:
            logger.error(f"Error rebuilding table: {e}")
            # Fallback to individual cell updates
            for idx in self.row_data:
                try:
                    select_mark = "[X]" if selected else "[ ]"
                    self.update_cell(idx, 0, select_mark)
                except Exception as e:
                    logger.error(f"Error updating cell {idx}: {e}")
        
        # Force a final refresh to ensure display updates
        self.refresh()
        
        # Update selected hosts list
        self._update_selected_hosts()
        logger.debug(f"Selected hosts updated: {len(self.selected_hosts)}")

    def deselect_all(self) -> None:
        """Deselect all hosts."""
        self.select_all(selected=False)
        
    def toggle_select_all(self) -> None:
        """Toggle selection state of all hosts."""
        # If any are selected, deselect all
        if self.selected_hosts:
            self.deselect_all()
        else:
            self.select_all(True)

    def select_by_pattern(self, pattern: str, is_regex: bool = False) -> None:
        """Select hosts matching a pattern.

        Args:
            pattern: String pattern to match
            is_regex: Whether to treat pattern as a regex
        """
        import re

        # Prepare regex
        if is_regex:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                # If invalid regex, do substring match instead
                is_regex = False

        # Reset selection
        self.select_all(False)

        # Select matching hosts
        for idx, row_data in self.row_data.items():
            host = row_data["host"]

            # Match by hostname, IP, cluster, or tags
            if is_regex:
                if (regex.search(host.name) or
                    regex.search(host.ip) or
                    regex.search(str(host.metadata.get('cluster', ''))) or
                    regex.search(str(host.metadata.get('tags', '')))):
                    self.row_data[idx]["selected"] = True
                    self.update_cell(idx, 0, "[X]")
            else:
                pattern_lower = pattern.lower()
                if (pattern_lower in host.name.lower() or
                    pattern_lower in host.ip.lower() or
                    pattern_lower in str(host.metadata.get('cluster', '')).lower() or
                    pattern_lower in str(host.metadata.get('tags', '')).lower()):
                    self.row_data[idx]["selected"] = True
                    self.update_cell(idx, 0, "[X]")

        # Update selected hosts
        self._update_selected_hosts()

    def on_key(self, event) -> None:
        """Handle keyboard events for the table."""
        from ..logger import get_logger
        logger = get_logger()
        logger.debug(f"Key event in host table: {event.key}")

        # Check for Space key to select the current row
        if event.key == "space":
            # Get the current cursor position
            cursor_row = self.cursor_row
            if cursor_row is not None:
                # Toggle the selection state
                if cursor_row in self.row_data:
                    current_state = self.row_data[cursor_row]["selected"]
                    new_state = not current_state
                    self.row_data[cursor_row]["selected"] = new_state

                    logger.debug(f"Space toggled row {cursor_row} to {new_state}")

                    # Update the visual checkbox in the table
                    checkbox = "[X]" if new_state else "[ ]"  # Simple X for selected
                    try:
                        # Try different methods to update the cell as Textual's API might vary
                        # Method 1: Direct update_cell method
                        self.update_cell(cursor_row, 0, checkbox)
                        
                        # Make sure to refresh the table display
                        self.refresh()
                        logger.debug(f"Updated cell {cursor_row}, 0 to {checkbox}")
                    except Exception as e:
                        logger.error(f"Error updating cell with update_cell: {e}")
                        try:
                            # Method 2: Using update_cell_at with tuple coordinates
                            self.update_cell_at((cursor_row, 0), checkbox)
                            self.refresh()
                            logger.debug("Updated cell using update_cell_at")
                        except Exception as e2:
                            logger.error(f"Error updating cell with update_cell_at: {e2}")

                    # Update the selected hosts list
                    self._update_selected_hosts()
                    logger.debug(f"Updated selected hosts: {len(self.selected_hosts)}")

                    # Provide feedback in the app's status bar if available
                    try:
                        if hasattr(self.app, "status_bar"):
                            host_name = self.row_data[cursor_row]["host"].name
                            status = f"Selected {host_name}" if new_state else f"Deselected {host_name}"
                            self.app.status_bar.update_status(status)
                    except Exception as e:
                        logger.error(f"Error updating status bar: {e}")

                    # Prevent default handling to avoid the event bubbling up
                    event.prevent_default()
                    event.stop()
                    return

        # Let DataTable handle other keys - don't use super() since parent might not have on_key
        try:
            # Use the object's direct parent class method if it exists
            DataTable.on_key(self, event)
        except AttributeError:
            # If DataTable doesn't have on_key, just pass
            pass

    def on_data_table_cell_selected(self, event) -> None:
        """Handle cell selection to support clicking on the checkbox."""
        from ..logger import get_logger
        logger = get_logger()
        logger.debug(f"Cell selection event: {event}")

        try:
            # Check if the cell is in the checkbox column (column 0)
            if event.cell_key.column == 0:
                row_index = event.cell_key.row
                logger.debug(f"Checkbox cell clicked at row {row_index}")

                # Toggle selection
                new_state = not self.row_data[row_index]["selected"]
                self.row_data[row_index]["selected"] = new_state
                logger.debug(f"Toggled row {row_index} selection to {new_state}")

                # Update cell
                select_mark = "[X]" if new_state else "[ ]"
                logger.debug(f"Updating checkbox cell to {select_mark}")
                self.update_cell(row_index, 0, select_mark)

                # Update selected hosts list
                self._update_selected_hosts()
                logger.debug(f"Selected hosts updated: {len(self.selected_hosts)}")
        except Exception as e:
            logger.error(f"Error handling cell selection: {e}")


class FilterBar(Horizontal):
    """Filter bar for searching and filtering hosts."""

    def __init__(self):
        """Initialize the filter bar with search input and buttons."""
        super().__init__()

        # Create filter input with real-time update capabilities
        self.filter_input = Input(placeholder="Filter hosts (regex supported, e.g. '.*web.*' or 'status:active')")
        self.filter_button = Button("Filter", variant="primary")
        self.regex_button = Button("Regex", variant="default")
        self.clear_button = Button("Clear")

        # Set default state for regex mode
        self.use_regex = False

        # Add children
        self.mount(
            Label("Filter: "),
            self.filter_input,
            self.filter_button,
            self.regex_button,
            self.clear_button
        )

        # Setup real-time filtering
        self.filter_input.changed_timer = None

    def on_input_changed(self, event) -> None:
        """Handle input changes with debouncing for real-time filtering."""
        # We'll use a direct approach without timers for simplicity
        # Trigger the filter action on the parent app
        self.app.action_filter()

    def toggle_regex_mode(self):
        """Toggle regex search mode."""
        self.use_regex = not self.use_regex

        # Update button style
        if self.use_regex:
            self.regex_button.variant = "success"
        else:
            self.regex_button.variant = "default"

        # Re-apply filter with new regex setting if there's text in the filter box
        if self.filter_input.value:
            self.app.action_filter()


class StatusBar(Static):
    """Status bar showing connection and selection information."""

    def __init__(self):
        """Initialize the status bar."""
        super().__init__("Ready")

        # Set style
        self.styles.background = "blue"
        self.styles.color = "white"
        self.styles.padding = (0, 1)

    def update_status(self, message: str, status_type: str = "info") -> None:
        """Update the status message.

        Args:
            message: Status message to display
            status_type: Type of status (info, warning, error)
        """
        if status_type == "error":
            self.update(Text(f"ERROR: {message}", style="bold red"))
        elif status_type == "warning":
            self.update(Text(f"WARNING: {message}", style="bold yellow"))
        elif status_type == "success":
            self.update(Text(f"SUCCESS: {message}", style="bold green"))
        else:
            self.update(Text(message))


class ActionBar(Horizontal):
    """Action bar with buttons for host operations."""

    def __init__(self):
        """Initialize the action bar with operation buttons."""
        super().__init__()

        self.connect_button = Button("Connect", variant="success")
        self.refresh_button = Button("Refresh", variant="primary")
        self.quit_button = Button("Quit", variant="error")

        # Add children and set spacing
        self.mount(self.connect_button, self.refresh_button, self.quit_button)
        self.styles.gap = "1"
