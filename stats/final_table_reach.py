# -*- coding: utf-8 -*-

"""
Плагин для подсчёта процента попадания Hero на финальный стол.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats # Импортируем модели

class FinalTableReachStat(BaseStat):
    """
    Считает процент попадания Hero на финальный стол (9-max).
    """
    name: str = "% Reach FT"
    description: str = "Процент турниров, в которых Hero достиг финального стола"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: Any, # Используем overall_stats для получения общих сумм
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает процент достижения финального стола.

        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'final_table_reach_percent'.
        """
        if not tournaments and not overall_stats:
            return {"final_table_reach_percent": 0.0}

        # Этот стат уже рассчитывается и хранится в OverallStats
        # Плагин просто извлекает его.

        if overall_stats and hasattr(overall_stats, 'total_final_tables') and hasattr(overall_stats, 'total_tournaments'):
            total_final_tables = overall_stats.total_final_tables
            total_tournaments = overall_stats.total_tournaments
            reach_percent = (total_final_tables / total_tournaments * 100) if total_tournaments > 0 else 0.0
            reach_percent = round(reach_percent, 2)
        else:
            # Fallback расчет
            total_tournaments = len(tournaments)
            total_final_tables = sum(1 for t in tournaments if t.reached_final_table)
            reach_percent = (total_final_tables / total_tournaments * 100) if total_tournaments > 0 else 0.0
            reach_percent = round(reach_percent, 2)


        return {"final_table_reach_percent": reach_percent}