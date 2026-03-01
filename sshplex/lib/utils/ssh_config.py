"""Helpers for resolving SSH config values."""

from __future__ import annotations

import shlex
import subprocess


def resolve_ssh_effective_config(host_or_alias: str) -> dict[str, str]:
    """Resolve effective SSH options with `ssh -G`.

    Returns a dict of lowercase key -> value. Empty dict if unavailable.
    """
    target = (host_or_alias or "").strip()
    if not target:
        return {}

    try:
        proc = subprocess.run(
            ["/usr/bin/ssh", "-G", target],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return {}

    if proc.returncode != 0:
        return {}

    resolved: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or " " not in line:
            continue
        key, value = line.split(" ", 1)
        resolved[key.strip().lower()] = value.strip()
    return resolved


def mask_sensitive(value: str) -> str:
    """Mask sensitive path-ish values for UI preview."""
    val = (value or "").strip()
    if not val:
        return val
    if val.startswith("~"):
        return "~/<hidden>"
    if val.startswith("/"):
        return "/<hidden>"
    return val


def build_ssh_command_preview(host_or_alias: str, username: str, port: int, key_path: str) -> str:
    """Build a short human-readable command preview."""
    parts = ["/usr/bin/ssh"]
    if key_path:
        parts.extend(["-i", mask_sensitive(key_path)])
    if port and port != 22:
        parts.extend(["-p", str(port)])
    if username:
        parts.append(f"{username}@{host_or_alias}")
    else:
        parts.append(host_or_alias)
    return " ".join(shlex.quote(p) for p in parts)
