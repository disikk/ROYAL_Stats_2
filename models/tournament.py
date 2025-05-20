# -*- coding: utf-8 -*-

"""
Модель турнира для Hero в Royal Stats.
Описывает данные из таблицы tournaments.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Tournament:
    """
    Турнир с данными только по Hero.
    Соответствует структуре таблицы tournaments.
    """
    tournament_id: str
    tournament_name: Optional[str] = None
    start_time: Optional[str] = None # Храним как текст, конвертируем при необходимости
    buyin: float = 0.0
    payout: float = 0.0
    finish_place: Optional[int] = None # None, если не закончил турнир в этой сессии
    ko_count: int = 0 # Общее количество KO Hero в турнире
    session_id: Optional[str] = None # ID сессии импорта
    reached_final_table: bool = False # Достиг ли Hero финального стола 9-max
    final_table_initial_stack_chips: Optional[float] = None # Стек на старте финалки в фишках
    final_table_initial_stack_bb: Optional[float] = None # Стек на старте финалки в BB
    id: Optional[int] = None # ID из БД, опционально

    def as_dict(self) -> dict:
        """
        Преобразует объект в словарь для удобства работы с БД.
        """
        return {
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "start_time": self.start_time,
            "buyin": self.buyin,
            "payout": self.payout,
            "finish_place": self.finish_place,
            "ko_count": self.ko_count,
            "session_id": self.session_id,
            "reached_final_table": self.reached_final_table,
            "final_table_initial_stack_chips": self.final_table_initial_stack_chips,
            "final_table_initial_stack_bb": self.final_table_initial_stack_bb,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Tournament':
        """
        Создает объект Tournament из словаря (например, полученного из БД).
        """
        # Убедимся, что все ключи есть, используя get с None или дефолтными значениями
        return Tournament(
            tournament_id=data.get("tournament_id"), # Предполагаем, что tournament_id всегда есть из БД
            tournament_name=data.get("tournament_name"),
            start_time=data.get("start_time"),
            buyin=data.get("buyin", 0.0),
            payout=data.get("payout", 0.0),
            finish_place=data.get("finish_place"),
            ko_count=data.get("ko_count", 0),
            session_id=data.get("session_id"),
            reached_final_table=bool(data.get("reached_final_table", 0)), # SQLite хранит BOOLEAN как 0/1
            final_table_initial_stack_chips=data.get("final_table_initial_stack_chips"),
            final_table_initial_stack_bb=data.get("final_table_initial_stack_bb"),
            id=data.get("id")
        )