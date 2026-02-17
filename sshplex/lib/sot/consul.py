"""Consul host list Source of Truth provider for SSHplex."""

from typing import List, Dict, Any, Optional
from ..logger import get_logger
from .base import SoTProvider, Host


class ConsulProvider(SoTProvider):
    """Consul host list implementation of SoT provider."""

    def __init__(self, import_config: Any) -> None:
        """Initialize Consul provider.

        Args:
            import_config: Import configuration object containing Consul settings
        """
        self.consetup = import_config
        self.filters = self.consetup.default_filters or {}
        self.logger = get_logger()
        self.name = import_config.name
        self.api = None

    def connect(self) -> bool:
        """Establish connection to Consul API.

        Returns:
            True if connection was established successfully, False otherwise
        """
        try:
            import consul
        except ImportError:
            self.logger.error(
                "python-consul2 is required for the Consul provider. "
                "Install it with: pip install 'sshplex[consul]' or pip install python-consul2. "
                "See https://python-consul2.readthedocs.io/en/latest/"
            )
            return False

        try:
            self.api = consul.Consul(
                host=self.consetup.config.host,
                port=self.consetup.config.port,
                token=self.consetup.config.token,
                scheme=self.consetup.config.scheme,
                verify=self.consetup.config.verify,
                dc=self.consetup.config.dc,
                cert=self.consetup.config.cert,
            )
            self.logger.debug(f"Consul provider '{self.consetup.name}' - connection established")
            return True

        except Exception as e:
            self.logger.error(f"Consul inventory loading failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test Consul provider connectivity by checking cluster leader status.

        Returns:
            True if a Consul leader is available, False otherwise
        """
        if self.api is None:
            self.logger.error("Consul API not initialized - call connect() first")
            return False

        try:
            leader = self.api.status.leader()
            return bool(leader)
        except Exception as e:
            self.logger.error(f"Consul connection test failed: {e}")
            return False

    def get_hosts(self, filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Retrieve hosts from Consul catalog.

        Args:
            filters: Optional filters to apply (tags, name patterns, etc.)

        Returns:
            List of Host objects from Consul catalog
        """
        hosts = []

        if self.api is None:
            self.logger.error("Consul API not initialized - call connect() first")
            return hosts

        try:
            nodes = self.api.catalog.nodes(dc=self.consetup.config.dc)[1]

            for host_data in nodes:
                name = host_data['Node']
                ip = host_data['Address']

                kwargs = {k: v for k, v in host_data['Meta'].items()}
                kwargs['provider'] = self.name

                host = Host(name=name, ip=ip, **kwargs)

                host.metadata['sources'] = [self.name]
                host.metadata['provider'] = self.name

                hosts.append(host)

            # Apply filters if provided
            active_filters = filters or self.filters
            if active_filters:
                hosts = self._apply_filters(hosts, active_filters)

        except Exception as e:
            self.logger.error(f"Consul get_hosts failed: {e}")
            return hosts

        self.logger.info(f"Consul provider '{self.name}' returned {len(hosts)} hosts")
        return hosts

    def _apply_filters(self, hosts: List[Host], filters: Dict[str, Any]) -> List[Host]:
        """Apply filters to the host list.

        Args:
            hosts: List of Host objects to filter
            filters: Dictionary of filter criteria

        Returns:
            Filtered list of Host objects
        """
        filtered = hosts

        for key, value in filters.items():
            if key == "name_pattern":
                import fnmatch
                filtered = [h for h in filtered if fnmatch.fnmatch(h.name, value)]
            elif key == "tags":
                if isinstance(value, list):
                    filtered = [
                        h for h in filtered
                        if any(tag in (getattr(h, 'tags', []) or []) for tag in value)
                    ]
            else:
                filtered = [
                    h for h in filtered
                    if getattr(h, key, h.metadata.get(key)) == value
                ]

        return filtered
