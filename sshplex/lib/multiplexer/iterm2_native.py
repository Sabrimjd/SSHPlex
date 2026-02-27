"""iTerm2 native multiplexer implementation (no tmux).

Uses iTerm2's Python API for native window/tab/pane management with real broadcast support.
Requires iTerm2 running on macOS with API access enabled.

Backend options:
- backend: "iterm2-native" - Pure iTerm2 Python API (no tmux dependency)
"""

import platform
import re
from typing import Any, List, Optional, Tuple

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
        self._pending_sessions: List[Tuple[str, str]] = []

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
        self._native_target = (
            getattr(config.tmux, 'iterm2_native_target', 'current-window')
            if config and hasattr(config, 'tmux')
            else 'current-window'
        )
        self._hide_from_history = (
            bool(getattr(config.tmux, 'iterm2_native_hide_from_history', True))
            if config and hasattr(config, 'tmux')
            else True
        )

    @staticmethod
    def _sanitize_command(command: str) -> str:
        """Redact sensitive SSH command values in logs."""
        redacted = re.sub(r"(\s-i\s+)\S+", r"\1<redacted-key>", command)
        redacted = re.sub(r"(IdentityFile=)\S+", r"\1<redacted-key>", redacted)
        return redacted

    @staticmethod
    def _extract_tab_session(tab: Any) -> Optional[Any]:
        """Get a usable session from an iTerm2 tab."""
        if tab is None:
            return None

        current = getattr(tab, "current_session", None)
        if current is not None:
            return current

        sessions = getattr(tab, "sessions", None)
        if sessions:
            return sessions[0]

        return None

    def _command_for_send(self, command: str) -> str:
        """Prepare command text for iTerm2 async_send_text."""
        text = command
        if self._hide_from_history and text and not text.startswith(" "):
            text = " " + text
        return text + "\n"

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

        self._pending_sessions.append((hostname, command))
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
        sessions_data = list(self._pending_sessions)
        max_panes = self._max_panes_per_tab
        profile = self._profile
        split_pattern = self._split_pattern
        enable_broadcast = self._broadcast_enabled and len(sessions_data) > 1

        self.logger.debug(
            "SSHplex: iTerm2 native attach start "
            f"(session={self.session_name}, profile={profile}, split_pattern={split_pattern}, "
            f"max_panes_per_tab={max_panes}, queued_sessions={len(sessions_data)}, "
            f"broadcast={enable_broadcast}, auto_attach={auto_attach}, target={self._native_target})"
        )

        async def _create_sessions(connection: Any) -> None:
            """Create all sessions in a single async context."""
            sessions: List[Any] = []

            # Ensure iTerm2 app delegates are initialized.
            app = await iterm2.async_get_app(connection)
            if app is None:
                raise ITerm2NativeError("Failed to initialize iTerm2 app delegate")
            self.logger.debug("SSHplex: iTerm2 app delegate initialized")

            async def _create_tab_with_session(window_obj: Any, profile_name: str) -> Any:
                """Create a tab and return (tab, session), with shell fallback."""
                tab = await window_obj.async_create_tab(profile=profile_name)
                session = self._extract_tab_session(tab)

                if session is None:
                    self.logger.warning(
                        "SSHplex: Tab created without session, retrying with explicit /bin/zsh shell"
                    )
                    tab = await window_obj.async_create_tab(profile=profile_name, command="/bin/zsh")
                    session = self._extract_tab_session(tab)

                return tab, session

            async def _set_labels(tab_obj: Any, session_obj: Any, hostname: str) -> None:
                """Set visible names for session and tab."""
                await session_obj.async_set_name(hostname)
                try:
                    await tab_obj.async_set_title(hostname)
                except Exception as title_error:
                    self.logger.debug(
                        f"SSHplex: Could not set tab title for '{hostname}': {title_error}"
                    )
                try:
                    await tab_obj.async_set_variable("user.sshplex_managed", True)
                    await tab_obj.async_set_variable("user.sshplex_session_name", self.session_name)
                    await tab_obj.async_set_variable("user.sshplex_hostname", hostname)
                except Exception as var_error:
                    self.logger.debug(
                        f"SSHplex: Could not set tab metadata for '{hostname}': {var_error}"
                    )

            # Get first command to run in the initial window
            first_hostname, first_command = sessions_data[0] if sessions_data else (None, None)

            if not first_hostname:
                self.logger.error("SSHplex: No sessions to create")
                raise ITerm2NativeError("No sessions to create")
            first_command_text = first_command or f"ssh {first_hostname}"

            current_tab = None
            if self._native_target == "current-window":
                await app.async_refresh_focus()
                window = app.current_window
                if window is None:
                    self.logger.warning(
                        "SSHplex: No current iTerm2 window found, falling back to new window"
                    )
                    window = await iterm2.Window.async_create(connection, profile=profile)
                    if not window:
                        self.logger.error("SSHplex: Failed to create fallback iTerm2 window")
                        raise ITerm2NativeError("Failed to create fallback iTerm2 window")
                    self.logger.info(f"SSHplex: Created fallback iTerm2 window for {len(sessions_data)} sessions")
                else:
                    self.logger.info("SSHplex: Using current iTerm2 window as attach target")
                    current_tab, recovered_session = await _create_tab_with_session(window, profile)
                    if recovered_session is not None:
                        await _set_labels(current_tab, recovered_session, first_hostname)
                        await recovered_session.async_send_text(self._command_for_send(first_command_text))
                        sessions.append(recovered_session)
                        self.logger.info(f"SSHplex: Created session for '{first_hostname}'")
                        self.logger.debug(
                            "SSHplex: Dispatched first command to "
                            f"'{first_hostname}': {self._sanitize_command(first_command_text)}"
                        )
            else:
                # Create dedicated window for SSHplex native sessions.
                window = await iterm2.Window.async_create(connection, profile=profile)
                if not window:
                    self.logger.error("SSHplex: Failed to create iTerm2 window")
                    raise ITerm2NativeError("Failed to create iTerm2 window")
                self.logger.info(f"SSHplex: Created iTerm2 window for {len(sessions_data)} sessions")

            # Refresh app state so session/tab delegates can resolve split results.
            await app.async_refresh()

            if current_tab is None:
                current_tab = window.current_tab

                # If current_tab is None, try to get first tab from tabs list
                if current_tab is None and window.tabs:
                    current_tab = window.tabs[0]

                # If still None, create a new tab
                if current_tab is None:
                    current_tab, recovered_session = await _create_tab_with_session(window, profile)
                    if recovered_session is not None:
                        await _set_labels(current_tab, recovered_session, first_hostname)
                        await recovered_session.async_send_text(self._command_for_send(first_command_text))
                        sessions.append(recovered_session)
                        self.logger.info(f"SSHplex: Created session for '{first_hostname}'")
                        self.logger.debug(
                            "SSHplex: Dispatched first command to "
                            f"'{first_hostname}': {self._sanitize_command(first_command_text)}"
                        )

            if current_tab is None:
                self.logger.error("SSHplex: Failed to get or create a tab")
                raise ITerm2NativeError("Failed to get or create initial iTerm2 tab")

            # Get the session that was created with the first command
            first_session = self._extract_tab_session(current_tab)
            if not sessions:
                if first_session is None:
                    self.logger.warning(
                        "SSHplex: Initial tab has no session, creating recovery tab"
                    )
                    recovery_tab, recovery_session = await _create_tab_with_session(window, profile)
                    if recovery_tab is not None:
                        current_tab = recovery_tab
                    first_session = recovery_session

                if first_session is not None:
                    await _set_labels(current_tab, first_session, first_hostname)
                    await first_session.async_send_text(self._command_for_send(first_command_text))
                    sessions.append(first_session)
                    self.logger.info(f"SSHplex: Created session for '{first_hostname}'")
                    self.logger.debug(
                        "SSHplex: Dispatched first command to "
                        f"'{first_hostname}': {self._sanitize_command(first_command_text)}"
                    )
                else:
                    self.logger.error(
                        "SSHplex: First tab has no current session "
                        f"for '{first_hostname}'"
                    )
                    self.logger.debug(
                        "SSHplex: Initial tab diagnostics "
                        f"(tab={current_tab}, has_sessions={bool(getattr(current_tab, 'sessions', None))})"
                    )
                    raise ITerm2NativeError(
                        f"First tab has no usable session for '{first_hostname}'"
                    )

            current_tab_pane_count = 1  # We already have 1 session

            # Process remaining sessions (skip first one)
            for hostname, command in sessions_data[1:]:
                # Check if we need a new tab
                if current_tab_pane_count >= max_panes:
                    self.logger.info(f"SSHplex: Creating new tab (max {max_panes} panes)")
                    current_tab, new_session = await _create_tab_with_session(window, profile)
                    if current_tab and new_session:
                        await _set_labels(current_tab, new_session, hostname)
                        await new_session.async_send_text(self._command_for_send(command))
                        sessions.append(new_session)
                        current_tab_pane_count = 1
                        self.logger.info(f"SSHplex: Created session for '{hostname}' in new tab")
                        self.logger.debug(
                            "SSHplex: Dispatched command in new tab to "
                            f"'{hostname}': {self._sanitize_command(command)}"
                        )
                        continue
                    self.logger.error(f"SSHplex: Failed to create tab for {hostname}")
                    continue

                # Split existing session
                if split_pattern == 'vertical':
                    vertical = True
                elif split_pattern == 'horizontal':
                    vertical = False
                else:  # alternate
                    vertical = (current_tab_pane_count % 2 == 0)

                # Get last session to split
                if sessions:
                    last_session = sessions[-1]
                    session = await last_session.async_split_pane(vertical=vertical, profile=profile)
                else:
                    self.logger.error(f"SSHplex: No session available to split for {hostname}")
                    continue

                if not session:
                    self.logger.error(f"SSHplex: Failed to create session for {hostname}")
                    continue

                # Set session name (SSHplex-controlled)
                await _set_labels(current_tab, session, hostname)

                # Send command
                await session.async_send_text(self._command_for_send(command))
                self.logger.debug(
                    "SSHplex: Dispatched split-pane command to "
                    f"'{hostname}': {self._sanitize_command(command)}"
                )

                sessions.append(session)
                current_tab_pane_count += 1
                self.logger.info(f"SSHplex: Created session for '{hostname}'")

            # Enable broadcast if requested
            if enable_broadcast and len(sessions) > 1:
                # Refresh app and resolve sessions by ID before creating broadcast domains.
                # This is important for tab-heavy layouts where session objects can be stale.
                await app.async_refresh()

                domain = iterm2.broadcast.BroadcastDomain()
                resolved_sessions = 0
                for session in sessions:
                    sid = getattr(session, "session_id", None)
                    if sid:
                        resolved = app.get_session_by_id(sid)
                        if resolved is not None:
                            domain.add_session(resolved)
                            resolved_sessions += 1

                if resolved_sessions > 1:
                    await iterm2.async_set_broadcast_domains(connection, [domain])
                    self.logger.info(
                        "SSHplex: Broadcast mode ENABLED "
                        f"({resolved_sessions} sessions)"
                    )
                else:
                    self.logger.warning(
                        "SSHplex: Broadcast requested but insufficient resolved sessions "
                        f"({resolved_sessions}/{len(sessions)})"
                    )

            print(f"\n✅ iTerm2 session created with {len(sessions)} connections")
            if enable_broadcast:
                print("📡 Broadcast mode enabled - input goes to all sessions")

            if not sessions:
                raise ITerm2NativeError("No iTerm2 sessions were created")

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
            self.logger.exception("SSHplex: iTerm2 native traceback")

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
