"""CLI debug interface for SSHplex (for pip-installed package)"""

import argparse
import sys
from typing import Any

from . import __version__
from .lib.commands import clear_cache, run_debug_mode, show_config_info
from .lib.config import load_config
from .lib.logger import get_logger, setup_logging


def main() -> int:
    """CLI debug entry point for installed SSHplex package."""

    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description="SSHplex CLI: Debug interface and utilities for SSH connection management.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  sshplex-cli --debug              Run connectivity test
  sshplex-cli --list-providers     List configured providers
  sshplex-cli --clear-cache        Clear the host cache
  sshplex-cli --show-config        Show configuration paths
            """
        )
        parser.add_argument('--config', type=str, default=None, 
                          help='Path to the configuration file (default: ~/.config/sshplex/sshplex.yaml)')
        parser.add_argument('--version', action='version', version=f'SSHplex {__version__}')
        parser.add_argument('--debug', action='store_true', 
                          help='Run in debug mode - test provider connectivity and list hosts')
        parser.add_argument('--list-providers', action='store_true',
                          help='List all configured SoT providers')
        parser.add_argument('--clear-cache', action='store_true',
                          help='Clear the host cache')
        parser.add_argument('--show-config', action='store_true',
                          help='Show configuration file paths and status')
        parser.add_argument('--verbose', '-v', action='store_true',
                          help='Enable verbose output')
        args = parser.parse_args()

        # Handle show-config without loading config
        if args.show_config:
            return show_config_info()

        # Load configuration (will use default path if none specified)
        if args.debug or args.list_providers or args.clear_cache:
            print("SSHplex CLI - Loading configuration...")
            config = load_config(args.config)

            # Setup logging
            log_level = "DEBUG" if args.verbose else config.logging.level
            setup_logging(
                log_level=log_level,
                log_file=config.logging.file,
                enabled=config.logging.enabled or args.verbose
            )

            logger = get_logger()
            logger.info("SSHplex CLI started")

            if args.clear_cache:
                return clear_cache(config, logger, no_cache_message="Clearing cache...")
            elif args.list_providers:
                return list_providers(config, logger)
            else:
                return run_debug_mode(
                    config,
                    logger,
                    footer_note="Note: For the full TUI interface, run the main application",
                )
        else:
            # Default to debug mode if no specific action
            print("SSHplex CLI - Loading configuration...")
            config = load_config(args.config)

            setup_logging(
                log_level=config.logging.level,
                log_file=config.logging.file,
                enabled=config.logging.enabled
            )

            logger = get_logger()
            logger.info("SSHplex CLI debug mode started")

            return run_debug_mode(
                config,
                logger,
                footer_note="Note: For the full TUI interface, run the main application",
            )

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure config.yaml exists and is properly configured")
        print("Run 'sshplex-cli --show-config' for configuration details")
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


def list_providers(config: Any, logger: Any) -> int:
    """List all configured SoT providers."""
    logger.info("Listing configured SoT providers")
    
    if not hasattr(config.sot, 'import_') or not config.sot.import_:
        print("❌ No SoT providers configured")
        print("Add providers to ~/.config/sshplex/sshplex.yaml")
        return 1
    
    print(f"📋 Configured SoT Providers ({len(config.sot.import_)} total)")
    print("=" * 60)
    
    for i, provider in enumerate(config.sot.import_, 1):
        status_icon = "📦"
        if provider.type == "netbox":
            status_icon = "🌐"
        elif provider.type == "ansible":
            status_icon = "📝"
        elif provider.type == "consul":
            status_icon = "🔍"
        elif provider.type == "git":
            status_icon = "🔄"
        
        print(f"{i}. {status_icon} {provider.name}")
        print(f"   Type: {provider.type}")
        
        if provider.type == "netbox" and provider.url:
            print(f"   URL:  {provider.url}")
        elif provider.type == "ansible" and provider.inventory_paths:
            print(f"   Paths: {', '.join(provider.inventory_paths)}")
        elif provider.type == "consul" and provider.config:
            print(f"   Host: {provider.config.host}:{provider.config.port}")
        elif provider.type == "git" and provider.repo_url:
            branch = provider.branch or "main"
            profile = provider.profile or "solo"
            inventory_format = provider.inventory_format or "static"
            print(f"   Repo: {provider.repo_url} [{branch}, {profile}, {inventory_format}]")
            source_pattern = provider.source_pattern or f"{provider.path}/{provider.file_glob}"
            print(f"   Source: {source_pattern}")
        elif provider.type == "static" and provider.hosts:
            print(f"   Hosts: {len(provider.hosts)} defined")
        
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
