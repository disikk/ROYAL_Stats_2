# -*- coding: utf-8 -*-
"""
Статистика глубокой стадии финального стола (5 игроков и меньше).
Возвращает частоту достижения этой стадии, средний стек и ROI.
"""
from typing import Dict, Any, List, Optional

from .base import BaseStat
from models import Tournament, FinalTableHand, Session


class DeepFTStat(BaseStat):
    """Статистика по стадии \u22645 игроков на финальном столе."""

    name = "Deep FT"
    description = (
        "Проходы в глубокую стадию финалки (\u22645 игроков), "
        "средний стек и ROI в таких турнирах"
    )

    def compute(
        self,
        tournaments: Optional[List[Tournament]] = None,
        final_table_hands: Optional[List[FinalTableHand]] = None,
        sessions: Optional[List[Session]] = None,
        overall_stats: Optional[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        tournaments = tournaments or []
        final_table_hands = final_table_hands or []

        # Сохраняем первую руку, где игроков 5 или меньше
        first_hands: dict[str, FinalTableHand] = {}
        for hand in final_table_hands:
            if hand.players_count <= 5:
                saved = first_hands.get(hand.tournament_id)
                if saved is None or hand.hand_number < saved.hand_number:
                    first_hands[hand.tournament_id] = hand

        reached_ids = set(first_hands.keys())

        if overall_stats and hasattr(overall_stats, "total_final_tables"):
            total_ft = overall_stats.total_final_tables
        else:
            total_ft = sum(1 for t in tournaments if t.reached_final_table)

        reach_percent = (len(reached_ids) / total_ft * 100) if total_ft else 0.0

        stacks_chips = [h.hero_stack for h in first_hands.values() if h.hero_stack is not None]
        avg_stack_chips = sum(stacks_chips) / len(stacks_chips) if stacks_chips else 0.0

        stacks_bb = [h.hero_stack / h.bb for h in first_hands.values() if h.hero_stack is not None and h.bb]
        avg_stack_bb = sum(stacks_bb) / len(stacks_bb) if stacks_bb else 0.0

        stage_tournaments = [t for t in tournaments if t.tournament_id in reached_ids]
        total_buyin = sum(t.buyin for t in stage_tournaments if t.buyin is not None)
        total_payout = sum(t.payout for t in stage_tournaments if t.payout is not None)
        roi = (total_payout - total_buyin) / total_buyin * 100 if total_buyin > 0 else 0.0

        return {
            "deep_ft_reach_percent": round(reach_percent, 2),
            "deep_ft_avg_stack_chips": round(avg_stack_chips, 2),
            "deep_ft_avg_stack_bb": round(avg_stack_bb, 2),
            "deep_ft_roi": round(roi, 2),
        }
