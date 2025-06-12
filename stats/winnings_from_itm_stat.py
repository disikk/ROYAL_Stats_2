# -*- coding: utf-8 -*-

"""
Плагин для расчета стата "Выигрыш от ITM".
Считает суммы, полученные от попадания в регулярные призы (с 1 по 3 места).
За 1 место дается 4 бай-ина, за 2 - 3, за 3 - 2.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class WinningsFromITMStat(BaseStat):
    name = "Выигрыш от ITM"
    description = "Сумма, полученная от попадания в регулярные призы (1-3 места)"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает общую сумму, полученную от попадания в призы на 1-3 местах.
        1 место = 4 бай-ина
        2 место = 3 бай-ина
        3 место = 2 бай-ина

        Args:
            tournaments: Список турниров для расчета
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            overall_stats: Общая статистика (не используется)
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с ключами:
            - 'winnings_from_itm': общая сумма выигрыша от ITM
            - 'value': то же значение для обратной совместимости
        """
        tournaments = tournaments or []
        total_itm_winnings = 0.0

        for t in tournaments:
            if t.finish_place is None or t.buyin is None or t.buyin <= 0:
                continue

            if t.finish_place == 1:
                total_itm_winnings += 4 * t.buyin
            elif t.finish_place == 2:
                total_itm_winnings += 3 * t.buyin
            elif t.finish_place == 3:
                total_itm_winnings += 2 * t.buyin

        total_itm_winnings = round(total_itm_winnings, 2)

        # Возвращаем значение под ожидаемым ключом, сохраняя "value" для совместимости
        return {
            "winnings_from_itm": total_itm_winnings,
            "value": total_itm_winnings
        }
