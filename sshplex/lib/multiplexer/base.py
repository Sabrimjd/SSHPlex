"""Base class for terminal multiplexers in SSHplex."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class MultiplexerBase(ABC):
    """Abstract base class for terminal multiplexers."""

    def __init__(self, session_name: str):
        """Initialize the multiplexer with a session name."""
        self.session_name = session_name
        self.panes: Dict[str, Any] = {}

    @abstractmethod
    def create_session(self) -> bool:
        """Create a new multiplexer session."""
        pass

    @abstractmethod
    def create_pane(self, hostname: str, command: Optional[str] = None) -> bool:
        """Create a new pane for the given hostname."""
        pass

    @abstractmethod
    def set_pane_title(self, pane_id: str, title: str) -> bool:
        """Set the title of a specific pane."""
        pass

    @abstractmethod
    def send_command(self, pane_id: str, command: str) -> bool:
        """Send a command to a specific pane."""
        pass

    @abstractmethod
    def broadcast_command(self, command: str) -> bool:
        """Send a command to all panes."""
        pass

    @abstractmethod
    def close_session(self) -> None:
        """Close the multiplexer session."""
        pass

    @abstractmethod
    def attach_to_session(self) -> None:
        """Attach to the multiplexer session."""
        pass
