# -*- coding: utf-8 -*-

"""
Модель раздачи финального стола для Hero в Royal Stats.
Описывает данные из таблицы hero_final_table_hands.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class FinalTableHand:
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
    hero_ko_this_hand: int = 0
    session_id: Optional[str] = None
    is_early_final: bool = False # Стадия 9-6 игроков
    id: Optional[int] = None # ID из БД, опционально

    def as_dict(self) -> dict:
        """
        Преобразует объект в словарь для удобства работы с БД.
        """
        return {
            "tournament_id": self.tournament_id,
            "hand_id": self.hand_id,
            "hand_number": self.hand_number,
            "table_size": self.table_size,
            "bb": self.bb,
            "hero_stack": self.hero_stack,
            "hero_ko_this_hand": self.hero_ko_this_hand,
            "session_id": self.session_id,
            "is_early_final": self.is_early_final,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data: dict) -> 'FinalTableHand':
        """
        Создает объект FinalTableHand из словаря (например, полученного из БД).
        """
        return FinalTableHand(
            tournament_id=data.get("tournament_id"), # Предполагаем, что tournament_id всегда есть
            hand_id=data.get("hand_id"), # Предполагаем, что hand_id всегда есть
            hand_number=data.get("hand_number", 0),
            table_size=data.get("table_size", 0),
            bb=data.get("bb", 0.0),
            hero_stack=data.get("hero_stack", 0.0),
            hero_ko_this_hand=data.get("hero_ko_this_hand", 0),
            session_id=data.get("session_id"),
            is_early_final=bool(data.get("is_early_final", 0)), # SQLite хранит BOOLEAN как 0/1
            id=data.get("id")
        )