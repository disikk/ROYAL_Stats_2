"""
Модель агрегированной статистики Hero для Royal Stats.
Используется для передачи итоговых показателей в GUI, отчёты, экспорты.
"""

from dataclasses import dataclass

@dataclass
class HeroStats:
    """
    Агрегированные показатели только по Hero (для сводных отчётов).
    """
    total_tournaments: int
    total_sessions: int
    total_buyin: float
    total_payout: float
    total_ko: int
    last_update: str = ""

    def as_dict(self):
        return {
            "total_tournaments": self.total_tournaments,
            "total_sessions": self.total_sessions,
            "total_buyin": self.total_buyin,
            "total_payout": self.total_payout,
            "total_ko": self.total_ko,
            "last_update": self.last_update,
        }
