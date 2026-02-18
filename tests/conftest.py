"""Pytest fixtures for SSHplex tests."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict():
    """Return a sample configuration dictionary."""
    return {
        'sshplex': {
            'session_prefix': 'sshplex',
        },
        'sot': {
            'providers': ['static'],
            'import': [
                {
                    'name': 'test-static',
                    'type': 'static',
                    'hosts': [
                        {'name': 'host1', 'ip': '192.168.1.10', 'description': 'Test host 1'},
                        {'name': 'host2', 'ip': '192.168.1.20', 'description': 'Test host 2'},
                    ]
                }
            ]
        },
        'ssh': {
            'username': 'testuser',
            'key_path': '~/.ssh/id_test',
            'timeout': 10,
            'port': 22,
            'strict_host_key_checking': False,
            'retry': {
                'enabled': True,
                'max_attempts': 3,
                'delay_seconds': 2.0,
                'exponential_backoff': True,
            }
        },
        'tmux': {
            'layout': 'tiled',
            'broadcast': False,
            'window_name': 'sshplex',
            'max_panes_per_window': 5,
            'control_with_iterm2': False,
        },
        'ui': {
            'show_log_panel': False,
            'log_panel_height': 20,
            'table_columns': ['name', 'ip', 'description', 'provider'],
        },
        'logging': {
            'enabled': False,
            'level': 'INFO',
            'file': 'logs/sshplex.log',
        },
        'cache': {
            'enabled': True,
            'cache_dir': '~/.cache/sshplex',
            'ttl_hours': 24,
        }
    }


@pytest.fixture
def sample_static_hosts():
    """Return sample static host configurations."""
    return [
        {'name': 'web-01', 'ip': '10.0.1.10', 'description': 'Web server', 'tags': ['web', 'prod']},
        {'name': 'db-01', 'ip': '10.0.1.20', 'description': 'Database server', 'tags': ['db', 'prod']},
        {'name': 'cache-01', 'ip': '10.0.1.30', 'description': 'Cache server', 'tags': ['cache', 'prod']},
    ]


@pytest.fixture
def sample_ansible_inventory():
    """Return a sample Ansible inventory structure."""
    return {
        'all': {
            'hosts': {
                'localhost': {
                    'ansible_connection': 'local'
                }
            },
            'children': {
                'webservers': {
                    'hosts': {
                        'web1': {'ansible_host': '10.1.1.1'},
                        'web2': {'ansible_host': '10.1.1.2'},
                    }
                },
                'databases': {
                    'hosts': {
                        'db1': {'ansible_host': '10.1.2.1'},
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_netbox_api():
    """Create a mock NetBox API."""
    mock_api = MagicMock()
    
    # Mock status check
    mock_api.status.return_value = {'version': '3.5.0'}
    
    # Mock virtual machines
    mock_vm = MagicMock()
    mock_vm.name = 'test-vm-01'
    mock_vm.primary_ip4 = '10.0.0.1/24'
    mock_vm.status = 'active'
    mock_vm.role = 'server'
    mock_vm.cluster = 'test-cluster'
    mock_vm.tags = []
    mock_vm.description = 'Test VM'
    
    mock_api.virtualization.virtual_machines.filter.return_value = [mock_vm]
    mock_api.dcim.devices.filter.return_value = []
    
    return mock_api


@pytest.fixture
def mock_libtmux_server():
    """Create a mock libtmux Server."""
    with patch('libtmux.Server') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock session
        mock_session = MagicMock()
        mock_session.session_name = 'test-session'
        mock_session.attached_window = MagicMock()
        mock_instance.new_session.return_value = mock_session
        mock_instance.has_session.return_value = False
        
        yield mock
