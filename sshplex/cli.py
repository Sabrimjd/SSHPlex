"""CLI debug interface for SSHplex (for pip-installed package)"""

import sys
import argparse
from typing import Any

from . import __version__
from .lib.config import load_config
from .lib.logger import setup_logging, get_logger
from .lib.sot.factory import SoTFactory


def main() -> int:
    """CLI debug entry point for installed SSHplex package."""

    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="SSHplex CLI: Debug interface for NetBox connectivity testing.")
        parser.add_argument('--config', type=str, default=None, help='Path to the configuration file (default: ~/.config/sshplex/sshplex.yaml)')
        parser.add_argument('--version', action='version', version=f'SSHplex {__version__}')
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
    """Run debug mode - SoT provider connection and host listing test."""
    logger.info("Running CLI debug mode - SoT provider connectivity test")

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

    logger.info("SSHplex CLI debug mode completed successfully")
    print(f"\n✅ CLI debug mode completed successfully")
    print("Note: For the full TUI interface, run the main application")
    return 0


if __name__ == "__main__":
    sys.exit(main())
