"""NetBox Source of Truth provider for SSHplex."""

import pynetbox
from typing import List, Dict, Any, Optional
from ..logger import get_logger
from .base import SoTProvider, Host


class NetBoxProvider(SoTProvider):
    """NetBox implementation of SoT provider."""

    def __init__(self, url: str, token: str, verify_ssl: bool = True, timeout: int = 30) -> None:
        """Initialize NetBox provider.

        Args:
            url: NetBox instance URL
            token: API token for authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.url = url
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.api: Optional[Any] = None
        self.logger = get_logger()

    def connect(self) -> bool:
        """Establish connection to NetBox API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to NetBox at {self.url}")

            self.api = pynetbox.api(
                url=self.url,
                token=self.token
            )

            # Configure SSL verification and timeout
            if self.api is not None:
                self.api.http_session.verify = self.verify_ssl
                self.api.http_session.timeout = self.timeout

            # Log SSL verification status
            if not self.verify_ssl:
                self.logger.warning("SSL certificate verification is DISABLED")
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                except ImportError:
                    pass  # urllib3 not available, continue anyway

            # Test the connection
            if self.test_connection():
                self.logger.info("Successfully connected to NetBox")
                return True
            else:
                self.logger.error("Failed to establish NetBox connection")
                return False

        except Exception as e:
            self.logger.error(f"NetBox connection failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to NetBox API.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.api:
                return False

            # Try to get NetBox status
            status = self.api.status()
            self.logger.debug(f"NetBox status: {status}")
            return True

        except Exception as e:
            self.logger.error(f"NetBox connection test failed: {e}")
            return False

    def get_hosts(self, filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Retrieve virtual machines from NetBox.

        Args:
            filters: Optional filters to apply (status, role, etc.)

        Returns:
            List of Host objects
        """
        if not self.api:
            self.logger.error("NetBox API not connected. Call connect() first.")
            return []

        try:
            self.logger.info("Retrieving VMs from NetBox")

            # Build filter parameters
            filter_params = {}
            if filters:
                filter_params.update(filters)
                self.logger.info(f"Applying filters: {filter_params}")

            # Get virtual machines
            vms = list(self.api.virtualization.virtual_machines.filter(**filter_params))

            hosts = []
            for vm in vms:
                # Extract VM details
                name = vm.name
                ip = self._get_primary_ip(vm)

                if not ip:
                    self.logger.warning(f"VM {name} has no primary IP, skipping")
                    continue

                # Get tags as a comma-separated string
                tags = ""
                if hasattr(vm, 'tags') and vm.tags:
                    try:
                        tags = ", ".join([str(tag) for tag in vm.tags])
                    except Exception as e:
                        self.logger.debug(f"Error processing tags for VM {name}: {e}")

                # Create host with metadata
                host = Host(
                    name=name,
                    ip=ip,
                    status=str(vm.status) if vm.status else "unknown",
                    role=str(vm.role) if vm.role else "unknown",
                    platform=str(vm.platform) if vm.platform else "unknown",
                    cluster=str(vm.cluster) if vm.cluster else "unknown",
                    tags=tags,
                    description=str(vm.description) if vm.description else ""
                )

                hosts.append(host)
                self.logger.debug(f"Added host: {host}")

            self.logger.info(f"Retrieved {len(hosts)} VMs from NetBox")
            return hosts

        except Exception as e:
            self.logger.error(f"Failed to retrieve VMs from NetBox: {e}")
            return []

    def _get_primary_ip(self, vm: Any) -> Optional[str]:
        """Extract primary IP address from VM object.

        Args:
            vm: NetBox VM object

        Returns:
            Primary IP address as string, or None if not found
        """
        try:
            if vm.primary_ip4:
                # Remove CIDR notation if present
                ip = str(vm.primary_ip4).split('/')[0]
                return ip
            elif vm.primary_ip6:
                # Use IPv6 if no IPv4
                ip = str(vm.primary_ip6).split('/')[0]
                return ip
            else:
                return None
        except Exception as e:
            self.logger.debug(f"Error extracting IP for VM {vm.name}: {e}")
            return None
