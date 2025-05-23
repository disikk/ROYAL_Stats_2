# -*- coding: utf-8 -*-

"""
Плагин для подсчёта среднего количества нокаутов Hero за турнир.
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import Tournament # Импортируем модель Tournament

class AvgKOPerTournamentStat(BaseStat):
    """
    Считает среднее количество KO Hero за каждый сыгранный турнир.
    """
    name: str = "Avg KO / Tournament"
    description: str = "Среднее количество нокаутов Hero за турнир"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[Any], # Не используется напрямую этим плагином
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: Any, # Используем overall_stats для получения общих сумм
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает среднее количество KO за турнир.

        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключом 'avg_ko_per_tournament'.
        """
        if not tournaments and not overall_stats:
            return {"avg_ko_per_tournament": 0.0}

        # Этот стат уже рассчитывается и хранится в OverallStats
        # Плагин просто извлекает его. Это демонстрирует, как плагины
        # могут использовать уже посчитанные агрегаты.

        # Если overall_stats не передан или нет нужного поля, рассчитываем сами
        if overall_stats and hasattr(overall_stats, 'avg_ko_per_tournament'):
            avg_ko = overall_stats.avg_ko_per_tournament
        else:
            # Fallback расчет, если нет OverallStats или поля
            total_ko = sum(t.ko_count for t in tournaments if t.ko_count is not None)
            total_tournaments = len(tournaments)
            avg_ko = total_ko / total_tournaments if total_tournaments > 0 else 0.0
            avg_ko = round(avg_ko, 2) # Округляем

        return {"avg_ko_per_tournament": avg_ko}