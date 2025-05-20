#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для получения статистики нокаутов из базы данных ROYAL_Stats.
Использование: python ko_counter.py <имя_файла_бд>
"""

import sqlite3
import sys
import os

def get_knockouts_stats(db_path):
    """
    Получает статистику нокаутов из указанной БД.
    
    Args:
        db_path: Путь к файлу базы данных SQLite
        
    Returns:
        dict: Статистика по нокаутам
    """
    conn = None
    try:
        # Подключаемся к БД
        conn = sqlite3.connect(db_path)
        # Устанавливаем тип row_factory, чтобы получать данные как словари
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем, какая таблица с нокаутами есть в БД
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('hero_knockouts', 'knockouts')")
        tables = [row['name'] for row in cursor.fetchall()]
        
        ko_stats = {"total_ko": 0, "tournaments": {}}
        
        if 'hero_knockouts' in tables:
            # Используем таблицу hero_knockouts (Hero-only вариант)
            # Общее количество нокаутов
            cursor.execute("SELECT COUNT(*) AS count FROM hero_knockouts")
            ko_stats['total_ko'] = cursor.fetchone()['count']
            
            # По турнирам
            cursor.execute("""
                SELECT tournament_id, COUNT(*) as ko_count 
                FROM hero_knockouts 
                GROUP BY tournament_id
                ORDER BY ko_count DESC
            """)
            tournaments = [dict(row) for row in cursor.fetchall()]
            for t in tournaments:
                ko_stats['tournaments'][t['tournament_id']] = t['ko_count']
                
            # Проверяем есть ли столбец split
            cursor.execute("PRAGMA table_info(hero_knockouts)")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'split' in columns:
                cursor.execute("SELECT COUNT(*) as count FROM hero_knockouts WHERE split=1")
                ko_stats['split_ko'] = cursor.fetchone()['count']
                
        elif 'knockouts' in tables:
            # Используем таблицу knockouts (общая версия)
            # Вариант 1: подсчет всех нокаутов во всех сессиях
            cursor.execute("SELECT COUNT(*) AS count FROM knockouts")
            ko_stats['total_ko'] = cursor.fetchone()['count']
            
            # По турнирам
            cursor.execute("""
                SELECT tournament_id, COUNT(*) as ko_count 
                FROM knockouts 
                GROUP BY tournament_id
                ORDER BY ko_count DESC
            """)
            tournaments = [dict(row) for row in cursor.fetchall()]
            for t in tournaments:
                ko_stats['tournaments'][t['tournament_id']] = t['ko_count']
        else:
            ko_stats['error'] = "В базе данных не найдены таблицы с нокаутами"
        
        # Дополнительно: проверяем таблицу статистики
        for table_name in ['statistics', 'hero_stats']:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                stats_row = cursor.fetchone()
                if stats_row and 'total_knockouts' in stats_row.keys():
                    ko_stats['stats_total_ko'] = stats_row['total_knockouts']
                break
        
        return ko_stats
            
    except sqlite3.Error as e:
        return {"error": f"Ошибка SQLite: {e}"}
    except Exception as e:
        return {"error": f"Ошибка: {e}"}
    finally:
        if conn:
            conn.close()

def main():
    # Проверяем аргументы командной строки
    if len(sys.argv) != 2:
        print("Использование: python ko_counter.py <имя_файла_бд>")
        sys.exit(1)
    
    # Получаем имя файла БД и проверяем его наличие
    db_filename = sys.argv[1]
    if not os.path.exists(db_filename):
        print(f"Ошибка: файл {db_filename} не найден")
        sys.exit(1)
    
    # Получаем статистику нокаутов
    ko_stats = get_knockouts_stats(db_filename)
    
    # Проверяем на ошибки
    if 'error' in ko_stats:
        print(f"Ошибка: {ko_stats['error']}")
        sys.exit(1)
    
    # Выводим информацию о нокаутах
    print(f"\n=== Статистика нокаутов в БД {db_filename} ===")
    print(f"Всего нокаутов: {ko_stats['total_ko']}")
    
    if 'split_ko' in ko_stats:
        print(f"Из них split-нокаутов: {ko_stats['split_ko']}")
    
    if 'stats_total_ko' in ko_stats and ko_stats['stats_total_ko'] != ko_stats['total_ko']:
        print(f"Примечание: в таблице статистики указано {ko_stats['stats_total_ko']} нокаутов")
    
    # Выводим статистику по турнирам
    if ko_stats['tournaments']:
        print("\nНокауты по турнирам:")
        for i, (tournament_id, ko_count) in enumerate(
            sorted(ko_stats['tournaments'].items(), key=lambda x: x[1], reverse=True), 1
        ):
            print(f"{i}. Турнир #{tournament_id}: {ko_count} нокаутов")
    else:
        print("\nНет данных о нокаутах по отдельным турнирам")
    
    print("\nАнализ завершен.")

if __name__ == "__main__":
    main()