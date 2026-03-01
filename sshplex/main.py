#!/usr/bin/env python3
"""Main entry point for SSHplex TUI Application (pip-installed package)"""

import argparse
import shutil
import sys
from datetime import datetime
from typing import Any, Optional

from . import __version__
from .lib.commands import clear_cache, run_debug_mode, show_config_info
from .lib.config import load_config
from .lib.logger import get_logger, setup_logging
from .lib.onboarding import OnboardingWizard
from .lib.ui.host_selector import HostSelector


def check_system_dependencies(config: Any) -> bool:
    """Check if required system dependencies are available."""
    backend = str(getattr(getattr(config, "tmux", None), "backend", "tmux") or "tmux")
    if backend == "iterm2-native":
        return True

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


def run_onboarding(config_path: Optional[str] = None) -> int:
    """Run the interactive onboarding wizard."""
    try:
        from pathlib import Path
        path = Path(config_path) if config_path else None
        wizard = OnboardingWizard(config_path=path)
        success = wizard.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nOnboarding cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Onboarding failed: {e}")
        return 1


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
        parser.add_argument('--onboarding', action='store_true', help='Run the interactive setup wizard')
        parser.add_argument('--clear-cache', action='store_true', help='Clear the host cache before starting')
        parser.add_argument('--show-config', action='store_true', help='Show configuration paths and exit')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
        args = parser.parse_args()

        # Handle show-config without loading config
        if args.show_config:
            return show_config_info()

        # Handle onboarding wizard
        if args.onboarding:
            return run_onboarding(args.config)

        # Load configuration (will use default path if none specified)
        print("SSHplex - Loading configuration...")
        config = load_config(args.config)

        # Check system dependencies (skip for debug/cache operations)
        if not args.debug and not args.clear_cache and not check_system_dependencies(config):
            return 1

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
            return run_debug_mode(config, logger)
        else:
            # TUI mode - main application
            return tui_mode(config, logger, args.config)

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


def tui_mode(config: Any, logger: Any, config_path: Optional[str] = None) -> int:
    """Run in TUI mode for interactive host selection and connection."""
    logger.info("Starting TUI mode - interactive host selection")

    try:
        # Start the host selector TUI
        app = HostSelector(config=config, config_path=config_path or "")
        selected_hosts = app.run()

        if not selected_hosts:
            created_native = getattr(app, "native_sessions_created_count", 0)
            if created_native:
                logger.info(f"Exited TUI after creating {created_native} iTerm2 native session(s)")
                return 0

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
            connected_count = connector.last_success_count
            selected_count = len(selected_hosts)
            logger.info(f"Successfully created tmux session '{session_name}' with {mode_display}")

            print("\nSSHplex Session Created Successfully!")
            print(f"tmux session: {session_name}")
            print(f"{connected_count}/{selected_count} SSH connections established in {mode_display}")
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
