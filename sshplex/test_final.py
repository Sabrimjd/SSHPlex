#!/usr/bin/env python3
"""Test Phase 2 SSH connections and keep session alive."""

import sys
import os
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import load_config
from lib.logger import setup_logging, get_logger
from lib.sot.base import Host
from sshplex_connector import SSHplexConnector


def test_ssh_and_attach():
    """Test SSH connections and provide session for manual attachment."""

    # Load configuration
    config = load_config("config.yaml")

    # Setup logging
    setup_logging(log_level="INFO", log_file="logs/sshplex.log")
    logger = get_logger()

    logger.info("SSHplex: Creating SSH connections with tmux panes")

    # Create test hosts
    test_hosts = [
        Host(name="localhost", ip="127.0.0.1", metadata={"status": "active"}),
        Host(name="localhost-2", ip="127.0.0.1", metadata={"status": "active"}),
    ]

    # Initialize connector
    connector = SSHplexConnector()

    # Connect to hosts
    success = connector.connect_to_hosts(
        test_hosts,
        username=config.ssh.username,
        key_path=config.ssh.key_path,
        port=config.ssh.port
    )

    if success:
        session_name = connector.get_session_name()
        logger.info(f"SSHplex: Created session '{session_name}' with {len(test_hosts)} SSH connections")
        print(f"\n✅ SSHplex Phase 2 Implementation Complete!")
        print(f"📡 tmux session created: {session_name}")
        print(f"🔗 {len(test_hosts)} SSH connections established")
        print(f"\n🚀 To view the tmux session with SSH connections:")
        print(f"   tmux attach-session -t {session_name}")
        print(f"\n⚡ In tmux, you can:")
        print(f"   - Switch between panes: Ctrl+b then arrow keys")
        print(f"   - Detach: Ctrl+b then d")
        print(f"   - Exit: Type 'exit' in each pane")

        print(f"\nSession will remain active. Press Ctrl+C to close it.")

        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n🛑 Closing SSHplex session...")
            connector.close_connections()
            print(f"✅ Session closed successfully")
    else:
        logger.error("SSHplex: Failed to create SSH connections")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_ssh_and_attach())
