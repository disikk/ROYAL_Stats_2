# -*- coding: utf-8 -*-

"""
Модель турнира для Hero в Royal Stats.
Описывает данные из таблицы tournaments.
"""

from dataclasses import dataclass
from typing import Optional

from .base_model import BaseModel

@dataclass
class Tournament(BaseModel):
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
    ko_count: float = 0.0 # Общее количество KO Hero в турнире
    session_id: Optional[str] = None # ID сессии импорта
    has_ts: bool = False
    has_hh: bool = False
    reached_final_table: bool = False # Достиг ли Hero финального стола 9-max
    final_table_initial_stack_chips: Optional[float] = None # Стек на старте финалки в фишках
    final_table_initial_stack_bb: Optional[float] = None # Стек на старте финалки в BB
    final_table_start_players: Optional[int] = None # Количество игроков в первой руке финального стола
    id: Optional[int] = None # ID из БД, опционально

