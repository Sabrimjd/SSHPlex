"""Tests for SSHplex NetBox provider."""

import pytest
from unittest.mock import MagicMock, patch

from sshplex.lib.sot.netbox import NetBoxProvider


class TestNetBoxProvider:
    """Tests for NetBoxProvider class."""

    @pytest.fixture
    def mock_pynetbox(self):
        """Mock pynetbox module."""
        with patch('sshplex.lib.sot.netbox.pynetbox') as mock:
            yield mock

    @pytest.fixture
    def mock_vm(self):
        """Create a mock NetBox VM object."""
        vm = MagicMock()
        vm.name = 'test-vm-01'
        vm.primary_ip4 = '10.0.1.1/24'
        vm.primary_ip6 = None
        vm.status = 'active'
        vm.role = 'server'
        vm.cluster = 'test-cluster'
        vm.tags = ['web', 'prod']
        vm.description = 'Test VM description'
        return vm

    @pytest.fixture
    def mock_device(self):
        """Create a mock NetBox device object."""
        device = MagicMock()
        device.name = 'test-device-01'
        device.primary_ip4 = '10.0.2.1/24'
        device.primary_ip6 = None
        device.status = 'active'
        device.role = 'router'
        device.platform = 'ios'
        device.rack = 'rack-01'
        device.comments = 'Test device'
        device.tags = ['network', 'prod']
        return device

    @pytest.fixture
    def provider(self):
        """Create a NetBoxProvider instance."""
        return NetBoxProvider(
            url='https://netbox.example.com',
            token='test-token',
            verify_ssl=False,
            timeout=30
        )

    def test_init(self):
        """Test provider initialization."""
        provider = NetBoxProvider(
            url='https://netbox.example.com',
            token='test-token'
        )
        assert provider.url == 'https://netbox.example.com'
        assert provider.token == 'test-token'
        assert provider.verify_ssl is True
        assert provider.timeout == 30

    def test_connect_success(self, provider, mock_pynetbox):
        """Test successful connection to NetBox."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_pynetbox.api.return_value = mock_api
        
        result = provider.connect()
        
        assert result is True
        mock_pynetbox.api.assert_called_once()

    def test_connect_failure(self, provider, mock_pynetbox):
        """Test connection failure."""
        mock_pynetbox.api.side_effect = Exception('Connection failed')
        
        result = provider.connect()
        
        assert result is False

    def test_test_connection_success(self, provider, mock_pynetbox):
        """Test connection test when connected."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        result = provider.test_connection()
        
        assert result is True

    def test_test_connection_not_connected(self, provider):
        """Test connection test when not connected."""
        result = provider.test_connection()
        assert result is False

    def test_get_hosts_no_connection(self, provider):
        """Test get_hosts without connection."""
        hosts = provider.get_hosts()
        assert hosts == []

    def test_get_hosts_vms_only(self, provider, mock_pynetbox, mock_vm):
        """Test getting only VMs from NetBox."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 1
        assert hosts[0].name == 'test-vm-01'
        assert hosts[0].ip == '10.0.1.1'

    def test_get_hosts_devices_only(self, provider, mock_pynetbox, mock_device):
        """Test getting only devices from NetBox."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = []
        mock_api.dcim.devices.filter.return_value = [mock_device]
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 1
        assert hosts[0].name == 'test-device-01'
        assert hosts[0].ip == '10.0.2.1'

    def test_get_hosts_both(self, provider, mock_pynetbox, mock_vm, mock_device):
        """Test getting both VMs and devices."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = [mock_device]
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 2

    def test_get_hosts_with_filters(self, provider, mock_pynetbox, mock_vm):
        """Test getting hosts with filters."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts(filters={'status': 'active', 'role': 'server'})
        
        # Verify filter was passed and hosts returned
        mock_api.virtualization.virtual_machines.filter.assert_called()
        assert len(hosts) == 1

    def test_vm_without_ip_skipped(self, provider, mock_pynetbox):
        """Test that VMs without IP are skipped."""
        mock_vm = MagicMock()
        mock_vm.name = 'no-ip-vm'
        mock_vm.primary_ip4 = None
        mock_vm.primary_ip6 = None
        
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 0

    def test_ipv6_fallback(self, provider, mock_pynetbox):
        """Test IPv6 fallback when no IPv4."""
        mock_vm = MagicMock()
        mock_vm.name = 'ipv6-vm'
        mock_vm.primary_ip4 = None
        mock_vm.primary_ip6 = '2001:db8::1/64'
        mock_vm.status = 'active'
        mock_vm.role = 'server'
        mock_vm.cluster = 'cluster'
        mock_vm.tags = []
        mock_vm.description = ''
        
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 1
        assert hosts[0].ip == '2001:db8::1'

    def test_ip_cidr_removed(self, provider, mock_pynetbox, mock_vm):
        """Test that CIDR notation is removed from IP."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        # IP should not contain CIDR
        assert '/' not in hosts[0].ip

    def test_host_metadata(self, provider, mock_pynetbox, mock_vm):
        """Test that host metadata is populated."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        host = hosts[0]
        assert host.status == 'active'
        assert host.role == 'server'
        assert host.cluster == 'test-cluster'
        assert 'provider' in host.metadata

    def test_provider_name_attribute(self, provider, mock_pynetbox, mock_vm):
        """Test that provider_name is used in host metadata."""
        setattr(provider, 'provider_name', 'custom-netbox')
        
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
        mock_api.dcim.devices.filter.return_value = []
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        assert hosts[0].metadata.get('provider') == 'custom-netbox'

    def test_ssl_verification_disabled(self, mock_pynetbox):
        """Test that SSL verification can be disabled."""
        provider = NetBoxProvider(
            url='https://netbox.example.com',
            token='test-token',
            verify_ssl=False
        )
        
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        
        # Verify SSL verification was disabled
        assert mock_api.http_session.verify is False

    def test_timeout_configuration(self, mock_pynetbox):
        """Test that timeout is configured."""
        provider = NetBoxProvider(
            url='https://netbox.example.com',
            token='test-token',
            timeout=60
        )
        
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        
        assert mock_api.http_session.timeout == 60

    def test_error_handling_in_get_hosts(self, provider, mock_pynetbox):
        """Test error handling in get_hosts."""
        mock_api = MagicMock()
        mock_api.status.return_value = {'version': '3.5.0'}
        mock_api.virtualization.virtual_machines.filter.side_effect = Exception('API error')
        mock_pynetbox.api.return_value = mock_api
        
        provider.connect()
        hosts = provider.get_hosts()
        
        # Should return empty list on error
        assert hosts == []
