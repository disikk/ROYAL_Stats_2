# -*- coding: utf-8 -*-

"""
ROI-плагин для Hero.
Обновлен для работы с OverallStats.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import OverallStats # Импортируем модель OverallStats
import math # Для округления

class ROIStat(BaseStat):
    name = "ROI"
    description = "Return On Investment (ROI) — средний возврат на вложенный бай-ин для Hero"

    def compute(self,
                tournaments: List[Any], # Не используется напрямую этим плагином
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: OverallStats, # Используем overall_stats для получения общих сумм
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает ROI на основе общих бай-инов и выплат из OverallStats.

        Args:
            overall_stats: Объект OverallStats с общими суммами бай-инов и выплат.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'roi'.
        """
        # ROI рассчитывается на основе общих сумм, которые хранятся в OverallStats.
        # Плагин использует эти агрегированные данные.

        total_buyin = 0.0
        total_payout = 0.0

        if overall_stats and hasattr(overall_stats, 'total_buy_in') and hasattr(overall_stats, 'total_prize'):
             total_buyin = overall_stats.total_buy_in
             total_payout = overall_stats.total_prize

        profit = total_payout - total_buyin

        if total_buyin == 0:
            roi = 0.0
        else:
            roi = (profit / total_buyin) * 100.0

        # Округляем до двух знаков после запятой
        roi = round(roi, 2)

        return {"roi": roi}