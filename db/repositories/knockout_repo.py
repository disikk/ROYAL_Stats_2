#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Репозиторий для работы с нокаутами в ROYAL_Stats.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple

# Импортируем базовый класс репозитория
from .base_repository import BaseRepository

class KnockoutRepository(BaseRepository):
    """
    Репозиторий для работы с нокаутами.
    """
    
    def __init__(self, db_manager):
        """
        Инициализирует репозиторий нокаутов.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        super().__init__(db_manager)
        
    def save_knockout(self, knockout_data: Dict[str, Any], tournament_id: str, session_id: str) -> int:
        """
        Сохраняет данные о нокауте в базу.
        
        Args:
            knockout_data: Словарь с данными о нокауте
            tournament_id: ID турнира
            session_id: ID сессии загрузки
            
        Returns:
            ID сохраненного нокаута
        """
        # Подготавливаем параметры для вставки
        params = (
            tournament_id,
            knockout_data.get('hand_id', ''),
            knockout_data.get('knocked_out_player', knockout_data.get('player_name', 'Unknown')),
            knockout_data.get('pot_size', 0),
            knockout_data.get('multi_knockout', False),
            session_id
        )
        
        query = """
        INSERT INTO knockouts (
            tournament_id, hand_id, knocked_out_player, pot_size, multi_knockout, session_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        return self.execute_insert(query, params)
    
    def save_knockouts(self, knockouts: List[Dict[str, Any]], tournament_id: str, session_id: str) -> int:
        """
        Сохраняет список нокаутов в базу.
        
        Args:
            knockouts: Список словарей с данными о нокаутах
            tournament_id: ID турнира
            session_id: ID сессии загрузки
            
        Returns:
            Количество сохраненных нокаутов
        """
        if not knockouts:
            self.logger.debug(f"Нет нокаутов для сохранения для турнира {tournament_id}")
            return 0
            
        saved_count = 0
        for knockout in knockouts:
            try:
                self.save_knockout(knockout, tournament_id, session_id)
                saved_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении нокаута для турнира {tournament_id}: {e}")
                # Продолжаем сохранение других нокаутов, несмотря на ошибку
                
        return saved_count
    
    def get_knockout_by_id(self, knockout_id: int) -> Optional[Dict]:
        """
        Получает данные нокаута по его ID.
        
        Args:
            knockout_id: ID нокаута
            
        Returns:
            Словарь с данными нокаута или None
        """
        return self.get_by_id("knockouts", knockout_id)
    
    def get_knockouts_by_tournament(self, tournament_id: str) -> List[Dict]:
        """
        Получает список нокаутов по ID турнира.
        
        Args:
            tournament_id: ID турнира
            
        Returns:
            Список словарей с данными нокаутов
        """
        query = "SELECT * FROM knockouts WHERE tournament_id = ?"
        return self.execute_query(query, (tournament_id,))
    
    def get_knockouts_by_session(self, session_id: str) -> List[Dict]:
        """
        Получает список нокаутов по ID сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список словарей с данными нокаутов
        """
        query = "SELECT * FROM knockouts WHERE session_id = ?"
        return self.execute_query(query, (session_id,))
    
    def get_all_knockouts(self, limit: int = None, offset: int = None) -> List[Dict]:
        """
        Получает список всех нокаутов.
        
        Args:
            limit: Ограничение количества результатов (опционально)
            offset: Смещение для пагинации (опционально)
            
        Returns:
            Список словарей с данными нокаутов
        """
        query = "SELECT * FROM knockouts ORDER BY id DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        if offset:
            query += f" OFFSET {offset}"
            
        return self.execute_query(query)
    
    def count_knockouts(self, session_id: str = None, tournament_id: str = None) -> int:
        """
        Подсчитывает количество нокаутов.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            tournament_id: ID турнира для фильтрации (опционально)
            
        Returns:
            Количество нокаутов
        """
        conditions = []
        params = []
        
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
            
        if tournament_id:
            conditions.append("tournament_id = ?")
            params.append(tournament_id)
            
        if conditions:
            condition_str = " AND ".join(conditions)
            return self.count("knockouts", condition_str, tuple(params))
        else:
            return self.count("knockouts")
    
    def get_knockouts_by_tournament_count(self, session_id: str = None) -> Dict[str, int]:
        """
        Возвращает количество нокаутов, сгруппированных по турнирам.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {tournament_id: количество_нокаутов}
        """
        query = "SELECT tournament_id, COUNT(*) as count FROM knockouts"
        params = []
        
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
            
        query += " GROUP BY tournament_id"
        
        result = self.execute_query(query, tuple(params) if params else None)
        return {row['tournament_id']: row['count'] for row in result}
    
    def get_knockouts_by_date(self, start_date: str = None, end_date: str = None) -> Dict[str, int]:
        """
        Возвращает количество нокаутов, сгруппированных по датам.
        
        Args:
            start_date: Начальная дата в формате "YYYY-MM-DD" (опционально)
            end_date: Конечная дата в формате "YYYY-MM-DD" (опционально)
            
        Returns:
            Словарь {дата: количество_нокаутов}
        """
        query = """
        SELECT 
            DATE(t.start_time) as date, 
            COUNT(k.id) as count
        FROM 
            knockouts k
        JOIN 
            tournaments t ON k.tournament_id = t.tournament_id
        """
        
        params = []
        conditions = []
        
        if start_date:
            conditions.append("DATE(t.start_time) >= DATE(?)")
            params.append(start_date)
            
        if end_date:
            conditions.append("DATE(t.start_time) <= DATE(?)")
            params.append(end_date)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " GROUP BY date ORDER BY date"
        
        result = self.execute_query(query, tuple(params) if params else None)
        return {row['date']: row['count'] for row in result}
    
    def get_multi_knockout_stats(self, session_id: str = None) -> Dict[str, int]:
        """
        Возвращает статистику по обычным нокаутам и мульти-нокаутам.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Словарь {тип: количество}
        """
        query = """
        SELECT 
            SUM(CASE WHEN multi_knockout = 0 THEN 1 ELSE 0 END) as single,
            SUM(CASE WHEN multi_knockout = 1 THEN 1 ELSE 0 END) as multi
        FROM knockouts
        """
        
        params = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        
        if not result:
            return {'single': 0, 'multi': 0}
            
        return {
            'single': result[0]['single'] if result[0]['single'] is not None else 0,
            'multi': result[0]['multi'] if result[0]['multi'] is not None else 0
        }
    
    def get_early_stage_knockouts(self, session_id: str = None) -> int:
        """
        Возвращает количество нокаутов, сделанных игроком, 
        когда за столом было от 6 до 9 человек включительно.
        Использует аппроксимацию: считает, что первые 33% нокаутов в турнире 
        были сделаны на ранней стадии.
        
        Args:
            session_id: ID сессии для фильтрации (опционально)
            
        Returns:
            Количество нокаутов на ранней стадии
        """
        query = """
        SELECT t.tournament_id, t.players_count, COUNT(k.id) as ko_count
        FROM tournaments t
        JOIN knockouts k ON t.tournament_id = k.tournament_id
        """
        
        params = []
        if session_id:
            query += " WHERE t.session_id = ?"
            params.append(session_id)
            
        result = self.execute_query(query, tuple(params) if params else None)
        
        total_early_knockouts = 0
        for row in result:
            players_count = row['players_count'] or 9  # Если NULL, считаем 9
            ko_count = row['ko_count']
            
            # Вычисляем количество нокаутов на ранней стадии
            # Для турнира с 9 игроками, ранняя стадия - это выбывание первых 3х игроков
            early_stage_cutoff = min(3, max(1, int(players_count * 0.33)))
            early_knockouts = min(ko_count, early_stage_cutoff)
            
            total_early_knockouts += early_knockouts
            
        return total_early_knockouts
    
    def delete_knockout(self, knockout_id: int) -> bool:
        """
        Удаляет нокаут по ID.
        
        Args:
            knockout_id: ID нокаута
            
        Returns:
            True в случае успеха, False в случае ошибки
        """
        query = "DELETE FROM knockouts WHERE id = ?"
        rows_affected = self.execute_delete(query, (knockout_id,))
        return rows_affected > 0
    
    def delete_knockouts_by_tournament(self, tournament_id: str) -> int:
        """
        Удаляет все нокауты турнира.
        
        Args:
            tournament_id: ID турнира
            
        Returns:
            Количество удаленных нокаутов
        """
        query = "DELETE FROM knockouts WHERE tournament_id = ?"
        return self.execute_delete(query, (tournament_id,))
    
    def delete_knockouts_by_session(self, session_id: str) -> int:
        """
        Удаляет все нокауты сессии.
        
        Args:
            session_id: ID сессии
            
        Returns:
            Количество удаленных нокаутов
        """
        query = "DELETE FROM knockouts WHERE session_id = ?"
        return self.execute_delete(query, (session_id,))