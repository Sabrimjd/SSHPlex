"""Tests for SSHplex Ansible inventory provider."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from sshplex.lib.sot.ansible import AnsibleProvider
from sshplex.lib.sot.base import Host


class TestAnsibleProvider:
    """Tests for AnsibleProvider class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for inventory files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def simple_inventory(self, temp_dir):
        """Create a simple Ansible inventory file."""
        inventory = {
            'all': {
                'hosts': {
                    'localhost': {'ansible_connection': 'local'}
                },
                'children': {
                    'webservers': {
                        'hosts': {
                            'web1': {'ansible_host': '10.1.1.1', 'ansible_user': 'webuser'},
                            'web2': {'ansible_host': '10.1.1.2'},
                        }
                    },
                    'databases': {
                        'hosts': {
                            'db1': {'ansible_host': '10.1.2.1', 'ansible_port': 3306},
                        }
                    }
                }
            }
        }
        
        inventory_file = temp_dir / "inventory.yml"
        with open(inventory_file, 'w') as f:
            yaml.dump(inventory, f)
        
        return inventory_file

    @pytest.fixture
    def provider(self, simple_inventory):
        """Create an AnsibleProvider instance."""
        return AnsibleProvider(inventory_paths=[str(simple_inventory)])

    def test_init(self, simple_inventory):
        """Test provider initialization."""
        provider = AnsibleProvider(inventory_paths=[str(simple_inventory)])
        assert len(provider.inventory_paths) == 1

    def test_connect(self, provider):
        """Test connect method loads inventory."""
        assert provider.connect() is True
        assert len(provider.inventories) == 1

    def test_connect_missing_file(self, temp_dir):
        """Test connect with missing inventory file."""
        provider = AnsibleProvider(inventory_paths=[str(temp_dir / "missing.yml")])
        assert provider.connect() is False

    def test_test_connection(self, provider):
        """Test test_connection method."""
        provider.connect()
        assert provider.test_connection() is True

    def test_test_connection_not_loaded(self):
        """Test test_connection when inventory not loaded."""
        provider = AnsibleProvider(inventory_paths=[])
        assert provider.test_connection() is False

    def test_get_hosts(self, provider):
        """Test getting hosts from inventory."""
        provider.connect()
        hosts = provider.get_hosts()
        
        # Should have web1, web2, db1 (localhost skipped - no ansible_host)
        assert len(hosts) == 3
        
        host_names = [h.name for h in hosts]
        assert 'web1' in host_names
        assert 'web2' in host_names
        assert 'db1' in host_names

    def test_host_data_populated(self, provider):
        """Test that host data is correctly populated."""
        provider.connect()
        hosts = provider.get_hosts()
        
        web1 = next(h for h in hosts if h.name == 'web1')
        assert web1.ip == '10.1.1.1'
        assert web1.ansible_user == 'webuser'
        assert web1.ansible_group == 'webservers'

    def test_filter_by_groups(self, simple_inventory):
        """Test filtering by group."""
        provider = AnsibleProvider(
            inventory_paths=[str(simple_inventory)],
            filters={'groups': ['webservers']}
        )
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 2
        assert all('webservers' in h.metadata.get('ansible_group', '') for h in hosts)

    def test_filter_exclude_groups(self, simple_inventory):
        """Test excluding groups."""
        provider = AnsibleProvider(
            inventory_paths=[str(simple_inventory)],
            filters={'exclude_groups': ['databases']}
        )
        provider.connect()
        hosts = provider.get_hosts()
        
        host_names = [h.name for h in hosts]
        assert 'db1' not in host_names
        assert 'web1' in host_names

    def test_filter_host_patterns(self, simple_inventory):
        """Test filtering by host patterns."""
        provider = AnsibleProvider(
            inventory_paths=[str(simple_inventory)],
            filters={'host_patterns': [r'^web.*$']}
        )
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 2
        assert all(h.name.startswith('web') for h in hosts)

    def test_multiple_inventories(self, temp_dir):
        """Test loading multiple inventory files."""
        # Create two inventory files
        inv1 = {
            'all': {
                'children': {
                    'group1': {
                        'hosts': {'host1': {'ansible_host': '10.0.1.1'}}
                    }
                }
            }
        }
        inv2 = {
            'all': {
                'children': {
                    'group2': {
                        'hosts': {'host2': {'ansible_host': '10.0.2.1'}}
                    }
                }
            }
        }
        
        file1 = temp_dir / "inv1.yml"
        file2 = temp_dir / "inv2.yml"
        
        with open(file1, 'w') as f:
            yaml.dump(inv1, f)
        with open(file2, 'w') as f:
            yaml.dump(inv2, f)
        
        provider = AnsibleProvider(inventory_paths=[str(file1), str(file2)])
        assert provider.connect() is True
        
        hosts = provider.get_hosts()
        assert len(hosts) == 2

    def test_nested_groups(self, temp_dir):
        """Test deeply nested group structure."""
        inventory = {
            'all': {
                'children': {
                    'production': {
                        'children': {
                            'us_east': {
                                'hosts': {
                                    'prod-web-01': {'ansible_host': '10.10.1.1'}
                                }
                            }
                        }
                    }
                }
            }
        }
        
        inv_file = temp_dir / "nested.yml"
        with open(inv_file, 'w') as f:
            yaml.dump(inventory, f)
        
        provider = AnsibleProvider(inventory_paths=[str(inv_file)])
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 1
        assert hosts[0].name == 'prod-web-01'

    def test_host_without_ansible_host_skipped(self, temp_dir):
        """Test that hosts without ansible_host are skipped."""
        inventory = {
            'all': {
                'hosts': {
                    'host1': {'ansible_host': '10.0.0.1'},
                    'host2': {},  # No ansible_host
                    'host3': {'ansible_host': '10.0.0.3'},
                }
            }
        }
        
        inv_file = temp_dir / "test.yml"
        with open(inv_file, 'w') as f:
            yaml.dump(inventory, f)
        
        provider = AnsibleProvider(inventory_paths=[str(inv_file)])
        provider.connect()
        hosts = provider.get_hosts()
        
        assert len(hosts) == 2
        host_names = [h.name for h in hosts]
        assert 'host2' not in host_names

    def test_empty_inventory(self, temp_dir):
        """Test with empty inventory file."""
        inv_file = temp_dir / "empty.yml"
        with open(inv_file, 'w') as f:
            yaml.dump({}, f)
        
        provider = AnsibleProvider(inventory_paths=[str(inv_file)])
        assert provider.connect() is False

    def test_invalid_yaml(self, temp_dir):
        """Test handling of invalid YAML."""
        inv_file = temp_dir / "invalid.yml"
        with open(inv_file, 'w') as f:
            f.write("invalid: yaml: [")
        
        provider = AnsibleProvider(inventory_paths=[str(inv_file)])
        assert provider.connect() is False

    def test_host_metadata_sources(self, provider):
        """Test that host metadata includes source information."""
        provider.connect()
        hosts = provider.get_hosts()
        
        for host in hosts:
            assert 'sources' in host.metadata
            assert 'provider' in host.metadata

    def test_duplicate_hosts_merged(self, temp_dir):
        """Test that duplicate hosts are merged."""
        # Create inventory with duplicate hosts
        inv1 = {
            'all': {
                'hosts': {
                    'host1': {'ansible_host': '10.0.0.1', 'var1': 'value1'}
                }
            }
        }
        inv2 = {
            'all': {
                'hosts': {
                    'host1': {'ansible_host': '10.0.0.1', 'var2': 'value2'}
                }
            }
        }
        
        file1 = temp_dir / "inv1.yml"
        file2 = temp_dir / "inv2.yml"
        
        with open(file1, 'w') as f:
            yaml.dump(inv1, f)
        with open(file2, 'w') as f:
            yaml.dump(inv2, f)
        
        provider = AnsibleProvider(inventory_paths=[str(file1), str(file2)])
        provider.connect()
        hosts = provider.get_hosts()
        
        # Should have only 1 host (merged)
        assert len(hosts) == 1
