# -*- coding: utf-8 -*-

"""
Плагин для подсчёта среднего занятого места Hero когда не дошел до финального стола.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats

class AvgFinishPlaceNoFTStat(BaseStat):
    """
    Считает среднее финишное место Hero только среди турниров, 
    где он НЕ достиг финального стола (reached_final_table = False).
    """
    name: str = "Avg Place No FT"
    description: str = "Среднее место когда не дошел до финального стола"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any],
                sessions: List[Any],
                overall_stats: Any,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает среднее финишное место среди турниров без финалки.

        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'avg_finish_place_no_ft'.
        """
        if not tournaments and not overall_stats:
            return {"avg_finish_place_no_ft": 0.0}

        # Этот стат нужно добавить в OverallStats
        # Пока делаем fallback расчет всегда
        if overall_stats and hasattr(overall_stats, 'avg_finish_place_no_ft'):
            avg_place_no_ft = overall_stats.avg_finish_place_no_ft
        else:
            # Fallback расчет - турниры где не дошли до финалки
            no_ft_places = [t.finish_place for t in tournaments 
                           if not t.reached_final_table and t.finish_place is not None]
            avg_place_no_ft = sum(no_ft_places) / len(no_ft_places) if no_ft_places else 0.0
            avg_place_no_ft = round(avg_place_no_ft, 2)

        return {"avg_finish_place_no_ft": avg_place_no_ft}