#!/usr/bin/env python3
"""
Test script for SSHplex tmux session manager.
This script tests the new "s" key session manager functionality.
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.config import load_config
from lib.logger import setup_logging, get_logger
from lib.ui.host_selector import HostSelector

def test_session_manager():
    """Test the tmux session manager functionality."""
    
    # Setup logger
    setup_logging()
    logger = get_logger()
    logger.info("SSHplex: Testing session manager functionality")
    
    # Load configuration
    try:
        config = load_config("config.yaml")
        logger.info("SSHplex: Configuration loaded successfully")
    except Exception as e:
        logger.error(f"SSHplex: Failed to load configuration: {e}")
        return

    print("🧪 SSHplex Session Manager Test")
    print("📋 This will launch the TUI with session manager support")
    print("🔑 Press 's' to open the tmux session manager")
    print("💡 Instructions for session manager:")
    print("   - Enter: Connect to selected session")
    print("   - K: Kill selected session")  
    print("   - R: Refresh session list")
    print("   - ESC: Close session manager")
    print("\n🚀 Starting SSHplex TUI...")

    # Create and run the TUI
    app = HostSelector(config)
    try:
        result = app.run()
        
        if result:
            logger.info(f"SSHplex: TUI returned {len(result)} selected hosts")
            for host in result:
                logger.info(f"SSHplex: Selected host: {host.name} ({host.ip})")
        else:
            logger.info("SSHplex: TUI closed without selection")
            
    except KeyboardInterrupt:
        print("\n⚠️  SSHplex TUI interrupted by user")
        logger.info("SSHplex: TUI interrupted by user")
    except Exception as e:
        print(f"❌ SSHplex TUI error: {e}")
        logger.error(f"SSHplex: TUI error: {e}")

if __name__ == "__main__":
    test_session_manager()
