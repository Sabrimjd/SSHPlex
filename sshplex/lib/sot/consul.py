"""consul host list Source of Truth provider for SSHplex."""

from typing import List, Dict, Any, Optional
from ..logger import get_logger
from .base import SoTProvider, Host
import sys
try:
    import consul
except ImportError:
    sys.exit(
        """failed=True msg='python-consul2 required for this module.
See https://python-consul2.readthedocs.io/en/latest/'"""
    )

class ConsulProvider(SoTProvider):
    """consul host list implementation of SoT provider."""

    def __init__(self, import_config: Any) -> None:
        """Initialize consul provider.

        Args:
            config: Configuration
        """
        self.consetup = import_config
        self.filters = self.consetup.default_filters or {}
        self.logger = get_logger()
        self.name = import_config.name

    def connect(self) -> bool:
        """consul api connection.

        Returns:
            True if all inventories loaded successfully, False otherwise
        """
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
          self.logger.debug(f"consul provider '{self.consetup.name}' - connection established")
          return True

        except Exception as e:
            self.logger.error(f"Consul inventory loading failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test consul provider status.

        Returns:
            Always True since consul data is always available
        """
        leader = self.api.status.leader()
        return bool(leader)

    def get_hosts(self, filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Retrieve hosts from consul configuration.

        Args:
            filters: Optional filters to apply (tags, name patterns, etc.)

        Returns:
            List of Host objects from consul configuration
        """
        hosts = []

        try:
          nodes = self.api.catalog.nodes(dc=self.consetup.config.dc)[1]

          for host_data in nodes:
            # Extract name and ip, create kwargs from remaining data
            name = host_data['Node']
            ip = host_data['Address']

            # Create kwargs with remaining host data
            kwargs = {k: v for k, v in host_data['Meta'].items()}
            kwargs['provider'] = self.name

            # Create host object
            host = Host(name=name, ip=ip, **kwargs)

            # Add source information to metadata
            host.metadata['sources'] = [self.name]
            host.metadata['provider'] = self.name

            hosts.append(host)

          # TODO: Apply filters if provided

        except Exception as e:
            self.logger.error(f"Consul get_hosts failed: {e}")
            return hosts

        self.logger.info(f"consul provider '{self.name}' returned {len(hosts)} hosts")
        return hosts
