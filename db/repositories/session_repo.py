#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Репозиторий для работы с сессиями в ROYAL_Stats.
"""

import logging
import uuid
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

# Импортируем базовый класс репозитория
from .base_repository import BaseRepository

class SessionRepository(BaseRepository):
    """
    Репозиторий для работы с сессиями.
    """
    
    def __init__(self, db_manager):
        """
        Инициализирует репозиторий сессий.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        super().__init__(db_manager)
        
    def create_session(self, session_name: str) -> str:
        """
        Создает новую сессию загрузки.
        
        Args:
            session_name: Название сессии
            
        Returns:
            ID созданной сессии
        """
        # Генерируем уникальный ID сессии
        session_id = str(uuid.uuid4())
        
        # Подготавливаем параметры для вставки
        params = (
            session_id,
            session_name,
            0,  # tournaments_count
            0,  # knockouts_count
            0.0,  # avg_finish_place
            0.0,  # total_prize
            0.0   # avg_initial_stack
        )
        
        query = """
        INSERT INTO sessions (
            session_id, session_name, tournaments_count, knockouts_count,
            avg_finish_place, total_prize, avg_initial_stack
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        self.execute_insert(query, params)
        self.logger.debug(f"Создана новая сессия: {session_name} (ID: {session_id})")
        
        return session_id
    
    def get_session_by_id(self, session_id: str) -> Optional[Dict]:
        """
        Получает информацию о сессии по ID.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Словарь с информацией о сессии или None
        """
        query = "SELECT * FROM sessions WHERE session_id = ?"
        result = self.execute_query(query, (session_id,))
        return result[0] if result else None
    
    def get_all_sessions(self) -> List[Dict]:
        """
        Получает список всех сессий.
        
        Returns:
            Список словарей с информацией о сессиях
        """
        query = "SELECT * FROM sessions ORDER BY created_at DESC"
        return self.execute_query(query)
    
    def update_session_stats(self, session_id: str) -> bool:
        """
        Обновляет статистику указанной сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        # Получаем количество турниров в сессии
        tournaments_query = "SELECT COUNT(*) as count FROM tournaments WHERE session_id = ?"
        tournaments_result = self.execute_query(tournaments_query, (session_id,))
        tournaments_count = tournaments_result[0]['count'] if tournaments_result else 0
        
        # Получаем количество нокаутов в сессии
        knockouts_query = "SELECT COUNT(*) as count FROM knockouts WHERE session_id = ?"
        knockouts_result = self.execute_query(knockouts_query, (session_id,))
        knockouts_count = knockouts_result[0]['count'] if knockouts_result else 0
        
        # Рассчитываем среднее место
        avg_place_query = """
        SELECT AVG(finish_place) as avg_place 
        FROM tournaments 
        WHERE session_id = ? AND finish_place IS NOT NULL
        """
        avg_place_result = self.execute_query(avg_place_query, (session_id,))
        avg_finish_place = avg_place_result[0]['avg_place'] if avg_place_result and avg_place_result[0]['avg_place'] is not None else 0.0
        
        # Получаем общий выигрыш
        prize_query = "SELECT SUM(prize) as total FROM tournaments WHERE session_id = ? AND prize IS NOT NULL"
        prize_result = self.execute_query(prize_query, (session_id,))
        total_prize = prize_result[0]['total'] if prize_result and prize_result[0]['total'] is not None else 0.0
        
        # Получаем общую сумму бай-инов
        buyin_query = """
        SELECT SUM(total_buy_in) as total 
        FROM tournaments 
        WHERE session_id = ? AND total_buy_in IS NOT NULL
        """
        buyin_result = self.execute_query(buyin_query, (session_id,))
        total_buy_in = buyin_result[0]['total'] if buyin_result and buyin_result[0]['total'] is not None else 0.0
        
        # Получаем средний начальный стек
        stack_query = """
        SELECT AVG(average_initial_stack) as avg_stack 
        FROM tournaments 
        WHERE session_id = ? AND average_initial_stack IS NOT NULL AND average_initial_stack > 0
        """
        stack_result = self.execute_query(stack_query, (session_id,))
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
        
        rows_affected = self.execute_update(update_query, params)
        
        self.logger.debug(f"Обновлена статистика сессии {session_id}: турниров={tournaments_count}, "
                         f"нокаутов={knockouts_count}, ср.место={avg_finish_place}, "
                         f"выигрыш={total_prize}, ср.стек={avg_initial_stack}")
                         
        return rows_affected > 0
    
    def update_session_name(self, session_id: str, new_name: str) -> bool:
        """
        Обновляет название сессии.
        
        Args:
            session_id: ID сессии
            new_name: Новое название
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        query = "UPDATE sessions SET session_name = ? WHERE session_id = ?"
        rows_affected = self.execute_update(query, (new_name, session_id))
        return rows_affected > 0
    
    def delete_session(self, session_id: str) -> bool:
        """
        Удаляет сессию и все связанные с ней данные.
        
        Args:
            session_id: ID сессии
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        # Создаем скрипт удаления
        script = f"""
        DELETE FROM tournaments WHERE session_id = '{session_id}';
        DELETE FROM knockouts WHERE session_id = '{session_id}';
        DELETE FROM sessions WHERE session_id = '{session_id}';
        """
        
        try:
            self.db_manager.execute_script(script)
            self.logger.debug(f"Удалена сессия {session_id} и все связанные данные")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при удалении сессии {session_id}: {e}")
            return False
            
    def get_session_tournaments_count(self, session_id: str) -> int:
        """
        Возвращает количество турниров в сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Количество турниров в сессии
        """
        if not self.db_manager.is_connected():
            return 0
            
        try:
            query = "SELECT COUNT(*) as count FROM tournaments WHERE session_id = ?"
            result = self.execute_query(query, (session_id,))
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Ошибка при получении количества турниров сессии {session_id}: {str(e)}")
            return 0
    
    def update_overall_statistics(self) -> bool:
        """
        Обновляет общую статистику на основе всех данных в базе.
        
        Returns:
            True в случае успеха, False в случае ошибки
        """
        try:
            # Получаем количество турниров
            tournaments_query = "SELECT COUNT(*) as count FROM tournaments"
            tournaments_result = self.execute_query(tournaments_query)
            total_tournaments = tournaments_result[0]['count'] if tournaments_result else 0
            
            # Получаем общую сумму бай-инов
            buyin_query = "SELECT SUM(total_buy_in) as total FROM tournaments WHERE total_buy_in IS NOT NULL"
            buyin_result = self.execute_query(buyin_query)
            total_buy_in = buyin_result[0]['total'] if buyin_result and buyin_result[0]['total'] is not None else 0
            
            # Получаем общее количество нокаутов
            knockouts_query = "SELECT COUNT(*) as count FROM knockouts"
            knockouts_result = self.execute_query(knockouts_query)
            total_knockouts = knockouts_result[0]['count'] if knockouts_result else 0
            
            # Получаем количество x2 нокаутов
            x2_query = "SELECT SUM(IFNULL(knockouts_x2, 0)) as total FROM tournaments"
            x2_result = self.execute_query(x2_query)
            total_knockouts_x2 = x2_result[0]['total'] if x2_result and x2_result[0]['total'] is not None else 0
            
            # Получаем количество x10 нокаутов
            x10_query = "SELECT SUM(IFNULL(knockouts_x10, 0)) as total FROM tournaments"
            x10_result = self.execute_query(x10_query)
            total_knockouts_x10 = x10_result[0]['total'] if x10_result and x10_result[0]['total'] is not None else 0
            
            # Получаем количество x100 нокаутов
            x100_query = "SELECT SUM(IFNULL(knockouts_x100, 0)) as total FROM tournaments"
            x100_result = self.execute_query(x100_query)
            total_knockouts_x100 = x100_result[0]['total'] if x100_result and x100_result[0]['total'] is not None else 0
            
            # Получаем количество x1000 нокаутов
            x1000_query = "SELECT SUM(IFNULL(knockouts_x1000, 0)) as total FROM tournaments"
            x1000_result = self.execute_query(x1000_query)
            total_knockouts_x1000 = x1000_result[0]['total'] if x1000_result and x1000_result[0]['total'] is not None else 0
            
            # Получаем количество x10000 нокаутов
            x10000_query = "SELECT SUM(IFNULL(knockouts_x10000, 0)) as total FROM tournaments"
            x10000_result = self.execute_query(x10000_query)
            total_knockouts_x10000 = x10000_result[0]['total'] if x10000_result and x10000_result[0]['total'] is not None else 0
            
            # Рассчитываем среднее место
            avg_place_query = "SELECT AVG(finish_place) as avg_place FROM tournaments WHERE finish_place IS NOT NULL"
            avg_place_result = self.execute_query(avg_place_query)
            avg_finish_place = avg_place_result[0]['avg_place'] if avg_place_result and avg_place_result[0]['avg_place'] is not None else 0
            
            # Получаем количество первых мест
            first_query = "SELECT COUNT(*) as count FROM tournaments WHERE finish_place = 1"
            first_result = self.execute_query(first_query)
            first_places = first_result[0]['count'] if first_result else 0
            
            # Получаем количество вторых мест
            second_query = "SELECT COUNT(*) as count FROM tournaments WHERE finish_place = 2"
            second_result = self.execute_query(second_query)
            second_places = second_result[0]['count'] if second_result else 0
            
            # Получаем количество третьих мест
            third_query = "SELECT COUNT(*) as count FROM tournaments WHERE finish_place = 3"
            third_result = self.execute_query(third_query)
            third_places = third_result[0]['count'] if third_result else 0
            
            # Получаем общий выигрыш
            prize_query = "SELECT SUM(prize) as total FROM tournaments WHERE prize IS NOT NULL"
            prize_result = self.execute_query(prize_query)
            total_prize = prize_result[0]['total'] if prize_result and prize_result[0]['total'] is not None else 0
            
            # Получаем средний начальный стек
            stack_query = """
            SELECT AVG(average_initial_stack) as avg_stack 
            FROM tournaments 
            WHERE average_initial_stack IS NOT NULL AND average_initial_stack > 0
            """
            stack_result = self.execute_query(stack_query)
            avg_initial_stack = stack_result[0]['avg_stack'] if stack_result and stack_result[0]['avg_stack'] is not None else 0
            
            # Убеждаемся, что запись существует
            self.execute_query("INSERT OR IGNORE INTO statistics (id) VALUES (1)")
            
            # Обновляем статистику
            update_query = """
            UPDATE statistics SET
                total_tournaments = ?,
                total_knockouts = ?,
                total_knockouts_x2 = ?,
                total_knockouts_x10 = ?,
                total_knockouts_x100 = ?,
                total_knockouts_x1000 = ?,
                total_knockouts_x10000 = ?,
                avg_finish_place = ?,
                first_places = ?,
                second_places = ?,
                third_places = ?,
                total_prize = ?,
                avg_initial_stack = ?,
                total_buy_in = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = 1
            """
            
            params = (
                total_tournaments,
                total_knockouts,
                total_knockouts_x2,
                total_knockouts_x10,
                total_knockouts_x100,
                total_knockouts_x1000,
                total_knockouts_x10000,
                avg_finish_place,
                first_places,
                second_places,
                third_places,
                total_prize,
                avg_initial_stack,
                total_buy_in
            )
            
            rows_affected = self.execute_update(update_query, params)
            
            self.logger.debug(f"Обновлена общая статистика: турниров={total_tournaments}, "
                             f"нокаутов={total_knockouts}, x2={total_knockouts_x2}, "
                             f"x10={total_knockouts_x10}, x100={total_knockouts_x100}, "
                             f"x1000={total_knockouts_x1000}, x10000={total_knockouts_x10000}")
                             
            return rows_affected > 0
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении общей статистики: {e}")
            return False
    
    def get_overall_statistics(self) -> Dict:
        """
        Возвращает общую статистику из базы данных.
        
        Returns:
            Словарь с общей статистикой
        """
        query = "SELECT * FROM statistics WHERE id = 1"
        result = self.execute_query(query)
        
        if not result:
            # Базовая статистика для случая, если запись не найдена
            return {
                'total_tournaments': 0,
                'total_knockouts': 0,
                'total_knockouts_x2': 0,
                'total_knockouts_x10': 0,
                'total_knockouts_x100': 0,
                'total_knockouts_x1000': 0,
                'total_knockouts_x10000': 0,
                'avg_finish_place': 0.0,
                'first_places': 0,
                'second_places': 0,
                'third_places': 0,
                'total_prize': 0.0,
                'avg_initial_stack': 0.0,
                'total_buy_in': 0.0
            }
            
        stats = result[0]
        
        # Проверка и приведение значений к правильным типам
        for key in stats:
            if stats[key] is None:
                if key.startswith('total_') or key.endswith('_places'):
                    stats[key] = 0
                else:
                    stats[key] = 0.0
        
        return stats
    
    def clear_all_data(self) -> bool:
        """
        Очищает все данные в базе.
        
        Returns:
            True в случае успеха, False в случае ошибки
        """
        script = """
        DELETE FROM tournaments;
        DELETE FROM knockouts;
        DELETE FROM sessions;
        DELETE FROM places_distribution;
        UPDATE statistics SET
            total_tournaments = 0,
            total_knockouts = 0,
            total_knockouts_x2 = 0,
            total_knockouts_x10 = 0,
            total_knockouts_x100 = 0,
            total_knockouts_x1000 = 0,
            total_knockouts_x10000 = 0,
            avg_finish_place = 0,
            first_places = 0,
            second_places = 0,
            third_places = 0,
            total_prize = 0,
            avg_initial_stack = 0,
            total_buy_in = 0,
            last_updated = CURRENT_TIMESTAMP
        WHERE id = 1;
        """
        
        try:
            self.db_manager.execute_script(script)
            self.logger.debug("Очищены все данные в базе")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при очистке всех данных: {e}")
            return False
        
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
        query = """
        INSERT INTO stat_modules (name, display_name, enabled, position)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            display_name = excluded.display_name,
            enabled = excluded.enabled,
            position = excluded.position
        """
        
        try:
            self.execute_query(query, (name, display_name, enabled, position))
            
            # Получаем ID модуля
            id_query = "SELECT id FROM stat_modules WHERE name = ?"
            result = self.execute_query(id_query, (name,))
            return result[0]['id'] if result else None
        except Exception as e:
            self.logger.error(f"Ошибка при регистрации модуля статистики {name}: {e}")
            return None
    
    def get_stat_modules(self, enabled_only: bool = False) -> List[Dict]:
        """
        Получает список зарегистрированных модулей статистики.
        
        Args:
            enabled_only: Возвращать только включенные модули
            
        Returns:
            Список словарей с информацией о модулях
        """
        query = "SELECT * FROM stat_modules"
        
        if enabled_only:
            query += " WHERE enabled = 1"
            
        query += " ORDER BY position"
        
        return self.execute_query(query)
    
    def save_module_setting(self, module_id: int, key: str, value: str) -> bool:
        """
        Сохраняет настройку модуля статистики.
        
        Args:
            module_id: ID модуля
            key: Ключ настройки
            value: Значение настройки
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        query = """
        INSERT INTO module_settings (module_id, key, value)
        VALUES (?, ?, ?)
        ON CONFLICT(module_id, key) DO UPDATE SET
            value = excluded.value
        """
        
        try:
            self.execute_query(query, (module_id, key, value))
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении настройки модуля {module_id}: {e}")
            return False
    
    def get_module_settings(self, module_id: int) -> Dict[str, str]:
        """
        Получает настройки модуля статистики.
        
        Args:
            module_id: ID модуля
            
        Returns:
            Словарь {ключ: значение}
        """
        query = "SELECT key, value FROM module_settings WHERE module_id = ?"
        result = self.execute_query(query, (module_id,))
        
        return {row['key']: row['value'] for row in result}