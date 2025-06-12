# -*- coding: utf-8 -*-

"""
Плагин для подсчета нокаутов в стадии 6-9 человек (ранняя стадия финального стола).
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class KOStage69Stat(BaseStat):
    name = "KO Stage 6-9"
    description = "Количество нокаутов в стадии 6-9 человек"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Подсчитывает количество нокаутов Hero в стадии 6-9 человек.

        Args:
            tournaments: Список турниров (не используется)
            final_table_hands: Список рук финального стола с информацией о KO
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с ключами:
            - 'ko_stage_6_9': количество KO в стадии 6-9 человек
            - 'ko_stage_6_9_amount': сумма KO в стадии 6-9 человек
        """
        final_table_hands = final_table_hands or []
        
        # Фильтруем руки по количеству игроков (6-9)
        stage_6_9_hands = [
            hand for hand in final_table_hands 
            if hand.players_count >= 6 and hand.players_count <= 9
        ]
        
        # Подсчитываем KO
        ko_count = 0
        ko_amount = 0.0
        
        for hand in stage_6_9_hands:
            if hand.hero_ko_this_hand > 0:
                ko_count += 1
                ko_amount += hand.hero_ko_this_hand
        
        return {
            "ko_stage_6_9": ko_count,
            "ko_stage_6_9_amount": round(ko_amount, 2)
        }