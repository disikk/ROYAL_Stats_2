# -*- coding: utf-8 -*-

"""
Плагин для подсчёта общего количества нокаутов, совершённых Hero.
Обновлен для работы с OverallStats.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import OverallStats # Импортируем модель OverallStats

class TotalKOStat(BaseStat):
    name = "Total KO"
    description = "Общее количество сделанных Hero нокаутов"

    def compute(self,
                tournaments: List[Any], # Не используется напрямую этим плагином
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: OverallStats, # Используем overall_stats для получения общей суммы
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Получает общее количество KO из OverallStats.

        Args:
            overall_stats: Объект OverallStats с уже посчитанной общей суммой KO.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'total_ko'.
        """
        # Общее количество KO уже хранится в OverallStats, рассчитанное ApplicationService.
        # Плагин просто извлекает это значение.

        # Если overall_stats не передан или нет нужного поля, возвращаем 0
        total_ko = overall_stats.total_knockouts if overall_stats and hasattr(overall_stats, 'total_knockouts') else 0

        return {"total_ko": total_ko}