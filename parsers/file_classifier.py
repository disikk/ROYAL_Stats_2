# -*- coding: utf-8 -*-

"""
Классификатор файлов для Royal Stats.
Определяет тип покерного файла (Tournament Summary или Hand History).
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger('ROYAL_Stats.FileClassifier')


class FileClassifier:
    """
    Класс для определения типа покерного файла.
    """
    
    @staticmethod
    def determine_file_type(file_path: str) -> Tuple[Optional[str], List[str]]:
        """
        Определяет тип покерного файла по первым двум строкам.
        
        Args:
            file_path: Путь к файлу для анализа
            
        Returns:
            'ts' - Tournament Summary
            'hh' - Hand History  
            None - файл не соответствует ожидаемым форматам
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                second_line = f.readline()

            lines = [first_line.strip(), second_line.strip()]

            # Нужно минимум 2 строки для проверки
            if not first_line or not second_line:
                return None, lines
            
            # Проверка Tournament Summary
            if (first_line.startswith("Tournament #") and 
                "Mystery Battle Royale" in first_line and 
                second_line.startswith("Buy-in:")):
                return 'ts', lines
                
            # Проверка Hand History
            if (first_line.startswith("Poker Hand #") and 
                "Mystery Battle Royale" in first_line and 
                second_line.startswith("Table")):
                return 'hh', lines
                
            # Если не подходит ни под один формат
            return None, lines
            
        except Exception as e:
            logger.warning(f"Не удалось прочитать файл {file_path}: {e}")
            return None, []
    
    @staticmethod
    def is_poker_file(file_path: str) -> bool:
        """
        Предварительная проверка файла - является ли покерным файлом.
        
        Args:
            file_path: Путь к файлу для проверки
            
        Returns:
            True, если файл соответствует ожидаемым форматам покерных файлов
        """
        file_type, _ = FileClassifier.determine_file_type(file_path)
        return file_type is not None
