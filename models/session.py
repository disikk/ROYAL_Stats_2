"""
Модель игровой сессии для Hero в Royal Stats.
Содержит только данные, относящиеся к Hero.
"""

from dataclasses import dataclass
from typing import List

@dataclass
class HeroSession:
    """
    Игровая сессия Hero (обычно — группа турниров за один день/период).
    """
    session_id: str                  # Уникальный идентификатор сессии (можно UUID или дата)
    tournaments: List[str]           # Список ID турниров, сыгранных в сессии
    total_buyin: float               # Общая сумма входов (buy-in) за все турниры сессии
    total_payout: float              # Общая сумма выплат по всем турнирам
    total_ko: int                    # Общее количество KO за сессию

    def as_dict(self):
        """
        Для сериализации.
        """
        return {
            "session_id": self.session_id,
            "tournaments": self.tournaments,
            "total_buyin": self.total_buyin,
            "total_payout": self.total_payout,
            "total_ko": self.total_ko,
        }
