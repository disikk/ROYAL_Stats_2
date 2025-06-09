# -*- coding: utf-8 -*-

"""
Плагин для расчёта удачи/неудачи в нокаутах.
Показывает отклонение полученных денег от нокаутов относительно среднего.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session
import logging

logger = logging.getLogger(__name__)

class KOLuckStat(BaseStat):
    name = "KO Luck"
    description = "Отклонение полученных денег от нокаутов относительно среднего значения"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает отклонение в деньгах от нокаутов.
        
        Формула: сумма моих нокаутов ($) – количество_нокаутов * средний нокаут ($)
        
        Args:
            tournaments: Список турниров
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - buyin_avg_ko_map: Dict[float, float] - словарь средних значений KO по бай-инам
            
        Returns:
            Словарь с ключом 'ko_luck' - отклонение в долларах
        """
        tournaments = tournaments or []
        if not tournaments:
            return {"ko_luck": 0.0}
            
        # Получаем словарь средних значений KO из kwargs или используем дефолтный
        buyin_avg_ko_map = kwargs.get('buyin_avg_ko_map', {
            0.25: 0.23,
            1.0: 0.93,
            3.0: 2.79,
            10.0: 9.28,
            25.0: 23.18,
        })
            
        # Словарь для регулярных выплат по местам (в байинах)
        # Это типичные выплаты для Battle Royale турниров
        regular_payouts = {
            1: 4.0,     # 1 место = 4 байина
            2: 3.0,     # 2 место = 3 байина
            3: 2.0,     # 3 место = 2 байина
        }
        
        total_ko_earnings = 0.0  # Общая сумма денег от нокаутов
        total_expected_ko_value = 0.0  # Ожидаемая сумма денег от нокаутов
        
        for tournament in tournaments:
            # Пропускаем турниры без выплат или байинов
            if not tournament.payout or not tournament.buyin:
                continue
                
            # Рассчитываем регулярную выплату за место
            regular_payout = 0.0
            if tournament.finish_place in regular_payouts:
                regular_payout = regular_payouts[tournament.finish_place] * tournament.buyin
                
            # Остаток от выплаты - это деньги от нокаутов
            ko_earning = tournament.payout - regular_payout
            total_ko_earnings += ko_earning
            
            # Логируем для турниров с необычными значениями
            if ko_earning > tournament.buyin * 5:  # Если выплата от KO больше 5 байинов
                logger.debug(f"Турнир {tournament.tournament_id}: место={tournament.finish_place}, "
                           f"buyin={tournament.buyin}, payout={tournament.payout}, "
                           f"regular_payout={regular_payout}, ko_earning={ko_earning}, "
                           f"ko_count={tournament.ko_count}")
            
            # Рассчитываем ожидаемую сумму от нокаутов
            if tournament.buyin in buyin_avg_ko_map and tournament.ko_count > 0:
                avg_ko_value = buyin_avg_ko_map[tournament.buyin]
                expected_value = tournament.ko_count * avg_ko_value
                total_expected_ko_value += expected_value
                
        # Отклонение = фактические деньги от нокаутов - ожидаемые деньги от нокаутов
        ko_luck = total_ko_earnings - total_expected_ko_value
        
        # Логируем для отладки
        logger.debug(f"KO Luck расчет: total_ko_earnings={total_ko_earnings:.2f}, "
                    f"total_expected_ko_value={total_expected_ko_value:.2f}, "
                    f"ko_luck={ko_luck:.2f}")
        
        # Округляем до двух знаков после запятой
        ko_luck = round(ko_luck, 2)
        
        return {"ko_luck": ko_luck}