# -*- coding: utf-8 -*-

"""
Плагин для подсчёта среднего занятого места Hero на финальном столе (позиции 1-9).
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats

class AvgFinishPlaceFTStat(BaseStat):
    """
    Считает среднее финишное место Hero только среди турниров, 
    где он достиг финального стола (позиции 1-9).
    """
    name: str = "Avg Place on FT"
    description: str = "Среднее занятое место на финальном столе (1-9)"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any],
                sessions: List[Any],
                overall_stats: Any,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает среднее финишное место только среди турниров на финалке.

        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'avg_finish_place_ft'.
        """
        if not tournaments and not overall_stats:
            return {"avg_finish_place_ft": 0.0}

        # Этот стат уже рассчитывается и хранится в OverallStats
        # Плагин просто извлекает его.
        if overall_stats and hasattr(overall_stats, 'avg_finish_place_ft'):
            avg_place_ft = overall_stats.avg_finish_place_ft
        else:
            # Fallback расчет
            ft_places = [t.finish_place for t in tournaments 
                        if t.reached_final_table and t.finish_place is not None 
                        and 1 <= t.finish_place <= 9]
            avg_place_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0
            avg_place_ft = round(avg_place_ft, 2)

        return {"avg_finish_place_ft": avg_place_ft}