# -*- coding: utf-8 -*-

"""
Модуль для асинхронного выполнения операций в фоновых потоках.
"""

from PyQt6 import QtCore
import logging
from typing import Callable, Any, Optional
import threading
import time

logger = logging.getLogger('ROYAL_Stats.Background')

class CancellableWorker(QtCore.QObject):
    """Воркер с поддержкой отмены операции."""
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(Exception)
    progress = QtCore.pyqtSignal(int, int)  # current, total
    
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False
        self._lock = threading.Lock()
        
    def cancel(self):
        """Отменяет выполнение операции."""
        with self._lock:
            self._is_cancelled = True
            
    def is_cancelled(self) -> bool:
        """Проверяет, была ли операция отменена."""
        with self._lock:
            return self._is_cancelled
    
    @QtCore.pyqtSlot()
    def run(self):
        """Выполняет функцию с обработкой ошибок."""
        try:
            # Передаем callback для проверки отмены
            self.kwargs['is_cancelled_callback'] = self.is_cancelled
            
            result = self.fn(*self.args, **self.kwargs)
            
            if not self.is_cancelled():
                self.finished.emit(result)
        except Exception as e:
            logger.error(f"Ошибка в фоновом потоке: {e}")
            if not self.is_cancelled():
                self.error.emit(e)
        finally:
            # Закрываем соединение с БД для этого потока
            try:
                from db.manager import database_manager
                database_manager.close_connection()
            except:
                pass


class ThreadManager:
    """Менеджер потоков с поддержкой отмены и очистки."""
    
    def __init__(self):
        self._threads = {}  # widget_id -> (thread, worker)
        self._db_semaphore = threading.Semaphore(2)  # Ограничиваем до 2 одновременных операций с БД
        
    def run_in_thread(self, widget_id: str, fn: Callable, 
                     callback: Callable, error_callback: Optional[Callable] = None,
                     owner: QtCore.QObject = None, *args, **kwargs) -> QtCore.QThread:
        """
        Запускает функцию в фоне с автоматической отменой предыдущей операции.
        
        Args:
            widget_id: Уникальный ID виджета (для отмены предыдущих операций)
            fn: Функция для выполнения в фоне
            callback: Функция для обработки результата
            error_callback: Функция для обработки ошибок
            owner: Владелец потока
            *args, **kwargs: Аргументы для fn
        """
        # Отменяем предыдущую операцию для этого виджета
        self.cancel(widget_id)
        
        # Создаем новый поток
        thread = QtCore.QThread(owner)
        worker = CancellableWorker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        
        # Подключаем сигналы
        thread.started.connect(worker.run)
        worker.finished.connect(callback)
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda: self._cleanup(widget_id))
        
        if error_callback:
            worker.error.connect(error_callback)
        worker.error.connect(thread.quit)
        worker.error.connect(lambda: self._cleanup(widget_id))
        
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(worker.deleteLater)
        
        # Сохраняем ссылки
        self._threads[widget_id] = (thread, worker)
        
        # Запускаем поток
        thread.start()
        return thread
        
    def cancel(self, widget_id: str):
        """Отменяет операцию для указанного виджета."""
        if widget_id in self._threads:
            thread, worker = self._threads[widget_id]
            worker.cancel()
            if thread.isRunning():
                thread.quit()
                # Увеличиваем время ожидания для больших операций
                thread.wait(2000)  # Ждем максимум 2 секунды
                if thread.isRunning():
                    logger.warning(f"Поток {widget_id} не завершился, принудительное завершение")
                    thread.terminate()  # Принудительное завершение
                    
    def _cleanup(self, widget_id: str):
        """Удаляет ссылки на завершенный поток."""
        if widget_id in self._threads:
            del self._threads[widget_id]
            
    def cancel_all(self):
        """Отменяет все активные операции."""
        for widget_id in list(self._threads.keys()):
            self.cancel(widget_id)


# Глобальный менеджер потоков
thread_manager = ThreadManager()


# Простая функция для обратной совместимости
def run_in_thread(fn, callback, owner):
    """
    Запускает функцию в фоновом потоке.
    Результат будет передан в callback в главном потоке.
    """
    widget_id = str(id(owner))  # Используем ID объекта как уникальный ключ
    return thread_manager.run_in_thread(widget_id, fn, callback, owner=owner)
