# -*- coding: utf-8 -*-

"""
Репозиторий для хранения и получения данных о сессиях Hero. Использует DatabaseManager.
Обновлен под новую схему БД.
"""

import uuid
from typing import List, Optional
from db.manager import database_manager # Используем синглтон менеджер БД
from models import Session

class SessionRepository:
    """
    Репозиторий для хранения агрегированной инфы о сессиях Hero из таблицы sessions.
    """

    def __init__(self):
        self.db = database_manager # Используем синглтон

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

# Создаем синглтон экземпляр репозитория
session_repository = SessionRepository()