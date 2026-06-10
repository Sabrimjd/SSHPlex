"""Tests for host health-check helpers."""

from __future__ import annotations

import asyncio

from sshplex.lib.health import HealthStatus, check_host


def test_check_host_returns_unhealthy_for_unreachable_port() -> None:
    status = asyncio.run(check_host("127.0.0.1", port=1, timeout=0.2))
    assert status == HealthStatus.UNHEALTHY


def test_check_host_returns_healthy_for_open_port() -> None:
    async def _handler(
        _reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.close()
        await writer.wait_closed()

    async def _run() -> None:
        server = await asyncio.start_server(_handler, "127.0.0.1", 0)
        try:
            sockets = server.sockets or []
            assert sockets
            port = int(sockets[0].getsockname()[1])
            status = await check_host("127.0.0.1", port=port, timeout=0.5)
            assert status == HealthStatus.HEALTHY
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(_run())
