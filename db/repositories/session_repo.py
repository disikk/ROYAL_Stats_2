"""
Репозиторий для хранения и получения данных о сессиях только по Hero. Использует DatabaseManager.
"""

import json

class SessionRepository:
    """
    Репозиторий для хранения агрегированной инфы о сессиях Hero.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self._ensure_table()

    def _ensure_table(self):
        """
        Создаёт таблицу сессий Hero (если не создана).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS hero_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    tournaments TEXT NOT NULL,       -- Список турниров (JSON)
                    total_buyin REAL NOT NULL,
                    total_payout REAL NOT NULL,
                    total_ko INTEGER NOT NULL
                )
            """)
            conn.commit()

    def add_or_update_session(self, session_id, tournaments, total_buyin, total_payout, total_ko):
        """
        Добавляет или обновляет сессию по Hero.
        tournaments — список ID турниров (сериализуется в JSON).
        """
        tournaments_json = json.dumps(tournaments)
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO hero_sessions (session_id, tournaments, total_buyin, total_payout, total_ko)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id)
                DO UPDATE SET
                    tournaments=excluded.tournaments,
                    total_buyin=excluded.total_buyin,
                    total_payout=excluded.total_payout,
                    total_ko=excluded.total_ko
            """, (session_id, tournaments_json, total_buyin, total_payout, total_ko))
            conn.commit()

    def get_hero_session(self, session_id):
        """
        Получает агрегированную инфу по одной сессии Hero.
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT tournaments, total_buyin, total_payout, total_ko
                FROM hero_sessions WHERE session_id=?
            """, (session_id,))
            row = c.fetchone()
            if row:
                return {
                    "session_id": session_id,
                    "tournaments": json.loads(row[0]),
                    "total_buyin": row[1],
                    "total_payout": row[2],
                    "total_ko": row[3],
                }
            return None

    def get_all_hero_sessions(self):
        """
        Получает все сессии Hero (для отчёта или GUI).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT session_id, tournaments, total_buyin, total_payout, total_ko
                FROM hero_sessions
            """)
            rows = c.fetchall()
            return [
                {
                    "session_id": row[0],
                    "tournaments": json.loads(row[1]),
                    "total_buyin": row[2],
                    "total_payout": row[3],
                    "total_ko": row[4],
                } for row in rows
            ]
