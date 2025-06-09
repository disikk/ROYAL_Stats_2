# -*- coding: utf-8 -*-

"""
Определения событий для Royal Stats.
Базовые классы событий и конкретные события системы.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class Event:
    """Базовый класс для всех событий в системе."""
    timestamp: datetime
    source: str  # Имя компонента, который создал событие
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class DataImportedEvent(Event):
    """
    Событие, возникающее после завершения импорта данных.
    
    Attributes:
        session_id: ID сессии, в которую были импортированы данные
        imported_tournament_ids: Список ID турниров, которые были импортированы/обновлены
        files_processed: Количество обработанных файлов
        tournaments_saved: Количество сохраненных турниров
        hands_saved: Количество сохраненных рук
    """
    session_id: str
    imported_tournament_ids: List[str]
    files_processed: int
    tournaments_saved: int
    hands_saved: int


@dataclass
class StatisticsUpdatedEvent(Event):
    """
    Событие, возникающее после обновления статистики.
    
    Attributes:
        db_path: Путь к БД, для которой обновилась статистика
        session_id: ID сессии, если обновлялась статистика сессии
        is_overall: True, если обновилась общая статистика
        is_session: True, если обновилась статистика сессии
        is_incremental: True, если выполнено инкрементальное обновление
        added_tournaments: Количество добавленных турниров (для инкрементального обновления)
        added_hands: Количество добавленных рук (для инкрементального обновления)
    """
    db_path: str
    session_id: Optional[str] = None
    is_overall: bool = False
    is_session: bool = False
    is_incremental: bool = False
    added_tournaments: int = 0
    added_hands: int = 0


@dataclass
class DatabaseChangedEvent(Event):
    """
    Событие, возникающее при смене активной базы данных.
    
    Attributes:
        old_db_path: Путь к предыдущей БД
        new_db_path: Путь к новой БД
    """
    old_db_path: Optional[str]
    new_db_path: str


@dataclass
class SessionDeletedEvent(Event):
    """
    Событие, возникающее при удалении сессии.
    
    Attributes:
        session_id: ID удаленной сессии
        db_path: Путь к БД, из которой удалена сессия
    """
    session_id: str
    db_path: str


@dataclass
class TournamentDeletedEvent(Event):
    """
    Событие, возникающее при удалении турнира.
    
    Attributes:
        tournament_id: ID удаленного турнира
        session_id: ID сессии, к которой относился турнир
        db_path: Путь к БД, из которой удален турнир
    """
    tournament_id: str
    session_id: str
    db_path: str


@dataclass
class CacheInvalidatedEvent(Event):
    """
    Событие, возникающее при инвалидации кеша.
    
    Attributes:
        db_path: Путь к БД, для которой инвалидирован кеш
        reason: Причина инвалидации кеша
    """
    db_path: str
    reason: str