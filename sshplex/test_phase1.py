#!/usr/bin/env python3
"""Test script for SSHplex Phase 1 - NetBox connectivity"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from lib.config import load_config, Config
        print("✓ Config module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import config module: {e}")
        return False

    try:
        from lib.logger import setup_logging, get_logger
        print("✓ Logger module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import logger module: {e}")
        return False

    try:
        from lib.sot.base import SoTProvider, Host
        print("✓ SoT base module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import SoT base module: {e}")
        return False

    try:
        from lib.sot.netbox import NetBoxProvider
        print("✓ NetBox provider imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import NetBox provider: {e}")
        return False

    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")

    try:
        from lib.config import load_config
        config = load_config("config.yaml")
        print("✓ Configuration loaded successfully")
        print(f"  - NetBox URL: {config.netbox.url}")
        print(f"  - Logging level: {config.logging.level}")
        print(f"  - Default filters: {config.netbox.default_filters}")
        return True
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False

def main():
    """Run all tests."""
    print("SSHplex Phase 1 - Running tests...\n")

    # Test imports
    if not test_imports():
        return 1

    # Test configuration
    if not test_config():
        return 1

    print("\n✓ All tests passed! SSHplex Phase 1 is ready.")
    print("\nTo test NetBox connectivity, update config.yaml with your NetBox details and run:")
    print("  python sshplex.py")

    return 0

if __name__ == "__main__":
    sys.exit(main())
