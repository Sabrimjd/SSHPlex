"""Base classes for Source of Truth providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class Host:
    """Simple host data structure."""

    def __init__(self, name: str, ip: str, **kwargs: Any) -> None:
        self.name = name
        self.ip = ip
        self.metadata = kwargs

        # Set additional attributes from kwargs for easy access
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        return f"{self.name} ({self.ip})"

    def __repr__(self) -> str:
        return f"Host(name='{self.name}', ip='{self.ip}')"


class SoTProvider(ABC):
    """Abstract base class for Source of Truth providers."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the SoT provider.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def get_hosts(self, filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Retrieve hosts from the SoT provider.

        Args:
            filters: Optional filters to apply

        Returns:
            List of Host objects
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to the SoT provider.

        Returns:
            True if connection is healthy, False otherwise
        """
        pass
