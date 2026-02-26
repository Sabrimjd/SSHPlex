"""iTerm2 integration utilities for SSHplex.

This module provides a unified interface for iTerm2 tmux integration,
handling AppleScript generation, session management, and error handling.
"""

import platform
import subprocess
import time

from ..logger import get_logger

# Constants
MACOS_PLATFORM = "darwin"
ITERM2_APP_NAME = "iTerm2"
TMUX_CONTROL_MODE_FLAG = "-CC"


class ITerm2Error(Exception):
    """Raised when iTerm2 operations fail."""
    pass


def is_macos() -> bool:
    """Check if running on macOS.

    Returns:
        True if on macOS, False otherwise
    """
    return platform.system().lower() == MACOS_PLATFORM


def check_iterm2_installed() -> bool:
    """Check if iTerm2 is installed on the system.

    Returns:
        True if iTerm2 is installed, False otherwise
    """
    if not is_macos():
        return False

    try:
        result = subprocess.run(
            ["osascript", "-e", f'exists application "{ITERM2_APP_NAME}"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and "true" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_iterm2_running() -> bool:
    """Check if iTerm2 is currently running.

    Returns:
        True if iTerm2 is running, False otherwise
    """
    if not is_macos():
        return False

    try:
        result = subprocess.run(
            ["osascript", "-e", f'application "{ITERM2_APP_NAME}" is running'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and "true" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def escape_applescript_string(value: str) -> str:
    """Escape a string for safe use in AppleScript.

    Args:
        value: The string to escape

    Returns:
        Escaped string safe for AppleScript
    """
    # Escape backslashes first, then quotes
    return value.replace('\\', '\\\\').replace('"', '\\"')


def generate_iterm2_applescript(
    session_name: str,
    target: str = "new-window",
    profile: str = "Default"
) -> str:
    """Generate AppleScript to launch iTerm2 with tmux -CC mode.

    Args:
        session_name: Name of the tmux session to attach to
        target: Where to open - "new-window" or "new-tab"
        profile: iTerm2 profile name to use

    Returns:
        AppleScript string

    Raises:
        ITerm2Error: If target is invalid
    """
    # Validate target
    valid_targets = ["new-window", "new-tab"]
    if target not in valid_targets:
        raise ITerm2Error(f"Invalid iTerm2 target: {target}. Must be one of: {valid_targets}")

    # Escape session name and profile for AppleScript
    safe_session = escape_applescript_string(session_name)
    safe_profile = escape_applescript_string(profile)

    if target == "new-window":
        # Create new iTerm2 window (activates iTerm2 if not running)
        apple_script = f'''
tell application "{ITERM2_APP_NAME}"
    activate
    create window with profile "{safe_profile}"
    tell current session of current window
        set name to "{safe_session}"
        write text "tmux {TMUX_CONTROL_MODE_FLAG} attach-session -t {safe_session}; exit"
    end tell
end tell
'''
    else:  # new-tab
        # Create new tab in current window, or new window if no windows exist
        # This handles both cases: iTerm2 running with windows, or not running/no windows
        apple_script = f'''
tell application "{ITERM2_APP_NAME}"
    activate
    if (count of windows) = 0 then
        -- No windows exist, create a new one
        create window with profile "{safe_profile}"
    else
        -- Window exists, create new tab
        tell current window
            create tab with profile "{safe_profile}"
        end tell
    end if
    tell current session of current window
        set name to "{safe_session}"
        write text "tmux {TMUX_CONTROL_MODE_FLAG} attach-session -t {safe_session}; exit"
    end tell
end tell
'''

    return apple_script.strip()


def launch_iterm2_session(
    session_name: str,
    target: str = "new-window",
    profile: str = "Default",
    fallback_to_standard: bool = True
) -> bool:
    """Launch iTerm2 with tmux -CC mode for the specified session.

    Args:
        session_name: Name of the tmux session to attach to
        target: Where to open - "new-window" or "new-tab"
        profile: iTerm2 profile name to use
        fallback_to_standard: If True, return False on failure instead of raising

    Returns:
        True if iTerm2 launched successfully, False otherwise

    Raises:
        ITerm2Error: If iTerm2 launch fails and fallback_to_standard is False
    """
    logger = get_logger()

    # Pre-flight checks
    if not is_macos():
        error_msg = "iTerm2 integration is only supported on macOS"
        if fallback_to_standard:
            logger.warning(error_msg)
            return False
        raise ITerm2Error(error_msg)

    if not check_iterm2_installed():
        error_msg = f"{ITERM2_APP_NAME} is not installed"
        if fallback_to_standard:
            logger.warning(error_msg)
            return False
        raise ITerm2Error(error_msg)

    # Generate AppleScript
    try:
        apple_script = generate_iterm2_applescript(session_name, target, profile)
    except ITerm2Error:
        raise
    except Exception as e:
        error_msg = f"Failed to generate AppleScript: {e}"
        if fallback_to_standard:
            logger.error(error_msg)
            return False
        raise ITerm2Error(error_msg) from e

    # Launch iTerm2 via osascript
    try:
        process = subprocess.Popen(
            ["osascript", "-e", apple_script],
            start_new_session=True,
            stderr=subprocess.PIPE
        )

        # Brief delay to check for immediate failures
        time.sleep(0.5)

        if process.poll() is not None:
            _, stderr = process.communicate()
            error_msg = f"Failed to launch {ITERM2_APP_NAME}: {stderr.decode().strip()}"
            if fallback_to_standard:
                logger.error(error_msg)
                return False
            raise ITerm2Error(error_msg)

        logger.info(f"SSHplex: Launched {ITERM2_APP_NAME} with tmux session '{session_name}'")
        print(f"🚀 {ITERM2_APP_NAME} launched with tmux session: {session_name}")
        return True

    except FileNotFoundError:
        error_msg = "osascript not found - iTerm2 integration requires macOS"
        if fallback_to_standard:
            logger.error(error_msg)
            return False
        raise ITerm2Error(error_msg) from None
    except Exception as e:
        error_msg = f"Failed to launch {ITERM2_APP_NAME}: {e}"
        if fallback_to_standard:
            logger.error(error_msg)
            return False
        raise ITerm2Error(error_msg) from e


def get_iterm2_status() -> dict:
    """Get iTerm2 installation and running status.

    Returns:
        Dict with 'installed', 'running', and 'platform' keys
    """
    return {
        "platform": platform.system().lower(),
        "is_macos": is_macos(),
        "installed": check_iterm2_installed(),
        "running": check_iterm2_running(),
    }
