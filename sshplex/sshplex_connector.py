"""SSHplex Connector - SSH connections and multiplexer session management."""

import os
import platform
import re
import shlex
import time
from datetime import datetime
from typing import Any, List, Optional

from .lib.logger import get_logger
from .lib.sot.base import Host


class SSHConnectionError(Exception):
    """Raised when SSH connection fails after all retries."""
    pass


class SSHplexConnector:
    """Manages SSH connections and multiplexer session management.

    Supports 3 backends:
    1. tmux standalone - Pure tmux (Linux, macOS)
    2. tmux + iTerm2 - tmux with iTerm2 -CC mode (macOS)
    3. iTerm2 native - Pure iTerm2 Python API (macOS)
    """

    def __init__(self, session_name: Optional[str], config: Optional[Any] = None):
        """Initialize the connector with optional session name and config.

        Args:
            session_name: Session name (auto-generated if None)
            config: SSHplex configuration object
        """
        if session_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"

        self.session_name = session_name
        self.config = config
        self.logger = get_logger()
        self.system = platform.system().lower()
        self.backend = getattr(config.tmux, 'backend', 'tmux') if config else 'tmux'
        self.last_success_count = 0
        self.last_failed_hosts: List[str] = []
        self.multiplexer: Any

        # Initialize multiplexer based on backend config
        if self.backend == "iterm2-native":
            from .lib.multiplexer.iterm2_native import ITerm2NativeManager
            self.multiplexer = ITerm2NativeManager(session_name, config)
            self.logger.info("SSHplex: Using iTerm2 native backend")
        else:
            from .lib.multiplexer.tmux import TmuxManager
            self.multiplexer = TmuxManager(session_name, config)
            if getattr(config.tmux, 'control_with_iterm2', False) if config else False:
                self.logger.info("SSHplex: Using tmux + iTerm2 -CC mode backend")
            else:
                self.logger.info("SSHplex: Using tmux standalone backend")

    @staticmethod
    def _sanitize_ssh_command(command: str) -> str:
        """Redact sensitive SSH command values in logs."""
        redacted = re.sub(r"(\s-i\s+)\S+", r"\1<redacted-key>", command)
        redacted = re.sub(r"(IdentityFile=)\S+", r"\1<redacted-key>", redacted)
        return redacted

    def connect_to_hosts(self, hosts: List[Host], username: str, key_path: Optional[str] = None, port: int = 22, use_panes: bool = True, use_broadcast: bool = False) -> bool:
        """Establish SSH connections to the specified hosts using shell SSH with retry support.

        Args:
            hosts: List of hosts to connect to
            username: SSH username
            key_path: Path to SSH private key (optional)
            port: SSH port (default: 22)
            use_panes: If True, create panes; if False, create windows/tabs
            use_broadcast: If True, enable synchronize-panes for broadcast input

        Raises:
            ValueError: If username is empty or hosts list is invalid
        """
        if not hosts:
            self.logger.warning("SSHplex: No hosts provided for connection")
            return False

        if not username or not username.strip():
            raise ValueError("SSH username cannot be empty")
        
        # Validate username format to prevent injection
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            raise ValueError(f"Invalid username format: {username}")

        if port < 1 or port > 65535:
            raise ValueError(f"SSH port must be between 1 and 65535, got {port}")

        # Get retry configuration
        if self.config is None:
            max_attempts = 1
            base_delay = 1
            retry_exponential = False
        else:
            retry_config = self.config.ssh.retry
            max_attempts = retry_config.max_attempts if retry_config.enabled else 1
            base_delay = retry_config.delay_seconds
            retry_exponential = retry_config.exponential_backoff

        try:
            # Create tmux session
            if not self.multiplexer.create_session():
                self.logger.error("SSHplex: Failed to create tmux session")
                self.last_success_count = 0
                self.last_failed_hosts = [h.ip if h.ip else h.name for h in hosts]
                return False

            success_count = 0
            failed_hosts = []

            for _i, host in enumerate(hosts):
                target_host = host.ip if host.ip else host.name
                pane_id = host.name if host.name else target_host

                # Validate connection target format to prevent injection
                if not re.match(r'^[a-zA-Z0-9.-]+$', target_host):
                    self.logger.warning(f"Invalid hostname format (potential injection): {target_host}")
                    self.logger.warning("Skipping potentially malicious host")
                    continue

                # Build SSH command
                ssh_command = self._build_ssh_command(host, username, key_path, port)
                self.logger.debug(
                    "SSHplex: Built SSH command for "
                    f"{target_host}: {self._sanitize_ssh_command(ssh_command)}"
                )

                self.logger.info(f"SSHplex: Connecting to {target_host} as {username}")

                # Attempt connection with retry logic
                connection_success = False
                last_error = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        if self.backend == "iterm2-native":
                            if use_panes:
                                max_panes = self.config.tmux.max_panes_per_window if self.config else 5
                                if self.multiplexer.create_pane(pane_id, ssh_command, max_panes):
                                    connection_success = True
                                    self.logger.info(f"SSHplex: Successfully created pane for {target_host}")
                                else:
                                    last_error = "Failed to create iTerm2 native pane"
                            else:
                                if self.multiplexer.create_window(pane_id, ssh_command):
                                    connection_success = True
                                    self.logger.info(f"SSHplex: Successfully created tab for {target_host}")
                                else:
                                    last_error = "Failed to create iTerm2 native tab"
                        else:
                            if use_panes:
                                # Create pane with SSH command
                                max_panes = self.config.tmux.max_panes_per_window if self.config else 5
                                if self.multiplexer.create_pane(pane_id, ssh_command, max_panes):
                                    connection_success = True
                                    self.logger.info(f"SSHplex: Successfully created pane for {target_host}")
                                else:
                                    last_error = "Failed to create tmux pane"
                            else:
                                # Create window (tab) with SSH command
                                use_iterm2 = "darwin" in self.system and (self.config.tmux.control_with_iterm2 if self.config else False)
                                if use_iterm2:
                                    # iTerm2 mode: use single-pane windows for tmux -CC integration
                                    if self.multiplexer.create_pane(pane_id, ssh_command, 1):
                                        connection_success = True
                                        self.logger.info(f"SSHplex: Successfully created window for {target_host}")
                                    else:
                                        last_error = "Failed to create iTerm2 window"
                                else:
                                    if self.multiplexer.create_window(pane_id, ssh_command):
                                        connection_success = True
                                        self.logger.info(f"SSHplex: Successfully created window for {target_host}")
                                    else:
                                        last_error = "Failed to create tmux window"
                        
                        if connection_success:
                            break
                            
                    except Exception as e:
                        last_error = str(e)
                        self.logger.warning(f"SSHplex: Connection attempt {attempt}/{max_attempts} failed for {target_host}: {e}")
                    
                    # If not successful and more attempts remain, wait before retry
                    if not connection_success and attempt < max_attempts:
                        # Calculate delay with optional exponential backoff
                        if retry_exponential:
                            delay = base_delay * (2 ** (attempt - 1))
                        else:
                            delay = base_delay
                        
                        self.logger.info(f"SSHplex: Retrying {target_host} in {delay}s (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(delay)

                if connection_success:
                    success_count += 1
                else:
                    self.logger.error(f"SSHplex: Failed to create connection for {target_host} after {max_attempts} attempts: {last_error}")
                    failed_hosts.append(target_host)

            # Apply tiled layout for multiple panes (only when using panes, not windows)
            if use_panes and success_count > 1:
                self.multiplexer.setup_tiled_layout()

            # Enable broadcast mode if requested
            if use_broadcast and success_count > 1:
                if self.multiplexer.enable_broadcast():
                    self.logger.info("SSHplex: Broadcast mode enabled")
                else:
                    self.logger.warning("SSHplex: Failed to enable broadcast mode")

            mode_text = "panes" if use_panes else "windows"
            broadcast_text = " with broadcast" if use_broadcast else ""
            self.logger.info(f"SSHplex: Connected to {success_count}/{len(hosts)} hosts using {mode_text}{broadcast_text}")

            self.last_success_count = success_count
            self.last_failed_hosts = failed_hosts
            
            if failed_hosts:
                self.logger.warning(f"SSHplex: Failed to connect to hosts: {', '.join(failed_hosts)}")
            
            return success_count > 0

        except Exception as e:
            self.logger.error(f"SSHplex: Error during connection process: {e}")
            self.last_success_count = 0
            self.last_failed_hosts = [h.ip if h.ip else h.name for h in hosts]
            return False

    def _build_ssh_command(self, host: Any, username: str, key_path: Optional[str] = None, port: int = 22) -> str:
        """Build SSH command string with configurable security options.

        Args:
            host: Host object with name, ip, and metadata attributes
            username: SSH username
            key_path: Path to SSH private key (optional)
            port: SSH port (default: 22)

        Returns:
            SSH command string

        Raises:
            ValueError: If host is missing required attributes
        """
        if not host:
            raise ValueError("Host object cannot be None")

        # Validate host has required attributes
        hostname = host.ip if host.ip else host.name
        if not hostname:
            raise ValueError(f"Host missing both ip and name: {host}")

        cmd_parts = ["TERM=xterm-256color", "/usr/bin/ssh"]

        # Try to configure proxy if available
        try:
            if self.config is not None:
                provider_name = host.metadata.get('provider', '')
                if provider_name:
                    proxy = next(
                        (item for item in self.config.ssh.proxy if provider_name in item.imports),
                        None
                    )
                    if proxy:
                        # Sanitize proxy credentials to prevent injection
                        proxy_host = proxy.host or ''
                        proxy_user = proxy.username or ''
                        proxy_key = proxy.key_path or ''
                        
                        # Validate proxy values format
                        if (re.match(r'^[a-zA-Z0-9.-]+$', proxy_host) and
                            re.match(r'^[a-zA-Z0-9._-]+$', proxy_user) and
                            os.path.isabs(proxy_key) and '..' not in proxy_key):
                            # Use shlex.quote for safe shell escaping
                            cmd_parts.extend([
                                "-o", f"ProxyCommand=/usr/bin/ssh -i {shlex.quote(proxy_key)} -W %h:%p {shlex.quote(proxy_user)}@{shlex.quote(proxy_host)}"
                            ])
                        else:
                            self.logger.warning("Proxy configuration contains invalid values, skipping proxy")
        except Exception:
            # Proxy not configured for this host, continue without it
            pass

        # Configure host key checking based on config
        if self.config is not None:
            strict_mode = self.config.ssh.strict_host_key_checking
            if strict_mode:
                cmd_parts.extend(["-o", "StrictHostKeyChecking=yes"])
            else:
                # Less strict but still reasonable
                cmd_parts.extend(["-o", "StrictHostKeyChecking=accept-new"])

            # Configure known_hosts file
            known_hosts = self.config.ssh.user_known_hosts_file
            if known_hosts:
                cmd_parts.extend(["-o", f"UserKnownHostsFile={known_hosts}"])
            # If empty, SSH uses default ~/.ssh/known_hosts
        else:
            # Use reasonable defaults when config is None
            cmd_parts.extend(["-o", "StrictHostKeyChecking=accept-new"])

        cmd_parts.extend(["-o", "LogLevel=ERROR"])

        # Add key file if provided
        if key_path:
            cmd_parts.extend(["-i", key_path])

        # Add port if not default
        if port != 22:
            cmd_parts.extend(["-p", str(port)])

        # Add connection timeout
        timeout = getattr(self.config.ssh, 'timeout', 10) if self.config else 10
        cmd_parts.extend(["-o", f"ConnectTimeout={timeout}"])

        # Add user@hostname with proper escaping
        cmd_parts.append(f"{shlex.quote(username)}@{shlex.quote(hostname)}")

        return " ".join(cmd_parts)

    def get_session_name(self) -> str:
        """Get the tmux session name."""
        return self.session_name

    def attach_to_session(self, auto_attach: bool = True) -> None:
        """Prepare session for attachment or auto-attach."""
        self.multiplexer.attach_to_session(auto_attach=auto_attach)

    def close_connections(self) -> None:
        """Close all SSH connections and tmux session."""
        self.logger.info("SSHplex: Closing all connections")
        self.multiplexer.close_session()
