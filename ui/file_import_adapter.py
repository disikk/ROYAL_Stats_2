#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптер для FileImportService для поддержки сигналов рабочих потоков.
Обертывает метод process_files, преобразуя аргументы для соответствия ожиданиям Worker.
"""

import logging
from typing import List, Dict, Any, Optional

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.FileImportAdapter')

class FileImportAdapter:
    """
    Адаптер для FileImportService для работы с сигналами потоков.
    """
    
    @staticmethod
    def adapt_process_files(service, method_name='process_files'):
        """
        Заменяет метод process_files в FileImportService адаптированной версией.
        
        Args:
            service: Экземпляр FileImportService
            method_name: Имя метода для адаптации
        """
        if not hasattr(service, method_name):
            logger.error(f"Сервис не имеет метода {method_name}")
            return
            
        original_method = getattr(service, method_name)
        
        def adapted_process_files(file_paths, session_id, progress_callback=None, cancel_check=None, worker_signals=None, is_cancelled=None, **kwargs):
            """
            Адаптированная версия метода process_files, поддерживающая worker_signals.
            
            Args:
                file_paths: Список путей к файлам
                session_id: ID сессии
                progress_callback: Функция обратного вызова для обновления прогресса
                cancel_check: Функция для проверки отмены операции
                worker_signals: Сигналы рабочего потока
                is_cancelled: Функция для проверки отмены операции
                **kwargs: Дополнительные аргументы
                
            Returns:
                Результат вызова оригинального метода
            """
            # Создаем новую функцию для проверки отмены, если есть оба параметра
            effective_cancel_check = cancel_check
            if is_cancelled and not cancel_check:
                effective_cancel_check = is_cancelled
                
            # Если есть worker_signals, настраиваем функцию обновления прогресса
            effective_progress_callback = progress_callback
            if worker_signals and hasattr(worker_signals, 'progress') and not progress_callback:
                effective_progress_callback = worker_signals.progress.emit
                
            # Передаем все параметры в оригинальный метод
            return original_method(
                file_paths, 
                session_id, 
                effective_progress_callback, 
                effective_cancel_check,
                worker_signals=worker_signals,
                is_cancelled=is_cancelled,
                **kwargs
            )
        
        # Заменяем оригинальный метод на адаптированный
        setattr(service, method_name, adapted_process_files)
        logger.info(f"Метод {method_name} успешно адаптирован для поддержки worker_signals")
        
    @staticmethod
    def initialize():
        """
        Находит и адаптирует все необходимые компоненты.
        """
        try:
            # Проверяем доступность FileImportService
            from services.file_import import FileImportService
            
            # Получаем доступ к экземпляру сервиса в MainWindow
            import sys
            for module_name, module in sys.modules.items():
                if 'ui.main_window' in module_name or module_name == 'ui.main_window':
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, 'file_import_service'):
                            FileImportAdapter.adapt_process_files(attr.file_import_service)
                            logger.info("FileImportService успешно адаптирован")
                            return
            
            logger.warning("Не удалось найти экземпляр FileImportService для адаптации")
        except ImportError as e:
            logger.error(f"Не удалось импортировать необходимые модули: {e}")
        except Exception as e:
            logger.error(f"Ошибка при адаптации FileImportService: {e}", exc_info=True)