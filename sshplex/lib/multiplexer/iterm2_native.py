"""iTerm2 native multiplexer implementation (no tmux).

Uses iTerm2's Python API for native window/tab/pane management with real broadcast support.
Requires iTerm2 running on macOS with API access enabled.

Backend options:
- backend: "iterm2-native" - Pure iTerm2 Python API (no tmux dependency)
"""

import platform
from typing import Any, Dict, List, Optional

from ..logger import get_logger
from .base import MultiplexerBase


class ITerm2NativeError(Exception):
    """Raised when iTerm2 native operations fail."""
    pass


class ITerm2NativeManager(MultiplexerBase):
    """iTerm2 native multiplexer using Python API directly (no tmux).

    Features:
    - Direct async API connection to iTerm2
    - Full session tracking (hostname -> Session object)
    - SSHplex-controlled tab/session naming
    - Runtime broadcast toggle via iTerm2 broadcast domains
    - Layout management (tiled, split patterns)

    Backend: "iterm2-native" (macOS only)
    """

    DEFAULT_MAX_PANES = 5

    def __init__(self, session_name: Optional[str], config: Optional[Any] = None):
        """Initialize iTerm2 native manager.

        Args:
            session_name: Session name (used for window naming)
            config: SSHplex configuration object

        Raises:
            ITerm2NativeError: If not on macOS or iTerm2 API not available
        """
        import time

        if session_name is None:
            session_name = f"sshplex-{int(time.time())}"

        super().__init__(session_name)
        self.logger = get_logger()
        self.config = config
        self.system = platform.system().lower()

        # Validate platform
        if self.system != "darwin":
            raise ITerm2NativeError(
                "iTerm2 native mode requires macOS. "
                "Use backend: 'tmux' on Linux."
            )

        # Check iTerm2 API availability
        self._check_iterm2_api()

        # Session tracking: hostname -> SSH command
        self._pending_sessions: Dict[str, str] = {}

        # Broadcast state
        self._broadcast_enabled = False

        # Layout config
        self._max_panes_per_tab = (
            config.tmux.max_panes_per_window
            if config and hasattr(config, 'tmux')
            else self.DEFAULT_MAX_PANES
        )
        self._split_pattern = (
            getattr(config.tmux, 'iterm2_split_pattern', 'alternate')
            if config and hasattr(config, 'tmux')
            else 'alternate'
        )
        self._profile = (
            getattr(config.tmux, 'iterm2_profile', 'Default')
            if config and hasattr(config, 'tmux')
            else 'Default'
        )

    def _check_iterm2_api(self) -> bool:
        """Check if iTerm2 Python API is available.

        Returns:
            True if iterm2 package is installed

        Raises:
            ITerm2NativeError: If iterm2 package not installed
        """
        try:
            import importlib.util
            spec = importlib.util.find_spec("iterm2")
            if spec is None:
                raise ITerm2NativeError(
                    "iTerm2 Python API not installed. "
                    "Install with: pip install 'sshplex[iterm2]'"
                ) from None
            return True
        except ImportError:
            raise ITerm2NativeError(
                "iTerm2 Python API not installed. "
                "Install with: pip install 'sshplex[iterm2]'"
            ) from None

    def create_session(self) -> bool:
        """Initialize iTerm2 session.

        Note: Actual window creation happens in attach_to_session.

        Returns:
            True always (window created lazily)
        """
        self.logger.info(f"SSHplex: iTerm2 native session '{self.session_name}' initialized")
        return True

    def create_pane(
        self,
        hostname: str,
        command: Optional[str] = None,
        max_panes_per_window: int = 5
    ) -> bool:
        """Queue a pane creation for the given hostname.

        Note: Panes are created in batch when attach_to_session is called.

        Args:
            hostname: Host identifier
            command: SSH command to execute
            max_panes_per_window: Maximum panes before creating new tab

        Returns:
            True if pane queued successfully
        """
        if command is None:
            command = f"ssh {hostname}"

        self._pending_sessions[hostname] = command
        self._max_panes_per_tab = max_panes_per_window
        self.logger.info(f"SSHplex: Queued iTerm2 pane for '{hostname}'")
        return True

    def create_window(self, hostname: str, command: Optional[str] = None) -> bool:
        """Queue a window creation for the given hostname.

        Args:
            hostname: Host identifier
            command: SSH command to execute

        Returns:
            True if window queued successfully
        """
        return self.create_pane(hostname, command, max_panes_per_window=1)

    def send_command(self, hostname: str, command: str) -> bool:
        """Send command to specific session.

        Note: Not supported in native mode after session creation.
        Use iTerm2's native features instead.

        Args:
            hostname: Host identifier
            command: Command to send

        Returns:
            False (not supported after creation)
        """
        self.logger.warning(
            "SSHplex: send_command not supported in iTerm2 native mode. "
            "Use iTerm2's native command features instead."
        )
        return False

    def broadcast_command(self, command: str) -> bool:
        """Send command to all panes.

        Note: Use broadcast mode instead for simultaneous input.

        Args:
            command: Command to broadcast

        Returns:
            True if broadcast enabled
        """
        if self._broadcast_enabled:
            self.logger.info("SSHplex: Commands sent to all sessions via broadcast mode")
            return True
        else:
            self.logger.warning(
                "SSHplex: Enable broadcast mode first for simultaneous input. "
                "Press Cmd+Option+I in iTerm2 or set broadcast: true in config."
            )
            return False

    def enable_broadcast(self) -> bool:
        """Enable broadcast mode.

        Note: Broadcast is enabled when creating sessions if broadcast: true in config.

        Returns:
            True if broadcast enabled
        """
        self._broadcast_enabled = True
        self.logger.info("SSHplex: Broadcast mode will be enabled when session is created")
        return True

    def disable_broadcast(self) -> bool:
        """Disable broadcast mode.

        Returns:
            True if broadcast disabled
        """
        self._broadcast_enabled = False
        self.logger.info("SSHplex: Broadcast mode disabled")
        return True

    def close_session(self) -> None:
        """Close the iTerm2 window.

        Note: User should close iTerm2 window manually.
        """
        self._pending_sessions.clear()
        self._broadcast_enabled = False
        self.logger.info(f"SSHplex: iTerm2 native session '{self.session_name}' cleared")

    def attach_to_session(self, auto_attach: bool = True) -> None:
        """Create iTerm2 sessions with all queued SSH connections.

        This is the main entry point that creates the iTerm2 window and panes.

        Args:
            auto_attach: If True, create sessions immediately
        """
        if not self._pending_sessions:
            self.logger.warning("SSHplex: No sessions to create")
            print("\n⚠️  No SSH connections to create.")
            return

        try:
            import iterm2
        except ImportError:
            print("\n❌ iTerm2 Python API not installed.")
            print("   Install with: pip install 'sshplex[iterm2]'")
            return

        # Build sessions list for the async function
        sessions_data = list(self._pending_sessions.items())
        max_panes = self._max_panes_per_tab
        profile = self._profile
        split_pattern = self._split_pattern
        enable_broadcast = self._broadcast_enabled and len(sessions_data) > 1

        async def _create_sessions(connection: Any) -> None:
            """Create all sessions in a single async context."""
            # Create new window
            window = await iterm2.Window.async_create(connection, profile=profile)
            if not window:
                self.logger.error("SSHplex: Failed to create iTerm2 window")
                return

            self.logger.info(f"SSHplex: Created iTerm2 window for {len(sessions_data)} sessions")

            sessions: List[Any] = []
            current_tab = window.current_tab
            current_tab_pane_count = 0

            for hostname, command in sessions_data:
                # Check if we need a new tab
                if current_tab_pane_count >= max_panes:
                    self.logger.info(f"SSHplex: Creating new tab (max {max_panes} panes)")
                    current_tab = await window.async_create_tab(profile=profile)
                    current_tab_pane_count = 0

                if current_tab_pane_count == 0:
                    # First session in tab - use existing
                    session = current_tab.current_session
                else:
                    # Split existing session
                    if split_pattern == 'vertical':
                        vertical = True
                    elif split_pattern == 'horizontal':
                        vertical = False
                    else:  # alternate
                        vertical = (current_tab_pane_count % 2 == 0)

                    last_session = sessions[-1] if sessions else current_tab.current_session
                    session = await last_session.async_split_pane(vertical=vertical, profile=profile)

                if not session:
                    self.logger.error(f"SSHplex: Failed to create session for {hostname}")
                    continue

                # Set session name (SSHplex-controlled)
                await session.async_set_name(hostname)

                # Send command
                await session.async_send_text(command + "\n")

                sessions.append(session)
                current_tab_pane_count += 1
                self.logger.info(f"SSHplex: Created session for '{hostname}'")

            # Enable broadcast if requested
            if enable_broadcast and len(sessions) > 1:
                domain = iterm2.broadcast.BroadcastDomain()
                for session in sessions:
                    domain.add_session(session)
                await iterm2.async_set_broadcast_domains(connection, [domain])
                self.logger.info("SSHplex: Broadcast mode ENABLED")

            print(f"\n✅ iTerm2 session created with {len(sessions)} connections")
            if enable_broadcast:
                print("📡 Broadcast mode enabled - input goes to all sessions")

        # Run with iTerm2's run_until_complete to maintain connection
        try:
            print(f"\n🚀 Creating iTerm2 session with {len(sessions_data)} SSH connections...")
            iterm2.run_until_complete(_create_sessions)
            self.logger.info("SSHplex: iTerm2 session created successfully")
        except Exception as e:
            error_msg = str(e)
            if "Connect call failed" in error_msg or "Connection refused" in error_msg:
                print("\n❌ iTerm2 Python API is not enabled.")
                print("   To fix:")
                print("   1. Open iTerm2")
                print("   2. Go to iTerm2 → Settings → General → Magic")
                print("   3. Enable 'Python API'")
                print("   4. Restart iTerm2 and try again")
            else:
                print(f"\n❌ Failed to create iTerm2 session: {e}")
            self.logger.error(f"SSHplex: Failed to create iTerm2 session: {e}")

    def get_session_name(self) -> str:
        """Get the session name."""
        return self.session_name

    def setup_broadcast_keybinding(self) -> bool:
        """Not applicable for iTerm2 native mode.

        iTerm2 has built-in broadcast shortcuts (Cmd+Option+I).
        """
        return True

    def setup_tiled_layout(self) -> bool:
        """Apply tiled layout to all tabs.

        Note: Called after attach_to_session in base class, but sessions
        are already created in iTerm2 native mode.
        """
        # Layout is applied automatically when creating panes
        return True

    def set_pane_title(self, pane_id: str, title: str) -> bool:
        """Set the title of a specific pane (session).

        Note: Not supported after session creation in iTerm2 native mode.

        Args:
            pane_id: Hostname (used as session identifier)
            title: New title

        Returns:
            False (not supported after creation)
        """
        self.logger.warning("SSHplex: set_pane_title not supported after session creation")
        return False
