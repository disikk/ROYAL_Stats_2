# -*- coding: utf-8 -*-

"""
Типизированные результаты парсинга для различных парсеров.
Содержит dataclass'ы для структурированного представления результатов.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HandHistoryResult:
    """Результат парсинга файла истории рук (Hand History)."""
    
    tournament_id: Optional[str]
    start_time: Optional[str]
    reached_final_table: bool
    final_table_initial_stack_chips: Optional[float]
    final_table_initial_stack_bb: Optional[float]
    final_table_start_players: Optional[int]
    final_table_hands_data: List[dict]  # Временно оставляем как список словарей
    
    def is_valid(self) -> bool:
        """Проверяет валидность результата парсинга."""
        return self.tournament_id is not None


@dataclass
class TournamentSummaryResult:
    """Результат парсинга файла сводки турнира (Tournament Summary)."""
    
    tournament_id: Optional[str]
    tournament_name: Optional[str]
    start_time: Optional[str]
    buyin: Optional[float]
    payout: Optional[float]
    finish_place: Optional[int]
    
    def is_valid(self) -> bool:
        """Проверяет валидность результата парсинга."""
        return self.tournament_id is not None