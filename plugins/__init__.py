"""Infrastructure for loading plugins."""

from .plugin_manager import Plugin, discover_plugins

__all__ = ["Plugin", "discover_plugins"]
