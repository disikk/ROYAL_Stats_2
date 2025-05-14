#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилита для создания новой базы данных.
"""

from db.manager import DatabaseManager

def create_database():
    """
    Создает новую базу данных с именем по умолчанию.
    """
    # Создаем экземпляр менеджера БД
    db_manager = DatabaseManager("databases")
    
    # Создаем новую БД
    db_path = db_manager.create_database("default.db")
    
    # Инициализируем БД (создаем таблицы)
    db_manager.initialize_db(db_path)
    
    print(f"База данных успешно создана и инициализирована по пути: {db_path}")
    
if __name__ == "__main__":
    create_database()