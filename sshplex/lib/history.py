"""SSHplex recent/favorites host history management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class HostRecord:
    """Persisted host record used for recent/favorite tracking."""

    name: str
    ip: str
    last_connected: str
    favorite: bool = False


class HistoryManager:
    """Store and retrieve recent and favorite hosts."""

    def __init__(self, config_dir: str | Path = "~/.config/sshplex") -> None:
        self.config_dir = Path(config_dir).expanduser()

    @property
    def history_file(self) -> Path:
        return self.config_dir / "history.yaml"

    def _load_records(self) -> list[HostRecord]:
        if not self.history_file.exists():
            return []

        try:
            with self.history_file.open() as handle:
                data = yaml.safe_load(handle) or []
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        records: list[HostRecord] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            ip = item.get("ip")
            last_connected = item.get("last_connected", "")
            favorite = bool(item.get("favorite", False))
            if not isinstance(name, str) or not isinstance(ip, str):
                continue
            if not isinstance(last_connected, str):
                last_connected = ""
            records.append(
                HostRecord(
                    name=name,
                    ip=ip,
                    last_connected=last_connected,
                    favorite=favorite,
                )
            )
        return records

    def _save_records(self, records: list[HostRecord]) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "name": record.name,
                "ip": record.ip,
                "last_connected": record.last_connected,
                "favorite": record.favorite,
            }
            for record in records
        ]
        with self.history_file.open("w") as handle:
            yaml.safe_dump(payload, handle, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _host_key(name: str, ip: str) -> str:
        return f"{name}|{ip}"

    def add_recent(self, name: str, ip: str, max_recent: int = 20) -> None:
        records = self._load_records()
        key = self._host_key(name, ip)
        now = datetime.now().isoformat()

        by_key = {self._host_key(record.name, record.ip): record for record in records}
        existing = by_key.get(key)
        favorite = existing.favorite if existing else False
        by_key[key] = HostRecord(
            name=name, ip=ip, last_connected=now, favorite=favorite
        )

        ordered = sorted(
            by_key.values(),
            key=lambda record: record.last_connected,
            reverse=True,
        )
        self._save_records(ordered[:max_recent])

    def set_favorite(self, name: str, ip: str, favorite: bool) -> None:
        records = self._load_records()
        key = self._host_key(name, ip)
        by_key = {self._host_key(record.name, record.ip): record for record in records}
        existing = by_key.get(key)
        by_key[key] = HostRecord(
            name=name,
            ip=ip,
            last_connected=existing.last_connected if existing else "",
            favorite=favorite,
        )
        self._save_records(list(by_key.values()))

    def is_favorite(self, name: str, ip: str) -> bool:
        key = self._host_key(name, ip)
        for record in self._load_records():
            if self._host_key(record.name, record.ip) == key:
                return record.favorite
        return False

    def get_favorites(self) -> list[HostRecord]:
        return [record for record in self._load_records() if record.favorite]

    def get_recent(self, limit: int = 20) -> list[HostRecord]:
        records = sorted(
            self._load_records(),
            key=lambda record: record.last_connected,
            reverse=True,
        )
        return records[:limit]
