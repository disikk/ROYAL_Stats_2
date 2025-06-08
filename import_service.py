# -*- coding: utf-8 -*-
import os
import logging
import json # Not used in extracted code, but was in original AppService imports for import_files context
import hashlib # Not used in extracted code, but was in original AppService imports for import_files context
import uuid # Not used in extracted code, but was in original AppService imports for import_files context
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime # Used for default session name
import math # Not used in extracted code, but was in original AppService imports for import_files context
import re # Not used in extracted code, but was in original AppService imports for import_files context

# Specific imports based on extracted code needs and original context
import config # Used by logger setup
# db.manager is passed in __init__, so direct import might not be needed by the class itself,
# but logger setup might use it.
# from db.manager import database_manager
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    FinalTableHandRepository
)
from parsers import HandHistoryParser, TournamentSummaryParser
from models import Tournament, Session, FinalTableHand # These are needed by import_files

logger = logging.getLogger('ROYAL_Stats.ImportService') # As per prompt
if hasattr(config, 'DEBUG'): # As per prompt
    logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
else:
    logger.setLevel(logging.INFO)

# --- determine_file_type function ---
def determine_file_type(file_path: str) -> Optional[str]:
    """
    Определяет тип покерного файла по первым двум строкам.

    Returns:
        'ts' - Tournament Summary
        'hh' - Hand History
        None - файл не соответствует ожидаемым форматам
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        if len(lines) < 2:
            return None

        first_line = lines[0].strip()
        second_line = lines[1].strip()

        if (first_line.startswith("Tournament #") and
            "Mystery Battle Royale" in first_line and
            second_line.startswith("Buy-in:")):
            return 'ts'

        if (first_line.startswith("Poker Hand #") and
            "Mystery Battle Royale" in first_line and
            second_line.startswith("Table")):
            return 'hh'

        return None

    except Exception as e:
        # Use the module-level logger
        logger.warning(f"Не удалось прочитать файл {file_path}: {e}")
        return None

# --- is_poker_file function ---
def is_poker_file(file_path: str) -> bool:
    """
    Предварительная проверка файла - является ли покерным файлом.
    Возвращает True, если файл соответствует ожидаемым форматам.
    """
    return determine_file_type(file_path) is not None

class ImportService:
    def __init__(self,
                 db_manager_instance: Any, # As per prompt
                 tournament_repo: TournamentRepository,
                 session_repo: SessionRepository,
                 ft_hand_repo: FinalTableHandRepository,
                 hh_parser: HandHistoryParser,
                 ts_parser: TournamentSummaryParser):
        self.db = db_manager_instance # As per prompt
        self.tournament_repo = tournament_repo
        self.session_repo = session_repo
        self.ft_hand_repo = ft_hand_repo
        self.hh_parser = hh_parser
        self.ts_parser = ts_parser
        logger.info("ImportService instance initialized") # As per prompt

    # --- import_files method ---
    def import_files(
        self,
        paths: List[str],
        session_name: Optional[str],
        session_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_canceled_callback: Optional[Callable[[], bool]] = None,
    ):
        """
        Импортирует файлы/папки, парсит их и сохраняет данные в БД.
        KO counts для турниров обновляются.
        Статистика после импорта НЕ обновляется этим методом (должна быть вызвана отдельно).

        Args:
            paths: Список путей к файлам или папкам.
            session_name: Имя новой сессии (используется, если session_id не задан).
            session_id: Идентификатор существующей сессии для догрузки.
            progress_callback: Optional function(current, total, text) for UI progress.
            is_canceled_callback: Optional function() that returns True if the import should be cancelled.
        """
        logger.info(f"=== НАЧАЛО ИМПОРТА (ImportService) ===")
        logger.debug(
            f"is_canceled_callback передан: {is_canceled_callback is not None}"
        )

        if progress_callback:
            progress_callback(0, 0, "Подготовка файлов...")

        total_candidates = 0
        for path_item in paths:
            if is_canceled_callback and is_canceled_callback():
                logger.info("Импорт отменен пользователем при подсчете файлов.")
                if progress_callback:
                    progress_callback(0, 0, "Импорт отменен пользователем")
                return
            if os.path.isdir(path_item):
                for _, _, filenames in os.walk(path_item):
                    if is_canceled_callback and is_canceled_callback():
                        logger.debug("Импорт отменен пользователем при подсчете файлов.")
                        if progress_callback:
                            progress_callback(0, 0, "Импорт отменен пользователем")
                        return
                    total_candidates += len([f for f in filenames if f.lower().endswith(".txt")])
            elif os.path.isfile(path_item) and path_item.lower().endswith(".txt"):
                total_candidates += 1

        all_files_to_process = []
        filtered_files_count = 0
        processed_candidates = 0
        for path_item in paths:
            if is_canceled_callback and is_canceled_callback():
                logger.info("Импорт отменен пользователем при подготовке файлов.")
                if progress_callback:
                    progress_callback(processed_candidates, total_candidates, "Импорт отменен пользователем")
                return
            if os.path.isdir(path_item):
                for root, _, filenames in os.walk(path_item):
                    for fname in filenames:
                        if is_canceled_callback and is_canceled_callback():
                            logger.debug("Импорт отменен пользователем при подготовке файлов.")
                            if progress_callback:
                                progress_callback(processed_candidates, total_candidates, "Импорт отменен пользователем")
                            return
                        if fname.lower().endswith(".txt"):
                            full_path = os.path.join(root, fname)
                            if is_poker_file(full_path):
                                all_files_to_process.append(full_path)
                            else:
                                filtered_files_count += 1
                            processed_candidates += 1
                            if progress_callback and total_candidates > 0:
                                progress_callback(processed_candidates, total_candidates, "Подготовка файлов...")
            elif os.path.isfile(path_item) and path_item.lower().endswith(".txt"):
                if is_canceled_callback and is_canceled_callback():
                    logger.debug("Импорт отменен пользователем при подготовке файлов.")
                    if progress_callback:
                        progress_callback(processed_candidates, total_candidates, "Импорт отменен пользователем")
                    return
                if is_poker_file(path_item):
                    all_files_to_process.append(path_item)
                else:
                    filtered_files_count += 1
                processed_candidates += 1
                if progress_callback and total_candidates > 0:
                    progress_callback(processed_candidates, total_candidates, "Подготовка файлов...")

        if filtered_files_count > 0:
            logger.debug(
                f"Отфильтровано {filtered_files_count} файлов без покерных шаблонов"
            )

        total_files = len(all_files_to_process)
        if total_files == 0:
            logger.info("Нет файлов для обработки.")
            if progress_callback:
                 progress_callback(0, 0, "Нет файлов для обработки")
            return

        PARSING_WEIGHT_LOCAL = 78
        SAVING_WEIGHT_LOCAL = 22

        total_steps = 100
        current_progress = 0

        logger.info(
            f"Начат импорт {total_files} файлов в сессию"
            f" '{session_name if session_id is None else session_id}' (ImportService)"
        )

        effective_session_id = session_id
        # current_session: Optional[Session] = None # Define type for clarity
        if effective_session_id:
            current_session = self.session_repo.get_session_by_id(effective_session_id)
            if not current_session:
                logger.error(f"Сессия {effective_session_id} не найдена")
                if progress_callback:
                    progress_callback(0, total_steps, f"Ошибка: Сессия не найдена")
                return
        else:
            try:
                s_name = session_name or f"Import Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                current_session = self.session_repo.create_session(s_name)
                effective_session_id = current_session.session_id # type: ignore
                logger.info(f"Создана новая сессия для импорта: {effective_session_id}")
            except Exception as e:
                logger.error(f"Не удалось создать сессию для импорта: {e}")
                if progress_callback:
                    progress_callback(0, total_steps, f"Ошибка: Не удалось создать сессию: {e}")
                return

        parsed_tournaments_data: Dict[str, Dict[str, Any]] = {}
        all_final_table_hands_data: List[Dict[str, Any]] = []

        if progress_callback:
            progress_callback(current_progress, total_steps, "Начинаем обработку файлов...")

        files_processed = 0
        for file_path in all_files_to_process:
            if is_canceled_callback and is_canceled_callback():
                logger.warning(f"=== ИМПОРТ ОТМЕНЕН при парсинге файлов (ImportService) ===")
                if progress_callback:
                    progress_callback(current_progress, total_steps, "Импорт отменен пользователем")
                return

            file_progress = int((files_processed / max(total_files,1)) * PARSING_WEIGHT_LOCAL)
            if progress_callback:
                progress_callback(file_progress, total_steps, f"Обработка: {os.path.basename(file_path)}")

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                file_type = determine_file_type(file_path)
                if file_type is None:
                    logger.warning(f"Файл не соответствует ожидаемым форматам: {file_path}. Файл пропущен.")
                    files_processed += 1
                    continue

                is_ts = file_type == 'ts'
                is_hh = file_type == 'hh'

                if is_hh:
                    hh_data = self.hh_parser.parse(content, filename=os.path.basename(file_path))
                    tourney_id = hh_data.get('tournament_id')
                    if tourney_id:
                        if tourney_id not in parsed_tournaments_data:
                             parsed_tournaments_data[tourney_id] = {'tournament_id': tourney_id, 'session_id': effective_session_id, 'ko_count': 0, 'reached_final_table': False}
                        parsed_tournaments_data[tourney_id]['start_time'] = parsed_tournaments_data[tourney_id].get('start_time') or hh_data.get('start_time')
                        if hh_data.get('reached_final_table', False):
                             parsed_tournaments_data[tourney_id]['reached_final_table'] = True
                             parsed_tournaments_data[tourney_id]['final_table_initial_stack_chips'] = hh_data.get('final_table_initial_stack_chips')
                             parsed_tournaments_data[tourney_id]['final_table_initial_stack_bb'] = hh_data.get('final_table_initial_stack_bb')
                             parsed_tournaments_data[tourney_id]['final_table_start_players'] = hh_data.get('final_table_start_players')
                        ft_hands_data = hh_data.get('final_table_hands_data', [])
                        for hand_data in ft_hands_data:
                             hand_data['session_id'] = effective_session_id
                             all_final_table_hands_data.append(hand_data)
                elif is_ts:
                    ts_data = self.ts_parser.parse(content, filename=os.path.basename(file_path))
                    tourney_id = ts_data.get('tournament_id')
                    if tourney_id:
                        if tourney_id not in parsed_tournaments_data:
                             parsed_tournaments_data[tourney_id] = {'tournament_id': tourney_id, 'session_id': effective_session_id, 'ko_count': 0, 'reached_final_table': False}
                        parsed_tournaments_data[tourney_id]['tournament_name'] = ts_data.get('tournament_name') or parsed_tournaments_data[tourney_id].get('tournament_name')
                        parsed_tournaments_data[tourney_id]['start_time'] = ts_data.get('start_time') or parsed_tournaments_data[tourney_id].get('start_time')
                        parsed_tournaments_data[tourney_id]['buyin'] = ts_data.get('buyin') or parsed_tournaments_data[tourney_id].get('buyin')
                        parsed_tournaments_data[tourney_id]['payout'] = ts_data.get('payout') or parsed_tournaments_data[tourney_id].get('payout')
                        parsed_tournaments_data[tourney_id]['finish_place'] = ts_data.get('finish_place') or parsed_tournaments_data[tourney_id].get('finish_place')
            except Exception as e:
                logger.error(f"Ошибка обработки файла {file_path}: {e}")
            files_processed += 1

        current_progress = PARSING_WEIGHT_LOCAL

        if is_canceled_callback and is_canceled_callback():
            logger.warning(f"=== ИМПОРТ ОТМЕНЕН перед сохранением в БД (ImportService) ===")
            if progress_callback:
                progress_callback(current_progress, total_steps, "Импорт отменен пользователем")
            return

        logger.info("Сохранение обработанных данных в БД (ImportService)...")
        if progress_callback:
            progress_callback(current_progress, total_steps, "Сохранение данных в базу...")

        tournaments_saved = 0
        total_parsed_tournaments = len(parsed_tournaments_data)

        for tourney_id, data in parsed_tournaments_data.items():
            try:
                existing_tourney = self.tournament_repo.get_tournament_by_id(tourney_id)
                final_tourney_data = {}
                if existing_tourney:
                    final_tourney_data.update(existing_tourney.as_dict())
                final_tourney_data.update(data)

                if existing_tourney:
                    if existing_tourney.reached_final_table:
                        final_tourney_data['reached_final_table'] = True
                    if existing_tourney.final_table_initial_stack_chips is not None and data.get('final_table_initial_stack_chips') is None:
                        final_tourney_data['final_table_initial_stack_chips'] = existing_tourney.final_table_initial_stack_chips
                        final_tourney_data['final_table_initial_stack_bb'] = existing_tourney.final_table_initial_stack_bb
                    if existing_tourney.final_table_start_players is not None and data.get('final_table_start_players') is None:
                         final_tourney_data['final_table_start_players'] = existing_tourney.final_table_start_players
                    if existing_tourney.session_id:
                        final_tourney_data['session_id'] = existing_tourney.session_id
                    elif effective_session_id:
                        final_tourney_data['session_id'] = effective_session_id
                elif effective_session_id:
                    final_tourney_data['session_id'] = effective_session_id


                finish_place = final_tourney_data.get('finish_place')
                if finish_place is not None and 1 <= finish_place <= 9:
                    final_tourney_data['reached_final_table'] = True

                merged_tournament = Tournament.from_dict(final_tourney_data)
                self.tournament_repo.add_or_update_tournament(merged_tournament)
                tournaments_saved += 1

                if progress_callback and (tournaments_saved % 5 == 0 or tournaments_saved == total_parsed_tournaments):
                    save_progress = current_progress + int((tournaments_saved / max(total_parsed_tournaments, 1)) * (SAVING_WEIGHT_LOCAL * 0.4))
                    progress_callback(save_progress, total_steps, f"Сохранено турниров: {tournaments_saved}/{total_parsed_tournaments}")
            except Exception as e:
                logger.error(f"Ошибка сохранения/обновления турнира {tourney_id}: {e}")
        logger.info(f"Сохранено/обновлено {tournaments_saved} турниров.")

        total_hands_to_save = len(all_final_table_hands_data)
        hands_saved = 0
        for hand_data in all_final_table_hands_data:
             try:
                  hand = FinalTableHand.from_dict(hand_data)
                  self.ft_hand_repo.add_hand(hand)
                  hands_saved += 1
                  if progress_callback and (hands_saved % 10 == 0 or hands_saved == total_hands_to_save):
                      hands_progress = current_progress + int(SAVING_WEIGHT_LOCAL * 0.4) + int((hands_saved / max(total_hands_to_save, 1)) * (SAVING_WEIGHT_LOCAL * 0.4))
                      progress_callback(hands_progress, total_steps, f"Сохранено рук: {hands_saved}/{total_hands_to_save}")
             except Exception as e:
                  logger.error(f"Ошибка сохранения финальной раздачи {hand_data.get('hand_id')} турнира {hand_data.get('tournament_id')}: {e}")

        if hands_saved > 0:
            try:
                conn = self.db.get_connection()
                conn.commit()
                logger.debug(f"Commit выполнен для {hands_saved} рук (ImportService)")
            except Exception as e:
                logger.error(f"Ошибка при commit (ImportService): {e}")

        logger.debug("Подсчет и обновление ko_count для турниров (ImportService)...")
        ko_update_base_progress = current_progress + int(SAVING_WEIGHT_LOCAL * 0.8)
        if progress_callback:
            progress_callback(ko_update_base_progress, total_steps, "Подсчет нокаутов...")

        tournaments_processed_for_ko = 0
        for tourney_id_ko in parsed_tournaments_data:
            try:
                tournament_ft_hands = self.ft_hand_repo.get_hands_by_tournament(tourney_id_ko)
                total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands)

                tourney_to_update_ko = self.tournament_repo.get_tournament_by_id(tourney_id_ko)
                if tourney_to_update_ko:
                    tourney_to_update_ko.ko_count = total_ko
                    self.tournament_repo.add_or_update_tournament(tourney_to_update_ko)
                else:
                    logger.warning(f"Турнир {tourney_id_ko} не найден для обновления KO count.")

                tournaments_processed_for_ko += 1
                if progress_callback and (tournaments_processed_for_ko % 5 == 0 or tournaments_processed_for_ko == total_parsed_tournaments):
                    ko_progress = ko_update_base_progress + int((tournaments_processed_for_ko / max(total_parsed_tournaments, 1)) * (SAVING_WEIGHT_LOCAL * 0.2))
                    progress_callback(ko_progress, total_steps, f"Обработано турниров (KO): {tournaments_processed_for_ko}/{total_parsed_tournaments}")
            except Exception as e:
                logger.error(f"Ошибка подсчета и сохранения KO для турнира {tourney_id_ko} (ImportService): {e}")

        current_progress = total_steps
        logger.info(f"Импорт завершен (ImportService): Сохранено/обновлено {tournaments_saved} турниров. Сохранено {hands_saved} рук. KO counts обновлены.")

        logger.debug("=== ПРОВЕРКА БД ПОСЛЕ ИМПОРТА (ImportService) ===")
        try:
            test_query_hands = "SELECT COUNT(*) FROM hero_final_table_hands"
            result_hands = self.db.execute_query(test_query_hands)
            logger.debug(
                f"Количество рук в hero_final_table_hands: {result_hands[0][0] if result_hands and result_hands[0] else 0}"
            )
            test_query_tournaments = "SELECT COUNT(*) FROM tournaments"
            result_tournaments = self.db.execute_query(test_query_tournaments)
            logger.debug(
                f"Количество турниров в tournaments: {result_tournaments[0][0] if result_tournaments and result_tournaments[0] else 0}"
            )
        except Exception as e:
            logger.error(f"Ошибка при проверке БД после импорта: {e}")


        if progress_callback:
            progress_callback(total_steps, total_steps, "Импорт файлов завершен (статистика не обновлена).")
    # --- end of import_files method ---
