"""Tests for HostSelector snippets and health helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sshplex.lib.health import HealthStatus
from sshplex.lib.snippets import Snippet
from sshplex.lib.sot.base import Host
from sshplex.lib.ui import host_selector as host_selector_module
from sshplex.lib.ui.host_selector import HostSelector


def make_app() -> HostSelector:
    config = SimpleNamespace(
        health=SimpleNamespace(enabled=True, timeout=0.2, cache_ttl_minutes=5),
        snippets=SimpleNamespace(enabled=True, show_preview=False),
        ssh=SimpleNamespace(port=22),
        sshplex=SimpleNamespace(session_prefix="sshplex"),
        tmux=SimpleNamespace(backend="tmux"),
    )
    app = HostSelector(config)
    app.log_message = Mock()
    app.notify = Mock()
    return app


def test_iterm2_native_snippets_do_not_call_tmux(monkeypatch: pytest.MonkeyPatch) -> None:
    app = make_app()
    app.config.tmux.backend = "iterm2-native"
    app.use_broadcast = True
    run_mock = Mock()
    monkeypatch.setattr(host_selector_module.subprocess, "run", run_mock)

    app._dispatch_snippet_command(
        Snippet(name="uptime", description="Show uptime", command="uptime", tags=[])
    )

    run_mock.assert_not_called()
    app.log_message.assert_called_once()
    assert "iTerm2 native" in app.log_message.call_args.args[0]
    app.notify.assert_called_once()


@pytest.mark.asyncio
async def test_health_checks_uncached_hosts_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app()
    hosts = [Host("host1", "10.0.0.1"), Host("host2", "10.0.0.2")]
    app.get_hosts_to_display = Mock(return_value=hosts)
    app.populate_table = Mock()
    app.update_status = Mock()
    app.update_status_with_mode = Mock()

    started = []
    release = None

    async def fake_check_host(target: str, port: int, timeout: float) -> HealthStatus:
        nonlocal release
        started.append(target)
        if release is None:
            release = asyncio.get_running_loop().create_future()
        if len(started) == 2 and not release.done():
            release.set_result(None)
        await release
        return HealthStatus.HEALTHY

    monkeypatch.setattr(host_selector_module, "check_host", fake_check_host)

    await app._check_health_async()

    assert sorted(started) == ["10.0.0.1", "10.0.0.2"]
    assert all(status == HealthStatus.HEALTHY for status, _ in app.health_cache.values())
    assert app.update_status.call_args.args[0] == "Health check: 2/2"


@pytest.mark.asyncio
async def test_health_check_skips_fresh_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = make_app()
    host = Host("host1", "10.0.0.1")
    app.get_hosts_to_display = Mock(return_value=[host])
    app.populate_table = Mock()
    app.update_status_with_mode = Mock()
    app.health_cache[app._host_key(host)] = (
        HealthStatus.HEALTHY,
        datetime.now() - timedelta(minutes=1),
    )
    check_mock = Mock()
    monkeypatch.setattr(host_selector_module, "check_host", check_mock)

    await app._check_health_async()

    check_mock.assert_not_called()
    app.populate_table.assert_called_once_with([host])
    app.update_status_with_mode.assert_called_once()
