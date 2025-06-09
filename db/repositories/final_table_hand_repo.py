# -*- coding: utf-8 -*-

"""
Репозиторий для работы с данными раздач финального стола Hero.
"""

import sqlite3
import logging
from typing import List, Optional
from db.manager import DatabaseManager, database_manager  # Используем синглтон менеджер БД
from models import FinalTableHand
from services.app_config import app_config

logger = logging.getLogger('ROYAL_Stats.FinalTableHandRepository')
logger.setLevel(logging.DEBUG)

class FinalTableHandRepository:
    """
    Репозиторий для хранения и получения данных раздач финального стола Hero.
    """

    def __init__(self, db_manager: DatabaseManager = database_manager):
        """Initialize repository with the shared database manager."""
        self.db = db_manager

    def add_hand(self, hand: FinalTableHand):
        """
        Добавляет новую раздачу финального стола Hero.
        Использует ON CONFLICT(tournament_id, hand_id) DO NOTHING
        для игнорирования дубликатов при повторном парсинге тех же файлов.
        """
        logger.info(f"=== ОТЛАДКА add_hand ===")
        logger.info(f"Попытка сохранить руку: tournament_id={hand.tournament_id}, hand_id={hand.hand_id}, table_size={hand.table_size}")
        
        query = """
            INSERT INTO hero_final_table_hands (
                tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tournament_id, hand_id) DO NOTHING
        """
        params = (
            hand.tournament_id,
            hand.hand_id,
            hand.hand_number,
            hand.table_size,
            hand.bb,
            hand.hero_stack,
            hand.players_count,
            hand.hero_ko_this_hand,
            hand.pre_ft_ko,
            hand.hero_ko_attempts,
            hand.session_id,
            hand.is_early_final,
        )
        
        result = self.db.execute_update(query, params)
        logger.info(f"Результат execute_update: {result} строк изменено")


    def get_hands_by_tournament(self, tournament_id: str) -> List[FinalTableHand]:
        """
        Возвращает все раздачи финального стола для указанного турнира.
        Отсортированы по номеру раздачи.
        """
        query = """
            SELECT
                id, tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            FROM hero_final_table_hands
            WHERE tournament_id = ?
            ORDER BY hand_number ASC
        """
        results = self.db.execute_query(query, (tournament_id,))
        return [FinalTableHand.from_dict(dict(row)) for row in results]

    def get_hands_by_session(self, session_id: str) -> List[FinalTableHand]:
        """
        Возвращает все раздачи финального стола для указанной сессии.
        """
        query = """
            SELECT
                id, tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            FROM hero_final_table_hands
            WHERE session_id = ?
            ORDER BY hand_number ASC
        """
        results = self.db.execute_query(query, (session_id,))
        return [FinalTableHand.from_dict(dict(row)) for row in results]

    def get_all_hands(self) -> List[FinalTableHand]:
         """
         Возвращает все раздачи финального стола Hero из текущей БД.
         """
         query = """
            SELECT
                id, tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            FROM hero_final_table_hands
            ORDER BY hand_number ASC -- Порядок важен для определения первой руки
         """
         results = self.db.execute_query(query)
         return [FinalTableHand.from_dict(dict(row)) for row in results]


    def get_early_final_hands(self, session_id: Optional[str] = None) -> List[FinalTableHand]:
        """
        Возвращает раздачи ранней стадии финального стола (9-6 игроков),
        опционально фильтруя по сессии.
        """
        query = """
            SELECT
                id, tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            FROM hero_final_table_hands
            WHERE is_early_final = 1
        """
        params = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " ORDER BY hand_number ASC"

        results = self.db.execute_query(query, params)
        return [FinalTableHand.from_dict(dict(row)) for row in results]

    def get_hands_by_filters(self, session_id: Optional[str] = None, tournament_ids: Optional[List[str]] = None) -> List[FinalTableHand]:
        """
        Возвращает раздачи финального стола с фильтрацией на уровне SQL.
        
        Args:
            session_id: ID сессии для фильтрации (если не указан - все сессии)
            tournament_ids: Список ID турниров для фильтрации (если не указан - все турниры)
            
        Returns:
            Список раздач финального стола
        """
        query = """
            SELECT
                id, tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            FROM hero_final_table_hands
            WHERE 1=1
        """
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        if tournament_ids:
            placeholders = ','.join(['?' for _ in tournament_ids])
            query += f" AND tournament_id IN ({placeholders})"
            params.extend(tournament_ids)
            
        query += " ORDER BY hand_number ASC"
        
        results = self.db.execute_query(query, params)
        return [FinalTableHand.from_dict(dict(row)) for row in results]

    def get_first_final_table_hand_for_tournament(self, tournament_id: str) -> Optional[FinalTableHand]:
        """Возвращает первую раздачу 9-max стола для указанного турнира."""
        query = """
            SELECT
                id, tournament_id, hand_id, hand_number, table_size, bb,
                hero_stack, players_count, hero_ko_this_hand, pre_ft_ko,
                hero_ko_attempts, session_id, is_early_final
            FROM hero_final_table_hands
            WHERE tournament_id = ? AND table_size = ?
            ORDER BY hand_number ASC
            LIMIT 1
        """
        result = self.db.execute_query(
            query,
            (tournament_id, app_config.final_table_size)
        )
        if result:
            return FinalTableHand.from_dict(dict(result[0]))
        return None
    
    def get_ko_counts_for_tournaments(self, tournament_ids: List[str]) -> dict[str, float]:
        """
        Эффективно получает суммарное количество KO для списка турниров одним запросом.
        Возвращает словарь {tournament_id: total_ko}.
        """
        if not tournament_ids:
            return {}
        
        placeholders = ','.join(['?' for _ in tournament_ids])
        query = f"""
            SELECT tournament_id, SUM(hero_ko_this_hand) as total_ko
            FROM hero_final_table_hands
            WHERE tournament_id IN ({placeholders})
            GROUP BY tournament_id
        """
        
        results = self.db.execute_query(query, tournament_ids)
        return {row[0]: row[1] if row[1] is not None else 0.0 for row in results}
    
    def get_early_ft_ko_count(self, tournament_ids: Optional[List[str]] = None) -> float:
        """
        Получает общее количество KO в ранней стадии финального стола.
        Оптимизирован для инкрементального обновления с возможностью фильтрации по турнирам.
        """
        query = """
            SELECT SUM(hero_ko_this_hand) 
            FROM hero_final_table_hands 
            WHERE is_early_final = 1
        """
        params = []
        
        if tournament_ids:
            placeholders = ','.join(['?' for _ in tournament_ids])
            query += f" AND tournament_id IN ({placeholders})"
            params.extend(tournament_ids)
        
        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0
    
    def get_pre_ft_ko_sum(self, tournament_ids: Optional[List[str]] = None) -> float:
        """
        Получает сумму Pre-FT KO.
        Оптимизирован для инкрементального обновления.
        """
        query = "SELECT SUM(pre_ft_ko) FROM hero_final_table_hands"
        params = []
        
        if tournament_ids:
            placeholders = ','.join(['?' for _ in tournament_ids])
            query += f" WHERE tournament_id IN ({placeholders})"
            params.extend(tournament_ids)
        
        result = self.db.execute_query(query, params)
        return result[0][0] if result and result[0][0] is not None else 0.0