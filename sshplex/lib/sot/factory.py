"""Source of Truth provider factory for SSHplex."""

from typing import List, Dict, Any, Optional
from ..logger import get_logger
from ..cache import HostCache
from .base import SoTProvider, Host
from .netbox import NetBoxProvider
from .ansible import AnsibleProvider
from .static import StaticProvider


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

        # Initialize cache with configuration
        cache_config = getattr(config, 'cache', None)
        if cache_config and cache_config.enabled:
            self.cache = HostCache(
                cache_dir=cache_config.cache_dir,
                cache_ttl_hours=cache_config.ttl_hours
            )
        else:
            # Use default cache settings if not configured
            self.cache = HostCache()

        self._cached_hosts: Optional[List[Host]] = None

    def initialize_providers(self) -> bool:
        """Initialize all configured SoT providers from import configurations.

        Returns:
            True if at least one provider was successfully initialized
        """
        self.providers = []
        success_count = 0

        # Check if we have import configurations
        if not hasattr(self.config.sot, 'import_') or not self.config.sot.import_:
            self.logger.error("No import configurations found in sot.import")
            return False

        for import_config in self.config.sot.import_:
            try:
                provider: Optional[SoTProvider] = None

                if import_config.type == "static":
                    provider = self._create_static_provider(import_config)
                elif import_config.type == "netbox":
                    provider = self._create_netbox_provider_from_import(import_config)
                elif import_config.type == "ansible":
                    provider = self._create_ansible_provider_from_import(import_config)
                else:
                    self.logger.error(f"Unknown SoT provider type: {import_config.type}")
                    continue

                if provider and provider.connect():
                    self.providers.append(provider)
                    success_count += 1
                    self.logger.info(f"Successfully initialized {import_config.type} provider '{import_config.name}'")
                else:
                    self.logger.error(f"Failed to initialize {import_config.type} provider '{import_config.name}'")

            except Exception as e:
                self.logger.error(f"Error initializing {import_config.type} provider '{import_config.name}': {e}")

        self.logger.info(f"Initialized {success_count}/{len(self.config.sot.import_)} SoT providers")
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

    def _create_static_provider(self, import_config: Any) -> Optional[StaticProvider]:
        """Create Static provider instance from import configuration.

        Args:
            import_config: Import configuration object

        Returns:
            StaticProvider instance or None if configuration invalid
        """
        if not import_config.hosts:
            self.logger.error(f"Static provider '{import_config.name}' has no hosts configured")
            return None

        return StaticProvider(
            name=import_config.name,
            hosts=import_config.hosts
        )

    def _create_netbox_provider_from_import(self, import_config: Any) -> Optional[NetBoxProvider]:
        """Create NetBox provider instance from import configuration.

        Args:
            import_config: Import configuration object

        Returns:
            NetBoxProvider instance or None if configuration invalid
        """
        if not import_config.url or not import_config.token:
            self.logger.error(f"NetBox provider '{import_config.name}' missing required url or token")
            return None

        provider = NetBoxProvider(
            url=import_config.url,
            token=import_config.token,
            verify_ssl=import_config.verify_ssl if import_config.verify_ssl is not None else True,
            timeout=import_config.timeout or 30
        )

        # Store additional attributes
        setattr(provider, 'provider_name', import_config.name)
        setattr(provider, 'import_filters', import_config.default_filters or {})

        return provider

    def _create_ansible_provider_from_import(self, import_config: Any) -> Optional[AnsibleProvider]:
        """Create Ansible provider instance from import configuration.

        Args:
            import_config: Import configuration object

        Returns:
            AnsibleProvider instance or None if configuration invalid
        """
        if not import_config.inventory_paths:
            self.logger.error(f"Ansible provider '{import_config.name}' has no inventory_paths configured")
            return None

        provider = AnsibleProvider(
            inventory_paths=import_config.inventory_paths,
            filters=import_config.default_filters or {}
        )

        # Store additional attributes
        setattr(provider, 'provider_name', import_config.name)

        return provider

    def get_all_hosts(self, additional_filters: Optional[Dict[str, Any]] = None, force_refresh: bool = False) -> List[Host]:
        """Get hosts from all configured providers with caching support.

        Args:
            additional_filters: Additional filters to apply to all providers
            force_refresh: If True, bypass cache and fetch fresh data from providers

        Returns:
            Combined list of hosts from all providers
        """
        # If we have cached hosts and not forcing refresh, return them
        if not force_refresh and self._cached_hosts is not None:
            self.logger.debug("Returning already loaded hosts from memory")
            return self._cached_hosts

        # Try to load from cache first (unless forcing refresh)
        if not force_refresh:
            cached_hosts = self.cache.load_hosts()
            if cached_hosts is not None:
                self.logger.info(f"Loaded {len(cached_hosts)} hosts from cache")
                self._cached_hosts = cached_hosts
                return cached_hosts

        # Cache miss or force refresh - fetch from providers
        self.logger.info("Cache miss or refresh requested - fetching hosts from providers")

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

        # Save to cache
        provider_info = {
            'provider_count': len(self.providers),
            'provider_names': self.get_provider_names(),
            'filters_applied': additional_filters or {}
        }
        self.cache.save_hosts(final_hosts, provider_info)

        # Store in memory for quick access
        self._cached_hosts = final_hosts

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

        # Add provider-specific default filters from import configuration
        import_filters = getattr(provider, 'import_filters', None)
        if import_filters:
            filters.update(import_filters)
        elif isinstance(provider, NetBoxProvider) and self.config.netbox:
            # Fallback to old configuration structure if available
            filters.update(self.config.netbox.default_filters)
        elif isinstance(provider, AnsibleProvider) and self.config.ansible_inventory:
            # Fallback to old configuration structure if available
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
        # First check if the host already has provider information
        provider = getattr(host, 'provider', None)
        if provider:
            return str(provider)

        # Check metadata for provider information
        if 'provider' in host.metadata:
            return str(host.metadata['provider'])

        # Legacy source detection logic
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

    def refresh_cache(self, additional_filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Force refresh of the host cache from all providers.

        Args:
            additional_filters: Additional filters to apply to all providers

        Returns:
            Freshly loaded hosts from all providers
        """
        self.logger.info("Forcing cache refresh from all providers")
        return self.get_all_hosts(additional_filters=additional_filters, force_refresh=True)

    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """Get cache information.

        Returns:
            Dictionary with cache metadata or None if no cache exists
        """
        return self.cache.get_cache_info()

    def clear_cache(self) -> bool:
        """Clear the host cache.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
        self._cached_hosts = None
        return self.cache.clear_cache()

    def is_cache_valid(self) -> bool:
        """Check if the cache is valid and up-to-date.

        Returns:
            True if cache is valid, False otherwise
        """
        return self.cache.is_cache_valid()
