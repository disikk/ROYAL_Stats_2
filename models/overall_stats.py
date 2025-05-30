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
    total_knockouts: float = 0.0
    avg_finish_place: float = 0.0 # Среднее место по всем турнирам
    avg_finish_place_ft: float = 0.0 # Среднее место только на финалке (1-9)
    avg_finish_place_no_ft: float = 0.0  # Среднее место когда не дошел до финалки
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
    early_ft_ko_count: float = 0.0 # Общее KO в ранней стадии финалки (9-6 игроков)
    early_ft_ko_per_tournament: float = 0.0 # Среднее KO в ранней финалке на турнир (достигший финалки)
    early_ft_bust_count: int = 0  # Количество вылетов Hero на местах 6-9
    early_ft_bust_per_tournament: float = 0.0  # Среднее число таких вылетов на турнир с финалкой
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
            "avg_finish_place_no_ft": self.avg_finish_place_no_ft,
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
            "early_ft_bust_count": self.early_ft_bust_count,
            "early_ft_bust_per_tournament": self.early_ft_bust_per_tournament,
            "last_updated": self.last_updated,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data) -> 'OverallStats':
        """
        Создает объект OverallStats из словаря или объекта sqlite3.Row (например, полученного из БД).
        """
        # Поддержка как для словарей (dict), так и для sqlite3.Row
        # sqlite3.Row поддерживает доступ как по индексу, так и по имени колонки
        try:
            # Проверяем, имеет ли объект метод get (dict)
            if hasattr(data, 'get'):
                return OverallStats(
                    total_tournaments=data.get("total_tournaments", 0),
                    total_final_tables=data.get("total_final_tables", 0),
                    total_knockouts=data.get("total_knockouts", 0.0),
                    avg_finish_place=data.get("avg_finish_place", 0.0),
                    avg_finish_place_ft=data.get("avg_finish_place_ft", 0.0),
                    avg_finish_place_no_ft=data.get("avg_finish_place_no_ft", 0.0),
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
                    early_ft_ko_count=data.get("early_ft_ko_count", 0.0),
                    early_ft_ko_per_tournament=data.get("early_ft_ko_per_tournament", 0.0),
                    early_ft_bust_count=data.get("early_ft_bust_count", 0),
                    early_ft_bust_per_tournament=data.get("early_ft_bust_per_tournament", 0.0),
                    last_updated=data.get("last_updated"),
                    id=data.get("id", 1)
                )
            else:
                # Предполагаем, что это sqlite3.Row (доступ по имени колонки как к элементу словаря)
                return OverallStats(
                    total_tournaments=data["total_tournaments"] if "total_tournaments" in data.keys() else 0,
                    total_final_tables=data["total_final_tables"] if "total_final_tables" in data.keys() else 0,
                    total_knockouts=data["total_knockouts"] if "total_knockouts" in data.keys() else 0.0,
                    avg_finish_place=data["avg_finish_place"] if "avg_finish_place" in data.keys() else 0.0,
                    avg_finish_place_ft=data["avg_finish_place_ft"] if "avg_finish_place_ft" in data.keys() else 0.0,
                    avg_finish_place_no_ft=data["avg_finish_place_no_ft"] if "avg_finish_place_no_ft" in data.keys() else 0.0,
                    total_prize=data["total_prize"] if "total_prize" in data.keys() else 0.0,
                    total_buy_in=data["total_buy_in"] if "total_buy_in" in data.keys() else 0.0,
                    avg_ko_per_tournament=data["avg_ko_per_tournament"] if "avg_ko_per_tournament" in data.keys() else 0.0,
                    avg_ft_initial_stack_chips=data["avg_ft_initial_stack_chips"] if "avg_ft_initial_stack_chips" in data.keys() else 0.0,
                    avg_ft_initial_stack_bb=data["avg_ft_initial_stack_bb"] if "avg_ft_initial_stack_bb" in data.keys() else 0.0,
                    big_ko_x1_5=data["big_ko_x1_5"] if "big_ko_x1_5" in data.keys() else 0,
                    big_ko_x2=data["big_ko_x2"] if "big_ko_x2" in data.keys() else 0,
                    big_ko_x10=data["big_ko_x10"] if "big_ko_x10" in data.keys() else 0,
                    big_ko_x100=data["big_ko_x100"] if "big_ko_x100" in data.keys() else 0,
                    big_ko_x1000=data["big_ko_x1000"] if "big_ko_x1000" in data.keys() else 0,
                    big_ko_x10000=data["big_ko_x10000"] if "big_ko_x10000" in data.keys() else 0,
                    early_ft_ko_count=data["early_ft_ko_count"] if "early_ft_ko_count" in data.keys() else 0.0,
                    early_ft_ko_per_tournament=data["early_ft_ko_per_tournament"] if "early_ft_ko_per_tournament" in data.keys() else 0.0,
                    early_ft_bust_count=data["early_ft_bust_count"] if "early_ft_bust_count" in data.keys() else 0,
                    early_ft_bust_per_tournament=data["early_ft_bust_per_tournament"] if "early_ft_bust_per_tournament" in data.keys() else 0.0,
                    last_updated=data["last_updated"] if "last_updated" in data.keys() else None,
                    id=data["id"] if "id" in data.keys() else 1
                )
        except Exception as e:
            # В случае ошибки возвращаем объект с значениями по умолчанию
            print(f"Error in OverallStats.from_dict: {e}")
            return OverallStats()

    @property
    def last_updated_datetime(self) -> Optional[datetime]:
        """Возвращает дату последнего обновления в формате datetime."""
        if self.last_updated:
            try:
                return datetime.fromisoformat(self.last_updated)
            except ValueError:
                return None
        return None