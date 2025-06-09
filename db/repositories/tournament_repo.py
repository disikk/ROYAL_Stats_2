# -*- coding: utf-8 -*-

"""
Репозиторий турниров Hero. Работает через DatabaseManager.
Обновлен под новую схему БД.
"""

import sqlite3
from typing import List, Optional, Dict, Any, Tuple
from db.manager import DatabaseManager, database_manager  # Используем синглтон менеджер БД
from models import Tournament
from dataclasses import dataclass

@dataclass
class PaginationResult:
    """Результат пагинированного запроса."""
    tournaments: List[Tournament]
    total_count: int
    current_page: int
    page_size: int
    total_pages: int

class TournamentRepository:
    """
    Хранит и отдает инфу о турнирах только по Hero из таблицы tournaments.
    """

    def __init__(self, db_manager: DatabaseManager = database_manager):
        # Репозитории работают с менеджером БД
        self.db = db_manager  # Используем переданный менеджер

    def add_or_update_tournament(self, tournament: Tournament):
        """
        Добавляет новый турнир или обновляет существующий по tournament_id.
        Использует ON CONFLICT для upsert.
        Логика мерджа данных из HH и TS происходит в ApplicationService,
        сюда приходит уже подготовленный объект Tournament.
        Если значения всех полей не изменились, обновление пропускается,
        чтобы избежать лишних модификаций базы.
        """

        existing = self.get_tournament_by_id(tournament.tournament_id)
        if existing:
            def _strip(t: Tournament) -> dict:
                data = t.as_dict()
                data.pop("id", None)
                return data

            if _strip(existing) == _strip(tournament):
                return
        query = """
            INSERT INTO tournaments (
                tournament_id, tournament_name, start_time, buyin, payout,
                finish_place, ko_count, session_id, reached_final_table,
                final_table_initial_stack_chips, final_table_initial_stack_bb,
                final_table_start_players
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                final_table_initial_stack_bb = COALESCE(excluded.final_table_initial_stack_bb, tournaments.final_table_initial_stack_bb),
                final_table_start_players = COALESCE(excluded.final_table_start_players, tournaments.final_table_start_players)
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
            tournament.final_table_start_players,
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
                final_table_initial_stack_chips, final_table_initial_stack_bb,
                final_table_start_players
            FROM tournaments
            WHERE tournament_id=?
        """
        result = self.db.execute_query(query, (tournament_id,))
        if result:
            # results from execute_query are Row objects, convert to dict first
            return Tournament.from_dict(dict(result[0]))
        return None

    def get_all_tournaments(
        self,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        start_time_from: Optional[str] = None,
        start_time_to: Optional[str] = None,
    ) -> List[Tournament]:
        """
        Возвращает список всех турниров Hero с возможной фильтрацией по сессии,
        бай-ину и диапазону дат.
        """
        query = """
            SELECT
                id, tournament_id, tournament_name, start_time, buyin, payout,
                finish_place, ko_count, session_id, reached_final_table,
                final_table_initial_stack_chips, final_table_initial_stack_bb,
                final_table_start_players
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

        if start_time_from:
            conditions.append("start_time >= ?")
            params.append(start_time_from)

        if start_time_to:
            conditions.append("start_time <= ?")
            params.append(start_time_to)

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

    def get_ko_counts_for_tournaments(self, tournament_ids: List[str]) -> Dict[str, int]:
        """
        Эффективно получает количество KO для списка турниров одним запросом.
        Возвращает словарь {tournament_id: ko_count}.
        """
        if not tournament_ids:
            return {}
            
        placeholders = ",".join("?" * len(tournament_ids))
        query = f"""
            SELECT 
                tournament_id,
                SUM(hero_ko_this_hand) as ko_count
            FROM hero_final_table_hands
            WHERE tournament_id IN ({placeholders})
            GROUP BY tournament_id
        """
        
        results = self.db.execute_query(query, tournament_ids)
        
        # Преобразуем в словарь
        ko_counts = {}
        for row in results:
            ko_counts[row[0]] = row[1] if row[1] is not None else 0
            
        # Добавляем нулевые значения для турниров без KO
        for t_id in tournament_ids:
            if t_id not in ko_counts:
                ko_counts[t_id] = 0
                
        return ko_counts

    def get_tournaments_paginated(
        self,
        page: int = 1,
        page_size: int = 50,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        result_filter: Optional[str] = None,
        sort_column: str = "start_time",
        sort_direction: str = "DESC",
        start_time_from: Optional[str] = None,
        start_time_to: Optional[str] = None,
    ) -> PaginationResult:
        """
        Возвращает пагинированный список турниров с сортировкой.
        Args:
            page: Номер страницы (начиная с 1)
            page_size: Количество записей на странице
            session_id: Фильтр по сессии
            buyin_filter: Фильтр по бай-ину
            result_filter: Фильтр по результату ("prizes", "final_table", "out_of_prizes")
            sort_column: Колонка для сортировки
            sort_direction: Направление сортировки ("ASC" или "DESC")
            start_time_from: Начальная дата для фильтрации
            start_time_to: Конечная дата для фильтрации
        """
        page = max(1, page)
        page_size = max(1, min(500, page_size))
        allowed_sort_columns = {
            "tournament_id": "tournament_id",
            "start_time": "start_time",
            "buyin": "buyin",
            "finish_place": "finish_place",
            "payout": "payout",
            "ko_count": "ko_count",
            "final_table_initial_stack_chips": "final_table_initial_stack_chips",
            "profit": "(COALESCE(payout, 0) - COALESCE(buyin, 0))"
        }
        if sort_column not in allowed_sort_columns:
            sort_column = "start_time"
        if sort_direction.upper() not in ["ASC", "DESC"]:
            sort_direction = "DESC"
        base_query = """
            SELECT
                id, tournament_id, tournament_name, start_time, buyin, payout,
                finish_place, ko_count, session_id, reached_final_table,
                final_table_initial_stack_chips, final_table_initial_stack_bb,
                final_table_start_players
            FROM tournaments
        """
        count_query = "SELECT COUNT(*) FROM tournaments"
        conditions = []
        params = []
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)
        if start_time_from:
            conditions.append("start_time >= ?")
            params.append(start_time_from)
        if start_time_to:
            conditions.append("start_time <= ?")
            params.append(start_time_to)
        if result_filter:
            if result_filter == "prizes":
                conditions.append("finish_place IS NOT NULL AND finish_place BETWEEN 1 AND 3")
            elif result_filter == "final_table":
                conditions.append("reached_final_table = 1")
            elif result_filter == "out_of_prizes":
                conditions.append("finish_place IS NOT NULL AND finish_place > 3")
        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
        full_count_query = count_query + where_clause
        count_result = self.db.execute_query(full_count_query, params)
        total_count = count_result[0][0] if count_result else 0
        total_pages = (total_count + page_size - 1) // page_size
        if page > total_pages and total_pages > 0:
            page = total_pages
        sort_clause = f" ORDER BY {allowed_sort_columns[sort_column]} {sort_direction.upper()}"
        offset = (page - 1) * page_size
        pagination_clause = f" LIMIT {page_size} OFFSET {offset}"
        full_query = base_query + where_clause + sort_clause + pagination_clause
        results = self.db.execute_query(full_query, params)
        tournaments = [Tournament.from_dict(dict(row)) for row in results]
        return PaginationResult(
            tournaments=tournaments,
            total_count=total_count,
            current_page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_tournaments_count_by_filters(
        self,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        result_filter: Optional[str] = None
    ) -> int:
        """
        Возвращает количество турниров с учетом фильтров.
        Используется для обновления UI с информацией о фильтрации.
        """
        query = "SELECT COUNT(*) FROM tournaments"
        conditions = []
        params = []
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if buyin_filter is not None:
            conditions.append("buyin = ?")
            params.append(buyin_filter)
        if result_filter:
            if result_filter == "prizes":
                conditions.append("finish_place IS NOT NULL AND finish_place BETWEEN 1 AND 3")
            elif result_filter == "final_table":
                conditions.append("reached_final_table = 1")
            elif result_filter == "out_of_prizes":
                conditions.append("finish_place IS NOT NULL AND finish_place > 3")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        result = self.db.execute_query(query, params)
        return result[0][0] if result else 0

    def get_tournaments_statistics_by_filters(
        self,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        result_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Возвращает агрегированную статистику по турнирам с учетом фильтров.
        """
        base_query = """
            SELECT 
                COUNT(*) as total_tournaments,
                SUM(COALESCE(buyin, 0)) as total_buyin,
                SUM(COALESCE(payout, 0)) as total_payout,
                SUM(COALESCE(payout, 0) - COALESCE(buyin, 0)) as total_profit,
                SUM(ko_count) as total_ko,
                COUNT(CASE WHEN finish_place IS NOT NULL AND finish_place BETWEEN 1 AND 3 THEN 1 END) as itm_count
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
        if result_filter:
            if result_filter == "prizes":
                conditions.append("finish_place IS NOT NULL AND finish_place BETWEEN 1 AND 3")
            elif result_filter == "final_table":
                conditions.append("reached_final_table = 1")
            elif result_filter == "out_of_prizes":
                conditions.append("finish_place IS NOT NULL AND finish_place > 3")
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        result = self.db.execute_query(base_query, params)
        if result and result[0]:
            row = result[0]
            total_tournaments = row[0] or 0
            total_buyin = row[1] or 0.0
            total_payout = row[2] or 0.0
            total_profit = row[3] or 0.0
            total_ko = row[4] or 0
            itm_count = row[5] or 0
            itm_percent = (itm_count / total_tournaments * 100) if total_tournaments > 0 else 0.0
            roi = ((total_profit / total_buyin) * 100) if total_buyin > 0 else 0.0
            return {
                "total_tournaments": total_tournaments,
                "total_buyin": total_buyin,
                "total_payout": total_payout,
                "total_profit": total_profit,
                "total_ko": total_ko,
                "itm_count": itm_count,
                "itm_percent": itm_percent,
                "roi": roi
            }
        return {
            "total_tournaments": 0,
            "total_buyin": 0.0,
            "total_payout": 0.0,
            "total_profit": 0.0,
            "total_ko": 0,
            "itm_count": 0,
            "itm_percent": 0.0,
            "roi": 0.0
        }

    def delete_tournament_by_id(self, tournament_id: str):
        """Удаляет турнир по его ID."""
        query = "DELETE FROM tournaments WHERE tournament_id = ?"
        self.db.execute_update(query, (tournament_id,))

    def get_all_finish_places(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> List[int]:
        """
        Возвращает список всех finish_place для расчета среднего места.
        Опционально фильтрует по сессии или бай-ину.
        """
        query = "SELECT finish_place FROM tournaments WHERE finish_place IS NOT NULL"
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

        results = self.db.execute_query(query, params)
        return [row[0] for row in results if row[0] is not None]

    def get_final_table_finish_places(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> List[int]:
        """
        Возвращает список finish_place только для турниров с финальным столом.
        Опционально фильтрует по сессии или бай-ину.
        """
        query = """
            SELECT finish_place 
            FROM tournaments 
            WHERE reached_final_table = 1 
                AND finish_place IS NOT NULL 
                AND finish_place BETWEEN 1 AND 9
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

        results = self.db.execute_query(query, params)
        return [row[0] for row in results if row[0] is not None]

    def get_final_table_initial_stacks(self, session_id: Optional[str] = None, buyin_filter: Optional[float] = None) -> Dict[str, List[float]]:
        """
        Возвращает словарь {'chips': [...], 'bb': [...]} со стеками на старте финалки.
        Опционально фильтрует по сессии или бай-ину.
        """
        query = """
            SELECT 
                final_table_initial_stack_chips,
                final_table_initial_stack_bb
            FROM tournaments
            WHERE reached_final_table = 1
                AND final_table_initial_stack_chips IS NOT NULL
                AND final_table_initial_stack_bb IS NOT NULL
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

        results = self.db.execute_query(query, params)
        
        stacks = {
            'chips': [],
            'bb': []
        }
        
        for row in results:
            if row[0] is not None and row[1] is not None:
                stacks['chips'].append(row[0])
                stacks['bb'].append(row[1])
        
        return stacks


# Создаем синглтон экземпляр репозитория
tournament_repository = TournamentRepository(database_manager)
