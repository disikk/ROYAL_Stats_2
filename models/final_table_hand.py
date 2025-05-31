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
    players_count: int = 0
    hero_ko_this_hand: float = 0.0
    pre_ft_ko: float = 0.0
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
            "players_count": self.players_count,
            "hero_ko_this_hand": self.hero_ko_this_hand,
            "pre_ft_ko": self.pre_ft_ko,
            "session_id": self.session_id,
            "is_early_final": self.is_early_final,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data) -> 'FinalTableHand':
        """
        Создает объект FinalTableHand из словаря или sqlite3.Row (например, полученного из БД).
        """
        try:
            # Проверяем, имеет ли объект метод get (dict)
            if hasattr(data, 'get'):
                return FinalTableHand(
                    tournament_id=data.get("tournament_id"), # Предполагаем, что tournament_id всегда есть
                    hand_id=data.get("hand_id"), # Предполагаем, что hand_id всегда есть
                    hand_number=data.get("hand_number", 0),
                    table_size=data.get("table_size", 0),
                    bb=data.get("bb", 0.0),
                    hero_stack=data.get("hero_stack", 0.0),
                    players_count=data.get("players_count", 0),
                    hero_ko_this_hand=data.get("hero_ko_this_hand", 0.0),
                    pre_ft_ko=data.get("pre_ft_ko", 0.0),
                    session_id=data.get("session_id"),
                    is_early_final=bool(data.get("is_early_final", 0)), # SQLite хранит BOOLEAN как 0/1
                    id=data.get("id")
                )
            else:
                # Предполагаем, что это sqlite3.Row (доступ по имени колонки как к элементу словаря)
                return FinalTableHand(
                    tournament_id=data["tournament_id"] if "tournament_id" in data.keys() else None,
                    hand_id=data["hand_id"] if "hand_id" in data.keys() else None,
                    hand_number=data["hand_number"] if "hand_number" in data.keys() else 0,
                    table_size=data["table_size"] if "table_size" in data.keys() else 0,
                    bb=data["bb"] if "bb" in data.keys() else 0.0,
                    hero_stack=data["hero_stack"] if "hero_stack" in data.keys() else 0.0,
                    players_count=data["players_count"] if "players_count" in data.keys() else 0,
                    hero_ko_this_hand=data["hero_ko_this_hand"] if "hero_ko_this_hand" in data.keys() else 0.0,
                    pre_ft_ko=data["pre_ft_ko"] if "pre_ft_ko" in data.keys() else 0.0,
                    session_id=data["session_id"] if "session_id" in data.keys() else None,
                    is_early_final=bool(data["is_early_final"]) if "is_early_final" in data.keys() else False, # SQLite хранит BOOLEAN как 0/1
                    id=data["id"] if "id" in data.keys() else None
                )
        except Exception as e:
            # В случае ошибки возвращаем базовый объект
            print(f"Error in FinalTableHand.from_dict: {e}")
            return FinalTableHand(tournament_id="error", hand_id="error", hand_number=0, table_size=0, bb=0.0, hero_stack=0.0, players_count=0)
