# -*- coding: utf-8 -*-

"""
Плагин для расчёта стата "Выигрыш от KO".
Использует количество нокаутов в турнирах и умножает его на
средний размер нокаута для соответствующего бай-ина.
Значения средних нокаутов берутся из ``config.ini``.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session
from services.app_config import app_config

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
            **kwargs: Дополнительные параметры. Можно передать ``buyin_avg_ko_map``
                для переопределения значений из конфигурации.

        Returns:
            Словарь с ключами:
            - ``winnings_from_ko``: сумма выигрыша от KO
            - ``value``: то же значение (для обратной совместимости)
            - ``total_ko_amount``: сумма выигрыша от KO
        """

        tournaments = tournaments or []
        buyin_avg_ko_map = kwargs.get('buyin_avg_ko_map', app_config.buyin_avg_ko_map)

        total_ko_amount = 0.0
        for t in tournaments:
            if t.buyin in buyin_avg_ko_map and t.ko_count:
                total_ko_amount += t.ko_count * buyin_avg_ko_map[t.buyin]

        total_ko_amount = round(total_ko_amount, 2)

        return {
            "winnings_from_ko": total_ko_amount,
            "value": total_ko_amount,
            "total_ko_amount": total_ko_amount,
        }
