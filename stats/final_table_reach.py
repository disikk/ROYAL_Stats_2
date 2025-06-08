# -*- coding: utf-8 -*-

"""
Плагин для подсчёта процента попадания Hero на финальный стол.
Автономный плагин для работы с сырыми данными.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class FinalTableReachStat(BaseStat):
    """
    Считает процент попадания Hero на финальный стол (9-max).
    """
    name: str = "% Reach FT"
    description: str = "Процент турниров, в которых Hero достиг финального стола"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает процент достижения финального стола.

        Args:
            tournaments: Список объектов Tournament
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - precomputed_stats: Dict с предварительно рассчитанными total_final_tables и total_tournaments

        Returns:
            Словарь с ключом 'final_table_reach_percent' - процент достижения финального стола
        """
        tournaments = tournaments or []
        if not tournaments:
            return {"final_table_reach_percent": 0.0}

        # Проверяем наличие предварительно рассчитанных значений
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        if 'total_final_tables' in precomputed_stats and 'total_tournaments' in precomputed_stats:
            # Используем предварительно рассчитанные значения
            total_final_tables = precomputed_stats['total_final_tables']
            total_tournaments = precomputed_stats['total_tournaments']
        else:
            # Рассчитываем из сырых данных
            total_tournaments = len(tournaments)
            total_final_tables = sum(1 for t in tournaments if t.reached_final_table)
        
        # Вычисляем процент
        reach_percent = (total_final_tables / total_tournaments * 100) if total_tournaments > 0 else 0.0
        reach_percent = round(reach_percent, 2)

        return {"final_table_reach_percent": reach_percent}