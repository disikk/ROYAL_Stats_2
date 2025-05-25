# -*- coding: utf-8 -*-

"""
Репозиторий для работы с данными раздач финального стола Hero.
"""

import sqlite3
import logging
from typing import List, Optional
from db.manager import database_manager # Используем синглтон менеджер БД
from models import FinalTableHand
import config # Для определения MIN_KO_BLIND_LEVEL_BB

logger = logging.getLogger('ROYAL_Stats.FinalTableHandRepository')
logger.setLevel(logging.DEBUG)

class FinalTableHandRepository:
    """
    Репозиторий для хранения и получения данных раздач финального стола Hero.
    """

    def __init__(self):
        self.db = database_manager # Используем синглтон

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
                hero_stack, hero_ko_this_hand, session_id, is_early_final
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tournament_id, hand_id) DO NOTHING
        """
        params = (
            hand.tournament_id,
            hand.hand_id,
            hand.hand_number,
            hand.table_size,
            hand.bb,
            hand.hero_stack,
            hand.hero_ko_this_hand,
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
                hero_stack, hero_ko_this_hand, session_id, is_early_final
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
                hero_stack, hero_ko_this_hand, session_id, is_early_final
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
                 hero_stack, hero_ko_this_hand, session_id, is_early_final
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
                hero_stack, hero_ko_this_hand, session_id, is_early_final
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

    def get_first_final_table_hand_for_tournament(self, tournament_id: str) -> Optional[FinalTableHand]:
         """
         Возвращает первую раздачу 9-max стола (по hand_number) для указанного турнира.
         Это соответствует старту финалки.
         """
         # Ищем раздачу с минимальным номером, которая является 9-max
         # (полагаемся на то, что 9-max стол появляется один раз и с него начинается финалка)
         query = """
             SELECT
                 id, tournament_id, hand_id, hand_number, table_size, bb,
                 hero_stack, hero_ko_this_hand, session_id, is_early_final
             FROM hero_final_table_hands
             WHERE tournament_id = ? AND table_size = ? -- Ищем именно 9-max стол
             ORDER BY hand_number ASC
             LIMIT 1
         """
         result = self.db.execute_query(query, (tournament_id, config.FINAL_TABLE_SIZE))
         if result:
             return FinalTableHand.from_dict(dict(result[0]))
         return None