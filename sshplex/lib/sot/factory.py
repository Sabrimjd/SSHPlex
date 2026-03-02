"""Source of Truth provider factory for SSHplex."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..cache import HostCache
from ..config import SUPPORTED_SOT_PROVIDER_TYPES
from ..logger import get_logger
from .ansible import AnsibleProvider
from .base import Host, SoTProvider
from .git import GitProvider
from .netbox import NetBoxProvider
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
        self.providers: list[SoTProvider] = []

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

        self._cached_hosts_by_key: dict[str, list[Host]] = {}
        self._cache_lock = threading.RLock()
        self._provider_creators: dict[str, str] = {
            "static": "_create_static_provider",
            "netbox": "_create_netbox_provider_from_import",
            "ansible": "_create_ansible_provider_from_import",
            "consul": "_create_consul_provider",
            "git": "_create_git_provider",
        }

    @staticmethod
    def _normalize_filters(additional_filters: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize optional host filters to a deterministic dictionary."""
        if not additional_filters:
            return {}
        return {str(key): value for key, value in additional_filters.items()}

    def _build_cache_key(self, additional_filters: dict[str, Any] | None) -> str:
        """Build a deterministic cache key based on active filters."""
        normalized = self._normalize_filters(additional_filters)
        if not normalized:
            return "default"
        try:
            return json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
        except TypeError:
            fallback = {key: str(value) for key, value in normalized.items()}
            return json.dumps(fallback, sort_keys=True, separators=(",", ":"))

    def _get_enabled_provider_types(self, configured_imports: list[Any]) -> set[str]:
        """Resolve enabled provider types from config or infer from imports."""
        configured_types = {
            str(provider_type).strip()
            for provider_type in (getattr(self.config.sot, "providers", []) or [])
            if str(provider_type).strip()
        }
        unknown_configured = configured_types.difference(SUPPORTED_SOT_PROVIDER_TYPES)
        if unknown_configured:
            self.logger.warning(
                "Ignoring unknown provider types from sot.providers: "
                f"{sorted(unknown_configured)}"
            )
        configured_types = configured_types.intersection(SUPPORTED_SOT_PROVIDER_TYPES)
        if configured_types:
            return configured_types

        inferred_types = {
            str(getattr(import_config, "type", "")).strip()
            for import_config in configured_imports
            if str(getattr(import_config, "type", "")).strip()
        }
        inferred_types = inferred_types.intersection(SUPPORTED_SOT_PROVIDER_TYPES)
        if inferred_types:
            self.logger.info(
                "No explicit sot.providers configured; inferred provider types from imports: "
                f"{sorted(inferred_types)}"
            )
        return inferred_types

    def initialize_providers(self) -> bool:
        """Initialize all configured SoT providers from import configurations.

        Returns:
            True if at least one provider was successfully initialized
        """
        self.providers = []
        success_count = 0
        attempted_count = 0

        # Check if we have import configurations
        configured_imports = list(getattr(self.config.sot, 'import_', []) or [])
        if not configured_imports:
            self.logger.error("No import configurations found in sot.import")
            return False

        enabled_provider_types = self._get_enabled_provider_types(configured_imports)
        if enabled_provider_types:
            self.logger.info(
                f"Enabled provider types: {sorted(enabled_provider_types)}"
            )

        for import_config in configured_imports:
            try:
                import_type = str(getattr(import_config, "type", "")).strip()
                import_name = str(getattr(import_config, "name", "")).strip() or "unnamed"

                if enabled_provider_types and import_type not in enabled_provider_types:
                    self.logger.info(
                        f"Skipping provider '{import_name}' ({import_type}) because it is disabled"
                    )
                    continue

                attempted_count += 1
                if import_type not in SUPPORTED_SOT_PROVIDER_TYPES:
                    self.logger.error(
                        f"Unknown SoT provider type: {import_type}. "
                        f"Supported types: {list(SUPPORTED_SOT_PROVIDER_TYPES)}"
                    )
                    continue

                creator_name = self._provider_creators.get(import_type)
                if creator_name is None:
                    self.logger.error(f"No provider creator registered for type '{import_type}'")
                    continue

                creator = getattr(self, creator_name, None)
                if creator is None:
                    self.logger.error(
                        f"Provider creator method '{creator_name}' is missing for type '{import_type}'"
                    )
                    continue

                provider: SoTProvider | None = creator(import_config)

                if provider and provider.connect():
                    self.providers.append(provider)
                    success_count += 1
                    self.logger.info(f"Successfully initialized {import_type} provider '{import_name}'")
                else:
                    self.logger.error(f"Failed to initialize {import_type} provider '{import_name}'")

            except Exception as e:
                self.logger.error(f"Error initializing provider: {e}")

        if attempted_count == 0:
            self.logger.error(
                "No providers were initialized because none matched the enabled provider types"
            )
            return False

        self.logger.info(f"Initialized {success_count}/{attempted_count} SoT providers")
        return success_count > 0

    def _create_static_provider(self, import_config: Any) -> StaticProvider | None:
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

    def _create_consul_provider(self, import_config: Any) -> SoTProvider | None:
        """Create Consul provider instance from import configuration.

        Args:
            import_config: Import configuration object

        Returns:
            ConsulProvider instance or None if configuration invalid
        """
        if not import_config.config:
            self.logger.error(f"Consul provider '{import_config.name}' has no configuration")
            return None

        from .consul import ConsulProvider
        return ConsulProvider(
            import_config=import_config
        )

    def _create_git_provider(self, import_config: Any) -> GitProvider | None:
        """Create Git provider instance from import configuration."""
        repo_url = str(getattr(import_config, "repo_url", "") or "").strip()
        if not repo_url:
            self.logger.error(f"Git provider '{import_config.name}' missing required repo_url")
            return None

        cache_root = Path(getattr(self.config.cache, "cache_dir", "~/.cache/sshplex")).expanduser()
        git_cache_dir = cache_root / "git"

        return GitProvider(import_config=import_config, cache_dir=str(git_cache_dir))

    def _create_netbox_provider_from_import(self, import_config: Any) -> NetBoxProvider | None:
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
        provider.provider_name = import_config.name
        provider.import_filters = import_config.default_filters or {}

        return provider

    def _create_ansible_provider_from_import(self, import_config: Any) -> AnsibleProvider | None:
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
        provider.provider_name = import_config.name

        return provider

    def _load_hosts_from_cache(
        self,
        force_refresh: bool,
        additional_filters: dict[str, Any] | None,
    ) -> list[Host] | None:
        """Load hosts from memory/cache when refresh is not requested."""
        if force_refresh:
            return None

        cache_key = self._build_cache_key(additional_filters)
        with self._cache_lock:
            memory_hosts = self._cached_hosts_by_key.get(cache_key)
            if memory_hosts is not None:
                self.logger.debug(f"Returning hosts from memory cache key '{cache_key}'")
                return memory_hosts

        # Disk cache is only used for unfiltered host sets.
        if cache_key != "default":
            return None

        cached_hosts = self.cache.load_hosts()
        if cached_hosts is not None:
            self.logger.info(f"Loaded {len(cached_hosts)} hosts from cache")
            with self._cache_lock:
                self._cached_hosts_by_key[cache_key] = cached_hosts
            return cached_hosts

        return None

    def _save_hosts_to_cache(
        self,
        hosts: list[Host],
        additional_filters: dict[str, Any] | None,
        fetch_mode: str,
    ) -> None:
        """Persist retrieved hosts in cache and memory."""
        cache_key = self._build_cache_key(additional_filters)
        with self._cache_lock:
            self._cached_hosts_by_key[cache_key] = hosts

        # Keep on-disk cache canonical for unfiltered results only.
        if cache_key != "default":
            return

        provider_info = {
            'provider_count': len(self.providers),
            'provider_names': self.get_provider_names(),
            'filters_applied': additional_filters or {},
            'fetch_mode': fetch_mode,
            'cache_key': cache_key,
        }
        self.cache.save_hosts(hosts, provider_info)

    def _deduplicate_hosts(self, hosts: list[Host]) -> list[Host]:
        """Deduplicate hosts and merge metadata/source information."""
        unique_hosts: dict[str, Host] = {}

        for host in hosts:
            key = f"{host.name}:{host.ip}"
            existing = unique_hosts.get(key)

            if existing is None:
                unique_hosts[key] = host
                continue

            existing_sources = existing.metadata.get('sources', [])
            incoming_sources = host.metadata.get('sources', [])

            existing.merge_metadata(host.metadata)

            if isinstance(existing_sources, str):
                existing_sources = [existing_sources]
            elif not isinstance(existing_sources, list):
                existing_sources = [str(existing_sources)] if existing_sources else []

            if isinstance(incoming_sources, str):
                incoming_sources = [incoming_sources]
            elif not isinstance(incoming_sources, list):
                incoming_sources = [str(incoming_sources)] if incoming_sources else []

            merged_sources: list[str] = []
            for source in [
                *existing_sources,
                *incoming_sources,
                self._get_host_source(existing),
                self._get_host_source(host),
            ]:
                source_text = str(source).strip() if source else ""
                if source_text and source_text not in merged_sources:
                    merged_sources.append(source_text)

            if merged_sources:
                existing.merge_metadata({'sources': merged_sources})

        return list(unique_hosts.values())

    def get_all_hosts(self, additional_filters: dict[str, Any] | None = None, force_refresh: bool = False) -> list[Host]:
        """Get hosts from all configured providers with caching support.

        Args:
            additional_filters: Additional filters to apply to all providers
            force_refresh: If True, bypass cache and fetch fresh data from providers

        Returns:
            Combined list of hosts from all providers
        """
        cached_hosts = self._load_hosts_from_cache(force_refresh, additional_filters)
        if cached_hosts is not None:
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

        final_hosts = self._deduplicate_hosts(all_hosts)
        self.logger.info(f"Retrieved {len(final_hosts)} unique hosts from {len(self.providers)} providers")

        self._save_hosts_to_cache(final_hosts, additional_filters, fetch_mode='sequential')

        return final_hosts

    def get_all_hosts_parallel(self, additional_filters: dict[str, Any] | None = None, force_refresh: bool = False, max_workers: int = 4) -> list[Host]:
        """Get hosts from all configured providers in parallel with caching support.

        This method improves performance when multiple providers are configured
        by fetching hosts concurrently instead of sequentially.

        Args:
            additional_filters: Additional filters to apply to all providers
            force_refresh: If True, bypass cache and fetch fresh data from providers
            max_workers: Maximum number of parallel provider queries (default: 4)

        Returns:
            Combined list of hosts from all providers
        """
        cached_hosts = self._load_hosts_from_cache(force_refresh, additional_filters)
        if cached_hosts is not None:
            return cached_hosts

        # Cache miss or force refresh - fetch from providers in parallel
        self.logger.info("Cache miss or refresh requested - fetching hosts from providers in parallel")

        if not self.providers:
            self.logger.error("No SoT providers initialized")
            return []

        all_hosts = []

        # Use ThreadPoolExecutor for parallel fetching
        # Note: IO-bound operations benefit more from threads than processes
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='provider-') as executor:
            # Submit tasks for each provider
            future_to_provider = {}
            for provider in self.providers:
                future = executor.submit(
                    self._fetch_provider_hosts,
                    provider,
                    additional_filters
                )
                future_to_provider[future] = provider

            # Collect results as they complete
            for future in as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    hosts = future.result()
                    provider_name = type(provider).__name__
                    self.logger.info(f"Retrieved {len(hosts)} hosts from {provider_name}")
                    all_hosts.extend(hosts)
                except Exception as e:
                    provider_name = type(provider).__name__
                    self.logger.error(f"Error retrieving hosts from {provider_name}: {e}")

        final_hosts = self._deduplicate_hosts(all_hosts)

        self.logger.info(f"Retrieved {len(final_hosts)} unique hosts from {len(self.providers)} providers")

        self._save_hosts_to_cache(final_hosts, additional_filters, fetch_mode='parallel')

        return final_hosts

    def _fetch_provider_hosts(self, provider: SoTProvider,
                              additional_filters: dict[str, Any] | None) -> list[Host]:
        """Fetch hosts from a single provider with error handling.

        Args:
            provider: SoT provider instance
            additional_filters: Additional filters to apply

        Returns:
            List of hosts from the provider (empty list on error)
        """
        try:
            # Get provider-specific filters
            provider_filters = self._get_provider_filters(provider, additional_filters)

            return provider.get_hosts(filters=provider_filters)
        except Exception as e:
            provider_name = type(provider).__name__
            self.logger.error(f"Error in {provider_name}: {e}")
            return []

    def _get_provider_filters(self, provider: SoTProvider,
                              additional_filters: dict[str, Any] | None) -> dict[str, Any] | None:
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

    def test_all_connections(self) -> dict[str, bool]:
        """Test connections to all providers.

        Returns:
            Dictionary mapping provider names to connection status
        """
        results = {}

        for provider in self.providers:
            provider_name = type(provider).__name__
            provider_config_name = getattr(provider, 'provider_name', provider_name)
            try:
                self.logger.info(f"Testing connection to {provider_config_name} ({provider_name})...")
                start_time = time.time()

                success = provider.test_connection()

                elapsed = time.time() - start_time
                self.logger.info(f"Connection test to {provider_config_name} completed in {elapsed:.2f}s")

                if success:
                    self.logger.info(f"✅ {provider_config_name}: Connection successful")
                else:
                    self.logger.error(f"❌ {provider_config_name}: Connection failed")

                results[provider_name] = success
            except Exception as e:
                self.logger.error(f"❌ Connection test failed for {provider_config_name}: {e}")
                self.logger.exception(f"Full exception details for {provider_config_name}:")
                results[provider_name] = False

        return results

    def get_provider_count(self) -> int:
        """Get the number of initialized providers.

        Returns:
            Number of active providers
        """
        return len(self.providers)

    def get_provider_names(self) -> list[str]:
        """Get names of all initialized providers.

        Returns:
            List of provider class names
        """
        return [type(provider).__name__ for provider in self.providers]

    def get_cache_info(self) -> dict[str, Any] | None:
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
        with self._cache_lock:
            self._cached_hosts_by_key.clear()
        return self.cache.clear_cache()

    def is_cache_valid(self) -> bool:
        """Check if the cache is valid and up-to-date.

        Returns:
            True if cache is valid, False otherwise
        """
        return self.cache.is_cache_valid()

    def sync_git_sources(self, force: bool = False) -> list[dict[str, Any]]:
        """Sync configured git providers and return per-provider statuses."""
        results: list[dict[str, Any]] = []
        providers_to_sync = [provider for provider in self.providers if isinstance(provider, GitProvider)]

        if not providers_to_sync:
            providers_to_sync = self._initialize_git_providers_for_sync()

        for provider in providers_to_sync:
            if not isinstance(provider, GitProvider):
                continue
            try:
                status = provider.sync(force=force)
                results.append(status)
            except Exception as e:
                provider_name = getattr(provider, "provider_name", type(provider).__name__)
                self.logger.error(f"Git sync failed for {provider_name}: {e}")
                results.append(
                    {
                        "provider": provider_name,
                        "status": "error",
                        "message": str(e),
                        "old_commit": None,
                        "new_commit": None,
                        "changed_files": 0,
                    }
                )
        return results

    def _initialize_git_providers_for_sync(self) -> list[GitProvider]:
        """Initialize git providers directly from config for sync-only operations."""
        initialized: list[GitProvider] = []
        configured_imports = list(getattr(self.config.sot, "import_", []) or [])
        if not configured_imports:
            return initialized

        enabled_provider_types = self._get_enabled_provider_types(configured_imports)

        for import_config in configured_imports:
            import_type = str(getattr(import_config, "type", "")).strip()
            if import_type != "git":
                continue

            if enabled_provider_types and import_type not in enabled_provider_types:
                continue

            provider = self._create_git_provider(import_config)
            if provider is None:
                continue
            if provider.connect():
                initialized.append(provider)

        return initialized
