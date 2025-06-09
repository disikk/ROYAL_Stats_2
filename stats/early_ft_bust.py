# -*- coding: utf-8 -*-
"""
Плагин для подсчёта количества вылетов Hero на ранней стадии финального стола
и среднего их числа на турнир с финалкой.
"""
from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats
from services import app_config


class EarlyFTBustStat(BaseStat):
    """Статистика вылетов в ранней стадии финального стола."""

    name: str = "Early FT Busts"
    
    @property
    def description(self) -> str:
        return (
            f"Количество вылетов Hero на ранней стадии финального стола ({app_config.early_ft_min_players}-"
            f"{app_config.final_table_size} место)"
        )

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[Any],
        sessions: List[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Рассчитывает количество вылетов и среднее число таких вылетов."""
        overall_stats = kwargs.get('overall_stats')
        
        if not tournaments and not overall_stats:
            return {"early_ft_bust_count": 0, "early_ft_bust_per_tournament": 0.0}

        if overall_stats and hasattr(overall_stats, "early_ft_bust_count") and hasattr(
            overall_stats, "early_ft_bust_per_tournament"
        ):
            bust_count = overall_stats.early_ft_bust_count
            bust_per_tournament = overall_stats.early_ft_bust_per_tournament
        else:
            ft_tournaments = [t for t in tournaments if t.reached_final_table]
            bust_count = sum(
                1
                for t in ft_tournaments
                if (
                    t.finish_place is not None
                    and app_config.early_ft_min_players <= t.finish_place <= app_config.final_table_size
                )
            )
            total_final_tables = len(ft_tournaments)
            bust_per_tournament = (
                bust_count / total_final_tables if total_final_tables > 0 else 0.0
            )

        return {
            "early_ft_bust_count": bust_count,
            "early_ft_bust_per_tournament": round(bust_per_tournament, 2),
        }
