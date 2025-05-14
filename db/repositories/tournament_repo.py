#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Репозиторий для работы с турнирами в ROYAL_Stats.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

# Импортируем базовый класс репозитория
from .base_repository import BaseRepository

class TournamentRepository(BaseRepository):
    """
    Репозиторий для работы с турнирами.
    """
    
    def __init__(self, db_manager):
        """
        Инициализирует репозиторий турниров.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        super().__init__(db_manager)
        
    def save_tournament(self, tournament_data: Dict[str, Any], session_id: str) -> int:
        """
        Сохраняет данные о турнире в базу.
        
        Args:
            tournament_data: Словарь с данными о турнире
            session_id: ID сессии загрузки
            
        Returns:
            ID сохраненного турнира
        """
        # Проверки значений нокаутов
        for key in ['knockouts_x2', 'knockouts_x10', 'knockouts_x100', 'knockouts_x1000', 'knockouts_x10000']:
            if key not in tournament_data or tournament_data[key] is None:
                tournament_data[key] = 0
                self.logger.debug(f"Установлено {key}=0 (не был указан в данных турнира)")
            elif not isinstance(tournament_data[key], int) or tournament_data[key] < 0:
                self.logger.warning(f"Некорректное значение {key}={tournament_data[key]}, будет установлено 0")
                tournament_data[key] = 0
                
        # Подготавливаем параметры для вставки
        params = (
            tournament_data.get('tournament_id'),
            tournament_data.get('tournament_name', f"Tournament #{tournament_data.get('tournament_id')}"),
            tournament_data.get('game_type', 'No Limit Hold\'em'),
            tournament_data.get('buy_in', 0.0),
            tournament_data.get('fee', 0.0),
            tournament_data.get('bounty', 0.0),
            tournament_data.get('total_buy_in', tournament_data.get('buy_in', 0.0)),
            tournament_data.get('players_count', tournament_data.get('players', 9)),  # Поддержка обоих форматов
            tournament_data.get('prize_pool', 0.0),
            tournament_data.get('start_time'),
            tournament_data.get('finish_place'),
            tournament_data.get('prize', tournament_data.get('prize_total', 0)),  # Поддержка обоих форматов
            tournament_data.get('knockouts_x2', 0),
            tournament_data.get('knockouts_x10', 0),
            tournament_data.get('knockouts_x100', 0),
            tournament_data.get('knockouts_x1000', 0),
            tournament_data.get('knockouts_x10000', 0),
            session_id,
            tournament_data.get('average_initial_stack', 0.0)  # Среднее значение начального стека
        )
        
        query = """
        INSERT INTO tournaments (
            tournament_id, tournament_name, game_type, buy_in, fee, bounty,
            total_buy_in, players_count, prize_pool, start_time, finish_place, prize,
            knockouts_x2, knockouts_x10, knockouts_x100, knockouts_x1000, knockouts_x10000, 
            session_id, average_initial_stack
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        tournament_id = self.execute_insert(query, params)
        
        # Обновляем распределение мест
        place = tournament_data.get('finish_place')
        # Проверяем, что место в диапазоне 1-9
        if place and 1 <= place <= 9:
            self._update_place_distribution(place)
            
        return tournament_id
    
    def _update_place_distribution(self, place: int) -> None:
        """
        Обновляет распределение мест.
        
        Args:
            place: Занятое место (1-9)
        """
        query = """
        INSERT INTO places_distribution (place, count) 
        VALUES (?, 1)
        ON CONFLICT(place) DO UPDATE SET
            count = count + 1
        """
        
        self.execute_update(query, (place,))
    
    def update_tournament(self, tournament_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновляет данные турнира.
        
        Args:
            tournament_id: ID турнира
            data: Словарь с данными для обновления
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        # Формируем запрос обновления динамически
        fields = []
        params = []
        
        for key, value in data.items():
            fields.append(f"{key} = ?")
            params.append(value)
            
        # Добавляем ID турнира
        params.append(tournament_id)
        
        query = f"UPDATE tournaments SET {', '.join(fields)} WHERE id = ?"
        
        rows_affected = self.execute_update(query, tuple(params))
        return rows_affected > 0
    
    def get_tournament_by_id(self, tournament_id: int) -> Optional[Dict]:
        """
        Получает данные турнира по его ID.
        
        Args:
            tournament_id: ID турнира
            
        Returns:
            Словарь с данными турнира или None
        """
        return self.get_by_id("tournaments", tournament_id)
    
    def get_tournament_by_external_id(self, external_id: str) -> Optional[Dict]:
        """
        Получает данные турнира по его внешнему ID.
        
        Args:
            external_id: Внешний ID турнира (tournament_id в таблице)
            
        Returns:
            Словарь с данными турнира или None
        """
        query = "SELECT * FROM tournaments WHERE tournament_id = ?"
        result = self.execute_query(query, (external_id,))
        return result[0] if result else None
    
    def get_tournaments_by_session(self, session_id: str) -> List[Dict]:
        """
        Получает список турниров по ID сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с данными турниров
        """
        query = """
        SELECT t.*, 
               (SELECT COUNT(k.id) FROM knockouts k 
                WHERE k.tournament_id = t.tournament_id AND k.session_id = t.session_id) as knockouts_count
        FROM tournaments t 
        WHERE t.session_id = ? 
        ORDER BY t.start_time DESC
        """
        
        return self.execute_query(query, (session_id,))
    
    def get_all_tournaments(self, limit: int = None, offset: int = None) -> List[Dict]:
        """
        Получает список всех турниров.
        
        Args:
            limit: Ограничение количества результатов (опционально)
            offset: Смещение для пагинации (опционально)
            
        Returns:
            Список словарей с данными турниров
        """
        query = """
        SELECT t.*, 
               (SELECT COUNT(k.id) FROM knockouts k WHERE k.tournament_id = t.tournament_id) as knockouts_count 
        FROM tournaments t 
        ORDER BY t.start_time DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        if offset:
            query += f" OFFSET {offset}"
            
        return self.execute_query(query)
    
    def get_all_tournaments_with_knockouts(self) -> List[Dict]:
        """
        Получает список всех турниров с подсчетом нокаутов.
        
        Returns:
            Список словарей с данными турниров и количеством нокаутов
        """
        query = """
        SELECT t.*, 
               (SELECT COUNT(k.id) FROM knockouts k WHERE k.tournament_id = t.tournament_id) as knockouts_count 
        FROM tournaments t 
        ORDER BY t.start_time DESC
        """
        
        return self.execute_query(query)
    
    def get_session_tournaments_with_knockouts(self, session_id: str) -> List[Dict]:
        """
        Получает список турниров сессии с подсчетом нокаутов.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с данными турниров и количеством нокаутов
        """
        query = """
        SELECT t.*, 
               (SELECT COUNT(k.id) FROM knockouts k 
                WHERE k.tournament_id = t.tournament_id AND k.session_id = t.session_id) as knockouts_count
        FROM tournaments t 
        WHERE t.session_id = ? 
        ORDER BY t.start_time DESC
        """
        
        return self.execute_query(query, (session_id,))
    
    def get_tournaments_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Получает список турниров в указанном временном диапазоне.
        
        Args:
            start_date: Начальная дата в формате "YYYY-MM-DD"
            end_date: Конечная дата в формате "YYYY-MM-DD"
            
        Returns:
            Список словарей с данными турниров
        """
        query = """
        SELECT * FROM tournaments 
        WHERE DATE(start_time) BETWEEN DATE(?) AND DATE(?)
        ORDER BY start_time DESC
        """
        
        return self.execute_query(query, (start_date, end_date))
    
    def count_tournaments(self, session_id: str = None) -> int:
        """
        Подсчитывает количество турниров.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Количество турниров
        """
        if session_id:
            return self.count("tournaments", "session_id = ?", (session_id,))
        else:
            return self.count("tournaments")
    
    def sum_prizes(self, session_id: str = None) -> float:
        """
        Суммирует призы за турниры.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Сумма призов
        """
        query = "SELECT SUM(prize) as total FROM tournaments WHERE prize IS NOT NULL"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        return result[0]['total'] if result and result[0]['total'] is not None else 0.0
    
    def sum_buyin(self, session_id: str = None) -> float:
        """
        Суммирует бай-ины за турниры.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Сумма бай-инов
        """
        query = "SELECT SUM(total_buy_in) as total FROM tournaments WHERE total_buy_in IS NOT NULL"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        return result[0]['total'] if result and result[0]['total'] is not None else 0.0
    
    def get_average_finish_place(self, session_id: str = None) -> float:
        """
        Вычисляет среднее место в турнирах.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Среднее место
        """
        query = "SELECT AVG(finish_place) as avg_place FROM tournaments WHERE finish_place IS NOT NULL"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        return result[0]['avg_place'] if result and result[0]['avg_place'] is not None else 0.0
    
    def get_places_distribution(self) -> Dict[int, int]:
        """
        Возвращает распределение мест.
        
        Returns:
            Словарь {место: количество_турниров}
        """
        query = "SELECT place, count FROM places_distribution ORDER BY place"
        
        result = self.execute_query(query)
        
        # Преобразуем результат в словарь
        distribution = {i: 0 for i in range(1, 10)}
        for row in result:
            distribution[row['place']] = row['count']
            
        return distribution
    
    def get_top_positions_count(self, session_id: str = None) -> Dict[str, int]:
        """
        Возвращает количество призовых мест (1-3).
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {место: количество}
        """
        query = """
        SELECT 
            SUM(CASE WHEN finish_place = 1 THEN 1 ELSE 0 END) as first,
            SUM(CASE WHEN finish_place = 2 THEN 1 ELSE 0 END) as second,
            SUM(CASE WHEN finish_place = 3 THEN 1 ELSE 0 END) as third
        FROM tournaments
        """
        
        params = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        
        if not result:
            return {'first': 0, 'second': 0, 'third': 0}
            
        return {
            'first': result[0]['first'] if result[0]['first'] is not None else 0,
            'second': result[0]['second'] if result[0]['second'] is not None else 0,
            'third': result[0]['third'] if result[0]['third'] is not None else 0
        }
    
    def get_average_initial_stack(self, session_id: str = None) -> float:
        """
        Вычисляет средний начальный стек в турнирах.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Средний начальный стек
        """
        query = """
        SELECT AVG(average_initial_stack) as avg_stack 
        FROM tournaments 
        WHERE average_initial_stack IS NOT NULL AND average_initial_stack > 0
        """
        
        params = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        return result[0]['avg_stack'] if result and result[0]['avg_stack'] is not None else 0.0
    
    def delete_tournament(self, tournament_id: int) -> bool:
        """
        Удаляет турнир по ID.
        
        Args:
            tournament_id: ID турнира
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        query = "DELETE FROM tournaments WHERE id = ?"
        rows_affected = self.execute_delete(query, (tournament_id,))
        return rows_affected > 0
    
    def delete_tournaments_by_session(self, session_id: str) -> int:
        """
        Удаляет все турниры сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Количество удаленных турниров
        """
        query = "DELETE FROM tournaments WHERE session_id = ?"
        return self.execute_delete(query, (session_id,))