# -*- coding: utf-8 -*-

"""
Инициализация пакета моделей данных (dataclass) для ROYAL_Stats (Hero-only).
"""

from .base_model import BaseModel
from .tournament import Tournament
from .session import Session
from .overall_stats import OverallStats
from .final_table_hand import FinalTableHand # Новая модель

# Импортируем все модели для удобства
__all__ = [
    'BaseModel',
    'Tournament',
    'Session',
    'OverallStats',
    'FinalTableHand',
]