#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Инициализация модуля базы данных для ROYAL_Stats.
Экспортирует классы и функции для работы с базой данных.
"""

from .database import DatabaseManager
from . import schema

__all__ = [
    'DatabaseManager',
    'schema'
]
