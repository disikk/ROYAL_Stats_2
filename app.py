# -*- coding: utf-8 -*-

"""
Точка входа в приложение Royal Stats (Hero-only).
"""

import os
import sys
import logging
from PyQt6 import QtWidgets

# Импорты для UI
from ui.main_window import MainWindow
from ui.app_style import apply_dark_theme

# Импорты для DI контейнера
from services import (
    AppConfig,
    AppFacade,
    ImportService,
    StatisticsService,
    EventBus,
    get_event_bus
)
from db.manager import database_manager
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    OverallStatsRepository,
    PlaceDistributionRepository,
    FinalTableHandRepository,
)
from parsers import HandHistoryParser, TournamentSummaryParser
from stats import (
    BaseStat,
    BigKOStat,
    ITMStat,
    ROIStat,
    TotalKOStat,
    AvgKOPerTournamentStat,
    FinalTableReachStat,
    AvgFTInitialStackStat,
    EarlyFTKOStat,
    EarlyFTBustStat,
    PreFTKOStat,
    AvgFinishPlaceStat,
    AvgFinishPlaceFTStat,
    AvgFinishPlaceNoFTStat,
    FTStackConversionStat,
)

# Настройка базового логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ROYAL_Stats.App')


class DependencyContainer:
    """
    Контейнер для управления зависимостями приложения.
    Создает и настраивает все компоненты с правильными зависимостями.
    """
    
    def __init__(self):
        # Загружаем конфигурацию
        self.config = self._create_config()
        
        # Настраиваем уровень логирования
        if self.config.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Создаем шину событий
        self.event_bus = get_event_bus()
        
        # Создаем менеджер БД
        self.db_manager = database_manager
        self.db_manager.set_db_path(self.config.current_db_path)
        
        # Создаем репозитории
        self.tournament_repo = TournamentRepository()
        self.session_repo = SessionRepository()
        self.overall_stats_repo = OverallStatsRepository()
        self.place_dist_repo = PlaceDistributionRepository()
        self.ft_hand_repo = FinalTableHandRepository()
        
        # Создаем парсеры
        self.hh_parser = HandHistoryParser(self.config.hero_name)
        self.ts_parser = TournamentSummaryParser(self.config.hero_name)
        
        # Создаем сервисы
        self.import_service = self._create_import_service()
        self.statistics_service = self._create_statistics_service()
        
        # Создаем фасад приложения
        self.app_facade = self._create_app_facade()
    
    def _create_config(self) -> AppConfig:
        """Создает конфигурацию приложения."""
        try:
            # Пытаемся создать из существующего config.py
            return AppConfig.from_legacy_config()
        except Exception:
            # Если не удалось, создаем дефолтную
            logger.warning("Не удалось загрузить legacy config, используем дефолтную конфигурацию")
            return AppConfig()
    
    def _create_import_service(self) -> ImportService:
        """Создает сервис импорта с зависимостями."""
        return ImportService(
            tournament_repo=self.tournament_repo,
            session_repo=self.session_repo,
            ft_hand_repo=self.ft_hand_repo,
            hh_parser=self.hh_parser,
            ts_parser=self.ts_parser,
            event_bus=self.event_bus
        )
    
    def _create_statistics_service(self) -> StatisticsService:
        """Создает сервис статистики с зависимостями."""
        # Создаем плагины статистики
        stat_plugins = [
            TotalKOStat(),
            ITMStat(),
            ROIStat(),
            BigKOStat(),
            AvgKOPerTournamentStat(),
            FinalTableReachStat(),
            AvgFTInitialStackStat(),
            EarlyFTKOStat(),
            EarlyFTBustStat(),
            PreFTKOStat(),
            AvgFinishPlaceStat(),
            AvgFinishPlaceFTStat(),
            AvgFinishPlaceNoFTStat(),
            FTStackConversionStat(),
        ]
        
        return StatisticsService(
            tournament_repo=self.tournament_repo,
            session_repo=self.session_repo,
            overall_stats_repo=self.overall_stats_repo,
            place_dist_repo=self.place_dist_repo,
            ft_hand_repo=self.ft_hand_repo,
            cache_file_path=self.config.stats_cache_file,
            stat_plugins=stat_plugins,
            event_bus=self.event_bus
        )
    
    def _create_app_facade(self) -> AppFacade:
        """Создает фасад приложения."""
        return AppFacade(
            config=self.config,
            db_manager=self.db_manager,
            event_bus=self.event_bus,
            import_service=self.import_service,
            statistics_service=self.statistics_service
        )


def main():
    """
    Главная функция запуска приложения.
    """
    # Создаем контейнер зависимостей
    container = DependencyContainer()
    
    logger.info(f"Запуск приложения {container.config.app_title} v{container.config.app_version}")
    logger.info(f"Текущая рабочая директория: {os.getcwd()}")
    logger.info(f"База данных: {container.config.current_db_path}")

    app = QtWidgets.QApplication(sys.argv)

    # Применяем тему
    apply_dark_theme(app)

    # Создаем и показываем главное окно
    # Передаем фасад приложения в главное окно
    main_window = MainWindow(app_facade=container.app_facade)
    main_window.show()

    # Запускаем приложение
    exit_code = app.exec()
    logger.info("Приложение завершило работу.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()