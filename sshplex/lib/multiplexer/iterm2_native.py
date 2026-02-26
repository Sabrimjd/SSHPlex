"""iTerm2 native multiplexer implementation (no tmux).

Uses iTerm2's Python API for native window/tab/pane management with real broadcast support.
Requires iTerm2 running on macOS with API access enabled.

Backend options:
- backend: "iterm2-native" - Pure iTerm2 Python API (no tmux dependency)
"""

import asyncio
import platform
from typing import Any, Dict, Optional

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

        # iTerm2 connection (established lazily)
        self._connection: Optional[Any] = None  # iterm2.Connection
        self._app: Optional[Any] = None  # iterm2.App

        # Window/Tab tracking
        self._window: Optional[Any] = None  # iterm2.Window
        self._current_tab: Optional[Any] = None  # iterm2.Tab
        self._current_tab_pane_count = 0

        # Session tracking: hostname -> iterm2.Session
        self._iterm2_sessions: Dict[str, Any] = {}

        # Broadcast state
        self._broadcast_domain: Optional[Any] = None  # iterm2.broadcast.BroadcastDomain
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

    async def _connect(self) -> Any:
        """Establish connection to iTerm2.

        Returns:
            iterm2.Connection object

        Raises:
            ITerm2NativeError: If connection fails
        """
        if self._connection is None:
            try:
                import iterm2
                self._connection = await iterm2.Connection().async_create()
                self._app = await iterm2.async_get_app(self._connection)
                self.logger.info("SSHplex: Connected to iTerm2")
            except Exception as e:
                error_msg = str(e)
                if "Connect call failed" in error_msg or "Connection refused" in error_msg:
                    raise ITerm2NativeError(
                        "iTerm2 Python API is not enabled. "
                        "To fix:\n"
                        "  1. Open iTerm2\n"
                        "  2. Go to iTerm2 → Settings → General → Magic\n"
                        "  3. Enable 'Python API'\n"
                        "  4. Restart iTerm2 and try again"
                    ) from e
                raise ITerm2NativeError(f"Failed to connect to iTerm2: {e}") from e
        return self._connection

    async def _disconnect(self) -> None:
        """Close iTerm2 connection."""
        from contextlib import suppress

        if self._connection:
            with suppress(Exception):
                await self._connection.async_close()
            self._connection = None
            self._app = None

    def create_session(self) -> bool:
        """Initialize iTerm2 connection and create window.

        Returns:
            True if session created successfully
        """
        async def _create():
            import iterm2

            conn = await self._connect()
            self._window = await iterm2.Window.async_create(
                conn,
                profile=self._profile
            )

            if self._window:
                # Set window title (SSHplex-controlled)
                # Note: Window title is set via the first session's name
                self._current_tab = self._window.current_tab
                self._current_tab_pane_count = 0
                self.logger.info(
                    f"SSHplex: iTerm2 native session '{self.session_name}' created"
                )
                return True
            return False

        try:
            return asyncio.run(_create())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create iTerm2 session: {e}")
            return False

    def create_pane(
        self,
        hostname: str,
        command: Optional[str] = None,
        max_panes_per_window: int = 5
    ) -> bool:
        """Create a new pane for hostname.

        Args:
            hostname: Host identifier
            command: SSH command to execute
            max_panes_per_window: Maximum panes before creating new tab

        Returns:
            True if pane created successfully
        """
        async def _create():
            import iterm2

            # Ensure window exists
            if not self._window:
                await self._connect()
                self._window = await iterm2.Window.async_create(
                    self._connection,
                    profile=self._profile
                )
                self._current_tab = self._window.current_tab
                self._current_tab_pane_count = 0

            # Check if we need a new tab
            if self._current_tab_pane_count >= max_panes_per_window:
                self.logger.info(
                    f"SSHplex: Max panes ({max_panes_per_window}) reached, creating new tab"
                )
                self._current_tab = await self._window.async_create_tab(
                    profile=self._profile
                )
                self._current_tab_pane_count = 0

            session = None

            if self._current_tab_pane_count == 0:
                # First session in tab - use existing
                session = self._current_tab.current_session
            else:
                # Split existing session
                # Determine split direction based on pattern
                if self._split_pattern == 'vertical':
                    vertical = True
                elif self._split_pattern == 'horizontal':
                    vertical = False
                else:  # alternate
                    vertical = (self._current_tab_pane_count % 2 == 0)

                # Get last session to split
                sessions = self._current_tab.sessions
                if sessions:
                    last_session = sessions[-1]
                    session = await last_session.async_split_pane(
                        vertical=vertical,
                        profile=self._profile
                    )

            if not session:
                self.logger.error(f"SSHplex: Failed to create pane for {hostname}")
                return False

            # Set session name (SSHplex-controlled)
            await session.async_set_name(hostname)

            # Send command
            if command:
                await session.async_send_text(command + "\n")

            # Track session
            self._iterm2_sessions[hostname] = session
            self._current_tab_pane_count += 1

            self.logger.info(
                f"SSHplex: Created pane for '{hostname}' "
                f"({self._current_tab_pane_count}/{max_panes_per_window} in tab)"
            )
            return True

        try:
            return asyncio.run(_create())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create pane for '{hostname}': {e}")
            return False

    def create_window(self, hostname: str, command: Optional[str] = None) -> bool:
        """Create a new tab for hostname (not a split pane).

        Args:
            hostname: Host identifier
            command: SSH command to execute

        Returns:
            True if tab created successfully
        """
        async def _create():
            import iterm2

            # Ensure window exists
            if not self._window:
                await self._connect()
                self._window = await iterm2.Window.async_create(
                    self._connection,
                    profile=self._profile
                )

            # Create new tab
            tab = await self._window.async_create_tab(profile=self._profile)
            if not tab:
                self.logger.error(f"SSHplex: Failed to create tab for {hostname}")
                return False

            session = tab.current_session

            # Set names (SSHplex-controlled)
            await tab.async_set_title(hostname)
            await session.async_set_name(hostname)

            # Send command
            if command:
                await session.async_send_text(command + "\n")

            # Track session
            self._iterm2_sessions[hostname] = session

            self.logger.info(f"SSHplex: Created tab for '{hostname}'")
            return True

        try:
            return asyncio.run(_create())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to create tab for '{hostname}': {e}")
            return False

    def send_command(self, hostname: str, command: str) -> bool:
        """Send command to specific session.

        Args:
            hostname: Host identifier
            command: Command to send

        Returns:
            True if command sent successfully
        """
        async def _send():
            session = self._iterm2_sessions.get(hostname)
            if not session:
                self.logger.error(f"SSHplex: Session for '{hostname}' not found")
                return False

            await session.async_send_text(command + "\n", suppress_broadcast=True)
            self.logger.debug(f"SSHplex: Sent command to '{hostname}': {command}")
            return True

        try:
            return asyncio.run(_send())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to send command to '{hostname}': {e}")
            return False

    def broadcast_command(self, command: str) -> bool:
        """Send command to all sessions (only works if broadcast enabled).

        Args:
            command: Command to broadcast

        Returns:
            True if command broadcast successfully
        """
        if not self._broadcast_enabled:
            self.logger.warning(
                "SSHplex: Broadcast not enabled. Call enable_broadcast() first."
            )
            return False

        async def _broadcast():
            # When broadcast is on, sending to any session goes to all
            first_session = next(iter(self._iterm2_sessions.values()), None)
            if not first_session:
                return False

            await first_session.async_send_text(command + "\n")
            self.logger.info(f"SSHplex: Broadcast command: {command}")
            return True

        try:
            return asyncio.run(_broadcast())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to broadcast command: {e}")
            return False

    def enable_broadcast(self) -> bool:
        """Enable broadcast mode across all sessions.

        Returns:
            True if broadcast enabled successfully
        """
        async def _enable():
            import iterm2

            if not self._iterm2_sessions:
                self.logger.warning("SSHplex: No sessions to enable broadcast")
                return False

            self._broadcast_domain = iterm2.broadcast.BroadcastDomain()
            for session in self._iterm2_sessions.values():
                self._broadcast_domain.add_session(session)

            await iterm2.async_set_broadcast_domains(
                self._connection,
                [self._broadcast_domain]
            )
            self._broadcast_enabled = True
            self.logger.info("SSHplex: Broadcast mode ENABLED")
            return True

        try:
            return asyncio.run(_enable())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to enable broadcast: {e}")
            return False

    def disable_broadcast(self) -> bool:
        """Disable broadcast mode.

        Returns:
            True if broadcast disabled successfully
        """
        async def _disable():
            import iterm2

            await iterm2.async_set_broadcast_domains(self._connection, [])
            self._broadcast_domain = None
            self._broadcast_enabled = False
            self.logger.info("SSHplex: Broadcast mode DISABLED")
            return True

        try:
            return asyncio.run(_disable())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to disable broadcast: {e}")
            return False

    def toggle_broadcast(self) -> bool:
        """Toggle broadcast mode.

        Returns:
            True if toggle successful
        """
        if self._broadcast_enabled:
            return self.disable_broadcast()
        return self.enable_broadcast()

    def setup_tiled_layout(self) -> bool:
        """Apply tiled layout to all tabs.

        Returns:
            True if layout applied successfully
        """
        async def _layout():
            import iterm2

            if not self._window:
                return False

            for tab in self._window.tabs:
                sessions = tab.sessions
                if len(sessions) > 1:
                    # Equal sizes
                    for session in sessions:
                        session.preferred_size = iterm2.util.Size(80, 24)
                    await tab.async_update_layout()

            self.logger.info("SSHplex: Applied tiled layout")
            return True

        try:
            return asyncio.run(_layout())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to apply layout: {e}")
            return False

    def set_pane_title(self, pane_id: str, title: str) -> bool:
        """Set the title of a specific pane (session).

        Args:
            pane_id: Hostname (used as session identifier)
            title: New title

        Returns:
            True if title set successfully
        """
        async def _set_title():
            session = self._iterm2_sessions.get(pane_id)
            if not session:
                return False

            await session.async_set_name(title)
            return True

        try:
            return asyncio.run(_set_title())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to set pane title: {e}")
            return False

    def attach_to_session(self, auto_attach: bool = True) -> None:
        """Prepare session for interactive use.

        Args:
            auto_attach: If True, bring window to front
        """
        if not auto_attach:
            print(
                f"\n✅ iTerm2 session '{self.session_name}' created "
                f"with {len(self._iterm2_sessions)} connections"
            )
            print("💡 Use iTerm2's native features to interact")
            return

        async def _attach():
            if self._window:
                await self._window.async_activate()
                print(
                    f"\n✅ iTerm2 window activated "
                    f"with {len(self._iterm2_sessions)} sessions"
                )

        try:
            asyncio.run(_attach())
        except Exception as e:
            self.logger.error(f"SSHplex: Failed to attach: {e}")

    def close_session(self) -> None:
        """Close the iTerm2 window and disconnect."""
        from contextlib import suppress

        async def _close():
            if self._window:
                with suppress(Exception):
                    await self._window.async_close(force=True)

            await self._disconnect()

        try:
            asyncio.run(_close())
        except Exception as e:
            self.logger.error(f"SSHplex: Error closing session: {e}")
        finally:
            self._iterm2_sessions.clear()
            self._broadcast_domain = None
            self._broadcast_enabled = False
            self._window = None
            self._current_tab = None
            self._current_tab_pane_count = 0
            self.logger.info(f"SSHplex: iTerm2 native session '{self.session_name}' closed")

    def get_session_name(self) -> str:
        """Get the session name."""
        return self.session_name

    def setup_broadcast_keybinding(self) -> bool:
        """Not applicable for iTerm2 native mode.

        iTerm2 has built-in broadcast shortcuts (Cmd+Option+I).
        """
        return True
