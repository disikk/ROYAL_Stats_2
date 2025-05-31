# -*- coding: utf-8 -*-

"""
Плагин для расчёта удачи/неудачи в нокаутах.
Показывает отклонение полученных денег от нокаутов относительно среднего.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats
from config import BUYIN_AVG_KO_MAP

class KOLuckStat(BaseStat):
    name = "KO Luck"
    description = "Отклонение полученных денег от нокаутов относительно среднего значения"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any],  # Не используется этим плагином
                sessions: List[Any],  # Не используется этим плагином
                overall_stats: OverallStats,  # Не используется этим плагином
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает отклонение в деньгах от нокаутов.
        
        Формула: сумма моих нокаутов ($) – количество_нокаутов * средний нокаут ($)
        
        Args:
            tournaments: Список турниров
            **kwargs: Дополнительные параметры
            
        Returns:
            Словарь с ключом 'ko_luck' - отклонение в долларах
        """
        if not tournaments:
            return {"ko_luck": 0.0}
            
        # Словарь для регулярных выплат по местам
        regular_payouts = {
            1: 4.0,  # 1 место = 4 байина
            2: 3.0,  # 2 место = 3 байина
            3: 2.0,  # 3 место = 2 байина
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
            
            # Рассчитываем ожидаемую сумму от нокаутов
            if tournament.buyin in BUYIN_AVG_KO_MAP and tournament.ko_count > 0:
                avg_ko_value = BUYIN_AVG_KO_MAP[tournament.buyin]
                expected_value = tournament.ko_count * avg_ko_value
                total_expected_ko_value += expected_value
                
        # Отклонение = фактические деньги от нокаутов - ожидаемые деньги от нокаутов
        ko_luck = total_ko_earnings - total_expected_ko_value
        
        # Округляем до двух знаков после запятой
        ko_luck = round(ko_luck, 2)
        
        return {"ko_luck": ko_luck}