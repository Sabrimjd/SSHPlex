"""SSHplex tmux multiplexer implementation."""

import libtmux
from typing import Optional, Dict
from datetime import datetime

from .base import MultiplexerBase
from ..logger import get_logger


class TmuxManager(MultiplexerBase):
    """tmux implementation for SSHplex multiplexer."""

    def __init__(self, session_name: Optional[str] = None):
        """Initialize tmux manager with session name."""
        if session_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"

        super().__init__(session_name)
        self.logger = get_logger()
        self.server = libtmux.Server()
        self.session: Optional[libtmux.Session] = None
        self.window: Optional[libtmux.Window] = None
        self.panes: Dict[str, libtmux.Pane] = {}

    def create_session(self) -> bool:
        """Create a new tmux session with SSHplex branding."""
        try:
            self.logger.info(f"SSHplex: Creating tmux session '{self.session_name}'")

            # Check if session already exists
            if self.server.has_session(self.session_name):
                self.logger.warning(f"SSHplex: Session '{self.session_name}' already exists")
                self.session = self.server.get_session(self.session_name)
            else:
                # Create new session
                self.session = self.server.new_session(
                    session_name=self.session_name,
                    window_name="sshplex",
                    start_directory="~"
                )

            # Get the main window
            if self.session:
                self.window = self.session.attached_window
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
            if self.session is None or self.window is None:
                if not self.create_session():
                    return False

            self.logger.info(f"SSHplex: Creating pane for host '{hostname}'")

            # Split window to create new pane (except for the first pane)
            if self.window is None:
                self.logger.error("SSHplex: No window available for pane creation")
                return False

            if len(self.panes) == 0:
                # First pane - use the existing window pane
                pane = self.window.attached_pane
            else:
                # Additional panes - split the window
                pane = self.window.split_window()

            # Store pane reference
            self.panes[hostname] = pane

            # Set pane title
            self.set_pane_title(hostname, hostname)

            # Execute the provided command (should be SSH command)
            if command:
                self.send_command(hostname, command)

            self.logger.info(f"SSHplex: Pane created for '{hostname}' successfully")
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
                self.window = None
                self.panes.clear()

        except Exception as e:
            self.logger.error(f"SSHplex: Error closing session: {e}")

    def attach_to_session(self, auto_attach: bool = True) -> None:
        """Attach to the tmux session."""
        try:
            if self.session:
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

    def get_session_name(self) -> str:
        """Get the tmux session name for external attachment."""
        return self.session_name

    def setup_tiled_layout(self) -> bool:
        """Set up tiled layout for multiple panes."""
        try:
            if self.window and len(self.panes) > 1:
                self.window.select_layout('tiled')
                self.logger.info("SSHplex: Applied tiled layout to tmux window")
                return True
            return False

        except Exception as e:
            self.logger.error(f"SSHplex: Failed to set tiled layout: {e}")
            return False
