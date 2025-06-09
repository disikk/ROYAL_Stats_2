# -*- coding: utf-8 -*-
"""Статистика эффективности конверсии стека с учетом попыток выбить соперников."""

from typing import Dict, Any, List
from statistics import median

from .base import BaseStat
from models import Tournament, OverallStats, FinalTableHand
from services.app_config import app_config


class FTStackConversionAttemptsStat(BaseStat):
    """Эффективность конверсии стека в ранние KO с учетом попыток."""

    name: str = "FT Stack Conversion (Attempts Adjusted)"
    description: str = (
        "Эффективность превращения стека в нокауты с учетом попыток выбить соперников.\n"
        "Учитывает не только результат, но и количество попыток.\n"
        "\n"
        "Расчет: (Фактические KO / Ожидаемые KO) × (Средние попытки / Фактические попытки)\n"
        "\n"
        "Интерпретация:\n"
        "• >1.0 - вы эффективно конвертируете попытки в нокауты\n"
        "• =1.0 - средняя эффективность\n"
        "• <1.0 - низкая эффективность конверсии попыток\n"
        "\n"
        "Этот показатель учитывает везение: если вы делаете много попыток,\n"
        "но выбиваете мало - это может быть невезение, а не плохая игра"
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
            return {
                "ft_stack_conversion_attempts": 0.0,
                "avg_ko_attempts_per_ft": 0.0,
                "ko_attempts_success_rate": 0.0
            }

        # Считаем early KO без pre_ft_ko
        ft_tours = [t for t in tournaments if t.reached_final_table]
        
        # Фильтруем руки ранней FT фазы
        early_ft_hands = [h for h in final_table_hands if h.is_early_final]
        
        # Считаем KO и попытки
        early_ko_count = sum(
            h.hero_ko_this_hand - h.pre_ft_ko for h in early_ft_hands
        )
        total_attempts = sum(h.hero_ko_attempts for h in early_ft_hands)
        
        count = len(ft_tours)
        early_ko_per_tournament = early_ko_count / count if count else 0.0
        attempts_per_tournament = total_attempts / count if count else 0.0

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
            return {
                "ft_stack_conversion_attempts": 0.0,
                "avg_ko_attempts_per_ft": 0.0,
                "ko_attempts_success_rate": 0.0
            }

        # Рассчитываем медианный стек в фишках
        median_stack_chips = median([d['stack_chips'] for d in ft_data])
        
        # Общее количество фишек на финальном столе всегда равно 18000
        total_chips_at_ft = 18000
        
        # Доля стека игрока от общего количества фишек
        stack_share = median_stack_chips / total_chips_at_ft
        
        # Рассчитываем среднее количество возможных KO в ранней фазе
        possible_early_ko_per_tournament = []
        for d in ft_data:
            # Ранняя фаза заканчивается при 5 игроках
            early_phase_knockouts = max(0, d['start_players'] - 5)
            possible_early_ko_per_tournament.append(early_phase_knockouts)
        
        avg_possible_early_ko = sum(possible_early_ko_per_tournament) / len(possible_early_ko_per_tournament)
        
        # Ожидаемое число ранних KO пропорционально доле стека
        expected_ko = stack_share * avg_possible_early_ko
        
        # Базовая эффективность (как в основном стате)
        base_efficiency = (
            early_ko_per_tournament / expected_ko if expected_ko > 0 else 0.0
        )
        
        # Корректировка на попытки
        # Предполагаем, что в среднем для одного KO нужно 2-3 попытки
        avg_attempts_per_ko = 2.5
        expected_attempts = expected_ko * avg_attempts_per_ko
        
        # Фактор корректировки на попытки
        # Если делаем больше попыток чем ожидается - эффективность снижается
        # Если делаем меньше попыток - эффективность повышается
        attempts_factor = (
            expected_attempts / attempts_per_tournament 
            if attempts_per_tournament > 0 else 1.0
        )
        
        # Финальная эффективность с учетом попыток
        adjusted_efficiency = base_efficiency * attempts_factor
        
        # Процент успешных попыток
        success_rate = (
            (early_ko_count / total_attempts * 100) 
            if total_attempts > 0 else 0.0
        )

        return {
            "ft_stack_conversion_attempts": round(adjusted_efficiency, 2),
            "avg_ko_attempts_per_ft": round(attempts_per_tournament, 2),
            "ko_attempts_success_rate": round(success_rate, 1)
        }