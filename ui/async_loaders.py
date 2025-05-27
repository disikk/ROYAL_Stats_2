# -*- coding: utf-8 -*-

"""
Асинхронные загрузчики данных для UI компонентов.
"""

from PyQt6 import QtCore
import logging

logger = logging.getLogger('ROYAL_Stats.AsyncLoaders')


class ViewDataLoader(QtCore.QThread):
    """Поток для асинхронной загрузки данных в view компонентах."""
    finished = QtCore.pyqtSignal(object)  # Передаем загруженные данные
    error = QtCore.pyqtSignal(str)
    
    def __init__(self, loader_func):
        super().__init__()
        self.loader_func = loader_func
        
    def run(self):
        """Выполняет загрузку данных."""
        try:
            data = self.loader_func()
            self.finished.emit(data)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            self.error.emit(str(e))