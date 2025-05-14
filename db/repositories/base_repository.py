#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый класс репозитория для ROYAL_Stats.
Предоставляет общие методы для всех репозиториев.
"""

import logging
from typing import List, Dict, Any, Optional

class BaseRepository:
    """
    Базовый класс для всех репозиториев.
    Обеспечивает общую функциональность для работы с таблицами БД.
    """
    
    def __init__(self, db_manager):
        """
        Инициализирует репозиторий.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f'ROYAL_Stats.Repository.{self.__class__.__name__}')
        
    def execute_query(self, query: str, params=None) -> List[Dict]:
        """
        Выполняет запрос к базе данных.
        
        Args:
            query: SQL запрос
            params: Параметры запроса (опционально)
            
        Returns:
            Результат запроса
        """
        if not self.db_manager.connection:
            raise ValueError("База данных не подключена")
            
        try:
            result = self.db_manager.execute_query(query, params)
            if result:
                # Преобразуем sqlite3.Row в словари
                return [dict(row) for row in result]
            return []
        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    def execute_insert(self, query: str, params=None) -> Optional[int]:
        """
        Выполняет запрос на вставку данных.
        
        Args:
            query: SQL запрос на вставку
            params: Параметры запроса
            
        Returns:
            ID вставленной записи или None
        """
        if not self.db_manager.connection:
            raise ValueError("База данных не подключена")
            
        try:
            self.db_manager.execute_query(query, params)
            return self.db_manager.cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса вставки: {e}")
            raise
    
    def execute_update(self, query: str, params=None) -> int:
        """
        Выполняет запрос на обновление данных.
        
        Args:
            query: SQL запрос на обновление
            params: Параметры запроса
            
        Returns:
            Количество обновленных строк
        """
        if not self.db_manager.connection:
            raise ValueError("База данных не подключена")
            
        try:
            self.db_manager.execute_query(query, params)
            return self.db_manager.cursor.rowcount
        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса обновления: {e}")
            raise
    
    def execute_delete(self, query: str, params=None) -> int:
        """
        Выполняет запрос на удаление данных.
        
        Args:
            query: SQL запрос на удаление
            params: Параметры запроса
            
        Returns:
            Количество удаленных строк
        """
        if not self.db_manager.connection:
            raise ValueError("База данных не подключена")
            
        try:
            self.db_manager.execute_query(query, params)
            return self.db_manager.cursor.rowcount
        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса удаления: {e}")
            raise
    
    def get_by_id(self, table: str, id_value: int) -> Optional[Dict]:
        """
        Получает запись по ID.
        
        Args:
            table: Название таблицы
            id_value: Значение ID
            
        Returns:
            Словарь с данными записи или None
        """
        query = f"SELECT * FROM {table} WHERE id = ?"
        result = self.execute_query(query, (id_value,))
        return result[0] if result else None
    
    def get_all(self, table: str, order_by: str = None) -> List[Dict]:
        """
        Получает все записи из таблицы.
        
        Args:
            table: Название таблицы
            order_by: Поле для сортировки (опционально)
            
        Returns:
            Список словарей с данными записей
        """
        query = f"SELECT * FROM {table}"
        if order_by:
            query += f" ORDER BY {order_by}"
            
        return self.execute_query(query)
    
    def count(self, table: str, condition: str = None, params = None) -> int:
        """
        Подсчитывает количество записей в таблице.
        
        Args:
            table: Название таблицы
            condition: Условие WHERE (опционально)
            params: Параметры для условия (опционально)
            
        Returns:
            Количество записей
        """
        query = f"SELECT COUNT(*) as count FROM {table}"
        if condition:
            query += f" WHERE {condition}"
            
        result = self.execute_query(query, params)
        return result[0]['count'] if result else 0