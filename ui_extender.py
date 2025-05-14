#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Инициализатор для расширения UI-компонентов ROYAL_Stats.
Подключает адаптеры для различных классов интерфейса.
"""

import logging
import importlib
import sys
from typing import Any, List, Dict, Optional, Type

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.UIExtender')

class UIExtender:
    """
    Класс для расширения функциональности UI-компонентов.
    """
    
    @classmethod
    def initialize(cls):
        """
        Инициализирует расширения UI-компонентов.
        """
        try:
            # Расширяем модули статистики
            cls._extend_stats_modules()
            
            # Расширяем дерево сессий
            cls._extend_session_tree()
            
            # Адаптируем FileImportService
            cls._adapt_file_import_service()
            
            logger.info("Расширения UI-компонентов успешно инициализированы")
        except Exception as e:
            logger.error(f"Ошибка при инициализации расширений UI: {e}", exc_info=True)
    
    @classmethod
    def _extend_stats_modules(cls):
        """
        Расширяет классы модулей статистики.
        """
        try:
            # Импортируем ChartFactory
            from ui.chart_factory import ChartFactory
            
            # Расширяем модули
            ChartFactory.extend_all_stats_modules()
        except ImportError as e:
            logger.error(f"Не удалось импортировать ChartFactory: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Ошибка при расширении модулей статистики: {e}", exc_info=True)
    
    @classmethod
    def _extend_session_tree(cls):
        """
        Расширяет класс дерева сессий.
        """
        try:
            # Пытаемся импортировать SessionTree
            ui_module = importlib.import_module('ui.widgets.session_tree')
            if hasattr(ui_module, 'SessionTree'):
                # Импортируем адаптер
                from ui.session_tree_adapter import SessionTreeAdapter
                
                # Расширяем класс
                SessionTreeAdapter.extend_session_tree(ui_module.SessionTree)
            else:
                logger.warning("Класс SessionTree не найден в модуле ui.widgets.session_tree")
        except ImportError as e:
            logger.error(f"Не удалось импортировать модуль session_tree: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Ошибка при расширении SessionTree: {e}", exc_info=True)
            
    @classmethod
    def _adapt_file_import_service(cls):
        """
        Адаптирует FileImportService для работы с сигналами потоков.
        """
        try:
            # Импортируем адаптер
            from ui.file_import_adapter import FileImportAdapter
            
            # Проверяем импорт FileImportService
            from services.file_import import FileImportService
            
            # Адаптируем все экземпляры FileImportService в MainWindow
            try:
                # Поскольку мы вызываемся во время инициализации приложения,
                # создаем явный прототип для адаптации всех будущих экземпляров
                original_init = FileImportService.__init__
                
                def patched_init(self, *args, **kwargs):
                    result = original_init(self, *args, **kwargs)
                    # Адаптируем метод process_files сразу после создания экземпляра
                    FileImportAdapter.adapt_process_files(self)
                    return result
                
                # Заменяем конструктор
                FileImportService.__init__ = patched_init
                logger.info("FileImportService.__init__ успешно переопределен для автоматической адаптации")
                
            except Exception as e:
                logger.error(f"Не удалось переопределить FileImportService.__init__: {e}", exc_info=True)
                # Используем запасной метод
                FileImportAdapter.initialize()
                
        except ImportError as e:
            logger.error(f"Не удалось импортировать необходимые модули: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Ошибка при адаптации FileImportService: {e}", exc_info=True)