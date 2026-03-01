"""SSHplex Configuration Editor Screen."""

import contextlib
from pathlib import Path
from typing import Any, Dict, List

import yaml
from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
)

from ..config import (
    MUX_BACKEND_LABELS,
    SOT_PROVIDER_LABELS,
    SUPPORTED_MUX_BACKENDS,
    SUPPORTED_SOT_PROVIDER_TYPES,
    Config,
    get_default_config_path,
)


def _form_field(
    field_id: str,
    label: str,
    widget: Any,
    description: str = "",
) -> Vertical:
    """Create a standardized form field with label, widget, and optional description."""
    children: List[Any] = [Label(f"{label}:", classes="form-label")]
    if description:
        children.append(Static(description, classes="form-description"))
    widget.id = field_id
    children.append(widget)
    container = Vertical(*children, classes="form-field")
    return container


def _form_row(*fields: Vertical) -> Horizontal:
    """Create a compact horizontal row of form fields."""
    return Horizontal(*fields, classes="form-row")


class TableColumnsPickerScreen(ModalScreen[list[str] | None]):
    """Modal picker for table columns with grouped checkboxes."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "apply", "Apply", show=True, priority=True),
    ]

    CSS = """
    TableColumnsPickerScreen {
        align: center middle;
    }

    #columns-picker-dialog {
        layout: vertical;
        width: 88%;
        height: 86%;
        border: thick $primary;
        background: $surface;
        padding: 0 1;
    }

    #columns-picker-title {
        height: 1;
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 0;
    }

    #columns-picker-subtitle {
        height: 1;
        color: $text-muted;
        text-style: italic;
        margin-bottom: 0;
    }

    #columns-picker-scroll {
        height: 1fr;
        border: round $secondary;
        padding: 0 1;
        margin-bottom: 0;
    }

    .columns-picker-category {
        height: 1;
        margin-top: 1;
        margin-bottom: 0;
        color: $primary;
        text-style: bold;
    }

    .columns-picker-grid {
        grid-size: 3;
        grid-columns: 1fr 1fr 1fr;
        grid-gutter: 0 1;
        width: 1fr;
        height: auto;
        margin-bottom: 0;
    }

    .columns-picker-checkbox {
        height: auto;
        width: 1fr;
        color: $text;
        margin-bottom: 0;
    }

    #columns-picker-actions {
        height: 4;
        align: center middle;
        padding: 0;
    }

    #columns-picker-actions Button {
        height: 3;
        min-width: 12;
        margin: 0 1;
    }
    """

    def __init__(
        self,
        categorized_columns: Dict[str, List[str]],
        selected_columns: List[str],
        detected_columns: List[str],
    ) -> None:
        super().__init__()
        self._categorized_columns = categorized_columns
        self._selected_columns = list(selected_columns)
        self._detected_columns = list(detected_columns)
        self._column_by_checkbox_id: Dict[str, str] = {}
        self._checkbox_id_by_column: Dict[str, str] = {}
        ordered: List[str] = []
        for columns in categorized_columns.values():
            for column in columns:
                if column not in ordered:
                    ordered.append(column)
        self._ordered_columns = ordered

    def compose(self) -> ComposeResult:
        with Vertical(id="columns-picker-dialog"):
            yield Static("Table Columns Picker", id="columns-picker-title")
            yield Static(
                "Select columns by category (SoT, origin, SSH). Use Ctrl+S to apply.",
                id="columns-picker-subtitle",
            )

            with VerticalScroll(id="columns-picker-scroll"):
                checkbox_idx = 1
                selected_set = set(self._selected_columns)
                for category, columns in self._categorized_columns.items():
                    if not columns:
                        continue
                    yield Static(category, classes="columns-picker-category")

                    checkboxes: List[Checkbox] = []
                    for column in columns:
                        checkbox_id = f"col-picker-{checkbox_idx}"
                        self._column_by_checkbox_id[checkbox_id] = column
                        self._checkbox_id_by_column[column] = checkbox_id
                        checkboxes.append(
                            Checkbox(
                                column,
                                value=column in selected_set,
                                id=checkbox_id,
                                classes="columns-picker-checkbox",
                                compact=True,
                            )
                        )
                        checkbox_idx += 1

                    yield Grid(*checkboxes, classes="columns-picker-grid")

            with Horizontal(id="columns-picker-actions"):
                yield Button("Detected", id="btn-columns-select-detected", variant="primary")
                yield Button("All", id="btn-columns-select-all", variant="default")
                yield Button("None", id="btn-columns-select-none", variant="default")
                yield Button("Apply", id="btn-columns-apply", variant="success")
                yield Button("Cancel", id="btn-columns-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-columns-select-detected":
            detected = [col for col in self._detected_columns if col in self._checkbox_id_by_column]
            if detected:
                self._set_selected_columns(detected)
            else:
                self.app.notify("No detected columns available", title="Columns", timeout=2)
            return
        if btn_id == "btn-columns-select-all":
            self._set_selected_columns(self._ordered_columns)
            return
        if btn_id == "btn-columns-select-none":
            self._set_selected_columns([])
            return
        if btn_id == "btn-columns-apply":
            self.action_apply()
            return
        if btn_id == "btn-columns-cancel":
            self.action_cancel()

    def _set_selected_columns(self, selected_columns: List[str]) -> None:
        selected = set(selected_columns)
        for checkbox_id, column in self._column_by_checkbox_id.items():
            with contextlib.suppress(Exception):
                checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                checkbox.value = column in selected

    def _get_selected_columns(self) -> List[str]:
        selected: List[str] = []
        for column in self._ordered_columns:
            checkbox_id = self._checkbox_id_by_column.get(column)
            if not checkbox_id:
                continue
            with contextlib.suppress(Exception):
                checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                if checkbox.value:
                    selected.append(column)
        return selected

    def action_apply(self) -> None:
        selected = self._get_selected_columns()
        if not selected:
            selected = ["name", "ip"]
        self.dismiss(selected)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfigEditorScreen(ModalScreen[bool]):
    """Modal screen for editing sshplex.yaml configuration."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("q", "cancel", "Cancel", show=False),
        Binding("ctrl+s", "save", "Save", show=True, priority=True),
    ]

    CSS = """
    ConfigEditorScreen {
        align: center middle;
    }

    #config-editor-dialog {
        layout: vertical;
        width: 96%;
        height: 92%;
        border: thick $primary;
        background: $surface;
        padding: 0 1;
    }

    #editor-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 0;
        width: 100%;
    }

    #editor-status {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
        margin-top: 0;
    }

    #editor-buttons {
        height: 4;
        dock: bottom;
        align: center middle;
        padding: 0;
    }

    #editor-buttons Button {
        height: 3;
        min-width: 14;
        margin: 0 1;
        content-align: center middle;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }

    .form-field {
        height: auto;
        margin-bottom: 0;
    }

    .form-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }

    .form-row .form-field {
        width: 1fr;
        margin-right: 1;
        margin-bottom: 0;
    }

    .form-row .form-field:last-child {
        margin-right: 0;
    }

    .form-label {
        height: 1;
        color: $text;
        text-style: bold;
    }

    .form-description {
        height: 1;
        color: $text-muted;
        text-style: italic;
    }

    .section-header {
        height: 1;
        margin-top: 0;
        margin-bottom: 0;
        color: $primary;
        text-style: bold underline;
    }

    .dynamic-list {
        border: none;
        padding: 0;
        margin-bottom: 0;
        height: auto;
    }

    #mux-backend-fields {
        height: auto;
    }

    #mux-backend-fields-container {
        height: auto;
    }

    .dynamic-list-item {
        border: none;
        padding: 0;
        margin-bottom: 0;
        height: auto;
    }

    .proxy-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }

    .proxy-row Input {
        margin-right: 1;
    }

    .proxy-name,
    .proxy-host,
    .proxy-imports,
    .proxy-key_path {
        width: 1fr;
    }

    .proxy-username {
        width: 16;
        min-width: 12;
    }

    .proxy-row Button {
        height: 3;
        min-width: 8;
    }

    .import-collapsible {
        border: solid $secondary;
        padding: 0;
        margin-bottom: 0;
    }

    .import-header {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }

    .import-name {
        width: 1fr;
        margin-right: 1;
    }

    .import-type {
        width: 16;
        margin-right: 1;
    }

    .import-type-fields {
        height: auto;
    }

    .import-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }

    .import-row Input,
    .import-row Select {
        margin-right: 1;
    }

    .import-netbox-url,
    .import-netbox-filters,
    .import-ansible-paths,
    .import-consul-token {
        width: 1fr;
    }

    .import-netbox-token {
        width: 22;
    }

    .import-consul-host {
        width: 1fr;
    }

    .import-consul-port,
    .import-consul-scheme,
    .import-consul-dc {
        width: 10;
    }

    .import-git-repo,
    .import-git-source {
        width: 1fr;
    }

    .import-git-branch,
    .import-git-format,
    .import-git-auto-pull {
        width: 18;
    }

    .import-git-priority,
    .import-git-interval {
        width: 12;
    }

    #sources-providers {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }

    #sources-providers Checkbox {
        width: 14;
        margin-right: 1;
    }

    .list-buttons {
        height: auto;
        align: left middle;
    }

    .list-buttons Button {
        height: 3;
        margin: 0 1 0 0;
    }

    .static-host-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 0;
    }

    .static-host-row Input {
        margin-right: 0;
    }

    .static-host-name {
        width: 12;
        min-width: 10;
    }

    .static-host-ip {
        width: 1fr;
        min-width: 14;
    }

    .static-host-alias {
        width: 16;
        min-width: 12;
    }

    .static-host-user {
        width: 10;
        min-width: 8;
    }

    .static-host-port {
        width: 7;
        min-width: 6;
    }

    .static-host-key {
        width: 1fr;
        min-width: 14;
    }

    .static-host-row Button {
        height: 3;
        min-width: 8;
        margin-right: 0;
    }

    .static-host-list {
        height: 15;
        border: round $secondary;
        padding: 0;
    }

    #yaml-editor-row {
        layout: horizontal;
        height: 1fr;
        margin-bottom: 0;
    }

    #cfg-yaml-editor {
        width: 1fr;
        margin-right: 1;
        height: 1fr;
        border: round $primary;
    }

    #cfg-yaml-preview-wrap {
        width: 1fr;
        height: 1fr;
        border: round $secondary;
        padding: 0 1;
    }

    #cfg-yaml-preview {
        width: 1fr;
        height: auto;
    }
    """

    def __init__(self, config: Config, config_path: str = "", runtime_hosts: List[Any] | None = None) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self._runtime_hosts = list(runtime_hosts or [])
        self._yaml_syntax_theme = "monokai"
        self._proxy_counter = 0
        self._import_counter = 0
        self._import_types: Dict[str, str] = {}  # idx -> current type
        self._static_host_counters: Dict[str, int] = {}
        self._mux_backend: str = "tmux"  # current mux backend
        self._table_column_presets: Dict[str, List[str]] = {
            "custom": [],
            "minimal": ["name", "ip"],
            "standard": [
                "name",
                "ip",
                "source",
                "status",
                "cluster",
                "role",
                "tags",
                "description",
                "user",
                "port",
                "platform",
            ],
            "operational": ["name", "ip", "status", "role", "cluster", "source"],
            "inventory": ["name", "ip", "site", "platform", "env", "role", "status"],
        }
        self._table_columns_hint = self._build_table_columns_hint()

    @staticmethod
    def _safe_select_initial(value: str, allowed: List[str], default: str) -> str:
        """Return a safe initial Select value to avoid InvalidSelectValueError."""
        if value in allowed:
            return value
        return default

    def _detect_table_columns_preset(self) -> str:
        """Detect which preset matches current table columns."""
        current = [str(c).strip() for c in self.config.ui.table_columns]
        for preset, cols in self._table_column_presets.items():
            if preset == "custom":
                continue
            if current == cols:
                return preset
        return "custom"

    def _build_table_columns_hint(self) -> str:
        """Build a user-friendly hint for available table columns."""
        common = [
            "name", "ip", "cluster", "role", "tags", "status", "source", "site", "platform", "env",
            "alias", "user", "port", "key_path",
        ]
        detected = self._detect_columns_from_cache_and_imports()
        if detected:
            sample = ", ".join(detected[:10])
            return (
                "Use 'Choose Columns' for grouped picker. Common: " + ", ".join(common) +
                f" | Detected from live/cache/imports: {sample}"
            )

        return "Use 'Choose Columns' for grouped picker. Common columns: " + ", ".join(common)

    @staticmethod
    def _parse_columns_csv(columns_value: str) -> List[str]:
        """Parse comma-separated columns with stable dedup order."""
        parsed: List[str] = []
        for raw in str(columns_value or "").split(","):
            column = raw.strip()
            if not column or column in parsed:
                continue
            parsed.append(column)
        return parsed

    def _get_available_table_columns(self) -> List[str]:
        """Build the available column list for picker from presets/current/detected."""
        preferred = [
            "name", "ip", "cluster", "role", "tags", "status", "source", "site", "platform", "env",
            "description", "alias", "user", "port", "key_path",
            "ansible_group", "ansible_user", "ansible_port", "ansible_connection", "inventory_file",
            "git_repo", "git_branch", "git_commit", "git_file", "git_inventory_format",
            "netbox_site", "netbox_tenant", "netbox_device_role", "netbox_device_type", "netbox_platform",
            "consul_service", "consul_node", "consul_dc", "consul_tags",
            "provider", "sources",
        ]

        available: List[str] = []

        def _append(columns: List[str]) -> None:
            for column in columns:
                c = str(column).strip()
                if c and c not in available:
                    available.append(c)

        _append(preferred)
        _append(self.config.ui.table_columns)
        detected = self._detect_columns_from_cache_and_imports()
        _append(detected)

        return available

    @staticmethod
    def _categorize_table_columns(columns: List[str]) -> Dict[str, List[str]]:
        """Group table columns into UX categories by SoT and origin."""
        category_order = [
            "Common",
            "Origin / Source Tracking",
            "Static / SSH Overrides",
            "Ansible SoT",
            "Git SoT",
            "NetBox SoT",
            "Consul SoT",
            "Other",
        ]
        categorized: Dict[str, List[str]] = {category: [] for category in category_order}

        common = {
            "name", "ip", "cluster", "role", "tags", "status", "site", "platform", "env", "description"
        }
        origin = {"source", "provider", "sources", "inventory_file"}
        static_ssh = {"alias", "user", "port", "key_path", "ssh_alias", "ssh_user", "ssh_port", "ssh_key_path"}
        ansible_fixed = {"ansible_group", "ansible_user", "ansible_port", "ansible_connection"}
        git_fixed = {"git_repo", "git_branch", "git_commit", "git_file", "git_inventory_format"}

        for column in columns:
            c = str(column).strip()
            if not c:
                continue

            if c in common:
                categorized["Common"].append(c)
            elif c in origin:
                categorized["Origin / Source Tracking"].append(c)
            elif c in static_ssh:
                categorized["Static / SSH Overrides"].append(c)
            elif c in ansible_fixed or c.startswith("ansible_"):
                categorized["Ansible SoT"].append(c)
            elif c in git_fixed or c.startswith("git_"):
                categorized["Git SoT"].append(c)
            elif c.startswith("netbox_"):
                categorized["NetBox SoT"].append(c)
            elif c.startswith("consul_"):
                categorized["Consul SoT"].append(c)
            else:
                categorized["Other"].append(c)

        for key, values in categorized.items():
            seen: set[str] = set()
            unique_values: List[str] = []
            for value in values:
                if value in seen:
                    continue
                unique_values.append(value)
                seen.add(value)
            categorized[key] = unique_values

        return categorized

    def _open_table_columns_picker(self) -> None:
        """Open grouped table-columns picker modal."""
        columns_input = self.query_one("#cfg-ui-table_columns", Input)
        selected = self._parse_columns_csv(columns_input.value)
        detected = self._detect_columns_from_cache_and_imports()
        available = self._get_available_table_columns()
        categorized = self._categorize_table_columns(available)
        picker = TableColumnsPickerScreen(
            categorized_columns=categorized,
            selected_columns=selected,
            detected_columns=detected,
        )
        self.app.push_screen(picker, callback=self._on_table_columns_picked)

    def _on_table_columns_picked(self, selected_columns: List[str] | None) -> None:
        """Apply selected columns returned from picker modal."""
        if selected_columns is None:
            return

        columns_input = self.query_one("#cfg-ui-table_columns", Input)
        columns_input.value = ", ".join(selected_columns)
        with contextlib.suppress(Exception):
            preset = self.query_one("#cfg-ui-table_columns_preset", Select)
            preset.value = "custom"
        self._update_status("Table columns updated from picker")

    def _detect_columns_from_cache_and_imports(self) -> List[str]:
        """Detect columns from live hosts, cache, imports, and edited rows."""
        keys: set[str] = set()

        def _add_keys_from_host_like(item: Dict[str, Any]) -> None:
            for base_key in [
                "name", "ip", "cluster", "role", "tags", "provider", "status",
                "site", "platform", "env", "ssh_alias", "ssh_user", "ssh_port", "ssh_key_path",
            ]:
                if base_key in item and item.get(base_key) not in (None, "", []):
                    keys.add(base_key)
            metadata = item.get("metadata", {})
            if isinstance(metadata, dict):
                keys.update(str(k) for k, v in metadata.items() if v not in (None, "", []))

        # 0) Live host objects from currently loaded TUI table
        for host in self._runtime_hosts:
            try:
                host_like: Dict[str, Any] = {
                    "name": getattr(host, "name", ""),
                    "ip": getattr(host, "ip", ""),
                    "metadata": getattr(host, "metadata", {}) or {},
                }
                for key in [
                    "cluster", "role", "tags", "provider", "status", "site", "platform", "env",
                    "ssh_alias", "ssh_user", "ssh_port", "ssh_key_path",
                ]:
                    value = getattr(host, key, None)
                    if value not in (None, "", []):
                        host_like[key] = value
                _add_keys_from_host_like(host_like)
            except Exception:
                continue

        # 1) Cache metadata keys (runtime reality)
        candidate_cache_dirs = [
            Path(str(getattr(self.config.cache, "cache_dir", "~/.cache/sshplex"))).expanduser(),
            Path("~/.cache/sshplex").expanduser(),
            Path("~/cache/sshplex").expanduser(),
        ]
        for cache_dir in candidate_cache_dirs:
            try:
                cache_file = cache_dir / "hosts.yaml"
                if not cache_file.exists():
                    continue
                with open(cache_file) as f:
                    hosts_data = yaml.safe_load(f) or []
                for host in hosts_data[:800]:
                    if isinstance(host, dict):
                        _add_keys_from_host_like(host)
            except Exception:
                continue

        # 2) Static import host keys from current config editor data
        try:
            for imp in getattr(self.config.sot, "import_", []):
                if str(getattr(imp, "type", "")) != "static":
                    continue
                for host_data in list(getattr(imp, "hosts", []) or []):
                    if not isinstance(host_data, dict):
                        continue
                    _add_keys_from_host_like(host_data)
        except Exception:
            pass

        # 3) Include currently edited static rows in UI (even before save)
        try:
            for i in range(1, self._import_counter + 1):
                imp_type = self._get_select_value(f"import-{i}-type", "")
                if imp_type != "static":
                    continue
                max_host_idx = self._static_host_counters.get(str(i), 0)
                for host_idx in range(1, max_host_idx + 1):
                    try:
                        self.query_one(f"#import-{i}-host-item-{host_idx}")
                    except Exception:
                        continue
                    row = {
                        "name": self._get_input_value(f"import-{i}-host-{host_idx}-name"),
                        "ip": self._get_input_value(f"import-{i}-host-{host_idx}-ip"),
                        "ssh_alias": self._get_input_value(f"import-{i}-host-{host_idx}-ssh_alias"),
                        "ssh_user": self._get_input_value(f"import-{i}-host-{host_idx}-ssh_user"),
                        "ssh_port": self._get_input_value(f"import-{i}-host-{host_idx}-ssh_port"),
                        "ssh_key_path": self._get_input_value(f"import-{i}-host-{host_idx}-ssh_key_path"),
                    }
                    _add_keys_from_host_like(row)
        except Exception:
            pass

        normalized: set[str] = set()
        for key in keys:
            if key == "provider":
                normalized.add("source")
            elif key == "ssh_alias":
                normalized.add("alias")
            elif key == "ssh_user":
                normalized.add("user")
            elif key == "ssh_port":
                normalized.add("port")
            elif key == "ssh_key_path":
                normalized.add("key_path")
            elif key not in {"metadata", "sources"}:
                normalized.add(key)

        preferred = [
            "name", "ip", "cluster", "role", "tags", "source", "status", "site", "platform", "env",
            "alias", "user", "port", "key_path",
        ]
        ordered = [k for k in preferred if k in normalized]
        extras = sorted(k for k in normalized if k not in set(preferred))
        return ordered + extras

    def compose(self) -> ComposeResult:
        enabled_provider_values = {
            str(provider).strip()
            for provider in (getattr(self.config.sot, "providers", []) or [])
            if str(provider).strip()
        }
        if not enabled_provider_values:
            enabled_provider_values = {
                str(getattr(imp, "type", "")).strip()
                for imp in (getattr(self.config.sot, "import_", []) or [])
                if str(getattr(imp, "type", "")).strip()
            }

        with Vertical(id="config-editor-dialog"):
            yield Static("SSHplex Configuration Editor", id="editor-title")

            with TabbedContent():
                with TabPane("General", id="tab-general"), VerticalScroll():
                    yield Static("SSHplex", classes="section-header")
                    yield _form_field(
                        "cfg-general-session_prefix",
                        "Session Prefix",
                        Input(value=self.config.sshplex.session_prefix),
                        "Prefix for tmux session names",
                    )
                    yield Static("UI", classes="section-header")
                    yield _form_row(
                        _form_field(
                            "cfg-ui-theme",
                            "Theme",
                            Select(
                                [
                                    ("textual-dark", "textual-dark"),
                                    ("textual-light", "textual-light"),
                                    ("nord", "nord"),
                                    ("gruvbox", "gruvbox"),
                                    ("catppuccin-mocha", "catppuccin-mocha"),
                                    ("dracula", "dracula"),
                                    ("tokyo-night", "tokyo-night"),
                                    ("monokai", "monokai"),
                                    ("flexoki", "flexoki"),
                                    ("catppuccin-latte", "catppuccin-latte"),
                                    ("catppuccin-frappe", "catppuccin-frappe"),
                                    ("catppuccin-macchiato", "catppuccin-macchiato"),
                                    ("solarized-light", "solarized-light"),
                                    ("solarized-dark", "solarized-dark"),
                                    ("rose-pine", "rose-pine"),
                                    ("rose-pine-moon", "rose-pine-moon"),
                                    ("rose-pine-dawn", "rose-pine-dawn"),
                                    ("atom-one-dark", "atom-one-dark"),
                                    ("atom-one-light", "atom-one-light"),
                                ],
                                value=self._safe_select_initial(
                                    str(getattr(self.config.ui, "theme", "textual-dark")),
                                    [
                                        "textual-dark", "textual-light", "nord", "gruvbox", "catppuccin-mocha",
                                        "dracula", "tokyo-night", "monokai", "flexoki", "catppuccin-latte",
                                        "catppuccin-frappe", "catppuccin-macchiato", "solarized-light",
                                        "solarized-dark", "rose-pine", "rose-pine-moon", "rose-pine-dawn",
                                        "atom-one-dark", "atom-one-light",
                                    ],
                                    "textual-dark",
                                ),
                            ),
                            "Persisted app theme used on next launch",
                        ),
                        _form_field(
                            "cfg-ui-table_columns_preset",
                            "Table Columns Preset",
                            Select(
                                [
                                    ("Custom", "custom"),
                                    ("Minimal", "minimal"),
                                    ("Standard", "standard"),
                                    ("Operational", "operational"),
                                    ("Inventory", "inventory"),
                                ],
                                value=self._detect_table_columns_preset(),
                            ),
                            "Choose a preset or keep Custom",
                        ),
                    )
                    yield _form_row(
                        _form_field(
                            "cfg-ui-show_log_panel",
                            "Show Log Panel",
                            Switch(value=self.config.ui.show_log_panel),
                        ),
                        _form_field(
                            "cfg-ui-log_panel_height",
                            "Log Panel Height (%)",
                            Input(value=str(self.config.ui.log_panel_height)),
                        ),
                    )
                    yield _form_field(
                        "cfg-ui-table_columns",
                        "Table Columns",
                        Input(value=", ".join(self.config.ui.table_columns)),
                        self._table_columns_hint,
                    )
                    with Horizontal(classes="list-buttons"):
                        yield Button("Choose Columns", id="btn-columns-picker", variant="primary")
                        yield Button("Detect from Data", id="btn-detect-columns", variant="primary")
                        yield Button("Apply Standard", id="btn-columns-standard", variant="default")
                    yield Static("Logging", classes="section-header")
                    yield _form_row(
                        _form_field(
                            "cfg-logging-enabled",
                            "Enabled",
                            Switch(value=self.config.logging.enabled),
                        ),
                        _form_field(
                            "cfg-logging-level",
                            "Level",
                            Select(
                                [(v, v) for v in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]],
                                value=self._safe_select_initial(
                                    str(getattr(self.config.logging, "level", "INFO")),
                                    ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                    "INFO",
                                ),
                            ),
                        ),
                    )
                    yield _form_field(
                        "cfg-logging-file",
                        "Log File",
                        Input(value=self.config.logging.file),
                    )
                    yield Static("Cache", classes="section-header")
                    yield _form_row(
                        _form_field(
                            "cfg-cache-enabled",
                            "Enabled",
                            Switch(value=self.config.cache.enabled),
                        ),
                        _form_field(
                            "cfg-cache-ttl_hours",
                            "TTL (hours)",
                            Input(value=str(self.config.cache.ttl_hours)),
                        ),
                    )
                    yield _form_field(
                        "cfg-cache-cache_dir",
                        "Cache Directory",
                        Input(value=self.config.cache.cache_dir),
                    )

                with TabPane("SSH", id="tab-ssh"), VerticalScroll():
                    yield Static("Connection Defaults", classes="section-header")
                    yield _form_row(
                        _form_field(
                            "cfg-ssh-username",
                            "Username",
                            Input(value=self.config.ssh.username),
                            "Default user when a host has no ssh_user override",
                        ),
                        _form_field(
                            "cfg-ssh-port",
                            "Port",
                            Input(value=str(self.config.ssh.port)),
                            "Default SSH port when host has no ssh_port",
                        ),
                    )
                    yield _form_row(
                        _form_field(
                            "cfg-ssh-key_path",
                            "Key Path",
                            Input(value=self.config.ssh.key_path),
                            "Default key path when host has no ssh_key_path",
                        ),
                        _form_field(
                            "cfg-ssh-timeout",
                            "Timeout",
                            Input(value=str(self.config.ssh.timeout)),
                            "Connection timeout in seconds per SSH attempt",
                        ),
                    )
                    yield _form_row(
                        _form_field(
                            "cfg-ssh-strict_host_key_checking",
                            "Strict Host Key Checking",
                            Switch(value=self.config.ssh.strict_host_key_checking),
                            "ON: verify host keys strictly | OFF: less secure, easier lab setup",
                        ),
                        _form_field(
                            "cfg-ssh-user_known_hosts_file",
                            "Known Hosts File",
                            Input(value=self.config.ssh.user_known_hosts_file),
                            "Custom known_hosts file path (empty = default)",
                        ),
                    )
                    yield Static("Retry Settings", classes="section-header")
                    yield _form_row(
                        _form_field(
                            "cfg-ssh-retry-enabled",
                            "Retry Enabled",
                            Switch(value=self.config.ssh.retry.enabled),
                            "Retry transient SSH connection failures",
                        ),
                        _form_field(
                            "cfg-ssh-retry-exponential_backoff",
                            "Exponential Backoff",
                            Switch(value=self.config.ssh.retry.exponential_backoff),
                            "ON: delay grows each retry | OFF: fixed delay",
                        ),
                    )
                    yield _form_row(
                        _form_field(
                            "cfg-ssh-retry-max_attempts",
                            "Max Attempts",
                            Input(value=str(self.config.ssh.retry.max_attempts)),
                            "Total attempts including first try",
                        ),
                        _form_field(
                            "cfg-ssh-retry-delay_seconds",
                            "Delay Seconds",
                            Input(value=str(self.config.ssh.retry.delay_seconds)),
                            "Base wait time between retries",
                        ),
                    )
                    yield Static("SSH Proxies", classes="section-header")
                    yield Vertical(id="proxy-list", classes="dynamic-list")

                with TabPane("Mux", id="tab-mux"), VerticalScroll(id="mux-scroll"):
                    yield Static("Session Layout", classes="section-header")
                    yield _form_row(
                        _form_field(
                            "cfg-mux-backend",
                            "Backend",
                            Select(
                                [
                                    (MUX_BACKEND_LABELS.get(backend, backend), backend)
                                    for backend in SUPPORTED_MUX_BACKENDS
                                ],
                                value=self._safe_select_initial(
                                    str(getattr(self.config.tmux, "backend", "tmux")),
                                    list(SUPPORTED_MUX_BACKENDS),
                                    "tmux",
                                ),
                            ),
                            "Multiplexer backend (iTerm2 native is macOS only)",
                        ),
                        _form_field(
                            "cfg-mux-use_panes",
                            "Connection Mode",
                            Select(
                                [("Panes (splits)", "panes"), ("Tabs (separate)", "tabs")],
                                value="panes" if getattr(self.config.tmux, 'use_panes', True) else "tabs",
                            ),
                            "Panes: split within tabs | Tabs: each host in separate tab",
                        ),
                    )
                    yield _form_row(
                        _form_field(
                            "cfg-mux-layout",
                            "Layout",
                            Select(
                                [(v, v) for v in ["tiled", "even-horizontal", "even-vertical", "main-horizontal", "main-vertical"]],
                                value=self._safe_select_initial(
                                    str(getattr(self.config.tmux, "layout", "tiled")),
                                    ["tiled", "even-horizontal", "even-vertical", "main-horizontal", "main-vertical"],
                                    "tiled",
                                ),
                            ),
                            "Pane layout",
                        ),
                        _form_field(
                            "cfg-mux-window_name",
                            "Window Name",
                            Input(value=self.config.tmux.window_name),
                        ),
                    )
                    yield _form_row(
                        _form_field(
                            "cfg-mux-max_panes_per_window",
                            "Max Panes Per Tab",
                            Input(value=str(self.config.tmux.max_panes_per_window)),
                        ),
                        _form_field(
                            "cfg-mux-broadcast",
                            "Broadcast",
                            Switch(value=self.config.tmux.broadcast),
                            "Start with broadcast enabled",
                        ),
                    )
                    yield _form_field(
                        "cfg-mux-register_history",
                        "Register SSHPlex Commands in Shell History",
                        Switch(value=not bool(getattr(self.config.tmux, 'iterm2_native_hide_from_history', True))),
                        "iTerm2-native only. OFF means commands are hidden from history.",
                    )
                    yield Vertical(id="mux-backend-fields")

                with TabPane("Sources", id="tab-sources"), VerticalScroll():
                    yield Static("Providers", classes="section-header")
                    yield Static("Enable the data sources SSHplex should load.", classes="form-description")
                    with Horizontal(id="sources-providers"):
                        for provider in SUPPORTED_SOT_PROVIDER_TYPES:
                            yield Checkbox(
                                SOT_PROVIDER_LABELS.get(provider, provider.title()),
                                value=provider in enabled_provider_values,
                                id=f"cfg-sot-provider-{provider}",
                                compact=True,
                            )
                    with Horizontal(classes="list-buttons"):
                        yield Button("All", id="btn-providers-all", variant="default")
                        yield Button("None", id="btn-providers-none", variant="default")
                    yield Static("Imports", classes="section-header")
                    yield Vertical(id="import-list", classes="dynamic-list")

                with TabPane("Config YAML", id="tab-yaml"), Vertical():
                    yield Static("Edit on left, rich YAML highlight preview on right.", classes="form-description")
                    with Horizontal(id="yaml-editor-row"):
                        yield TextArea(
                            "",
                            id="cfg-yaml-editor",
                            language="yaml",
                            theme="monokai",
                            soft_wrap=False,
                            show_line_numbers=True,
                        )
                        with VerticalScroll(id="cfg-yaml-preview-wrap"):
                            yield Static(id="cfg-yaml-preview")
                    with Horizontal(classes="list-buttons"):
                        yield Button("Reload File", id="btn-yaml-reload", variant="default")
                        yield Button("Save YAML", id="btn-yaml-save", variant="primary")

            with Horizontal(id="editor-buttons"):
                yield Button("Save (Ctrl+S)", id="btn-save", variant="primary")
                yield Button("Cancel (Esc)", id="btn-cancel", variant="default")

            yield Static("", id="editor-status")

    def on_mount(self) -> None:
        """Populate dynamic lists after mount."""
        self._populate_proxy_list()
        self._populate_import_list()
        self._populate_mux_backend_fields()
        self._sync_yaml_editor_theme()
        self._load_yaml_editor_from_file()
        self._refresh_mux_scroll()

    def _sync_yaml_editor_theme(self, current_theme: str = "") -> None:
        """Keep YAML editor syntax theme aligned with current app theme."""
        theme_map = {
            "textual-dark": "monokai",
            "textual-light": "github_light",
            "nord": "nord",
            "gruvbox": "gruvbox",
            "catppuccin-mocha": "dracula",
            "dracula": "dracula",
            "tokyo-night": "monokai",
            "monokai": "monokai",
            "flexoki": "vscode_dark",
            "catppuccin-latte": "github_light",
            "catppuccin-frappe": "dracula",
            "catppuccin-macchiato": "dracula",
            "solarized-light": "github_light",
            "solarized-dark": "monokai",
            "rose-pine": "dracula",
            "rose-pine-moon": "dracula",
            "rose-pine-dawn": "github_light",
            "atom-one-dark": "vscode_dark",
            "atom-one-light": "github_light",
        }
        app_theme = current_theme or str(getattr(self.app, "theme", "textual-dark") or "textual-dark")
        syntax_theme = theme_map.get(app_theme, "monokai")
        self._yaml_syntax_theme = syntax_theme
        try:
            editor = self.query_one("#cfg-yaml-editor", TextArea)
            editor.theme = syntax_theme
        except Exception:
            pass
        self._update_yaml_preview()

    def _update_yaml_preview(self) -> None:
        """Render rich YAML syntax preview next to editor."""
        try:
            editor = self.query_one("#cfg-yaml-editor", TextArea)
            preview = self.query_one("#cfg-yaml-preview", Static)
        except Exception:
            return

        raw = editor.text or ""
        if not raw.strip():
            raw = "# Empty configuration"

        try:
            syntax = Syntax(raw, "yaml", theme=self._yaml_syntax_theme, line_numbers=True, word_wrap=False)
        except Exception:
            syntax = Syntax(raw, "yaml", theme="monokai", line_numbers=True, word_wrap=False)
        preview.update(syntax)

    def _refresh_mux_scroll(self) -> None:
        """Force Mux scroll container to recalculate layout after dynamic mounts."""
        try:
            mux_scroll = self.query_one("#mux-scroll", VerticalScroll)
            mux_scroll.refresh(layout=True)
        except Exception:
            pass

    # --- Mux backend fields ---

    def _populate_mux_backend_fields(self) -> None:
        """Populate backend-specific fields based on current backend."""
        container = self.query_one("#mux-backend-fields", Vertical)
        backend = self._safe_select_initial(
            str(getattr(self.config.tmux, "backend", "tmux")),
            list(SUPPORTED_MUX_BACKENDS),
            "tmux",
        )
        self._mux_backend = backend
        container.mount(self._make_mux_backend_fields(backend))

    def _make_mux_backend_fields(self, backend: str) -> Vertical:
        """Create backend-specific fields."""
        children: List[Any] = []

        if backend == "tmux":
            # tmux + iTerm2 -CC mode options
            children.append(Static("iTerm2 Integration (macOS)", classes="section-header"))
            iterm2_target = getattr(self.config.tmux, 'iterm2_attach_target', 'new-window')
            if iterm2_target not in ('new-window', 'new-tab'):
                iterm2_target = 'new-window'
            children.append(_form_row(
                _form_field(
                    "cfg-mux-control_with_iterm2",
                    "Enable iTerm2 -CC Mode",
                    Switch(value=self.config.tmux.control_with_iterm2),
                    "Use iTerm2 tmux -CC mode on macOS",
                ),
                _form_field(
                    "cfg-mux-iterm2_attach_target",
                    "Attach Target",
                    Select(
                        [("New Window", "new-window"), ("New Tab", "new-tab")],
                        value=iterm2_target,
                    ),
                    "Where to open tmux session in iTerm2",
                ),
            ))
            children.append(_form_field(
                "cfg-mux-iterm2_profile",
                "iTerm2 Profile",
                Input(value=getattr(self.config.tmux, 'iterm2_profile', 'Default')),
                "iTerm2 profile name to use",
            ))
        elif backend == "iterm2-native":
            # iTerm2 native options
            children.append(Static("iTerm2 Native Options", classes="section-header"))
            children.append(_form_row(
                _form_field(
                    "cfg-mux-iterm2_native_target",
                    "Open Target",
                    Select(
                        [
                            ("Current iTerm2 Window", "current-window"),
                            ("New iTerm2 Window", "new-window"),
                        ],
                        value=self._safe_select_initial(
                            str(getattr(self.config.tmux, "iterm2_native_target", "current-window")),
                            ["current-window", "new-window"],
                            "current-window",
                        ),
                    ),
                    "Open sessions in current window (new tabs) or a new window",
                ),
                _form_field(
                    "cfg-mux-iterm2_split_pattern",
                    "Split Pattern",
                    Select(
                        [("Alternate", "alternate"), ("Vertical", "vertical"), ("Horizontal", "horizontal")],
                        value=self._safe_select_initial(
                            str(getattr(self.config.tmux, "iterm2_split_pattern", "alternate")),
                            ["alternate", "vertical", "horizontal"],
                            "alternate",
                        ),
                    ),
                    "Pane split pattern",
                ),
            ))
            children.append(_form_field(
                "cfg-mux-iterm2_profile",
                "iTerm2 Profile",
                Input(value=getattr(self.config.tmux, 'iterm2_profile', 'Default')),
                "iTerm2 profile name to use",
            ))
        return Vertical(*children, id="mux-backend-fields-container")

    # --- Dynamic proxy list ---

    def _populate_proxy_list(self) -> None:
        """Populate the proxy list from current config."""
        container = self.query_one("#proxy-list", Vertical)
        for proxy in self.config.ssh.proxy:
            self._proxy_counter += 1
            container.mount(self._make_proxy_item(self._proxy_counter, proxy))
        container.mount(
            Horizontal(
                Button("+ Add Proxy", id="btn-add-proxy", variant="success"),
                classes="list-buttons",
            )
        )

    def _make_proxy_item(self, idx: int, proxy: Any = None) -> Vertical:
        """Create a proxy form item."""
        name = proxy.name if proxy else ""
        imports = ", ".join(proxy.imports) if proxy else ""
        host = proxy.host if proxy else ""
        username = proxy.username if proxy else ""
        key_path = proxy.key_path if proxy else ""

        return Vertical(
            Label(f"Proxy #{idx}", classes="form-label"),
            Horizontal(
                Input(value=name, placeholder="Proxy name", id=f"proxy-{idx}-name", classes="proxy-name"),
                Input(value=host, placeholder="Host", id=f"proxy-{idx}-host", classes="proxy-host"),
                classes="proxy-row",
            ),
            Horizontal(
                Input(value=imports, placeholder="Imports (comma-separated)", id=f"proxy-{idx}-imports", classes="proxy-imports"),
                Input(value=username, placeholder="Username", id=f"proxy-{idx}-username", classes="proxy-username"),
                Input(value=key_path, placeholder="Key path", id=f"proxy-{idx}-key_path", classes="proxy-key_path"),
                Button("Remove", id=f"btn-remove-proxy-{idx}", variant="error"),
                classes="proxy-row",
            ),
            classes="dynamic-list-item",
            id=f"proxy-item-{idx}",
        )

    # --- Dynamic import list ---

    def _populate_import_list(self) -> None:
        """Populate the import list from current config."""
        container = self.query_one("#import-list", Vertical)
        for imp in self.config.sot.import_:
            self._import_counter += 1
            container.mount(self._make_import_item(self._import_counter, imp, collapsed=self._import_counter > 1))
        container.mount(
            Horizontal(
                Button("+ Add Import", id="btn-add-import", variant="success"),
                classes="list-buttons",
            )
        )

    def _make_import_item(self, idx: int, imp: Any = None, collapsed: bool = False) -> Collapsible:
        """Create a compact import form item with type-specific fields."""
        name = imp.name if imp else ""
        imp_type = self._safe_select_initial(
            str(getattr(imp, "type", "static")) if imp else "static",
            list(SUPPORTED_SOT_PROVIDER_TYPES),
            "static",
        )
        self._import_types[str(idx)] = imp_type

        header = Horizontal(
            Input(value=name, placeholder="Import name", id=f"import-{idx}-name", classes="import-name"),
            Select(
                [(v, v) for v in SUPPORTED_SOT_PROVIDER_TYPES],
                value=imp_type,
                id=f"import-{idx}-type",
                classes="import-type",
            ),
            Button("Remove", id=f"btn-remove-import-{idx}", variant="error"),
            classes="import-header",
        )

        type_fields = Vertical(
            *self._make_import_type_fields(idx, imp_type, imp),
            id=f"import-{idx}-type-fields",
            classes="import-type-fields",
        )

        name_label = f"{name}" if name else f"Import #{idx}"
        return Collapsible(
            Vertical(header, type_fields, classes="dynamic-list-item"),
            title=f"{name_label} [{imp_type}]",
            collapsed=collapsed,
            id=f"import-item-{idx}",
            classes="import-collapsible",
        )

    def _import_form_field(self, field_id: str, label: str, description: str, widget: Any) -> Vertical:
        """Build an import field with label + helper text above input."""
        return _form_field(field_id, label, widget, description)

    def _make_import_type_fields(self, idx: int, imp_type: str, imp: Any = None) -> list:
        """Generate type-specific fields for an import item."""
        fields: list = []
        if imp_type == "static":
            fields.append(Static("Static hosts", classes="form-label"))
            fields.append(
                Static(
                    "Alias = SSH Host alias from ~/.ssh/config. Port/User/Key override global ssh settings. "
                    "Use 'Preview' to view effective values (ssh -G).",
                    classes="form-description",
                )
            )
            fields.append(
                Static("Columns: name | ip/hostname | alias | user | port | key_path", classes="form-description")
            )

            self._static_host_counters[str(idx)] = 0
            source_hosts = list(getattr(imp, "hosts", []) or [])
            if not source_hosts:
                source_hosts = [{"name": "", "ip": ""}]
            host_rows: List[Any] = []
            for host_data in source_hosts:
                self._static_host_counters[str(idx)] += 1
                host_row = self._make_static_host_row(idx, self._static_host_counters[str(idx)], host_data)
                host_rows.append(host_row)
            fields.append(Horizontal(Button("+ Add Host", id=f"btn-add-static-host-{idx}", variant="success"), classes="list-buttons"))
            host_list = VerticalScroll(*host_rows, id=f"import-{idx}-static-hosts", classes="static-host-list")
            fields.append(host_list)
        elif imp_type == "netbox":
            fields.append(Static("NetBox settings", classes="form-label"))
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-url",
                    "NetBox URL",
                    "NetBox API endpoint (https://netbox.example.com)",
                    Input(
                        value=(imp.url or "") if imp else "",
                        placeholder="https://netbox.example.com",
                        classes="import-netbox-url",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-token",
                    "API Token",
                    "Read token used to query inventory",
                    Input(
                        value=(imp.token or "") if imp else "",
                        placeholder="NetBox token",
                        password=True,
                        classes="import-netbox-token",
                    ),
                ),
            ))
            filters_str = ""
            if imp and imp.default_filters:
                filters_str = ", ".join(f"{k}={v}" for k, v in imp.default_filters.items())
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-filters",
                    "Default Filters",
                    "Optional query filters (key=value, key2=value2)",
                    Input(
                        value=filters_str,
                        placeholder="status=active, role=server",
                        classes="import-netbox-filters",
                    ),
                )
            ))
        elif imp_type == "ansible":
            fields.append(Static("Ansible settings", classes="form-label"))
            paths = ""
            if imp and imp.inventory_paths:
                paths = ", ".join(imp.inventory_paths)
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-inventory_paths",
                    "Inventory Paths",
                    "Comma-separated local inventory files",
                    Input(
                        value=paths,
                        placeholder="inventory/prod.yml, inventory/staging.yml",
                        classes="import-ansible-paths",
                    ),
                )
            ))
        elif imp_type == "consul":
            fields.append(Static("Consul settings", classes="form-label"))
            cfg = imp.config if imp else None
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-consul_host",
                    "Consul Host",
                    "Consul server hostname",
                    Input(
                        value=(cfg.host if cfg else ""),
                        placeholder="consul.example.com",
                        classes="import-consul-host",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-consul_port",
                    "Port",
                    "Consul API port",
                    Input(
                        value=str(cfg.port if cfg else 443),
                        placeholder="443",
                        classes="import-consul-port",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-consul_scheme",
                    "Scheme",
                    "http or https",
                    Input(
                        value=(cfg.scheme if cfg else "https"),
                        placeholder="https",
                        classes="import-consul-scheme",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-consul_dc",
                    "Datacenter",
                    "Consul datacenter name",
                    Input(
                        value=(cfg.dc if cfg else "dc1"),
                        placeholder="dc1",
                        classes="import-consul-dc",
                    ),
                ),
            ))
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-consul_token",
                    "Token",
                    "Read token for catalog queries",
                    Input(
                        value=(cfg.token if cfg else ""),
                        placeholder="Consul token",
                        password=True,
                        classes="import-consul-token",
                    ),
                )
            ))
        elif imp_type == "git":
            fields.append(Static("Git settings", classes="form-label"))
            source_pattern = "hosts/**/*.y*ml"
            if imp is not None:
                source_pattern = str(
                    getattr(imp, "source_pattern", "hosts/**/*.y*ml") or "hosts/**/*.y*ml"
                ).strip()

            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-git_repo_url",
                    "Repository URL",
                    "Git repository URL (ssh or https)",
                    Input(
                        value=(getattr(imp, "repo_url", "") or "") if imp else "",
                        placeholder="git@github.com:org/repo.git",
                        classes="import-git-repo",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-git_branch",
                    "Branch",
                    "Branch to track for updates",
                    Input(
                        value=(getattr(imp, "branch", "main") or "main") if imp else "main",
                        placeholder="main",
                        classes="import-git-branch",
                    ),
                ),
            ))

            inventory_format_value = self._safe_select_initial(
                str(getattr(imp, "inventory_format", "static") or "static") if imp else "static",
                ["static", "ansible"],
                "static",
            )
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-git_source_pattern",
                    "Source Pattern",
                    "Repo path + glob in one value (e.g. hosts/**/*.y*ml)",
                    Input(
                        value=source_pattern,
                        placeholder="hosts/**/*.y*ml",
                        classes="import-git-source",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-git_inventory_format",
                    "Inventory Format",
                    "Static hosts or Ansible inventory YAML",
                    Select(
                        [("Static", "static"), ("Ansible", "ansible")],
                        value=inventory_format_value,
                        classes="import-git-format",
                    ),
                ),
            ))

            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-git_priority",
                    "Priority",
                    "Higher value wins on duplicates",
                    Input(
                        value=str(getattr(imp, "priority", 100) if imp else 100),
                        placeholder="100",
                        classes="import-git-priority",
                    ),
                ),
            ))

            auto_pull_value = "true"
            if imp is not None and not bool(getattr(imp, "auto_pull", True)):
                auto_pull_value = "false"
            auto_pull_value = self._safe_select_initial(
                auto_pull_value,
                ["true", "false"],
                "true",
            )
            fields.append(_form_row(
                self._import_form_field(
                    f"import-{idx}-git_auto_pull",
                    "Auto Pull",
                    "Auto checks remote changes before refresh",
                    Select(
                        [("Auto", "true"), ("Manual", "false")],
                        value=auto_pull_value,
                        classes="import-git-auto-pull",
                    ),
                ),
                self._import_form_field(
                    f"import-{idx}-git_pull_interval",
                    "Pull Interval (s)",
                    "Seconds between automatic pull attempts",
                    Input(
                        value=str(getattr(imp, "pull_interval_seconds", 300) if imp else 300),
                        placeholder="300",
                        classes="import-git-interval",
                    ),
                ),
            ))

        return fields

    def _make_static_host_row(self, import_idx: int, host_idx: int, host_data: Dict[str, Any]) -> Horizontal:
        """Build one editable static host row."""
        name = str(host_data.get("name", ""))
        ip = str(host_data.get("ip", ""))
        alias = str(host_data.get("ssh_alias", ""))
        ssh_user = str(host_data.get("ssh_user", ""))
        ssh_port = str(host_data.get("ssh_port", ""))
        ssh_key_path = str(host_data.get("ssh_key_path", ""))

        can_remove = host_idx > 1
        return Horizontal(
            Input(value=name, placeholder="name", id=f"import-{import_idx}-host-{host_idx}-name", classes="static-host-name"),
            Input(value=ip, placeholder="ip/hostname", id=f"import-{import_idx}-host-{host_idx}-ip", classes="static-host-ip"),
            Input(value=alias, placeholder="alias(~/.ssh/config)", id=f"import-{import_idx}-host-{host_idx}-ssh_alias", classes="static-host-alias"),
            Input(value=ssh_user, placeholder="user", id=f"import-{import_idx}-host-{host_idx}-ssh_user", classes="static-host-user"),
            Input(value=ssh_port, placeholder="port(22)", id=f"import-{import_idx}-host-{host_idx}-ssh_port", classes="static-host-port"),
            Input(value=ssh_key_path, placeholder="key_path", id=f"import-{import_idx}-host-{host_idx}-ssh_key_path", classes="static-host-key"),
            Button("Preview", id=f"btn-show-static-host-ssh-{import_idx}-{host_idx}", variant="default"),
            Button("Remove", id=f"btn-remove-static-host-{import_idx}-{host_idx}", variant="error", disabled=not can_remove),
            classes="static-host-row",
            id=f"import-{import_idx}-host-item-{host_idx}",
        )

    # --- Button handlers ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id or ""

        if btn_id == "btn-save":
            self.action_save()
        elif btn_id == "btn-cancel":
            self.action_cancel()
        elif btn_id == "btn-providers-all":
            self._set_all_providers(True)
        elif btn_id == "btn-providers-none":
            self._set_all_providers(False)
        elif btn_id == "btn-add-proxy":
            self._add_proxy()
        elif btn_id.startswith("btn-remove-proxy-"):
            idx = btn_id.replace("btn-remove-proxy-", "")
            self._remove_proxy(idx)
        elif btn_id == "btn-add-import":
            self._add_import()
        elif btn_id.startswith("btn-remove-import-"):
            idx = btn_id.replace("btn-remove-import-", "")
            self._remove_import(idx)
        elif btn_id.startswith("btn-add-static-host-"):
            parts = btn_id.split("-")
            if len(parts) == 5:
                self._add_static_host(parts[-1])
            elif len(parts) >= 6:
                self._add_static_host(parts[-2])
        elif btn_id.startswith("btn-remove-static-host-"):
            parts = btn_id.split("-")
            if len(parts) >= 6:
                self._remove_static_host(parts[-2], parts[-1])
        elif btn_id.startswith("btn-show-static-host-ssh-"):
            parts = btn_id.split("-")
            if len(parts) >= 7:
                self._show_static_host_ssh_preview(parts[-2], parts[-1])
        elif btn_id == "btn-yaml-reload":
            self._load_yaml_editor_from_file()
        elif btn_id == "btn-yaml-save":
            self._save_from_yaml_editor()
        elif btn_id == "btn-columns-picker":
            self._open_table_columns_picker()
        elif btn_id == "btn-detect-columns":
            self._apply_detected_columns_from_cache()
        elif btn_id == "btn-columns-standard":
            columns_input = self.query_one("#cfg-ui-table_columns", Input)
            columns_input.value = ", ".join(self._table_column_presets["standard"])

    def _set_all_providers(self, enabled: bool) -> None:
        """Toggle all provider checkboxes on/off."""
        for provider in SUPPORTED_SOT_PROVIDER_TYPES:
            with contextlib.suppress(Exception):
                checkbox = self.query_one(f"#cfg-sot-provider-{provider}", Checkbox)
                checkbox.value = enabled

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes to re-render dynamic fields."""
        select_id = event.select.id or ""

        # Handle mux backend changes
        if select_id == "cfg-mux-backend":
            new_backend = str(event.value)
            if self._mux_backend != new_backend:
                self._mux_backend = new_backend
                self.run_worker(self._rebuild_mux_backend_fields(new_backend))
            return

        # Handle table-column presets
        if select_id == "cfg-ui-table_columns_preset":
            preset = str(event.value)
            if preset in self._table_column_presets and preset != "custom":
                columns_input = self.query_one("#cfg-ui-table_columns", Input)
                columns_input.value = ", ".join(self._table_column_presets[preset])
            return

        if select_id == "cfg-ui-theme":
            self._sync_yaml_editor_theme(str(event.value))
            return

        # Handle import type changes
        if not select_id.startswith("import-") or not select_id.endswith("-type"):
            return

        # Extract index: "import-{idx}-type"
        parts = select_id.split("-")
        if len(parts) != 3:
            return
        idx = parts[1]
        new_type = str(event.value)

        # Skip if type hasn't actually changed (e.g. initial mount event)
        if self._import_types.get(idx) == new_type:
            return

        self._import_types[idx] = new_type
        with contextlib.suppress(Exception):
            self.query_one(f"#cfg-sot-provider-{new_type}", Checkbox).value = True
        self.run_worker(self._rebuild_import_type_fields(idx, new_type))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Keep compact import headers in sync with import name edits."""
        input_id = event.input.id or ""
        if input_id == "cfg-ui-table_columns":
            with contextlib.suppress(Exception):
                preset = self.query_one("#cfg-ui-table_columns_preset", Select)
                if preset.value != "custom":
                    preset.value = "custom"
            return

        if not input_id.startswith("import-") or not input_id.endswith("-name"):
            return

        parts = input_id.split("-")
        if len(parts) != 3:
            return

        idx = parts[1]
        name = event.value.strip() or f"Import #{idx}"
        imp_type = self._import_types.get(idx, "static")
        with contextlib.suppress(Exception):
            item = self.query_one(f"#import-item-{idx}", Collapsible)
            item.title = f"{name} [{imp_type}]"

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Live-update rich YAML preview while typing."""
        control = getattr(event, "control", None)
        if control is None:
            return
        if getattr(control, "id", "") != "cfg-yaml-editor":
            return
        self._update_yaml_preview()

    async def _rebuild_mux_backend_fields(self, new_backend: str) -> None:
        """Rebuild backend-specific fields when mux backend changes."""
        container = self.query_one("#mux-backend-fields", Vertical)

        # Remove old fields
        for child in list(container.children):
            await child.remove()

        # Mount new fields
        container.mount(self._make_mux_backend_fields(new_backend))
        container.refresh(layout=True)
        self._refresh_mux_scroll()

    async def _rebuild_import_type_fields(self, idx: str, new_type: str) -> None:
        """Rebuild type-specific fields when import type changes."""
        container = self.query_one(f"#import-{idx}-type-fields", Vertical)

        for child in list(container.children):
            await child.remove()

        new_fields = self._make_import_type_fields(int(idx), new_type)
        for field in new_fields:
            await container.mount(field)

        with contextlib.suppress(Exception):
            title_name = self._get_input_value(f"import-{idx}-name") or f"Import #{idx}"
            item = self.query_one(f"#import-item-{idx}", Collapsible)
            item.title = f"{title_name} [{new_type}]"

    def _add_proxy(self) -> None:
        """Add a new proxy entry."""
        self._proxy_counter += 1
        container = self.query_one("#proxy-list", Vertical)
        # Mount before the add button row
        add_btn_row = container.query(".list-buttons").last()
        container.mount(self._make_proxy_item(self._proxy_counter), before=add_btn_row)

    def _remove_proxy(self, idx: str) -> None:
        """Remove a proxy entry."""
        try:
            item = self.query_one(f"#proxy-item-{idx}")
            item.remove()
        except Exception:
            pass

    def _add_import(self) -> None:
        """Add a new import entry."""
        self._import_counter += 1
        container = self.query_one("#import-list", Vertical)
        add_btn_row = container.query(".list-buttons").last()
        container.mount(self._make_import_item(self._import_counter, collapsed=False), before=add_btn_row)

    def _remove_import(self, idx: str) -> None:
        """Remove an import entry."""
        try:
            item = self.query_one(f"#import-item-{idx}")
            item.remove()
        except Exception:
            pass

    def _add_static_host(self, import_idx: str) -> None:
        """Add one static host row for an import."""
        try:
            current = self._static_host_counters.get(import_idx, 0) + 1
            self._static_host_counters[import_idx] = current
            container = self.query_one(f"#import-{import_idx}-static-hosts", VerticalScroll)
            container.mount(self._make_static_host_row(int(import_idx), current, {"name": "", "ip": ""}))
        except Exception as e:
            self._update_status(f"Could not add static host row: {e}", error=True)

    def _remove_static_host(self, import_idx: str, host_idx: str) -> None:
        """Remove one static host row from an import."""
        with contextlib.suppress(Exception):
            self.query_one(f"#import-{import_idx}-host-item-{host_idx}").remove()

    def _show_static_host_ssh_preview(self, import_idx: str, host_idx: str) -> None:
        """Show effective SSH config preview for one static host row."""
        from ..utils.ssh_config import mask_sensitive, resolve_ssh_effective_config

        alias = self._get_input_value(f"import-{import_idx}-host-{host_idx}-ssh_alias")
        ip = self._get_input_value(f"import-{import_idx}-host-{host_idx}-ip")
        user_override = self._get_input_value(f"import-{import_idx}-host-{host_idx}-ssh_user")
        port_override = self._get_input_value(f"import-{import_idx}-host-{host_idx}-ssh_port")
        key_override = self._get_input_value(f"import-{import_idx}-host-{host_idx}-ssh_key_path")
        target = alias or ip
        if not target:
            self._update_status("Set alias or ip first", error=True)
            return

        resolved = resolve_ssh_effective_config(target)

        host_name = resolved.get("hostname", target) if resolved else target
        user = user_override or resolved.get("user", "") or getattr(self.config.ssh, "username", "")
        port = port_override or resolved.get("port", "22")
        key = key_override or resolved.get("identityfile", "") or getattr(self.config.ssh, "key_path", "")

        key = mask_sensitive(str(key).split()[0]) if key else "-"

        preview = f"ssh preview => host={host_name} user={user or '-'} port={port} key={key}"
        self._update_status(preview)

    def _load_yaml_editor_from_file(self) -> None:
        """Load current config file content into YAML editor tab."""
        config_path = get_default_config_path() if not self.config_path else Path(self.config_path)
        editor = self.query_one("#cfg-yaml-editor", TextArea)
        try:
            if config_path.exists():
                editor.text = config_path.read_text()
            else:
                editor.text = yaml.dump(
                    _clean_none(self.config.model_dump(by_alias=True)),
                    default_flow_style=False,
                    sort_keys=False,
                )
            self._update_yaml_preview()
            self._update_status("YAML editor loaded")
        except Exception as e:
            self._update_status(f"Could not load YAML: {e}", error=True)

    def _save_from_yaml_editor(self) -> None:
        """Validate and save config from YAML editor tab."""
        editor = self.query_one("#cfg-yaml-editor", TextArea)
        raw = (editor.text or "").strip()
        if not raw:
            self._update_status("YAML editor is empty", error=True)
            return

        try:
            loaded = yaml.safe_load(raw)
            validated = Config(**loaded)
            yaml_data = _clean_none(validated.model_dump(by_alias=True))
        except Exception as e:
            self._update_status(f"YAML validation error: {e}", error=True)
            return

        config_path = get_default_config_path() if not self.config_path else Path(self.config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(config_path, "w") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            self._update_status(f"Failed to write config: {e}", error=True)
            return

        self.dismiss(True)
        self.app.notify("Configuration saved from YAML editor.", title="Config Saved", timeout=4)

    # --- Data collection ---

    def _get_input_value(self, widget_id: str, default: str = "") -> str:
        """Safely get an Input widget's value."""
        try:
            return self.query_one(f"#{widget_id}", Input).value.strip()
        except Exception:
            return default

    def _get_switch_value(self, widget_id: str, default: bool = False) -> bool:
        """Safely get a Switch widget's value."""
        try:
            return self.query_one(f"#{widget_id}", Switch).value
        except Exception:
            return default

    def _get_select_value(self, widget_id: str, default: str = "") -> str:
        """Safely get a Select widget's value."""
        try:
            val = self.query_one(f"#{widget_id}", Select).value
            return str(val) if val is not None and val != Select.BLANK else default
        except Exception:
            return default

    def _collect_form_data(self) -> Dict[str, Any]:
        """Collect all form data into a dict suitable for Config(**data)."""
        data: Dict[str, Any] = {}

        # General
        data["sshplex"] = {
            "session_prefix": self._get_input_value("cfg-general-session_prefix", "sshplex"),
        }

        # SSH
        proxies = self._collect_proxies()
        data["ssh"] = {
            "username": self._get_input_value("cfg-ssh-username", "admin"),
            "key_path": self._get_input_value("cfg-ssh-key_path", "~/.ssh/id_rsa"),
            "timeout": int(self._get_input_value("cfg-ssh-timeout", "10")),
            "port": int(self._get_input_value("cfg-ssh-port", "22")),
            "strict_host_key_checking": self._get_switch_value("cfg-ssh-strict_host_key_checking"),
            "user_known_hosts_file": self._get_input_value("cfg-ssh-user_known_hosts_file"),
            "retry": {
                "enabled": self._get_switch_value("cfg-ssh-retry-enabled", True),
                "max_attempts": int(self._get_input_value("cfg-ssh-retry-max_attempts", "3")),
                "delay_seconds": float(self._get_input_value("cfg-ssh-retry-delay_seconds", "2.0")),
                "exponential_backoff": self._get_switch_value("cfg-ssh-retry-exponential_backoff", True),
            },
            "proxy": proxies,
        }

        # Mux (tmux/iTerm2)
        backend = self._get_select_value("cfg-mux-backend", "tmux")
        mux_data: Dict[str, Any] = {
            "backend": backend,
            "use_panes": self._get_select_value("cfg-mux-use_panes", "panes") == "panes",
            "layout": self._get_select_value("cfg-mux-layout", "tiled"),
            "broadcast": self._get_switch_value("cfg-mux-broadcast"),
            "iterm2_native_hide_from_history": not self._get_switch_value("cfg-mux-register_history", False),
            "window_name": self._get_input_value("cfg-mux-window_name", "sshplex"),
            "max_panes_per_window": int(self._get_input_value("cfg-mux-max_panes_per_window", "5")),
        }

        # Backend-specific fields
        if backend == "tmux":
            mux_data["control_with_iterm2"] = self._get_switch_value("cfg-mux-control_with_iterm2")
            mux_data["iterm2_attach_target"] = self._get_select_value("cfg-mux-iterm2_attach_target", "new-window")
            mux_data["iterm2_profile"] = self._get_input_value("cfg-mux-iterm2_profile", "Default")
        elif backend == "iterm2-native":
            mux_data["control_with_iterm2"] = False  # Not applicable
            mux_data["iterm2_attach_target"] = "new-window"  # Default
            mux_data["iterm2_native_target"] = self._get_select_value("cfg-mux-iterm2_native_target", "current-window")
            mux_data["iterm2_profile"] = self._get_input_value("cfg-mux-iterm2_profile", "Default")
            mux_data["iterm2_split_pattern"] = self._get_select_value("cfg-mux-iterm2_split_pattern", "alternate")

        data["tmux"] = mux_data

        # Sources
        providers = self._collect_enabled_providers()
        if not providers:
            raise ValueError("at least one provider must be enabled")
        imports = self._collect_imports()
        data["sot"] = {
            "providers": providers,
            "import": imports,
        }

        # UI
        columns_str = self._get_input_value("cfg-ui-table_columns", "name, ip, cluster, role, tags")
        columns = [c.strip() for c in columns_str.split(",") if c.strip()]
        data["ui"] = {
            "theme": self._get_select_value("cfg-ui-theme", "textual-dark"),
            "show_log_panel": self._get_switch_value("cfg-ui-show_log_panel", True),
            "log_panel_height": int(self._get_input_value("cfg-ui-log_panel_height", "20")),
            "table_columns": columns,
        }

        # Logging
        data["logging"] = {
            "enabled": self._get_switch_value("cfg-logging-enabled", True),
            "level": self._get_select_value("cfg-logging-level", "INFO"),
            "file": self._get_input_value("cfg-logging-file", "logs/sshplex.log"),
        }

        # Cache
        data["cache"] = {
            "enabled": self._get_switch_value("cfg-cache-enabled", True),
            "cache_dir": self._get_input_value("cfg-cache-cache_dir", "~/.cache/sshplex"),
            "ttl_hours": int(self._get_input_value("cfg-cache-ttl_hours", "24")),
        }

        return data

    def _collect_proxies(self) -> List[Dict[str, Any]]:
        """Collect proxy entries from the dynamic list."""
        proxies: List[Dict[str, Any]] = []
        for i in range(1, self._proxy_counter + 1):
            try:
                self.query_one(f"#proxy-item-{i}")
            except Exception:
                continue  # removed

            name = self._get_input_value(f"proxy-{i}-name")
            if not name:
                continue

            imports_str = self._get_input_value(f"proxy-{i}-imports")
            imports = [s.strip() for s in imports_str.split(",") if s.strip()]

            proxies.append({
                "name": name,
                "imports": imports,
                "host": self._get_input_value(f"proxy-{i}-host"),
                "username": self._get_input_value(f"proxy-{i}-username"),
                "key_path": self._get_input_value(f"proxy-{i}-key_path"),
            })
        return proxies

    def _collect_enabled_providers(self) -> List[str]:
        """Collect enabled SoT providers from checkbox controls."""
        enabled: List[str] = []
        for provider in SUPPORTED_SOT_PROVIDER_TYPES:
            try:
                if self.query_one(f"#cfg-sot-provider-{provider}", Checkbox).value:
                    enabled.append(provider)
            except Exception:
                continue
        return enabled

    def _collect_imports(self) -> List[Dict[str, Any]]:
        """Collect import entries from the dynamic list."""
        imports: List[Dict[str, Any]] = []
        for i in range(1, self._import_counter + 1):
            try:
                self.query_one(f"#import-item-{i}")
            except Exception:
                continue  # removed

            name = self._get_input_value(f"import-{i}-name")
            imp_type = self._get_select_value(f"import-{i}-type", "static")
            if not name:
                continue

            entry: Dict[str, Any] = {"name": name, "type": imp_type}

            if imp_type == "static":
                hosts: List[Dict[str, Any]] = []
                max_host_idx = self._static_host_counters.get(str(i), 0)
                for host_idx in range(1, max_host_idx + 1):
                    try:
                        self.query_one(f"#import-{i}-host-item-{host_idx}")
                    except Exception:
                        continue

                    host_name = self._get_input_value(f"import-{i}-host-{host_idx}-name")
                    host_ip = self._get_input_value(f"import-{i}-host-{host_idx}-ip")
                    if not host_name and not host_ip:
                        continue
                    if not host_name or not host_ip:
                        raise ValueError(f"static import #{i} host row {host_idx}: name and ip are required")

                    row: Dict[str, Any] = {
                        "name": host_name,
                        "ip": host_ip,
                    }
                    ssh_alias = self._get_input_value(f"import-{i}-host-{host_idx}-ssh_alias")
                    ssh_user = self._get_input_value(f"import-{i}-host-{host_idx}-ssh_user")
                    ssh_port = self._get_input_value(f"import-{i}-host-{host_idx}-ssh_port")
                    ssh_key_path = self._get_input_value(f"import-{i}-host-{host_idx}-ssh_key_path")

                    if ssh_alias:
                        row["ssh_alias"] = ssh_alias
                    if ssh_user:
                        row["ssh_user"] = ssh_user
                    if ssh_port:
                        try:
                            row["ssh_port"] = int(ssh_port)
                        except ValueError:
                            row["ssh_port"] = ssh_port
                    if ssh_key_path:
                        row["ssh_key_path"] = ssh_key_path

                    hosts.append(row)
                entry["hosts"] = hosts
            elif imp_type == "netbox":
                entry["url"] = self._get_input_value(f"import-{i}-url")
                entry["token"] = self._get_input_value(f"import-{i}-token")
                filters_str = self._get_input_value(f"import-{i}-filters")
                if filters_str:
                    filters = {}
                    for pair in filters_str.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            filters[k.strip()] = v.strip()
                    entry["default_filters"] = filters
            elif imp_type == "ansible":
                paths_str = self._get_input_value(f"import-{i}-inventory_paths")
                if paths_str:
                    entry["inventory_paths"] = [p.strip() for p in paths_str.split(",") if p.strip()]
            elif imp_type == "consul":
                entry["config"] = {
                    "host": self._get_input_value(f"import-{i}-consul_host", "consul.example.com"),
                    "port": int(self._get_input_value(f"import-{i}-consul_port", "443")),
                    "token": self._get_input_value(f"import-{i}-consul_token"),
                    "scheme": self._get_input_value(f"import-{i}-consul_scheme", "https"),
                    "dc": self._get_input_value(f"import-{i}-consul_dc", "dc1"),
                }
            elif imp_type == "git":
                entry["repo_url"] = self._get_input_value(f"import-{i}-git_repo_url")
                entry["branch"] = self._get_input_value(f"import-{i}-git_branch", "main")
                entry["source_pattern"] = self._get_input_value(
                    f"import-{i}-git_source_pattern",
                    "hosts/**/*.y*ml",
                )
                entry["inventory_format"] = self._get_select_value(f"import-{i}-git_inventory_format", "static")
                entry["pull_strategy"] = "ff-only"
                entry["auto_pull"] = self._get_select_value(f"import-{i}-git_auto_pull", "true") == "true"

                pull_interval_raw = self._get_input_value(f"import-{i}-git_pull_interval", "300")
                try:
                    entry["pull_interval_seconds"] = int(pull_interval_raw)
                except ValueError as e:
                    raise ValueError(f"git import #{i}: pull interval must be an integer") from e

                priority_raw = self._get_input_value(f"import-{i}-git_priority", "100")
                try:
                    entry["priority"] = int(priority_raw)
                except ValueError as e:
                    raise ValueError(f"git import #{i}: priority must be an integer") from e

            imports.append(entry)
        return imports

    # --- Save / Cancel ---

    def _update_status(self, message: str, error: bool = False) -> None:
        """Update the status bar."""
        status = self.query_one("#editor-status", Static)
        if error:
            status.update(f"[red]{message}[/red]")
        else:
            status.update(f"[green]{message}[/green]")

    def _focus_field_for_error(self, error_text: str) -> None:
        """Best-effort focus jump to a likely related field."""
        mapping = [
            ("tmux.backend", "#cfg-mux-backend"),
            ("iterm2_native_target", "#cfg-mux-iterm2_native_target"),
            ("iterm2_split_pattern", "#cfg-mux-iterm2_split_pattern"),
            ("ui.theme", "#cfg-ui-theme"),
            ("provider", "#cfg-sot-provider-static"),
            ("logging.level", "#cfg-logging-level"),
            ("table_columns", "#cfg-ui-table_columns"),
            ("session_prefix", "#cfg-general-session_prefix"),
        ]
        for needle, selector in mapping:
            if needle in error_text:
                with contextlib.suppress(Exception):
                    self.query_one(selector).focus()
                return

    def _apply_detected_columns_from_cache(self) -> None:
        """Populate table columns using cached metadata keys plus core fields."""
        detected = self._detect_columns_from_cache_and_imports() or ["name", "ip", "cluster", "role", "tags"]

        try:
            columns_input = self.query_one("#cfg-ui-table_columns", Input)
            columns_input.value = ", ".join(detected)
            with contextlib.suppress(Exception):
                preset = self.query_one("#cfg-ui-table_columns_preset", Select)
                preset.value = "custom"
            self._update_status("Detected columns from live data/cache/imports")
        except Exception as e:
            self._update_status(f"Could not apply detected columns: {e}", error=True)

    def action_save(self) -> None:
        """Validate and save configuration."""
        try:
            data = self._collect_form_data()
        except (ValueError, TypeError) as e:
            self._update_status(f"Invalid input: {e}", error=True)
            self._focus_field_for_error(str(e))
            return

        # Validate via Pydantic
        try:
            validated = Config(**data)
        except Exception as e:
            self._update_status(f"Validation error: {e}", error=True)
            self._focus_field_for_error(str(e))
            return

        # Dump to YAML with by_alias=True for correct 'import' key
        yaml_data = validated.model_dump(by_alias=True)

        # Remove None values for cleaner YAML
        yaml_data = _clean_none(yaml_data)

        config_path = get_default_config_path() if not self.config_path else Path(self.config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            self._update_status(f"Failed to write config: {e}", error=True)
            return

        self.dismiss(True)
        self.app.notify("Configuration saved and reloaded.", title="Config Saved", timeout=4)

    def action_cancel(self) -> None:
        """Cancel editing and close."""
        self.dismiss(False)


def _clean_none(data: Any) -> Any:
    """Recursively remove None values from dicts."""
    if isinstance(data, dict):
        return {k: _clean_none(v) for k, v in data.items() if v is not None}
    if isinstance(data, list):
        return [_clean_none(item) for item in data]
    return data
