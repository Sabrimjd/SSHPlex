"""Tests for ConfigEditor table-column picker helpers."""

from __future__ import annotations

from sshplex.lib.ui.config_editor import ConfigEditorScreen


def test_parse_columns_csv_deduplicates_and_trims() -> None:
    parsed = ConfigEditorScreen._parse_columns_csv(" name, ip ,name, , source ,ip ")
    assert parsed == ["name", "ip", "source"]


def test_categorize_table_columns_groups_by_origin_and_sot() -> None:
    categorized = ConfigEditorScreen._categorize_table_columns(
        [
            "name",
            "ip",
            "source",
            "alias",
            "ansible_user",
            "git_repo",
            "netbox_site",
            "consul_service",
            "custom_field",
        ]
    )

    assert "name" in categorized["Common"]
    assert "source" in categorized["Origin / Source Tracking"]
    assert "alias" in categorized["Static / SSH Overrides"]
    assert "ansible_user" in categorized["Ansible SoT"]
    assert "git_repo" in categorized["Git SoT"]
    assert "netbox_site" in categorized["NetBox SoT"]
    assert "consul_service" in categorized["Consul SoT"]
    assert "custom_field" in categorized["Other"]
