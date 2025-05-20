# -*- coding: utf-8 -*-

"""
Модель агрегированной статистики Hero для Royal Stats.
Описывает данные из таблицы overall_stats.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class OverallStats:
    """
    Агрегированные показатели только по Hero (для сводных отчётов).
    Соответствует структуре таблицы overall_stats.
    """
    total_tournaments: int = 0
    total_final_tables: int = 0
    total_knockouts: int = 0
    avg_finish_place: float = 0.0 # Среднее место по всем турнирам
    avg_finish_place_ft: float = 0.0 # Среднее место только на финалке (1-9)
    total_prize: float = 0.0
    total_buy_in: float = 0.0
    avg_ko_per_tournament: float = 0.0 # Среднее KO за турнир (по всем турнирам)
    avg_ft_initial_stack_chips: float = 0.0 # Средний стек на старте финалки в фишках
    avg_ft_initial_stack_bb: float = 0.0 # Средний стек на старте финалки в BB
    big_ko_x1_5: int = 0
    big_ko_x2: int = 0
    big_ko_x10: int = 0
    big_ko_x100: int = 0
    big_ko_x1000: int = 0
    big_ko_x10000: int = 0
    early_ft_ko_count: int = 0 # Общее KO в ранней стадии финалки (9-6 игроков)
    early_ft_ko_per_tournament: float = 0.0 # Среднее KO в ранней финалке на турнир (достигший финалки)
    last_updated: Optional[str] = None
    id: Optional[int] = 1 # ID из БД, всегда 1

    def as_dict(self) -> dict:
        """
        Преобразует объект в словарь для удобства работы с БД.
        """
        return {
            "total_tournaments": self.total_tournaments,
            "total_final_tables": self.total_final_tables,
            "total_knockouts": self.total_knockouts,
            "avg_finish_place": self.avg_finish_place,
            "avg_finish_place_ft": self.avg_finish_place_ft,
            "total_prize": self.total_prize,
            "total_buy_in": self.total_buy_in,
            "avg_ko_per_tournament": self.avg_ko_per_tournament,
            "avg_ft_initial_stack_chips": self.avg_ft_initial_stack_chips,
            "avg_ft_initial_stack_bb": self.avg_ft_initial_stack_bb,
            "big_ko_x1_5": self.big_ko_x1_5,
            "big_ko_x2": self.big_ko_x2,
            "big_ko_x10": self.big_ko_x10,
            "big_ko_x100": self.big_ko_x100,
            "big_ko_x1000": self.big_ko_x1000,
            "big_ko_x10000": self.big_ko_x10000,
            "early_ft_ko_count": self.early_ft_ko_count,
            "early_ft_ko_per_tournament": self.early_ft_ko_per_tournament,
            "last_updated": self.last_updated,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data: dict) -> 'OverallStats':
        """
        Создает объект OverallStats из словаря (например, полученного из БД).
        """
        return OverallStats(
            total_tournaments=data.get("total_tournaments", 0),
            total_final_tables=data.get("total_final_tables", 0),
            total_knockouts=data.get("total_knockouts", 0),
            avg_finish_place=data.get("avg_finish_place", 0.0),
            avg_finish_place_ft=data.get("avg_finish_place_ft", 0.0),
            total_prize=data.get("total_prize", 0.0),
            total_buy_in=data.get("total_buy_in", 0.0),
            avg_ko_per_tournament=data.get("avg_ko_per_tournament", 0.0),
            avg_ft_initial_stack_chips=data.get("avg_ft_initial_stack_chips", 0.0),
            avg_ft_initial_stack_bb=data.get("avg_ft_initial_stack_bb", 0.0),
            big_ko_x1_5=data.get("big_ko_x1_5", 0),
            big_ko_x2=data.get("big_ko_x2", 0),
            big_ko_x10=data.get("big_ko_x10", 0),
            big_ko_x100=data.get("big_ko_x100", 0),
            big_ko_x1000=data.get("big_ko_x1000", 0),
            big_ko_x10000=data.get("big_ko_x10000", 0),
            early_ft_ko_count=data.get("early_ft_ko_count", 0),
            early_ft_ko_per_tournament=data.get("early_ft_ko_per_tournament", 0.0),
            last_updated=data.get("last_updated"),
            id=data.get("id", 1)
        )

    @property
    def last_updated_datetime(self) -> Optional[datetime]:
        """Возвращает дату последнего обновления в формате datetime."""
        if self.last_updated:
            try:
                return datetime.fromisoformat(self.last_updated)
            except ValueError:
                return None
        return None