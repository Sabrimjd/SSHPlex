"""Shared command helpers for main and CLI entry points."""

from __future__ import annotations

from typing import Any

from .cache import HostCache
from .config import get_config_info
from .sot.factory import SoTFactory


def show_config_info() -> int:
    """Show configuration file paths and status."""
    info = get_config_info()

    print("📁 SSHplex Configuration Information")
    print("=" * 50)
    print(f"Config Directory:    {info['default_config_path'].rsplit('/', 1)[0]}")
    print(f"Config File:         {info['default_config_path']}")
    print(f"Config Exists:       {'✅ Yes' if info['default_config_exists'] else '❌ No'}")
    print(f"Template File:       {info['template_path']}")
    print(f"Template Exists:     {'✅ Yes' if info['template_exists'] else '❌ No'}")
    print()

    if not info['default_config_exists']:
        print("💡 Run 'sshplex' to create a default configuration file")

    return 0


def clear_cache(config: Any, logger: Any, no_cache_message: str = "No cache to clear") -> int:
    """Clear the host cache."""
    logger.info("Clearing host cache")

    cache = HostCache(
        cache_dir=config.cache.cache_dir,
        cache_ttl_hours=config.cache.ttl_hours,
    )

    cache_info = cache.get_cache_info()
    if cache_info:
        print(
            "🗑️  Clearing cache "
            f"({cache_info.get('host_count', 0)} hosts, age: {cache_info.get('age_hours', 0):.1f}h)"
        )
    else:
        print(f"🗑️  {no_cache_message}")

    if cache.clear_cache():
        print("✅ Cache cleared successfully")
        return 0

    print("❌ Failed to clear cache")
    return 1


def run_debug_mode(config: Any, logger: Any, footer_note: str = "") -> int:
    """Run provider connectivity + host retrieval debug flow."""
    logger.info("Running debug mode - SoT provider connectivity test")

    sot_factory = SoTFactory(config)

    cache_info = sot_factory.get_cache_info()
    if cache_info:
        print(f"📦 Cache: {cache_info.get('host_count', 0)} hosts cached ({cache_info.get('age_hours', 0):.1f}h old)")

    if not sot_factory.initialize_providers():
        logger.error("Failed to initialize any SoT providers")
        print("❌ Failed to initialize any SoT providers")
        print("Check your configuration and network connectivity")
        return 1

    print(
        "✅ Successfully initialized "
        f"{sot_factory.get_provider_count()} SoT provider(s): {', '.join(sot_factory.get_provider_names())}"
    )

    logger.info("Testing SoT provider connections...")
    connection_results = sot_factory.test_all_connections()

    for provider_name, status in connection_results.items():
        if status:
            print(f"✅ {provider_name}: Connection successful")
        else:
            print(f"❌ {provider_name}: Connection failed")

    logger.info("Retrieving hosts from all SoT providers...")
    hosts = sot_factory.get_all_hosts()

    if hosts:
        logger.info(f"Successfully retrieved {len(hosts)} hosts")
        print(f"\n📋 Found {len(hosts)} hosts from all providers:")
        print("-" * 80)
        for i, host in enumerate(hosts, 1):
            status = getattr(host, 'status', host.metadata.get('status', 'unknown'))
            sources = host.metadata.get('sources', ['unknown'])
            source_str = ', '.join(sources) if isinstance(sources, list) else str(sources)
            print(f"{i:3d}. {host.name:<25} {host.ip:<15} [{status:<8}] ({source_str})")
        print("-" * 80)
    else:
        logger.warning("No hosts found matching the filters")
        print("⚠️  No hosts found matching the configured filters")
        print("Check your SoT provider filters in the configuration")

    logger.info("SSHplex debug mode completed successfully")
    print("\n✅ Debug mode completed successfully")
    if footer_note:
        print(footer_note)
    return 0
