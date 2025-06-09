# -*- coding: utf-8 -*-

"""
Модель раздачи финального стола для Hero в Royal Stats.
Описывает данные из таблицы hero_final_table_hands.
"""

from dataclasses import dataclass
from typing import Optional

from .base_model import BaseModel

@dataclass
class FinalTableHand(BaseModel):
    """
    Раздача финального стола, в которой участвовал Hero.
    Соответствует структуре таблицы hero_final_table_hands.
    """
    tournament_id: str
    hand_id: str
    hand_number: int
    table_size: int
    bb: float
    hero_stack: float
    players_count: int = 0
    hero_ko_this_hand: float = 0.0
    pre_ft_ko: float = 0.0
    hero_ko_attempts: int = 0  # Количество попыток выбить соперников в этой руке
    session_id: Optional[str] = None
    is_early_final: bool = False # Стадия 9-6 игроков
    id: Optional[int] = None # ID из БД, опционально

