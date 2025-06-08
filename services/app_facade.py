# -*- coding: utf-8 -*-

"""
Фасад приложения Royal Stats.
Тонкий координатор, который объединяет работу всех сервисов
и предоставляет единый интерфейс для UI.
"""

import os
import logging
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime

from models import Tournament, Session, OverallStats
from db.manager import DatabaseManager
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    OverallStatsRepository,
    PlaceDistributionRepository,
    FinalTableHandRepository,
)
from parsers import HandHistoryParser, TournamentSummaryParser

from .import_service import ImportService
from .statistics_service import StatisticsService
from .app_config import AppConfig
from .event_bus import EventBus
from .events import (
    DataImportedEvent,
    StatisticsUpdatedEvent,
    DatabaseChangedEvent,
    SessionDeletedEvent,
    TournamentDeletedEvent,
    CacheInvalidatedEvent
)

logger = logging.getLogger('ROYAL_Stats.AppFacade')


class AppFacade:
    """
    Фасад приложения - единая точка входа для UI.
    Координирует работу всех сервисов и управляет их взаимодействием.
    """
    
    def __init__(
        self,
        config: AppConfig,
        db_manager: DatabaseManager,
        event_bus: EventBus,
        import_service: ImportService,
        statistics_service: StatisticsService
    ):
        """
        Инициализация фасада приложения.
        
        Args:
            config: Конфигурация приложения
            db_manager: Менеджер базы данных
            event_bus: Шина событий
            import_service: Сервис импорта
            statistics_service: Сервис статистики
        """
        self.config = config
        self.db_manager = db_manager
        self.event_bus = event_bus
        self.import_service = import_service
        self.statistics_service = statistics_service
        
        # Репозитории для прямого доступа к данным
        self._tournament_repo = TournamentRepository()
        self._session_repo = SessionRepository()
        
        logger.info("AppFacade инициализирован")
    
    # === Управление базами данных ===
    
    @property
    def db_path(self) -> str:
        """Возвращает путь к текущей базе данных."""
        return self.db_manager.db_path
    
    def get_available_databases(self) -> List[str]:
        """Возвращает список доступных файлов баз данных."""
        return self.db_manager.get_available_databases()
    
    def switch_database(self, db_path: str, load_stats: bool = True):
        """
        Переключает активную базу данных.
        
        Args:
            db_path: Путь к новой БД
            load_stats: Загружать ли статистику сразу
        """
        old_path = self.db_manager.db_path
        self.db_manager.set_db_path(db_path)
        self.config.set_current_db_path(db_path)
        
        # Публикуем событие о смене БД
        self.event_bus.publish(DatabaseChangedEvent(
            timestamp=datetime.now(),
            source="AppFacade",
            old_db_path=old_path,
            new_db_path=db_path
        ))
        
        if load_stats:
            # Подгружаем статистику для новой БД
            self.statistics_service.ensure_overall_stats_cached(db_path)
        
        logger.info(f"База данных переключена на: {db_path}")
    
    def create_new_database(self, db_name: str):
        """
        Создает новую базу данных и переключается на нее.
        
        Args:
            db_name: Имя новой БД
        """
        new_db_path = os.path.join(self.config.db_dir, db_name)
        if not new_db_path.lower().endswith(".db"):
            new_db_path += ".db"
        
        if os.path.exists(new_db_path):
            logger.warning(f"Попытка создать существующую БД: {new_db_path}")
            raise FileExistsError(f"База данных '{os.path.basename(new_db_path)}' уже существует.")
        
        self.db_manager.set_db_path(new_db_path)
        self.config.set_current_db_path(new_db_path)
        
        # Принудительно открываем соединение, чтобы создать файл
        conn = self.db_manager.get_connection()
        self.db_manager.close_connection()
        
        # Публикуем событие
        self.event_bus.publish(DatabaseChangedEvent(
            timestamp=datetime.now(),
            source="AppFacade",
            old_db_path=None,
            new_db_path=new_db_path
        ))
        
        logger.info(f"Создана новая база данных: {new_db_path}")
    
    def rename_database(self, old_path: str, new_name: str) -> str:
        """
        Переименовывает файл базы данных.
        
        Args:
            old_path: Текущий путь к БД
            new_name: Новое имя БД
            
        Returns:
            Новый путь к БД
        """
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        if not new_path.lower().endswith(".db"):
            new_path += ".db"
        
        if os.path.exists(new_path):
            raise FileExistsError(
                f"База данных '{os.path.basename(new_path)}' уже существует."
            )
        
        # Закрываем соединение перед переименованием
        self.db_manager.close_all_connections()
        os.rename(old_path, new_path)
        
        # Обновляем кеши в сервисе статистики
        self.statistics_service.update_cache_for_renamed_db(old_path, new_path)
        
        # Если переименовали текущую БД, переключаемся на нее
        if self.db_manager.db_path == old_path:
            self.switch_database(new_path, load_stats=False)
        
        return new_path
    
    # === Импорт данных ===
    
    def import_files(
        self,
        paths: List[str],
        session_name: str | None,
        session_id: str | None = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_canceled_callback: Optional[Callable[[], bool]] = None,
    ):
        """
        Импортирует файлы через ImportService и обновляет статистику.
        
        Args:
            paths: Список путей к файлам или папкам
            session_name: Имя новой сессии
            session_id: ID существующей сессии
            progress_callback: Callback для прогресса
            is_canceled_callback: Callback для проверки отмены
        """
        # Выполняем импорт через сервис
        import_result = self.import_service.import_files(
            paths=paths,
            session_name=session_name,
            session_id=session_id,
            progress_callback=progress_callback,
            is_canceled_callback=is_canceled_callback
        )
        
        if import_result:
            imported_session_id = import_result['session_id']
            imported_tournaments = import_result['imported_tournaments']
            imported_hands = import_result['imported_hands']
            updated_tournament_ids = import_result['updated_tournament_ids']
            
            # Публикуем событие об импорте
            all_tournament_ids = [t.tournament_id for t in imported_tournaments] + updated_tournament_ids
            self.event_bus.publish(DataImportedEvent(
                timestamp=datetime.now(),
                source="AppFacade",
                session_id=imported_session_id,
                imported_tournament_ids=all_tournament_ids,
                files_processed=len(paths),  # Упрощение
                tournaments_saved=len(imported_tournaments),
                hands_saved=len(imported_hands)
            ))
            
            # Обновляем статистику с использованием инкрементального обновления
            self.statistics_service.update_all_statistics(
                session_id=imported_session_id,
                db_path=self.db_path,
                progress_callback=progress_callback,
                added_tournaments=imported_tournaments,
                added_hands=imported_hands,
                use_incremental=True
            )
            
            # Публикуем событие об обновлении статистики
            self.event_bus.publish(StatisticsUpdatedEvent(
                timestamp=datetime.now(),
                source="AppFacade",
                db_path=self.db_path,
                session_id=imported_session_id,
                is_overall=True,
                is_session=True,
                is_incremental=True
            ))
    
    # === Работа с данными ===
    
    def get_overall_stats(self) -> OverallStats:
        """Возвращает общую статистику."""
        return self.statistics_service.get_overall_stats(self.db_path)
    
    def get_all_tournaments(self, buyin_filter: Optional[float] = None) -> List[Tournament]:
        """Возвращает список всех турниров."""
        return self._tournament_repo.get_all_tournaments(buyin_filter=buyin_filter)
    
    def get_all_sessions(self) -> List[Session]:
        """Возвращает список всех сессий."""
        return self._session_repo.get_all_sessions()
    
    def get_place_distribution(self) -> Dict[int, int]:
        """Возвращает распределение мест на финальном столе."""
        return self.statistics_service.get_place_distribution(self.db_path)
    
    def get_place_distribution_for_session(self, session_id: str) -> tuple[Dict[int, int], int]:
        """Возвращает распределение мест для конкретной сессии."""
        return self.statistics_service.get_place_distribution_for_session(session_id)
    
    def get_distinct_buyins(self) -> List[float]:
        """Возвращает список уникальных бай-инов."""
        return self._tournament_repo.get_distinct_buyins()
    
    def get_session_stats(self, session_id: str) -> Optional[Session]:
        """Возвращает статистику для указанной сессии."""
        return self._session_repo.get_session_by_id(session_id)
    
    # === Управление данными ===
    
    def delete_session(self, session_id: str):
        """
        Удаляет сессию и все связанные данные.
        
        Args:
            session_id: ID сессии для удаления
        """
        # Удаляем сессию (каскадное удаление удалит связанные данные)
        self._session_repo.delete_session_by_id(session_id)
        
        # Публикуем событие
        self.event_bus.publish(SessionDeletedEvent(
            timestamp=datetime.now(),
            source="AppFacade",
            session_id=session_id,
            db_path=self.db_path
        ))
        
        # Инвалидируем кеш статистики
        self.statistics_service.invalidate_cache(self.db_path)
        
        # Публикуем событие об инвалидации кеша
        self.event_bus.publish(CacheInvalidatedEvent(
            timestamp=datetime.now(),
            source="AppFacade",
            db_path=self.db_path,
            reason=f"Session {session_id} deleted"
        ))
    
    def rename_session(self, session_id: str, new_name: str):
        """
        Переименовывает сессию.
        
        Args:
            session_id: ID сессии
            new_name: Новое имя
        """
        self._session_repo.update_session_name(session_id, new_name)
    
    def delete_tournament(self, tournament_id: str):
        """
        Удаляет турнир и связанные с ним данные.
        
        Args:
            tournament_id: ID турнира для удаления
        """
        # Получаем информацию о турнире перед удалением
        tournament = self._tournament_repo.get_tournament_by_id(tournament_id)
        if tournament:
            session_id = tournament.session_id
            
            # Удаляем турнир
            self._tournament_repo.delete_tournament_by_id(tournament_id)
            
            # Публикуем событие
            self.event_bus.publish(TournamentDeletedEvent(
                timestamp=datetime.now(),
                source="AppFacade",
                tournament_id=tournament_id,
                session_id=session_id,
                db_path=self.db_path
            ))
            
            # Инвалидируем кеш статистики
            self.statistics_service.invalidate_cache(self.db_path)
            
            # Публикуем событие об инвалидации кеша
            self.event_bus.publish(CacheInvalidatedEvent(
                timestamp=datetime.now(),
                source="AppFacade",
                db_path=self.db_path,
                reason=f"Tournament {tournament_id} deleted"
            ))
    
    # === Прямой доступ к репозиториям (для совместимости) ===
    
    @property
    def tournament_repo(self):
        """Предоставляет прямой доступ к репозиторию турниров."""
        return self._tournament_repo
    
    @property
    def session_repo(self):
        """Предоставляет прямой доступ к репозиторию сессий."""
        return self._session_repo