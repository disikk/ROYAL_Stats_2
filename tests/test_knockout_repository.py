import unittest
from db.database import DatabaseManager
from db.repositories.knockout_repo import KnockoutRepository

class TestKnockoutRepository(unittest.TestCase):
    def setUp(self):
        import tempfile
        # Use temporary file-based database so connections share state
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.repo = KnockoutRepository(self.db_manager)

    def tearDown(self):
        import os
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass

    def test_unique_constraint_on_add(self):
        # Insert the same knockout twice
        self.repo.add_knockout('T1', 1, split=False)
        self.repo.add_knockout('T1', 1, split=False)

        with self.db_manager.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM hero_knockouts")
            count = c.fetchone()[0]

        self.assertEqual(count, 1)

if __name__ == '__main__':
    unittest.main()
