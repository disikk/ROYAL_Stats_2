"""
Репозиторий турниров Hero. Работает через DatabaseManager.
"""

class TournamentRepository:
    """
    Хранит и отдаёт инфу о турнирах только по Hero.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self._ensure_table()

    def _ensure_table(self):
        """
        Создаёт таблицу hero_tournaments (если не создана).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS hero_tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id TEXT UNIQUE NOT NULL,
                    place INTEGER NOT NULL,
                    payout REAL NOT NULL,
                    buyin REAL NOT NULL,
                    ko_count INTEGER NOT NULL,
                    date TEXT
                )
            """)
            # Ensure 'date' column exists (for old DB versions)
            c.execute("PRAGMA table_info(hero_tournaments)")
            cols = [r[1] for r in c.fetchall()]
            if 'date' not in cols:
                try:
                    c.execute("ALTER TABLE hero_tournaments ADD COLUMN date TEXT")
                    conn.commit() # Commit alter table
                except Exception as e:
                    # Handle potential error, e.g. table being locked, though less likely here.
                    print(f"Error adding date column: {e}")
            conn.commit()

    def add_or_update_tournament(self, tournament_id, place, payout, buyin, ko_count, date=None):
        """
        Добавляет или обновляет запись по турниру (Hero-only).
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            # Ensure 'date' column exists (for old DB versions)
            c.execute("PRAGMA table_info(hero_tournaments)")
            cols = [r[1] for r in c.fetchall()]
            if 'date' not in cols:
                try:
                    c.execute("ALTER TABLE hero_tournaments ADD COLUMN date TEXT")
                except Exception:
                    pass
            c.execute("""
                INSERT INTO hero_tournaments (tournament_id, place, payout, buyin, ko_count, date)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tournament_id)
                DO UPDATE SET
                    place=excluded.place,
                    payout=excluded.payout,
                    buyin=excluded.buyin,
                    ko_count=excluded.ko_count,
                    date=COALESCE(excluded.date, hero_tournaments.date)
            """, (tournament_id, place, payout, buyin, ko_count, date))
            conn.commit()

    def get_hero_tournament(self, tournament_id):
        """
        Возвращает данные Hero по одному турниру.
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT place, payout, buyin, ko_count, date
                FROM hero_tournaments
                WHERE tournament_id=?
            """, (tournament_id,))
            row = c.fetchone()
            if row:
                return {
                    "tournament_id": tournament_id,
                    "place": row[0],
                    "payout": row[1],
                    "buyin": row[2],
                    "ko_count": row[3],
                    "date": row[4],
                }
            return None

    def get_all_hero_tournaments(self):
        """
        Возвращает список всех турниров Hero.
        """
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT tournament_id, place, payout, buyin, ko_count, date
                FROM hero_tournaments
            """)
            rows = c.fetchall()
            return [
                {
                    "tournament_id": row[0],
                    "place": row[1],
                    "payout": row[2],
                    "buyin": row[3],
                    "ko_count": row[4],
                    "date": row[5],
                } for row in rows
            ]
