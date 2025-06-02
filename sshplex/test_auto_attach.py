#!/usr/bin/env python3
"""
Test script for SSHplex auto-attach functionality.
This script tests Phase 2 with auto-attachment to tmux session.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.config import load_config
from lib.logger import setup_logging, get_logger
from lib.sot.netbox import Host
from sshplex_connector import SSHplexConnector
from datetime import datetime

def test_auto_attach():
    """Test auto-attachment to tmux session."""

    # Setup logger
    setup_logging()
    logger = get_logger()
    logger.info("SSHplex: Testing auto-attach functionality")

    # Load configuration
    try:
        config = load_config("config.yaml")
        logger.info("SSHplex: Configuration loaded successfully")
    except Exception as e:
        logger.error(f"SSHplex: Failed to load configuration: {e}")
        return

    # Create test hosts (using Host objects)
    test_hosts = [Host(name="localhost", ip="127.0.0.1")]

    print("🧪 SSHplex Auto-Attach Test")
    print(f"📋 Test hosts: {test_hosts}")
    print(f"👤 SSH username: {config.ssh.username}")

    # Create connector with timestamped session name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"sshplex-test-{timestamp}"
    connector = SSHplexConnector(session_name)

    # Connect to hosts
    if connector.connect_to_hosts(
        hosts=test_hosts,
        username=config.ssh.username,
        key_path=config.ssh.key_path,
        port=config.ssh.port
    ):
        print(f"\n✅ Tmux session '{session_name}' created successfully!")
        print(f"🔗 {len(test_hosts)} SSH connection(s) established")
        print(f"\n🚀 Auto-attaching to session...")
        print(f"📝 Note: This will replace the current shell with tmux")

        # Auto-attach to the session
        connector.attach_to_session(auto_attach=True)
    else:
        print("❌ Failed to create SSH connections")
        logger.error("SSHplex: Test failed - could not create connections")

if __name__ == "__main__":
    test_auto_attach()
