#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats - Ядро и управление статистическими модулями.
"""

__all__ = ['plugin_manager']

from core.plugin_manager import PluginManager

# Создаем экземпляр менеджера модулей
plugin_manager = PluginManager()