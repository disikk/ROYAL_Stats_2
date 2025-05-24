# -*- coding: utf-8 -*-

"""
Репозиторий турниров Hero. Работает через DatabaseManager.
Обновлен под новую схему БД.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from db.manager import database_manager # Используем синглтон менеджер БД
from models import Tournament

class TournamentRepository:
    """
    Хранит и отдает инфу о турнирах только по Hero из таблицы tournaments.
    """

    def __init__(self):
        # Репозитории работают с менеджером БД
        self.db = database_manager # Используем синглтон

    def add_or_update_tournament(self, tournament: Tournament):
        """
        Добавляет новый турнир или обновляет существующий по tournament_id.
        Использует ON CONFLICT для upsert.
        Логика мерджа данных из HH и TS происходит в ApplicationService,
        сюда приходит уже подготовленный объект Tournament.
        """
        query = """
            INSERT INTO tournaments (
                tournament_id, tournament_name, start_time, buyin, payout,
                finish_place, ko_count, session_id, reached_final_table,
                final_table_initial_stack_chips, final_table_initial_stack_bb
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tournament_id)
            DO UPDATE SET
                tournament_name = COALESCE(excluded.tournament_name, tournaments.tournament_name),
                start_time = COALESCE(excluded.start_time, tournaments.start_time),
                buyin = COALESCE(excluded.buyin, tournaments.buyin),
                payout = COALESCE(excluded.payout, tournaments.payout),
                finish_place = COALESCE(excluded.finish_place, tournaments.finish_place),
                ko_count = excluded.ko_count, -- ko_count приходит уже объединенный из ApplicationService
                session_id = COALESCE(tournaments.session_id, excluded.session_id), -- Сохраняем первый session_id, если новый не установлен
                reached_final_table = tournaments.reached_final_table OR excluded.reached_final_table, -- Флаг становится TRUE если хоть раз был TRUE
                final_table_initial_stack_chips = COALESCE(excluded.final_table_initial_stack_chips, tournaments.final_table_initial_stack_chips),
                final_table_initial_stack_bb = COALESCE(excluded.final_table_initial_stack_bb, tournaments.final_table_initial_stack_bb)
        """

        params = (
            tournament.tournament_id,
            tournament.tournament_name,
            tournament.start_time,
            tournament.buyin,
            tournament.payout,
            tournament.finish_place,
            tournament.ko_count,
            tournament.session_id,
            tournament.reached_final_table,
            tournament.final_table_initial_stack_chips,
            tournament.final_table_initial_stack_bb,
        )

        self.db.execute_update(query, params)


    def get_tournament_by_id(self, tournament_id: str) -> Optional[Tournament]:
        """
        Возвращает данные Hero по одному турниру по ID.
        """
        query = """
            SELECT
                id, tournament_id, tournament_name, start_time, buyin, payout,
                finish_place, ko_count, session_id, reached_final_table,
                final_table_initial_stack_chips, final_table_initial_stack_bb
            FROM tournaments
            WHERE tournament_id=?
        """
        result = self.db.execute_query(query, (tournament_id,))
        if result:
            # results from execute_query are Row objects, convert to dict first
            return Tournament.from_dict(dict(result[0]))
        return None

    def get_all_tournaments(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> List[Tournament]:
        """
        Возвращает список всех турниров Hero, опционально фильтруя по сессии или бай-ину.
        """
        query = """
            SELECT
                id, tournament_id, tournament_name, start_time, buyin, payout,
                finish_place, ko_count, session_id, reached_final_table,
                final_table_initial_stack_chips, final_table_initial_stack_bb
            FROM tournaments
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Сортируем по времени начала турнира для хронологического порядка
        query += " ORDER BY start_time ASC"

        results = self.db.execute_query(query, params)
        return [Tournament.from_dict(dict(row)) for row in results]

    def count_all(self, buyin_filter: Optional[float] = None) -> int:
        """
        Возвращает общее количество турниров, опционально фильтруя по бай-ину.
        """
        query = "SELECT COUNT(*) FROM tournaments"
        conditions = []
        params = []

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result else 0

    def count_reached_final_table(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> int:
         """
         Возвращает количество турниров, в которых Hero достиг финального стола,
         опционально фильтруя по сессии или бай-ину.
         """
         query = "SELECT COUNT(*) FROM tournaments WHERE reached_final_table = 1"
         conditions = []
         params = []

         if session_id:
             conditions.append("session_id = ?")
             params.append(session_id)

         if buyin_filter is not None:
             conditions.append("buyin = ?")
             params.append(buyin_filter)

         if conditions:
              query += " AND " + " AND ".join(conditions)

         result = self.db.execute_query(query, params)
         return result[0][0] if result else 0

    def sum_ko_count(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> int:
        """
        Суммирует общее количество KO из таблицы tournaments,
        опционально фильтруя по сессии или бай-ину.
        """
        query = "SELECT SUM(ko_count) FROM tournaments"
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0

    def sum_payout(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Суммирует общую выплату из таблицы tournaments,
        опционально фильтруя по сессии или бай-ину.
        """
        query = "SELECT SUM(payout) FROM tournaments"
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0

    def sum_buyin(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Суммирует общий бай-ин из таблицы tournaments,
        опционально фильтруя по сессии или бай-ину.
        """
        query = "SELECT SUM(buyin) FROM tournaments"
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0


    def get_avg_finish_place(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Рассчитывает среднее финишное место по турнирам (включая не финалку),
        опционально фильтруя по сессии или бай-ину.
        Возвращает 0.0 если нет турниров.
        """
        query = "SELECT AVG(finish_place) FROM tournaments WHERE finish_place IS NOT NULL"
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
             query += " AND " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0


    def get_avg_finish_place_ft(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Рассчитывает среднее финишное место только по турнирам на финальном столе (1-9),
        опционально фильтруя по сессии или бай-ину.
        Возвращает 0.0 если нет турниров на финалке.
        """
        query = """
            SELECT AVG(finish_place)
            FROM tournaments
            WHERE reached_final_table = 1 AND finish_place IS NOT NULL AND finish_place BETWEEN 1 AND 9
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
             query += " AND " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0


    def get_avg_ft_initial_stack_chips(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Рассчитывает средний стек Hero в фишках на старте финального стола
        (только для турниров, достигших финалки), опционально фильтруя.
        """
        query = """
            SELECT AVG(final_table_initial_stack_chips)
            FROM tournaments
            WHERE reached_final_table = 1 AND final_table_initial_stack_chips IS NOT NULL
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
             query += " AND " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0


    def get_avg_ft_initial_stack_bb(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Рассчитывает средний стек Hero в BB на старте финального стола
        (только для турниров, достигших финалки), опционально фильтруя.
        """
        query = """
            SELECT AVG(final_table_initial_stack_bb)
            FROM tournaments
            WHERE reached_final_table = 1 AND final_table_initial_stack_bb IS NOT NULL
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
             query += " AND " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0

    def get_distinct_buyins(self) -> List[float]:
        """
        Возвращает список всех уникальных бай-инов турниров Hero.
        """
        query = "SELECT DISTINCT buyin FROM tournaments WHERE buyin IS NOT NULL ORDER BY buyin ASC"
        results = self.db.execute_query(query)
        return [row[0] for row in results if row[0] is not None]

    def get_avg_finish_place_no_ft(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> float:
        """
        Рассчитывает среднее финишное место только по турнирам, где НЕ достиг финального стола,
        опционально фильтруя по сессии или бай-ину.
        Возвращает 0.0 если нет таких турниров.
        """
        query = """
            SELECT AVG(finish_place)
            FROM tournaments
            WHERE reached_final_table = 0 AND finish_place IS NOT NULL
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)

        if conditions:
            query += " AND " + " AND ".join(conditions)

        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0


# Создаем синглтон экземпляр репозитория
tournament_repository = TournamentRepository()