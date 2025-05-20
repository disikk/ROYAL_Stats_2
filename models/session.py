# -*- coding: utf-8 -*-

"""
Модель игровой сессии для Hero в Royal Stats.
Описывает данные из таблицы sessions.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Session:
    """
    Игровая сессия Hero (обычно — группа турниров за один день/период).
    Соответствует структуре таблицы sessions.
    """
    session_id: str
    session_name: str
    created_at: Optional[str] = None # Дата/время создания сессии
    tournaments_count: int = 0 # Общее количество турниров в сессии
    knockouts_count: int = 0 # Общее количество KO в сессии
    avg_finish_place: float = 0.0 # Среднее место в сессии (по всем турнирам в сессии)
    total_prize: float = 0.0 # Общая выплата в сессии
    total_buy_in: float = 0.0 # Общий бай-ин в сессии
    id: Optional[int] = None # ID из БД, опционально

    def as_dict(self) -> dict:
        """
        Преобразует объект в словарь для удобства работы с БД.
        """
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "created_at": self.created_at,
            "tournaments_count": self.tournaments_count,
            "knockouts_count": self.knockouts_count,
            "avg_finish_place": self.avg_finish_place,
            "total_prize": self.total_prize,
            "total_buy_in": self.total_buy_in,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Session':
        """
        Создает объект Session из словаря (например, полученного из БД).
        """
        return Session(
            session_id=data.get("session_id"), # Предполагаем, что session_id всегда есть
            session_name=data.get("session_name", "Без названия"),
            created_at=data.get("created_at"),
            tournaments_count=data.get("tournaments_count", 0),
            knockouts_count=data.get("knockouts_count", 0),
            avg_finish_place=data.get("avg_finish_place", 0.0),
            total_prize=data.get("total_prize", 0.0),
            total_buy_in=data.get("total_buy_in", 0.0),
            id=data.get("id")
        )

    @property
    def created_datetime(self) -> Optional[datetime]:
        """Возвращает дату создания в формате datetime."""
        if self.created_at:
            try:
                # SQLite хранит TIMESTAMP как текст по умолчанию
                return datetime.fromisoformat(self.created_at)
            except ValueError:
                return None
        return None