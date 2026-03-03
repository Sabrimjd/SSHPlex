"""SSHplex command snippets management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .logger import get_logger


@dataclass
class Snippet:
    """A reusable command snippet."""

    name: str
    description: str
    command: str
    tags: list[str]


class SnippetManager:
    """Manage loading and saving SSHplex command snippets."""

    def __init__(self, config_dir: str | Path = "~/.config/sshplex"):
        """Initialize snippet manager.

        Args:
            config_dir: Directory for SSHplex config files.
        """
        self.logger = get_logger()
        self.config_dir = Path(config_dir).expanduser()

    @property
    def snippets_file(self) -> Path:
        """Path to snippets YAML file."""
        return self.config_dir / "snippets.yaml"

    def load_snippets(self) -> list[Snippet]:
        """Load snippets from YAML file.

        Returns:
            List of snippets, or an empty list if file is missing/invalid.
        """
        if not self.snippets_file.exists():
            return []

        try:
            with self.snippets_file.open() as handle:
                raw_data = yaml.safe_load(handle)

            if not raw_data:
                return []

            if not isinstance(raw_data, list):
                self.logger.warning("Snippets file is invalid: expected a list")
                return []

            snippets: list[Snippet] = []
            for item in raw_data:
                if not isinstance(item, dict):
                    self.logger.warning(f"Skipping invalid snippet entry: {item}")
                    continue

                name = item.get("name")
                description = item.get("description")
                command = item.get("command")
                tags = item.get("tags", [])

                if (
                    not isinstance(name, str)
                    or not isinstance(description, str)
                    or not isinstance(command, str)
                ):
                    self.logger.warning(f"Skipping snippet with invalid fields: {item}")
                    continue

                if not isinstance(tags, list) or not all(
                    isinstance(tag, str) for tag in tags
                ):
                    self.logger.warning(f"Skipping snippet with invalid tags: {item}")
                    continue

                snippets.append(
                    Snippet(
                        name=name,
                        description=description,
                        command=command,
                        tags=tags,
                    )
                )

            return snippets

        except (yaml.YAMLError, OSError) as exc:
            self.logger.error(f"Failed to load snippets: {exc}")
            return []
        except Exception as exc:
            self.logger.error(f"Unexpected error loading snippets: {exc}")
            return []

    def save_snippets(self, snippets: list[Snippet]) -> None:
        """Save snippets to YAML file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        payload = [
            {
                "name": snippet.name,
                "description": snippet.description,
                "command": snippet.command,
                "tags": snippet.tags,
            }
            for snippet in snippets
        ]

        with self.snippets_file.open("w") as handle:
            yaml.safe_dump(payload, handle, default_flow_style=False, sort_keys=False)

    @staticmethod
    def get_default_snippets() -> list[Snippet]:
        """Return built-in default snippets."""
        return [
            Snippet(
                name="Disk Usage",
                description="Show disk usage",
                command="df -h",
                tags=["system", "disk"],
            ),
            Snippet(
                name="Memory Usage",
                description="Show memory stats",
                command="free -h",
                tags=["system", "memory"],
            ),
            Snippet(
                name="CPU Info",
                description="Show CPU information",
                command="lscpu",
                tags=["system", "cpu"],
            ),
            Snippet(
                name="Top Processes",
                description="Show top processes",
                command="top -b -n 1 | head -20",
                tags=["system", "processes"],
            ),
            Snippet(
                name="System Uptime",
                description="Show system uptime",
                command="uptime",
                tags=["system", "uptime"],
            ),
            Snippet(
                name="Network Connections",
                description="Show network connections",
                command="ss -tunap",
                tags=["network", "connections"],
            ),
            Snippet(
                name="Quick Log Tail",
                description="Tail last 50 lines of syslog",
                command="tail -n 50 /var/log/syslog",
                tags=["logs", "system"],
            ),
            Snippet(
                name="Disk I/O",
                description="Show disk I/O statistics",
                command="iostat -xz 1 3",
                tags=["system", "io"],
            ),
            Snippet(
                name="Memory Details",
                description="Detailed memory info",
                command="cat /proc/meminfo",
                tags=["system", "memory"],
            ),
            Snippet(
                name="Service Status",
                description="Check systemd services",
                command="systemctl list-units --type=service --state=running | head -20",
                tags=["system", "services"],
            ),
        ]

    def ensure_snippets_file(self) -> None:
        """Create snippets file with defaults if missing."""
        if self.snippets_file.exists():
            return

        self.save_snippets(self.get_default_snippets())
        self.logger.info(f"Created default snippets file at {self.snippets_file}")
