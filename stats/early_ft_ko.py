# -*- coding: utf-8 -*-

"""
Плагин для подсчёта количества и среднего KO Hero в ранней стадии финального стола.
Автономный плагин для работы с сырыми данными.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class EarlyFTKOStat(BaseStat):
    """Считает общее количество KO и среднее KO за турнир (достигший финалки)
    в раздачах финального стола в ранней стадии."""
    name: str = "Early FT KO"
    description: str = "Статистика KO в ранней стадии финального стола (6-9 игроков)"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает статистику KO в ранней стадии финального стола.

        Args:
            tournaments: Список турниров
            final_table_hands: Список рук финального стола
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры:
                - precomputed_stats: Dict с предварительно рассчитанными early_ft_ko_count, 
                  early_ft_ko_per_tournament и total_final_tables

        Returns:
            Словарь с ключами 'early_ft_ko_count' и 'early_ft_ko_per_tournament'
        """
        # Проверяем наличие предварительно рассчитанных значений
        tournaments = tournaments or []
        final_table_hands = final_table_hands or []
        precomputed_stats = kwargs.get('precomputed_stats', {})
        
        if ('early_ft_ko_count' in precomputed_stats and 
            'early_ft_ko_per_tournament' in precomputed_stats):
            # Используем предварительно рассчитанные значения
            early_ft_ko_count = precomputed_stats['early_ft_ko_count']
            early_ft_ko_per_tournament = precomputed_stats['early_ft_ko_per_tournament']
        else:
            # Рассчитываем из сырых данных
            # Фильтруем руки, относящиеся к ранней стадии финалки (is_early_final)
            early_hands = [hand for hand in final_table_hands if hand.is_early_final]
            early_ft_ko_count = sum(hand.hero_ko_this_hand for hand in early_hands)
            
            # Для расчета среднего на турнир нужно количество турниров с финальным столом
            if 'total_final_tables' in precomputed_stats:
                total_final_tables = precomputed_stats['total_final_tables']
            else:
                # Считаем из списка турниров
                total_final_tables = sum(1 for t in tournaments if t.reached_final_table)
            
            early_ft_ko_per_tournament = early_ft_ko_count / total_final_tables if total_final_tables > 0 else 0.0
            early_ft_ko_per_tournament = round(early_ft_ko_per_tournament, 2)

        return {
            "early_ft_ko_count": early_ft_ko_count,
            "early_ft_ko_per_tournament": early_ft_ko_per_tournament,
        }