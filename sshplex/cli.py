"""CLI debug interface for SSHplex (for pip-installed package)"""

import sys
import argparse
from typing import Any, Optional

from . import __version__
from .lib.config import load_config, get_config_info
from .lib.logger import setup_logging, get_logger
from .lib.sot.factory import SoTFactory


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
                return clear_cache(config, logger)
            elif args.list_providers:
                return list_providers(config, logger)
            else:
                return debug_mode(config, logger)
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

            return debug_mode(config, logger)

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


def show_config_info() -> int:
    """Show configuration file paths and status."""
    info = get_config_info()
    
    print("📁 SSHplex Configuration Information")
    print("=" * 50)
    print(f"Config Directory:    {info['default_config_path'].rsplit('/', 1)[0]}")
    print(f"Config File:         {info['default_config_path']}")
    print(f"Config Exists:       {'✅ Yes' if info['default_config_exists'] else '❌ No'}")
    print(f"Template File:       {info['template_path']}")
    print(f"Template Exists:     {'✅ Yes' if info['template_exists'] else '❌ No'}")
    print()
    
    if not info['default_config_exists']:
        print("💡 Run 'sshplex' to create a default configuration file")
    
    return 0


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
        
        print(f"{i}. {status_icon} {provider.name}")
        print(f"   Type: {provider.type}")
        
        if provider.type == "netbox" and provider.url:
            print(f"   URL:  {provider.url}")
        elif provider.type == "ansible" and provider.inventory_paths:
            print(f"   Paths: {', '.join(provider.inventory_paths)}")
        elif provider.type == "consul" and provider.config:
            print(f"   Host: {provider.config.host}:{provider.config.port}")
        elif provider.type == "static" and provider.hosts:
            print(f"   Hosts: {len(provider.hosts)} defined")
        
        print()
    
    return 0


def clear_cache(config: Any, logger: Any) -> int:
    """Clear the host cache."""
    logger.info("Clearing host cache")
    
    from .lib.cache import HostCache
    
    cache = HostCache(
        cache_dir=config.cache.cache_dir,
        cache_ttl_hours=config.cache.ttl_hours
    )
    
    cache_info = cache.get_cache_info()
    if cache_info:
        print(f"🗑️  Clearing cache ({cache_info.get('host_count', 0)} hosts, age: {cache_info.get('age_hours', 0):.1f}h)")
    else:
        print("🗑️  Clearing cache...")
    
    if cache.clear_cache():
        print("✅ Cache cleared successfully")
        return 0
    else:
        print("❌ Failed to clear cache")
        return 1


def debug_mode(config: Any, logger: Any) -> int:
    """Run debug mode - SoT provider connection and host listing test."""
    logger.info("Running CLI debug mode - SoT provider connectivity test")

    # Initialize SoT factory
    logger.info("Initializing SoT factory")
    sot_factory = SoTFactory(config)

    # Check cache status
    cache_info = sot_factory.get_cache_info()
    if cache_info:
        print(f"📦 Cache: {cache_info.get('host_count', 0)} hosts cached ({cache_info.get('age_hours', 0):.1f}h old)")

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
    print("\n✅ CLI debug mode completed successfully")
    print("Note: For the full TUI interface, run the main application")
    return 0


if __name__ == "__main__":
    sys.exit(main())
