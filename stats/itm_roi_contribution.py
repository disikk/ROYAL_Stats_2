# -*- coding: utf-8 -*-

"""
Плагин для расчета вклада ITM (призовых за 1-2-3 места) в общий ROI.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class ITMRoiContributionStat(BaseStat):
    name = "ITM ROI Contribution"
    description = "Вклад призовых за места 1-3 в общий ROI (%)"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает процентный вклад призовых за места 1-3 в общий ROI.

        Args:
            tournaments: Список турниров для расчета
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с ключами:
            - 'itm_roi_contribution': процент вклада ITM 1-3 в общий ROI
            - 'itm_profit': прибыль от мест 1-3
            - 'total_profit': общая прибыль
            - 'place_1_count': количество первых мест
            - 'place_2_count': количество вторых мест
            - 'place_3_count': количество третьих мест
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

        # Фильтруем турниры с местами 1-3
        itm_tournaments = [t for t in tournaments if t.finish_place and 1 <= t.finish_place <= 3]
        
        # Считаем количество мест
        place_1_count = sum(1 for t in itm_tournaments if t.finish_place == 1)
        place_2_count = sum(1 for t in itm_tournaments if t.finish_place == 2)
        place_3_count = sum(1 for t in itm_tournaments if t.finish_place == 3)
        
        # Считаем выплаты за места 1-3
        itm_payouts = sum(t.payout if t.payout is not None else 0 for t in itm_tournaments)
        
        # Считаем бай-ины для ITM турниров
        itm_buyins = sum(t.buyin for t in itm_tournaments if t.buyin is not None)
        
        # Прибыль от ITM
        itm_profit = itm_payouts - itm_buyins
        
        # Общая прибыль
        total_profit = total_payout - total_buyin

        # Вклад ITM в процентах
        if total_profit > 0:
            itm_contribution_percent = (itm_profit / total_profit) * 100.0
        else:
            itm_contribution_percent = 0.0

        # Округляем результаты
        itm_contribution_percent = round(itm_contribution_percent, 2)
        itm_profit = round(itm_profit, 2)
        total_profit = round(total_profit, 2)

        return {
            "itm_roi_contribution": itm_contribution_percent,
            "itm_profit": itm_profit,
            "total_profit": total_profit,
            "place_1_count": place_1_count,
            "place_2_count": place_2_count,
            "place_3_count": place_3_count
        }