# -*- coding: utf-8 -*-

"""
Инициализация пакета парсеров для Royal Stats (Hero-only).
"""

from .hand_history import HandHistoryParser
from .tournament_summary import TournamentSummaryParser
from .base_parser import BaseParser
from .base_plugin import BaseParserPlugin
from .file_classifier import FileClassifier
from plugins import discover_plugins as _discover_external_plugins

def discover_plugins(entry_point_group: str = "royal_stats"):
    """Возвращает все доступные классы плагинов-парсеров."""
    plugins = [HandHistoryParser, TournamentSummaryParser]
    discovered = _discover_external_plugins(entry_point_group)
    for plugin_cls in discovered.get("parsers", []):
        if issubclass(plugin_cls, BaseParserPlugin):
            plugins.append(plugin_cls)
    return plugins

__all__ = [
    'HandHistoryParser',
    'TournamentSummaryParser',
    'BaseParser',
    'BaseParserPlugin',
    'FileClassifier',
    'discover_plugins',
]
