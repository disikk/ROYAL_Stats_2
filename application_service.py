# -*- coding: utf-8 -*-

"""
Сервис приложения Royal Stats.
Содержит основную бизнес-логику, оркестрирует работу парсеров и репозиториев,
подсчитывает агрегированную статистику.
"""

import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import math # Для округления в BB
import re  # Добавить к существующим импортам

import config
from db.manager import database_manager # Используем синглтон менеджер БД
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    OverallStatsRepository,
    PlaceDistributionRepository,
    FinalTableHandRepository,
)
from parsers import HandHistoryParser, TournamentSummaryParser
from models import Tournament, Session, OverallStats, FinalTableHand
# Импортируем плагины статистик (будут реализованы далее)
from stats import (
    BaseStat, # Базовый класс
    BigKOStat,
    ITMStat,
    ROIStat,
    TotalKOStat,
    AvgKOPerTournamentStat, # Новый
    FinalTableReachStat, # Новый
    AvgFTInitialStackStat, # Новый
    EarlyFTKOStat, # Новый
    EarlyFTBustStat,
    AvgFinishPlaceStat,
    AvgFinishPlaceFTStat,
    AvgFinishPlaceNoFTStat,
)

logger = logging.getLogger('ROYAL_Stats.ApplicationService')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

# Список плагинов статистик, которые будем использовать
# В реальном приложении можно было бы загружать их динамически
STAT_PLUGINS: List[BaseStat] = [
    TotalKOStat(),
    ITMStat(),
    ROIStat(),
    BigKOStat(),
    AvgKOPerTournamentStat(),
    FinalTableReachStat(),
    AvgFTInitialStackStat(),
    EarlyFTKOStat(),
    EarlyFTBustStat(),
    AvgFinishPlaceStat(),
    AvgFinishPlaceFTStat(),
    AvgFinishPlaceNoFTStat(),
]

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
        
        # Нужно минимум 2 строки для проверки
        if len(lines) < 2:
            return None
            
        first_line = lines[0].strip()
        second_line = lines[1].strip()
        
        # Проверка Tournament Summary
        if (first_line.startswith("Tournament #") and 
            "Mystery Battle Royale" in first_line and 
            second_line.startswith("Buy-in:")):
            logger.debug(f"Файл определен как Tournament Summary: {file_path}")
            return 'ts'
            
        # Проверка Hand History
        if (first_line.startswith("Poker Hand #") and 
            "Mystery Battle Royale" in first_line and 
            second_line.startswith("Table")):
            logger.debug(f"Файл определен как Hand History: {file_path}")
            return 'hh'
            
        # Если не подходит ни под один формат
        logger.debug(f"Файл отфильтрован (не соответствует покерным форматам): {file_path}")
        logger.debug(f"  1-я строка: {first_line[:50]}...")
        logger.debug(f"  2-я строка: {second_line[:50]}...")
        return None
        
    except Exception as e:
        logger.warning(f"Не удалось прочитать файл {file_path}: {e}")
        return None


def is_poker_file(file_path: str) -> bool:
    """
    Предварительная проверка файла - является ли покерным файлом.
    Возвращает True, если файл соответствует ожидаемым форматам.
    """
    return determine_file_type(file_path) is not None

class ApplicationService:
    """
    Центральный сервис приложения.
    """

    def __init__(self):
        self.db = database_manager
        self.tournament_repo = TournamentRepository()
        self.session_repo = SessionRepository()
        self.overall_stats_repo = OverallStatsRepository()
        self.place_dist_repo = PlaceDistributionRepository()
        self.ft_hand_repo = FinalTableHandRepository()

        self.hh_parser = HandHistoryParser()
        self.ts_parser = TournamentSummaryParser()
        
    @property
    def db_path(self) -> str:
        """Возвращает путь к текущей базе данных."""
        return self.db.db_path

    def get_available_databases(self) -> List[str]:
        """Возвращает список доступных файлов баз данных."""
        return self.db.get_available_databases()

    def switch_database(self, db_path: str):
        """Переключает активную базу данных."""
        self.db.set_db_path(db_path)
        # После смены БД, репозитории автоматически будут работать с новой БД

    def create_new_database(self, db_name: str):
        """Создает новую базу данных и переключается на нее."""
        # DatabaseManager сам создаст папку, если нужно, и инициализирует схему
        new_db_path = os.path.join(config.DEFAULT_DB_DIR, db_name)
        if not new_db_path.lower().endswith(".db"):
            new_db_path += ".db"

        if os.path.exists(new_db_path):
            logger.warning(f"Попытка создать существующую БД: {new_db_path}")
            # Можно вернуть False или пробросить исключение, чтобы UI показал ошибку
            raise FileExistsError(f"База данных '{os.path.basename(new_db_path)}' уже существует.")

        self.db.set_db_path(new_db_path)  # Устанавливаем новый путь

        # Принудительно открываем соединение, чтобы физически создать файл БД
        # и инициализировать схему. Иначе файл появится только при первом
        # обращении к данным, что мешает отображению новой БД в диалоге.
        conn = self.db.get_connection()
        self.db.close_connection()

        logger.info(f"Создана и выбрана новая база данных: {new_db_path}")

    def import_files(
        self,
        paths: List[str],
        session_name: str | None,
        session_id: str | None = None,
        progress_callback=None,
        is_canceled_callback=None,
    ):
        """
        Импортирует файлы/папки, парсит их и сохраняет данные в БД.
        Обновляет статистику после импорта.

        Args:
            paths: Список путей к файлам или папкам.
            session_name: Имя новой сессии (используется, если session_id не задан).
            session_id: Идентификатор существующей сессии для догрузки.
            progress_callback: Optional function(current, total, text) for UI progress.
            is_canceled_callback: Optional function() that returns True if the import should be cancelled.
        """
        logger.info(f"=== НАЧАЛО ИМПОРТА ===")
        logger.info(f"is_canceled_callback передан: {is_canceled_callback is not None}")
        
        all_files_to_process = []
        filtered_files_count = 0
        for path in paths:
            if os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        if fname.lower().endswith((".txt")):
                            full_path = os.path.join(root, fname)
                            if is_poker_file(full_path):
                                all_files_to_process.append(full_path)
                            else:
                                filtered_files_count += 1
                                logger.debug(f"Файл отфильтрован (нет покерных шаблонов): {fname}")
            elif os.path.isfile(path):
                if path.lower().endswith((".txt")):
                    if is_poker_file(path):
                        all_files_to_process.append(path)
                    else:
                        filtered_files_count += 1
                        logger.debug(f"Файл отфильтрован (нет покерных шаблонов): {os.path.basename(path)}")
        if filtered_files_count > 0:
            logger.info(f"Отфильтровано {filtered_files_count} файлов без покерных шаблонов")

        total_files = len(all_files_to_process)
        if total_files == 0:
            logger.info("Нет файлов для обработки.")
            if progress_callback:
                 progress_callback(0, 0, "Нет файлов для обработки")
            return

        # Рассчитываем общее количество шагов прогресса
        # Этапы: парсинг файлов + сохранение в БД + обновление статистики
        # Парсинг: 1 шаг на файл
        # Сохранение в БД: примерно 20% от общего времени
        # Обновление статистики: примерно 10% от общего времени
        PARSING_WEIGHT = 70  # 70% времени на парсинг
        SAVING_WEIGHT = 20   # 20% времени на сохранение
        STATS_WEIGHT = 10    # 10% времени на обновление статистики
        
        total_steps = 100  # Работаем с процентами
        current_progress = 0
        
        logger.info(
            f"Начат импорт {total_files} файлов в сессию"
            f" '{session_name if session_id is None else session_id}'"
        )

        if session_id:
            current_session = self.session_repo.get_session_by_id(session_id)
            if not current_session:
                logger.error(f"Сессия {session_id} не найдена")
                if progress_callback:
                    progress_callback(0, total_steps, f"Ошибка: Сессия не найдена")
                return
        else:
            try:
                current_session = self.session_repo.create_session(session_name or "")
                session_id = current_session.session_id
                logger.info(f"Создана новая сессия для импорта: {session_id}")
            except Exception as e:
                logger.error(f"Не удалось создать сессию для импорта: {e}")
                if progress_callback:
                    progress_callback(0, total_steps, f"Ошибка: Не удалось создать сессию: {e}")
                return


        # Словарь для временного хранения данных турниров во время парсинга
        # Ключ: tournament_id, Значение: Dict с объединенными данными
        parsed_tournaments_data: Dict[str, Dict[str, Any]] = {}
        # Список данных финальных рук для пакетного сохранения
        all_final_table_hands_data: List[Dict[str, Any]] = []

        # ЭТАП 1: Парсинг файлов
        if progress_callback:
            progress_callback(current_progress, total_steps, "Начинаем обработку файлов...")
        
        files_processed = 0
        for file_path in all_files_to_process:
            # Проверяем флаг отмены
            if is_canceled_callback and is_canceled_callback():
                logger.warning(f"=== ИМПОРТ ОТМЕНЕН при парсинге файлов ===")
                logger.info("Импорт отменен пользователем. Прерываем обработку файлов.")
                if progress_callback:
                    progress_callback(current_progress, total_steps, "Импорт отменен пользователем")
                return
            
            # Обновляем прогресс с учетом веса этапа парсинга
            file_progress = int((files_processed / total_files) * PARSING_WEIGHT)
            if progress_callback:
                progress_callback(file_progress, total_steps, f"Обработка: {os.path.basename(file_path)}")

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Определяем тип файла
                file_type = determine_file_type(file_path)
                if file_type is None:
                    logger.warning(f"Файл не соответствует ожидаемым форматам: {file_path}. Файл пропущен.")
                    files_processed += 1
                    continue

                is_ts = file_type == 'ts'
                is_hh = file_type == 'hh'

                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Обрабатываем файл соответствующим парсером
                if is_hh:
                    logger.debug(f"Обработка файла Hand History: {file_path}")
                    hh_data = self.hh_parser.parse(content, filename=os.path.basename(file_path))
                    tourney_id = hh_data.get('tournament_id')
                    
                    # ОТЛАДКА: проверяем что вернул парсер
                    logger.info(f"=== ОТЛАДКА HH ПАРСЕР ===")
                    logger.info(f"Tournament ID: {tourney_id}")
                    logger.info(f"Reached final table: {hh_data.get('reached_final_table', False)}")
                    logger.info(f"Final table hands data: {len(hh_data.get('final_table_hands_data', []))} рук")

                    if tourney_id:
                        # Инициализируем запись в словаре, если ее нет
                        if tourney_id not in parsed_tournaments_data:
                             parsed_tournaments_data[tourney_id] = {'tournament_id': tourney_id, 'session_id': session_id, 'ko_count': 0, 'reached_final_table': False}

                        # Добавляем данные из HH к временной записи турнира
                        parsed_tournaments_data[tourney_id]['start_time'] = parsed_tournaments_data[tourney_id].get('start_time') or hh_data.get('start_time')
                        
                        # Обновляем временные данные турнира из HH
                        if hh_data.get('reached_final_table', False):
                             parsed_tournaments_data[tourney_id]['reached_final_table'] = True
                             parsed_tournaments_data[tourney_id]['final_table_initial_stack_chips'] = hh_data.get('final_table_initial_stack_chips')
                             parsed_tournaments_data[tourney_id]['final_table_initial_stack_bb'] = hh_data.get('final_table_initial_stack_bb')

                        # Собираем данные финальных раздач
                        ft_hands_data = hh_data.get('final_table_hands_data', [])
                        logger.debug(f"HH парсер вернул {len(ft_hands_data)} рук финального стола для турнира {tourney_id}")
                        for hand_data in ft_hands_data:
                             hand_data['session_id'] = session_id # Добавляем session_id к каждой руке
                             all_final_table_hands_data.append(hand_data)
                             logger.debug(f"Добавлена рука: tournament_id={hand_data.get('tournament_id')}, "
                                        f"hand_id={hand_data.get('hand_id')}, "
                                        f"table_size={hand_data.get('table_size')}, "
                                        f"hero_ko={hand_data.get('hero_ko_this_hand')}")


                elif is_ts:
                    logger.debug(f"Обработка файла Tournament Summary: {file_path}")
                    ts_data = self.ts_parser.parse(content, filename=os.path.basename(file_path))
                    tourney_id = ts_data.get('tournament_id')

                    if tourney_id:
                        # Инициализируем запись, если ее нет
                        if tourney_id not in parsed_tournaments_data:
                             parsed_tournaments_data[tourney_id] = {'tournament_id': tourney_id, 'session_id': session_id, 'ko_count': 0, 'reached_final_table': False} # Инициализируем ko_count=0

                        # Обновляем временные данные турнира из TS (TS имеет приоритет по fin_place, payout, buyin, name, start_time)
                        parsed_tournaments_data[tourney_id]['tournament_name'] = ts_data.get('tournament_name') or parsed_tournaments_data[tourney_id].get('tournament_name')
                        parsed_tournaments_data[tourney_id]['start_time'] = ts_data.get('start_time') or parsed_tournaments_data[tourney_id].get('start_time')
                        parsed_tournaments_data[tourney_id]['buyin'] = ts_data.get('buyin') or parsed_tournaments_data[tourney_id].get('buyin')
                        parsed_tournaments_data[tourney_id]['payout'] = ts_data.get('payout') or parsed_tournaments_data[tourney_id].get('payout')
                        parsed_tournaments_data[tourney_id]['finish_place'] = ts_data.get('finish_place') or parsed_tournaments_data[tourney_id].get('finish_place') # finish_place 0 или None из HH, TS должно переписать

                        # Логируем найденные значения для отладки
                        logger.debug(f"TS данные для {tourney_id}: name={ts_data.get('tournament_name')}, buyin={ts_data.get('buyin')}, payout={ts_data.get('payout')}, place={ts_data.get('finish_place')}")


            except Exception as e:
                logger.error(f"Ошибка обработки файла {file_path}: {e}")
                # Продолжаем обрабатывать другие файлы

            files_processed += 1


        # Завершаем этап парсинга
        current_progress = PARSING_WEIGHT

        # --- Сохранение данных в БД ---
        logger.info(f"=== ОТЛАДКА ПЕРЕД СОХРАНЕНИЕМ ===")
        logger.info(f"Всего рук финального стола для сохранения: {len(all_final_table_hands_data)}")
        if all_final_table_hands_data:
            logger.info(f"Пример первой руки: {all_final_table_hands_data[0]}")
        
        # ЭТАП 2: Сохранение данных в БД
        # Проверяем флаг отмены перед сохранением в БД
        if is_canceled_callback and is_canceled_callback():
            logger.warning(f"=== ИМПОРТ ОТМЕНЕН перед сохранением в БД ===")
            logger.info("Импорт отменен пользователем. Пропускаем сохранение данных в БД.")
            if progress_callback:
                progress_callback(current_progress, total_steps, "Импорт отменен пользователем")
            return
            
        logger.info("Сохранение обработанных данных в БД...")
        if progress_callback:
            progress_callback(current_progress, total_steps, "Сохранение данных в базу...")

        # 1. СНАЧАЛА сохраняем/обновляем данные турниров
        if progress_callback:
            progress_callback(current_progress, total_steps, "Сохранение турниров...")
        
        tournaments_saved = 0
        total_tournaments = len(parsed_tournaments_data)
        
        for tourney_id, data in parsed_tournaments_data.items():
             try:
                 # Запрашиваем текущий турнир для merge
                 existing_tourney = self.tournament_repo.get_tournament_by_id(tourney_id)

                 # Объединяем данные: TS > HH > Existing
                 final_tourney_data = {}
                 if existing_tourney:
                     final_tourney_data.update(existing_tourney.as_dict()) # Base from existing

                 final_tourney_data.update(data) # Override with data from parsed file batch

                 # Специальная логика для полей, которые должны объединяться, а не перезаписываться
                 # reached_final_table = Existing OR New
                 if existing_tourney and existing_tourney.reached_final_table:
                     final_tourney_data['reached_final_table'] = True # Если хоть раз достигли финалки, флаг остается TRUE

                 # final_table_initial_stack - сохраняем только если это первая раздача финалки в истории парсинга этого турнира
                 if existing_tourney and existing_tourney.final_table_initial_stack_chips is not None:
                      # Если стек уже сохранен в БД, не перезаписываем его
                      final_tourney_data['final_table_initial_stack_chips'] = existing_tourney.final_table_initial_stack_chips
                      final_tourney_data['final_table_initial_stack_bb'] = existing_tourney.final_table_initial_stack_bb

                 # session_id - сохраняем первый session_id, связанный с этим турниром
                 if existing_tourney and existing_tourney.session_id:
                      final_tourney_data['session_id'] = existing_tourney.session_id


                 # Логируем финальные данные турнира перед сохранением
                 logger.debug(f"Сохранение турнира {tourney_id}: name={final_tourney_data.get('tournament_name')}, " 
                            f"buyin={final_tourney_data.get('buyin')}, payout={final_tourney_data.get('payout')}, "
                            f"place={final_tourney_data.get('finish_place')}")

                 # Создаем объект Tournament из объединенных данных
                 merged_tournament = Tournament.from_dict(final_tourney_data)
                 self.tournament_repo.add_or_update_tournament(merged_tournament)
                 tournaments_saved += 1
                 
                 # Обновляем прогресс
                 if tournaments_saved % 5 == 0 or tournaments_saved == total_tournaments:
                     save_progress = current_progress + int((tournaments_saved / max(total_tournaments, 1)) * (SAVING_WEIGHT * 0.4))
                     if progress_callback:
                         progress_callback(save_progress, total_steps, f"Сохранено турниров: {tournaments_saved}/{total_tournaments}")

             except Exception as e:
                  logger.error(f"Ошибка сохранения/обновления турнира {tourney_id}: {e}")

        logger.info(f"Сохранено/обновлено {tournaments_saved} турниров.")

        # 2. ТЕПЕРЬ сохраняем данные финальных раздач (с ON CONFLICT DO NOTHING)
        logger.info(f"Начинаем сохранение {len(all_final_table_hands_data)} рук финального стола")
        total_hands_to_save = len(all_final_table_hands_data)
        hands_saved = 0
        
        for hand_data in all_final_table_hands_data:
             try:
                  logger.debug(f"Сохраняем руку: {hand_data}")
                  hand = FinalTableHand.from_dict(hand_data)
                  self.ft_hand_repo.add_hand(hand)
                  hands_saved += 1
                  logger.debug(f"Рука сохранена успешно: {hand.hand_id}")
                  
                  # Обновляем прогресс для сохранения рук
                  if hands_saved % 10 == 0 or hands_saved == total_hands_to_save:  # Обновляем каждые 10 рук
                      hands_progress = current_progress + int(SAVING_WEIGHT * 0.4) + int((hands_saved / max(total_hands_to_save, 1)) * (SAVING_WEIGHT * 0.4))
                      if progress_callback:
                          progress_callback(hands_progress, total_steps, f"Сохранено рук: {hands_saved}/{total_hands_to_save}")
                          
             except Exception as e:
                  logger.error(f"Ошибка сохранения финальной раздачи {hand_data.get('hand_id')} турнира {hand_data.get('tournament_id')}: {e}")
                  import traceback
                  logger.error(f"Traceback: {traceback.format_exc()}")
        
        logger.info(f"Сохранение рук завершено: {hands_saved} из {total_hands_to_save}")
        
        # Добавить явный commit после сохранения всех рук
        if hands_saved > 0:
            try:
                conn = self.db.get_connection()
                conn.commit()
                logger.info(f"Commit выполнен для {hands_saved} рук")
            except Exception as e:
                logger.error(f"Ошибка при commit: {e}")

        # 3. Подсчитываем ko_count для каждого турнира на основе сохраненных рук
        logger.info("Подсчет ko_count для турниров...")
        if progress_callback:
            progress_callback(current_progress + int(SAVING_WEIGHT * 0.8), total_steps, "Подсчет нокаутов...")
        
        tournaments_processed = 0
        
        for tourney_id in parsed_tournaments_data:
            try:
                # Получаем все руки финального стола для этого турнира из БД
                tournament_ft_hands = self.ft_hand_repo.get_hands_by_tournament(tourney_id)
                # Суммируем KO из всех рук
                total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands)
                # Обновляем ko_count в parsed_tournaments_data
                parsed_tournaments_data[tourney_id]['ko_count'] = total_ko
                if total_ko > 0:
                    logger.debug(f"Турнир {tourney_id}: найдено {total_ko} KO в {len(tournament_ft_hands)} руках")
                tournaments_processed += 1
                
                # Обновляем прогресс
                if tournaments_processed % 5 == 0 or tournaments_processed == total_tournaments:
                    ko_progress = current_progress + int(SAVING_WEIGHT * 0.8) + int((tournaments_processed / max(total_tournaments, 1)) * (SAVING_WEIGHT * 0.2))
                    if progress_callback:
                        progress_callback(ko_progress, total_steps, f"Обработано турниров: {tournaments_processed}/{total_tournaments}")
                        
            except Exception as e:
                logger.error(f"Ошибка подсчета KO для турнира {tourney_id}: {e}")

        current_progress = PARSING_WEIGHT + SAVING_WEIGHT
        logger.info(f"Сохранено/обновлено {tournaments_saved} турниров. Сохранено {len(all_final_table_hands_data)} рук финального стола.")


        # --- Обновление статистики ---
        # ЭТАП 3: Обновление статистики
        # Проверяем флаг отмены перед обновлением статистики
        if is_canceled_callback and is_canceled_callback():
            logger.warning(f"=== ИМПОРТ ОТМЕНЕН перед обновлением статистики ===")
            logger.info("Импорт отменен пользователем. Пропускаем обновление статистики.")
            if progress_callback:
                progress_callback(current_progress, total_steps, "Импорт отменен пользователем")
            return
            
        logger.info("Обновление агрегированной статистики...")
        if progress_callback:
            progress_callback(current_progress, total_steps, "Обновление статистики...")
        
        try:
             # Передаем callback в _update_all_statistics для отслеживания прогресса
             self._update_all_statistics(session_id, 
                                        progress_callback=lambda step, total: progress_callback(
                                            current_progress + int((step / total) * STATS_WEIGHT), 
                                            total_steps, 
                                            f"Обновление статистики... {step}/{total}"
                                        ))
             logger.info("Обновление статистики завершено.")
        except Exception as e:
             logger.error(f"Ошибка при обновлении статистики: {e}")
             if progress_callback:
                  progress_callback(total_steps, total_steps, f"Ошибка при обновлении статистики: {e}")
             # В реальном приложении здесь может потребоваться более детальная обработка
             return

            # В самом конце метода import_files
        logger.info("=== ПРОВЕРКА БД ПОСЛЕ ИМПОРТА ===")
        test_query = "SELECT COUNT(*) FROM hero_final_table_hands"
        result = self.db.execute_query(test_query)
        logger.info(f"Количество рук в hero_final_table_hands: {result[0][0] if result else 0}")

        test_query2 = "SELECT COUNT(*) FROM tournaments"  
        result2 = self.db.execute_query(test_query2)
        logger.info(f"Количество турниров в tournaments: {result2[0][0] if result2 else 0}")

        # Завершение импорта
        if progress_callback:
            progress_callback(total_steps, total_steps, "Импорт завершен успешно!")

    def _update_all_statistics(self, session_id: str, progress_callback=None):
        """
        Пересчитывает и обновляет все агрегированные статистики (общие и по сессии).
        Вызывается после импорта данных.
        """
        logger.debug("Запущен пересчет всей статистики.")
        
        # Предварительно загружаем данные для оценки объема работы
        all_tournaments = self.tournament_repo.get_all_tournaments()
        all_final_tournaments = [
            t for t in all_tournaments
            if t.reached_final_table and t.finish_place is not None and 1 <= t.finish_place <= 9
        ]
        sessions_to_update = self.session_repo.get_all_sessions()

        # Общее количество операций для прогресса
        total_steps = 1 + len(all_final_tournaments) + len(all_tournaments) + len(sessions_to_update)
        current_step = 0

        # --- Обновление Overall Stats ---
        try:
            if progress_callback:
                progress_callback(current_step, total_steps)
            logger.debug("Обновление общей статистики...")
            overall_stats = self._calculate_overall_stats()
            self.overall_stats_repo.update_overall_stats(overall_stats)
            logger.info("Общая статистика обновлена успешно.")
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps)
        except Exception as e:
            logger.error(f"Ошибка при обновлении overall_stats: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # --- Обновление Place Distribution ---
        try:
            logger.debug("Обновление распределения мест...")
            self.place_dist_repo.reset_distribution()
            for tourney in all_final_tournaments:
                self.place_dist_repo.increment_place_count(tourney.finish_place)
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
            logger.info(f"Распределение мест обновлено для {len(all_final_tournaments)} турниров.")
        except Exception as e:
            logger.error(f"Ошибка при обновлении place_distribution: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # --- Обновление KO count для турниров ---
        try:
            logger.debug("Обновление ko_count для турниров...")
            for tournament in all_tournaments:
                tournament_ft_hands = self.ft_hand_repo.get_hands_by_tournament(tournament.tournament_id)
                total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands)
                tournament.ko_count = total_ko
                self.tournament_repo.add_or_update_tournament(tournament)
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
            logger.info(f"KO count обновлен для {len(all_tournaments)} турниров.")
        except Exception as e:
            logger.error(f"Ошибка при обновлении ko_count: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # --- Обновление Session Stats ---
        try:
            logger.debug("Обновление статистики сессий...")
            for session in sessions_to_update:
                try:
                    self._calculate_and_update_session_stats(session.session_id)
                except Exception as e:
                    logger.error(f"Ошибка при обновлении сессии {session.session_id}: {e}")
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
            logger.info(f"Статистика обновлена для {len(sessions_to_update)} сессий.")
        except Exception as e:
            logger.error(f"Ошибка при обновлении session stats: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        if progress_callback:
            progress_callback(total_steps, total_steps)

        logger.info("Обновление всей статистики завершено (с учетом возможных ошибок).")


    def _calculate_overall_stats(self) -> OverallStats:
        """
        Рассчитывает все показатели для OverallStats на основе данных из БД.
        """
        all_tournaments = self.tournament_repo.get_all_tournaments()
        all_ft_hands = self.ft_hand_repo.get_all_hands() # Все руки финалок
        logger.info(f"_calculate_overall_stats: Загружено {len(all_tournaments)} турниров")
        logger.info(f"_calculate_overall_stats: Загружено {len(all_ft_hands)} рук финального стола")
        # Проверяем содержимое первого турнира для отладки
        if all_tournaments:
            t = all_tournaments[0]
            logger.debug(f"Пример турнира: id={t.tournament_id}, buyin={t.buyin}, payout={t.payout}, place={t.finish_place}, ft={t.reached_final_table}, ko={t.ko_count}")

        stats = OverallStats() # Создаем объект с дефолтными значениями

        stats.total_tournaments = len(all_tournaments)

        # Фильтруем турниры, достигшие финального стола
        final_table_tournaments = [t for t in all_tournaments if t.reached_final_table]
        stats.total_final_tables = len(final_table_tournaments)

        # Расчеты, основанные на турнирах:
        stats.total_buy_in = sum(t.buyin for t in all_tournaments if t.buyin is not None)
        stats.total_prize = sum(t.payout if t.payout is not None else 0 for t in all_tournaments)

        # Среднее место по всем турнирам (включая не финалку)
        all_places = [t.finish_place for t in all_tournaments if t.finish_place is not None]
        stats.avg_finish_place = sum(all_places) / len(all_places) if all_places else 0.0

        # Среднее место только на финалке (1-9)
        ft_places = [t.finish_place for t in final_table_tournaments if t.finish_place is not None and 1 <= t.finish_place <= 9]
        stats.avg_finish_place_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0

        # Общее количество KO - суммируем hero_ko_this_hand из всех рук финального стола
        # Обновленный HandHistoryParser точно определяет выбывших игроков путем сравнения
        # списков игроков между соседними раздачами в хронологическом порядке
        stats.total_knockouts = sum(hand.hero_ko_this_hand for hand in all_ft_hands)
        logger.info(f"Рассчитано total_knockouts: {stats.total_knockouts}")

        # Avg KO / Tournament (по всем турнирам, включая не финалку)
        stats.avg_ko_per_tournament = stats.total_knockouts / stats.total_tournaments if stats.total_tournaments > 0 else 0.0

        # % Reach FT
        stats.final_table_reach_percent = (stats.total_final_tables / stats.total_tournaments * 100) if stats.total_tournaments > 0 else 0.0


        # Средний стек на старте финалки (чипсы и BB)
        ft_initial_stacks_chips = [t.final_table_initial_stack_chips for t in final_table_tournaments if t.final_table_initial_stack_chips is not None]
        stats.avg_ft_initial_stack_chips = sum(ft_initial_stacks_chips) / len(ft_initial_stacks_chips) if ft_initial_stacks_chips else 0.0

        ft_initial_stacks_bb = [t.final_table_initial_stack_bb for t in final_table_tournaments if t.final_table_initial_stack_bb is not None]
        stats.avg_ft_initial_stack_bb = sum(ft_initial_stacks_bb) / len(ft_initial_stacks_bb) if ft_initial_stacks_bb else 0.0

        # Расчеты для "ранней стадии финалки" (9-6 игроков)
        early_ft_hands = [hand for hand in all_ft_hands if hand.is_early_final]
        stats.early_ft_ko_count = sum(hand.hero_ko_this_hand for hand in early_ft_hands)

        # Среднее KO в ранней финалке на турнир (считаем только для турниров, достигших финалки)
        stats.early_ft_ko_per_tournament = stats.early_ft_ko_count / stats.total_final_tables if stats.total_final_tables > 0 else 0.0

        # Вылеты Hero на ранней стадии финалки (6-9 место)
        stats.early_ft_bust_count = sum(
            1
            for t in final_table_tournaments
            if t.finish_place is not None and 6 <= t.finish_place <= 9
        )
        stats.early_ft_bust_per_tournament = (
            stats.early_ft_bust_count / stats.total_final_tables if stats.total_final_tables > 0 else 0.0
        )

        # Логируем статистику по выплатам для отладки
        tournaments_with_payout = sum(1 for t in all_tournaments if t.payout is not None and t.payout > 0)
        tournaments_without_payout = sum(1 for t in all_tournaments if t.payout is None or t.payout == 0)
        logger.info(f"Турниры с выплатами: {tournaments_with_payout}, без выплат: {tournaments_without_payout}")

        # Логируем примеры турниров с выплатами для отладки Big KO
        tournaments_with_big_payout = [t for t in all_tournaments 
                                      if t.payout is not None and t.payout > 0 and t.buyin is not None 
                                      and t.payout >= t.buyin * 10]
        if tournaments_with_big_payout:
            logger.info(f"Найдено {len(tournaments_with_big_payout)} турниров с выплатой >= 10x buyin:")
            for t in tournaments_with_big_payout[:5]:  # Показываем первые 5
                logger.info(f"  - Турнир {t.tournament_id}: место {t.finish_place}, "
                           f"buyin=${t.buyin}, payout=${t.payout} "
                           f"(ratio: {t.payout/t.buyin:.1f}x)")

        # Расчет Big KO (требует buyin и payout из турниров)
        big_ko_results = BigKOStat().compute(all_tournaments, all_ft_hands, [], None)
        logger.info(f"BigKO результаты: {big_ko_results}")
        stats.big_ko_x1_5 = big_ko_results.get("x1.5", 0)
        stats.big_ko_x2 = big_ko_results.get("x2", 0)
        stats.big_ko_x10 = big_ko_results.get("x10", 0)
        stats.big_ko_x100 = big_ko_results.get("x100", 0)
        stats.big_ko_x1000 = big_ko_results.get("x1000", 0)
        stats.big_ko_x10000 = big_ko_results.get("x10000", 0)


        # Среднее место когда НЕ дошел до финалки
        no_ft_places = [t.finish_place for t in all_tournaments 
                       if not t.reached_final_table and t.finish_place is not None]
        stats.avg_finish_place_no_ft = sum(no_ft_places) / len(no_ft_places) if no_ft_places else 0.0
        stats.avg_finish_place_no_ft = round(stats.avg_finish_place_no_ft, 2)

        # Можно округлить некоторые значения для хранения
        stats.avg_finish_place = round(stats.avg_finish_place, 2)
        stats.avg_finish_place_ft = round(stats.avg_finish_place_ft, 2)
        stats.avg_ko_per_tournament = round(stats.avg_ko_per_tournament, 2)
        stats.avg_ft_initial_stack_chips = round(stats.avg_ft_initial_stack_chips, 2)
        stats.avg_ft_initial_stack_bb = round(stats.avg_ft_initial_stack_bb, 2)
        stats.early_ft_ko_per_tournament = round(stats.early_ft_ko_per_tournament, 2)
        stats.early_ft_bust_per_tournament = round(stats.early_ft_bust_per_tournament, 2)
        stats.final_table_reach_percent = round(stats.final_table_reach_percent, 2)

        logger.info(f"Итоговая статистика: tournaments={stats.total_tournaments}, knockouts={stats.total_knockouts}, prize={stats.total_prize}, buyin={stats.total_buy_in}")
        return stats

    def _calculate_and_update_session_stats(self, session_id: str):
        """
        Рассчитывает и обновляет статистику для конкретной сессии.
        """
        logger.debug(f"Расчет статистики для сессии {session_id}")
        session = self.session_repo.get_session_by_id(session_id)
        if not session:
            logger.warning(f"Сессия с ID {session_id} не найдена для обновления статистики.")
            return

        tournaments_in_session = self.tournament_repo.get_all_tournaments(session_id=session_id)
        ft_hands_in_session = self.ft_hand_repo.get_hands_by_session(session_id=session_id)


        session.tournaments_count = len(tournaments_in_session)
        session.knockouts_count = sum(hand.hero_ko_this_hand for hand in ft_hands_in_session)

        # Среднее место по всем турнирам в сессии
        all_places_session = [t.finish_place for t in tournaments_in_session if t.finish_place is not None]
        session.avg_finish_place = sum(all_places_session) / len(all_places_session) if all_places_session else 0.0

        session.total_prize = sum(t.payout for t in tournaments_in_session if t.payout is not None)
        session.total_buy_in = sum(t.buyin for t in tournaments_in_session if t.buyin is not None)

        # Округляем значения
        session.avg_finish_place = round(session.avg_finish_place, 2)
        session.total_prize = round(session.total_prize, 2)
        session.total_buy_in = round(session.total_buy_in, 2)

        logger.debug(f"Сессия {session_id}: турниров={session.tournaments_count}, KO={session.knockouts_count}, avg_place={session.avg_finish_place}, prize={session.total_prize}, buyin={session.total_buy_in}")
        self.session_repo.update_session_stats(session)


    # --- Методы для получения данных для UI ---

    def get_overall_stats(self) -> OverallStats:
        """Возвращает объект OverallStats с общей статистикой."""
        return self.overall_stats_repo.get_overall_stats()

    def get_all_tournaments(self, buyin_filter: Optional[float] = None) -> List[Tournament]:
        """Возвращает список всех турниров Hero, опционально фильтруя по бай-ину."""
        return self.tournament_repo.get_all_tournaments(buyin_filter=buyin_filter)

    def get_all_sessions(self) -> List[Session]:
        """Возвращает список всех сессий Hero."""
        return self.session_repo.get_all_sessions()

    def get_place_distribution(self) -> Dict[int, int]:
        """Возвращает распределение мест на финальном столе (1-9)."""
        return self.place_dist_repo.get_distribution()

    def get_place_distribution_pre_ft(self) -> Dict[int, int]:
        """Возвращает распределение мест до финального стола (10-18)."""
        tournaments = self.tournament_repo.get_all_tournaments()
        distribution = {i: 0 for i in range(10, 19)}
        for tourney in tournaments:
            if tourney.finish_place is not None and 10 <= tourney.finish_place <= 18:
                distribution[tourney.finish_place] += 1
        return distribution

    def get_place_distribution_overall(self) -> Dict[int, int]:
        """Возвращает распределение мест по всем турнирам (1-18)."""
        tournaments = self.tournament_repo.get_all_tournaments()
        distribution = {i: 0 for i in range(1, 19)}
        for tourney in tournaments:
            if tourney.finish_place is not None and 1 <= tourney.finish_place <= 18:
                distribution[tourney.finish_place] += 1
        return distribution

    def get_distinct_buyins(self) -> List[float]:
        """Возвращает список уникальных бай-инов из сохраненных турниров."""
        return self.tournament_repo.get_distinct_buyins()

    # Методы для получения данных сессии для отображения стат по сессии
    def get_session_stats(self, session_id: str) -> Optional[Session]:
        """Возвращает объект Session с агрегированной статистикой для указанной сессии."""
        return self.session_repo.get_session_by_id(session_id)

    def get_place_distribution_for_session(self, session_id: str) -> Dict[int, int]:
         """
         Рассчитывает и возвращает распределение мест (1-9) только для турниров в указанной сессии.
         """
         tournaments_in_session = self.tournament_repo.get_all_tournaments(session_id=session_id)
         distribution = {i: 0 for i in range(1, 10)}
         total_final_tables_in_session = 0

         for tourney in tournaments_in_session:
              if tourney.reached_final_table:
                   total_final_tables_in_session += 1 # Count FTs for this session
                   if tourney.finish_place is not None and 1 <= tourney.finish_place <= 9:
                        distribution[tourney.finish_place] += 1

         # Возвращаем распределение и общее количество финалок в сессии для нормализации в UI
         return distribution, total_final_tables_in_session

    def delete_session(self, session_id: str):
        """Удаляет сессию и все связанные данные."""
        # Удаляем сессию (каскадное удаление удалит связанные турниры и руки)
        self.session_repo.delete_session_by_id(session_id)
        # Статистика пересчитывается асинхронно во внешнем потоке


# Создаем синглтон экземпляр ApplicationService
application_service = ApplicationService()