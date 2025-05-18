"""
Менеджер работы с БД для Royal Stats (Hero-only).
Централизует соединения, можно расширять под миграции и транзакции.
"""

import sqlite3

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        """
        Открывает новое соединение с БД.
        """
        return sqlite3.connect(self.db_path)
