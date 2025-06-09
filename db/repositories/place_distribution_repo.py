# -*- coding: utf-8 -*-

"""
Репозиторий для работы с распределением мест Hero на финальном столе.
"""

import sqlite3
from typing import Dict
from db.manager import DatabaseManager, database_manager  # Используем синглтон менеджер БД

class PlaceDistributionRepository:
    """
    Репозиторий для хранения и получения распределения мест Hero на финальном столе (1-9).
    """

    def __init__(self, db_manager: DatabaseManager = database_manager):
        self.db = db_manager  # Используем переданный менеджер

    def get_distribution(self) -> Dict[int, int]:
        """
        Возвращает распределение занятых мест (1-9) на финальном столе.
        Ключ - место, значение - количество финишей.
        """
        query = "SELECT place, count FROM places_distribution ORDER BY place"
        results = self.db.execute_query(query)
        # Преобразуем список Row в словарь для удобства {place: count}
        distribution = {row['place']: row['count'] for row in results}
        
        # Убедимся, что все места от 1 до 9 присутствуют в словаре, даже если count = 0
        for i in range(1, 10):
            if i not in distribution:
                distribution[i] = 0
                
        return distribution

    def increment_place_count(self, place: int):
        """
        Увеличивает счетчик для указанного финишного места.
        Предполагается, что place находится в диапазоне 1-9.
        """
        if not 1 <= place <= 9:
            print(f"Предупреждение: Попытка инкрементировать счетчик для некорректного места: {place}")
            return

        query = "UPDATE places_distribution SET count = count + 1 WHERE place = ?"
        self.db.execute_update(query, (place,))

    def update_distribution(self, distribution: Dict[int, int]):
        """
        Обновляет распределение мест, изменяя только отличающиеся значения.
        Используется при пересчёте статистики, чтобы не трогать БД,
        если распределение не изменилось.
        """
        current = self.get_distribution()
        for place in range(1, 10):
            new_count = distribution.get(place, 0)
            if current.get(place, 0) != new_count:
                query = "UPDATE places_distribution SET count = ? WHERE place = ?"
                self.db.execute_update(query, (new_count, place))

    def reset_distribution(self):
        """
        Сбрасывает все счетчики распределения мест в 0.
        Может понадобиться, если мы захотим пересчитать статистику с нуля
        для текущей БД или при удалении данных.
        """
        query = "UPDATE places_distribution SET count = 0"
        self.db.execute_update(query)


# Пример использования (в ApplicationService)
# from db.repositories import PlaceDistributionRepository
# place_repo = PlaceDistributionRepository()
# dist = place_repo.get_distribution()
# place_repo.increment_place_count(3) # Hero занял 3-е место на финалке