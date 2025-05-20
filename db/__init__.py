# -*- coding: utf-8 -*-

"""
Инициализация модуля базы данных для ROYAL_Stats (Hero-only).
Экспортирует менеджер базы данных и схему.
"""

# Импортируем синглтон DatabaseManager
from .manager import database_manager
# Импортируем модуль схемы (содержит SQL запросы)
from . import schema

# Импортируем все репозитории для удобства доступа через db.repositories
from . import repositories

__all__ = [
    'database_manager', # Теперь экспортируем синглтон
    'schema',
    'repositories', # Экспортируем пакет репозиториев
]