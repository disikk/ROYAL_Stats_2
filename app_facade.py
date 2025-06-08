# -*- coding: utf-8 -*-
class ImportService: pass
class StatisticsService: pass
from typing import Any, List, Dict, Optional, Callable # Ensure Callable is here for progress_callback
import os
import logging
import json
import hashlib
import config
from db.repositories import (
    TournamentRepository,
    PaginationResult,
    SessionRepository,
    OverallStatsRepository,
    PlaceDistributionRepository,
    FinalTableHandRepository,
)
from models import Tournament, Session, OverallStats, FinalTableHand

logger = logging.getLogger('ROYAL_Stats.AppFacade')

class AppFacade:
    def __init__(self,
                 import_service: ImportService,
                 statistics_service: StatisticsService,
                 db_manager_instance: Any,
                 tournament_repo: TournamentRepository,
                 session_repo: SessionRepository,
                 overall_stats_repo: OverallStatsRepository, # Keep for type hints if needed
                 place_dist_repo: PlaceDistributionRepository, # Keep for type hints if needed
                 ft_hand_repo: FinalTableHandRepository): # Keep for type hints if needed
        self.import_service = import_service
        self.statistics_service = statistics_service
        self.db = db_manager_instance
        self._tournament_repo = tournament_repo
        self.session_repo = session_repo
        # These repos below might not be directly used by AppFacade if all stats logic is in StatisticsService
        self.overall_stats_repo = overall_stats_repo
        self.place_dist_repo = place_dist_repo
        self.ft_hand_repo = ft_hand_repo
        logger.info("AppFacade initialized")

    @property
    def tournament_repo(self): # This property might still be useful for UI direct access for pagination
        return self._tournament_repo

    @property
    def db_path(self) -> str:
        return self.db.db_path

    # --- Import-related method ---
    def import_files(
        self,
        paths: List[str],
        session_name: Optional[str],
        session_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        is_canceled_callback: Optional[Callable[[], bool]] = None,
    ):
        logger.info(f"AppFacade: Delegating import to ImportService. Session: {session_name or session_id}")
        self.import_service.import_files(
            paths, session_name, session_id, progress_callback, is_canceled_callback
        )
        logger.info("AppFacade: Import complete. Triggering statistics update.")
        # Pass the specific session_id if known, otherwise None for a potentially broader update.
        # The import_service doesn't currently return the active session_id if one was created.
        # This is a detail to refine. For now, triggering a general cache check/update.
        self.statistics_service.ensure_overall_stats_cached(progress_callback=progress_callback)


    # --- Statistics Getter Methods (delegating to StatisticsService) ---
    def ensure_overall_stats_cached(self, progress_callback=None) -> None:
        self.statistics_service.ensure_overall_stats_cached(progress_callback)

    def get_overall_stats(self) -> Optional[OverallStats]: # Type hint from models.OverallStats
        return self.statistics_service.get_overall_stats()

    def get_place_distribution(self) -> Dict[int, int]:
        return self.statistics_service.get_place_distribution()

    def get_place_distribution_pre_ft(self) -> Dict[int, int]:
        # This logic was simple and didn't use cache in original ApplicationService.
        # It could live here or be moved to StatisticsService for consistency.
        # For now, let's assume it's moved to StatisticsService.
        return self.statistics_service.get_place_distribution_pre_ft()

    def get_place_distribution_overall(self) -> Dict[int, int]:
        # Similar to pre_ft, this was a direct calculation.
        return self.statistics_service.get_place_distribution_overall()

    def get_session_stats(self, session_id: str) -> Optional[Session]: # Type hint from models.Session
        return self.statistics_service.get_session_stats(session_id)

    def get_place_distribution_for_session(self, session_id: str) -> Dict[int, int]: # Or Tuple
        # Assuming StatisticsService.get_place_distribution_for_session is updated to return what's needed
        # or this Facade method adapts the result.
        # The prompt's StatisticsService skeleton for this method returns Dict[int,int], not tuple.
        # If StatisticsService is changed to return tuple, this is fine. If not, this Facade method needs to adapt.
        # For now, directly returning what service provides.
        result = self.statistics_service.get_place_distribution_for_session(session_id)
        # If service returns tuple (dist, count), and facade needs only dist: return result[0]
        # If service returns dict, and facade needs dict: return result
        # Assuming service will align with original tuple or this facade adapts.
        # For now, let's assume the skeleton for stat service was simplified and it might return a tuple.
        # Or, if it strictly returns Dict, then this facade method signature here is wrong.
        # Let's stick to the prompt's skeleton for StatisticsService which returns Dict[int,int]
        return result


    # --- Database and Session/Tournament Management Methods ---
    # These methods might interact with StatisticsService for cache invalidation or updates.
    def get_available_databases(self) -> List[str]:
        return self.db.get_available_databases()

    def switch_database(self, db_path: str, load_stats: bool = True):
        self.db.set_db_path(db_path)
        if load_stats:
            self.statistics_service.ensure_overall_stats_cached()
        else:
            # If not loading stats, an explicit cache clear for the new db_path might be needed
            # if StatisticsService doesn't automatically handle it based on db_path.
            # For now, assume ensure_overall_stats_cached is sufficient or a new method in StatsService.
            # The prompt's V2 content added a _clear_cache_for_db call.
            if hasattr(self.statistics_service, '_clear_cache_for_db'):
                self.statistics_service._clear_cache_for_db(db_path)
            else:
                logger.warning("_clear_cache_for_db not found on StatisticsService, cache might be stale after switch_database if not loading stats.")


    def create_new_database(self, db_name: str):
        # Copied from ApplicationService, seems okay.
        new_db_path = os.path.join(config.DEFAULT_DB_DIR, db_name)
        if not new_db_path.lower().endswith(".db"):
            new_db_path += ".db"
        if os.path.exists(new_db_path):
            raise FileExistsError(f"База данных '{os.path.basename(new_db_path)}' уже существует.")
        self.db.set_db_path(new_db_path)
        conn = self.db.get_connection() # Creates and initializes schema
        if conn: # Ensure connection was made before trying to close
            self.db.close_connection(conn)
        logger.info(f"Создана и выбрана новая база данных: {new_db_path}")
        # New DB is empty, ensure_overall_stats_cached will set up empty stats.
        self.statistics_service.ensure_overall_stats_cached()


    def rename_database(self, old_path: str, new_name: str) -> str:
        # This needs to interact with StatisticsService cache.
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        if not new_path.lower().endswith(".db"):
            new_path += ".db"
        if os.path.exists(new_path):
            raise FileExistsError(f"База данных '{os.path.basename(new_path)}' уже существует.")

        current_db_was_renamed = (self.db.db_path == old_path)
        self.db.close_all_connections()
        os.rename(old_path, new_path)

        if hasattr(self.statistics_service, '_clear_cache_for_db'):
            self.statistics_service._clear_cache_for_db(old_path) # Remove old cache entries
        else:
            logger.warning("_clear_cache_for_db not found on StatisticsService, cache might be stale for old_path.")

        if current_db_was_renamed:
            self.db.set_db_path(new_path) # Point DB manager to new path
            self.statistics_service.ensure_overall_stats_cached() # Load/init cache for new_path
        return new_path

    def delete_session(self, session_id: str):
        self.session_repo.delete_session_by_id(session_id) # This should cascade delete tournaments, hands
        logger.info(f"Сессия {session_id} удалена. Обновление статистики...")
        # This was: self._update_all_statistics(session_id) - but session_id is now gone.
        # So, a global recalculation or a more sophisticated diff-based update is needed.
        # For now, trigger a global update.
        self.statistics_service._update_all_statistics(session_id=None) # Global update

    def rename_session(self, session_id: str, new_name: str):
        self.session_repo.update_session_name(session_id, new_name)
        # No stats change, so no call to StatisticsService needed.

    def delete_tournament(self, tournament_id: str):
        self._tournament_repo.delete_tournament_by_id(tournament_id) # Cascade delete hands for this tourney
        logger.info(f"Турнир {tournament_id} удален. Обновление статистики...")
        # Similar to delete_session, trigger a global stats update.
        self.statistics_service._update_all_statistics(session_id=None) # Global update

    # --- Direct Data Query Methods (may move to a query service later) ---
    def get_all_tournaments(self, buyin_filter: Optional[float] = None, session_id: Optional[str] = None) -> List[Tournament]:
        # Original ApplicationService had get_all_tournaments(buyin_filter)
        # The repo method is get_all_tournaments(session_id=None, buyin_filter=None)
        # This facade method should match UI needs or common use cases.
        return self._tournament_repo.get_all_tournaments(session_id=session_id, buyin_filter=buyin_filter)

    def get_all_sessions(self) -> List[Session]:
        return self.session_repo.get_all_sessions()

    def get_distinct_buyins(self) -> List[float]:
        return self._tournament_repo.get_distinct_buyins()

    # Methods that were placeholders for moved logic and should be GONE from AppFacade:
    # _compute_db_checksum, _load_persistent_cache, _save_persistent_cache
    # _update_all_statistics (the facade calls the service's one, doesn't implement its own)
    # _calculate_overall_stats, _calculate_and_update_session_stats
