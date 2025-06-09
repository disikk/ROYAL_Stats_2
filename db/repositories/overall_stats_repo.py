# -*- coding: utf-8 -*-

"""
Репозиторий агрегированной статистики только для Hero. Использует DatabaseManager.
"""

from typing import Optional
from db.manager import DatabaseManager, database_manager  # Используем синглтон менеджер БД
from models import OverallStats
from datetime import datetime # Импортируем для метки времени

class OverallStatsRepository:
    """
    Репозиторий для работы с таблицей overall_stats.
    Предполагается, что таблица содержит ровно одну запись с id=1.
    """

    def __init__(self, db_manager: DatabaseManager = database_manager):
        self.db = db_manager  # Используем переданный менеджер

    def get_overall_stats(self) -> OverallStats:
        """
        Получает агрегированную статистику по Hero.
        Если запись не существует, возвращает OverallStats с дефолтными значениями.
        """
        query = "SELECT * FROM overall_stats WHERE id = 1"
        result = self.db.execute_query(query)
        if result:
            return OverallStats.from_dict(dict(result[0]))
        else:
            # Возвращаем дефолтные значения, если запись еще не создана
            # Инициализация должна гарантировать наличие записи с id=1
            return OverallStats()

    def update_overall_stats(self, stats: OverallStats):
        """
        Обновляет агрегированную статистику Hero.
        Принимает объект OverallStats с уже подсчитанными агрегатами.
        Обновляет только запись с id=1.
        Если новые значения совпадают с уже сохранёнными, обновление не
        выполняется. Это предотвращает лишние изменения файла БД и,
        соответственно, изменение его контрольной суммы.
        """

        # Получаем текущие значения, чтобы сравнить с новыми
        current = self.get_overall_stats()

        def _strip(stats_obj: OverallStats) -> dict:
            data = stats_obj.as_dict()
            data.pop("last_updated", None)
            data.pop("id", None)
            return data

        if _strip(current) == _strip(stats):
            return

        query = """
            UPDATE overall_stats
            SET
                total_tournaments = ?,
                total_final_tables = ?,
                total_knockouts = ?,
                avg_finish_place = ?,
                avg_finish_place_ft = ?,
                avg_finish_place_no_ft = ?,
                total_prize = ?,
                total_buy_in = ?,
                avg_ko_per_tournament = ?,
                avg_ft_initial_stack_chips = ?,
                avg_ft_initial_stack_bb = ?,
                big_ko_x1_5 = ?,
                big_ko_x2 = ?,
                big_ko_x10 = ?,
                big_ko_x100 = ?,
                big_ko_x1000 = ?,
                big_ko_x10000 = ?,
                early_ft_ko_count = ?,
                early_ft_ko_per_tournament = ?,
                early_ft_bust_count = ?,
                early_ft_bust_per_tournament = ?,
                pre_ft_ko_count = ?,
                incomplete_ft_count = ?,
                incomplete_ft_percent = ?,
                last_updated = ?
            WHERE id = 1
        """
        params = (
            stats.total_tournaments,
            stats.total_final_tables,
            stats.total_knockouts,
            stats.avg_finish_place,
            stats.avg_finish_place_ft,
            stats.avg_finish_place_no_ft,
            stats.total_prize,
            stats.total_buy_in,
            stats.avg_ko_per_tournament,
            stats.avg_ft_initial_stack_chips,
            stats.avg_ft_initial_stack_bb,
            stats.big_ko_x1_5,
            stats.big_ko_x2,
            stats.big_ko_x10,
            stats.big_ko_x100,
            stats.big_ko_x1000,
            stats.big_ko_x10000,
            stats.early_ft_ko_count,
            stats.early_ft_ko_per_tournament,
            stats.early_ft_bust_count,
            stats.early_ft_bust_per_tournament,
            stats.pre_ft_ko_count,
            stats.incomplete_ft_count,
            stats.incomplete_ft_percent,
            datetime.now().isoformat(), # Обновляем метку времени
        )
        self.db.execute_update(query, params)