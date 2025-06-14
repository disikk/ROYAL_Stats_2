# -*- coding: utf-8 -*-

"""
Плагин для подсчета нокаутов в стадии 4-5 человек.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class KOStage45Stat(BaseStat):
    name = "KO Stage 4-5"
    description = "Количество нокаутов в стадии 4-5 человек"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Подсчитывает количество нокаутов Hero в стадии 4-5 человек.

        Args:
            tournaments: Список турниров (не используется)
            final_table_hands: Список рук финального стола с информацией о KO
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с ключами:
            - 'ko_stage_4_5': количество KO в стадии 4-5 человек
            - 'ko_stage_4_5_amount': сумма KO в стадии 4-5 человек
            - 'ko_stage_4_5_attempts_per_tournament': среднее число попыток
              нокаутов в турнирах с финальным столом
        """
        final_table_hands = final_table_hands or []
        
        # Фильтруем руки по количеству игроков (4-5)
        stage_4_5_hands = [
            hand for hand in final_table_hands 
            if hand.players_count >= 4 and hand.players_count <= 5
        ]
        
        # Подсчитываем KO и количество попыток
        ko_total = sum(hand.hero_ko_this_hand for hand in stage_4_5_hands)
        attempts_total = sum(hand.hero_ko_attempts for hand in stage_4_5_hands)

        ft_ids = {hand.tournament_id for hand in final_table_hands}
        ft_count = len(ft_ids)
        avg_attempts = attempts_total / ft_count if ft_count else 0.0

        return {
            "ko_stage_4_5": round(ko_total, 2),
            "ko_stage_4_5_amount": round(ko_total, 2),
            "ko_stage_4_5_attempts_per_tournament": round(avg_attempts, 2),
        }
