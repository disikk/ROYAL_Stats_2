# -*- coding: utf-8 -*-

"""
Модель игровой сессии для Hero в Royal Stats.
Описывает данные из таблицы sessions.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from .base_model import BaseModel

@dataclass
class Session(BaseModel):
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
