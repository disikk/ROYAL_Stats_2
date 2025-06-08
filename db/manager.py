# -*- coding: utf-8 -*-

"""
Менеджер базы данных для ROYAL_Stats (Hero-only).
Отвечает за подключение к базе данных, создание таблиц и управление соединениями.
Использует ThreadLocalConnection для потокобезопасности.
"""

import os
import sqlite3
import logging
import threading
from typing import Optional, List, Dict, Any

import config
import db.schema # Импортируем схему для создания таблиц

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.Database')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

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

    def get_connection(self) -> sqlite3.Connection:
        """
        Возвращает соединение SQLite для текущего потока.
        Создает новое, если для этого потока его еще нет.

        Returns:
            Соединение SQLite для текущего потока
        """
        # Проверяем, есть ли у текущего потока соединение, и активно ли оно
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            try:
                self.local.connection = sqlite3.connect(self.db_path, timeout=30.0)
                # Настройки для лучшей производительности и многопоточности
                self.local.connection.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging для параллельного чтения
                self.local.connection.execute("PRAGMA synchronous = NORMAL")  # Ускоряет запись, безопасно с WAL
                self.local.connection.execute("PRAGMA cache_size = -64000")  # 64MB кеша в памяти
                self.local.connection.execute("PRAGMA temp_store = MEMORY")  # Временные таблицы в памяти
                self.local.connection.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
                self.local.connection.execute("PRAGMA foreign_keys = ON")  # Включаем поддержку внешних ключей
                self.local.connection.row_factory = sqlite3.Row # Добавляем Row Factory
                self.local.cursor = self.local.connection.cursor()
                current_thread = threading.current_thread()
            except Exception as e:
                 logger.error(f"Не удалось создать соединение для потока {threading.current_thread().ident} к {self.db_path}: {e}")
                 self.local.connection = None
                 self.local.cursor = None
                 raise # Пробрасываем исключение дальше
        return self.local.connection

    def get_cursor(self) -> sqlite3.Cursor:
        """
        Возвращает курсор SQLite для текущего потока.
        """
        # Пытаемся получить соединение, что также гарантирует наличие курсора
        self.get_connection()
        return self.local.cursor


    def close_connection(self):
        """
        Закрывает соединение SQLite для текущего потока.
        """
        if hasattr(self.local, 'connection') and self.local.connection is not None:
            try:
                # Откатываем незавершенные транзакции перед закрытием
                try:
                    self.local.connection.rollback()
                except:
                    pass
                    
                self.local.connection.close()
                self.local.connection = None
                self.local.cursor = None
                current_thread = threading.current_thread()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии соединения в потоке {threading.current_thread().ident}: {str(e)}")


class DatabaseManager:
    """
    Класс для управления подключением к базе данных SQLite.
    Поддерживает переключение между файлами БД и инициализацию схемы.
    """

    def __init__(self):
        """
        Инициализирует менеджер БД.
        Путь к БД берется из config.DB_PATH при первом подключении.
        """
        self._db_path = config.DB_PATH # Текущий активный путь к БД
        self._conn_manager: Optional[ThreadLocalConnection] = None
        self._is_initialized = False # Флаг, показывающий, была ли инициализирована текущая БД

        # Убеждаемся, что папка для БД существует
        os.makedirs(config.DEFAULT_DB_DIR, exist_ok=True)

    @property
    def db_path(self) -> str:
        """Возвращает путь к текущей базе данных."""
        return self._db_path

    def set_db_path(self, new_db_path: str):
        """
        Устанавливает новый путь к базе данных и переподключается.
        Закрывает предыдущие соединения.
        """
        if self._db_path != new_db_path:
            logger.info(f"Переключение на базу данных: {new_db_path}")
            self.close_all_connections() # Закрываем все активные соединения перед сменой пути
            self._db_path = new_db_path
            self._conn_manager = None # Сбрасываем менеджер соединений
            self._is_initialized = False # Сбрасываем флаг инициализации
            config.set_db_path(new_db_path) # Сохраняем новый путь в конфиг


    def get_connection(self) -> sqlite3.Connection:
        """
        Возвращает соединение с текущей базой данных для текущего потока.
        Инициализирует базу при необходимости при первом обращении.
        """
        if self._conn_manager is None:
            # Создаем менеджер соединений при первом запросе
            self._conn_manager = ThreadLocalConnection(self._db_path)

        conn = self._conn_manager.get_connection()
        
        # Добавить отладку

        if not self._is_initialized:
             # При первом получении соединения для нового пути к БД,
             # проверяем и инициализируем схему.
             # Используем соединение текущего потока для инициализации.
             self.initialize_db(conn)
             self._is_initialized = True # Устанавливаем флаг после успешной инициализации

        return conn

    def close_connection(self):
        """Закрывает соединение для текущего потока."""
        if self._conn_manager:
            self._conn_manager.close_connection()

    def close_all_connections(self):
        """
        Пытается закрыть все потоко-локальные соединения.
        Это работает надежно только если вызывается из всех потоков,
        имеющих активные соединения. В контексте GUI, обычно достаточно
        закрыть соединение основного потока.
        """
        if self._conn_manager:
            # Закрываем соединение в текущем потоке
            self._conn_manager.close_connection()
            # В более сложных сценариях с фоновыми потоками, может потребоваться
            # механизм отслеживания и принудительного закрытия соединений
            # в других потоках, что усложнит ThreadLocalConnection.
            # Для данного приложения, закрытия в основном потоке должно быть достаточно.
            # Это скорее отладочный вывод, оставляем его только в режиме DEBUG
            logger.debug("Попытка закрыть все потоко-локальные соединения.")


    def execute_query(self, query: str, params=None) -> List[sqlite3.Row]:
        """Выполняет SELECT запрос и возвращает результат."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка выполнения SELECT запроса: {query} с параметрами {params}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # В зависимости от требуемой обработки ошибок, можно вернуть пустой список, None,
            # или пробросить исключение. Вернем пустой список.
            return []

    def execute_update(self, query: str, params=None) -> int:
        """Выполняет INSERT, UPDATE, DELETE запрос и возвращает кол-во измененных строк."""
        try:
            
            conn = self.get_connection()
            cursor = conn.cursor()
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            conn.commit()
            
            return cursor.rowcount
        except Exception as e:
            conn = self.get_connection() # Получаем соединение для текущего потока, чтобы откатить
            conn.rollback() # Откатываем изменения при ошибке
            logger.error(f"Ошибка выполнения UPDATE запроса: {query} с параметрами {params}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Пробрасываем исключение или обрабатываем иначе в зависимости от логики
            raise # Пробрасываем исключение
            return 0 # В случае проброса исключения, эта строка недостижима


    def get_available_databases(self) -> List[str]:
        """
        Возвращает список доступных баз данных в папке по умолчанию.
        
        Returns:
            Список путей к файлам баз данных SQLite (.db)
        """
        db_files = []
        try:
            # Проверяем существование директории
            if os.path.exists(config.DEFAULT_DB_DIR) and os.path.isdir(config.DEFAULT_DB_DIR):
                # Получаем список всех файлов с расширением .db
                for file_name in os.listdir(config.DEFAULT_DB_DIR):
                    if file_name.endswith('.db'):
                        full_path = os.path.join(config.DEFAULT_DB_DIR, file_name)
                        if os.path.isfile(full_path):
                            db_files.append(full_path)
                
            else:
                logger.warning(f"Директория {config.DEFAULT_DB_DIR} не существует или не является директорией")
                # Создаем директорию, если она не существует
                os.makedirs(config.DEFAULT_DB_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Ошибка при получении списка баз данных: {e}")
        
        return db_files
        
    def initialize_db(self, conn: sqlite3.Connection) -> None:
        """
        Инициализирует базу данных, создавая необходимые таблицы и начальные записи.
        Вызывается при первом подключении к новой или пустой БД.
        """
        try:
            cursor = conn.cursor()

            # Создаем все таблицы
            for query in db.schema.CREATE_TABLES_QUERIES:
                cursor.execute(query)

            # Вставляем начальные данные (overall_stats, places_distribution)
            for query in db.schema.INITIALIZATION_QUERIES:
                 cursor.execute(query)

            # Проверяем и добавляем новые колонки для существующих таблиц (миграции)
            # Проверяем наличие колонки final_table_start_players в таблице tournaments
            cursor.execute("PRAGMA table_info(tournaments)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'final_table_start_players' not in columns:
                cursor.execute("ALTER TABLE tournaments ADD COLUMN final_table_start_players INTEGER")
                # Отладочная информация о миграции схемы
                logger.debug("Добавлена колонка final_table_start_players в таблицу tournaments")
            
            # Проверяем наличие колонки hero_ko_attempts в таблице hero_final_table_hands
            cursor.execute("PRAGMA table_info(hero_final_table_hands)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'hero_ko_attempts' not in columns:
                cursor.execute("ALTER TABLE hero_final_table_hands ADD COLUMN hero_ko_attempts INTEGER DEFAULT 0")
                logger.debug("Добавлена колонка hero_ko_attempts в таблицу hero_final_table_hands")
            
            # Обновление индексов для существующих БД
            self._update_indexes(cursor)

            conn.commit()
            logger.info(f"База данных успешно инициализирована: {self._db_path}")

        except Exception as e:
            conn.rollback() # Откатываем все изменения при ошибке
            logger.critical(f"Критическая ошибка при инициализации базы данных {self._db_path}: {str(e)}")
            # В реальном приложении здесь можно показать сообщение пользователю
            # и, возможно, завершить работу или предложить выбрать другую БД.
            raise # Пробрасываем исключение, так как работа без схемы невозможна
    
    def _update_indexes(self, cursor: sqlite3.Cursor) -> None:
        """
        Проверяет и создает недостающие индексы для оптимизации производительности.
        Безопасно для выполнения на существующих БД - CREATE INDEX IF NOT EXISTS.
        """
        try:
            # Получаем список существующих индексов
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            existing_indexes = set(row[0] for row in cursor.fetchall())
            
            # Подсчитываем созданные индексы
            created_indexes = 0
            
            # Создаем недостающие индексы
            for index_query in db.schema.CREATE_INDEXES:
                # Извлекаем имя индекса из запроса
                index_name = index_query.split("IF NOT EXISTS ")[1].split(" ON")[0].strip()
                
                if index_name not in existing_indexes:
                    try:
                        cursor.execute(index_query)
                        created_indexes += 1
                        logger.debug(f"Создан индекс: {index_name}")
                    except sqlite3.Error as e:
                        # Если индекс уже существует под другим именем или есть другая проблема
                        logger.warning(f"Не удалось создать индекс {index_name}: {e}")
            
            if created_indexes > 0:
                logger.info(f"Создано {created_indexes} новых индексов для оптимизации производительности")
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении индексов: {e}")
            # Не прерываем инициализацию БД из-за проблем с индексами


# Синглтон менеджер БД
# Гарантируем, что в приложении будет только один экземпляр DatabaseManager
# Это упрощает управление соединениями и переключение между БД.
database_manager = DatabaseManager()
