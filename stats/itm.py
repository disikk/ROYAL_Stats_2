# -*- coding: utf-8 -*-

"""
ITM-плагин для Hero (In The Money — попадание в топ-3).
Обновлен для работы с новой архитектурой и моделями.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament, OverallStats # Импортируем модели

class ITMStat(BaseStat):
    name = "ITM"
    description = "ITM% — процент попадания Hero в топ-3 (призовые места)"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: Any, # Используем overall_stats для получения общих сумм
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает ITM%.

        Args:
            tournaments: Список объектов Tournament (используется только в fallback).
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'itm_percent'.
        """
        # ITM% основан на общем количестве турниров и финишах в топ-3.
        # Хотя общие суммы есть в OverallStats, ITM% не хранится напрямую.
        # Рассчитаем его здесь, используя OverallStats для общих чисел.

        if overall_stats:
             total = overall_stats.total_tournaments
             # Чтобы посчитать itm_count из OverallStats, нам нужно знать
             # количество 1х, 2х, 3х мест. Этого поля пока нет в OverallStats.
             # **Решение:** Добавим first_places, second_places, third_places в OverallStats.
             # И будем считать itm_count = sum(1х, 2х, 3х).
             # Временно, если нет этих полей, рассчитаем itm_count из списка турниров.
             if hasattr(overall_stats, 'first_places') and hasattr(overall_stats, 'second_places') and hasattr(overall_stats, 'third_places'):
                  itm_count = overall_stats.first_places + overall_stats.second_places + overall_stats.third_places
             else:
                  itm_count = sum(1 for t in tournaments if t.finish_place in (1, 2, 3))
        else:
             # Fallback расчет
             total = len(tournaments)
             itm_count = sum(1 for t in tournaments if t.finish_place in (1, 2, 3))

        itm_percent = (itm_count / total * 100) if total > 0 else 0.0
        itm_percent = round(itm_percent, 2)

        return {"itm_percent": itm_percent}