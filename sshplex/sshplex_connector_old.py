"""SSHplex Connection Manager - Phase 2 with tmux pane support."""

from loguru import logger
from lib.multiplexer.tmux import TmuxManager
import paramiko
from typing import List, Optional, Union, Any
import os
import subprocess


class SSHplexConnector:
    """Manages SSH connections and tmux session management."""

    def __init__(self, session_name: Optional[str] = None):
        """Initialize the connector with tmux session management."""
        self.tmux_manager = TmuxManager(session_name)
        self.ssh_clients = {}

    def connect_to_hosts(self, hosts: List[Any], username: str, key_path: Optional[str] = None) -> bool:
        """Create tmux panes for each host and display host information."""
        try:
            # Create tmux session
            if not self.tmux_manager.create_session():
                logger.error("SSHplex: Failed to create tmux session")
                return False

            logger.info(f"SSHplex: Creating panes for {len(hosts)} hosts")
            
            # Create a pane for each host
            for i, host in enumerate(hosts):
                hostname = getattr(host, 'name', str(host))
                host_ip = getattr(host, 'ip', hostname)
                
                logger.info(f"SSHplex: Creating pane {i+1}/{len(hosts)} for {hostname}")
                
                # Create pane with hostname display
                if self.tmux_manager.create_pane(hostname):
                    # Send command to display host information
                    self.tmux_manager.send_command(hostname, f'echo "=== SSHplex Host: {hostname} ==="')
                    self.tmux_manager.send_command(hostname, f'echo "IP: {host_ip}"')
                    self.tmux_manager.send_command(hostname, f'echo "Ready for SSH connection..."')
                    
                    # TODO: In Phase 3, we'll add actual SSH connection here
                    # For now, just display the host information
                    
                else:
                    logger.error(f"SSHplex: Failed to create pane for {hostname}")
            
            # Apply tiled layout for better visualization
            self.tmux_manager.setup_tiled_layout()
            
            logger.info(f"SSHplex: Successfully created {len(hosts)} panes")
            return True
            
        except Exception as e:
            logger.error(f"SSHplex: Failed to connect to hosts: {e}")
            return False

    def attach_to_session(self) -> None:
        """Attach to the tmux session using external tmux command."""
        try:
            session_name = self.tmux_manager.get_session_name()
            logger.info(f"SSHplex: Attaching to tmux session '{session_name}'")
            
            # Use subprocess to attach to tmux session
            # This will replace the current process
            os.execvp('tmux', ['tmux', 'attach-session', '-t', session_name])
            
        except Exception as e:
            logger.error(f"SSHplex: Failed to attach to session: {e}")
            # Fallback: try using subprocess
            try:
                subprocess.run(['tmux', 'attach-session', '-t', session_name])
            except Exception as fallback_error:
                logger.error(f"SSHplex: Fallback attach failed: {fallback_error}")

    def close_connections(self) -> None:
        """Close all SSH connections and tmux session."""
        logger.info("SSHplex: Closing all connections")
        
        # Close SSH clients
        for hostname, client in self.ssh_clients.items():
            try:
                client.close()
                logger.info(f"SSHplex: Closed SSH connection to {hostname}")
            except Exception as e:
                logger.error(f"SSHplex: Error closing SSH connection to {hostname}: {e}")
        
        # Close tmux session
        self.tmux_manager.close_session()

    def get_session_name(self) -> str:
        """Get the tmux session name."""
        return self.tmux_manager.get_session_name()