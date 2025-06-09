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
from .sshplex_connector import SSHplexConnector


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
        result = app.run()

        # Log the settings and selection results
        mode = "Panes" if app.use_panes else "Tabs"
        broadcast = "ON" if app.use_broadcast else "OFF"
        logger.info(f"SSHplex settings - Mode: {mode}, Broadcast: {broadcast}")

        # The app.run() may return None or a list of hosts
        if isinstance(result, list) and len(result) > 0:
            logger.info(f"User selected {len(result)} hosts for connection")
            for host in result:
                logger.info(f"  - {host.name} ({host.ip})")

            # Create tmux panes or windows for selected hosts
            mode = "panes" if app.use_panes else "windows"
            logger.info(f"SSHplex: Creating tmux {mode} for selected hosts")

            # Create connector with timestamped session name and max panes per window
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"
            max_panes_per_window = config.tmux.max_panes_per_window
            connector = SSHplexConnector(session_name, max_panes_per_window)

            # Connect to hosts (creates panes or windows with SSH connections)
            if connector.connect_to_hosts(
                hosts=result,
                username=config.ssh.username,
                key_path=config.ssh.key_path,
                port=config.ssh.port,
                use_panes=app.use_panes,
                use_broadcast=app.use_broadcast
            ):
                session_name = connector.get_session_name()
                mode_display = "panes" if app.use_panes else "windows"
                logger.info(f"SSHplex: Successfully created tmux session '{session_name}' with {mode_display}")
                logger.info(f"SSHplex: {len(result)} SSH connections established")

                # Display success message and auto-attach
                print(f"\n✅ SSHplex Session Created Successfully!")
                print(f"📡 tmux session: {session_name}")
                print(f"🔗 {len(result)} SSH connections established in {mode_display}")
                broadcast_status = " (ENABLED)" if app.use_broadcast else " (DISABLED)"
                print(f"📢 Broadcast mode: {broadcast_status}")
                print(f"\n🚀 Auto-attaching to session...")
                print(f"\n⚡ tmux commands (once attached):")
                if app.use_panes:
                    print(f"   - Switch panes: Ctrl+b then arrow keys")
                else:
                    print(f"   - Switch windows: Ctrl+b then n/p or number keys")
                print(f"   - Toggle broadcast: Ctrl+b then b")
                print(f"   - Detach session: Ctrl+b then d")
                print(f"   - List sessions: tmux list-sessions")

                # Auto-attach to the session (this will replace the current process)
                connector.attach_to_session(auto_attach=True)

            else:
                logger.error("SSHplex: Failed to create SSH connections")
                return 1

        else:
            logger.info("No hosts were selected")

        return 0

    except Exception as e:
        logger.error(f"TUI error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
