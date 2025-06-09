"""Source of Truth provider factory for SSHplex."""

from typing import List, Dict, Any, Optional
from ..logger import get_logger
from .base import SoTProvider, Host
from .netbox import NetBoxProvider
from .ansible import AnsibleProvider


class SoTFactory:
    """Factory for creating and managing Source of Truth providers."""

    def __init__(self, config: Any) -> None:
        """Initialize SoT factory with configuration.

        Args:
            config: SSHplex configuration object
        """
        self.config = config
        self.logger = get_logger()
        self.providers: List[SoTProvider] = []

    def initialize_providers(self) -> bool:
        """Initialize all configured SoT providers.

        Returns:
            True if at least one provider was successfully initialized
        """
        self.providers = []
        success_count = 0

        for provider_name in self.config.sot.providers:
            try:
                provider: Optional[SoTProvider] = None
                if provider_name == "netbox":
                    provider = self._create_netbox_provider()
                elif provider_name == "ansible":
                    provider = self._create_ansible_provider()
                else:
                    self.logger.error(f"Unknown SoT provider: {provider_name}")
                    continue

                if provider and provider.connect():
                    self.providers.append(provider)
                    success_count += 1
                    self.logger.info(f"Successfully initialized {provider_name} provider")
                else:
                    self.logger.error(f"Failed to initialize {provider_name} provider")

            except Exception as e:
                self.logger.error(f"Error initializing {provider_name} provider: {e}")

        self.logger.info(f"Initialized {success_count}/{len(self.config.sot.providers)} SoT providers")
        return success_count > 0

    def _create_netbox_provider(self) -> Optional[NetBoxProvider]:
        """Create NetBox provider instance.

        Returns:
            NetBoxProvider instance or None if configuration missing
        """
        if not self.config.netbox:
            self.logger.error("NetBox provider requested but configuration missing")
            return None

        return NetBoxProvider(
            url=self.config.netbox.url,
            token=self.config.netbox.token,
            verify_ssl=self.config.netbox.verify_ssl,
            timeout=self.config.netbox.timeout
        )

    def _create_ansible_provider(self) -> Optional[AnsibleProvider]:
        """Create Ansible provider instance.

        Returns:
            AnsibleProvider instance or None if configuration missing
        """
        if not self.config.ansible_inventory:
            self.logger.error("Ansible provider requested but configuration missing")
            return None

        return AnsibleProvider(
            inventory_paths=self.config.ansible_inventory.inventory_paths,
            filters=self.config.ansible_inventory.default_filters
        )

    def get_all_hosts(self, additional_filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Get hosts from all configured providers.

        Args:
            additional_filters: Additional filters to apply to all providers

        Returns:
            Combined list of hosts from all providers
        """
        if not self.providers:
            self.logger.error("No SoT providers initialized")
            return []

        all_hosts = []

        for provider in self.providers:
            try:
                # Get provider-specific filters
                provider_filters = self._get_provider_filters(provider, additional_filters)

                hosts = provider.get_hosts(filters=provider_filters)
                self.logger.info(f"Retrieved {len(hosts)} hosts from {type(provider).__name__}")
                all_hosts.extend(hosts)

            except Exception as e:
                self.logger.error(f"Error retrieving hosts from {type(provider).__name__}: {e}")

        # Remove duplicates based on name + ip combination
        unique_hosts = {}
        for host in all_hosts:
            key = f"{host.name}:{host.ip}"
            if key not in unique_hosts:
                unique_hosts[key] = host
            else:
                # If duplicate, merge metadata and note the source conflict
                existing = unique_hosts[key]
                existing.metadata.update(host.metadata)

                # Add source information
                existing_sources = existing.metadata.get('sources', [])
                new_sources = host.metadata.get('sources', [])

                if isinstance(existing_sources, str):
                    existing_sources = [existing_sources]
                if isinstance(new_sources, str):
                    new_sources = [new_sources]

                # Determine source for each host
                existing_source = self._get_host_source(existing)
                new_source = self._get_host_source(host)

                all_sources = existing_sources + new_sources + [existing_source, new_source]
                unique_sources: List[str] = list(set(filter(None, all_sources)))
                existing.metadata['sources'] = unique_sources

                self.logger.debug(f"Merged duplicate host {host.name} from sources: {unique_sources}")

        final_hosts = list(unique_hosts.values())
        self.logger.info(f"Retrieved {len(final_hosts)} unique hosts from {len(self.providers)} providers")
        return final_hosts

    def _get_provider_filters(self, provider: SoTProvider,
                              additional_filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get filters specific to a provider.

        Args:
            provider: SoT provider instance
            additional_filters: Additional filters to merge

        Returns:
            Combined filters for the provider
        """
        filters = {}

        # Add provider-specific default filters
        if isinstance(provider, NetBoxProvider) and self.config.netbox:
            filters.update(self.config.netbox.default_filters)
        elif isinstance(provider, AnsibleProvider) and self.config.ansible_inventory:
            filters.update(self.config.ansible_inventory.default_filters)

        # Merge additional filters
        if additional_filters:
            filters.update(additional_filters)

        return filters if filters else None

    def _get_host_source(self, host: Host) -> str:
        """Determine the source of a host based on its metadata.

        Args:
            host: Host object

        Returns:
            Source identifier string
        """
        if hasattr(host, 'inventory_file') or 'inventory_file' in host.metadata:
            inventory_file = getattr(host, 'inventory_file', host.metadata.get('inventory_file', ''))
            return f"ansible:{inventory_file}"
        elif hasattr(host, 'platform'):
            platform = getattr(host, 'platform', host.metadata.get('platform', ''))
            if platform in ["vm", "device"]:
                return "netbox"
            elif platform == "ansible":
                return "ansible"

        return "unknown"

    def test_all_connections(self) -> Dict[str, bool]:
        """Test connections to all providers.

        Returns:
            Dictionary mapping provider names to connection status
        """
        results = {}

        for provider in self.providers:
            provider_name = type(provider).__name__
            try:
                results[provider_name] = provider.test_connection()
            except Exception as e:
                self.logger.error(f"Connection test failed for {provider_name}: {e}")
                results[provider_name] = False

        return results

    def get_provider_count(self) -> int:
        """Get the number of initialized providers.

        Returns:
            Number of active providers
        """
        return len(self.providers)

    def get_provider_names(self) -> List[str]:
        """Get names of all initialized providers.

        Returns:
            List of provider class names
        """
        return [type(provider).__name__ for provider in self.providers]
