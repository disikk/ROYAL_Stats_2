# -*- coding: utf-8 -*-

"""
Базовый класс для всех стат-плагинов Royal Stats.
"""

from typing import Any, Dict, List
# Импортируем модели, которые могут понадобиться плагинам
from models import Tournament, FinalTableHand, Session, OverallStats

class BaseStat:
    """
    Интерфейс для стат-плагина.
    Все плагины обязаны определить name, description и реализовать compute.
    """

    # Уникальное имя стата
    name: str = "BaseStat"
    # Человекочитаемое описание стата
    description: str = "Базовый стат-плагин"

    def compute(self,
                tournaments: List[Tournament],
                final_table_hands: List[FinalTableHand],
                sessions: List[Session], # Возможно не понадобится для большинства стат
                overall_stats: OverallStats, # Возможно не понадобится для большинства стат
                **kwargs: Any # Для дополнительных параметров, например, buyin_filter
               ) -> Dict[str, Any]:
        """
        Главный метод расчёта стата.
        На вход подаются:
            - tournaments: список объектов Tournament (отфильтрованных по сессии/бай-ину, если применимо)
            - final_table_hands: список объектов FinalTableHand (отфильтрованных по сессии/турнирам, если применимо)
            - sessions: список объектов Session (может быть использован для сессионной статистики)
            - overall_stats: объект OverallStats (для доступа к уже посчитанным общим агрегатам)
            - **kwargs: Дополнительные параметры (например, buyin_filter)

        Возвращает словарь с рассчитанными значениями стата.
        Ключи словаря будут использоваться для отображения.
        Значения должны быть примитивными типами (int, float, str, bool).
        """
        raise NotImplementedError("Плагин обязан реализовать метод compute()")

    def get_description(self) -> str:
        """Возвращает описание стата."""
        return self.description

    def get_name(self) -> str:
        """Возвращает уникальное имя стата."""
        return self.name