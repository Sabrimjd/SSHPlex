#!/usr/bin/env python3
"""Main entry point for SSHplex TUI Application (pip-installed package)"""

import argparse
import shutil
import sys
from datetime import datetime
from typing import Any

from . import __version__
from .lib.config import get_config_info, load_config
from .lib.logger import get_logger, setup_logging
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
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description="SSHplex: Multiplex your SSH connections with style.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  sshplex                  Launch the TUI
  sshplex --debug          Run in debug mode
  sshplex --clear-cache    Clear the host cache
  sshplex --show-config    Show configuration paths
            """
        )
        parser.add_argument('--config', type=str, default=None, help='Path to the configuration file (default: ~/.config/sshplex/sshplex.yaml)')
        parser.add_argument('--version', action='version', version=f'SSHplex {__version__}')
        parser.add_argument('--debug', action='store_true', help='Run in debug mode (CLI only, no TUI)')
        parser.add_argument('--clear-cache', action='store_true', help='Clear the host cache before starting')
        parser.add_argument('--show-config', action='store_true', help='Show configuration paths and exit')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
        args = parser.parse_args()

        # Handle show-config without loading config
        if args.show_config:
            return show_config_info()

        # Check system dependencies (skip for debug/cache operations)
        if not args.debug and not args.clear_cache and not check_system_dependencies():
            return 1

        # Load configuration (will use default path if none specified)
        print("SSHplex - Loading configuration...")
        config = load_config(args.config)

        # Setup logging
        log_level = "DEBUG" if args.verbose else config.logging.level
        setup_logging(
            log_level=log_level,
            log_file=config.logging.file,
            enabled=config.logging.enabled or args.verbose
        )

        logger = get_logger()
        logger.info("SSHplex started")

        # Handle clear-cache
        if args.clear_cache:
            return clear_cache(config, logger)

        if args.debug:
            # Debug mode - simple provider test
            return debug_mode(config, logger)
        else:
            # TUI mode - main application
            return tui_mode(config, logger)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure config.yaml exists and is properly configured")
        print("Run 'sshplex --show-config' for configuration details")
        return 1
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Run 'sshplex --show-config' for configuration details")
        return 1
    except KeyboardInterrupt:
        print("\nSSHplex interrupted by user")
        return 130  # Standard exit code for SIGINT
    except RuntimeError as e:
        print(f"Runtime Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        # In debug mode, show full traceback
        if '--debug' in sys.argv or '-v' in sys.argv:
            import traceback
            traceback.print_exc()
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
        print("🗑️  No cache to clear")
        return 0
    
    if cache.clear_cache():
        print("✅ Cache cleared successfully")
        return 0
    else:
        print("❌ Failed to clear cache")
        return 1


def debug_mode(config: Any, logger: Any) -> int:
    """Run in debug mode - test all configured SoT providers."""
    logger.info("Running in debug mode - SoT provider connectivity test")

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

    logger.info("SSHplex debug mode completed successfully")
    print("\n✅ Debug mode completed successfully")
    return 0


def tui_mode(config: Any, logger: Any) -> int:
    """Run in TUI mode - interactive host selection with tmux panes."""
    logger.info("Starting TUI mode - interactive host selection with tmux integration")

    try:
        # Start the host selector TUI
        app = HostSelector(config=config)
        selected_hosts = app.run()

        if not selected_hosts:
            logger.info("No hosts selected, exiting")
            return 0

        logger.info(f"User selected {len(selected_hosts)} hosts for connection")

        use_panes = app.use_panes
        use_broadcast = app.use_broadcast
        mode_display = "panes" if use_panes else "windows"

        # Create connector and establish connections
        from .sshplex_connector import SSHplexConnector

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"sshplex-{timestamp}"
        connector = SSHplexConnector(session_name, config=config)

        if connector.connect_to_hosts(
            hosts=selected_hosts,
            username=config.ssh.username,
            key_path=config.ssh.key_path,
            port=config.ssh.port,
            use_panes=use_panes,
            use_broadcast=use_broadcast
        ):
            session_name = connector.get_session_name()
            logger.info(f"Successfully created tmux session '{session_name}' with {mode_display}")

            print("\nSSHplex Session Created Successfully!")
            print(f"tmux session: {session_name}")
            print(f"{len(selected_hosts)} SSH connections established in {mode_display}")
            broadcast_status = "ENABLED" if use_broadcast else "DISABLED"
            print(f"Broadcast mode: {broadcast_status}")
            print("\nAuto-attaching to session...")

            # Auto-attach to the session (this will replace the current process)
            connector.attach_to_session(auto_attach=True)
        else:
            logger.error("Failed to create SSH connections")
            print("Failed to create SSH connections")
            return 1

        return 0

    except Exception as e:
        logger.error(f"TUI error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
