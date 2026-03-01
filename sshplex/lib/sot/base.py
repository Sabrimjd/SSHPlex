"""Base classes for Source of Truth providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Host:
    """Simple host data structure."""

    _RESERVED_METADATA_KEYS = {"name", "ip", "metadata"}

    def __init__(
        self,
        name: str,
        ip: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.ip = ip
        self.metadata: Dict[str, Any] = {}

        if metadata:
            self.update_metadata(metadata)
        if kwargs:
            self.update_metadata(kwargs)

    def update_metadata(self, values: Dict[str, Any]) -> None:
        """Merge metadata values and mirror them as instance attributes."""
        for raw_key, value in values.items():
            key = str(raw_key)
            if key in self._RESERVED_METADATA_KEYS:
                continue
            self.metadata[key] = value
            setattr(self, key, value)

    def merge_metadata(self, values: Dict[str, Any]) -> None:
        """Compatibility helper to merge metadata values in-place."""
        self.update_metadata(values)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize host object to cache-friendly dictionary."""
        return {
            "name": self.name,
            "ip": self.ip,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Host":
        """Create host object from serialized dictionary payload."""
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        extras = {
            key: value
            for key, value in payload.items()
            if key not in cls._RESERVED_METADATA_KEYS
        }
        merged_metadata = dict(metadata)
        merged_metadata.update(extras)

        return cls(
            name=str(payload["name"]),
            ip=str(payload["ip"]),
            metadata=merged_metadata,
        )

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
