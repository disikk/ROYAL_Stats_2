#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для определения типа файлов в покерном трекере ROYAL_Stats.
"""

import os
import logging
from typing import Literal, Optional

# Настраиваем логирование
logger = logging.getLogger('ROYAL_Stats.FileDetector')

# Определение возможных типов файлов
FileType = Literal['hand_history', 'tournament_summary', 'unknown']


def detect_file_type(file_path: str) -> FileType:
    """
    Определяет тип файла: история рук, сводка турнира или неизвестный.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        'hand_history', 'tournament_summary' или 'unknown'.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(2000)  # Читаем первые 2000 байт для определения типа
            
            # Определение файлов tournament summary
            if ('Tournament #' in content and 
                ('Buy' in content or 'buy' in content.lower()) and 
                any(marker in content for marker in ['place', 'st place', 'nd place', 'rd place', 'th place'])):
                logger.debug(f"Файл {file_path} определен как сводка турнира (tournament_summary)")
                return 'tournament_summary'
                
            # Определение файлов hand history
            if ('Hand #' in content or 'Poker Hand #' in content or 
                ('Table' in content and 'Seat' in content) or
                '9max' in os.path.basename(file_path).lower()):
                logger.debug(f"Файл {file_path} определен как история рук (hand_history)")
                return 'hand_history'
                
            logger.info(f"Тип файла {file_path} не определен")
            return 'unknown'
    except Exception as e:
        logger.warning(f"Ошибка при определении типа файла {file_path}: {str(e)}")
        return 'unknown'


def is_tournament_summary(file_path: str) -> bool:
    """
    Проверяет, является ли файл сводкой турнира.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        True, если файл является сводкой турнира, иначе False.
    """
    return detect_file_type(file_path) == 'tournament_summary'


def is_hand_history(file_path: str) -> bool:
    """
    Проверяет, является ли файл историей рук.
    
    Args:
        file_path: Путь к файлу.
        
    Returns:
        True, если файл является историей рук, иначе False.
    """
    return detect_file_type(file_path) == 'hand_history'