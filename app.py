# -*- coding: utf-8 -*-

"""
Точка входа в приложение Royal Stats (Hero-only).
"""

import os
import sys
import logging
import importlib
from PyQt6 import QtWidgets

# Импорты для UI
from ui.main_window import MainWindow
from ui.app_style import apply_dark_theme

# Импорты для DI контейнера
from services import (
    app_config,
    AppConfig,
    AppFacade,
    ImportService,
    StatisticsService,
    EventBus,
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


# Настройка базового логгирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ROYAL_Stats.App")


class DependencyContainer:
    """
    Контейнер для управления зависимостями приложения.
    Создает и настраивает все компоненты с правильными зависимостями.
    """

    @staticmethod
    def load_class(path: str):
        """Загружает класс по строковому пути."""
        module_path, class_name = path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def __init__(self):
        # Загружаем конфигурацию
        self.config = self._create_config()

        # Настраиваем уровень логирования
        if self.config.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        # Создаем шину событий
        self.event_bus = self._create_event_bus()

        # Создаем менеджер БД
        self.db_manager = database_manager
        self.db_manager.set_db_path(self.config.current_db_path)

        # Создаем репозитории
        self.tournament_repo = TournamentRepository(self.db_manager)
        self.session_repo = SessionRepository(self.db_manager)
        self.overall_stats_repo = OverallStatsRepository(self.db_manager)
        self.place_dist_repo = PlaceDistributionRepository(self.db_manager)
        self.ft_hand_repo = FinalTableHandRepository(self.db_manager)

        # Создаем парсеры
        self.hh_parser = HandHistoryParser(self.config.hero_name)
        self.ts_parser = TournamentSummaryParser(self.config.hero_name)

        # Создаем сервисы
        self.import_service = self._create_import_service()
        self.statistics_service = self._create_statistics_service()

        # Создаем фасад приложения
        self.app_facade = self._create_app_facade()

    def _create_config(self) -> AppConfig:
        """Возвращает глобальную конфигурацию приложения."""
        return app_config

    def _create_event_bus(self):
        """Создает экземпляр шины событий."""
        bus_cls_path = self.config.services.get("event_bus")
        bus_cls = self.load_class(bus_cls_path)
        return bus_cls()

    def _create_import_service(self) -> ImportService:
        """Создает сервис импорта с зависимостями."""
        service_cls = self.load_class(self.config.services.get("import_service"))
        return service_cls(
            tournament_repo=self.tournament_repo,
            session_repo=self.session_repo,
            ft_hand_repo=self.ft_hand_repo,
            hh_parser=self.hh_parser,
            ts_parser=self.ts_parser,
            event_bus=self.event_bus,
        )

    def _create_statistics_service(self) -> StatisticsService:
        """Создает сервис статистики с зависимостями."""
        service_cls = self.load_class(self.config.services.get("statistics_service"))
        return service_cls(
            tournament_repo=self.tournament_repo,
            session_repo=self.session_repo,
            overall_stats_repo=self.overall_stats_repo,
            place_dist_repo=self.place_dist_repo,
            ft_hand_repo=self.ft_hand_repo,
            cache_file_path=self.config.stats_cache_file,
            stat_plugins=None,
            event_bus=self.event_bus,
        )

    def _create_app_facade(self) -> AppFacade:
        """Создает фасад приложения."""
        facade_cls = self.load_class(self.config.services.get("app_facade"))
        return facade_cls(
            config=self.config,
            db_manager=self.db_manager,
            event_bus=self.event_bus,
            import_service=self.import_service,
            statistics_service=self.statistics_service,
        )


def main():
    """
    Главная функция запуска приложения.
    """
    # Создаем контейнер зависимостей
    container = DependencyContainer()

    logger.info(
        f"Запуск приложения {container.config.app_title} v{container.config.app_version}"
    )
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
