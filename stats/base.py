# -*- coding: utf-8 -*-

"""
Базовый класс для всех стат-плагинов Royal Stats.
"""

from typing import Any, Dict, List, Optional
# Импортируем модели, которые могут понадобиться плагинам
from models import Tournament, FinalTableHand, Session

class BaseStat:
    """
    Интерфейс для стат-плагина.
    Все плагины обязаны определить name, description и реализовать compute.
    
    Плагины должны быть полностью автономными и рассчитывать
    все необходимые значения из сырых данных.
    """

    # Уникальное имя стата
    name: str = "BaseStat"
    # Человекочитаемое описание стата
    description: str = "Базовый стат-плагин"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[FinalTableHand],
                sessions: Optional[List[Session]] = None,
                **kwargs: Any
               ) -> Dict[str, Any]:
        """
        Главный метод расчёта стата.
        
        Args:
            tournaments: список объектов Tournament (отфильтрованных по сессии/бай-ину, если применимо)
            final_table_hands: список объектов FinalTableHand (отфильтрованных по сессии/турнирам)
            sessions: список объектов Session (опционально, для сессионной статистики)
            **kwargs: Дополнительные параметры:
                - buyin_filter: фильтр по бай-ину
                - precomputed_stats: Dict[str, Any] - предварительно рассчитанные значения
                  для оптимизации (например, total_buy_in, total_prize и т.д.)

        Returns:
            Словарь с рассчитанными значениями стата.
            Ключи словаря будут использоваться для отображения.
            Значения должны быть примитивными типами (int, float, str, bool).
            
        Note:
            Плагины должны самостоятельно рассчитывать все необходимые значения
            из переданных сырых данных. Для оптимизации можно использовать
            precomputed_stats из kwargs, но плагин должен корректно работать
            и без них (fallback на прямые вычисления).
        """
        raise NotImplementedError("Плагин обязан реализовать метод compute()")

    def get_description(self) -> str:
        """Возвращает описание стата."""
        return self.description

    def get_name(self) -> str:
        """Возвращает уникальное имя стата."""
        return self.name