# -*- coding: utf-8 -*-

"""
Event Bus для Royal Stats.
Централизованная система публикации и подписки на события.
"""

import logging
import threading
from typing import Dict, List, Callable, Type, Any
from weakref import WeakSet

from .events import Event

logger = logging.getLogger('ROYAL_Stats.EventBus')


class EventBus:
    """
    Шина событий для слабосвязанной коммуникации между компонентами.
    
    Поддерживает:
    - Подписку на события по типу
    - Публикацию событий
    - Слабые ссылки на подписчиков (автоматическая очистка)
    - Потокобезопасность
    """
    
    def __init__(self):
        """Инициализация шины событий."""
        self._subscribers: Dict[Type[Event], WeakSet[Callable]] = {}
        self._lock = threading.RLock()
        logger.debug("EventBus инициализирован")
    
    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]):
        """
        Подписывает обработчик на определенный тип события.
        
        Args:
            event_type: Тип события для подписки
            handler: Функция-обработчик, которая будет вызвана при возникновении события
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = WeakSet()
            
            self._subscribers[event_type].add(handler)
            logger.debug(f"Добавлена подписка на {event_type.__name__} для {handler}")
    
    def unsubscribe(self, event_type: Type[Event], handler: Callable[[Event], None]):
        """
        Отписывает обработчик от определенного типа события.
        
        Args:
            event_type: Тип события
            handler: Функция-обработчик для отписки
        """
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].discard(handler)
                logger.debug(f"Удалена подписка на {event_type.__name__} для {handler}")
    
    def publish(self, event: Event):
        """
        Публикует событие всем подписчикам.
        
        Args:
            event: Экземпляр события для публикации
        """
        event_type = type(event)
        logger.debug(f"Публикация события {event_type.__name__} от {event.source}")
        
        with self._lock:
            # Получаем копию списка подписчиков для безопасной итерации
            handlers = list(self._subscribers.get(event_type, []))
        
        # Вызываем обработчики вне блокировки для предотвращения deadlock
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Ошибка при обработке события {event_type.__name__} "
                           f"в обработчике {handler}: {e}", exc_info=True)
    
    def clear_all_subscriptions(self):
        """Очищает все подписки. Используется при завершении приложения."""
        with self._lock:
            self._subscribers.clear()
            logger.debug("Все подписки очищены")
    
    def get_subscriber_count(self, event_type: Type[Event]) -> int:
        """
        Возвращает количество подписчиков для определенного типа события.
        
        Args:
            event_type: Тип события
            
        Returns:
            Количество активных подписчиков
        """
        with self._lock:
            return len(self._subscribers.get(event_type, []))


# Глобальный экземпляр EventBus (синглтон)
_event_bus_instance: EventBus | None = None
_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """
    Возвращает глобальный экземпляр EventBus.
    Создает его при первом вызове (lazy initialization).
    
    Returns:
        Глобальный экземпляр EventBus
    """
    global _event_bus_instance
    
    if _event_bus_instance is None:
        with _lock:
            # Double-check locking pattern
            if _event_bus_instance is None:
                _event_bus_instance = EventBus()
    
    return _event_bus_instance