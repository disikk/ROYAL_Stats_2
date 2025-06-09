# -*- coding: utf-8 -*-

"""
ROI-плагин для Hero.
Автономный плагин для расчета Return On Investment.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class ROIStat(BaseStat):
    name = "ROI"
    description = "Return On Investment (ROI) — средний возврат на вложенный бай-ин для Hero"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает ROI на основе общих бай-инов и выплат.

        Args:
            tournaments: Список турниров для расчета
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - precomputed_stats: Dict с предварительно рассчитанными total_buy_in и total_prize

        Returns:
            Словарь с ключом 'roi' - процент возврата инвестиций
        """
        # Проверяем наличие предварительно рассчитанных значений для оптимизации
        tournaments = tournaments or []
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        if 'total_buy_in' in precomputed_stats and 'total_prize' in precomputed_stats:
            # Используем предварительно рассчитанные значения
            total_buyin = precomputed_stats['total_buy_in']
            total_payout = precomputed_stats['total_prize']
        else:
            # Рассчитываем из сырых данных
            total_buyin = sum(t.buyin for t in tournaments if t.buyin is not None)
            total_payout = sum(t.payout if t.payout is not None else 0 for t in tournaments)

        profit = total_payout - total_buyin

        if total_buyin == 0:
            roi = 0.0
        else:
            roi = (profit / total_buyin) * 100.0

        # Округляем до двух знаков после запятой
        roi = round(roi, 2)

        return {"roi": roi}