"""SSHplex Configuration Editor Screen."""

from typing import Any, Dict, List

import yaml
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from ..config import Config, get_default_config_path


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


class ConfigEditorScreen(ModalScreen[bool]):
    """Modal screen for editing sshplex.yaml configuration."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+s", "save", "Save", show=True, priority=True),
    ]

    CSS = """
    ConfigEditorScreen {
        align: center middle;
    }

    #config-editor-dialog {
        width: 90%;
        height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #editor-title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
        width: 100%;
    }

    #editor-status {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
        margin-top: 1;
    }

    #editor-buttons {
        height: 3;
        dock: bottom;
        align: center middle;
        margin-top: 1;
    }

    #editor-buttons Button {
        margin: 0 2;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1;
    }

    .form-field {
        height: auto;
        margin-bottom: 1;
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
        margin-top: 1;
        margin-bottom: 1;
        color: $primary;
        text-style: bold underline;
    }

    .dynamic-list {
        border: dashed $primary;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }

    .dynamic-list-item {
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }

    .list-buttons {
        height: 3;
        align: left middle;
    }

    .list-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._proxy_counter = 0
        self._import_counter = 0
        self._import_types: Dict[str, str] = {}  # idx -> current type

    def compose(self) -> ComposeResult:
        with Vertical(id="config-editor-dialog"):
            yield Static("SSHplex Configuration Editor", id="editor-title")

            with TabbedContent():
                with TabPane("General", id="tab-general"), VerticalScroll():
                    yield _form_field(
                        "cfg-general-session_prefix",
                        "Session Prefix",
                        Input(value=self.config.sshplex.session_prefix),
                        "Prefix for tmux session names",
                    )

                with TabPane("SSH", id="tab-ssh"), VerticalScroll():
                    yield _form_field(
                        "cfg-ssh-username",
                        "Username",
                        Input(value=self.config.ssh.username),
                        "Default SSH username",
                    )
                    yield _form_field(
                        "cfg-ssh-key_path",
                        "Key Path",
                        Input(value=self.config.ssh.key_path),
                        "Path to SSH private key",
                    )
                    yield _form_field(
                        "cfg-ssh-timeout",
                        "Timeout",
                        Input(value=str(self.config.ssh.timeout)),
                        "Connection timeout in seconds",
                    )
                    yield _form_field(
                        "cfg-ssh-port",
                        "Port",
                        Input(value=str(self.config.ssh.port)),
                        "Default SSH port",
                    )
                    yield _form_field(
                        "cfg-ssh-strict_host_key_checking",
                        "Strict Host Key Checking",
                        Switch(value=self.config.ssh.strict_host_key_checking),
                    )
                    yield _form_field(
                        "cfg-ssh-user_known_hosts_file",
                        "Known Hosts File",
                        Input(value=self.config.ssh.user_known_hosts_file),
                        "Custom known_hosts file path (empty = default)",
                    )
                    # Retry sub-section
                    yield Static("Retry Settings", classes="section-header")
                    yield _form_field(
                        "cfg-ssh-retry-enabled",
                        "Retry Enabled",
                        Switch(value=self.config.ssh.retry.enabled),
                    )
                    yield _form_field(
                        "cfg-ssh-retry-max_attempts",
                        "Max Attempts",
                        Input(value=str(self.config.ssh.retry.max_attempts)),
                    )
                    yield _form_field(
                        "cfg-ssh-retry-delay_seconds",
                        "Delay Seconds",
                        Input(value=str(self.config.ssh.retry.delay_seconds)),
                    )
                    yield _form_field(
                        "cfg-ssh-retry-exponential_backoff",
                        "Exponential Backoff",
                        Switch(value=self.config.ssh.retry.exponential_backoff),
                    )
                    # Proxy list
                    yield Static("SSH Proxies", classes="section-header")
                    yield Vertical(id="proxy-list", classes="dynamic-list")

                with TabPane("Tmux", id="tab-tmux"), VerticalScroll():
                    yield _form_field(
                        "cfg-tmux-layout",
                        "Layout",
                        Select(
                            [(v, v) for v in ["tiled", "even-horizontal", "even-vertical", "main-horizontal", "main-vertical"]],
                            value=self.config.tmux.layout,
                        ),
                        "Tmux pane layout",
                    )
                    yield _form_field(
                        "cfg-tmux-broadcast",
                        "Broadcast",
                        Switch(value=self.config.tmux.broadcast),
                        "Start with broadcast enabled",
                    )
                    yield _form_field(
                        "cfg-tmux-window_name",
                        "Window Name",
                        Input(value=self.config.tmux.window_name),
                    )
                    yield _form_field(
                        "cfg-tmux-max_panes_per_window",
                        "Max Panes Per Window",
                        Input(value=str(self.config.tmux.max_panes_per_window)),
                    )
                    yield _form_field(
                        "cfg-tmux-control_with_iterm2",
                        "iTerm2 Integration",
                        Switch(value=self.config.tmux.control_with_iterm2),
                        "Use iTerm2 tmux -CC mode on macOS",
                    )

                with TabPane("Sources", id="tab-sources"), VerticalScroll():
                    yield _form_field(
                        "cfg-sot-providers",
                        "Providers",
                        Input(value=", ".join(self.config.sot.providers)),
                        "Comma-separated list of provider types",
                    )
                    yield Static("Imports", classes="section-header")
                    yield Vertical(id="import-list", classes="dynamic-list")

                with TabPane("UI", id="tab-ui"), VerticalScroll():
                    yield _form_field(
                        "cfg-ui-show_log_panel",
                        "Show Log Panel",
                        Switch(value=self.config.ui.show_log_panel),
                    )
                    yield _form_field(
                        "cfg-ui-log_panel_height",
                        "Log Panel Height (%)",
                        Input(value=str(self.config.ui.log_panel_height)),
                    )
                    yield _form_field(
                        "cfg-ui-table_columns",
                        "Table Columns",
                        Input(value=", ".join(self.config.ui.table_columns)),
                        "Comma-separated column names",
                    )

                with TabPane("Logging", id="tab-logging"), VerticalScroll():
                    yield _form_field(
                        "cfg-logging-enabled",
                        "Enabled",
                        Switch(value=self.config.logging.enabled),
                    )
                    yield _form_field(
                        "cfg-logging-level",
                        "Level",
                        Select(
                            [(v, v) for v in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]],
                            value=self.config.logging.level,
                        ),
                    )
                    yield _form_field(
                        "cfg-logging-file",
                        "Log File",
                        Input(value=self.config.logging.file),
                    )

                with TabPane("Cache", id="tab-cache"), VerticalScroll():
                    yield _form_field(
                        "cfg-cache-enabled",
                        "Enabled",
                        Switch(value=self.config.cache.enabled),
                    )
                    yield _form_field(
                        "cfg-cache-cache_dir",
                        "Cache Directory",
                        Input(value=self.config.cache.cache_dir),
                    )
                    yield _form_field(
                        "cfg-cache-ttl_hours",
                        "TTL (hours)",
                        Input(value=str(self.config.cache.ttl_hours)),
                    )

            with Horizontal(id="editor-buttons"):
                yield Button("Save (Ctrl+S)", id="btn-save", variant="primary")
                yield Button("Cancel (Esc)", id="btn-cancel", variant="default")

            yield Static("", id="editor-status")

    def on_mount(self) -> None:
        """Populate dynamic lists after mount."""
        self._populate_proxy_list()
        self._populate_import_list()

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
            Input(value=name, placeholder="Proxy name", id=f"proxy-{idx}-name"),
            Input(value=imports, placeholder="Imports (comma-separated)", id=f"proxy-{idx}-imports"),
            Input(value=host, placeholder="Host", id=f"proxy-{idx}-host"),
            Input(value=username, placeholder="Username", id=f"proxy-{idx}-username"),
            Input(value=key_path, placeholder="Key path", id=f"proxy-{idx}-key_path"),
            Button("Remove", id=f"btn-remove-proxy-{idx}", variant="error"),
            classes="dynamic-list-item",
            id=f"proxy-item-{idx}",
        )

    # --- Dynamic import list ---

    def _populate_import_list(self) -> None:
        """Populate the import list from current config."""
        container = self.query_one("#import-list", Vertical)
        for imp in self.config.sot.import_:
            self._import_counter += 1
            container.mount(self._make_import_item(self._import_counter, imp))
        container.mount(
            Horizontal(
                Button("+ Add Import", id="btn-add-import", variant="success"),
                classes="list-buttons",
            )
        )

    def _make_import_item(self, idx: int, imp: Any = None) -> Vertical:
        """Create an import form item with type-specific fields."""
        name = imp.name if imp else ""
        imp_type = imp.type if imp else "static"
        self._import_types[str(idx)] = imp_type

        children: List[Any] = [
            Label(f"Import #{idx}", classes="form-label"),
            Input(value=name, placeholder="Import name", id=f"import-{idx}-name"),
            Select(
                [(v, v) for v in ["static", "netbox", "ansible", "consul"]],
                value=imp_type,
                id=f"import-{idx}-type",
            ),
        ]

        # Type-specific fields
        children.extend(self._make_import_type_fields(idx, imp_type, imp))

        children.append(Button("Remove", id=f"btn-remove-import-{idx}", variant="error"))

        return Vertical(
            *children,
            classes="dynamic-list-item",
            id=f"import-item-{idx}",
        )

    def _make_import_type_fields(self, idx: int, imp_type: str, imp: Any = None) -> list:
        """Generate type-specific fields for an import item."""
        fields: list = []
        if imp_type == "static":
            hosts_yaml = ""
            if imp and imp.hosts:
                hosts_yaml = yaml.dump(imp.hosts, default_flow_style=False).strip()
            fields.append(
                Input(
                    value=hosts_yaml,
                    placeholder="hosts YAML (list of dicts)",
                    id=f"import-{idx}-hosts",
                )
            )
        elif imp_type == "netbox":
            fields.append(Input(value=(imp.url or "") if imp else "", placeholder="NetBox URL", id=f"import-{idx}-url"))
            fields.append(Input(value=(imp.token or "") if imp else "", placeholder="API Token", id=f"import-{idx}-token", password=True))
            filters_str = ""
            if imp and imp.default_filters:
                filters_str = ", ".join(f"{k}={v}" for k, v in imp.default_filters.items())
            fields.append(Input(value=filters_str, placeholder="Filters (key=val, ...)", id=f"import-{idx}-filters"))
        elif imp_type == "ansible":
            paths = ""
            if imp and imp.inventory_paths:
                paths = ", ".join(imp.inventory_paths)
            fields.append(Input(value=paths, placeholder="Inventory paths (comma-separated)", id=f"import-{idx}-inventory_paths"))
        elif imp_type == "consul":
            cfg = imp.config if imp else None
            fields.append(Input(value=(cfg.host if cfg else ""), placeholder="Consul host", id=f"import-{idx}-consul_host"))
            fields.append(Input(value=str(cfg.port if cfg else 443), placeholder="Port", id=f"import-{idx}-consul_port"))
            fields.append(Input(value=(cfg.token if cfg else ""), placeholder="Token", id=f"import-{idx}-consul_token", password=True))
            fields.append(Input(value=(cfg.scheme if cfg else "https"), placeholder="Scheme", id=f"import-{idx}-consul_scheme"))
            fields.append(Input(value=(cfg.dc if cfg else "dc1"), placeholder="Datacenter", id=f"import-{idx}-consul_dc"))

        return fields

    # --- Button handlers ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id or ""

        if btn_id == "btn-save":
            self.action_save()
        elif btn_id == "btn-cancel":
            self.action_cancel()
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

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle import type changes to re-render type-specific fields."""
        select_id = event.select.id or ""
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
        self.run_worker(self._rebuild_import_type_fields(idx, new_type))

    async def _rebuild_import_type_fields(self, idx: str, new_type: str) -> None:
        """Rebuild type-specific fields when import type changes."""
        container = self.query_one(f"#import-item-{idx}", Vertical)

        # Remove old type-specific fields (everything between the Select and the Remove button)
        children = list(container.children)
        # Keep: Label, name Input, type Select, remove Button
        # Remove everything else
        found_select = False
        for child in children:
            child_id = getattr(child, "id", "") or ""
            if child_id == f"import-{idx}-type":
                found_select = True
                continue
            if found_select and not child_id.startswith("btn-remove-import-"):
                await child.remove()
            elif child_id.startswith("btn-remove-import-"):
                break

        # Insert new type-specific fields before the Remove button
        new_fields = self._make_import_type_fields(int(idx), new_type)
        remove_btn = container.query_one(f"#btn-remove-import-{idx}", Button)
        for field in reversed(new_fields):
            await container.mount(field, before=remove_btn)

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
        container.mount(self._make_import_item(self._import_counter), before=add_btn_row)

    def _remove_import(self, idx: str) -> None:
        """Remove an import entry."""
        try:
            item = self.query_one(f"#import-item-{idx}")
            item.remove()
        except Exception:
            pass

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

        # Tmux
        data["tmux"] = {
            "layout": self._get_select_value("cfg-tmux-layout", "tiled"),
            "broadcast": self._get_switch_value("cfg-tmux-broadcast"),
            "window_name": self._get_input_value("cfg-tmux-window_name", "sshplex"),
            "max_panes_per_window": int(self._get_input_value("cfg-tmux-max_panes_per_window", "5")),
            "control_with_iterm2": self._get_switch_value("cfg-tmux-control_with_iterm2"),
        }

        # Sources
        providers_str = self._get_input_value("cfg-sot-providers", "static")
        providers = [p.strip() for p in providers_str.split(",") if p.strip()]
        imports = self._collect_imports()
        data["sot"] = {
            "providers": providers,
            "import": imports,
        }

        # UI
        columns_str = self._get_input_value("cfg-ui-table_columns", "name, ip, cluster, role, tags")
        columns = [c.strip() for c in columns_str.split(",") if c.strip()]
        data["ui"] = {
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
            "cache_dir": self._get_input_value("cfg-cache-cache_dir", "~/cache/sshplex"),
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
                hosts_str = self._get_input_value(f"import-{i}-hosts")
                if hosts_str:
                    try:
                        entry["hosts"] = yaml.safe_load(hosts_str)
                    except yaml.YAMLError:
                        entry["hosts"] = []
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

    def action_save(self) -> None:
        """Validate and save configuration."""
        try:
            data = self._collect_form_data()
        except (ValueError, TypeError) as e:
            self._update_status(f"Invalid input: {e}", error=True)
            return

        # Validate via Pydantic
        try:
            validated = Config(**data)
        except Exception as e:
            self._update_status(f"Validation error: {e}", error=True)
            return

        # Dump to YAML with by_alias=True for correct 'import' key
        yaml_data = validated.model_dump(by_alias=True)

        # Remove None values for cleaner YAML
        yaml_data = _clean_none(yaml_data)

        config_path = get_default_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            self._update_status(f"Failed to write config: {e}", error=True)
            return

        self.dismiss(True)
        self.app.notify("Configuration saved. Restart SSHplex for changes to take effect.", title="Config Saved", timeout=5)

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
