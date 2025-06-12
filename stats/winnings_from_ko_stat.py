# -*- coding: utf-8 -*-

"""
Плагин для расчёта стата "Выигрыш от KO".

Ранее размер выигрыша от нокаутов вычислялся как произведение
количества KO на усреднённое значение из ``config.ini``. Такой
подход давал заметную погрешность.

Теперь сумма выигрыша от KO определяется как разница между общей
выплатой за турнир и призом за ITM (если он был). Так мы получаем
суммарную стоимость всех нокаутов в каждом турнире.
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
            tournaments: Список турниров для расчёта
            final_table_hands: Не используется
            sessions: Не используется
            overall_stats: Не используется
            **kwargs: Дополнительные параметры (не используются)

        Returns:
            Словарь с ключами:
            - ``winnings_from_ko``: сумма выигрыша от KO
            - ``value``: то же значение (для обратной совместимости)
            - ``total_ko_amount``: сумма выигрыша от KO
        """

        tournaments = tournaments or []

        total_ko_amount = 0.0
        for t in tournaments:
            if t.payout is None or t.payout <= 0:
                continue

            itm_payout = 0.0
            if t.finish_place == 1:
                itm_payout = 4 * t.buyin
            elif t.finish_place == 2:
                itm_payout = 3 * t.buyin
            elif t.finish_place == 3:
                itm_payout = 2 * t.buyin

            ko_amount = t.payout - itm_payout
            total_ko_amount += ko_amount

        total_ko_amount = round(total_ko_amount, 2)

        return {
            "winnings_from_ko": total_ko_amount,
            "value": total_ko_amount,
            "total_ko_amount": total_ko_amount,
        }
