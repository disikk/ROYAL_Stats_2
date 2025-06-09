# -*- coding: utf-8 -*-
"""Utility for discovering and loading plugins."""

import logging
from importlib import metadata
from typing import Dict, List, Type

logger = logging.getLogger(__name__)


class Plugin:
    """Base class for all plugins."""

    #: Human readable plugin name
    name: str = "plugin"
    #: Category name used for grouping
    category: str = "default"


def discover_plugins(entry_point_group: str = "royal_stats") -> Dict[str, List[Type[Plugin]]]:
    """Discover plugins registered via entry points.

    Args:
        entry_point_group: Entry point group name.

    Returns:
        Dictionary where key is plugin category and value is list of plugin
        classes.
    """
    discovered: Dict[str, List[Type[Plugin]]] = {}
    try:
        eps = metadata.entry_points()
        selected = eps.select(group=entry_point_group) if hasattr(eps, "select") else eps.get(entry_point_group, [])
        for ep in selected:
            try:
                plugin_cls = ep.load()
                category = getattr(plugin_cls, "category", "default")
                discovered.setdefault(category, []).append(plugin_cls)
            except Exception as exc:
                logger.error("Failed to load plugin from entry point %s: %s", ep.name, exc)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to read entry points: %s", exc)
    return discovered
