# -*- coding: utf-8 -*-
"""
Плагин для расчета вклада нокаутов в общие выплаты.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament
from services.app_config import app_config


class KOContributionStat(BaseStat):
    """Возвращает долю выплат, полученных за нокауты."""

    name = "KO Contribution"
    description = "Доля выплат за нокауты (факт / adj)"

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[Any],
        sessions: List[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Возвращает фактический и скорректированный вклад нокаутов."""
        overall_stats = kwargs.get('overall_stats')
        
        if not tournaments:
            return {"ko_contribution": 0.0, "ko_contribution_adj": 0.0}

        regular = {1: 4.0, 2: 3.0, 3: 2.0}
        total_payout = 0.0
        regular_sum = 0.0
        expected_ko = 0.0

        for t in tournaments:
            payout = t.payout or 0.0
            buyin = t.buyin or 0.0
            total_payout += payout
            if t.finish_place in regular:
                regular_sum += regular[t.finish_place] * buyin
            if buyin in app_config.buyin_avg_ko_map and t.ko_count > 0:
                expected_ko += t.ko_count * app_config.buyin_avg_ko_map[buyin]

        ko_payout = total_payout - regular_sum
        actual = (ko_payout / total_payout * 100.0) if total_payout > 0 else 0.0
        denom = expected_ko + regular_sum
        adj = (expected_ko / denom * 100.0) if denom > 0 else 0.0

        return {
            "ko_contribution": round(actual, 2),
            "ko_contribution_adj": round(adj, 2),
        }
