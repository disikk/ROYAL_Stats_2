# -*- coding: utf-8 -*-

"""
Инициализация пакета парсеров для Royal Stats (Hero-only).
"""

from .hand_history import HandHistoryParser
from .tournament_summary import TournamentSummaryParser
from .base_parser import BaseParser

__all__ = [
    'HandHistoryParser',
    'TournamentSummaryParser',
    'BaseParser',
]