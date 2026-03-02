"""Interactive onboarding wizard for SSHplex."""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from ..config import (
    SUPPORTED_MUX_BACKENDS,
    SUPPORTED_SOT_PROVIDER_TYPES,
    Config,
)
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
            self.console.print("\n[red]❌ At least one inventory source is required to use SSHplex.[/red]")
            self.console.print("[yellow]Please run the wizard again and configure at least one provider.[/yellow]")
            return False
        
        # Generate configuration
        config = self._generate_config()

        # Review before saving
        self._show_configuration_summary(config)
        if not Confirm.ask("\nSave this configuration?", default=True):
            self.console.print("\n[yellow]Onboarding cancelled. Configuration was not saved.[/yellow]")
            return False
        
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
        welcome_text.append("\n  • Configure inventory sources (Static, NetBox, Ansible, Consul, Git)")
        welcome_text.append("\n  • Test connections before saving")
        welcome_text.append("\n  • Generate a working configuration file")
        
        panel = Panel(welcome_text, border_style="blue", padding=(1, 2))
        self.console.print(panel)
        self.console.print()
    
    def _detect_environment(self) -> None:
        """Detect system environment and dependencies."""
        self.console.print("\n🔍 [bold]Detecting Environment[/bold]\n")
        platform_name = platform.system()
        self.detected_info['platform'] = platform_name
        
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

        # Detect git
        git_path = shutil.which("git")
        self.detected_info['git_installed'] = git_path is not None
        self.detected_info['git_path'] = git_path

        # Detect iTerm2 app (macOS only)
        iterm_app_exists = platform_name.lower() == "darwin" and Path("/Applications/iTerm.app").exists()
        self.detected_info['iterm2_installed'] = iterm_app_exists
        
        # Display detected info
        table = Table(show_header=False, box=None)
        table.add_column("Item", style="cyan")
        table.add_column("Status")

        table.add_row("Platform", f"✅ {platform_name}")
        
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
            table.add_row("tmux", "⚠️  Not found (required for tmux backend)")

        # git
        if git_path:
            table.add_row("git", f"✅ {git_path}")
        else:
            table.add_row("git", "⚠️  Not found (required for git inventory source)")

        # iTerm2
        if platform_name.lower() == "darwin":
            if iterm_app_exists:
                table.add_row("iTerm2", "✅ /Applications/iTerm.app")
            else:
                table.add_row("iTerm2", "ℹ️  Not found (optional, only for native iTerm2 backend)")
        
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
        provider_descriptions = {
            "static": "Static host list (manual entry)",
            "netbox": "NetBox (infrastructure source of truth)",
            "ansible": "Ansible inventory file",
            "consul": "HashiCorp Consul (service discovery)",
            "git": "Git repository inventory (static or ansible YAML)",
        }
        provider_types = [
            (provider_type, provider_descriptions.get(provider_type, provider_type))
            for provider_type in SUPPORTED_SOT_PROVIDER_TYPES
        ]
        
        self.console.print("\n[bold]Select inventory source type:[/bold]")
        for i, (_, desc) in enumerate(provider_types, 1):
            self.console.print(f"  {i}. {desc}")
        
        choice = Prompt.ask("\nChoice", choices=[str(i) for i in range(1, len(provider_types) + 1)], default="1")
        provider_type = provider_types[int(choice) - 1][0]

        configurators = {
            "static": self._configure_static,
            "netbox": self._configure_netbox,
            "ansible": self._configure_ansible,
            "consul": self._configure_consul,
            "git": self._configure_git,
        }
        handler = configurators.get(provider_type)
        if handler is None:
            self.console.print(f"[red]Unsupported provider type: {provider_type}[/red]")
            return None
        return handler()
    
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
        # Validate Consul port input
        while True:
            port_input = Prompt.ask("Consul port", default="8500")
            try:
                port = int(port_input)
                if 1 <= port <= 65535:
                    break
                else:
                    self.console.print("[red]Port must be between 1 and 65535[/red]")
            except ValueError:
                self.console.print(f"[red]Invalid port number: {port_input}[/red]")
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

    def _configure_git(self) -> Optional[Dict[str, Any]]:
        """Configure read-only git inventory provider."""
        self.console.print("\n[bold cyan]Git Inventory Configuration[/bold cyan]")

        if not self.detected_info.get('git_installed'):
            self.console.print("[yellow]⚠️  git was not detected on this machine.[/yellow]")
            if not Confirm.ask("Continue configuring git provider anyway?", default=False):
                return None

        name = Prompt.ask("Provider name", default="git-hosts")
        repo_url = Prompt.ask("Repository URL", default="git@github.com:org/hosts.git")
        branch = Prompt.ask("Branch", default="main")
        source_pattern = Prompt.ask(
            "Source pattern (path + glob)",
            default="hosts/**/*.y*ml",
        )
        inventory_format = Prompt.ask(
            "Inventory format",
            choices=["static", "ansible"],
            default="static",
        )

        while True:
            priority_input = Prompt.ask("Priority", default="100")
            try:
                priority = int(priority_input)
                break
            except ValueError:
                self.console.print(f"[red]Invalid priority: {priority_input}[/red]")

        auto_pull = Confirm.ask("Enable auto pull", default=True)
        pull_interval_seconds = 300
        if auto_pull:
            while True:
                interval_input = Prompt.ask("Auto pull interval (seconds)", default="300")
                try:
                    pull_interval_seconds = int(interval_input)
                    if pull_interval_seconds >= 0:
                        break
                    self.console.print("[red]Interval must be >= 0[/red]")
                except ValueError:
                    self.console.print(f"[red]Invalid interval: {interval_input}[/red]")

        config: Dict[str, Any] = {
            "name": name,
            "type": "git",
            "repo_url": repo_url,
            "branch": branch,
            "source_pattern": source_pattern,
            "inventory_format": inventory_format,
            "priority": priority,
            "auto_pull": auto_pull,
            "pull_interval_seconds": pull_interval_seconds,
            "pull_strategy": "ff-only",
        }

        if inventory_format == "ansible":
            groups_str = Prompt.ask(
                "Ansible groups filter (comma-separated, optional)",
                default="",
            )
            if groups_str.strip():
                groups = [group.strip() for group in groups_str.split(",") if group.strip()]
                if groups:
                    config["default_filters"] = {"groups": groups}

        if Confirm.ask("\nTest repository access?", default=True):
            if self._test_git_connection(config):
                self.console.print("✅ Repository access successful!")
            else:
                self.console.print("❌ Could not read remote branch/source. Check URL/auth/branch.")
                if not Confirm.ask("Keep this configuration anyway?", default=False):
                    return None

        return config

    def _test_netbox_connection(self, config: Dict[str, Any]) -> bool:
        """Test NetBox connection."""
        self.logger.info(f"Testing NetBox connection to {config['url']}")
        self.console.print("\n🔄 Testing connection...")
        
        try:
            import pynetbox  # type: ignore[import-untyped]
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

    def _test_git_connection(self, config: Dict[str, Any]) -> bool:
        """Test git repository access and branch visibility."""
        repo_url = str(config.get("repo_url", "")).strip()
        branch = str(config.get("branch", "main")).strip() or "main"
        self.logger.info(f"Testing git source access: {repo_url}@{branch}")
        self.console.print("\n🔄 Testing repository access...")

        if not repo_url:
            self.logger.error("Git repository URL is empty")
            return False

        git_bin = shutil.which("git")
        if not git_bin:
            self.logger.error("git binary not found in PATH")
            return False

        try:
            result = subprocess.run(
                [git_bin, "ls-remote", "--heads", repo_url, branch],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode != 0:
                self.logger.error(f"git ls-remote failed: {result.stderr.strip()}")
                return False

            if not (result.stdout or "").strip():
                self.logger.warning(
                    f"Repository reachable but no matching branch found for '{branch}'"
                )
                return False

            return True
        except Exception as e:
            self.logger.error(f"Git repository check failed: {e}")
            return False

    def _select_backend(self) -> str:
        """Choose backend based on detected environment."""
        platform_name = str(self.detected_info.get('platform', platform.system()))
        tmux_installed = bool(self.detected_info.get('tmux_installed', False))
        iterm2_installed = bool(self.detected_info.get('iterm2_installed', False))

        if platform_name.lower() == "darwin" and iterm2_installed:
            default_backend = "tmux" if tmux_installed else "iterm2-native"
            backend = Prompt.ask(
                "Backend",
                choices=list(SUPPORTED_MUX_BACKENDS),
                default=default_backend,
            )
            return backend

        return "tmux"
    
    def _generate_config(self) -> Dict[str, Any]:
        """Generate configuration dictionary."""
        # Use detected SSH key as default, fallback to common default if none found
        default_key = self.detected_info.get('default_ssh_key') or '~/.ssh/id_ed25519'
        backend = self._select_backend()
        
        # Validate SSH port input
        while True:
            port_input = Prompt.ask("Default SSH port", default="22")
            try:
                ssh_port = int(port_input)
                if 1 <= ssh_port <= 65535:
                    break
                else:
                    self.console.print("[red]Port must be between 1 and 65535[/red]")
            except ValueError:
                self.console.print(f"[red]Invalid port number: {port_input}[/red]")
        
        config = {
            "ssh": {
                "username": Prompt.ask("\nDefault SSH username", default=os.environ.get('USER', 'admin')),
                "key_path": Prompt.ask("Default SSH key path", default=default_key),
                "port": ssh_port,
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
                "backend": backend,
                "control_with_iterm2": False
            },
            "ui": {
                "show_log_panel": False,
                "table_columns": ["name", "ip", "cluster", "role", "tags", "description", "provider"]
            }
        }

        if backend == "tmux" and not self.detected_info.get('tmux_installed'):
            self.console.print(
                "\n[yellow]⚠️  tmux backend selected but tmux was not detected. "
                "Install tmux or switch to iTerm2 native backend on macOS.[/yellow]"
            )
        
        return config

    def _show_configuration_summary(self, config: Dict[str, Any]) -> None:
        """Display final config summary before save."""
        self.console.print("\n🧾 [bold]Configuration Summary[/bold]\n")

        ssh = config.get("ssh", {})
        tmux = config.get("tmux", {})
        imports = list((config.get("sot", {}) or {}).get("import", []) or [])

        summary = Table(show_header=False, box=None)
        summary.add_column("Item", style="cyan")
        summary.add_column("Value")
        summary.add_row("Config Path", str(self.config_path))
        summary.add_row("Backend", str(tmux.get("backend", "tmux")))
        summary.add_row("SSH Username", str(ssh.get("username", "")))
        summary.add_row("SSH Port", str(ssh.get("port", 22)))
        summary.add_row("SSH Key", str(ssh.get("key_path", "")))
        summary.add_row("Sources", str(len(imports)))
        self.console.print(summary)

        if imports:
            provider_table = Table(show_header=True, box=None)
            provider_table.add_column("Name", style="bold")
            provider_table.add_column("Type", style="magenta")
            provider_table.add_column("Details", style="dim")

            for provider in imports:
                provider_name = str(provider.get("name", "unnamed"))
                provider_type = str(provider.get("type", "unknown"))
                details = ""
                if provider_type == "static":
                    details = f"hosts: {len(provider.get('hosts', []) or [])}"
                elif provider_type == "ansible":
                    details = f"paths: {len(provider.get('inventory_paths', []) or [])}"
                elif provider_type == "netbox":
                    details = str(provider.get("url", ""))
                elif provider_type == "consul":
                    cfg = provider.get("config", {}) or {}
                    details = f"{cfg.get('scheme', 'http')}://{cfg.get('host', 'localhost')}:{cfg.get('port', 8500)}"
                elif provider_type == "git":
                    details = str(provider.get("source_pattern", ""))

                provider_table.add_row(provider_name, provider_type, details)

            self.console.print()
            self.console.print(provider_table)
    
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
