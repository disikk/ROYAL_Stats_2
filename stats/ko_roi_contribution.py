# -*- coding: utf-8 -*-

"""
Плагин для расчета вклада нокаутов в общий ROI.
Показывает, какую часть общего профита составляют нокауты.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class KORoiContributionStat(BaseStat):
    name = "KO ROI Contribution"
    description = "Вклад нокаутов в общий ROI (%)"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает процентный вклад нокаутов в общий ROI.

        Args:
            tournaments: Список турниров для расчета
            final_table_hands: Список рук финального стола
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с ключами:
            - 'ko_roi_contribution': процент вклада KO в общий ROI
            - 'ko_profit': прибыль от нокаутов
            - 'total_profit': общая прибыль
        """
        tournaments = tournaments or []
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        # Получаем общие значения
        if 'total_buy_in' in precomputed_stats and 'total_prize' in precomputed_stats:
            total_buyin = precomputed_stats['total_buy_in']
            total_payout = precomputed_stats['total_prize']
        else:
            total_buyin = sum(t.buyin for t in tournaments if t.buyin is not None)
            total_payout = sum(t.payout if t.payout is not None else 0 for t in tournaments)

        # Получаем общую сумму нокаутов
        if 'total_knockouts_amount' in precomputed_stats:
            total_ko_amount = precomputed_stats['total_knockouts_amount']
        else:
            # Рассчитываем из рук финального стола
            final_table_hands = final_table_hands or []
            total_ko_amount = sum(hand.hero_ko_this_hand for hand in final_table_hands)

        # Общая прибыль
        total_profit = total_payout - total_buyin

        # Вклад KO в процентах
        if total_profit > 0:
            ko_contribution_percent = (total_ko_amount / total_profit) * 100.0
        else:
            ko_contribution_percent = 0.0

        # Округляем результаты
        ko_contribution_percent = round(ko_contribution_percent, 2)
        total_ko_amount = round(total_ko_amount, 2)
        total_profit = round(total_profit, 2)

        return {
            "ko_roi_contribution": ko_contribution_percent,
            "ko_profit": total_ko_amount,
            "total_profit": total_profit
        }