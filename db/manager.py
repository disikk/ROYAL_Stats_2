#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер базы данных для ROYAL_Stats.
Отвечает за подключение к базе данных, создание таблиц и управление соединениями.
"""

import os
import sqlite3
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.Database')


# Адаптеры репозиториев
class SessionRepositoryAdapter:
    """Адаптер для работы с сессиями через DatabaseManager"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all_sessions(self) -> List[Dict]:
        """Возвращает список всех сессий"""
        if not self.db_manager.is_connected():
            return []
            
        query = "SELECT * FROM sessions ORDER BY created_at DESC"
        return self.db_manager.execute_query(query) or []
    
    def create_session(self, session_name: str) -> str:
        """Создает новую сессию и возвращает ее ID"""
        if not self.db_manager.is_connected():
            raise ValueError("База данных не подключена")
            
        session_id = str(uuid.uuid4())
        query = """
        INSERT INTO sessions (
            id, session_id, session_name, tournaments_count, knockouts_count,
            avg_finish_place, total_prize, avg_initial_stack
        ) VALUES (?, ?, ?, 0, 0, 0.0, 0.0, 0.0)
        """
        
        self.db_manager.execute_query(query, (session_id, session_id, session_name))
        return session_id
    
    def update_session_stats(self, session_id: str) -> bool:
        """Обновляет статистику сессии"""
        if not self.db_manager.is_connected():
            return False
            
        # Получаем количество турниров в сессии
        tournaments_query = "SELECT COUNT(*) as count FROM tournaments WHERE session_id = ?"
        tournaments_result = self.db_manager.execute_query(tournaments_query, (session_id,))
        tournaments_count = tournaments_result[0]['count'] if tournaments_result else 0
        
        # Получаем количество нокаутов в сессии
        knockouts_query = "SELECT COUNT(*) as count FROM knockouts WHERE session_id = ?"
        knockouts_result = self.db_manager.execute_query(knockouts_query, (session_id,))
        knockouts_count = knockouts_result[0]['count'] if knockouts_result else 0
        
        # Рассчитываем среднее место
        avg_place_query = """
        SELECT AVG(finish_place) as avg_place 
        FROM tournaments 
        WHERE session_id = ? AND finish_place IS NOT NULL
        """
        avg_place_result = self.db_manager.execute_query(avg_place_query, (session_id,))
        avg_finish_place = avg_place_result[0]['avg_place'] if avg_place_result and avg_place_result[0]['avg_place'] is not None else 0.0
        
        # Получаем общий выигрыш
        prize_query = "SELECT SUM(prize) as total FROM tournaments WHERE session_id = ? AND prize IS NOT NULL"
        prize_result = self.db_manager.execute_query(prize_query, (session_id,))
        total_prize = prize_result[0]['total'] if prize_result and prize_result[0]['total'] is not None else 0.0
        
        # Получаем общую сумму бай-инов
        buyin_query = """
        SELECT SUM(total_buy_in) as total 
        FROM tournaments 
        WHERE session_id = ? AND total_buy_in IS NOT NULL
        """
        buyin_result = self.db_manager.execute_query(buyin_query, (session_id,))
        total_buy_in = buyin_result[0]['total'] if buyin_result and buyin_result[0]['total'] is not None else 0.0
        
        # Получаем средний начальный стек
        stack_query = """
        SELECT AVG(average_initial_stack) as avg_stack 
        FROM tournaments 
        WHERE session_id = ? AND average_initial_stack IS NOT NULL AND average_initial_stack > 0
        """
        stack_result = self.db_manager.execute_query(stack_query, (session_id,))
        avg_initial_stack = stack_result[0]['avg_stack'] if stack_result and stack_result[0]['avg_stack'] is not None else 0.0
        
        # Обновляем статистику сессии
        update_query = """
        UPDATE sessions SET
            tournaments_count = ?,
            knockouts_count = ?,
            avg_finish_place = ?,
            total_prize = ?,
            avg_initial_stack = ?,
            total_buy_in = ?
        WHERE session_id = ?
        """
        
        params = (
            tournaments_count, 
            knockouts_count, 
            avg_finish_place, 
            total_prize, 
            avg_initial_stack,
            total_buy_in,
            session_id
        )
        
        self.db_manager.execute_query(update_query, params)
        return True
    
    def get_stat_modules(self, enabled_only: bool = False) -> List[Dict]:
        """
        Получает список зарегистрированных модулей статистики.
        
        Args:
            enabled_only: Возвращать только включенные модули
            
        Returns:
            Список словарей с информацией о модулях
        """
        if not self.db_manager.is_connected():
            return []
            
        query = "SELECT * FROM stat_modules"
        
        if enabled_only:
            query += " WHERE enabled = 1"
            
        query += " ORDER BY position"
        
        return self.db_manager.execute_query(query) or []
    
    def register_stat_module(self, name: str, display_name: str, enabled: bool = True, position: int = 0) -> Optional[int]:
        """
        Регистрирует модуль статистики в базе данных.
        
        Args:
            name: Уникальное имя модуля
            display_name: Отображаемое имя
            enabled: Включен ли модуль
            position: Позиция в UI
            
        Returns:
            ID модуля или None в случае ошибки
        """
        if not self.db_manager.is_connected():
            return None
            
        query = """
        INSERT INTO stat_modules (name, display_name, enabled, position)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            display_name = excluded.display_name,
            enabled = excluded.enabled,
            position = excluded.position
        """
        
        try:
            self.db_manager.execute_query(query, (name, display_name, 1 if enabled else 0, position))
            
            # Получаем ID модуля
            id_query = "SELECT id FROM stat_modules WHERE name = ?"
            result = self.db_manager.execute_query(id_query, (name,))
            return result[0]['id'] if result else None
        except Exception as e:
            logger.error(f"Ошибка при регистрации модуля статистики {name}: {e}")
            return None


class TournamentRepositoryAdapter:
    """Адаптер для работы с турнирами через DatabaseManager"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_tournaments(self, session_id: Optional[str] = None) -> List[Dict]:
        """Возвращает список турниров, опционально фильтруя по сессии"""
        if not self.db_manager.is_connected():
            return []
            
        query = "SELECT * FROM tournaments"
        params = None
        
        if session_id:
            query += " WHERE session_id = ?"
            params = (session_id,)
            
        query += " ORDER BY start_time DESC"
        
        return self.db_manager.execute_query(query, params) or []
    
    def get_places_distribution(self, session_id: Optional[str] = None) -> Dict[int, int]:
        """Возвращает распределение мест в турнирах"""
        if not self.db_manager.is_connected():
            return {i: 0 for i in range(1, 10)}
            
        if session_id:
            # Распределение мест для конкретной сессии
            query = """
            SELECT finish_place as place, COUNT(*) as count 
            FROM tournaments 
            WHERE session_id = ? AND finish_place BETWEEN 1 AND 9
            GROUP BY finish_place
            ORDER BY finish_place
            """
            result = self.db_manager.execute_query(query, (session_id,))
        else:
            # Общее распределение мест
            query = """
            SELECT place, count 
            FROM places_distribution 
            ORDER BY place
            """
            result = self.db_manager.execute_query(query)
        
        # Преобразуем результат в словарь
        distribution = {i: 0 for i in range(1, 10)}
        if result:
            for row in result:
                place = row['place']
                if 1 <= place <= 9:
                    distribution[place] = row['count']
        
        return distribution


class KnockoutRepositoryAdapter:
    """Адаптер для работы с нокаутами через DatabaseManager"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_knockouts(self, session_id: Optional[str] = None) -> List[Dict]:
        """Возвращает список нокаутов, опционально фильтруя по сессии"""
        if not self.db_manager.is_connected():
            return []
            
        query = "SELECT * FROM knockouts"
        params = None
        
        if session_id:
            query += " WHERE session_id = ?"
            params = (session_id,)
            
        return self.db_manager.execute_query(query, params) or []


class DatabaseManager:
    """
    Класс для управления подключением к базе данных SQLite.
    """
    
    def __init__(self, db_folder='databases'):
        """
        Инициализирует менеджер БД.
        
        Args:
            db_folder: Путь к папке с базами данных
        """
        # Путь к папке с БД
        self.db_folder = db_folder
        
        # Создаем папку, если она не существует
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
            
        # Объявляем атрибуты для соединения и курсора
        self.connection = None
        self.cursor = None
        self.current_db_path = None
        
        # Репозитории для работы с данными
        self.session_repository = SessionRepositoryAdapter(self)
        self.tournament_repository = TournamentRepositoryAdapter(self)
        self.knockout_repository = KnockoutRepositoryAdapter(self)
        
    def connect(self, db_path: str, check_tables: bool = True) -> None:
        """
        Подключается к указанной базе данных.
        
        Args:
            db_path: Путь к файлу базы данных
            check_tables: Проверять и инициализировать таблицы, если отсутствуют
        """
        try:
            # Закрываем текущее соединение, если оно открыто
            if self.connection:
                self.close()
                
            # Создаем новое соединение
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row  # Для доступа к результатам по имени столбца
            self.cursor = self.connection.cursor()
            self.current_db_path = db_path
            
            # Проверяем наличие необходимых таблиц и инициализируем БД при необходимости
            if check_tables:
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in self.cursor.fetchall()]
                required_tables = ['sessions', 'tournaments', 'knockouts', 'places_distribution']
                
                # Если нет всех необходимых таблиц, инициализируем БД
                if not all(table in tables for table in required_tables):
                    logger.info(f"Инициализация базы данных: {db_path}")
                    self.initialize_db(db_path)
            
            logger.info(f"Подключено к базе данных: {db_path}")
        except Exception as e:
            logger.error(f"Ошибка при подключении к БД {db_path}: {str(e)}")
            raise
            
    def close(self) -> None:
        """
        Закрывает соединение с базой данных.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            self.current_db_path = None
            logger.debug("Соединение с базой данных закрыто")
        
    def create_database(self, db_name: str) -> str:
        """
        Создает новую базу данных с указанным именем.
        
        Args:
            db_name: Имя новой базы данных
            
        Returns:
            Путь к созданной базе данных
        """
        # Формируем путь к новой БД
        db_path = os.path.join(self.db_folder, db_name)
        
        try:
            # Создаем пустое соединение без проверки таблиц
            self.connect(db_path, check_tables=False)
            
            # Инициализируем БД (создаем таблицы)
            self.initialize_db(db_path)
            
            # Возвращаем путь к БД
            return db_path
        except Exception as e:
            logger.error(f"Ошибка при создании базы данных {db_name}: {str(e)}")
            raise
        
    def get_available_databases(self) -> List[str]:
        """
        Возвращает список доступных баз данных в папке.
        
        Returns:
            Список имен файлов баз данных
        """
        # Проверяем наличие папки
        if not os.path.exists(self.db_folder):
            return []
            
        # Получаем список файлов .db в папке
        db_files = []
        for file_name in os.listdir(self.db_folder):
            if file_name.endswith('.db'):
                db_files.append(file_name)
                
        return db_files
    
    def execute_query(self, query: str, params=None):
        """
        Выполняет запрос к базе данных.
        
        Args:
            query: SQL запрос
            params: Параметры запроса (опционально)
            
        Returns:
            Результат запроса
        """
        if not self.connection:
            raise ValueError("База данных не подключена")
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            # Если запрос изменяет данные, фиксируем изменения
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                self.connection.commit()
                
            # Если запрос выбирает данные, возвращаем результаты
            if query.strip().upper().startswith("SELECT"):
                return self.cursor.fetchall()
                
            return None
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
            
    def execute_update(self, query: str, params=None) -> int:
        """
        Выполняет запрос на обновление данных и возвращает количество затронутых строк.
        
        Args:
            query: SQL запрос (INSERT, UPDATE, DELETE)
            params: Параметры запроса (опционально)
            
        Returns:
            Количество затронутых строк
        """
        if not self.connection:
            raise ValueError("База данных не подключена")
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            self.connection.commit()
            return self.cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса обновления: {e}")
            raise
    
    def execute_script(self, script: str):
        """
        Выполняет SQL скрипт.
        
        Args:
            script: SQL скрипт
            
        Returns:
            None
        """
        if not self.connection:
            raise ValueError("База данных не подключена")
            
        try:
            self.cursor.executescript(script)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Ошибка выполнения скрипта: {e}")
            raise
    
    def create_tables(self, table_queries: List[str]) -> None:
        """
        Создает таблицы в базе данных, если их нет.
        
        Args:
            table_queries: Список SQL запросов для создания таблиц
        """
        if not self.connection:
            raise ValueError("База данных не подключена")
            
        try:
            for query in table_queries:
                self.cursor.execute(query)
                
            self.connection.commit()
            logger.debug("Таблицы успешно созданы/проверены")
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise

    def get_table_names(self) -> List[str]:
        """
        Возвращает список имен таблиц в текущей БД.
        
        Returns:
            Список имен таблиц
        """
        if not self.connection:
            return []
            
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = self.cursor.fetchall()
            return [table[0] for table in tables]
        except Exception as e:
            logger.error(f"Ошибка при получении списка таблиц: {e}")
            return []
            
    def is_connected(self) -> bool:
        """
        Проверяет, активно ли соединение с базой данных.
        
        Returns:
            True, если соединение активно, иначе False
        """
        return self.connection is not None
        
    def initialize_db(self, db_path: str) -> None:
        """
        Инициализирует базу данных, создавая необходимые таблицы.
        
        Args:
            db_path: Путь к базе данных
        """
        try:
            # Убираем повторный вызов connect, т.к. соединение уже должно быть установлено
            # к моменту вызова этого метода
            
            # Определяем структуру таблиц
            table_queries = [
                # Таблица сессий
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    session_id TEXT UNIQUE,
                    session_name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    tournaments_count INTEGER DEFAULT 0,
                    knockouts_count INTEGER DEFAULT 0,
                    avg_finish_place REAL DEFAULT 0,
                    total_prize REAL DEFAULT 0,
                    avg_initial_stack REAL DEFAULT 0,
                    total_buy_in REAL DEFAULT 0
                )
                """,
                
                # Таблица турниров
                """
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id TEXT NOT NULL,
                    tournament_name TEXT,
                    game_type TEXT DEFAULT 'No Limit Hold''em',
                    buy_in REAL DEFAULT 0,
                    fee REAL DEFAULT 0,
                    bounty REAL DEFAULT 0,
                    total_buy_in REAL DEFAULT 0,
                    players_count INTEGER DEFAULT 9,
                    prize_pool REAL DEFAULT 0,
                    prize REAL DEFAULT 0,
                    finish_place INTEGER,
                    session_id TEXT,
                    start_time TEXT,
                    average_initial_stack REAL DEFAULT 0,
                    knockouts_x2 INTEGER DEFAULT 0,
                    knockouts_x10 INTEGER DEFAULT 0,
                    knockouts_x100 INTEGER DEFAULT 0,
                    knockouts_x1000 INTEGER DEFAULT 0,
                    knockouts_x10000 INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """,
                
                # Таблица нокаутов
                """
                CREATE TABLE IF NOT EXISTS knockouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id TEXT,
                    hand_id TEXT,
                    knocked_out_player TEXT,
                    pot_size INTEGER,
                    multi_knockout BOOLEAN,
                    session_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """,
                
                # Таблица распределения мест
                """
                CREATE TABLE IF NOT EXISTS places_distribution (
                    place INTEGER PRIMARY KEY,
                    count INTEGER DEFAULT 0
                )
                """,
                
                # Таблица кэша статистики
                """
                CREATE TABLE IF NOT EXISTS stats_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    value TEXT,
                    updated_at TEXT
                )
                """,
                
                # Таблица модулей статистики
                """
                CREATE TABLE IF NOT EXISTS stat_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    display_name TEXT,
                    enabled INTEGER DEFAULT 1,
                    position INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                
                # Таблица статистики
                """
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY,
                    total_tournaments INTEGER DEFAULT 0,
                    total_knockouts INTEGER DEFAULT 0,
                    total_knockouts_x2 INTEGER DEFAULT 0,
                    total_knockouts_x10 INTEGER DEFAULT 0,
                    total_knockouts_x100 INTEGER DEFAULT 0,
                    total_knockouts_x1000 INTEGER DEFAULT 0,
                    total_knockouts_x10000 INTEGER DEFAULT 0,
                    avg_finish_place REAL DEFAULT 0,
                    first_places INTEGER DEFAULT 0,
                    second_places INTEGER DEFAULT 0,
                    third_places INTEGER DEFAULT 0,
                    total_prize REAL DEFAULT 0,
                    avg_initial_stack REAL DEFAULT 0,
                    total_buy_in REAL DEFAULT 0,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]
            
            # Создаем таблицы
            self.create_tables(table_queries)
            
            # Создаем таблицу настроек модулей
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS module_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER,
                key TEXT,
                value TEXT,
                FOREIGN KEY (module_id) REFERENCES stat_modules(id),
                UNIQUE(module_id, key)
            )
            """)
            
            # Вставляем начальную запись в таблицу статистики, если её нет
            self.cursor.execute("""
            INSERT OR IGNORE INTO statistics (id, total_tournaments, total_knockouts)
            VALUES (1, 0, 0)
            """)
            self.connection.commit()
            
            # Инициализируем таблицу распределения мест
            for place in range(1, 10):
                self.cursor.execute("""
                INSERT OR IGNORE INTO places_distribution (place, count)
                VALUES (?, 0)
                """, (place,))
            self.connection.commit()
            
            # Создаем таблицу кэша статистики, если её нет
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            self.connection.commit()
            
            logger.info(f"База данных успешно инициализирована: {db_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
            raise