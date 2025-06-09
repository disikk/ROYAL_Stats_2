# -*- coding: utf-8 -*-
"""
Плагин для расчёта ROI с поправкой на KO Luck.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import OverallStats, Tournament
from .ko_luck import KOLuckStat


class ROIAdjustedStat(BaseStat):
    """Возвращает ROI с учётом удачи в нокаутах."""

    name = "ROI Adjusted"
    description = "ROI с поправкой на KO Luck"

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[Any],
        sessions: List[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Возвращает ROI, скорректированный на KO Luck."""
        overall_stats = kwargs.get('overall_stats')
        
        if not tournaments and not overall_stats:
            return {"roi_adj": 0.0}

        total_buyin = 0.0
        total_payout = 0.0
        if overall_stats and hasattr(overall_stats, "total_buy_in") and hasattr(overall_stats, "total_prize"):
            total_buyin = overall_stats.total_buy_in
            total_payout = overall_stats.total_prize
        else:
            for t in tournaments:
                if t.buyin:
                    total_buyin += t.buyin
                if t.payout:
                    total_payout += t.payout

        profit = total_payout - total_buyin

        ko_luck = KOLuckStat().compute(tournaments, final_table_hands, sessions, overall_stats).get("ko_luck", 0.0)

        if total_buyin == 0:
            roi_adj = 0.0
        else:
            roi_adj = ((profit - ko_luck) / total_buyin) * 100.0

        roi_adj = round(roi_adj, 2)
        return {"roi_adj": roi_adj}
