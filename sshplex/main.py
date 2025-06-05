"""Main entry point for SSHplex TUI Application (pip-installed package)"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

from .lib.config import load_config
from .lib.logger import setup_logging, get_logger
from .lib.sot.netbox import NetBoxProvider
from .lib.ui.host_selector import HostSelector
from .sshplex_connector import SSHplexConnector


def main():
    """Main entry point for SSHplex TUI Application."""

    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="SSHplex: Multiplex your SSH connections with style.")
        parser.add_argument('--config', type=str, default=None, help='Path to the configuration file (default: ~/.config/sshplex/sshplex.yaml)')
        parser.add_argument('--version', action='version', version='SSHplex 1.0.0')
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


def debug_mode(config, logger):
    """Run in debug mode - simple NetBox connection test."""
    logger.info("Running in debug mode - NetBox connectivity test")

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

    logger.info("SSHplex debug mode completed successfully")
    print(f"\n✅ Debug mode completed successfully")
    return 0


def tui_mode(config, logger):
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

            # Create connector with timestamped session name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"sshplex-{timestamp}"
            connector = SSHplexConnector(session_name)

            # Connect to hosts (creates panes or windows with SSH connections)
            if connector.connect_to_hosts(
                hosts=result,
                username=config.ssh.username,
                key_path=config.ssh.key_path,
                port=config.ssh.port,
                use_panes=app.use_panes
            ):
                session_name = connector.get_session_name()
                mode_display = "panes" if app.use_panes else "windows"
                logger.info(f"SSHplex: Successfully created tmux session '{session_name}' with {mode_display}")
                logger.info(f"SSHplex: {len(result)} SSH connections established")

                # Display success message and auto-attach
                print(f"\n✅ SSHplex Session Created Successfully!")
                print(f"📡 tmux session: {session_name}")
                print(f"🔗 {len(result)} SSH connections established in {mode_display}")
                print(f"\n🚀 Auto-attaching to session...")
                print(f"\n⚡ tmux commands (once attached):")
                if app.use_panes:
                    print(f"   - Switch panes: Ctrl+b then arrow keys")
                else:
                    print(f"   - Switch windows: Ctrl+b then n/p or number keys")
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
