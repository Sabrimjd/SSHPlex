# sshplex_connector.py

from loguru import logger
import lib.tmux as tmux
import paramiko
from typing import List

class SSHplexConnector:
    """Manages SSH connections and tmux session management."""

    def __init__(self, session_name: str):
        self.session_name = session_name
        self.tmux_manager = tmux.TmuxManager(session_name)

    def connect_to_hosts(self, hosts: List[str], username: str, key_path: str) -> None:
        """Establish SSH connections to the specified hosts."""
        for host in hosts:
            try:
                logger.info(f"Connecting to {host} as {username}")
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=host, username=username, key_filename=key_path)
                logger.info(f"Successfully connected to {host}")
                self.tmux_manager.create_pane(host)
            except Exception as e:
                logger.error(f"Failed to connect to {host}: {e}")

    def close_connections(self) -> None:
        """Close all active SSH connections."""
        logger.info("Closing all SSH connections.")
        self.tmux_manager.close_all_panes()