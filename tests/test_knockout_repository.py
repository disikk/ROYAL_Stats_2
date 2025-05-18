import os
import tempfile
import unittest

from db.database import DatabaseManager
from db.repositories.knockout_repo import KnockoutRepository

class TestKnockoutRepository(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp()
        os.close(fd)
        self.manager = DatabaseManager(self.db_path)
        self.repo = KnockoutRepository(self.manager)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def test_insert_ignore_duplicates(self):
        self.repo.add_knockout("T1", 1)
        self.repo.add_knockout("T1", 1)  # duplicate should be ignored
        kos = self.repo.get_hero_knockouts("T1")
        self.assertEqual(len(kos), 1)

if __name__ == "__main__":
    unittest.main()
