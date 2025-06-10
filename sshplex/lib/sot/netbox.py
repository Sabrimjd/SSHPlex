"""NetBox Source of Truth provider for SSHplex."""

import pynetbox  # type: ignore
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
                    import urllib3  # type: ignore
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
        """Retrieve virtual machines and physical devices from NetBox.

        Args:
            filters: Optional filters to apply (status, role, etc.)

        Returns:
            List of Host objects
        """
        if not self.api:
            self.logger.error("NetBox API not connected. Call connect() first.")
            return []

        try:
            self.logger.info("Retrieving VMs and devices from NetBox")

            # Build filter parameters
            filter_params = {}
            if filters:
                filter_params.update(filters)
                self.logger.info(f"Applying filters: {filter_params}")

            hosts = []
            vm_count = 0
            device_count = 0

            # Get virtual machines
            self.logger.info("Querying virtual machines...")
            vms = list(self.api.virtualization.virtual_machines.filter(**filter_params))
            self.logger.info(f"Found {len(vms)} virtual machines")

            for vm in vms:
                host = self._process_vm(vm)
                if host:
                    hosts.append(host)
                    vm_count += 1

            # Get physical devices
            self.logger.info("Querying physical devices...")
            devices = list(self.api.dcim.devices.filter(**filter_params))
            self.logger.info(f"Found {len(devices)} physical devices")

            for device in devices:
                host = self._process_device(device)
                if host:
                    hosts.append(host)
                    device_count += 1

            self.logger.info(f"Retrieved {len(hosts)} total hosts from NetBox ({vm_count} VMs, {device_count} devices)")
            return hosts

        except Exception as e:
            self.logger.error(f"Failed to retrieve hosts from NetBox: {e}")
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

    def _process_vm(self, vm: Any) -> Optional[Host]:
        """Process a virtual machine object into a Host.

        Args:
            vm: NetBox VM object

        Returns:
            Host object or None if processing fails
        """
        try:
            # Extract VM details
            name = vm.name
            ip = self._get_primary_ip(vm)

            if not ip:
                self.logger.warning(f"VM {name} has no primary IP, skipping")
                return None

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
                platform="vm",  # Mark as virtual machine
                cluster=str(vm.cluster) if vm.cluster else "unknown",
                tags=tags,
                description=str(vm.description) if vm.description else "",
                provider=getattr(self, 'provider_name', 'netbox')
            )

            # Add source information to metadata
            host.metadata['sources'] = [getattr(self, 'provider_name', 'netbox')]
            host.metadata['provider'] = getattr(self, 'provider_name', 'netbox')

            self.logger.debug(f"Added VM host: {host}")
            return host

        except Exception as e:
            self.logger.error(f"Error processing VM {vm.name}: {e}")
            return None

    def _process_device(self, device: Any) -> Optional[Host]:
        """Process a physical device object into a Host.

        Args:
            device: NetBox device object

        Returns:
            Host object or None if processing fails
        """
        try:
            # Extract device details
            name = device.name
            ip = self._get_device_primary_ip(device)

            if not ip:
                self.logger.warning(f"Device {name} has no primary IP, skipping")
                return None

            # Get tags as a comma-separated string
            tags = ""
            if hasattr(device, 'tags') and device.tags:
                try:
                    tags = ", ".join([str(tag) for tag in device.tags])
                except Exception as e:
                    self.logger.debug(f"Error processing tags for device {name}: {e}")

            # Create host with metadata
            host = Host(
                name=name,
                ip=ip,
                status=str(device.status) if device.status else "unknown",
                role=str(device.role) if device.role else "unknown",
                platform=str(device.platform) if device.platform else "device",
                cluster=str(device.rack) if device.rack else "unknown",  # Use rack as cluster for devices
                tags=tags,
                description=str(device.comments) if device.comments else "",
                provider=getattr(self, 'provider_name', 'netbox')
            )

            # Add source information to metadata
            host.metadata['sources'] = [getattr(self, 'provider_name', 'netbox')]
            host.metadata['provider'] = getattr(self, 'provider_name', 'netbox')

            self.logger.debug(f"Added device host: {host}")
            return host

        except Exception as e:
            self.logger.error(f"Error processing device {device.name}: {e}")
            return None

    def _get_device_primary_ip(self, device: Any) -> Optional[str]:
        """Extract primary IP address from device object.

        Args:
            device: NetBox device object

        Returns:
            Primary IP address as string, or None if not found
        """
        try:
            if device.primary_ip4:
                # Remove CIDR notation if present
                ip = str(device.primary_ip4).split('/')[0]
                return ip
            elif device.primary_ip6:
                # Use IPv6 if no IPv4
                ip = str(device.primary_ip6).split('/')[0]
                return ip
            else:
                return None
        except Exception as e:
            self.logger.debug(f"Error extracting IP for device {device.name}: {e}")
            return None
