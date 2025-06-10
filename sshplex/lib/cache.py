"""SSHplex host cache management for optimized startup performance."""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .logger import get_logger
from .sot.base import Host


class HostCache:
    """Cache manager for storing and retrieving hosts from different SoT providers."""

    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_hours: int = 24):
        """Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files (defaults to ~/cache/sshplex)
            cache_ttl_hours: Cache time-to-live in hours (default 24 hours)
        """
        self.logger = get_logger()

        if cache_dir is None:
            cache_dir = os.path.expanduser("~/cache/sshplex")

        self.cache_dir = Path(cache_dir)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_file = self.cache_dir / "hosts.yaml"
        self.metadata_file = self.cache_dir / "cache_metadata.yaml"

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def is_cache_valid(self) -> bool:
        """Check if the cache is valid and not expired.

        Returns:
            True if cache exists and is not expired, False otherwise
        """
        if not self.cache_file.exists() or not self.metadata_file.exists():
            return False

        try:
            with open(self.metadata_file, 'r') as f:
                metadata = yaml.safe_load(f)

            if not metadata or 'timestamp' not in metadata:
                return False

            cache_time = datetime.fromisoformat(metadata['timestamp'])
            return datetime.now() - cache_time < self.cache_ttl

        except Exception as e:
            self.logger.warning(f"Failed to validate cache: {e}")
            return False

    def save_hosts(self, hosts: List[Host], provider_info: Dict[str, Any]) -> bool:
        """Save hosts to cache with metadata.

        Args:
            hosts: List of Host objects to cache
            provider_info: Information about the providers used

        Returns:
            True if cache was saved successfully, False otherwise
        """
        try:
            # Prepare hosts data for serialization
            hosts_data = []
            for host in hosts:
                host_dict = {
                    'name': host.name,
                    'ip': host.ip,
                    'metadata': host.metadata
                }
                hosts_data.append(host_dict)

            # Save hosts data
            with open(self.cache_file, 'w') as f:
                yaml.dump(hosts_data, f, default_flow_style=False, sort_keys=True)

            # Save metadata
            cache_metadata = {
                'timestamp': datetime.now().isoformat(),
                'host_count': len(hosts),
                'providers': provider_info,
                'cache_version': '1.0'
            }

            with open(self.metadata_file, 'w') as f:
                yaml.dump(cache_metadata, f, default_flow_style=False, sort_keys=True)

            self.logger.info(f"Successfully cached {len(hosts)} hosts to {self.cache_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save hosts to cache: {e}")
            return False

    def load_hosts(self) -> Optional[List[Host]]:
        """Load hosts from cache.

        Returns:
            List of Host objects if cache is valid and loaded successfully, None otherwise
        """
        if not self.is_cache_valid():
            return None

        try:
            with open(self.cache_file, 'r') as f:
                hosts_data = yaml.safe_load(f)

            if not hosts_data:
                return []

            hosts = []
            for host_dict in hosts_data:
                host = Host(
                    name=host_dict['name'],
                    ip=host_dict['ip'],
                    **host_dict.get('metadata', {})
                )
                hosts.append(host)

            self.logger.info(f"Successfully loaded {len(hosts)} hosts from cache")
            return hosts

        except Exception as e:
            self.logger.error(f"Failed to load hosts from cache: {e}")
            return None

    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """Get cache metadata information.

        Returns:
            Dictionary with cache information or None if cache doesn't exist
        """
        if not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file, 'r') as f:
                raw_metadata = yaml.safe_load(f)

            # Validate that metadata is a dictionary
            if not isinstance(raw_metadata, dict):
                self.logger.warning("Cache metadata is not a valid dictionary")
                return None

            metadata: Dict[str, Any] = raw_metadata

            if metadata and 'timestamp' in metadata:
                cache_time = datetime.fromisoformat(metadata['timestamp'])
                metadata['age_hours'] = (datetime.now() - cache_time).total_seconds() / 3600
                metadata['is_valid'] = self.is_cache_valid()

            return metadata

        except Exception as e:
            self.logger.error(f"Failed to read cache metadata: {e}")
            return None

    def clear_cache(self) -> bool:
        """Clear the cache by removing cache files.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()

            self.logger.info("Cache cleared successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return False

    def refresh_needed(self) -> bool:
        """Check if cache refresh is needed (cache is invalid or expired).

        Returns:
            True if refresh is needed, False otherwise
        """
        return not self.is_cache_valid()
