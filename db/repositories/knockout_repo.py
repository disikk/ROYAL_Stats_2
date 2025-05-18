"""
Репозиторий KO Hero. Работает через DatabaseManager.
"""

class KnockoutRepository:
    """
    Хранит только KO Hero.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self._ensure_table()

    def _ensure_table(self):
        """
        Создаёт таблицу hero_knockouts (если не создана).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS hero_knockouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id TEXT NOT NULL,
                    hand_idx INTEGER NOT NULL,
                    split BOOLEAN DEFAULT 0
                )
            """)
            conn.commit()

    def add_knockout(self, tournament_id, hand_idx, split=False):
        """
        Добавляет запись о KO Hero.
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO hero_knockouts (tournament_id, hand_idx, split)
                VALUES (?, ?, ?)
            """, (tournament_id, hand_idx, int(split)))
            conn.commit()

    def get_hero_knockouts(self, tournament_id=None):
        """
        Возвращает список KO Hero (по турниру или все).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            if tournament_id:
                c.execute("""
                    SELECT tournament_id, hand_idx, split
                    FROM hero_knockouts
                    WHERE tournament_id=?
                """, (tournament_id,))
            else:
                c.execute("""
                    SELECT tournament_id, hand_idx, split
                    FROM hero_knockouts
                """)
            rows = c.fetchall()
            return [
                {
                    "tournament_id": row[0],
                    "hand_idx": row[1],
                    "split": bool(row[2])
                } for row in rows
            ]
