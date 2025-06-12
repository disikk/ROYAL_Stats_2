# -*- coding: utf-8 -*-
"""
Плагин для расчета ожидаемого значения фишек до финального стола (Pre-FT ChipEV).
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament


class PreFTChipEVStat(BaseStat):
    """
    Рассчитывает среднее ожидаемое значение выигрыша фишек до финального стола.
    
    Формула: (сумма стеков на финалках / общее количество турниров) - 1000
    Показывает средний выигрыш/проигрыш фишек относительно стартового стека 1000.
    """

    name = "Pre-FT ChipEV"
    description = "Средний выигрыш фишек до финального стола"

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[Any],
        sessions: List[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Рассчитывает Pre-FT ChipEV."""
        
        if not tournaments:
            return {"pre_ft_chipev": 0.0}
        
        # Сумма всех стартовых стеков на финалках в фишках
        ft_stack_sum = sum(
            t.final_table_initial_stack_chips 
            for t in tournaments 
            if t.reached_final_table and t.final_table_initial_stack_chips is not None
        )
        
        # Формула: сумма стеков на финалках / общее количество турниров - 1000
        pre_ft_chipev = ft_stack_sum / len(tournaments) - 1000
        
        return {
            "pre_ft_chipev": round(pre_ft_chipev, 2)
        }