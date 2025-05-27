# -*- coding: utf-8 -*-

"""
Плагин для подсчёта среднего занятого места Hero по всем турнирам.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats

class AvgFinishPlaceStat(BaseStat):
    """
    Считает среднее финишное место Hero по всем сыгранным турнирам.
    """
    name: str = "Avg Finish Place"
    description: str = "Среднее занятое место Hero по всем турнирам"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any],
                sessions: List[Any],
                overall_stats: Any,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает среднее финишное место по всем турнирам.

        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'avg_finish_place'.
        """
        if not tournaments and not overall_stats:
            return {"avg_finish_place": 0.0}

        # Этот стат уже рассчитывается и хранится в OverallStats
        # Плагин просто извлекает его.
        if overall_stats and hasattr(overall_stats, 'avg_finish_place'):
            avg_place = overall_stats.avg_finish_place
        else:
            # Fallback расчет
            places = [t.finish_place for t in tournaments if t.finish_place is not None]
            avg_place = sum(places) / len(places) if places else 0.0
            avg_place = round(avg_place, 2)

        return {"avg_finish_place": avg_place}