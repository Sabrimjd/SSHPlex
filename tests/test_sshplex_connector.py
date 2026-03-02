"""Tests for SSH command construction hardening."""

from __future__ import annotations

import shlex
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from sshplex.lib.sot.base import Host
from sshplex.sshplex_connector import SSHplexConnector


def _build_connector(config: SimpleNamespace) -> SSHplexConnector:
    connector = SSHplexConnector.__new__(SSHplexConnector)
    connector.config = config
    connector.logger = MagicMock()
    return connector


def _base_config() -> SimpleNamespace:
    return SimpleNamespace(
        ssh=SimpleNamespace(
            strict_host_key_checking=False,
            user_known_hosts_file="",
            timeout=10,
            proxy=[],
            retry=SimpleNamespace(enabled=False, max_attempts=1, delay_seconds=1, exponential_backoff=False),
            username="admin",
            key_path="~/.ssh/id_ed25519",
            port=22,
        ),
    )


def test_build_ssh_command_quotes_key_and_known_hosts_paths() -> None:
    """SSH command should preserve paths containing spaces."""
    config = _base_config()
    config.ssh.user_known_hosts_file = "~/.ssh/known hosts"
    connector = _build_connector(config)
    host = Host(name="web-01", ip="10.0.0.10", provider="static")

    command = connector._build_ssh_command(
        host=host,
        username="admin",
        key_path="~/.ssh/private keys/id test",
        port=22,
    )
    parts = shlex.split(command)

    expanded_key = str(Path("~/.ssh/private keys/id test").expanduser())
    expanded_known_hosts = str(Path("~/.ssh/known hosts").expanduser())

    assert parts[0] == "TERM=xterm-256color"
    assert parts[1] == "/usr/bin/ssh"
    assert parts[parts.index("-i") + 1] == expanded_key
    assert f"UserKnownHostsFile={expanded_known_hosts}" in parts


def test_build_ssh_command_accepts_proxy_key_with_tilde_path() -> None:
    """Proxy command should include expanded proxy key path."""
    config = _base_config()
    config.ssh.proxy = [
        SimpleNamespace(
            name="proxy-a",
            imports=["static-a"],
            host="proxy.example.com",
            username="jumper",
            key_path="~/.ssh/proxy key",
        )
    ]
    connector = _build_connector(config)
    host = Host(name="db-01", ip="10.0.0.20", provider="static-a")

    command = connector._build_ssh_command(host=host, username="admin", key_path=None, port=22)
    parts = shlex.split(command)

    proxy_option = next(
        (parts[idx + 1] for idx, value in enumerate(parts) if value == "-o" and idx + 1 < len(parts) and parts[idx + 1].startswith("ProxyCommand=")),
        "",
    )

    assert proxy_option.startswith("ProxyCommand=/usr/bin/ssh ")
    assert str(Path("~/.ssh/proxy key").expanduser()) in proxy_option
