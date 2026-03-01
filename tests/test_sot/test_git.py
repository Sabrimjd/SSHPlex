"""Tests for git-backed SoT provider."""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

from sshplex.lib.sot.git import GitProvider


def _git_import(**overrides):
    defaults = {
        "name": "git-source",
        "repo_url": "git@github.com:acme/hosts.git",
        "branch": "main",
        "source_pattern": "hosts/**/*.y*ml",
        "path": "hosts",
        "file_glob": "**/*.y*ml",
        "auto_pull": True,
        "pull_interval_seconds": 300,
        "profile": "solo",
        "priority": 100,
        "pull_strategy": "ff-only",
        "inventory_format": "static",
        "default_filters": {},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _bind_repo(provider: GitProvider, repo_dir: Path) -> None:
    provider.repo_dir = repo_dir
    provider._sync_meta_file = repo_dir / ".sshplex_git_sync.json"


def test_extract_hosts_from_payload_variants() -> None:
    rows = GitProvider._extract_hosts_from_payload(
        {"hosts": [{"name": "a", "ip": "10.0.0.1"}]}
    )
    assert rows == [{"name": "a", "ip": "10.0.0.1"}]

    rows = GitProvider._extract_hosts_from_payload(
        {"node-a": {"ip": "10.0.0.2", "role": "web"}}
    )
    assert rows == [{"name": "node-a", "ip": "10.0.0.2", "role": "web"}]


def test_get_hosts_reads_yaml_and_populates_git_metadata(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "repo"
    hosts_dir = repo_dir / "hosts"
    hosts_dir.mkdir(parents=True)
    (hosts_dir / "servers.yaml").write_text(
        "- name: web-01\n  ip: 10.0.0.10\n  tags: [web]\n",
        encoding="utf-8",
    )

    provider = GitProvider(_git_import(), cache_dir=str(tmp_path / "cache"))
    _bind_repo(provider, repo_dir)

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", lambda args: "deadbee")

    hosts = provider.get_hosts()
    assert len(hosts) == 1
    host = hosts[0]
    assert host.name == "web-01"
    assert host.ip == "10.0.0.10"
    assert host.metadata["provider"] == "git-source"
    assert host.metadata["git_profile"] == "solo"
    assert host.metadata["git_priority"] == 100
    assert host.metadata["git_commit"] == "deadbee"
    assert host.metadata["git_file"] == "hosts/servers.yaml"


def test_sync_skips_when_pull_interval_not_reached(tmp_path, monkeypatch) -> None:
    provider = GitProvider(_git_import(pull_interval_seconds=300), cache_dir=str(tmp_path / "cache"))
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)
    _bind_repo(provider, repo_dir)
    provider._sync_meta_file.write_text(
        json.dumps({"last_sync_epoch": time.time(), "last_commit": "abc1234"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", lambda args: "abc1234")

    result = provider.sync(force=False)
    assert result["status"] == "skipped"
    assert "interval" in str(result["message"])


def test_sync_updates_when_remote_is_behind(tmp_path, monkeypatch) -> None:
    provider = GitProvider(_git_import(), cache_dir=str(tmp_path / "cache"))
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)
    _bind_repo(provider, repo_dir)

    state = {"rev_parse_calls": 0}

    def fake_git_output(args):
        if args[:2] == ["rev-parse", "HEAD"]:
            state["rev_parse_calls"] += 1
            return "aaaa111" if state["rev_parse_calls"] == 1 else "bbbb222"
        if args[:2] == ["status", "--porcelain"]:
            return ""
        if args[:3] == ["rev-list", "--left-right", "--count"]:
            return "0 2"
        if args[:2] == ["diff", "--name-only"]:
            return "hosts/a.yaml\nhosts/b.yaml\n"
        return ""

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", fake_git_output)
    monkeypatch.setattr(provider, "_run_git", lambda args: True)

    result = provider.sync(force=True)
    assert result["status"] == "updated"
    assert result["old_commit"] == "aaaa111"
    assert result["new_commit"] == "bbbb222"
    assert result["changed_files"] == 2


def test_sync_skips_when_mirror_checkout_is_dirty(tmp_path, monkeypatch) -> None:
    provider = GitProvider(_git_import(), cache_dir=str(tmp_path / "cache"))
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)
    _bind_repo(provider, repo_dir)

    def fake_git_output(args):
        if args[:2] == ["rev-parse", "HEAD"]:
            return "aaaa111"
        if args[:2] == ["status", "--porcelain"]:
            return " M hosts/local.yaml"
        return ""

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", fake_git_output)

    result = provider.sync(force=True)
    assert result["status"] == "skipped"
    assert "local changes" in str(result["message"])


def test_get_hosts_supports_ansible_inventory_format(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "repo"
    inv_dir = repo_dir / "inventory"
    inv_dir.mkdir(parents=True)
    (inv_dir / "prod.yml").write_text(
        """
all:
  children:
    webservers:
      hosts:
        web1:
          ansible_host: 10.10.1.11
          ansible_user: ubuntu
    databases:
      hosts:
        db1:
          ansible_host: 10.10.2.21
        db2:
          ansible_connection: local
""".strip()
        + "\n",
        encoding="utf-8",
    )

    provider = GitProvider(
        _git_import(
            path="inventory",
            source_pattern="inventory/**/*.y*ml",
            inventory_format="ansible",
            default_filters={"groups": ["webservers"]},
        ),
        cache_dir=str(tmp_path / "cache"),
    )
    _bind_repo(provider, repo_dir)

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", lambda args: "cafef00")

    hosts = provider.get_hosts()
    assert len(hosts) == 1
    host = hosts[0]
    assert host.name == "web1"
    assert host.ip == "10.10.1.11"
    assert host.metadata["provider"] == "git-source"
    assert host.metadata["git_inventory_format"] == "ansible"
    assert host.metadata["git_file"] == "inventory/prod.yml"


def test_get_hosts_ansible_inventory_allows_runtime_group_override(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "repo"
    inv_dir = repo_dir / "inventory"
    inv_dir.mkdir(parents=True)
    (inv_dir / "prod.yml").write_text(
        """
all:
  children:
    webservers:
      hosts:
        web1:
          ansible_host: 10.10.1.11
    databases:
      hosts:
        db1:
          ansible_host: 10.10.2.21
""".strip()
        + "\n",
        encoding="utf-8",
    )

    provider = GitProvider(
        _git_import(
            path="inventory",
            source_pattern="inventory/**/*.y*ml",
            inventory_format="ansible",
            default_filters={"groups": ["webservers"]},
        ),
        cache_dir=str(tmp_path / "cache"),
    )
    _bind_repo(provider, repo_dir)

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", lambda args: "cafef00")

    hosts = provider.get_hosts(filters={"groups": ["databases"]})
    assert len(hosts) == 1
    assert hosts[0].name == "db1"


def test_get_hosts_ansible_inventory_respects_exclude_groups(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "repo"
    inv_dir = repo_dir / "inventory"
    inv_dir.mkdir(parents=True)
    (inv_dir / "prod.yml").write_text(
        """
all:
  children:
    webservers:
      hosts:
        web1:
          ansible_host: 10.10.1.11
    databases:
      hosts:
        db1:
          ansible_host: 10.10.2.21
""".strip()
        + "\n",
        encoding="utf-8",
    )

    provider = GitProvider(
        _git_import(
            path="inventory",
            source_pattern="inventory/**/*.y*ml",
            inventory_format="ansible",
        ),
        cache_dir=str(tmp_path / "cache"),
    )
    _bind_repo(provider, repo_dir)

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", lambda args: "cafef00")

    hosts = provider.get_hosts(filters={"exclude_groups": ["databases"]})
    assert len(hosts) == 1
    assert hosts[0].name == "web1"


def test_get_hosts_ansible_inventory_applies_host_patterns(tmp_path, monkeypatch) -> None:
    repo_dir = tmp_path / "repo"
    inv_dir = repo_dir / "inventory"
    inv_dir.mkdir(parents=True)
    (inv_dir / "prod.yml").write_text(
        """
all:
  children:
    app:
      hosts:
        app-01:
          ansible_host: 10.10.1.11
        app-02:
          ansible_host: 10.10.1.12
""".strip()
        + "\n",
        encoding="utf-8",
    )

    provider = GitProvider(
        _git_import(
            path="inventory",
            source_pattern="inventory/**/*.y*ml",
            inventory_format="ansible",
        ),
        cache_dir=str(tmp_path / "cache"),
    )
    _bind_repo(provider, repo_dir)

    monkeypatch.setattr(provider, "_ensure_repository", lambda: True)
    monkeypatch.setattr(provider, "_git_output", lambda args: "cafef00")

    hosts = provider.get_hosts(filters={"host_patterns": [r"app-02$"]})
    assert len(hosts) == 1
    assert hosts[0].name == "app-02"
