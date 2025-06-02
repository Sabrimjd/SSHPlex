"""SSHplex Connector - SSH connections and tmux session management."""

from typing import List
from datetime import datetime

from lib.logger import get_logger
from lib.multiplexer.tmux import TmuxManager
from lib.sot.base import Host


class SSHplexConnector:
    """Manages SSH connections and tmux session management."""

    def __init__(self, session_name: str = None):
        """Initialize the connector with optional session name."""
        if session_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"

        self.session_name = session_name
        self.tmux_manager = TmuxManager(session_name)
        self.logger = get_logger()

    def connect_to_hosts(self, hosts: List[Host], username: str, key_path: str = None, port: int = 22) -> bool:
        """Establish SSH connections to the specified hosts using shell SSH."""
        if not hosts:
            self.logger.warning("SSHplex: No hosts provided for connection")
            return False

        try:
            # Create tmux session
            if not self.tmux_manager.create_session():
                self.logger.error("SSHplex: Failed to create tmux session")
                return False

            success_count = 0
            for host in hosts:
                hostname = host.ip if host.ip else host.name

                # Build SSH command
                ssh_command = self._build_ssh_command(hostname, username, key_path, port)

                self.logger.info(f"SSHplex: Connecting to {hostname} as {username}")

                # Create pane with SSH command
                if self.tmux_manager.create_pane(hostname, ssh_command):
                    success_count += 1
                    self.logger.info(f"SSHplex: Successfully created connection to {hostname}")
                else:
                    self.logger.error(f"SSHplex: Failed to create connection to {hostname}")

            # Apply tiled layout for multiple panes
            if success_count > 1:
                self.tmux_manager.setup_tiled_layout()

            self.logger.info(f"SSHplex: Connected to {success_count}/{len(hosts)} hosts")
            return success_count > 0

        except Exception as e:
            self.logger.error(f"SSHplex: Error during connection process: {e}")
            return False

    def _build_ssh_command(self, hostname: str, username: str, key_path: str = None, port: int = 22) -> str:
        """Build SSH command string."""
        cmd_parts = ["ssh"]

        # Add SSH options
        cmd_parts.extend(["-o", "StrictHostKeyChecking=no"])
        cmd_parts.extend(["-o", "UserKnownHostsFile=/dev/null"])
        cmd_parts.extend(["-o", "LogLevel=ERROR"])

        # Add key file if provided
        if key_path:
            cmd_parts.extend(["-i", key_path])

        # Add port if not default
        if port != 22:
            cmd_parts.extend(["-p", str(port)])

        # Add user@hostname
        cmd_parts.append(f"{username}@{hostname}")

        return " ".join(cmd_parts)

    def get_session_name(self) -> str:
        """Get the tmux session name."""
        return self.session_name

    def attach_to_session(self) -> None:
        """Prepare session for attachment."""
        self.tmux_manager.attach_to_session()

    def close_connections(self) -> None:
        """Close all SSH connections and tmux session."""
        self.logger.info("SSHplex: Closing all connections")
        self.tmux_manager.close_session()
