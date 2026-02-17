"""Main entry point for SSHplex TUI Application (pip-installed package)"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any

from . import __version__
from .lib.config import load_config
from .lib.logger import setup_logging, get_logger
from .lib.sot.factory import SoTFactory
from .lib.ui.host_selector import HostSelector



def check_system_dependencies() -> bool:
    """Check if required system dependencies are available."""
    # Check if tmux is installed and available in PATH
    if not shutil.which("tmux"):
        print("❌ Error: tmux is not installed or not found in PATH")
        print("\nSSHplex requires tmux for terminal multiplexing.")
        print("Please install tmux:")
        print("\n  macOS:    brew install tmux")
        print("  Ubuntu:   sudo apt install tmux")
        print("  RHEL/CentOS/Fedora: sudo dnf install tmux")
        print("\nThen try running SSHplex again.")
        return False

    return True


def main() -> int:
    """Main entry point for SSHplex TUI Application."""

    try:
        # Check system dependencies first
        if not check_system_dependencies():
            return 1

        # Parse command line arguments
        parser = argparse.ArgumentParser(description="SSHplex: Multiplex your SSH connections with style.")
        parser.add_argument('--config', type=str, default=None, help='Path to the configuration file (default: ~/.config/sshplex/sshplex.yaml)')
        parser.add_argument('--version', action='version', version=f'SSHplex {__version__}')
        parser.add_argument('--debug', action='store_true', help='Run in debug mode (CLI only, no TUI)')
        args = parser.parse_args()

        # Load configuration (will use default path if none specified)
        print("SSHplex - Loading configuration...")
        config = load_config(args.config)

        # Setup logging
        setup_logging(
            log_level=config.logging.level,
            log_file=config.logging.file,
            enabled=config.logging.enabled
        )

        logger = get_logger()
        logger.info("SSHplex started")

        if args.debug:
            # Debug mode - simple NetBox test
            return debug_mode(config, logger)
        else:
            # TUI mode - main application
            return tui_mode(config, logger)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure config.yaml exists and is properly configured")
        return 1
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nSSHplex interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def debug_mode(config: Any, logger: Any) -> int:
    """Run in debug mode - test all configured SoT providers."""
    logger.info("Running in debug mode - SoT provider connectivity test")

    # Initialize SoT factory
    logger.info("Initializing SoT factory")
    sot_factory = SoTFactory(config)

    # Initialize all providers
    if not sot_factory.initialize_providers():
        logger.error("Failed to initialize any SoT providers")
        print("❌ Failed to initialize any SoT providers")
        print("Check your configuration and network connectivity")
        return 1

    print(f"✅ Successfully initialized {sot_factory.get_provider_count()} SoT provider(s): {', '.join(sot_factory.get_provider_names())}")

    # Test all connections
    logger.info("Testing SoT provider connections...")
    connection_results = sot_factory.test_all_connections()

    for provider_name, status in connection_results.items():
        if status:
            print(f"✅ {provider_name}: Connection successful")
        else:
            print(f"❌ {provider_name}: Connection failed")

    # Retrieve hosts from all providers
    logger.info("Retrieving hosts from all SoT providers...")
    hosts = sot_factory.get_all_hosts()

    # Display results
    if hosts:
        logger.info(f"Successfully retrieved {len(hosts)} hosts")
        print(f"\n📋 Found {len(hosts)} hosts from all providers:")
        print("-" * 80)
        for i, host in enumerate(hosts, 1):
            status = getattr(host, 'status', host.metadata.get('status', 'unknown'))
            sources = host.metadata.get('sources', ['unknown'])
            source_str = ', '.join(sources) if isinstance(sources, list) else str(sources)
            print(f"{i:3d}. {host.name:<25} {host.ip:<15} [{status:<8}] ({source_str})")
        print("-" * 80)
    else:
        logger.warning("No hosts found matching the filters")
        print("⚠️  No hosts found matching the configured filters")
        print("Check your SoT provider filters in the configuration")

    logger.info("SSHplex debug mode completed successfully")
    print(f"\n✅ Debug mode completed successfully")
    return 0


def tui_mode(config: Any, logger: Any) -> int:
    """Run in TUI mode - interactive host selection with tmux panes."""
    logger.info("Starting TUI mode - interactive host selection with tmux integration")

    try:
        # Start the host selector TUI
        app = HostSelector(config=config)
        app.run()
        return 0

    except Exception as e:
        logger.error(f"TUI error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
