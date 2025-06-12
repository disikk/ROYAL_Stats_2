# -*- coding: utf-8 -*-

"""
Модель агрегированной статистики Hero для Royal Stats.
Описывает данные из таблицы overall_stats.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from .base_model import BaseModel

@dataclass
class OverallStats(BaseModel):
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
    pre_ft_ko_count: float = 0.0  # KO в последней 5-max раздаче перед финалкой
    pre_ft_chipev: float = 0.0  # Средний результат в фишках до финального стола
    incomplete_ft_count: int = 0  # Сколько финалок стартовало с <9 игроков
    incomplete_ft_percent: int = 0  # Процент таких финалок от общего числа
    last_updated: Optional[str] = None
    id: Optional[int] = 1 # ID из БД, всегда 1

    @property
    def last_updated_datetime(self) -> Optional[datetime]:
        """Возвращает дату последнего обновления в формате datetime."""
        if self.last_updated:
            try:
                return datetime.fromisoformat(self.last_updated)
            except ValueError:
                return None
        return None
