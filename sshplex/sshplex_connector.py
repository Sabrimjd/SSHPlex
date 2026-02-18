"""SSHplex Connector - SSH connections and tmux session management."""

from typing import Any, List, Optional
from datetime import datetime
import time
import subprocess

from .lib.logger import get_logger
from .lib.multiplexer.tmux import TmuxManager
from .lib.sot.base import Host

import platform


class SSHConnectionError(Exception):
    """Raised when SSH connection fails after all retries."""
    pass


class SSHplexConnector:
    """Manages SSH connections and tmux session management."""

    def __init__(self, session_name: Optional[str], config: Optional[Any] = None):
        """Initialize the connector with optional session name and max panes per window."""
        if session_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"

        self.session_name = session_name
        self.config = config
        self.tmux_manager = TmuxManager(session_name, config)
        self.logger = get_logger()
        self.system = platform.system().lower()

    def connect_to_hosts(self, hosts: List[Host], username: str, key_path: Optional[str] = None, port: int = 22, use_panes: bool = True, use_broadcast: bool = False) -> bool:
        """Establish SSH connections to the specified hosts using shell SSH with retry support.

        Args:
            hosts: List of hosts to connect to
            username: SSH username
            key_path: Path to SSH private key (optional)
            port: SSH port (default: 22)
            use_panes: If True, create panes; if False, create windows/tabs
            use_broadcast: If True, enable synchronize-panes for broadcast input
        """
        if not hosts:
            self.logger.warning("SSHplex: No hosts provided for connection")
            return False

        # Get retry configuration
        retry_config = self.config.ssh.retry
        max_attempts = retry_config.max_attempts if retry_config.enabled else 1
        base_delay = retry_config.delay_seconds

        try:
            # Create tmux session
            if not self.tmux_manager.create_session():
                self.logger.error("SSHplex: Failed to create tmux session")
                return False

            success_count = 0
            failed_hosts = []

            for i, host in enumerate(hosts):
                hostname = host.ip if host.ip else host.name

                # Build SSH command
                ssh_command = self._build_ssh_command(host, username, key_path, port)

                self.logger.info(f"SSHplex: Connecting to {hostname} as {username}")

                # Attempt connection with retry logic
                connection_success = False
                last_error = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        if use_panes:
                            # Create pane with SSH command
                            if self.tmux_manager.create_pane(hostname, ssh_command, self.config.tmux.max_panes_per_window):
                                connection_success = True
                                self.logger.info(f"SSHplex: Successfully created pane for {hostname}")
                            else:
                                last_error = "Failed to create tmux pane"
                        else:
                            # Create window (tab) with SSH command
                            if "darwin" in self.system and self.config.tmux.control_with_iterm2:
                                # iTerm2 mode: use single-pane windows for tmux -CC integration
                                if self.tmux_manager.create_pane(hostname, ssh_command, 1):
                                    connection_success = True
                                    self.logger.info(f"SSHplex: Successfully created window for {hostname}")
                                else:
                                    last_error = "Failed to create iTerm2 window"
                            else:
                                if self.tmux_manager.create_window(hostname, ssh_command):
                                    connection_success = True
                                    self.logger.info(f"SSHplex: Successfully created window for {hostname}")
                                else:
                                    last_error = "Failed to create tmux window"
                        
                        if connection_success:
                            break
                            
                    except Exception as e:
                        last_error = str(e)
                        self.logger.warning(f"SSHplex: Connection attempt {attempt}/{max_attempts} failed for {hostname}: {e}")
                    
                    # If not successful and more attempts remain, wait before retry
                    if not connection_success and attempt < max_attempts:
                        # Calculate delay with optional exponential backoff
                        if retry_config.exponential_backoff:
                            delay = base_delay * (2 ** (attempt - 1))
                        else:
                            delay = base_delay
                        
                        self.logger.info(f"SSHplex: Retrying {hostname} in {delay}s (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(delay)

                if connection_success:
                    success_count += 1
                else:
                    self.logger.error(f"SSHplex: Failed to create connection for {hostname} after {max_attempts} attempts: {last_error}")
                    failed_hosts.append(hostname)

            # Apply tiled layout for multiple panes (only when using panes, not windows)
            if use_panes and success_count > 1:
                self.tmux_manager.setup_tiled_layout()

            # Enable broadcast mode if requested
            if use_broadcast and success_count > 1:
                if self.tmux_manager.enable_broadcast():
                    self.logger.info("SSHplex: Broadcast mode enabled")
                else:
                    self.logger.warning("SSHplex: Failed to enable broadcast mode")

            mode_text = "panes" if use_panes else "windows"
            broadcast_text = " with broadcast" if use_broadcast else ""
            self.logger.info(f"SSHplex: Connected to {success_count}/{len(hosts)} hosts using {mode_text}{broadcast_text}")
            
            if failed_hosts:
                self.logger.warning(f"SSHplex: Failed to connect to hosts: {', '.join(failed_hosts)}")
            
            return success_count > 0

        except Exception as e:
            self.logger.error(f"SSHplex: Error during connection process: {e}")
            return False

    def _build_ssh_command(self, host: Any, username: str, key_path: Optional[str] = None, port: int = 22) -> str:
        """Build SSH command string with configurable security options."""
        cmd_parts = ["TERM=xterm-256color", "ssh"]

        # Try to configure proxy if available
        try:
            key = host.metadata['provider']
            proxy = next(
                (item for item in self.config.ssh.proxy if key in item.imports),
                None
            )
            if proxy:
                cmd_parts.extend([
                    "-o", f"ProxyCommand=ssh -i {proxy.key_path} -W %h:%p {proxy.username}@{proxy.host}"
                ])
        except Exception:
            # Proxy not configured for this host, continue without it
            pass

        hostname = host.ip if host.ip else host.name

        # Configure host key checking based on config
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

        cmd_parts.extend(["-o", "LogLevel=ERROR"])

        # Add key file if provided
        if key_path:
            cmd_parts.extend(["-i", key_path])

        # Add port if not default
        if port != 22:
            cmd_parts.extend(["-p", str(port)])

        # Add connection timeout
        timeout = getattr(self.config.ssh, 'timeout', 10)
        cmd_parts.extend(["-o", f"ConnectTimeout={timeout}"])

        # Add user@hostname
        cmd_parts.append(f"{username}@{hostname}")

        return " ".join(cmd_parts)

    def _test_ssh_connectivity(self, hostname: str, username: str, key_path: Optional[str], port: int) -> bool:
        """Test SSH connectivity to a host before creating pane/window.
        
        Returns True if connection is possible, False otherwise.
        """
        # Build a minimal test command
        cmd_parts = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
        
        if key_path:
            cmd_parts.extend(["-i", key_path])
        if port != 22:
            cmd_parts.extend(["-p", str(port)])
            
        cmd_parts.append(f"{username}@{hostname}")
        cmd_parts.append("exit")  # Just test connection, then exit
        
        try:
            result = subprocess.run(
                " ".join(cmd_parts),
                shell=True,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def get_session_name(self) -> str:
        """Get the tmux session name."""
        return self.session_name

    def attach_to_session(self, auto_attach: bool = True) -> None:
        """Prepare session for attachment or auto-attach."""
        self.tmux_manager.attach_to_session(auto_attach=auto_attach)

    def close_connections(self) -> None:
        """Close all SSH connections and tmux session."""
        self.logger.info("SSHplex: Closing all connections")
        self.tmux_manager.close_session()
