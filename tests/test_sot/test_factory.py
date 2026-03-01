"""Tests for SoTFactory behavior and merge consistency."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sshplex.lib.sot.base import Host
from sshplex.lib.sot.factory import SoTFactory


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


class DummyProvider:
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


def _make_config(imports: list[SimpleNamespace], providers: list[str]) -> SimpleNamespace:
    """Build a minimal config object for SoTFactory tests."""
    return SimpleNamespace(
        sot=SimpleNamespace(import_=imports, providers=providers),
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
