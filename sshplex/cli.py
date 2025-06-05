"""CLI debug interface for SSHplex (for pip-installed package)"""

import sys
import argparse
from typing import Any

from .lib.config import load_config
from .lib.logger import setup_logging, get_logger
from .lib.sot.netbox import NetBoxProvider


def main() -> int:
    """CLI debug entry point for installed SSHplex package."""

    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="SSHplex CLI: Debug interface for NetBox connectivity testing.")
        parser.add_argument('--config', type=str, default=None, help='Path to the configuration file (default: ~/.config/sshplex/sshplex.yaml)')
        parser.add_argument('--version', action='version', version='SSHplex 1.0.0')
        args = parser.parse_args()

        # Load configuration (will use default path if none specified)
        print("SSHplex CLI Debug Mode - Loading configuration...")
        config = load_config(args.config)

        # Setup logging
        setup_logging(
            log_level=config.logging.level,
            log_file=config.logging.file,
            enabled=config.logging.enabled
        )

        logger = get_logger()
        logger.info("SSHplex CLI debug mode started")

        return debug_mode(config, logger)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure config.yaml exists and is properly configured")
        print("Note: This is the CLI debug interface. For the full TUI application,")
        print("run the main sshplex.py script from the source repository.")
        return 1
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nSSHplex CLI interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def debug_mode(config: Any, logger: Any) -> int:
    """Run debug mode - NetBox connection and host listing test."""
    logger.info("Running CLI debug mode - NetBox connectivity test")

    # Initialize NetBox provider
    logger.info("Initializing NetBox provider")
    netbox = NetBoxProvider(
        url=config.netbox.url,
        token=config.netbox.token,
        verify_ssl=config.netbox.verify_ssl,
        timeout=config.netbox.timeout
    )

    # Test connection
    logger.info("Testing NetBox connection...")
    if not netbox.connect():
        logger.error("Failed to connect to NetBox")
        print("❌ Failed to connect to NetBox")
        print("Check your configuration and network connectivity")
        return 1

    print("✅ Successfully connected to NetBox")

    # Retrieve VMs with filters
    logger.info("Retrieving VMs from NetBox...")
    hosts = netbox.get_hosts(filters=config.netbox.default_filters)

    # Display results
    if hosts:
        logger.info(f"Successfully retrieved {len(hosts)} VMs")
        print(f"\n📋 Found {len(hosts)} hosts matching filters:")
        print("-" * 60)
        for i, host in enumerate(hosts, 1):
            status = host.metadata.get('status', 'unknown')
            print(f"{i:3d}. {host.name:<30} {host.ip:<15} [{status}]")
        print("-" * 60)
    else:
        logger.warning("No VMs found matching the filters")
        print("⚠️  No hosts found matching the configured filters")
        print("Check your NetBox filters in the configuration")

    logger.info("SSHplex CLI debug mode completed successfully")
    print(f"\n✅ CLI debug mode completed successfully")
    print("Note: For the full TUI interface, run the main application")
    return 0


if __name__ == "__main__":
    sys.exit(main())
