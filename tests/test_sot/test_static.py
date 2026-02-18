"""Tests for SSHplex static host provider."""

import pytest

from sshplex.lib.sot.base import Host
from sshplex.lib.sot.static import StaticProvider


class TestStaticProvider:
    """Tests for StaticProvider class."""

    @pytest.fixture
    def sample_hosts(self):
        """Sample host data for testing."""
        return [
            {'name': 'web-01', 'ip': '10.0.1.10', 'description': 'Web server', 'tags': ['web', 'prod']},
            {'name': 'db-01', 'ip': '10.0.1.20', 'description': 'Database server', 'tags': ['db', 'prod']},
            {'name': 'cache-01', 'ip': '10.0.1.30', 'description': 'Cache server', 'tags': ['cache', 'prod']},
        ]

    @pytest.fixture
    def provider(self, sample_hosts):
        """Create a StaticProvider instance."""
        return StaticProvider(name='test-static', hosts=sample_hosts)

    def test_init(self, sample_hosts):
        """Test provider initialization."""
        provider = StaticProvider(name='test', hosts=sample_hosts)
        assert provider.name == 'test'
        assert len(provider.hosts_data) == 3

    def test_connect(self, provider):
        """Test connect method (always returns True for static)."""
        assert provider.connect() is True

    def test_test_connection(self, provider):
        """Test test_connection method (always returns True for static)."""
        assert provider.test_connection() is True

    def test_get_hosts_no_filter(self, provider):
        """Test getting hosts without filters."""
        hosts = provider.get_hosts()
        assert len(hosts) == 3
        assert all(isinstance(h, Host) for h in hosts)
        
        # Verify host data
        assert hosts[0].name == 'web-01'
        assert hosts[0].ip == '10.0.1.10'
        assert hosts[0].description == 'Web server'

    def test_get_hosts_with_metadata(self, provider):
        """Test that host metadata is populated correctly."""
        hosts = provider.get_hosts()
        
        for host in hosts:
            assert 'provider' in host.metadata
            assert host.metadata['provider'] == 'test-static'
            assert 'sources' in host.metadata

    def test_get_hosts_empty_list(self):
        """Test provider with empty host list."""
        provider = StaticProvider(name='empty', hosts=[])
        hosts = provider.get_hosts()
        assert hosts == []

    def test_filter_by_tags(self, provider):
        """Test filtering hosts by tags."""
        hosts = provider.get_hosts(filters={'tags': 'web'})
        assert len(hosts) == 1
        assert hosts[0].name == 'web-01'

    def test_filter_by_tags_list(self, provider):
        """Test filtering hosts by multiple tags."""
        hosts = provider.get_hosts(filters={'tags': ['web', 'db']})
        assert len(hosts) == 2

    def test_filter_by_name_pattern(self, provider):
        """Test filtering hosts by name pattern."""
        hosts = provider.get_hosts(filters={'name_pattern': r'^web-.*$'})
        assert len(hosts) == 1
        assert hosts[0].name == 'web-01'

    def test_filter_by_description_pattern(self, provider):
        """Test filtering hosts by description pattern."""
        hosts = provider.get_hosts(filters={'description_pattern': 'server'})
        assert len(hosts) == 3  # All have "server" in description

    def test_filter_no_matches(self, provider):
        """Test filter that matches nothing."""
        hosts = provider.get_hosts(filters={'tags': 'nonexistent'})
        assert len(hosts) == 0

    def test_host_attributes(self, provider):
        """Test that host attributes are accessible."""
        hosts = provider.get_hosts()
        host = hosts[0]
        
        assert host.name == 'web-01'
        assert host.ip == '10.0.1.10'
        assert host.description == 'Web server'
        assert hasattr(host, 'tags')

    def test_host_with_extra_fields(self):
        """Test hosts with additional custom fields."""
        hosts_data = [
            {'name': 'host1', 'ip': '10.0.0.1', 'custom_field': 'value1', 'port': 2222}
        ]
        provider = StaticProvider(name='custom', hosts=hosts_data)
        hosts = provider.get_hosts()
        
        assert hosts[0].metadata.get('custom_field') == 'value1'
        assert hosts[0].metadata.get('port') == 2222

    def test_multiple_providers_unique_names(self):
        """Test that multiple providers can coexist."""
        provider1 = StaticProvider(name='provider1', hosts=[{'name': 'h1', 'ip': '10.0.0.1'}])
        provider2 = StaticProvider(name='provider2', hosts=[{'name': 'h2', 'ip': '10.0.0.2'}])
        
        hosts1 = provider1.get_hosts()
        hosts2 = provider2.get_hosts()
        
        assert hosts1[0].metadata['provider'] == 'provider1'
        assert hosts2[0].metadata['provider'] == 'provider2'
