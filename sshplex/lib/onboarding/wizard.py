"""Interactive onboarding wizard for SSHplex."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from ..config import Config
from ..logger import get_logger


class OnboardingWizard:
    """Interactive first-run setup wizard for SSHplex."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the onboarding wizard.
        
        Args:
            config_path: Optional custom config path
        """
        self.console = Console()
        self.logger = get_logger()
        self.config_path = config_path or Path.home() / ".config" / "sshplex" / "sshplex.yaml"
        self.detected_info: Dict[str, Any] = {}
        self.providers: List[Dict[str, Any]] = []
        
    def run(self) -> bool:
        """Run the onboarding wizard.
        
        Returns:
            True if onboarding completed successfully, False otherwise
        """
        self.logger.info("Starting onboarding wizard")
        
        # Show welcome screen
        self._show_welcome()
        
        # Detect system environment
        self._detect_environment()
        
        # Check if config already exists
        if self.config_path.exists() and not Confirm.ask(
            "\n⚠️  Configuration file already exists. Overwrite?", default=False
        ):
            self.console.print("\n[yellow]Onboarding cancelled. Existing configuration preserved.[/yellow]")
            return False
        
        # Collect provider configurations
        self._collect_providers()
        
        if not self.providers:
            self.console.print("\n[yellow]No providers configured. Creating minimal config...[/yellow]")
        
        # Generate configuration
        config = self._generate_config()
        
        # Save configuration
        if self._save_config(config):
            self._show_success()
            return True
        else:
            self.console.print("\n[red]❌ Failed to save configuration[/red]")
            return False
    
    def _show_welcome(self) -> None:
        """Display welcome screen."""
        welcome_text = Text()
        welcome_text.append("SSHplex Setup Wizard", style="bold blue")
        welcome_text.append("\n\n")
        welcome_text.append("Let's configure SSHplex for your environment.")
        welcome_text.append("\nThis wizard will help you:")
        welcome_text.append("\n  • Detect SSH keys and system dependencies")
        welcome_text.append("\n  • Configure inventory sources (NetBox, Ansible, Consul, etc.)")
        welcome_text.append("\n  • Test connections before saving")
        welcome_text.append("\n  • Generate a working configuration file")
        
        panel = Panel(welcome_text, border_style="blue", padding=(1, 2))
        self.console.print(panel)
        self.console.print()
    
    def _detect_environment(self) -> None:
        """Detect system environment and dependencies."""
        self.console.print("\n🔍 [bold]Detecting Environment[/bold]\n")
        
        # Detect SSH keys
        ssh_dir = Path.home() / ".ssh"
        ssh_keys = []
        if ssh_dir.exists():
            for key_file in ssh_dir.glob("id_*"):
                if key_file.is_file() and key_file.suffix != ".pub":
                    ssh_keys.append(str(key_file))
        
        self.detected_info['ssh_keys'] = ssh_keys
        self.detected_info['default_ssh_key'] = ssh_keys[0] if ssh_keys else None
        
        # Detect tmux
        tmux_path = shutil.which("tmux")
        self.detected_info['tmux_installed'] = tmux_path is not None
        self.detected_info['tmux_path'] = tmux_path
        
        # Display detected info
        table = Table(show_header=False, box=None)
        table.add_column("Item", style="cyan")
        table.add_column("Status")
        
        # SSH keys
        if ssh_keys:
            table.add_row("SSH Keys", f"✅ Found {len(ssh_keys)} key(s)")
            for key in ssh_keys:
                table.add_row("", f"  • {key}")
        else:
            table.add_row("SSH Keys", "⚠️  No SSH keys found in ~/.ssh/")
        
        # tmux
        if tmux_path:
            table.add_row("tmux", f"✅ {tmux_path}")
        else:
            table.add_row("tmux", "❌ Not found (required for SSHplex)")
        
        self.console.print(table)
    
    def _collect_providers(self) -> None:
        """Collect provider configurations from user."""
        self.console.print("\n📡 [bold]Configure Inventory Sources[/bold]\n")
        
        add_more = True
        while add_more:
            provider = self._configure_provider()
            if provider:
                self.providers.append(provider)
            
            add_more = Confirm.ask("\nAdd another inventory source?", default=False)
    
    def _configure_provider(self) -> Optional[Dict[str, Any]]:
        """Configure a single provider.
        
        Returns:
            Provider configuration dict or None if cancelled
        """
        self.console.print("\n" + "─" * 60)
        
        # Provider type selection
        provider_types = [
            ("static", "Static host list (manual entry)"),
            ("netbox", "NetBox (infrastructure source of truth)"),
            ("ansible", "Ansible inventory file"),
            ("consul", "HashiCorp Consul (service discovery)"),
        ]
        
        self.console.print("\n[bold]Select inventory source type:[/bold]")
        for i, (_, desc) in enumerate(provider_types, 1):
            self.console.print(f"  {i}. {desc}")
        
        choice = Prompt.ask("\nChoice", choices=[str(i) for i in range(1, len(provider_types) + 1)], default="1")
        provider_type = provider_types[int(choice) - 1][0]
        
        # Configure based on type
        if provider_type == "static":
            return self._configure_static()
        elif provider_type == "netbox":
            return self._configure_netbox()
        elif provider_type == "ansible":
            return self._configure_ansible()
        elif provider_type == "consul":
            return self._configure_consul()
        
        return None
    
    def _configure_static(self) -> Optional[Dict[str, Any]]:
        """Configure static host provider."""
        self.console.print("\n[bold cyan]Static Host List Configuration[/bold cyan]")
        
        name = Prompt.ask("Provider name", default="my-hosts")
        hosts: List[Dict[str, str]] = []
        
        self.console.print("\n[bold]Add hosts[/bold] (leave name empty to finish)")
        
        while True:
            host_name = Prompt.ask(f"\nHost {len(hosts) + 1} name", default="")
            if not host_name:
                break
            
            host_ip = Prompt.ask("IP address")
            description = Prompt.ask("Description (optional)", default="")
            
            host = {
                "name": host_name,
                "ip": host_ip,
            }
            if description:
                host["description"] = description
            
            hosts.append(host)
        
        if not hosts:
            self.console.print("[yellow]No hosts added. Skipping...[/yellow]")
            return None
        
        config = {
            "name": name,
            "type": "static",
            "hosts": hosts
        }
        
        # Test is not applicable for static hosts
        self.console.print(f"\n✅ Configured {len(hosts)} static hosts")
        return config
    
    def _configure_netbox(self) -> Optional[Dict[str, Any]]:
        """Configure NetBox provider."""
        self.console.print("\n[bold cyan]NetBox Configuration[/bold cyan]")
        
        name = Prompt.ask("Provider name", default="netbox")
        url = Prompt.ask("NetBox URL", default="https://netbox.example.com")
        token = Prompt.ask("API Token", password=True)
        verify_ssl = Confirm.ask("Verify SSL certificate", default=True)
        
        config = {
            "name": name,
            "type": "netbox",
            "url": url,
            "token": token,
            "verify_ssl": verify_ssl
        }
        
        # Test connection
        if Confirm.ask("\nTest connection?", default=True):
            if self._test_netbox_connection(config):
                self.console.print("✅ Connection successful!")
            else:
                self.console.print("❌ Connection failed. Check your credentials and URL.")
                if not Confirm.ask("Keep this configuration anyway?", default=False):
                    return None
        
        return config
    
    def _configure_ansible(self) -> Optional[Dict[str, Any]]:
        """Configure Ansible inventory provider."""
        self.console.print("\n[bold cyan]Ansible Inventory Configuration[/bold cyan]")
        
        name = Prompt.ask("Provider name", default="ansible")
        
        inventory_paths: List[str] = []
        self.console.print("\n[bold]Add inventory file paths[/bold] (leave empty to finish)")
        
        while True:
            path = Prompt.ask(f"Inventory path {len(inventory_paths) + 1}", default="")
            if not path:
                break
            
            # Check if path exists
            if not Path(path).exists():
                self.console.print(f"[yellow]⚠️  Path does not exist: {path}[/yellow]")
                if not Confirm.ask("Add anyway?", default=False):
                    continue
            
            inventory_paths.append(path)
        
        if not inventory_paths:
            self.console.print("[yellow]No inventory paths added. Skipping...[/yellow]")
            return None
        
        config = {
            "name": name,
            "type": "ansible",
            "inventory_paths": inventory_paths
        }
        
        # Test connection
        if Confirm.ask("\nTest connection?", default=True):
            if self._test_ansible_connection(config):
                self.console.print("✅ Inventory loaded successfully!")
            else:
                self.console.print("❌ Failed to load inventory. Check paths and format.")
                if not Confirm.ask("Keep this configuration anyway?", default=False):
                    return None
        
        return config
    
    def _configure_consul(self) -> Optional[Dict[str, Any]]:
        """Configure Consul provider."""
        self.console.print("\n[bold cyan]Consul Configuration[/bold cyan]")
        
        name = Prompt.ask("Provider name", default="consul")
        host = Prompt.ask("Consul host", default="localhost")
        port = int(Prompt.ask("Consul port", default="8500"))
        scheme = Prompt.ask("Scheme (http/https)", default="http")
        token = Prompt.ask("ACL Token (optional)", password=True, default="")
        dc = Prompt.ask("Datacenter (optional)", default="")
        
        consul_config: Dict[str, Any] = {
            "host": host,
            "port": port,
            "scheme": scheme,
            "token": token,  # Always include token, even if empty
        }
        
        if dc:
            consul_config["dc"] = dc
        
        config = {
            "name": name,
            "type": "consul",
            "config": consul_config
        }
        
        # Test connection
        if Confirm.ask("\nTest connection?", default=True):
            if self._test_consul_connection(config):
                self.console.print("✅ Connection successful!")
            else:
                self.console.print("❌ Connection failed. Check your configuration.")
                if not Confirm.ask("Keep this configuration anyway?", default=False):
                    return None
        
        return config
    
    def _test_netbox_connection(self, config: Dict[str, Any]) -> bool:
        """Test NetBox connection."""
        self.logger.info(f"Testing NetBox connection to {config['url']}")
        self.console.print("\n🔄 Testing connection...")
        
        try:
            import pynetbox
            nb = pynetbox.api(config['url'], token=config['token'])
            if config.get('verify_ssl') is False:
                nb.http_session.verify = False
            
            # Test by getting version
            version = nb.version
            self.logger.info(f"NetBox connection successful, version: {version}")
            return True
        except Exception as e:
            self.logger.error(f"NetBox connection failed: {e}")
            return False
    
    def _test_ansible_connection(self, config: Dict[str, Any]) -> bool:
        """Test Ansible inventory loading."""
        self.logger.info(f"Testing Ansible inventory from {config['inventory_paths']}")
        self.console.print("\n🔄 Loading inventory...")
        
        try:
            # Try to load the inventory
            from ..sot.ansible import AnsibleProvider
            provider = AnsibleProvider(
                inventory_paths=config['inventory_paths']
            )
            
            # Connect to load the inventory files
            if not provider.connect():
                self.logger.error("Ansible provider failed to connect/load inventory")
                return False
            
            hosts = provider.get_hosts()
            self.logger.info(f"Ansible inventory loaded, found {len(hosts)} hosts")
            return True
        except Exception as e:
            self.logger.error(f"Ansible inventory loading failed: {e}")
            return False
    
    def _test_consul_connection(self, config: Dict[str, Any]) -> bool:
        """Test Consul connection."""
        self.logger.info(f"Testing Consul connection to {config['config']['host']}:{config['config']['port']}")
        self.console.print("\n🔄 Testing connection...")
        
        try:
            import consul
            client = consul.Consul(**config['config'])
            
            # Test by getting leader
            leader = client.status.leader()
            self.logger.info(f"Consul connection successful, leader: {leader}")
            return True
        except Exception as e:
            self.logger.error(f"Consul connection failed: {e}")
            return False
    
    def _generate_config(self) -> Dict[str, Any]:
        """Generate configuration dictionary."""
        # Use detected SSH key as default, fallback to common default if none found
        default_key = self.detected_info.get('default_ssh_key') or '~/.ssh/id_ed25519'
        
        config = {
            "ssh": {
                "username": Prompt.ask("\nDefault SSH username", default=os.environ.get('USER', 'admin')),
                "key_path": Prompt.ask("Default SSH key path", default=default_key),
                "port": int(Prompt.ask("Default SSH port", default="22")),
            },
            "sot": {
                "import": self.providers
            },
            "cache": {
                "enabled": True,
                "cache_dir": "~/.cache/sshplex",
                "ttl_hours": 24
            },
            "logging": {
                "enabled": True,
                "level": "INFO",
                "file": "logs/sshplex.log"
            },
            "tmux": {
                "control_with_iterm2": False
            },
            "ui": {
                "show_log_panel": False,
                "table_columns": ["name", "ip", "cluster", "role", "tags", "description", "provider"]
            }
        }
        
        return config
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate configuration against full Config model
            Config(**config)  # Validates and raises ValidationError if invalid
            
            # Save to YAML
            import yaml
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
        except ValidationError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            self.console.print("\n[red]❌ Configuration validation failed:[/red]")
            self.console.print(str(e))
            return False
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _show_success(self) -> None:
        """Display success message."""
        success_text = Text()
        success_text.append("✅ Configuration Complete!", style="bold green")
        success_text.append(f"\n\nConfiguration saved to: {self.config_path}")
        success_text.append("\n\nYou're ready to use SSHplex!")
        success_text.append("\n\nNext steps:")
        success_text.append("\n  • Run [bold]sshplex[/bold] to launch the TUI")
        success_text.append("\n  • Press [bold]?[/bold] or [bold]h[/bold] in the TUI for keyboard shortcuts")
        success_text.append("\n  • Edit configuration anytime with [bold]e[/bold] key in TUI")
        
        panel = Panel(success_text, border_style="green", padding=(1, 2))
        self.console.print("\n")
        self.console.print(panel)
