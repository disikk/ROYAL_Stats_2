# -*- coding: utf-8 -*-

"""
ITM-плагин для Hero (In The Money — попадание в топ-3).
Обновлен для работы с новой архитектурой и моделями.
"""

from typing import Dict, Any, List, Optional
from .base import BaseStat
from models import Tournament, FinalTableHand, Session

class ITMStat(BaseStat):
    name = "ITM"
    description = "ITM% — процент попадания Hero в топ-3 (призовые места)"

    def compute(self,
                tournaments: Optional[List[Tournament]] = None,
                final_table_hands: Optional[List[FinalTableHand]] = None,
                sessions: Optional[List[Session]] = None,
                overall_stats: Optional[Any] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Рассчитывает ITM% (процент попадания в топ-3).
        
        Args:
            tournaments: Список объектов Tournament
            final_table_hands: Список рук финального стола (не используется)
            sessions: Список сессий (не используется)
            **kwargs: Дополнительные параметры
            
        Returns:
            Словарь с ключом 'itm_percent' - процент попадания в топ-3
        """
        # Всегда считаем из списка турниров
        tournaments = tournaments or []
        total = len(tournaments)
        itm_count = sum(1 for t in tournaments if t.finish_place is not None and t.finish_place in (1, 2, 3))

        itm_percent = (itm_count / total * 100) if total > 0 else 0.0
        itm_percent = round(itm_percent, 2)

        return {"itm_percent": itm_percent}