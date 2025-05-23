# -*- coding: utf-8 -*-

"""
Плагин для подсчёта среднего стека Hero в начале финального стола.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats # Импортируем модели
import math # Для округления

class AvgFTInitialStackStat(BaseStat):
    """
    Считает средний стек Hero в фишках и BB в первой раздаче финального стола.
    """
    name: str = "Avg FT Initial Stack"
    description: str = "Средний стек Hero в начале финального стола (фишки / BB)"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: Any, # Используем overall_stats для получения общих сумм
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает средний начальный стек на финалке.

        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключами 'avg_ft_initial_stack_chips' и 'avg_ft_initial_stack_bb'.
        """
        if not tournaments and not overall_stats:
            return {"avg_ft_initial_stack_chips": 0.0, "avg_ft_initial_stack_bb": 0.0}

        # Эти статы уже рассчитываются и хранятся в OverallStats
        # Плагин просто извлекает их.

        if overall_stats and hasattr(overall_stats, 'avg_ft_initial_stack_chips') and hasattr(overall_stats, 'avg_ft_initial_stack_bb'):
            avg_chips = overall_stats.avg_ft_initial_stack_chips
            avg_bb = overall_stats.avg_ft_initial_stack_bb
        else:
            # Fallback расчет
            ft_initial_stacks_chips = [t.final_table_initial_stack_chips for t in tournaments if t.reached_final_table and t.final_table_initial_stack_chips is not None]
            avg_chips = sum(ft_initial_stacks_chips) / len(ft_initial_stacks_chips) if ft_initial_stacks_chips else 0.0
            avg_chips = round(avg_chips, 2)

            ft_initial_stacks_bb = [t.final_table_initial_stack_bb for t in tournaments if t.reached_final_table and t.final_table_initial_stack_bb is not None]
            avg_bb = sum(ft_initial_stacks_bb) / len(ft_initial_stacks_bb) if ft_initial_stacks_bb else 0.0
            avg_bb = round(avg_bb, 2)

        return {
            "avg_ft_initial_stack_chips": avg_chips,
            "avg_ft_initial_stack_bb": avg_bb,
        }