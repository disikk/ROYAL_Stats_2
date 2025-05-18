"""
Пакет парсеров для Royal Stats (Hero-only).
"""

from .hand_history import HandHistoryParser
from .tournament_summary import TournamentSummaryParser
from .base_parser import BaseParser
# utils импортировать только если требуется для внешнего использования
