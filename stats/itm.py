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
                final_table_hands: List[Any],
                sessions: List[Any],
                overall_stats: Any,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает ITM%.
        
        Args:
            tournaments: Список объектов Tournament.
            overall_stats: Объект OverallStats (не используется в простой версии).
            **kwargs: Дополнительные параметры.
            
        Returns:
            Словарь с ключом 'itm_percent'.
        """
        # Всегда считаем из списка турниров
        total = len(tournaments)
        itm_count = sum(1 for t in tournaments if t.finish_place is not None and t.finish_place in (1, 2, 3))

        itm_percent = (itm_count / total * 100) if total > 0 else 0.0
        itm_percent = round(itm_percent, 2)

        return {"itm_percent": itm_percent}