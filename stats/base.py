"""
Базовый класс для всех стат-плагинов Royal Stats.
"""

from typing import Any, Dict, List

class BaseStat:
    """
    Интерфейс для стат-плагина.
    Все плагины обязаны реализовать compute и description.
    """

    name: str = "BaseStat"
    description: str = "Базовый стат-плагин"

    def compute(self, tournaments: List[Any], knockouts: List[Any], sessions: List[Any]) -> Dict:
        """
        Главный метод расчёта стата.
        На вход подаются:
            - tournaments: список HeroTournament
            - knockouts: список Knockout
            - sessions: список HeroSession
        Возвращает словарь или структуру для GUI/отчёта.
        """
        raise NotImplementedError("Плагин обязан реализовать метод compute()")

    def get_description(self) -> str:
        return self.description
