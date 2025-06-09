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
from viewmodels import StatsGridViewModel

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
    
    def get_tournaments_filtered(
        self,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        start_time_from: Optional[str] = None,
        start_time_to: Optional[str] = None
    ) -> List[Tournament]:
        """
        Возвращает отфильтрованный список турниров.
        
        Args:
            session_id: ID сессии для фильтрации
            buyin_filter: Фильтр по байину
            start_time_from: Начальная дата
            start_time_to: Конечная дата
            
        Returns:
            Список отфильтрованных турниров
        """
        return self._tournament_repo.get_all_tournaments(
            session_id=session_id,
            buyin_filter=buyin_filter,
            start_time_from=start_time_from,
            start_time_to=start_time_to
        )
    
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
    
    def get_tournaments_paginated(
        self,
        page: int,
        page_size: int,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        result_filter: Optional[str] = None,
        start_time_from: Optional[str] = None,
        start_time_to: Optional[str] = None,
        sort_column: str = "start_time",
        sort_direction: str = "DESC"
    ):
        """
        Возвращает турниры с пагинацией и фильтрами.
        Делегирует вызов к репозиторию турниров.
        """
        return self._tournament_repo.get_tournaments_paginated(
            page=page,
            page_size=page_size,
            session_id=session_id,
            buyin_filter=buyin_filter,
            result_filter=result_filter,
            start_time_from=start_time_from,
            start_time_to=start_time_to,
            sort_column=sort_column,
            sort_direction=sort_direction
        )
    
    def ensure_overall_stats_cached(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        """
        Обеспечивает наличие кешированной общей статистики.
        Делегирует вызов к StatisticsService.
        
        Args:
            progress_callback: Callback для отслеживания прогресса
        """
        self.statistics_service.ensure_overall_stats_cached(
            db_path=self.db_path,
            progress_callback=progress_callback
        )

    def update_all_statistics(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """Пересчитывает всю статистику в текущей базе данных."""
        self.statistics_service.update_all_statistics(
            session_id="",
            db_path=self.db_path,
            progress_callback=progress_callback,
            use_incremental=False,
        )
    
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
    
    # === ViewModel методы для UI ===
    
    def create_stats_grid_viewmodel(
        self,
        session_id: Optional[str] = None,
        buyin_filter: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> StatsGridViewModel:
        """
        Создает ViewModel для StatsGrid с учетом фильтров.
        
        Args:
            session_id: ID сессии для фильтрации
            buyin_filter: Фильтр по байину
            date_from: Начальная дата (формат YYYY/MM/DD HH:MM:SS)
            date_to: Конечная дата (формат YYYY/MM/DD HH:MM:SS)
            
        Returns:
            StatsGridViewModel с готовыми для отображения данными
        """
        # Получаем отфильтрованные турниры
        tournaments = self._tournament_repo.get_all_tournaments(
            session_id=session_id,
            buyin_filter=buyin_filter,
            start_time_from=date_from,
            start_time_to=date_to
        )
        
        # Получаем руки финального стола
        if buyin_filter is not None:
            # Если есть фильтр по байину, получаем список tournament_id
            tournament_ids = [t.tournament_id for t in tournaments]
            ft_hand_repo = FinalTableHandRepository()
            ft_hands = ft_hand_repo.get_hands_by_filters(
                session_id=session_id,
                tournament_ids=tournament_ids if tournament_ids else None
            )
        else:
            # Если нет фильтра по байину, фильтруем только по сессии
            ft_hand_repo = FinalTableHandRepository()
            ft_hands = ft_hand_repo.get_hands_by_filters(session_id=session_id)
        
        # Вычисляем общую статистику для отфильтрованных данных
        overall_stats = self._compute_overall_stats_filtered(tournaments, ft_hands)
        
        # Подготавливаем предварительно рассчитанные значения
        precomputed_stats = {
            'total_tournaments': overall_stats.total_tournaments,
            'total_buy_in': overall_stats.total_buy_in,
            'total_prize': overall_stats.total_prize,
            'total_knockouts': overall_stats.total_knockouts,
            'total_final_tables': overall_stats.total_final_tables,
        }
        
        # Создаем ViewModel
        return StatsGridViewModel.create_from_data(
            tournaments=tournaments,
            final_table_hands=ft_hands,
            overall_stats=overall_stats,
            precomputed_stats=precomputed_stats
        )
    
    def _compute_overall_stats_filtered(self, tournaments, ft_hands) -> OverallStats:
        """
        Вычисляет агрегированную статистику по отфильтрованным данным.
        Временный метод для совместимости - позже будет перенесен в StatisticsService.
        """
        stats = OverallStats()
        stats.total_tournaments = len(tournaments)
        
        # Оптимизированный подсчет с одним проходом по турнирам
        ft_count = 0
        total_buyin = 0.0
        total_prize = 0.0
        total_ko = 0.0
        ft_chips_sum = 0.0
        ft_chips_count = 0
        ft_bb_sum = 0.0
        ft_bb_count = 0
        early_bust_count = 0
        
        for t in tournaments:
            if t.reached_final_table:
                ft_count += 1
                if t.final_table_initial_stack_chips is not None:
                    ft_chips_sum += t.final_table_initial_stack_chips
                    ft_chips_count += 1
                if t.final_table_initial_stack_bb is not None:
                    ft_bb_sum += t.final_table_initial_stack_bb
                    ft_bb_count += 1
                if t.finish_place is not None and 6 <= t.finish_place <= 9:
                    early_bust_count += 1
            
            if t.buyin is not None:
                total_buyin += t.buyin
            if t.payout is not None:
                total_prize += t.payout
            total_ko += t.ko_count
        
        stats.total_final_tables = ft_count
        stats.total_buy_in = total_buyin
        stats.total_prize = total_prize
        stats.total_knockouts = round(total_ko, 1)
        stats.avg_ko_per_tournament = total_ko / stats.total_tournaments if stats.total_tournaments else 0.0
        stats.final_table_reach_percent = ft_count / stats.total_tournaments * 100 if stats.total_tournaments else 0.0
        stats.avg_ft_initial_stack_chips = ft_chips_sum / ft_chips_count if ft_chips_count else 0.0
        stats.avg_ft_initial_stack_bb = ft_bb_sum / ft_bb_count if ft_bb_count else 0.0
        stats.early_ft_bust_count = early_bust_count
        stats.early_ft_bust_per_tournament = early_bust_count / ft_count if ft_count else 0.0
        
        # Подсчет Big KO через плагин
        from stats import BigKOStat
        big_ko_res = BigKOStat().compute(tournaments, ft_hands)
        stats.big_ko_x1_5 = big_ko_res.get("x1.5", 0)
        stats.big_ko_x2 = big_ko_res.get("x2", 0)
        stats.big_ko_x10 = big_ko_res.get("x10", 0)
        stats.big_ko_x100 = big_ko_res.get("x100", 0)
        stats.big_ko_x1000 = big_ko_res.get("x1000", 0)
        stats.big_ko_x10000 = big_ko_res.get("x10000", 0)
        
        # Подсчет early FT KO
        early_ko_count = sum(hand.hero_ko_this_hand for hand in ft_hands if hand.is_early_final)
        stats.early_ft_ko_count = early_ko_count
        stats.early_ft_ko_per_tournament = early_ko_count / ft_count if ft_count else 0.0
        
        # Pre-FT KO
        stats.pre_ft_ko_count = sum(hand.pre_ft_ko for hand in ft_hands)
        
        return stats

    # === Прямой доступ к репозиториям (для совместимости) ===
    
    @property
    def tournament_repo(self):
        """Предоставляет прямой доступ к репозиторию турниров."""
        return self._tournament_repo
    
    @property
    def session_repo(self):
        """Предоставляет прямой доступ к репозиторию сессий."""
        return self._session_repo