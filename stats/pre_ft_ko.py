# -*- coding: utf-8 -*-
"""
Плагин для подсчёта количества KO, сделанных перед началом финального стола.
Рассчитывает сумму KO, начисленных за последнюю 5-max раздачу перед финалкой.
"""
from typing import Dict, Any, List
from .base import BaseStat
from models import FinalTableHand, OverallStats


class PreFTKOStat(BaseStat):
    name: str = "Pre FT KO"
    description: str = "KO, сделанные до начала финального стола (последняя 5-max раздача)"

    def compute(
        self,
        tournaments: List[Any],
        final_table_hands: List[FinalTableHand],
        sessions: List[Any],
        overall_stats: OverallStats,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Возвращает количество KO перед финальным столом."""
        if not final_table_hands and not overall_stats:
            return {"pre_ft_ko_count": 0.0}

        if overall_stats and hasattr(overall_stats, "pre_ft_ko_count"):
            count = overall_stats.pre_ft_ko_count
        else:
            count = sum(hand.pre_ft_ko for hand in final_table_hands)

        return {"pre_ft_ko_count": round(count, 2)}
