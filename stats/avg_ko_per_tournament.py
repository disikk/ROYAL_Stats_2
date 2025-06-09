# -*- coding: utf-8 -*-

"""
Плагин для подсчёта среднего количества нокаутов Hero за турнир.
Автономный плагин для работы с сырыми данными.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class AvgKOPerTournamentStat(BaseStat):
    """
    Считает среднее количество KO Hero за каждый сыгранный турнир.
    """
    name: str = "Avg KO / Tournament"
    description: str = "Среднее количество нокаутов Hero за турнир"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает среднее количество KO за турнир.

        Args:
            tournaments: Список объектов Tournament
            final_table_hands: Список рук финального стола (не используется напрямую)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - precomputed_stats: Dict с предварительно рассчитанным avg_ko_per_tournament

        Returns:
            Словарь с ключом 'avg_ko_per_tournament' - среднее количество KO за турнир
        """
        tournaments = tournaments or []
        if not tournaments:
            return {"avg_ko_per_tournament": 0.0}

        # Проверяем наличие предварительно рассчитанного значения
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        if 'avg_ko_per_tournament' in precomputed_stats:
            # Используем предварительно рассчитанное значение
            avg_ko = precomputed_stats['avg_ko_per_tournament']
        else:
            # Рассчитываем из сырых данных
            total_ko = sum(t.ko_count for t in tournaments if t.ko_count is not None)
            total_tournaments = len(tournaments)
            avg_ko = total_ko / total_tournaments if total_tournaments > 0 else 0.0
            avg_ko = round(avg_ko, 2)

        return {"avg_ko_per_tournament": avg_ko}