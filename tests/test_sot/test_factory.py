"""Tests for SoTFactory behavior and merge consistency."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sshplex.lib.sot.base import Host, SoTProvider
from sshplex.lib.sot.factory import SoTFactory
from sshplex.lib.sot.git import GitProvider


class InMemoryCache:
    """Simple cache test double used to avoid filesystem coupling."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
        self.saved_hosts = None
        self.saved_info = None

    def load_hosts(self):  # noqa: ANN001
        return None

    def save_hosts(self, hosts, provider_info):  # noqa: ANN001
        self.saved_hosts = hosts
        self.saved_info = provider_info
        return True

    def get_cache_info(self):  # noqa: ANN001
        return None

    def clear_cache(self):  # noqa: ANN001
        return True


class DummyProvider(SoTProvider):
    """Minimal provider stub for deterministic host-return tests."""

    def __init__(self, provider_name: str, hosts: list[Host]) -> None:
        self.provider_name = provider_name
        self._hosts = hosts

    def connect(self) -> bool:
        return True

    def test_connection(self) -> bool:
        return True

    def get_hosts(self, filters=None):  # noqa: ANN001
        _ = filters
        return [Host(name=host.name, ip=host.ip, **dict(host.metadata)) for host in self._hosts]


def _make_config(
    imports: list[SimpleNamespace],
    providers: list[str],
) -> SimpleNamespace:
    """Build a minimal config object for SoTFactory tests."""
    sot_config = SimpleNamespace(import_=imports, providers=providers)

    return SimpleNamespace(
        sot=sot_config,
        cache=SimpleNamespace(enabled=True, cache_dir="~/.cache/sshplex", ttl_hours=24),
        netbox=None,
        ansible_inventory=None,
    )


def test_initialize_providers_respects_enabled_provider_types() -> None:
    """Only imports matching enabled provider types should be initialized."""
    imports = [
        SimpleNamespace(name="static-src", type="static", hosts=[{"name": "h1", "ip": "10.0.0.1"}]),
        SimpleNamespace(
            name="nb-src",
            type="netbox",
            url="https://netbox.example.com",
            token="token",
            verify_ssl=True,
            timeout=30,
            default_filters={},
        ),
    ]
    config = _make_config(imports=imports, providers=["static"])

    static_provider = MagicMock()
    static_provider.connect.return_value = True
    netbox_provider = MagicMock()
    netbox_provider.connect.return_value = True

    with patch("sshplex.lib.sot.factory.HostCache", InMemoryCache):
        factory = SoTFactory(config)

    with patch.object(factory, "_create_static_provider", return_value=static_provider) as create_static, patch.object(
        factory,
        "_create_netbox_provider_from_import",
        return_value=netbox_provider,
    ) as create_netbox:
        assert factory.initialize_providers() is True

    create_static.assert_called_once()
    create_netbox.assert_not_called()
    assert factory.providers == [static_provider]


def test_initialize_providers_includes_git_when_enabled() -> None:
    """Git imports should initialize when git provider type is enabled."""
    imports = [
        SimpleNamespace(
            name="git-src",
            type="git",
            repo_url="git@github.com:acme/hosts.git",
            branch="main",
            auto_pull=True,
            pull_interval_seconds=300,
            priority=100,
            pull_strategy="ff-only",
        )
    ]
    config = _make_config(imports=imports, providers=["git"])

    git_provider = MagicMock()
    git_provider.connect.return_value = True

    with patch("sshplex.lib.sot.factory.HostCache", InMemoryCache):
        factory = SoTFactory(config)

    with patch.object(factory, "_create_git_provider", return_value=git_provider) as create_git:
        assert factory.initialize_providers() is True

    create_git.assert_called_once()
    assert factory.providers == [git_provider]


def test_initialize_providers_infers_enabled_types_when_providers_not_set() -> None:
    """Missing sot.providers should behave as enable-all configured imports."""
    imports = [
        SimpleNamespace(name="static-src", type="static", hosts=[{"name": "h1", "ip": "10.0.0.1"}]),
        SimpleNamespace(
            name="nb-src",
            type="netbox",
            url="https://netbox.example.com",
            token="token",
            verify_ssl=True,
            timeout=30,
            default_filters={},
        ),
    ]
    # Empty providers means infer enabled types from configured imports.
    config = _make_config(imports=imports, providers=[])

    static_provider = MagicMock()
    static_provider.connect.return_value = True
    netbox_provider = MagicMock()
    netbox_provider.connect.return_value = True

    with patch("sshplex.lib.sot.factory.HostCache", InMemoryCache):
        factory = SoTFactory(config)

    with patch.object(factory, "_create_static_provider", return_value=static_provider) as create_static, patch.object(
        factory,
        "_create_netbox_provider_from_import",
        return_value=netbox_provider,
    ) as create_netbox:
        assert factory.initialize_providers() is True

    create_static.assert_called_once()
    create_netbox.assert_called_once()
    assert factory.providers == [static_provider, netbox_provider]


def test_get_all_hosts_merge_is_consistent_between_modes() -> None:
    """Sequential and parallel paths should produce equivalent merged host metadata."""
    config = _make_config(imports=[], providers=[])

    with patch("sshplex.lib.sot.factory.HostCache", InMemoryCache):
        factory = SoTFactory(config)

    host_from_static = Host(
        name="node1",
        ip="10.0.0.1",
        provider="static-a",
        sources=["static-a"],
        role="web",
    )
    host_from_ansible = Host(
        name="node1",
        ip="10.0.0.1",
        provider="ansible-b",
        sources=["ansible-b"],
        env="prod",
    )

    factory.providers = [
        DummyProvider("static-a", [host_from_static]),
        DummyProvider("ansible-b", [host_from_ansible]),
    ]

    sequential_hosts = factory.get_all_hosts(force_refresh=True)
    parallel_hosts = factory.get_all_hosts_parallel(force_refresh=True, max_workers=2)

    assert len(sequential_hosts) == 1
    assert len(parallel_hosts) == 1

    seq_sources = set(sequential_hosts[0].metadata.get("sources", []))
    par_sources = set(parallel_hosts[0].metadata.get("sources", []))

    assert {"static-a", "ansible-b"}.issubset(seq_sources)
    assert seq_sources == par_sources
    assert sequential_hosts[0].metadata.get("role") == "web"
    assert parallel_hosts[0].metadata.get("env") == "prod"

    assert isinstance(factory.cache, InMemoryCache)
    assert factory.cache.saved_info is not None
    assert factory.cache.saved_info["fetch_mode"] == "parallel"


def test_get_all_hosts_uses_filter_aware_memory_cache() -> None:
    """Different filters should not reuse each other's in-memory cache entries."""
    config = _make_config(imports=[], providers=[])

    with patch("sshplex.lib.sot.factory.HostCache", InMemoryCache):
        factory = SoTFactory(config)

    class FilterAwareProvider(DummyProvider):
        def __init__(self) -> None:
            super().__init__("dynamic", [])
            self.calls: list[dict[str, str]] = []

        def get_hosts(self, filters=None):  # noqa: ANN001
            active_filters = dict(filters or {})
            self.calls.append({str(k): str(v) for k, v in active_filters.items()})
            role = str(active_filters.get("role", "unknown"))
            return [
                Host(
                    name=f"node-{role}",
                    ip="10.0.0.10" if role == "web" else "10.0.0.20",
                    provider="dynamic",
                    role=role,
                    sources=["dynamic"],
                )
            ]

    provider = FilterAwareProvider()
    factory.providers = [provider]

    web_hosts = factory.get_all_hosts(additional_filters={"role": "web"}, force_refresh=False)
    db_hosts = factory.get_all_hosts(additional_filters={"role": "db"}, force_refresh=False)
    cached_web_hosts = factory.get_all_hosts(additional_filters={"role": "web"}, force_refresh=False)

    assert web_hosts[0].metadata["role"] == "web"
    assert db_hosts[0].metadata["role"] == "db"
    assert cached_web_hosts[0].metadata["role"] == "web"
    assert len(provider.calls) == 2


def test_sync_git_sources_initializes_git_providers_without_full_init(tmp_path) -> None:
    """sync_git_sources should work even when non-git providers are not initialized."""
    imports = [
        SimpleNamespace(
            name="git-src",
            type="git",
            repo_url="git@github.com:acme/hosts.git",
            branch="main",
            auto_pull=True,
            pull_interval_seconds=300,
            priority=100,
            pull_strategy="ff-only",
        )
    ]
    config = _make_config(imports=imports, providers=["git"])

    with patch("sshplex.lib.sot.factory.HostCache", InMemoryCache):
        factory = SoTFactory(config)

    provider = GitProvider(imports[0], cache_dir=str(tmp_path / "git-cache"))
    provider.connect = MagicMock(return_value=True)  # type: ignore[method-assign]
    provider.sync = MagicMock(  # type: ignore[method-assign]
        return_value={
            "provider": "git-src",
            "status": "updated",
            "message": "updated from remote",
            "old_commit": "aaaa111",
            "new_commit": "bbbb222",
            "changed_files": 2,
        }
    )

    with patch.object(factory, "_create_git_provider", return_value=provider):
        results = factory.sync_git_sources(force=True)

    assert results and results[0]["status"] == "updated"
    provider.connect.assert_called_once()
    provider.sync.assert_called_once_with(force=True)
