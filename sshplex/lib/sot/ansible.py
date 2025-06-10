"""Ansible YAML Inventory Source of Truth provider for SSHplex."""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from ..logger import get_logger
from .base import SoTProvider, Host


class AnsibleProvider(SoTProvider):
    """Ansible YAML inventory implementation of SoT provider."""

    def __init__(self, inventory_paths: List[Union[str, Path]], filters: Optional[Dict[str, Any]] = None) -> None:
        """Initialize Ansible provider.

        Args:
            inventory_paths: List of paths to Ansible inventory YAML files
            filters: Optional filters to apply (groups, host patterns, etc.)
        """
        self.inventory_paths = [Path(path) for path in inventory_paths]
        self.filters = filters or {}
        self.inventories: List[Dict[str, Any]] = []
        self.logger = get_logger()

    def connect(self) -> bool:
        """Load and parse Ansible inventory files.

        Returns:
            True if all inventories loaded successfully, False otherwise
        """
        try:
            self.logger.info(f"Loading Ansible inventories from {len(self.inventory_paths)} files")

            self.inventories = []
            failed_files = []

            for inventory_path in self.inventory_paths:
                try:
                    if not inventory_path.exists():
                        self.logger.error(f"Ansible inventory file not found: {inventory_path}")
                        failed_files.append(str(inventory_path))
                        continue

                    self.logger.info(f"Loading inventory from: {inventory_path}")

                    with open(inventory_path, 'r') as f:
                        inventory_data = yaml.safe_load(f)

                    if not inventory_data:
                        self.logger.warning(f"Empty inventory file: {inventory_path}")
                        continue

                    self.inventories.append({
                        'path': str(inventory_path),
                        'data': inventory_data
                    })
                    self.logger.info(f"Successfully loaded inventory from: {inventory_path}")

                except yaml.YAMLError as e:
                    self.logger.error(f"Invalid YAML in inventory file {inventory_path}: {e}")
                    failed_files.append(str(inventory_path))
                except Exception as e:
                    self.logger.error(f"Error loading inventory file {inventory_path}: {e}")
                    failed_files.append(str(inventory_path))

            if failed_files:
                self.logger.warning(f"Failed to load {len(failed_files)} inventory files: {failed_files}")

            if not self.inventories:
                self.logger.error("No valid inventory files loaded")
                return False

            self.logger.info(f"Successfully loaded {len(self.inventories)} inventory files")
            return True

        except Exception as e:
            self.logger.error(f"Ansible inventory loading failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test if inventories are loaded.

        Returns:
            True if inventories are loaded, False otherwise
        """
        return len(self.inventories) > 0

    def get_hosts(self, filters: Optional[Dict[str, Any]] = None) -> List[Host]:
        """Retrieve hosts from Ansible inventories.

        Args:
            filters: Optional filters to apply (groups, host_patterns, etc.)

        Returns:
            List of Host objects
        """
        if not self.inventories:
            self.logger.error("No inventories loaded. Call connect() first.")
            return []

        try:
            # Merge filters
            active_filters = self.filters.copy()
            if filters:
                active_filters.update(filters)

            self.logger.info("Extracting hosts from Ansible inventories")
            if active_filters:
                self.logger.info(f"Applying filters: {active_filters}")

            hosts = []

            for inventory in self.inventories:
                inventory_hosts = self._extract_hosts_from_inventory(
                    inventory['data'],
                    inventory['path'],
                    active_filters
                )
                hosts.extend(inventory_hosts)

            # Remove duplicates based on name + ip combination
            unique_hosts = {}
            for host in hosts:
                key = f"{host.name}:{host.ip}"
                if key not in unique_hosts:
                    unique_hosts[key] = host
                else:
                    # If duplicate, merge metadata from both inventories
                    existing = unique_hosts[key]
                    existing.metadata.update(host.metadata)

            final_hosts = list(unique_hosts.values())
            self.logger.info(f"Retrieved {len(final_hosts)} unique hosts from Ansible inventories")
            return final_hosts

        except Exception as e:
            self.logger.error(f"Failed to retrieve hosts from Ansible inventories: {e}")
            return []

    def _extract_hosts_from_inventory(self, inventory_data: Dict[str, Any], inventory_path: str,
                                      filters: Dict[str, Any]) -> List[Host]:
        """Extract hosts from a single inventory data structure.

        Args:
            inventory_data: Parsed YAML inventory data
            inventory_path: Path to the inventory file (for metadata)
            filters: Filters to apply

        Returns:
            List of Host objects
        """
        # Get group filters
        include_groups = filters.get('groups', [])
        exclude_groups = filters.get('exclude_groups', [])
        host_patterns = filters.get('host_patterns', [])

        # First, collect all hosts with their group hierarchy
        all_hosts_with_groups: List[Tuple[Host, List[str]]] = []

        if 'all' in inventory_data:
            self._collect_hosts_with_hierarchy(
                inventory_data['all'],
                'all',
                inventory_path,
                [],  # parent_groups
                all_hosts_with_groups,
                host_patterns
            )
        else:
            # If no 'all' group, parse top-level structure
            for group_name, group_data in inventory_data.items():
                if isinstance(group_data, dict):
                    self._collect_hosts_with_hierarchy(
                        group_data,
                        group_name,
                        inventory_path,
                        [],  # parent_groups
                        all_hosts_with_groups,
                        host_patterns
                    )

        # Now filter based on group membership
        filtered_hosts = []

        for host, host_groups in all_hosts_with_groups:
            # Check exclude groups first
            if exclude_groups and any(group in exclude_groups for group in host_groups):
                continue

            # Check include groups (if specified)
            if include_groups:
                if any(group in include_groups for group in host_groups):
                    filtered_hosts.append(host)
            else:
                # No include filter, include all (except excluded)
                filtered_hosts.append(host)

        return filtered_hosts

    def _collect_hosts_with_hierarchy(self, group_data: Dict[str, Any], group_name: str, inventory_path: str,
                                      parent_groups: List[str], hosts_with_groups: List[Tuple[Host, List[str]]],
                                      host_patterns: List[str]) -> None:
        """Collect all hosts with their full group hierarchy.

        Args:
            group_data: Group data from inventory
            group_name: Name of the current group
            inventory_path: Path to inventory file
            parent_groups: List of parent group names
            hosts_with_groups: List to collect (host, group_list) tuples
            host_patterns: Host name patterns to match
        """
        current_hierarchy = parent_groups + [group_name]

        # Parse direct hosts in this group
        if 'hosts' in group_data:
            for host_name, host_vars in group_data['hosts'].items():
                host = self._create_host_from_vars(
                    host_name,
                    host_vars or {},
                    group_name,
                    inventory_path,
                    host_patterns
                )
                if host:
                    hosts_with_groups.append((host, current_hierarchy))

        # Recursively parse child groups
        if 'children' in group_data:
            for child_group_name, child_group_data in group_data['children'].items():
                if isinstance(child_group_data, dict):
                    self._collect_hosts_with_hierarchy(
                        child_group_data,
                        child_group_name,
                        inventory_path,
                        current_hierarchy,
                        hosts_with_groups,
                        host_patterns
                    )

    def _create_host_from_vars(self, host_name: str, host_vars: Dict[str, Any], group_name: str,
                               inventory_path: str, host_patterns: List[str]) -> Optional[Host]:
        """Create a Host object from Ansible host variables.

        Args:
            host_name: Name of the host
            host_vars: Host variables from inventory
            group_name: Group containing this host
            inventory_path: Path to inventory file
            host_patterns: Host name patterns to match

        Returns:
            Host object or None if filtered out
        """
        try:
            # Apply host pattern filters
            if host_patterns:
                import re
                matched = False
                for pattern in host_patterns:
                    if re.search(pattern, host_name):
                        matched = True
                        break
                if not matched:
                    return None

            # Get IP address from ansible_host variable
            ip = host_vars.get('ansible_host')
            if not ip:
                self.logger.warning(f"Host {host_name} has no ansible_host variable, skipping")
                return None

            # Extract other useful variables
            ansible_port = host_vars.get('ansible_port', 22)
            ansible_user = host_vars.get('ansible_user', '')
            ansible_connection = host_vars.get('ansible_connection', 'ssh')

            # Create host with metadata
            host = Host(
                name=host_name,
                ip=ip,
                status="active",  # Assume active since it's in inventory
                role=group_name,  # Use group as role
                platform="ansible",  # Mark as from Ansible
                cluster=group_name,  # Use group as cluster
                tags=f"ansible,{group_name}",
                description=f"From Ansible inventory: {Path(inventory_path).name}",
                # Ansible-specific metadata
                ansible_port=ansible_port,
                ansible_user=ansible_user,
                ansible_connection=ansible_connection,
                ansible_group=group_name,
                inventory_file=inventory_path,
                provider=getattr(self, 'provider_name', 'ansible')
            )

            # Add source information to metadata
            host.metadata['sources'] = [getattr(self, 'provider_name', 'ansible')]
            host.metadata['provider'] = getattr(self, 'provider_name', 'ansible')

            # Add all other host variables as metadata
            for key, value in host_vars.items():
                if key not in ['ansible_host', 'ansible_port', 'ansible_user', 'ansible_connection']:
                    setattr(host, f"ansible_{key}", value)

            self.logger.debug(f"Added Ansible host: {host}")
            return host

        except Exception as e:
            self.logger.error(f"Error processing Ansible host {host_name}: {e}")
            return None
