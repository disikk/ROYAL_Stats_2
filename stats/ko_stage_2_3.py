# -*- coding: utf-8 -*-

"""
Плагин для подсчета нокаутов в стадии 2-3 человека (хедз-ап и 3-макс).
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class KOStage23Stat(BaseStat):
    name = "KO Stage 2-3"
    description = "Количество нокаутов в стадии 2-3 человека"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Подсчитывает количество нокаутов Hero в стадии 2-3 человека.

        Args:
            tournaments: Список турниров (не используется)
            final_table_hands: Список рук финального стола с информацией о KO
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с ключами:
            - 'ko_stage_2_3': количество KO в стадии 2-3 человека
            - 'ko_stage_2_3_amount': сумма KO в стадии 2-3 человека
        """
        final_table_hands = final_table_hands or []
        
        # Фильтруем руки по количеству игроков (2-3)
        stage_2_3_hands = [
            hand for hand in final_table_hands 
            if hand.players_count >= 2 and hand.players_count <= 3
        ]
        
        # Подсчитываем KO. В hero_ko_this_hand может быть дробное
        # значение, если награда разделена между несколькими игроками.
        ko_total = sum(hand.hero_ko_this_hand for hand in stage_2_3_hands)

        return {
            "ko_stage_2_3": round(ko_total, 2),
            "ko_stage_2_3_amount": round(ko_total, 2)
        }
