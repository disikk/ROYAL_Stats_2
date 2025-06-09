# -*- coding: utf-8 -*-

"""
Репозиторий для хранения и получения данных о сессиях Hero. Использует DatabaseManager.
Обновлен под новую схему БД.
"""

import uuid
from typing import List, Optional
from db.manager import DatabaseManager, database_manager  # Используем синглтон менеджер БД
from models import Session

class SessionRepository:
    """
    Репозиторий для хранения агрегированной инфы о сессиях Hero из таблицы sessions.
    """

    def __init__(self, db_manager: DatabaseManager = database_manager):
        """Initialize repository with the shared database manager."""
        self.db = db_manager

    def create_session(self, session_name: str) -> Session:
        """
        Создает новую сессию в базе данных.
        Возвращает объект созданной сессии.
        """
        session_id = str(uuid.uuid4())
        query = """
            INSERT INTO sessions (session_id, session_name)
            VALUES (?, ?)
        """
        try:
            # Обратите внимание: session_id используется и как id (INTEGER PRIMARY KEY AUTOINCREMENT)
            # и как session_id (TEXT UNIQUE NOT NULL). Это может быть источником путаницы.
            # В схеме sessions.id это INTEGER PRIMARY KEY AUTOINCREMENT, а session_id - TEXT UNIQUE.
            # Давайте исправим insert, чтобы он вставлял только session_id и session_name,
            # а id генерировался автоматически.
            insert_query = """
                INSERT INTO sessions (session_id, session_name)
                VALUES (?, ?)
            """
            self.db.execute_update(insert_query, (session_id, session_name))

            # Получаем созданную сессию по session_id
            return self.get_session_by_id(session_id)

        except Exception as e:
            # Обработка ошибки создания сессии
            print(f"Ошибка при создании сессии '{session_name}': {e}")
            raise # Пробрасываем исключение

    def update_session_stats(self, session: Session):
        """
        Обновляет агрегированную статистику для существующей сессии.
        Принимает объект Session с уже подсчитанными агрегатами.
        Если значения статистики не изменились, обновление не выполняется,
        чтобы не менять файл базы данных лишний раз.
        """

        current = self.get_session_by_id(session.session_id)
        if current:
            def _strip(s: Session) -> dict:
                data = s.as_dict()
                # Поля session_name и created_at не меняются при обновлении
                data.pop("id", None)
                data.pop("session_name", None)
                data.pop("created_at", None)
                return data

            if _strip(current) == _strip(session):
                return

        query = """
            UPDATE sessions
            SET
                tournaments_count = ?,
                knockouts_count = ?,
                avg_finish_place = ?,
                total_prize = ?,
                total_buy_in = ?
            WHERE session_id = ?
        """
        params = (
            session.tournaments_count,
            session.knockouts_count,
            session.avg_finish_place,
            session.total_prize,
            session.total_buy_in,
            session.session_id,
        )
        self.db.execute_update(query, params)

    def update_session_name(self, session_id: str, new_name: str):
        """Обновляет название сессии."""
        query = "UPDATE sessions SET session_name = ? WHERE session_id = ?"
        self.db.execute_update(query, (new_name, session_id))

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """
        Получает агрегированную инфу по одной сессии Hero по session_id.
        """
        query = """
            SELECT
                id, session_id, session_name, created_at, tournaments_count,
                knockouts_count, avg_finish_place, total_prize, total_buy_in
            FROM sessions WHERE session_id=?
        """
        result = self.db.execute_query(query, (session_id,))
        if result:
             # results from execute_query are Row objects, convert to dict first
            return Session.from_dict(dict(result[0]))
        return None

    def get_all_sessions(self) -> List[Session]:
        """
        Получает все сессии Hero.
        """
        query = """
            SELECT
                id, session_id, session_name, created_at, tournaments_count,
                knockouts_count, avg_finish_place, total_prize, total_buy_in
            FROM sessions ORDER BY created_at DESC
        """
        results = self.db.execute_query(query)
        return [Session.from_dict(dict(row)) for row in results]

    def delete_session_by_id(self, session_id: str):
        """
        Удаляет сессию и все связанные с ней турниры и руки фин.стола (ON DELETE CASCADE).
        """
        query = "DELETE FROM sessions WHERE session_id = ?"
        self.db.execute_update(query, (session_id,))
    
    def calculate_session_stats_efficient(self, session_id: str) -> dict:
        """
        Эффективно рассчитывает статистику сессии одним SQL запросом.
        Возвращает словарь со всеми необходимыми показателями.
        """
        # Получаем основную статистику турниров
        tournament_stats_query = """
            SELECT 
                COUNT(*) as tournaments_count,
                SUM(CASE WHEN finish_place IS NOT NULL THEN finish_place ELSE 0 END) as sum_places,
                SUM(CASE WHEN finish_place IS NOT NULL THEN 1 ELSE 0 END) as count_places,
                SUM(CASE WHEN payout IS NOT NULL THEN payout ELSE 0 END) as total_prize,
                SUM(CASE WHEN buyin IS NOT NULL THEN buyin ELSE 0 END) as total_buy_in
            FROM tournaments
            WHERE session_id = ?
        """
        
        # Получаем количество KO
        ko_stats_query = """
            SELECT SUM(hero_ko_this_hand) as total_knockouts
            FROM hero_final_table_hands
            WHERE session_id = ?
        """
        
        tournament_result = self.db.execute_query(tournament_stats_query, (session_id,))
        ko_result = self.db.execute_query(ko_stats_query, (session_id,))
        
        stats = {
            'tournaments_count': 0,
            'knockouts_count': 0.0,
            'avg_finish_place': 0.0,
            'total_prize': 0.0,
            'total_buy_in': 0.0
        }
        
        if tournament_result and tournament_result[0]:
            row = tournament_result[0]
            stats['tournaments_count'] = row[0] or 0
            
            # Рассчитываем среднее место
            sum_places = row[1] or 0
            count_places = row[2] or 0
            if count_places > 0:
                stats['avg_finish_place'] = round(sum_places / count_places, 2)
            
            stats['total_prize'] = round(row[3] or 0, 2)
            stats['total_buy_in'] = round(row[4] or 0, 2)
        
        if ko_result and ko_result[0] and ko_result[0][0] is not None:
            stats['knockouts_count'] = ko_result[0][0]
        
        return stats

# Создаем синглтон экземпляр репозитория
session_repository = SessionRepository(database_manager)
