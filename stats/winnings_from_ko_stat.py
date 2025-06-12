# -*- coding: utf-8 -*-

"""
Плагин для расчета стата "Выигрыш от KO".
Считает сумму, полученную от нокаутов.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class WinningsFromKOStat(BaseStat):
    name = "Выигрыш от KO"
    description = "Сумма, полученная от нокаутов"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает общую сумму, полученную от нокаутов.

        Args:
            tournaments: Список турниров для расчета
            final_table_hands: Список рук финального стола
            sessions: Список сессий (не используется)
            overall_stats: Общая статистика (не используется)
            **kwargs: Дополнительные параметры, включая precomputed_stats

        Returns:
            Словарь с ключами:
            - 'winnings_from_ko': общая сумма выигрыша от KO
            - 'value': то же значение для обратной совместимости
            - 'total_ko_amount': общая сумма выигрыша от KO
        """
        precomputed_stats = kwargs.get('precomputed_stats', {})

        if 'total_knockouts_amount' in precomputed_stats:
            total_ko_amount = precomputed_stats['total_knockouts_amount']
        elif final_table_hands is not None:
            # Рассчитываем из рук финального стола, если precomputed_stats нет, но есть руки
            total_ko_amount = sum(hand.hero_ko_this_hand for hand in final_table_hands if hand.hero_ko_this_hand is not None)
        elif overall_stats and hasattr(overall_stats, 'total_knockouts'):
            # В крайнем случае, если есть overall_stats с полем total_knockouts (предполагая, что это сумма)
            # Это менее предпочтительный вариант, так как total_knockouts может быть просто количеством.
            # Исходя из KORoiContributionStat, total_knockouts_amount это денежная сумма.
            # В OverallStats total_knockouts это float, что может быть суммой.
            # Если overall_stats.total_knockouts это КОЛИЧЕСТВО, а не СУММА, эту ветку нужно убрать или изменить.
            # Судя по KORoiContributionStat, нам нужна именно сумма.
            # В models/overall_stats.py -> total_knockouts: float = 0.0. Похоже на сумму.
            # В services/statistics_service.py -> stats.total_knockouts = sum(hand.hero_ko_this_hand for hand in all_ft_hands)
            # Да, это сумма.
            total_ko_amount = overall_stats.total_knockouts
        else:
            # Если ни один из источников недоступен, но есть турниры,
            # можно попробовать посчитать через ko_count в турнирах, если он означает сумму.
            # В db/schema.py: tournaments.ko_count REAL DEFAULT 0. Похоже на сумму.
            # В services/statistics_service.py -> total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands); tournament.ko_count = total_ko. Да, это сумма.
            if tournaments is not None:
                total_ko_amount = sum(t.ko_count for t in tournaments if t.ko_count is not None)
            else:
                total_ko_amount = 0.0


        total_ko_amount = round(total_ko_amount, 2)

        # Возвращаем сумму под ключом, который ожидает ViewModel.
        # Также оставляем старый ключ "value" для возможной совместимости
        return {
            "winnings_from_ko": total_ko_amount,
            "value": total_ko_amount,
            "total_ko_amount": total_ko_amount
        }
