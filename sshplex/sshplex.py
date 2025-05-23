#!/usr/bin/env python3
"""SSHplex - SSH Connection Multiplexer - Phase 1 with TUI Host Selection"""

import sys
import argparse
from pathlib import Path

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.config import load_config
from lib.logger import setup_logging, get_logger
from lib.sot.netbox import NetBoxProvider
from lib.ui.host_selector import HostSelector


def main():
    """Main entry point for SSHplex Phase 1."""
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="SSHplex: Multiplex your SSH connections with style.")
        parser.add_argument('--config', type=str, default='config.yaml', help='Path to the configuration file.')
        parser.add_argument('--version', action='version', version='SSHplex 1.0.0')
        parser.add_argument('--no-tui', action='store_true', help='Run in CLI mode without TUI')
        args = parser.parse_args()
        
        # Load configuration
        print("SSHplex Phase 1 - Loading configuration...")
        config = load_config(args.config)
        
        # Setup logging
        setup_logging(
            log_level=config.logging.level,
            log_file=config.logging.file
        )
        
        logger = get_logger()
        logger.info("SSHplex Phase 1 started")
        
        if args.no_tui:
            # CLI mode - simple test
            return cli_mode(config, logger)
        else:
            # TUI mode - host selection interface
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


def cli_mode(config, logger):
    """Run in CLI mode - simple NetBox connection test."""
    logger.info("Running in CLI mode - NetBox connectivity test")
    
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
        return 1
    
    # Retrieve VMs with filters
    logger.info("Retrieving VMs from NetBox...")
    hosts = netbox.get_hosts(filters=config.netbox.default_filters)
    
    # Log results
    if hosts:
        logger.info(f"Successfully retrieved {len(hosts)} VMs:")
        for host in hosts:
            logger.info(f"  - {host.name} ({host.ip}) - Status: {host.metadata.get('status', 'unknown')}")
    else:
        logger.warning("No VMs found matching the filters")
    
    logger.info("SSHplex CLI mode completed successfully")
    return 0


def tui_mode(config, logger):
    """Run in TUI mode - interactive host selection."""
    logger.info("Starting TUI mode - interactive host selection")
    
    try:
        # Start the host selector TUI
        app = HostSelector(config=config)
        result = app.run()
        
        # The app.run() may return None or a list of hosts
        if isinstance(result, list) and len(result) > 0:
            logger.info(f"User selected {len(result)} hosts")
            for host in result:
                logger.info(f"  - {host.name} ({host.ip})")
        else:
            logger.info("No hosts were selected")
        
        return 0
        
    except Exception as e:
        logger.error(f"TUI error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
