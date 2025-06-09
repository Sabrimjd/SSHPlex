"""SSHplex tmux multiplexer implementation."""

import libtmux
from typing import Optional, Dict
from datetime import datetime

from .base import MultiplexerBase
from ..logger import get_logger


class TmuxManager(MultiplexerBase):
    """tmux implementation for SSHplex multiplexer."""

    def __init__(self, session_name: Optional[str] = None, max_panes_per_window: int = 5):
        """Initialize tmux manager with session name and max panes per window."""
        if session_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"

        super().__init__(session_name)
        self.logger = get_logger()
        self.server = libtmux.Server()
        self.session: Optional[libtmux.Session] = None
        self.current_window: Optional[libtmux.Window] = None
        self.windows: Dict[int, libtmux.Window] = {}  # window_id -> Window
        self.panes: Dict[str, libtmux.Pane] = {}
        self.max_panes_per_window = max_panes_per_window
        self.current_window_pane_count = 0

    def create_session(self) -> bool:
        """Create a new tmux session with SSHplex branding."""
        try:
            self.logger.info(f"SSHplex: Creating tmux session '{self.session_name}'")

            # Check if session already exists
            if self.server.has_session(self.session_name):
                self.logger.warning(f"SSHplex: Session '{self.session_name}' already exists")
                self.session = self.server.sessions.get(session_name=self.session_name)
            else:
                # Create new session
                self.session = self.server.new_session(
                    session_name=self.session_name,
                    window_name="sshplex",
                    start_directory="~"
                )

            # Get the main window and initialize tracking
            if self.session:
                self.current_window = self.session.attached_window
                if self.current_window:
                    self.windows[0] = self.current_window
                    self.current_window_pane_count = 0
                self.logger.info(f"SSHplex: tmux session '{self.session_name}' created successfully")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create tmux session: {e}")
            return False

    def create_pane(self, hostname: str, command: Optional[str] = None) -> bool:
        """Create a new pane for the given hostname."""
        try:
            if self.session is None or self.current_window is None:
                if not self.create_session():
                    return False

            self.logger.info(f"SSHplex: Creating pane for host '{hostname}'")

            # Check if we need to create a new window due to pane limit
            if self.current_window_pane_count >= self.max_panes_per_window:
                self.logger.info(f"SSHplex: Reached max panes per window ({self.max_panes_per_window}), creating new window")
                window_index = len(self.windows)
                if self.session is not None:
                    new_window = self.session.new_window(window_name=f"sshplex-{window_index}")
                    if new_window:
                        self.current_window = new_window
                        self.windows[window_index] = new_window
                        self.current_window_pane_count = 0
                        self.logger.info(f"SSHplex: Created new window {window_index} for additional panes")
                    else:
                        self.logger.error("SSHplex: Failed to create new window, using current window")
                else:
                    self.logger.error("SSHplex: No session available for creating new window")

            # Split window to create new pane (except for the first pane in current window)
            if self.current_window is None:
                self.logger.error("SSHplex: No window available for pane creation")
                return False

            if self.current_window_pane_count == 0:
                # First pane in this window - use the existing window pane
                pane = self.current_window.attached_pane
                if pane is None:
                    raise RuntimeError(f"No attached pane available for {hostname}")
            else:
                # Additional panes - split the window
                pane = self.current_window.split_window()
                if pane is None:
                    raise RuntimeError(f"Failed to create tmux pane for {hostname}")

            # Store pane reference and increment counter
            self.panes[hostname] = pane
            self.current_window_pane_count += 1

            # Set pane title
            self.set_pane_title(hostname, hostname)

            # Execute the provided command (should be SSH command)
            if command:
                self.send_command(hostname, command)

            self.logger.info(f"SSHplex: Pane created for '{hostname}' successfully (window panes: {self.current_window_pane_count}/{self.max_panes_per_window})")
            return True

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create pane for '{hostname}': {e}")
            return False

    def create_window(self, hostname: str, command: Optional[str] = None) -> bool:
        """Create a new window (tab) in the tmux session and execute a command."""
        try:
            if not self.session:
                self.logger.error("SSHplex: No active tmux session for window creation")
                return False

            # Create new window with hostname as the window name
            window = self.session.new_window(window_name=hostname)

            if not window:
                self.logger.error(f"SSHplex: Failed to create window for '{hostname}'")
                return False

            # Get the main pane of the new window
            pane = window.panes[0] if window.panes else None
            if not pane:
                self.logger.error(f"SSHplex: No pane found in new window for '{hostname}'")
                return False

            # Store the pane reference
            self.panes[hostname] = pane

            # Execute the provided command (should be SSH command)
            if command:
                pane.send_keys(command, enter=True)

            self.logger.info(f"SSHplex: Window created for '{hostname}' successfully")
            return True

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create window for '{hostname}': {e}")
            return False

    def set_pane_title(self, hostname: str, title: str) -> bool:
        """Set the title of a specific pane."""
        try:
            if hostname not in self.panes:
                self.logger.error(f"SSHplex: Pane for '{hostname}' not found")
                return False

            pane = self.panes[hostname]
            # Set pane title using printf escape sequence
            pane.send_keys(f'printf "\\033]2;{title}\\033\\\\"', enter=True)
            return True

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to set pane title for '{hostname}': {e}")
            return False

    def send_command(self, hostname: str, command: str) -> bool:
        """Send a command to a specific pane."""
        try:
            if hostname not in self.panes:
                self.logger.error(f"SSHplex: Pane for '{hostname}' not found")
                return False

            pane = self.panes[hostname]
            pane.send_keys(command, enter=True)
            self.logger.debug(f"SSHplex: Command sent to '{hostname}': {command}")
            return True

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to send command to '{hostname}': {e}")
            return False

    def broadcast_command(self, command: str) -> bool:
        """Send a command to all panes."""
        try:
            success_count = 0
            for hostname in self.panes:
                if self.send_command(hostname, command):
                    success_count += 1

            self.logger.info(f"SSHplex: Broadcast command sent to {success_count}/{len(self.panes)} panes")
            return success_count == len(self.panes)

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to broadcast command: {e}")
            return False

    def close_session(self) -> None:
        """Close the tmux session."""
        try:
            if self.session:
                self.logger.info(f"SSHplex: Closing tmux session '{self.session_name}'")
                self.session.kill_session()
                self.session = None
                self.current_window = None
                self.windows.clear()
                self.panes.clear()
                self.current_window_pane_count = 0

        except Exception as e:
            self.logger.error(f"SSHplex: Error closing session: {e}")

    def attach_to_session(self, auto_attach: bool = True) -> None:
        """Attach to the tmux session."""
        try:
            if self.session:
                # Set up custom key binding for broadcast toggle
                self.setup_broadcast_keybinding()

                if auto_attach:
                    self.logger.info(f"SSHplex: Auto-attaching to tmux session '{self.session_name}'")
                    # Auto-attach to the session by replacing current shell
                    import os
                    import sys
                    # Use exec to replace the current Python process with tmux attach
                    os.execlp("tmux", "tmux", "attach-session", "-t", self.session_name)
                else:
                    self.logger.info(f"SSHplex: Tmux session '{self.session_name}' is ready for attachment")
                    print(f"\nTo attach to the session, run: tmux attach-session -t {self.session_name}")
            else:
                self.logger.error("SSHplex: No session to attach to")

        except Exception as e:
            self.logger.error(f"SSHplex: Error attaching to session: {e}")

    def setup_broadcast_keybinding(self) -> bool:
        """Set up custom keybinding for broadcast toggle."""
        try:
            if not self.session:
                return False

            # Set up key binding for broadcast toggle (prefix + b)
            # This command will toggle synchronize-panes for the current window
            toggle_command = "if -F '#{synchronize-panes}' 'setw synchronize-panes off; display-message \"Broadcast OFF\"' 'setw synchronize-panes on; display-message \"Broadcast ON\"'"

            # Bind 'b' key (after prefix) to toggle broadcast
            self.session.cmd('bind-key', 'b', toggle_command)

            self.logger.info("SSHplex: Set up broadcast toggle keybinding (prefix + b)")
            return True

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to set up broadcast keybinding: {e}")
            return False

    def get_session_name(self) -> str:
        """Get the tmux session name for external attachment."""
        return self.session_name

    def setup_tiled_layout(self) -> bool:
        """Set up tiled layout for multiple panes in all windows."""
        try:
            if not self.windows:
                return False

            layout_applied = False
            for window_id, window in self.windows.items():
                if window and len(window.panes) > 1:
                    window.select_layout('tiled')
                    self.logger.info(f"SSHplex: Applied tiled layout to window {window_id}")
                    layout_applied = True

            if layout_applied:
                self.logger.info("SSHplex: Applied tiled layout to tmux windows")
            return layout_applied

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to set tiled layout: {e}")
            return False

    def enable_broadcast(self) -> bool:
        """Enable broadcast mode (synchronize-panes) for all windows in the session."""
        try:
            if not self.session:
                self.logger.error("SSHplex: No session available for broadcast")
                return False

            broadcast_enabled = False
            for window_id, window in self.windows.items():
                if window and len(window.panes) > 1:
                    window.cmd('set-window-option', 'synchronize-panes', 'on')
                    self.logger.info(f"SSHplex: Enabled broadcast for window {window_id}")
                    broadcast_enabled = True

            if broadcast_enabled:
                self.logger.info("SSHplex: Broadcast mode enabled for tmux session")
            return broadcast_enabled

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to enable broadcast mode: {e}")
            return False

    def disable_broadcast(self) -> bool:
        """Disable broadcast mode (synchronize-panes) for all windows in the session."""
        try:
            if not self.session:
                self.logger.error("SSHplex: No session available for broadcast")
                return False

            broadcast_disabled = False
            for window_id, window in self.windows.items():
                if window:
                    window.cmd('set-window-option', 'synchronize-panes', 'off')
                    self.logger.info(f"SSHplex: Disabled broadcast for window {window_id}")
                    broadcast_disabled = True

            if broadcast_disabled:
                self.logger.info("SSHplex: Broadcast mode disabled for tmux session")
            return broadcast_disabled

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to disable broadcast mode: {e}")
            return False

    def toggle_broadcast(self) -> bool:
        """Toggle broadcast mode for all windows in the session."""
        try:
            if not self.session:
                self.logger.error("SSHplex: No session available for broadcast")
                return False

            # Check current broadcast state of first window with multiple panes
            current_state = False
            for window in self.windows.values():
                if window and len(window.panes) > 1:
                    # Get current synchronize-panes setting
                    result = window.cmd('show-window-options', '-v', 'synchronize-panes')
                    if result and hasattr(result, 'stdout') and result.stdout:
                        current_state = result.stdout[0].strip() == 'on'
                    break

            # Toggle the state
            if current_state:
                return self.disable_broadcast()
            else:
                return self.enable_broadcast()

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to toggle broadcast mode: {e}")
            return False
