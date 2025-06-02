#!/usr/bin/env python3
"""SSHplex Phase 2 Test - Test tmux pane creation with sample hosts."""

import sys
from pathlib import Path

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import load_config
from lib.logger import setup_logging, get_logger
from lib.sot.base import Host
from sshplex_connector import SSHplexConnector


def test_phase2():
    """Test Phase 2 tmux pane functionality with sample hosts."""
    try:
        # Load configuration
        print("SSHplex Phase 2 Test - Loading configuration...")
        config = load_config('config.yaml')

        # Setup logging
        setup_logging(
            log_level=config.logging.level,
            log_file=config.logging.file
        )

        logger = get_logger()
        logger.info("SSHplex Phase 2 Test started")

        # Create sample hosts to test with
        sample_hosts = [
            Host(name="test-host-1", ip="192.168.1.10", metadata={"cluster": "test-cluster"}),
            Host(name="test-host-2", ip="192.168.1.11", metadata={"cluster": "test-cluster"}),
            Host(name="test-host-3", ip="192.168.1.12", metadata={"cluster": "test-cluster"}),
        ]

        logger.info(f"Testing with {len(sample_hosts)} sample hosts")
        for host in sample_hosts:
            logger.info(f"  - {host.name} ({host.ip})")

        # Create connector
        connector = SSHplexConnector("sshplex-test")

        # Test tmux pane creation
        logger.info("Testing tmux pane creation...")
        if connector.connect_to_hosts(
            hosts=sample_hosts,
            username=config.ssh.username,
            key_path=config.ssh.key_path
        ):
            logger.info("Successfully created tmux panes!")
            logger.info(f"tmux session name: {connector.get_session_name()}")
            logger.info("To attach to the session manually, run:")
            logger.info(f"  tmux attach-session -t {connector.get_session_name()}")

            input("\nPress Enter to attach to the tmux session...")
            connector.attach_to_session()
        else:
            logger.error("Failed to create tmux panes")
            return 1

        return 0

    except Exception as e:
        print(f"Test error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(test_phase2())
