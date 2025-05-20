# -*- coding: utf-8 -*-

"""
Плагин для подсчёта количества и среднего KO Hero в ранней стадии финального стола (9-6 игроков).
"""

from typing import Dict, Any, List
from .base import BaseStat
from models import FinalTableHand, OverallStats # Импортируем модели
import math # Для округления

class EarlyFTKOStat(BaseStat):
    """
    Считает общее количество KO и среднее KO за турнир (достигший финалки)
    в раздачах финального стола, где количество игроков было от 6 до 9 включительно.
    """
    name: str = "Early FT KO"
    description: str = "Статистика KO в ранней стадии финального стола (9-6 игроков)"

    def compute(self,
                tournaments: List[Any], # Не используется напрямую этим плагином
                final_table_hands: List[FinalTableHand], # Используем для фильтрации по стадии
                sessions: List[Any], # Не используется напрямую этим плагином
                overall_stats: Any, # Используем overall_stats для получения общих сумм
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает статистику KO в ранней стадии финального стола.

        Args:
            final_table_hands: Список объектов FinalTableHand.
            overall_stats: Объект OverallStats с уже посчитанными агрегатами.
            **kwargs: Дополнительные параметры.

        Returns:
            Словарь с ключами 'early_ft_ko_count' и 'early_ft_ko_per_tournament'.
        """
        # Эти статы уже рассчитываются и хранятся в OverallStats
        # Плагин просто извлекает их.

        if overall_stats and hasattr(overall_stats, 'early_ft_ko_count') and hasattr(overall_stats, 'early_ft_ko_per_tournament'):
            early_ft_ko_count = overall_stats.early_ft_ko_count
            early_ft_ko_per_tournament = overall_stats.early_ft_ko_per_tournament
        else:
            # Fallback расчет
            # Фильтруем руки, относящиеся к ранней стадии финалки
            early_hands = [hand for hand in final_table_hands if hand.is_early_final]
            early_ft_ko_count = sum(hand.hero_ko_this_hand for hand in early_hands)

            # Чтобы посчитать среднее на турнир, нужно знать, сколько турниров достигли финалки
            # В fallback режиме у нас нет доступа к полному списку турниров или OverallStats.
            # Это подчеркивает, почему расчеты лучше делать в ApplicationService.
            # Однако, для автономности плагина можно попробовать получить уникальные tournament_id
            # из early_hands и поделить на их количество, но это не совсем точно (турнир мог достичь
            # финалки, но не иметь рук в ранней стадии).
            # Лучший fallback: рассчитать только count. Или принять total_final_tables как kwargs.
            # Давайте используем OverallStats, как и планировалось.

            # Если OverallStats недоступен, мы не можем точно посчитать "на турнир".
            # В таком случае, лучше вернуть только count и, возможно, warning.
            # Но в нашей архитектуре OverallStats всегда доступен.

            # Получаем количество турниров, достигших финалки (нужно для расчета "на турнир")
            # В ApplicationService это OverallStats.total_final_tables.
            # Здесь в плагине, если нет OverallStats, мы не можем получить это число надежно.
            # Поэтому плагин *должен* использовать OverallStats.
            # Если ApplicationService не передаст OverallStats, плагин должен уметь это обработать.

            # Исправим compute signature в BaseStat, чтобы OverallStats был обязательным параметром,
            # или обрабатывать случай его отсутствия в плагинах, как сделано здесь.

            # Предполагая, что OverallStats всегда передается (по нашей архитектуре):
            total_final_tables = overall_stats.total_final_tables if overall_stats else 0
            early_ft_ko_per_tournament = early_ft_ko_count / total_final_tables if total_final_tables > 0 else 0.0
            early_ft_ko_per_tournament = round(early_ft_ko_per_tournament, 2)


        return {
            "early_ft_ko_count": early_ft_ko_count,
            "early_ft_ko_per_tournament": early_ft_ko_per_tournament,
        }