# -*- coding: utf-8 -*-

"""
Точка входа в приложение Royal Stats (Hero-only).
"""

import os
import sys
from PyQt6 import QtWidgets
from typing import List, Type # Added for STAT_PLUGINS type hint

# --- Configuration and Core Components ---
import config # For APP_TITLE, APP_VERSION, DEBUG, STATS_CACHE_FILE etc.

# --- Database ---
from db.manager import database_manager # Singleton DB manager
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    OverallStatsRepository,
    PlaceDistributionRepository,
    FinalTableHandRepository,
)

# --- Parsers ---
from parsers import HandHistoryParser, TournamentSummaryParser

# --- Statistics Plugins ---
from stats.base import BaseStat
from stats import (
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

# --- Services ---
from app_facade import AppFacade
from import_service import ImportService
from statistics_service import StatisticsService

# --- UI ---
from ui.main_window import MainWindow
from ui.app_style import apply_dark_theme

import logging

logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ROYAL_Stats.App')

STAT_PLUGINS_INSTANCES: List[BaseStat] = [
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

def main():
    logger.info(f"Запуск приложения {config.APP_TITLE} v{config.APP_VERSION}")
    logger.info(f"Текущая рабочая директория: {os.getcwd()}")

    db_mngr = database_manager

    tournament_repo = TournamentRepository()
    session_repo = SessionRepository()
    overall_stats_repo = OverallStatsRepository()
    place_dist_repo = PlaceDistributionRepository()
    ft_hand_repo = FinalTableHandRepository()

    hh_parser = HandHistoryParser()
    ts_parser = TournamentSummaryParser()

    import_service = ImportService(
        db_manager_instance=db_mngr,
        tournament_repo=tournament_repo,
        session_repo=session_repo,
        ft_hand_repo=ft_hand_repo,
        hh_parser=hh_parser,
        ts_parser=ts_parser
    )

    statistics_service = StatisticsService(
        db_manager_instance=db_mngr,
        tournament_repo=tournament_repo,
        session_repo=session_repo,
        overall_stats_repo=overall_stats_repo,
        place_dist_repo=place_dist_repo,
        ft_hand_repo=ft_hand_repo,
        stat_plugins=STAT_PLUGINS_INSTANCES,
        config_cache_file=config.STATS_CACHE_FILE,
        app_config_obj=config
    )

    app_facade = AppFacade(
        import_service=import_service,
        statistics_service=statistics_service,
        db_manager_instance=db_mngr,
        tournament_repo=tournament_repo,
        session_repo=session_repo,
        overall_stats_repo=overall_stats_repo,
        place_dist_repo=place_dist_repo,
        ft_hand_repo=ft_hand_repo
    )

    app = QtWidgets.QApplication(sys.argv)
    apply_dark_theme(app)

    main_window = MainWindow(app_facade=app_facade)
    main_window.show()

    exit_code = app.exec()
    logger.info("Приложение завершило работу.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()