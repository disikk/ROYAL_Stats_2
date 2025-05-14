#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с настройками приложения ROYAL_Stats.
Предоставляет класс AppSettings для загрузки, сохранения и доступа к настройкам.
"""

import os
import json
import logging
from typing import Any, Dict, Optional


class AppSettings:
    """
    Класс для управления настройками приложения.
    """
    
    def __init__(self, config_file: str = "config.json"):
        """
        Инициализирует объект настроек приложения.
        
        Args:
            config_file: Путь к файлу с настройками (по умолчанию "config.json")
        """
        self.config_file = config_file
        self.settings = {}
        self.logger = logging.getLogger('ROYAL_Stats.Settings')
        
        # Настройки по умолчанию
        self.default_settings = {
            "db_folder": "databases",
            "hero_name": "Hero",
            "recent_databases": [],
            "active_modules": ["positions", "knockouts", "large_knockouts", "profit"],
            "ui": {
                "theme": "light",
                "font_size": 9,
                "window_size": [1200, 800],
                "window_position": [100, 100],
                "splitter_sizes": [250, 950]
            }
        }
        
        # Загружаем настройки
        self._load_settings()
        
    def _load_settings(self) -> None:
        """
        Загружает настройки из файла.
        Если файл не существует или произошла ошибка, используются настройки по умолчанию.
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Обновляем настройки по умолчанию загруженными
                    self._update_dict_recursively(self.default_settings, loaded_settings)
            
            # Применяем настройки
            self.settings = self.default_settings.copy()
            self.logger.info("Настройки загружены")
            
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек: {str(e)}", exc_info=True)
            # В случае ошибки используем настройки по умолчанию
            self.settings = self.default_settings.copy()
    
    def _update_dict_recursively(self, target: Dict, source: Dict) -> None:
        """
        Рекурсивно обновляет словарь target данными из словаря source.
        
        Args:
            target: Целевой словарь для обновления
            source: Словарь с новыми данными
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Рекурсивно обновляем вложенные словари
                self._update_dict_recursively(target[key], value)
            else:
                # Обновляем значение
                target[key] = value
    
    def save(self) -> None:
        """
        Сохраняет настройки в файл.
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            self.logger.info("Настройки сохранены")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении настроек: {str(e)}", exc_info=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Возвращает значение настройки по ключу.
        
        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если ключ не найден
            
        Returns:
            Значение настройки или default, если ключ не найден
        """
        # Поддержка вложенных ключей через точку (например, "ui.theme")
        if "." in key:
            parts = key.split(".")
            current = self.settings
            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return default
            return current
        
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Устанавливает значение настройки по ключу.
        
        Args:
            key: Ключ настройки
            value: Новое значение
        """
        # Поддержка вложенных ключей через точку (например, "ui.theme")
        if "." in key:
            parts = key.split(".")
            current = self.settings
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self.settings[key] = value
    
    def add_recent_database(self, db_path: str) -> None:
        """
        Добавляет базу данных в список недавно использованных.
        
        Args:
            db_path: Путь к базе данных
        """
        recent_dbs = self.get("recent_databases", [])
        
        # Если база уже в списке, удаляем ее (чтобы добавить в начало)
        if db_path in recent_dbs:
            recent_dbs.remove(db_path)
        
        # Добавляем базу в начало списка
        recent_dbs.insert(0, db_path)
        
        # Оставляем только 5 последних баз
        recent_dbs = recent_dbs[:5]
        
        self.set("recent_databases", recent_dbs)
    
    def get_active_modules(self) -> list:
        """
        Возвращает список активных модулей статистики.
        
        Returns:
            Список имен активных модулей
        """
        return self.get("active_modules", [])
    
    def set_active_modules(self, modules: list) -> None:
        """
        Устанавливает список активных модулей статистики.
        
        Args:
            modules: Список имен активных модулей
        """
        self.set("active_modules", modules)