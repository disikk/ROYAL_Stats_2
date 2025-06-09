# -*- coding: utf-8 -*-

"""
Базовый класс для всех репозиториев.
Содержит общую логику работы с базой данных.
"""

from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, List, Any
import logging

from db.manager import DatabaseManager, database_manager

logger = logging.getLogger('ROYAL_Stats.BaseRepository')

# Тип для модели данных
T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Базовый класс для всех репозиториев.
    Предоставляет общий функционал для работы с БД.
    """
    
    def __init__(self, db_manager: DatabaseManager = database_manager):
        """Инициализация базового репозитория."""
        self._db_manager = db_manager
        self._logger = logging.getLogger(f'ROYAL_Stats.{self.__class__.__name__}')
    
    @property
    def db_manager(self):
        """Возвращает менеджер базы данных."""
        return self._db_manager
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """
        Выполняет SELECT запрос и возвращает результаты.
        
        Args:
            query: SQL запрос
            params: Параметры для запроса
            
        Returns:
            Список кортежей с результатами
        """
        try:
            with self._db_manager.connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            self._logger.error(f"Ошибка выполнения запроса: {e}")
            self._logger.error(f"Запрос: {query}")
            self._logger.error(f"Параметры: {params}")
            raise
    
    def execute_command(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Выполняет INSERT/UPDATE/DELETE запрос.
        
        Args:
            query: SQL запрос
            params: Параметры для запроса
            
        Returns:
            Количество затронутых строк
        """
        try:
            with self._db_manager.connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            self._logger.error(f"Ошибка выполнения команды: {e}")
            self._logger.error(f"Запрос: {query}")
            self._logger.error(f"Параметры: {params}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Выполняет множественный INSERT/UPDATE.
        
        Args:
            query: SQL запрос
            params_list: Список параметров для запроса
            
        Returns:
            Количество затронутых строк
        """
        try:
            with self._db_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            self._logger.error(f"Ошибка выполнения executemany: {e}")
            self._logger.error(f"Запрос: {query}")
            self._logger.error(f"Количество записей: {len(params_list)}")
            raise
    
    def execute_scalar(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Выполняет запрос и возвращает единственное значение.
        
        Args:
            query: SQL запрос
            params: Параметры для запроса
            
        Returns:
            Скалярное значение или None
        """
        result = self.execute_query(query, params)
        if result and result[0]:
            return result[0][0]
        return None
    
    @abstractmethod
    def _row_to_model(self, row: tuple) -> T:
        """
        Преобразует строку из БД в модель.
        Должен быть реализован в наследниках.
        
        Args:
            row: Кортеж с данными из БД
            
        Returns:
            Экземпляр модели
        """
        raise NotImplementedError
    
    def _rows_to_models(self, rows: List[tuple]) -> List[T]:
        """
        Преобразует множество строк в список моделей.
        
        Args:
            rows: Список кортежей из БД
            
        Returns:
            Список моделей
        """
        return [self._row_to_model(row) for row in rows]