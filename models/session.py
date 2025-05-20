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
    def from_dict(data) -> 'Session':
        """
        Создает объект Session из словаря или sqlite3.Row (например, полученного из БД).
        """
        try:
            # Проверяем, имеет ли объект метод get (dict)
            if hasattr(data, 'get'):
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
            else:
                # Предполагаем, что это sqlite3.Row (доступ по имени колонки как к элементу словаря)
                return Session(
                    session_id=data["session_id"] if "session_id" in data.keys() else None,
                    session_name=data["session_name"] if "session_name" in data.keys() else "Без названия",
                    created_at=data["created_at"] if "created_at" in data.keys() else None,
                    tournaments_count=data["tournaments_count"] if "tournaments_count" in data.keys() else 0,
                    knockouts_count=data["knockouts_count"] if "knockouts_count" in data.keys() else 0, 
                    avg_finish_place=data["avg_finish_place"] if "avg_finish_place" in data.keys() else 0.0,
                    total_prize=data["total_prize"] if "total_prize" in data.keys() else 0.0,
                    total_buy_in=data["total_buy_in"] if "total_buy_in" in data.keys() else 0.0,
                    id=data["id"] if "id" in data.keys() else None
                )
        except Exception as e:
            # В случае ошибки возвращаем объект с значениями по умолчанию
            print(f"Error in Session.from_dict: {e}")
            return Session(session_id="error", session_name="Error")

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