"""Tests for SSHplex host cache management."""

import pytest
import tempfile
import yaml
from pathlib import Path
from datetime import datetime, timedelta

from sshplex.lib.cache import HostCache
from sshplex.lib.sot.base import Host


class TestHostCache:
    """Tests for HostCache class."""

    @pytest.fixture
    def cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache(self, cache_dir):
        """Create a HostCache instance with temporary directory."""
        return HostCache(cache_dir=str(cache_dir), cache_ttl_hours=1)

    @pytest.fixture
    def sample_hosts(self):
        """Create sample hosts for testing."""
        return [
            Host(name="host1", ip="10.0.1.1", description="Test host 1", provider="test"),
            Host(name="host2", ip="10.0.1.2", description="Test host 2", provider="test"),
            Host(name="host3", ip="10.0.1.3", description="Test host 3", provider="test"),
        ]

    def test_init_creates_directory(self, cache_dir):
        """Test that cache directory is created if it doesn't exist."""
        new_dir = cache_dir / "new_cache"
        cache = HostCache(cache_dir=str(new_dir))
        assert new_dir.exists()
        assert cache.cache_dir == new_dir

    def test_default_values(self, cache_dir):
        """Test default cache configuration."""
        cache = HostCache(cache_dir=str(cache_dir))
        assert cache.cache_ttl == timedelta(hours=24)
        assert cache.cache_file.name == "hosts.yaml"
        assert cache.metadata_file.name == "cache_metadata.yaml"

    def test_custom_ttl(self, cache_dir):
        """Test custom TTL configuration."""
        cache = HostCache(cache_dir=str(cache_dir), cache_ttl_hours=48)
        assert cache.cache_ttl == timedelta(hours=48)

    def test_save_hosts(self, cache, sample_hosts):
        """Test saving hosts to cache."""
        provider_info = {
            'provider_count': 1,
            'provider_names': ['test'],
            'filters_applied': {}
        }
        
        result = cache.save_hosts(sample_hosts, provider_info)
        assert result is True
        assert cache.cache_file.exists()
        assert cache.metadata_file.exists()

    def test_load_hosts(self, cache, sample_hosts):
        """Test loading hosts from cache."""
        # Save hosts first
        provider_info = {'provider_count': 1}
        cache.save_hosts(sample_hosts, provider_info)
        
        # Load hosts
        loaded = cache.load_hosts()
        assert loaded is not None
        assert len(loaded) == len(sample_hosts)
        
        # Verify host data
        for i, host in enumerate(loaded):
            assert host.name == sample_hosts[i].name
            assert host.ip == sample_hosts[i].ip

    def test_load_hosts_cache_expired(self, cache, sample_hosts):
        """Test that expired cache returns None."""
        # Save hosts
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        
        # Manually expire the cache
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        with open(cache.metadata_file, 'r') as f:
            metadata = yaml.safe_load(f)
        metadata['timestamp'] = old_time
        with open(cache.metadata_file, 'w') as f:
            yaml.dump(metadata, f)
        
        # Try to load - should return None
        loaded = cache.load_hosts()
        assert loaded is None

    def test_is_cache_valid_empty(self, cache):
        """Test cache validation when cache doesn't exist."""
        assert cache.is_cache_valid() is False

    def test_is_cache_valid_fresh(self, cache, sample_hosts):
        """Test cache validation with fresh cache."""
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        assert cache.is_cache_valid() is True

    def test_is_cache_valid_expired(self, cache, sample_hosts):
        """Test cache validation with expired cache."""
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        
        # Manually expire
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        with open(cache.metadata_file, 'r') as f:
            metadata = yaml.safe_load(f)
        metadata['timestamp'] = old_time
        with open(cache.metadata_file, 'w') as f:
            yaml.dump(metadata, f)
        
        assert cache.is_cache_valid() is False

    def test_get_cache_info(self, cache, sample_hosts):
        """Test getting cache information."""
        # No cache initially
        info = cache.get_cache_info()
        assert info is None
        
        # Save and get info
        cache.save_hosts(sample_hosts, {'provider_count': 1, 'provider_names': ['test']})
        info = cache.get_cache_info()
        
        assert info is not None
        assert info['host_count'] == len(sample_hosts)
        assert 'age_hours' in info
        assert 'is_valid' in info

    def test_clear_cache(self, cache, sample_hosts):
        """Test clearing the cache."""
        # Save hosts
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        assert cache.cache_file.exists()
        assert cache.metadata_file.exists()
        
        # Clear cache
        result = cache.clear_cache()
        assert result is True
        assert not cache.cache_file.exists()
        assert not cache.metadata_file.exists()

    def test_refresh_needed(self, cache, sample_hosts):
        """Test refresh_needed method."""
        # No cache - refresh needed
        assert cache.refresh_needed() is True
        
        # Fresh cache - no refresh needed
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        assert cache.refresh_needed() is False

    def test_empty_hosts_list(self, cache):
        """Test saving and loading empty hosts list."""
        result = cache.save_hosts([], {'provider_count': 0})
        assert result is True
        
        loaded = cache.load_hosts()
        assert loaded is not None
        assert len(loaded) == 0

    def test_host_metadata_preserved(self, cache):
        """Test that host metadata is preserved through cache."""
        hosts = [
            Host(
                name="host1",
                ip="10.0.1.1",
                description="Test",
                custom_field="custom_value",
                provider="test"
            )
        ]
        
        cache.save_hosts(hosts, {'provider_count': 1})
        loaded = cache.load_hosts()
        
        assert loaded[0].metadata.get('custom_field') == 'custom_value'
        assert loaded[0].metadata.get('provider') == 'test'

    def test_concurrent_access(self, cache, sample_hosts):
        """Test that cache handles concurrent read/write gracefully."""
        # Save initial data
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        
        # Simulate concurrent access by reading and writing
        loaded = cache.load_hosts()
        assert loaded is not None
        
        # Save again while potentially reading
        new_hosts = [Host(name="new", ip="10.0.2.1", provider="test")]
        cache.save_hosts(new_hosts, {'provider_count': 1})
        
        # Should still work
        loaded = cache.load_hosts()
        assert len(loaded) == 1
        assert loaded[0].name == "new"

    def test_corrupted_cache_file(self, cache):
        """Test handling of corrupted cache file."""
        # Write invalid data
        with open(cache.cache_file, 'w') as f:
            f.write("not valid yaml: [")
        
        # Should return None gracefully
        loaded = cache.load_hosts()
        assert loaded is None

    def test_corrupted_metadata_file(self, cache, sample_hosts):
        """Test handling of corrupted metadata file."""
        # Save hosts
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        
        # Corrupt metadata
        with open(cache.metadata_file, 'w') as f:
            f.write("invalid: yaml: [")
        
        # Cache should be considered invalid
        assert cache.is_cache_valid() is False

    def test_missing_timestamp_in_metadata(self, cache, sample_hosts):
        """Test handling of metadata without timestamp."""
        cache.save_hosts(sample_hosts, {'provider_count': 1})
        
        # Remove timestamp from metadata
        with open(cache.metadata_file, 'r') as f:
            metadata = yaml.safe_load(f)
        del metadata['timestamp']
        with open(cache.metadata_file, 'w') as f:
            yaml.dump(metadata, f)
        
        assert cache.is_cache_valid() is False
