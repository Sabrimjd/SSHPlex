"""SSHplex tmux multiplexer implementation."""

import libtmux
from typing import Any, Optional, Dict
from datetime import datetime
import uuid

from .base import MultiplexerBase
from ..logger import get_logger

import platform
import subprocess


class TmuxError(Exception):
    """Raised when tmux operations fail."""
    pass


class TmuxManager(MultiplexerBase):
    """tmux implementation for SSHplex multiplexer."""

    # Default max panes per window
    DEFAULT_MAX_PANES = 5
    
    def __init__(self, session_name: Optional[str], config: Optional[Any] = None):
        """Initialize tmux manager with session name and max panes per window."""
        if session_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"

        super().__init__(session_name)
        self.logger = get_logger()
        self.server: Optional[libtmux.Server] = None
        self.session: Optional[libtmux.Session] = None
        self.current_window: Optional[libtmux.Window] = None
        self.windows: Dict[int, libtmux.Window] = {}  # window_id -> Window
        self.panes: Dict[str, libtmux.Pane] = {}
        self.config = config
        self.current_window_pane_count = 0
        self.system = platform.system().lower()
        self._initialized = False

    def _generate_unique_session_name(self, base_name: str) -> str:
        """Generate a unique session name to avoid collisions.
        
        Args:
            base_name: Base session name
            
        Returns:
            Unique session name with optional suffix
        """
        if not self.server:
            return base_name
            
        # Check if base name is available
        if not self.server.has_session(base_name):
            return base_name
        
        # Name exists, try with incremental suffix
        for i in range(1, 100):
            new_name = f"{base_name}-{i}"
            if not self.server.has_session(new_name):
                self.logger.info(f"Session '{base_name}' exists, using '{new_name}'")
                return new_name
        
        # Fallback to UUID-based name
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{base_name}-{unique_suffix}"

    def _init_server(self) -> bool:
        """Initialize tmux server connection.
        
        Returns:
            True if server initialized successfully
        """
        if self.server is not None:
            return True
            
        try:
            self.server = libtmux.Server()
            return True
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to initialize tmux server: {e}")
            return False

    def create_session(self) -> bool:
        """Create a new tmux session with SSHplex branding."""
        try:
            # Initialize server if needed
            if not self._init_server():
                return False

            self.logger.info(f"SSHplex: Creating tmux session '{self.session_name}'")

            # Generate unique session name if needed
            self.session_name = self._generate_unique_session_name(self.session_name)

            # Check if session already exists (should not happen after unique name generation)
            if self.server.has_session(self.session_name):
                self.logger.warning(f"SSHplex: Session '{self.session_name}' already exists, attaching")
                try:
                    self.session = self.server.sessions.get(session_name=self.session_name)
                except Exception:
                    # If get fails, try to find it
                    for sess in self.server.sessions:
                        if sess.session_name == self.session_name:
                            self.session = sess
                            break
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
                self._initialized = True
                self.logger.info(f"SSHplex: tmux session '{self.session_name}' created successfully")
                return True
            else:
                self.logger.error("SSHplex: Failed to get session after creation")
                return False

        except libtmux.common.LibTmuxException as e:
            self.logger.error(f"SSHplex: tmux error creating session: {e}")
            return False
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create tmux session: {e}")
            return False

    def create_pane(self, hostname: str, command: Optional[str] = None, max_panes_per_window: int = 5) -> bool:
        """Create a new pane for the given hostname, maximizing the number of panes per window."""
        try:
            # Ensure session and current window exist
            if self.session is None or self.current_window is None:
                if not self.create_session():
                    return False

            self.logger.info(f"SSHplex: Creating pane for host '{hostname}'")

            # Helper: create new window if needed
            def ensure_window_available():
                if self.current_window_pane_count >= max_panes_per_window:
                    self.logger.info(f"SSHplex: Reached max panes per window ({max_panes_per_window}), creating new window")
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

            ensure_window_available()

            if self.current_window is None:
                self.logger.error("SSHplex: No window available for pane creation")
                return False

            # Create pane
            if self.current_window_pane_count == 0:
                # First pane in this window: use attached pane
                pane = self.current_window.attached_pane
                if pane is None:
                    raise RuntimeError(f"No attached pane available for {hostname}")
            else:
                # Additional panes - attempt split with fallback
                vertical_split = (self.current_window_pane_count % 2 == 0)
                try:
                    pane = self.current_window.split_window(vertical=vertical_split)
                except Exception as e:
                    # Handle "no space" error by resizing or creating a new window
                    self.logger.warning(f"Pane split failed ({e}), attempting layout adjustment")
                    try:
                        # Resize window to fit more panes
                        self.current_window.resize_window(height=80, width=200)
                        pane = self.current_window.split_window(vertical=vertical_split)
                    except Exception:
                        # If still fails, create a new window
                        self.logger.info("Creating new window due to insufficient space")
                        ensure_window_available()
                        vertical_split = True  # first split in new window
                        pane = self.current_window.split_window(vertical=vertical_split)

                if pane is None:
                    raise RuntimeError(f"Failed to create tmux pane for {hostname}")

            # Balance layout for best use of space
            self.current_window.select_layout("tiled")

            # Store pane reference and increment counter
            self.panes[hostname] = pane
            self.current_window_pane_count += 1

            # Set pane title
            self.set_pane_title(hostname, hostname)

            # Execute command if provided
            if command:
                self.send_command(hostname, command)

            self.logger.info(f"SSHplex: Pane created for '{hostname}' successfully "
                            f"(window panes: {self.current_window_pane_count}/{max_panes_per_window})")
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

                    try:
                        if "darwin" in self.system and self.config and self.config.tmux.control_with_iterm2:
                            # macOS with iTerm2 integration
                            print("\n🖥️  Using iTerm2 tmux integration (-CC mode)...")
                            self._attach_iterm2()
                        else:
                            # Standard tmux attach
                            self._attach_standard()

                    except RuntimeError as e:
                        self.logger.error(f"SSHplex: Failed to launch tmux session: {e}")
                        print(f"\n⚠️  Failed to auto-attach: {e}")
                        print(f"\n💡 To attach manually, run: tmux attach-session -t {self.session_name}")
                    except Exception as e:
                        self.logger.error(f"SSHplex: Failed to launch tmux session: {e}")
                        print(f"\n⚠️  Failed to auto-attach: {e}")
                        print(f"\n💡 To attach manually, run: tmux attach-session -t {self.session_name}")
                else:
                    self.logger.info(f"SSHplex: Tmux session '{self.session_name}' is ready for attachment")
                    print(f"\n💡 To attach to the session, run: tmux attach-session -t {self.session_name}")
            else:
                self.logger.error("SSHplex: No session to attach to")

        except Exception as e:
            self.logger.error(f"SSHplex: Error attaching to session: {e}")

    def _attach_standard(self) -> None:
        """Standard tmux attach using os.execlp."""
        import os
        # Use exec to replace the current Python process with tmux attach
        os.execlp("tmux", "tmux", "attach-session", "-t", self.session_name)

    def _attach_iterm2(self) -> None:
        """Attach using iTerm2 tmux integration (macOS only)."""
        try:
            # Check if iTerm2 is installed
            check_installed = subprocess.run(
                ["osascript", "-e", 'exists application "iTerm2"'],
                capture_output=True,
                text=True
            )

            if check_installed.returncode != 0 or "false" in check_installed.stdout.lower():
                raise RuntimeError("iTerm2 is not installed on this system")

            # Check if iTerm2 is running
            check_running = subprocess.run(
                ["osascript", "-e", 'application "iTerm2" is running'],
                capture_output=True,
                text=True
            )

            iterm_running = check_running.returncode == 0 and "true" in check_running.stdout.lower()

            if iterm_running:
                # iTerm2 is running - create new window with tmux session
                apple_script = f'''
                tell application "iTerm2"
                    create window with default profile
                    tell current session of current window
                        set name to "{self.session_name}"
                        write text "tmux -CC attach-session -t {self.session_name}; exit"
                    end tell
                end tell
                '''
            else:
                # iTerm2 not running - launch it first
                apple_script = f'''
                tell application "iTerm2"
                    activate
                    delay 1
                    tell current session of current window
                        set name to "{self.session_name}"
                        write text "tmux -CC attach-session -t {self.session_name}; exit"
                    end tell
                end tell
                '''

            # Launch osascript in the background
            process = subprocess.Popen(
                ["osascript", "-e", apple_script],
                start_new_session=True  # ensures no signal ties to main TUI
            )

            # Check if osascript launched successfully
            if process.poll() is not None and process.returncode != 0:
                raise RuntimeError("Failed to launch iTerm2 via AppleScript")

            self.logger.info(f"SSHplex: Launched iTerm2 with tmux session '{self.session_name}'")
            print(f"🚀 iTerm2 launched with tmux session: {self.session_name}")

        except FileNotFoundError:
            raise RuntimeError("osascript not found - iTerm2 integration only works on macOS")
        except Exception as e:
            # Re-raise with more context
            raise RuntimeError(f"Failed to launch iTerm2: {e}")

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
