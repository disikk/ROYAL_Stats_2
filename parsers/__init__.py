#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats - Парсеры файлов для покерного трекера.
Данный модуль служит для импорта всех парсеров.
"""

from parsers.base_parser import BaseParser
from parsers.detector import detect_file_type
from parsers.hand_history import HandHistoryParser
from parsers.tournament_summary import TournamentSummaryParser

__all__ = [
    'BaseParser', 
    'detect_file_type', 
    'HandHistoryParser', 
    'TournamentSummaryParser'
]