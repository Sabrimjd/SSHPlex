"""Git-backed Source of Truth provider for SSHplex."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from ..logger import get_logger
from .ansible import AnsibleProvider
from .base import Host, SoTProvider


class GitProvider(SoTProvider):
    """Git repository implementation of SoT provider.

    The provider maintains a local mirror under the SSHplex cache directory and
    reads host definitions from YAML files in that checkout.
    """

    def __init__(self, import_config: Any, cache_dir: str | None = None) -> None:
        self.import_config = import_config
        self.logger = get_logger()

        self.name = str(getattr(import_config, "name", "git-source") or "git-source")
        self.provider_name = self.name
        self.repo_url = str(getattr(import_config, "repo_url", "") or "").strip()
        self.branch = str(getattr(import_config, "branch", "main") or "main").strip() or "main"
        self.source_pattern = str(getattr(import_config, "source_pattern", "") or "").strip()
        self.source_path = str(getattr(import_config, "path", "hosts") or "hosts").strip() or "hosts"
        self.file_glob = str(getattr(import_config, "file_glob", "**/*.y*ml") or "**/*.y*ml").strip() or "**/*.y*ml"
        self.auto_pull = bool(getattr(import_config, "auto_pull", True))
        self.pull_interval_seconds = int(getattr(import_config, "pull_interval_seconds", 300) or 300)
        self.profile = str(getattr(import_config, "profile", "solo") or "solo").strip() or "solo"
        self.priority = int(getattr(import_config, "priority", 100) or 100)
        self.pull_strategy = str(getattr(import_config, "pull_strategy", "ff-only") or "ff-only").strip() or "ff-only"
        self.inventory_format = self._normalize_inventory_format(
            str(getattr(import_config, "inventory_format", "static") or "static")
        )

        configured_filters = getattr(import_config, "default_filters", {}) or {}
        if isinstance(configured_filters, dict):
            self.ansible_filters = configured_filters
        else:
            self.ansible_filters = {}

        root = Path(cache_dir or "~/.cache/sshplex/git").expanduser()
        repo_hash = hashlib.sha1(f"{self.repo_url}::{self.branch}".encode()).hexdigest()[:12]
        self.repo_dir = root / repo_hash
        self._sync_meta_file = self.repo_dir / ".sshplex_git_sync.json"

    def connect(self) -> bool:
        """Ensure local git checkout is available and optionally auto-pull."""
        if not self.repo_url:
            self.logger.error(f"Git provider '{self.name}' missing repo_url")
            return False

        if not self._ensure_repository():
            return False

        if self.auto_pull:
            result = self.sync(force=False)
            return result.get("status") in {"updated", "up_to_date", "skipped"}

        return True

    def test_connection(self) -> bool:
        """Test git provider by ensuring repository is reachable and checked out."""
        if not self._ensure_repository():
            return False
        return bool(self._git_output(["rev-parse", "HEAD"]))

    def sync(self, force: bool = False) -> dict[str, Any]:
        """Sync local checkout from remote.

        Returns a status dict for UI notifications.
        """
        result: dict[str, Any] = {
            "provider": self.name,
            "profile": self.profile,
            "status": "error",
            "message": "sync failed",
            "old_commit": None,
            "new_commit": None,
            "changed_files": 0,
        }

        if self.pull_strategy != "ff-only":
            result.update(
                {
                    "status": "skipped",
                    "message": f"unsupported pull strategy '{self.pull_strategy}'",
                }
            )
            return result

        if not self._ensure_repository():
            result["message"] = "repository unavailable"
            return result

        old_commit = self._git_output(["rev-parse", "HEAD"]) or None
        result["old_commit"] = old_commit

        if not force and not self.auto_pull:
            result.update({"status": "skipped", "message": "auto_pull disabled"})
            return result

        if not force and self.pull_interval_seconds > 0:
            metadata = self._load_sync_metadata()
            last_sync = float(metadata.get("last_sync_epoch", 0.0) or 0.0)
            age = time.time() - last_sync
            if last_sync > 0 and age < self.pull_interval_seconds:
                result.update({"status": "skipped", "message": "pull interval not reached"})
                result["new_commit"] = old_commit
                return result

        dirty = self._git_output(["status", "--porcelain"])
        if dirty:
            result.update(
                {
                    "status": "skipped",
                    "message": "local changes detected in mirror checkout",
                    "new_commit": old_commit,
                }
            )
            return result

        fetch_ok = self._run_git(["fetch", "origin", self.branch])
        if not fetch_ok:
            result["message"] = "git fetch failed"
            return result

        counts = self._git_output(["rev-list", "--left-right", "--count", f"HEAD...origin/{self.branch}"])
        ahead = 0
        behind = 0
        if counts:
            parts = counts.replace("\t", " ").split()
            if len(parts) >= 2:
                try:
                    ahead = int(parts[0])
                    behind = int(parts[1])
                except ValueError:
                    ahead = 0
                    behind = 0

        if behind == 0:
            new_commit = self._git_output(["rev-parse", "HEAD"]) or old_commit
            result.update(
                {
                    "status": "up_to_date",
                    "message": "already up to date",
                    "new_commit": new_commit,
                }
            )
            self._save_sync_metadata(new_commit)
            return result

        if ahead > 0:
            result.update(
                {
                    "status": "skipped",
                    "message": "local mirror diverged from remote; manual reset required",
                    "new_commit": old_commit,
                }
            )
            return result

        if not self._run_git(["pull", "--ff-only", "origin", self.branch]):
            result["message"] = "git pull --ff-only failed"
            return result

        new_commit = self._git_output(["rev-parse", "HEAD"]) or old_commit
        changed_files = self._count_changed_files(old_commit, new_commit)
        result.update(
            {
                "status": "updated",
                "message": "updated from remote",
                "new_commit": new_commit,
                "changed_files": changed_files,
            }
        )
        self._save_sync_metadata(new_commit)
        return result

    def get_hosts(self, filters: dict[str, Any] | None = None) -> list[Host]:
        """Retrieve hosts from YAML files in the git checkout."""
        if not self._ensure_repository():
            return []

        if self.source_pattern:
            files = self._resolve_source_pattern_files(self.source_pattern)
        else:
            root = self.repo_dir / self.source_path
            files = self._resolve_source_files(root)
        if not files:
            location = self.source_pattern if self.source_pattern else self.source_path
            selection = self.source_pattern if self.source_pattern else self.file_glob
            self.logger.warning(
                f"Git provider '{self.name}' found no host files for source '{location}' matching '{selection}'"
            )
            return []

        current_commit = self._git_output(["rev-parse", "HEAD"]) or ""
        hosts: list[Host] = []

        for file_path in files:
            rel_file = str(file_path.relative_to(self.repo_dir))
            try:
                payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            except Exception as e:
                self.logger.error(f"Git provider '{self.name}' failed reading {file_path}: {e}")
                continue

            if self.inventory_format == "ansible":
                hosts.extend(
                    self._extract_hosts_from_ansible_payload(
                        payload=payload,
                        inventory_path=rel_file,
                        current_commit=current_commit,
                        filters=filters,
                    )
                )
                continue

            for host_data in self._extract_hosts_from_payload(payload):
                name = str(host_data.get("name", "")).strip()
                ip = str(host_data.get("ip", "")).strip()
                if not name or not ip:
                    self.logger.warning(
                        f"Git provider '{self.name}' skipped host in {file_path} because name/ip is missing"
                    )
                    continue

                metadata = {k: v for k, v in host_data.items() if k not in {"name", "ip"}}
                metadata["provider"] = self.name
                metadata["sources"] = [self.name]
                host = Host(name=name, ip=ip, **metadata)
                self._attach_git_metadata(host, rel_file, current_commit)
                hosts.append(host)

        hosts = self._deduplicate_hosts(hosts)
        if filters:
            generic_filters = {
                key: value
                for key, value in filters.items()
                if key not in {"groups", "exclude_groups", "host_patterns"}
            }
            hosts = self._apply_filters(hosts, generic_filters)

        self.logger.info(f"Git provider '{self.name}' returned {len(hosts)} hosts")
        return hosts

    def _ensure_repository(self) -> bool:
        """Ensure local mirror checkout exists and branch is selected."""
        if shutil.which("git") is None:
            self.logger.error("git binary is required for git SoT provider")
            return False

        self.repo_dir.parent.mkdir(parents=True, exist_ok=True)

        if (self.repo_dir / ".git").exists():
            return self._checkout_branch()

        if self.repo_dir.exists():
            shutil.rmtree(self.repo_dir, ignore_errors=True)

        cmd = [
            "git",
            "clone",
            "--branch",
            self.branch,
            "--single-branch",
            self.repo_url,
            str(self.repo_dir),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            self.logger.error(
                f"Git provider '{self.name}' failed to clone '{self.repo_url}' ({self.branch}): "
                f"{completed.stderr.strip()}"
            )
            return False

        return self._checkout_branch()

    def _checkout_branch(self) -> bool:
        """Ensure desired branch is checked out."""
        if self._run_git(["checkout", self.branch]):
            return True

        # Branch may not exist locally yet; try creating tracking branch.
        return self._run_git(["checkout", "-B", self.branch, f"origin/{self.branch}"])

    def _run_git(self, args: list[str]) -> bool:
        """Run git command in repository and return success status."""
        completed = subprocess.run(
            ["git", "-C", str(self.repo_dir), *args],
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return True
        self.logger.debug(
            f"Git provider '{self.name}' command failed: git {' '.join(args)} :: "
            f"{completed.stderr.strip()}"
        )
        return False

    def _git_output(self, args: list[str]) -> str:
        """Run git command and return stripped stdout (empty string on failure)."""
        completed = subprocess.run(
            ["git", "-C", str(self.repo_dir), *args],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return ""
        return (completed.stdout or "").strip()

    def _resolve_source_files(self, root: Path) -> list[Path]:
        """Resolve YAML files to parse for host data."""
        if root.is_file():
            return [root]
        if not root.exists() or not root.is_dir():
            return []

        matched = [path for path in root.glob(self.file_glob) if path.is_file()]
        return sorted(matched)

    def _resolve_source_pattern_files(self, source_pattern: str) -> list[Path]:
        """Resolve source pattern directly from repository root."""
        normalized = source_pattern.strip().lstrip("/")
        if not normalized:
            return []

        target = self.repo_dir / normalized
        if target.is_file():
            return [target]
        if target.is_dir():
            return sorted(path for path in target.glob("**/*.y*ml") if path.is_file())

        try:
            matched = [path for path in self.repo_dir.glob(normalized) if path.is_file()]
            return sorted(matched)
        except Exception as e:
            self.logger.error(
                f"Git provider '{self.name}' invalid source pattern '{source_pattern}': {e}"
            )
            return []

    @staticmethod
    def _extract_hosts_from_payload(payload: Any) -> list[dict[str, Any]]:
        """Normalize supported YAML payload shapes into host dictionaries."""
        if payload is None:
            return []

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            if isinstance(payload.get("hosts"), list):
                return [item for item in payload["hosts"] if isinstance(item, dict)]

            if "name" in payload and "ip" in payload:
                return [payload]

            rows: list[dict[str, Any]] = []
            for key, value in payload.items():
                if not isinstance(value, dict):
                    continue
                ip = value.get("ip") or value.get("host") or value.get("hostname")
                if not ip:
                    continue
                row = {"name": str(value.get("name", key)), "ip": str(ip)}
                row.update({k: v for k, v in value.items() if k not in {"name", "ip", "host", "hostname"}})
                rows.append(row)
            return rows

        return []

    def _count_changed_files(self, old_commit: str | None, new_commit: str | None) -> int:
        """Count changed files between two commits."""
        if not old_commit or not new_commit or old_commit == new_commit:
            return 0
        output = self._git_output(["diff", "--name-only", old_commit, new_commit])
        if not output:
            return 0
        return len([line for line in output.splitlines() if line.strip()])

    def _load_sync_metadata(self) -> dict[str, Any]:
        """Load last sync metadata from local file."""
        try:
            if not self._sync_meta_file.exists():
                return {}
            loaded = json.loads(self._sync_meta_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                return loaded
            return {}
        except Exception:
            return {}

    def _save_sync_metadata(self, commit: str | None) -> None:
        """Persist sync metadata."""
        try:
            self._sync_meta_file.write_text(
                json.dumps(
                    {
                        "last_sync_epoch": time.time(),
                        "last_commit": commit or "",
                    }
                ),
                encoding="utf-8",
            )
        except Exception as e:
            self.logger.debug(f"Git provider '{self.name}' could not persist sync metadata: {e}")

    @staticmethod
    def _normalize_inventory_format(raw_format: str) -> str:
        """Normalize inventory format alias to a supported value."""
        value = raw_format.strip().lower()
        if value in {"ansible", "ansible-inventory", "inventory"}:
            return "ansible"
        return "static"

    def _extract_hosts_from_ansible_payload(
        self,
        payload: Any,
        inventory_path: str,
        current_commit: str,
        filters: dict[str, Any] | None,
    ) -> list[Host]:
        """Extract hosts from ansible-style inventory payload."""
        if not isinstance(payload, dict):
            self.logger.warning(
                f"Git provider '{self.name}' expects ansible inventory mappings in {inventory_path}; skipping"
            )
            return []

        ansible_filters = dict(self.ansible_filters)
        if filters:
            for key in ("groups", "exclude_groups", "host_patterns"):
                if key in filters:
                    ansible_filters[key] = filters[key]

        parser = AnsibleProvider(inventory_paths=[])
        parser.provider_name = self.name
        extracted_hosts = parser._extract_hosts_from_inventory(payload, inventory_path, ansible_filters)
        for host in extracted_hosts:
            host.metadata["provider"] = self.name
            host.metadata["sources"] = [self.name]
            self._attach_git_metadata(host, inventory_path, current_commit)
        return extracted_hosts

    def _attach_git_metadata(self, host: Host, rel_file: str, current_commit: str) -> None:
        """Attach git metadata to an extracted host object."""
        host.metadata["git_repo"] = self.repo_url
        host.metadata["git_branch"] = self.branch
        host.metadata["git_profile"] = self.profile
        host.metadata["git_priority"] = self.priority
        host.metadata["git_commit"] = current_commit
        host.metadata["git_file"] = rel_file
        host.metadata["git_inventory_format"] = self.inventory_format

    def _deduplicate_hosts(self, hosts: list[Host]) -> list[Host]:
        """Deduplicate hosts by name+ip while merging metadata."""
        unique: dict[str, Host] = {}
        for host in hosts:
            key = f"{host.name}:{host.ip}"
            existing = unique.get(key)
            if existing is None:
                unique[key] = host
                continue

            existing.metadata.update(host.metadata)
            for metadata_key, metadata_value in host.metadata.items():
                setattr(existing, metadata_key, metadata_value)

            existing_sources = existing.metadata.get("sources", []) or []
            incoming_sources = host.metadata.get("sources", []) or []
            if isinstance(existing_sources, list) and isinstance(incoming_sources, list):
                merged_sources = []
                for source in [*existing_sources, *incoming_sources]:
                    if source not in merged_sources:
                        merged_sources.append(source)
                existing.metadata["sources"] = merged_sources

        return list(unique.values())

    def _apply_filters(self, hosts: list[Host], filters: dict[str, Any]) -> list[Host]:
        """Apply generic filters to host list."""
        filtered = hosts

        if "tags" in filters and filters["tags"]:
            required_tags = filters["tags"]
            if isinstance(required_tags, str):
                required_tags = [required_tags]
            if isinstance(required_tags, list):
                filtered = [
                    host
                    for host in filtered
                    if any(
                        tag in self._coerce_tags(getattr(host, "tags", []) or [])
                        for tag in required_tags
                    )
                ]

        if "name_pattern" in filters and filters["name_pattern"]:
            import re

            pattern = re.compile(str(filters["name_pattern"]))
            filtered = [host for host in filtered if pattern.search(host.name)]

        for key, value in filters.items():
            if key in {"tags", "name_pattern", "groups", "exclude_groups", "host_patterns"}:
                continue
            filtered = [
                host
                for host in filtered
                if getattr(host, key, host.metadata.get(key)) == value
            ]

        return filtered

    @staticmethod
    def _coerce_tags(value: Any) -> list[str]:
        """Normalize host tags to a list for filtering."""
        if isinstance(value, list):
            return [str(tag) for tag in value]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return []
