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
]

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

        self.db.set_db_path(new_db_path) # Set path will also attempt init

        logger.info(f"Создана и выбрана новая база данных: {new_db_path}")


    def import_files(self, paths: List[str], session_name: str, progress_callback=None, is_canceled_callback=None):
        """
        Импортирует файлы/папки, парсит их и сохраняет данные в БД.
        Обновляет статистику после импорта.

        Args:
            paths: Список путей к файлам или папкам.
            session_name: Имя новой сессии для этого импорта.
            progress_callback: Optional function(current, total, text) for UI progress.
            is_canceled_callback: Optional function() that returns True if the import should be cancelled.
        """
        all_files_to_process = []
        for path in paths:
            if os.path.isdir(path):
                # Рекурсивно собираем все .txt файлы из папки
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        if fname.lower().endswith((".txt", ".log", ".hh", ".summary")):
                             all_files_to_process.append(os.path.join(root, fname))
            elif os.path.isfile(path):
                if path.lower().endswith((".txt", ".log", ".hh", ".summary")):
                     all_files_to_process.append(path)

        total_files = len(all_files_to_process)
        if total_files == 0:
            logger.info("Нет файлов для обработки.")
            if progress_callback:
                 progress_callback(0, 0, "Нет файлов для обработки")
            return

        logger.info(f"Начат импорт {total_files} файлов в сессию '{session_name}'")
        processed_count = 0

        # Создаем новую сессию для этого импорта
        try:
            current_session = self.session_repo.create_session(session_name)
            session_id = current_session.session_id
            logger.info(f"Создана новая сессия для импорта: {session_id}")
        except Exception as e:
            logger.error(f"Не удалось создать сессию для импорта: {e}")
            if progress_callback:
                 progress_callback(0, total_files, f"Ошибка: Не удалось создать сессию: {e}")
            return


        # Словарь для временного хранения данных турниров во время парсинга
        # Ключ: tournament_id, Значение: Dict с объединенными данными
        parsed_tournaments_data: Dict[str, Dict[str, Any]] = {}
        # Список данных финальных рук для пакетного сохранения
        all_final_table_hands_data: List[Dict[str, Any]] = []


        for file_path in all_files_to_process:
            # Проверяем флаг отмены
            if is_canceled_callback and is_canceled_callback():
                logger.info("Импорт отменен пользователем. Прерываем обработку файлов.")
                if progress_callback:
                    progress_callback(processed_count, total_files, "Импорт отменен пользователем")
                return
                
            if progress_callback:
                progress_callback(processed_count, total_files, f"Обработка: {os.path.basename(file_path)}")

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Проверяем первые несколько строк, чтобы определить тип файла
                first_lines = content.splitlines()[:5]  # Берем первые 5 строк для анализа
                
                # Проверяем, похож ли файл на Tournament Summary
                # Характерные признаки TS: "Tournament #", "Buy-in:", "You finished the tournament"
                ts_markers = ["Tournament #", "Buy-in:", "You finished the tournament", "You received a total of"]
                has_ts_markers = any(marker in line for line in first_lines for marker in ts_markers)
                
                # Проверяем, похож ли файл на Hand History
                # Характерные признаки HH: "Poker Hand #", "Table", "Seat", строки с действиями игроков
                hh_markers = ["Poker Hand #", "Table", "Seat"]
                has_hh_markers = any(marker in line for line in first_lines for marker in hh_markers)
                
                # Если больше признаков TS, считаем файл турнирным саммари
                # Если больше признаков HH, считаем файл историей рук
                is_ts = False
                is_hh = False
                
                if has_ts_markers and not has_hh_markers:
                    is_ts = True
                    logger.debug(f"Файл определен как Tournament Summary по содержимому: {file_path}")
                elif has_hh_markers:
                    is_hh = True
                    logger.debug(f"Файл определен как Hand History по содержимому: {file_path}")
                else:
                    # Если нельзя определить тип, пробуем сначала TS-парсер (он делает меньше предположений)
                    # а затем HH-парсер, если TS-парсер не смог распознать файл
                    try:
                        ts_data = self.ts_parser.parse(content, filename=os.path.basename(file_path))
                        if ts_data.get('tournament_id'):
                            is_ts = True
                            logger.debug(f"Файл определен как Tournament Summary после попытки парсинга: {file_path}")
                        else:
                            # Если TS-парсер не смог распознать, пробуем HH-парсер
                            hh_data = self.hh_parser.parse(content, filename=os.path.basename(file_path))
                            if hh_data.get('tournament_id'):
                                is_hh = True
                                logger.debug(f"Файл определен как Hand History после попытки парсинга: {file_path}")
                    except Exception as e:
                        # Если оба парсера вызвали исключение, пропускаем файл
                        logger.warning(f"Не удалось определить тип файла: {file_path}. Файл пропущен. Ошибка: {e}")
                        processed_count += 1
                        continue

                # Если не удалось определить тип файла, пропускаем его
                if not is_hh and not is_ts:
                    logger.warning(f"Не удалось определить тип файла: {file_path}. Файл пропущен.")
                    processed_count += 1
                    continue
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Обрабатываем файл соответствующим парсером
                if is_hh:
                    hh_data = self.hh_parser.parse(content, filename=os.path.basename(file_path))
                    tourney_id = hh_data.get('tournament_id')

                    if tourney_id:
                        # Инициализируем запись в словаре, если ее нет
                        if tourney_id not in parsed_tournaments_data:
                             parsed_tournaments_data[tourney_id] = {'tournament_id': tourney_id, 'session_id': session_id, 'ko_count': 0, 'reached_final_table': False}

                        # Добавляем данные из HH к временной записи турнира
                        parsed_tournaments_data[tourney_id]['start_time'] = parsed_tournaments_data[tourney_id].get('start_time') or hh_data.get('start_time')
                        # Общее KO в турнире - это сумма KO по всем HH файлам для этого турнира
                        # Обновленная версия HandHistoryParser теперь:                        
                        # 1. Обрабатывает руки в хронологическом порядке
                        # 2. Отслеживает временные метки для каждой раздачи
                        # 3. Идентифицирует выбывших игроков, сравнивая последовательные раздачи
                        # 4. Записывает информацию о нокаутах, основываясь на выбывших игроках
                        #
                        # **Решение**: ko_count в таблице tournaments - это сумма hero_ko_this_hand
                        # из всех строк hero_final_table_hands для этого турнира.
                        # Это будет пересчитываться при обновлении статистики.
                        # Парсер HH теперь точно определяет нокауты путем отслеживания выбывших игроков
                        # между последовательными раздачами и заполняет hero_final_table_hands
                        # с правильной информацией о нокаутах.

                        # Обновляем временные данные турнира из HH
                        # Если это первый HH файл для турнира, который достиг финалки
                        # Обновленный HandHistoryParser теперь точно определяет первую раздачу финального стола
                        # благодаря хронологической обработке раздач
                        if hh_data.get('reached_final_table', False):
                             parsed_tournaments_data[tourney_id]['reached_final_table'] = True
                             parsed_tournaments_data[tourney_id]['final_table_initial_stack_chips'] = hh_data.get('final_table_initial_stack_chips')
                             parsed_tournaments_data[tourney_id]['final_table_initial_stack_bb'] = hh_data.get('final_table_initial_stack_bb')

                        # Собираем данные финальных раздач
                        # Обновленный HandHistoryParser обрабатывает раздачи в хронологическом порядке,
                        # определяет выбывших игроков путем сравнения списков игроков между соседними раздачами,
                        # и корректно подсчитывает hero_ko_this_hand для каждой раздачи финалки.
                        ft_hands_data = hh_data.get('final_table_hands_data', [])
                        for hand_data in ft_hands_data:
                             hand_data['session_id'] = session_id # Добавляем session_id к каждой руке
                             all_final_table_hands_data.append(hand_data)


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

            processed_count += 1
            if progress_callback:
                 progress_callback(processed_count, total_files, f"Обработано: {os.path.basename(file_path)}")


        # --- Сохранение данных в БД ---
        # Проверяем флаг отмены перед сохранением в БД
        if is_canceled_callback and is_canceled_callback():
            logger.info("Импорт отменен пользователем. Пропускаем сохранение данных в БД.")
            if progress_callback:
                progress_callback(processed_count, total_files, "Импорт отменен пользователем")
            return
            
        logger.info("Сохранение обработанных данных в БД...")
        total_saved = 0

        # 1. Сохраняем данные финальных раздач (с ON CONFLICT DO NOTHING)
        for hand_data in all_final_table_hands_data:
             try:
                  hand = FinalTableHand.from_dict(hand_data)
                  self.ft_hand_repo.add_hand(hand)
             except Exception as e:
                  logger.error(f"Ошибка сохранения финальной раздачи {hand_data.get('hand_id')} турнира {hand_data.get('tournament_id')}: {e}")


        # 2. Сохраняем/обновляем данные турниров
        for tourney_id, data in parsed_tournaments_data.items():
             try:
                 # Перед сохранением, получаем существующий турнир из БД,
                 # чтобы объединить ko_count, т.к. ko_count теперь вычисляется
                 # суммированием hero_ko_this_hand из hero_final_table_hands.
                 # Новая схема подразумевает, что ko_count в `tournaments`
                 # это просто сумма KO_THIS_HAND из всех рук финалки для этого турнира.
                 # Это значение пересчитывается при обновлении стат.
                 # Здесь мы просто сохраняем то, что получили из TS/HH,
                 # позволяя ApplicationService сделать финальные расчеты KO count.

                 # Запрашиваем текущий турнир для merge
                 existing_tourney = self.tournament_repo.get_tournament_by_id(tourney_id)

                 # Объединяем данные: TS > HH > Existing
                 final_tourney_data = {}
                 if existing_tourney:
                     final_tourney_data.update(existing_tourney.as_dict()) # Base from existing

                 final_tourney_data.update(data) # Override with data from parsed file batch

                 # Специальная логика для полей, которые должны объединяться, а не перезаписываться
                 # ko_count теперь вычисляется в ApplicationService на основе hero_ko_this_hand из рук финалки
                 # reached_final_table = Existing OR New
                 if existing_tourney and existing_tourney.reached_final_table:
                     final_tourney_data['reached_final_table'] = True # Если хоть раз достигли финалки, флаг остается TRUE

                 # final_table_initial_stack - сохраняем только если это первая раздача финалки в истории парсинга этого турнира
                 # Обновленный HandHistoryParser теперь корректно определяет first_ft_hand благодаря хронологической
                 # обработке раздач. ApplicationService должен решить, является ли это первой FT рукой ВООБЩЕ для турнира.
                 # Это можно сделать, проверив наличие initial_stack в БД перед обновлением.
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
                 total_saved += 1

             except Exception as e:
                  logger.error(f"Ошибка сохранения/обновления турнира {tourney_id}: {e}")

        logger.info(f"Сохранено/обновлено {total_saved} турниров. Сохранено {len(all_final_table_hands_data)} рук финального стола.")


        # --- Обновление статистики ---
        # Проверяем флаг отмены перед обновлением статистики
        if is_canceled_callback and is_canceled_callback():
            logger.info("Импорт отменен пользователем. Пропускаем обновление статистики.")
            if progress_callback:
                progress_callback(total_files, total_files, "Импорт отменен пользователем")
            return
            
        logger.info("Обновление агрегированной статистики...")
        try:
             self._update_all_statistics(session_id)
             logger.info("Обновление статистики завершено.")
        except Exception as e:
             logger.error(f"Ошибка при обновлении статистики: {e}")
             if progress_callback:
                  progress_callback(total_files, total_files, f"Ошибка при обновлении статистики: {e}")
             # В реальном приложении здесь может потребоваться более детальная обработка

        if progress_callback:
            progress_callback(total_files, total_files, "Импорт завершен")


    def _update_all_statistics(self, session_id_just_imported: Optional[str] = None):
        """
        Пересчитывает и обновляет все агрегированные статистики (общие и по сессии).
        Вызывается после импорта данных.
        """
        logger.debug("Запущен пересчет всей статистики.")

        # --- Обновление Overall Stats ---
        logger.debug("Обновление общей статистики...")
        overall_stats = self._calculate_overall_stats()
        self.overall_stats_repo.update_overall_stats(overall_stats)
        logger.debug("Общая статистика обновлена.")

        # --- Обновление Place Distribution ---
        logger.debug("Обновление распределения мест...")
        # Сначала сбросим текущее распределение, затем пересчитаем по всем турнирам
        self.place_dist_repo.reset_distribution()
        all_final_tournaments = self.tournament_repo.get_all_tournaments(buyin_filter=None) # Get all, filters applied in calculation
        for tourney in all_final_tournaments:
             # Учитываем место только если турнир достиг финалки и место в диапазоне 1-9
             if tourney.reached_final_table and tourney.finish_place is not None and 1 <= tourney.finish_place <= 9:
                  self.place_dist_repo.increment_place_count(tourney.finish_place)
        logger.debug("Распределение мест обновлено.")

        # --- Обновление KO count для турниров ---
        logger.debug("Обновление ko_count для турниров...")
        all_tournaments = self.tournament_repo.get_all_tournaments()
        for tournament in all_tournaments:
            # Получаем все руки финального стола для этого турнира
            tournament_ft_hands = self.ft_hand_repo.get_hands_by_tournament(tournament.tournament_id)
            # Суммируем KO из всех рук
            total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands)
            # Обновляем ko_count у турнира
            tournament.ko_count = total_ko
            # Сохраняем обновленный турнир
            self.tournament_repo.add_or_update_tournament(tournament)
        logger.debug("KO count для турниров обновлен.")

        # --- Обновление Session Stats ---
        logger.debug("Обновление статистики сессий...")
        sessions_to_update = self.session_repo.get_all_sessions()
        for session in sessions_to_update:
             self._calculate_and_update_session_stats(session.session_id)
        logger.debug("Статистика сессий обновлена.")


    def _calculate_overall_stats(self) -> OverallStats:
        """
        Рассчитывает все показатели для OverallStats на основе данных из БД.
        """
        # Получаем все турниры и финальные руки для расчетов
        all_tournaments = self.tournament_repo.get_all_tournaments()
        all_ft_hands = self.ft_hand_repo.get_all_hands() # Все руки финалок

        stats = OverallStats() # Создаем объект с дефолтными значениями

        stats.total_tournaments = len(all_tournaments)

        # Фильтруем турниры, достигшие финального стола
        final_table_tournaments = [t for t in all_tournaments if t.reached_final_table]
        stats.total_final_tables = len(final_table_tournaments)

        # Расчеты, основанные на турнирах:
        stats.total_buy_in = sum(t.buyin for t in all_tournaments if t.buyin is not None)
        stats.total_prize = sum(t.payout for t in all_tournaments if t.payout is not None)

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

        # Расчет Big KO (требует buyin и payout из турниров)
        # Эта логика находится в плагине BigKOStat. Вызовем его.
        big_ko_results = BigKOStat().compute(all_tournaments, all_ft_hands, []) # Передаем пустые списки для knockout и sessions т.к. данные в БД
        stats.big_ko_x1_5 = big_ko_results.get("x1.5", 0)
        stats.big_ko_x2 = big_ko_results.get("x2", 0)
        stats.big_ko_x10 = big_ko_results.get("x10", 0)
        stats.big_ko_x100 = big_ko_results.get("x100", 0)
        stats.big_ko_x1000 = big_ko_results.get("x1000", 0)
        stats.big_ko_x10000 = big_ko_results.get("x10000", 0)


        # Можно округлить некоторые значения для хранения
        stats.avg_finish_place = round(stats.avg_finish_place, 2)
        stats.avg_finish_place_ft = round(stats.avg_finish_place_ft, 2)
        stats.avg_ko_per_tournament = round(stats.avg_ko_per_tournament, 2)
        stats.avg_ft_initial_stack_chips = round(stats.avg_ft_initial_stack_chips, 2)
        stats.avg_ft_initial_stack_bb = round(stats.avg_ft_initial_stack_bb, 2)
        stats.early_ft_ko_per_tournament = round(stats.early_ft_ko_per_tournament, 2)
        stats.final_table_reach_percent = round(stats.final_table_reach_percent, 2)


        return stats

    def _calculate_and_update_session_stats(self, session_id: str):
        """
        Рассчитывает и обновляет статистику для конкретной сессии.
        """
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


# Создаем синглтон экземпляр ApplicationService
application_service = ApplicationService()