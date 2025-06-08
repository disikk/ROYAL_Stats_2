# -*- coding: utf-8 -*-

"""
Плагин для подсчёта общего количества нокаутов, совершённых Hero.
Автономный плагин для работы с сырыми данными.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class TotalKOStat(BaseStat):
    name = "Total KO"
    description = "Общее количество сделанных Hero нокаутов"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Подсчитывает общее количество нокаутов Hero.

        Args:
            tournaments: Список турниров (не используется напрямую)
            final_table_hands: Список рук финального стола с информацией о KO
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - precomputed_stats: Dict с предварительно рассчитанным total_knockouts

        Returns:
            Словарь с ключом 'total_ko' - общее количество нокаутов
        """
        # Проверяем наличие предварительно рассчитанного значения
        final_table_hands = final_table_hands or []
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        if 'total_knockouts' in precomputed_stats:
            # Используем предварительно рассчитанное значение
            total_ko = precomputed_stats['total_knockouts']
        else:
            # Рассчитываем из сырых данных
            # Суммируем все KO из рук финального стола
            total_ko = sum(hand.hero_ko_this_hand for hand in final_table_hands)
        
        return {"total_ko": total_ko}