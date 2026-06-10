"""SSHplex host health-check helpers."""

from __future__ import annotations

import asyncio
from enum import Enum


class HealthStatus(str, Enum):
    """Health-check state for a host."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


async def check_host(
    hostname: str, port: int = 22, timeout: float = 2.0
) -> HealthStatus:
    """Check whether a host accepts TCP connections.

    Args:
        hostname: Target hostname or IP.
        port: Target TCP port.
        timeout: Timeout in seconds.

    Returns:
        HealthStatus indicating host reachability.
    """
    try:
        connect_task = asyncio.open_connection(hostname, port)
        reader, writer = await asyncio.wait_for(connect_task, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        _ = reader
        return HealthStatus.HEALTHY
    except Exception:
        return HealthStatus.UNHEALTHY
