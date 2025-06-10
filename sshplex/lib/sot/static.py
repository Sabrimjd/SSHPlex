"""Static host list Source of Truth provider for SSHplex."""

from typing import List, Dict, Any, Optional
from ..logger import get_logger
from .base import SoTProvider, Host


class StaticProvider(SoTProvider):
    """Static host list implementation of SoT provider."""

    def __init__(self, name: str, hosts: List[Dict[str, Any]]) -> None:
        """Initialize static provider.

        Args:
            name: Name of this provider instance
            hosts: List of host dictionaries
        """
        self.name = name
        self.hosts_data = hosts
        self.logger = get_logger()

    def connect(self) -> bool:
        """Static provider doesn't need connection.

        Returns:
            Always True since static data is always available
        """
        self.logger.debug(f"Static provider '{self.name}' - connection established")
        return True

    def test_connection(self) -> bool:
        """Test static provider status.

        Returns:
            Always True since static data is always available
        """
        return True

    def get_hosts(self, filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Retrieve hosts from static configuration.

        Args:
            filters: Optional filters to apply (tags, name patterns, etc.)

        Returns:
            List of Host objects from static configuration
        """
        hosts = []

        for host_data in self.hosts_data:
            # Extract name and ip, create kwargs from remaining data
            name = host_data['name']
            ip = host_data['ip']

            # Create kwargs with remaining host data (excluding name and ip)
            kwargs = {k: v for k, v in host_data.items() if k not in ['name', 'ip']}
            kwargs['provider'] = self.name

            # Create host object
            host = Host(name=name, ip=ip, **kwargs)

            # Add source information to metadata
            host.metadata['sources'] = [self.name]
            host.metadata['provider'] = self.name

            hosts.append(host)

        # Apply filters if provided
        if filters:
            hosts = self._apply_filters(hosts, filters)

        self.logger.info(f"Static provider '{self.name}' returned {len(hosts)} hosts")
        return hosts

    def _apply_filters(self, hosts: List[Host], filters: Dict[str, Any]) -> List[Host]:
        """Apply filters to host list.

        Args:
            hosts: List of hosts to filter
            filters: Filters to apply

        Returns:
            Filtered list of hosts
        """
        filtered_hosts = hosts

        # Filter by tags
        if 'tags' in filters and filters['tags']:
            required_tags = filters['tags']
            if isinstance(required_tags, str):
                required_tags = [required_tags]

            filtered_hosts = [
                host for host in filtered_hosts
                if any(tag in getattr(host, 'tags', []) for tag in required_tags)
            ]

        # Filter by name pattern
        if 'name_pattern' in filters and filters['name_pattern']:
            import re
            pattern = re.compile(filters['name_pattern'], re.IGNORECASE)
            filtered_hosts = [
                host for host in filtered_hosts
                if pattern.search(host.name)
            ]

        # Filter by description pattern
        if 'description_pattern' in filters and filters['description_pattern']:
            import re
            pattern = re.compile(filters['description_pattern'], re.IGNORECASE)
            filtered_hosts = [
                host for host in filtered_hosts
                if pattern.search(getattr(host, 'description', ''))
            ]

        self.logger.debug(f"Static provider '{self.name}' filtered from {len(hosts)} to {len(filtered_hosts)} hosts")
        return filtered_hosts
