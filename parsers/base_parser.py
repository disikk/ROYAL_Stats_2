#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый класс для парсеров файлов в покерном трекере ROYAL_Stats.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class BaseParser(ABC):
    """
    Абстрактный базовый класс для всех парсеров файлов.
    
    Определяет общий интерфейс для всех парсеров.
    """
    
    def __init__(self, hero_name: str = "Hero"):
        """
        Инициализирует парсер.
        
        Args:
            hero_name: Имя игрока, для которого собираются статистика.
        """
        self.hero_name = hero_name
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Парсит файл и возвращает извлеченные данные.
        
        Args:
            file_path: Путь к файлу для парсинга.
            
        Returns:
            Словарь с извлеченными данными.
            
        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если возникла ошибка при парсинге файла.
        """
        pass
    
    def read_file_content(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        Читает содержимое файла.
        
        Args:
            file_path: Путь к файлу.
            encoding: Кодировка файла (по умолчанию utf-8).
            
        Returns:
            Содержимое файла в виде строки.
            
        Raises:
            FileNotFoundError: Если файл не найден.
        """
        try:
            return Path(file_path).read_text(encoding=encoding, errors='ignore')
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        except Exception as e:
            raise ValueError(f"Ошибка при чтении файла {file_path}: {str(e)}")
    
    def get_file_name(self, file_path: str) -> str:
        """
        Возвращает имя файла без пути и расширения.
        
        Args:
            file_path: Полный путь к файлу.
            
        Returns:
            Имя файла без пути и расширения.
        """
        return Path(file_path).stem