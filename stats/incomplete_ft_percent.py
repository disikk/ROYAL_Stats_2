# -*- coding: utf-8 -*-
"""
Плагин для подсчёта процента финальных столов, начавшихся неполным составом.
"""

from typing import Dict, Any, List

import config
from .base import BaseStat
from models import Tournament, FinalTableHand, OverallStats


class IncompleteFTPercentStat(BaseStat):
    """Возвращает процент финалок, стартовавших неполным составом."""

    name: str = "Incomplete FT%"
    description: str = "Процент финалок с <9 игроками в первой раздаче"

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[FinalTableHand],
        sessions: List[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Возвращает процент неполных финальных столов."""
        overall_stats = kwargs.get('overall_stats')
        
        if overall_stats and hasattr(overall_stats, "incomplete_ft_percent"):
            percent = overall_stats.incomplete_ft_percent
            return {"incomplete_ft_percent": percent}

        # Fallback расчёт при отсутствии OverallStats
        if not final_table_hands:
            return {"incomplete_ft_percent": 0}

        first_hands: dict[str, FinalTableHand] = {}
        for hand in final_table_hands:
            if hand.table_size == config.FINAL_TABLE_SIZE:
                saved = first_hands.get(hand.tournament_id)
                if saved is None or hand.hand_number < saved.hand_number:
                    first_hands[hand.tournament_id] = hand

        total_ft = len(first_hands)
        incomplete_count = sum(
            1 for h in first_hands.values() if h.players_count < config.FINAL_TABLE_SIZE
        )
        percent = int(round(incomplete_count / total_ft * 100)) if total_ft > 0 else 0
        return {"incomplete_ft_percent": percent}
