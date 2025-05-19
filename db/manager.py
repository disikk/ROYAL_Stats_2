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
import threading
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
        
        # Получаем количество нокаутов в сессии из hero_knockouts или hero_tournaments
        tables = self.db_manager.get_table_names()
        knockouts_count = 0

        if 'hero_knockouts' in tables:
            knockouts_query = """
            SELECT COUNT(hk.id) as count
            FROM hero_knockouts hk
            JOIN tournaments t ON hk.tournament_id = t.tournament_id
            WHERE t.session_id = ?
            """
            result = self.db_manager.execute_query(knockouts_query, (session_id,))
            if result:
                knockouts_count = result[0]['count'] or 0
        elif 'hero_tournaments' in tables:
            knockouts_query = """
            SELECT SUM(ht.ko_count) as count
            FROM hero_tournaments ht
            JOIN tournaments t ON ht.tournament_id = t.tournament_id
            WHERE t.session_id = ?
            """
            result = self.db_manager.execute_query(knockouts_query, (session_id,))
            if result and result[0]['count'] is not None:
                knockouts_count = result[0]['count']
        
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


class ThreadLocalConnection:
    """
    Класс для создания потокобезопасных соединений с SQLite.
    Каждый поток получает свое собственное соединение с базой данных.
    """
    def __init__(self, db_path):
        """
        Инициализирует менеджер потокобезопасных соединений.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.local = threading.local()
    
    def get_connection(self):
        """
        Возвращает соединение SQLite для текущего потока.
        
        Returns:
            Соединение SQLite для текущего потока
        """
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            self.local.connection = sqlite3.connect(self.db_path)
            self.local.connection.row_factory = sqlite3.Row
            self.local.cursor = self.local.connection.cursor()
            current_thread = threading.current_thread()
            logger.debug(f"Создано новое соединение для потока {current_thread.name} (id: {current_thread.ident})")
        return self.local.connection
    
    def get_cursor(self):
        """
        Возвращает курсор SQLite для текущего потока.
        
        Returns:
            Курсор SQLite для текущего потока
        """
        connection = self.get_connection()
        if not hasattr(self.local, 'cursor') or self.local.cursor is None:
            self.local.cursor = connection.cursor()
        return self.local.cursor
    
    def close(self):
        """
        Закрывает соединение SQLite для текущего потока.
        """
        if hasattr(self.local, 'connection') and self.local.connection is not None:
            self.local.connection.close()
            self.local.connection = None
            self.local.cursor = None
            current_thread = threading.current_thread()
            logger.debug(f"Соединение закрыто для потока {current_thread.name} (id: {current_thread.ident})")
    
    def close_all(self):
        """
        Этот метод должен быть вызван перед удалением объекта,
        но он не может закрыть соединения в других потоках.
        """
        self.close()  # Закрываем соединение только в текущем потоке


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
            
        # Объявляем атрибуты для соединения и потокобезопасного хранилища
        self.conn_manager = None
        self.current_db_path = None
        
        # Репозитории для работы с данными
        self.session_repository = SessionRepositoryAdapter(self)
        self.tournament_repository = TournamentRepositoryAdapter(self)
        self.knockout_repository = KnockoutRepositoryAdapter(self)
        
    @property
    def connection(self):
        """
        Свойство для доступа к соединению SQLite для текущего потока.
        
        Returns:
            Соединение SQLite для текущего потока или None, если соединение не установлено
        """
        if self.conn_manager is not None:
            return self.conn_manager.get_connection()
        return None
        
    @property
    def cursor(self):
        """
        Свойство для доступа к курсору SQLite для текущего потока.
        
        Returns:
            Курсор SQLite для текущего потока или None, если соединение не установлено
        """
        if self.conn_manager is not None:
            return self.conn_manager.get_cursor()
        return None
        
    def connect(self, db_path: str, check_tables: bool = True) -> None:
        """
        Подключается к указанной базе данных.
        
        Args:
            db_path: Путь к файлу базы данных
            check_tables: Проверять и инициализировать таблицы, если отсутствуют
        """
        try:
            # Закрываем текущее соединение, если оно открыто
            self.close()
                
            # Создаем новый менеджер соединений
            self.conn_manager = ThreadLocalConnection(db_path)
            self.current_db_path = db_path
            
            # Получаем курсор из менеджера соединений
            cursor = self.cursor
            
            # Проверяем наличие необходимых таблиц и инициализируем БД при необходимости
            if check_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
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
        Закрывает соединение с базой данных в текущем потоке.
        """
        if self.conn_manager:
            try:
                self.conn_manager.close()
                logger.debug("Соединение с базой данных закрыто в текущем потоке")
            except Exception as e:
                logger.warning(f"Ошибка при закрытии соединения: {str(e)}")
        
        # Оставляем conn_manager и current_db_path без изменений,
        # чтобы другие потоки могли продолжать работу
        # Они будут удалены при следующем вызове connect
        
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
        if not self.conn_manager:
            raise ValueError("База данных не подключена")
            
        try:
            # Получаем соединение и курсор для текущего потока
            connection = self.connection
            cursor = self.cursor
            
            # Выполняем запрос
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            # Если запрос изменяет данные, фиксируем изменения
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                connection.commit()
                
            # Если запрос выбирает данные, возвращаем результаты
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
                
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
        if not self.conn_manager:
            raise ValueError("База данных не подключена")
            
        try:
            # Получаем соединение и курсор для текущего потока
            connection = self.connection
            cursor = self.cursor
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            connection.commit()
            return cursor.rowcount
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
        if not self.conn_manager:
            raise ValueError("База данных не подключена")
            
        try:
            # Получаем соединение и курсор для текущего потока
            connection = self.connection
            cursor = self.cursor
            
            cursor.executescript(script)
            connection.commit()
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
    
    def create_connection(self):
        """
        Создает новый потокобезопасный объект соединения с текущей базой данных.
        
        Returns:
            Новый объект ThreadLocalConnection для текущей базы данных
        """
        if not self.current_db_path:
            raise ValueError("Нет активной базы данных для создания соединения")
            
        # Создаем новый ThreadLocalConnection, который будет использоваться в потоке
        # Этот объект будет создавать отдельное соединение для каждого потока
        return ThreadLocalConnection(self.current_db_path)
        
    def set_connection(self, connection):
        """
        Устанавливает соединение для текущего потока через локальный объект ThreadLocalConnection.
        Это безопасная альтернатива прямому доступу к свойству connection.
        
        Args:
            connection: Объект соединения SQLite, который нужно установить
        """
        if not self.conn_manager:
            # Если соединение еще не было инициализировано, создаем новый ThreadLocalConnection
            if not self.current_db_path:
                raise ValueError("Нет активной базы данных для установки соединения")
            self.conn_manager = ThreadLocalConnection(self.current_db_path)
            
        # Устанавливаем соединение в локальный объект потока
        self.conn_manager.local.connection = connection
        self.conn_manager.local.cursor = connection.cursor()
        current_thread = threading.current_thread()
        logger.debug(f"Установлено новое соединение для потока {current_thread.name} (id: {current_thread.ident})")
    
    def begin_transaction(self):
        """
        Начинает новую транзакцию в текущем потоке.
        """
        if not self.conn_manager:
            raise ValueError("База данных не подключена")
            
        # Получаем соединение и курсор для текущего потока
        cursor = self.cursor
            
        # SQLite по умолчанию начинает транзакцию при первом изменении,
        # но мы можем явно начать транзакцию для согласованности
        cursor.execute("BEGIN TRANSACTION")
        current_thread = threading.current_thread()
        logger.debug(f"Транзакция начата в потоке {current_thread.name} (id: {current_thread.ident})")
        
    def commit(self):
        """
        Фиксирует текущую транзакцию в текущем потоке.
        """
        if not self.conn_manager:
            raise ValueError("База данных не подключена")
            
        # Получаем соединение для текущего потока
        connection = self.connection
            
        connection.commit()
        current_thread = threading.current_thread()
        logger.debug(f"Транзакция зафиксирована в потоке {current_thread.name} (id: {current_thread.ident})")
        
    def rollback(self):
        """
        Откатывает текущую транзакцию в текущем потоке.
        """
        if not self.conn_manager:
            raise ValueError("База данных не подключена")
            
        # Получаем соединение для текущего потока
        connection = self.connection
            
        connection.rollback()
        current_thread = threading.current_thread()
        logger.debug(f"Транзакция отменена в потоке {current_thread.name} (id: {current_thread.ident})")
    
    # Для обратной совместимости, делаем db_manager ссылаться на себя же
    @property
    def db_manager(self):
        """Для обратной совместимости с кодом, который ожидает репозиторий с атрибутом db_manager"""
        return self
    
    # Методы-прокси для прямого доступа к репозиториям
    def get_tournaments(self, session_id=None):
        """Прокси-метод для доступа к tournament_repository.get_tournaments"""
        if hasattr(self, 'tournament_repository'):
            return self.tournament_repository.get_tournaments(session_id)
        return []  # Возвращаем пустой список вместо исключения
    
    def get_knockouts(self, session_id=None):
        """Прокси-метод для доступа к knockout_repository.get_knockouts"""
        if hasattr(self, 'knockout_repository'):
            return self.knockout_repository.get_knockouts(session_id)
        return []  # Возвращаем пустой список вместо исключения
    
    def get_places_distribution(self, session_id=None):
        """Прокси-метод для доступа к tournament_repository.get_places_distribution"""
        if hasattr(self, 'tournament_repository'):
            return self.tournament_repository.get_places_distribution(session_id)
        return {i: 0 for i in range(1, 10)}  # Возвращаем пустое распределение
    
    def update_session_stats(self, session_id):
        """Прокси-метод для доступа к session_repository.update_session_stats"""
        if hasattr(self, 'session_repository'):
            return self.session_repository.update_session_stats(session_id)
        return False  # Возвращаем False вместо исключения
        
    def update_overall_statistics(self, session_id=None):
        """Метод для обновления общей статистики."""
        if hasattr(self, 'session_repository'):
            # Обновляем статистику для всех сессий, если session_id не указан
            return self.update_session_stats(session_id)
        return False
        
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