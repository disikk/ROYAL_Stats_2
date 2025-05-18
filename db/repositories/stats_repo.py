"""
Репозиторий агрегированной статистики только для Hero. Использует DatabaseManager.
"""

class StatsRepository:
    """
    Репозиторий статистики по Hero (итоговые показатели по всем турнирам/сессиям).
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self._ensure_table()

    def _ensure_table(self):
        """
        Создаёт таблицу с итоговой статистикой Hero (если не создана).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS hero_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_tournaments INTEGER NOT NULL,
                    total_sessions INTEGER NOT NULL,
                    total_buyin REAL NOT NULL,
                    total_payout REAL NOT NULL,
                    total_ko INTEGER NOT NULL,
                    last_update TEXT
                )
            """)
            conn.commit()

    def update_stats(self, total_tournaments, total_sessions, total_buyin, total_payout, total_ko, last_update):
        """
        Перезаписывает всю агрегированную статистику Hero.
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM hero_stats")
            c.execute("""
                INSERT INTO hero_stats (total_tournaments, total_sessions, total_buyin, total_payout, total_ko, last_update)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (total_tournaments, total_sessions, total_buyin, total_payout, total_ko, last_update))
            conn.commit()

    def get_stats(self):
        """
        Получает агрегированную статистику по Hero.
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT total_tournaments, total_sessions, total_buyin, total_payout, total_ko, last_update
                FROM hero_stats
                LIMIT 1
            """)
            row = c.fetchone()
            if row:
                return {
                    "total_tournaments": row[0],
                    "total_sessions": row[1],
                    "total_buyin": row[2],
                    "total_payout": row[3],
                    "total_ko": row[4],
                    "last_update": row[5],
                }
            return None
