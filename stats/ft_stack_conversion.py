# -*- coding: utf-8 -*-
"""Статистика эффективности конверсии стека в ранние KO на финальном столе."""

from typing import Dict, Any, List
from statistics import median

from .base import BaseStat
from models import Tournament, OverallStats
import config


class FTStackConversionStat(BaseStat):
    """Примерная оценка конверсии стартового стека в ранние KO."""

    name: str = "FT Stack Conversion"
    description: str = (
        "Отношение фактических ранних KO к ожидаемым,\n"
        "рассчитанным из медианного стека на FT"
    )

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[Any],
        sessions: List[Any],
        overall_stats: OverallStats,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not tournaments and not overall_stats:
            return {"ft_stack_conversion": 0.0}

        if overall_stats and hasattr(overall_stats, "early_ft_ko_per_tournament"):
            early_ko_per_tournament = overall_stats.early_ft_ko_per_tournament
        else:
            ft_tours = [t for t in tournaments if t.reached_final_table]
            early_ko_count = sum(
                h.hero_ko_this_hand for h in final_table_hands if h.is_early_final
            )
            count = len(ft_tours)
            early_ko_per_tournament = early_ko_count / count if count else 0.0

        stacks = [
            t.final_table_initial_stack_bb
            for t in tournaments
            if t.reached_final_table and t.final_table_initial_stack_bb is not None
        ]
        if not stacks:
            return {"ft_stack_conversion": 0.0}

        median_stack = median(stacks)
        avg_stack = sum(stacks) / len(stacks)
        expected_ko = (median_stack / avg_stack) * (config.FINAL_TABLE_SIZE - 1)
        efficiency = (
            early_ko_per_tournament / expected_ko if expected_ko > 0 else 0.0
        )

        return {"ft_stack_conversion": round(efficiency, 2)}

