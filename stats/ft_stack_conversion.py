# -*- coding: utf-8 -*-
"""Статистика эффективности конверсии стека в ранние KO на финальном столе."""

from typing import Dict, Any, List
from statistics import median

from .base import BaseStat
from models import Tournament, OverallStats
from services.app_config import app_config


class FTStackConversionStat(BaseStat):
    """Эффективность конверсии стека в ранние KO на финальном столе."""

    name: str = "FT Stack Conversion"
    description: str = (
        "Эффективность превращения стека в нокауты на ранней стадии FT (9-6 игроков).\n"
        "Показывает, насколько хорошо вы реализуете свой стек для выбивания соперников.\n"
        "\n"
        "Расчет: Фактические KO / Ожидаемые KO (исходя из доли вашего стека)\n"
        "\n"
        "Интерпретация:\n"
        "• >1.0 - вы выбиваете больше, чем предполагает ваш стек (хорошо)\n"
        "• =1.0 - вы выбиваете ровно столько, сколько ожидается\n"
        "• <1.0 - вы выбиваете меньше ожидаемого (стек используется неэффективно)\n"
        "\n"
        "Пример: при значении 1.25 вы выбиваете на 25% больше соперников,\n"
        "чем в среднем выбил бы игрок с вашим стеком"
    )

    def compute(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[Any],
        sessions: List[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        overall_stats = kwargs.get('overall_stats')
        
        if not tournaments and not overall_stats:
            return {"ft_stack_conversion": 0.0}

        # Для конверсии стека учитываем только KO, сделанные непосредственно на
        # ранней стадии финального стола. KO из предпоследней 5-max раздачи
        # (pre_ft_ko) исключаем из подсчёта, т.к. они искажают показатель.

        ft_tours = [t for t in tournaments if t.reached_final_table]

        if final_table_hands:
            early_ko_count = sum(
                h.hero_ko_this_hand
                for h in final_table_hands
                if h.is_early_final
            )
            pre_ft_total = sum(h.pre_ft_ko for h in final_table_hands)
            early_ko_count -= pre_ft_total
        elif overall_stats and hasattr(overall_stats, "early_ft_ko_count"):
            # Фоллбэк на агрегированные данные, если список рук не передан
            pre_ft_ko = getattr(overall_stats, "pre_ft_ko_count", 0.0)
            early_ko_count = overall_stats.early_ft_ko_count - pre_ft_ko
        else:
            early_ko_count = 0.0

        count = len(ft_tours)
        if not count and overall_stats and hasattr(overall_stats, "total_final_tables"):
            count = overall_stats.total_final_tables

        early_ko_per_tournament = early_ko_count / count if count else 0.0

        # Собираем данные для турниров, где Hero достиг финального стола
        ft_data = []
        for t in tournaments:
            if (t.reached_final_table and 
                t.final_table_initial_stack_chips is not None and
                t.final_table_start_players is not None):
                ft_data.append({
                    'stack_chips': t.final_table_initial_stack_chips,
                    'start_players': t.final_table_start_players
                })
        
        if not ft_data:
            return {"ft_stack_conversion": 0.0}

        # Рассчитываем медианный стек в фишках
        median_stack_chips = median([d['stack_chips'] for d in ft_data])
        
        # Общее количество фишек на финальном столе всегда равно 18000
        total_chips_at_ft = 18000
        
        # Доля стека игрока от общего количества фишек
        stack_share = median_stack_chips / total_chips_at_ft
        
        # Рассчитываем среднее количество возможных KO в ранней фазе
        # для каждого турнира и берем среднее
        possible_early_ko_per_tournament = []
        for d in ft_data:
            # Ранняя фаза заканчивается при 5 игроках
            early_phase_knockouts = max(0, d['start_players'] - 5)
            possible_early_ko_per_tournament.append(early_phase_knockouts)
        
        avg_possible_early_ko = sum(possible_early_ko_per_tournament) / len(possible_early_ko_per_tournament)
        
        # Ожидаемое число ранних KO пропорционально доле стека
        expected_ko = stack_share * avg_possible_early_ko
        
        efficiency = (
            early_ko_per_tournament / expected_ko if expected_ko > 0 else 0.0
        )

        return {"ft_stack_conversion": round(efficiency, 2)}

