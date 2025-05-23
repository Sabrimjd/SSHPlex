"""Test script for SSHplex TUI."""

from textual.app import App
from lib.ui.host_selector import HostSelector
from lib.config import SSHplexConfig

# Simple mock for testing config
class MockConfig:
    def __init__(self):
        self.netbox = MockNetboxConfig()
        self.ssh = MockSSHConfig()
        self.tmux = MockTmuxConfig()
        self.logging = MockLoggingConfig()

class MockNetboxConfig:
    def __init__(self):
        self.url = "https://netbox.example.com"
        self.token = "mock-token"
        self.verify_ssl = False
        self.timeout = 10
        self.default_filters = {"status": "active"}

class MockSSHConfig:
    def __init__(self):
        self.username = "admin"
        self.key_path = "~/.ssh/id_rsa"

class MockTmuxConfig:
    def __init__(self):
        self.layout = "tiled"

class MockLoggingConfig:
    def __init__(self):
        self.level = "INFO"
        self.file = "logs/sshplex.log"

# Mock Host class for testing
class Host:
    def __init__(self, name, ip, **metadata):
        self.name = name
        self.ip = ip
        self.metadata = metadata

# Mock NetBoxProvider for testing
class MockNetBoxProvider:
    def __init__(self, *args, **kwargs):
        pass

    def connect(self):
        return True

    def get_hosts(self, filters=None):
        # Return some mock hosts
        return [
            Host("web01", "192.168.1.101", status="active", role="web", platform="ubuntu"),
            Host("web02", "192.168.1.102", status="active", role="web", platform="ubuntu"),
            Host("db01", "192.168.1.201", status="active", role="database", platform="centos"),
            Host("db02", "192.168.1.202", status="inactive", role="database", platform="centos"),
            Host("app01", "192.168.1.301", status="active", role="application", platform="ubuntu"),
            Host("app02", "192.168.1.302", status="active", role="application", platform="ubuntu"),
            Host("load01", "192.168.1.401", status="maintenance", role="loadbalancer", platform="nginx"),
            Host("mon01", "192.168.1.501", status="active", role="monitoring", platform="grafana"),
        ]

if __name__ == "__main__":
    # Create mock config
    config = MockConfig()

    # Create host selector app
    app = HostSelector(config)

    # Replace NetBox provider with mock implementation
    app.netbox = MockNetBoxProvider()

    # Run the app
    app.run()
