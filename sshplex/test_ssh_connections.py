#!/usr/bin/env python3
"""Test Phase 2 SSH connections with actual SSH commands."""

import sys
import os
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import load_config
from lib.logger import setup_logging, get_logger
from lib.sot.base import Host
from sshplex_connector import SSHplexConnector


def test_ssh_connections():
    """Test SSH connections with real hosts."""

    # Load configuration
    config = load_config("config.yaml")

    # Setup logging
    setup_logging(
        log_level="INFO",
        log_file="logs/sshplex.log"
    )

    logger = get_logger()
    logger.info("SSHplex: Starting SSH connection test")

    # Create test hosts (you can modify these to real hosts you have access to)
    test_hosts = [
        Host(name="localhost", ip="127.0.0.1", metadata={"status": "active"}),
        # Add more real hosts if you have them accessible
        # Host(name="server1", ip="192.168.1.10", metadata={"status": "active"}),
        # Host(name="server2", ip="192.168.1.11", metadata={"status": "active"}),
    ]

    # Initialize connector
    connector = SSHplexConnector()

    # SSH configuration from config file
    username = config.ssh.username
    key_path = config.ssh.key_path if hasattr(config.ssh, 'key_path') and config.ssh.key_path else None
    port = config.ssh.port

    logger.info(f"SSHplex: Connecting with username={username}, port={port}")
    if key_path:
        logger.info(f"SSHplex: Using SSH key: {key_path}")

    # Connect to hosts
    success = connector.connect_to_hosts(test_hosts, username, key_path, port)

    if success:
        session_name = connector.get_session_name()
        logger.info(f"SSHplex: SSH connections created successfully!")
        logger.info(f"SSHplex: tmux session: {session_name}")
        logger.info(f"SSHplex: To attach to the session, run: tmux attach-session -t {session_name}")

        # Keep the session alive
        input("Press Enter to close the session...")
        connector.close_connections()
    else:
        logger.error("SSHplex: Failed to create SSH connections")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_ssh_connections())
