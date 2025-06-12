# -*- coding: utf-8 -*-

"""
Сервис импорта файлов для Royal Stats.
Отвечает за координацию процесса импорта файлов покера,
работу с парсерами и сохранение данных в БД.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING
from datetime import datetime

from models import Tournament, Session, FinalTableHand
from parsers.file_classifier import FileClassifier

if TYPE_CHECKING:
    from parsers.base_plugin import BaseParserPlugin
    from parsers import discover_plugins
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    FinalTableHandRepository
)
from .event_bus import EventBus
from .events import DataImportedEvent

logger = logging.getLogger('ROYAL_Stats.ImportService')


class ImportService:
    """
    Сервис для импорта файлов истории рук и сводок турниров.
    Координирует работу парсеров и сохранение данных в БД.
    """
    
    def __init__(
        self,
        tournament_repo: TournamentRepository,
        session_repo: SessionRepository,
        ft_hand_repo: FinalTableHandRepository,
        parser_plugins: Optional[List['BaseParserPlugin']] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        Инициализация сервиса импорта.
        
        Args:
            tournament_repo: Репозиторий для работы с турнирами
            session_repo: Репозиторий для работы с сессиями
            ft_hand_repo: Репозиторий для работы с руками финального стола
            parser_plugins: Список парсеров или None для автозагрузки
            event_bus: Шина событий для публикации событий импорта
        """
        self.tournament_repo = tournament_repo
        self.session_repo = session_repo
        self.ft_hand_repo = ft_hand_repo
        self.event_bus = event_bus

        self.parsers = self._init_parsers(parser_plugins)

    def _init_parsers(self, parser_plugins: Optional[List['BaseParserPlugin']]) -> Dict[str, 'BaseParserPlugin']:
        """Загружает парсеры из переданного списка или через plugin_manager."""
        if parser_plugins is None:
            from parsers import discover_plugins
            parser_plugins = [cls() for cls in discover_plugins()]

        parsers: Dict[str, 'BaseParserPlugin'] = {}
        for plugin in parser_plugins:
            try:
                parsers[plugin.file_type] = plugin
            except Exception as exc:  # pragma: no cover - защитная логика
                logger.error("Не удалось инициализировать парсер %s: %s", plugin, exc)
        return parsers
    
    def import_files(
        self,
        paths: List[str],
        session_name: str | None,
        session_id: str | None = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_canceled_callback: Optional[Callable[[], bool]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Импортирует файлы/папки, парсит их и сохраняет данные в БД.
        
        Args:
            paths: Список путей к файлам или папкам.
            session_name: Имя новой сессии (используется, если session_id не задан).
            session_id: Идентификатор существующей сессии для догрузки.
            progress_callback: Optional function(current, total, text) for UI progress.
            is_canceled_callback: Optional function() that returns True if the import should be cancelled.
            
        Returns:
            Словарь с результатами импорта или None в случае ошибки/отмены:
            {
                'session_id': str,
                'imported_tournaments': List[Tournament],
                'imported_hands': List[FinalTableHand],
                'updated_tournament_ids': List[str]
            }
        """
        logger.info(f"=== НАЧАЛО ИМПОРТА ===")
        logger.debug(f"is_canceled_callback передан: {is_canceled_callback is not None}")

        def _cancelled() -> bool:
            """Проверяет, запрошена ли отмена импорта."""
            return bool(is_canceled_callback and is_canceled_callback())
        
        # Инициализируем прогресс-бар и оцениваем количество файлов
        if progress_callback:
            progress_callback(0, 0, "Подготовка файлов...")

        if _cancelled():
            logger.info("Импорт отменен пользователем перед подсчетом файлов.")
            return None

        # Подсчет общего количества файлов-кандидатов
        total_candidates = self._count_candidate_files(paths, is_canceled_callback)
        if total_candidates == 0:
            logger.info("Нет файлов для обработки.")
            if progress_callback:
                progress_callback(0, 0, "Нет файлов для обработки")
            return None

        if _cancelled():
            logger.info("Импорт отменен пользователем после подсчета файлов.")
            if progress_callback:
                progress_callback(0, 0, "Импорт отменен")
            return None
        
        # Сбор и фильтрация покерных файлов
        all_files_to_process, filtered_count = self._collect_poker_files(
            paths, total_candidates, progress_callback, is_canceled_callback
        )

        if filtered_count > 0:
            logger.debug(f"Отфильтровано {filtered_count} файлов без покерных шаблонов")

        total_files = len(all_files_to_process)
        if total_files == 0:
            logger.info("Нет файлов для обработки.")
            if progress_callback:
                progress_callback(0, 0, "Нет файлов для обработки")
            return None

        if _cancelled():
            logger.info("Импорт отменен пользователем после подготовки файлов.")
            if progress_callback:
                progress_callback(0, 0, "Импорт отменен")
            return None
        
        # Рассчитываем веса этапов для прогресса
        PARSING_WEIGHT = 70  # 70% времени на парсинг
        SAVING_WEIGHT = 30   # 30% времени на сохранение
        
        total_steps = 100  # Работаем с процентами
        current_progress = 0
        
        logger.info(
            f"Начат импорт {total_files} файлов в сессию"
            f" '{session_name if session_id is None else session_id}'"
        )
        
        # Создание или получение сессии
        current_session = self._get_or_create_session(session_id, session_name)
        if not current_session:
            if progress_callback:
                progress_callback(0, total_steps, "Ошибка: не удалось создать сессию")
            return None

        if _cancelled():
            logger.info("Импорт отменен пользователем после создания сессии.")
            return None
        
        session_id = current_session.session_id
        
        # Парсинг файлов
        parsed_data = self._parse_files(
            all_files_to_process, 
            session_id,
            current_progress,
            total_steps,
            PARSING_WEIGHT,
            progress_callback,
            is_canceled_callback
        )
        
        if not parsed_data:
            return None  # Импорт был отменен

        if _cancelled():
            logger.info("Импорт отменен пользователем после парсинга файлов.")
            return None
        
        current_progress = PARSING_WEIGHT
        
        # Сохранение данных в БД
        saved_data = self._save_parsed_data(
            parsed_data['tournaments'],
            parsed_data['hands'],
            current_progress,
            total_steps,
            SAVING_WEIGHT,
            progress_callback,
            is_canceled_callback
        )
        
        if not saved_data:
            return None  # Импорт был отменен или произошла ошибка

        if _cancelled():
            logger.info("Импорт отменен пользователем после сохранения данных.")
            return None
        
        # Публикуем событие об успешном импорте
        if self.event_bus and not _cancelled():
            imported_tournament_ids = list(parsed_data['tournaments'].keys())
            self.event_bus.publish(DataImportedEvent(
                timestamp=datetime.now(),
                source="ImportService",
                session_id=session_id,
                imported_tournament_ids=imported_tournament_ids,
                files_processed=total_files,
                tournaments_saved=len(parsed_data['tournaments']),
                hands_saved=len(parsed_data['hands'])
            ))
        
        # Завершение импорта
        if progress_callback and not _cancelled():
            progress_callback(total_steps, total_steps, "Импорт завершен успешно!")
        
        logger.info(f"=== ИМПОРТ ЗАВЕРШЕН ===")
        
        # Возвращаем результаты импорта
        return {
            'session_id': session_id,
            'imported_tournaments': saved_data['tournaments'],
            'imported_hands': saved_data['hands'],
            'updated_tournament_ids': saved_data['updated_tournament_ids']
        }
    
    def _count_candidate_files(
        self, 
        paths: List[str], 
        is_canceled_callback: Optional[Callable[[], bool]]
    ) -> int:
        """Подсчитывает общее количество .txt файлов в указанных путях."""
        total_candidates = 0
        for path in paths:
            if is_canceled_callback and is_canceled_callback():
                return 0
            if os.path.isdir(path):
                for _, _, filenames in os.walk(path):
                    if is_canceled_callback and is_canceled_callback():
                        return 0
                    total_candidates += len([f for f in filenames if f.lower().endswith('.txt')])
            elif os.path.isfile(path) and path.lower().endswith('.txt'):
                total_candidates += 1
        return total_candidates
    
    def _collect_poker_files(
        self,
        paths: List[str],
        total_candidates: int,
        progress_callback: Optional[Callable[[int, int, str], None]],
        is_canceled_callback: Optional[Callable[[], bool]]
    ) -> tuple[List[str], int]:
        """Собирает и фильтрует покерные файлы из указанных путей."""
        all_files_to_process = []
        filtered_files_count = 0
        processed_candidates = 0
        
        for path in paths:
            if is_canceled_callback and is_canceled_callback():
                logger.info("Импорт отменен пользователем при подготовке файлов.")
                if progress_callback:
                    progress_callback(processed_candidates, total_candidates, "Импорт отменен пользователем")
                return [], 0
                
            if os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        if is_canceled_callback and is_canceled_callback():
                            return [], 0
                        if fname.lower().endswith('.txt'):
                            full_path = os.path.join(root, fname)
                            if FileClassifier.is_poker_file(full_path):
                                all_files_to_process.append(full_path)
                            else:
                                filtered_files_count += 1
                            processed_candidates += 1
                            if progress_callback and total_candidates:
                                progress_callback(processed_candidates, total_candidates, "Подготовка файлов...")
            elif os.path.isfile(path) and path.lower().endswith('.txt'):
                if is_canceled_callback and is_canceled_callback():
                    return [], 0
                if FileClassifier.is_poker_file(path):
                    all_files_to_process.append(path)
                else:
                    filtered_files_count += 1
                processed_candidates += 1
                if progress_callback and total_candidates:
                    progress_callback(processed_candidates, total_candidates, "Подготовка файлов...")
        
        return all_files_to_process, filtered_files_count
    
    def _get_or_create_session(
        self, 
        session_id: Optional[str], 
        session_name: Optional[str]
    ) -> Optional[Session]:
        """Получает существующую сессию или создает новую."""
        if session_id:
            current_session = self.session_repo.get_session_by_id(session_id)
            if not current_session:
                logger.error(f"Сессия {session_id} не найдена")
                return None
        else:
            try:
                current_session = self.session_repo.create_session(session_name or "")
                logger.debug(f"Создана новая сессия для импорта: {current_session.session_id}")
            except Exception as e:
                logger.error(f"Не удалось создать сессию для импорта: {e}")
                return None
        
        return current_session
    
    def _parse_files(
        self,
        file_paths: List[str],
        session_id: str,
        current_progress: int,
        total_steps: int,
        parsing_weight: int,
        progress_callback: Optional[Callable[[int, int, str], None]],
        is_canceled_callback: Optional[Callable[[], bool]]
    ) -> Optional[Dict[str, Any]]:
        """Парсит файлы и возвращает структурированные данные."""
        parsed_tournaments_data: Dict[str, Dict[str, Any]] = {}
        all_final_table_hands_data: List[Dict[str, Any]] = []
        
        if progress_callback:
            progress_callback(current_progress, total_steps, "Начинаем обработку файлов...")
        
        files_processed = 0
        total_files = len(file_paths)
        
        for file_path in file_paths:
            # Проверяем флаг отмены
            if is_canceled_callback and is_canceled_callback():
                logger.warning(f"=== ИМПОРТ ОТМЕНЕН при парсинге файлов ===")
                return None
            
            # Обновляем прогресс
            file_progress = int((files_processed / total_files) * parsing_weight)
            if progress_callback:
                progress_callback(file_progress, total_steps, f"Обработка: {os.path.basename(file_path)}")
            
            try:
                # Парсим файл
                self._parse_single_file(
                    file_path, 
                    session_id, 
                    parsed_tournaments_data, 
                    all_final_table_hands_data
                )
            except Exception as e:
                logger.error(f"Ошибка обработки файла {file_path}: {e}")
                # Продолжаем обрабатывать другие файлы
            
            files_processed += 1
        
        return {
            'tournaments': parsed_tournaments_data,
            'hands': all_final_table_hands_data
        }
    
    def _parse_single_file(
        self,
        file_path: str,
        session_id: str,
        parsed_tournaments_data: Dict[str, Dict[str, Any]],
        all_final_table_hands_data: List[Dict[str, Any]]
    ):
        """Парсит отдельный файл и добавляет данные в общие структуры."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Определяем тип файла
        file_type = FileClassifier.determine_file_type(file_path)
        if file_type is None:
            logger.warning(f"Файл не соответствует ожидаемым форматам: {file_path}. Файл пропущен.")
            return
        
        # Обрабатываем файл соответствующим парсером
        parser = self.parsers.get(file_type)
        if not parser:
            logger.warning(f"Не найден парсер для типа {file_type} (файл {file_path})")
            return

        if file_type == 'hh':
            self._parse_hand_history(
                parser,
                content,
                file_path,
                session_id,
                parsed_tournaments_data,
                all_final_table_hands_data
            )
        elif file_type == 'ts':
            self._parse_tournament_summary(
                parser,
                content,
                file_path,
                session_id,
                parsed_tournaments_data
            )
    
    def _parse_hand_history(
        self,
        parser: 'BaseParserPlugin',
        content: str,
        file_path: str,
        session_id: str,
        parsed_tournaments_data: Dict[str, Dict[str, Any]],
        all_final_table_hands_data: List[Dict[str, Any]]
    ):
        """Обрабатывает файл истории рук."""
        hh_result = parser.parse(content, filename=os.path.basename(file_path))
        tourney_id = hh_result.tournament_id
        
        logger.debug(f"Tournament ID: {tourney_id}")
        logger.debug(f"Reached final table: {hh_result.reached_final_table}")
        logger.debug(f"Final table hands data: {len(hh_result.final_table_hands_data)} рук")
        
        if tourney_id:
            # Инициализируем запись в словаре, если ее нет
            if tourney_id not in parsed_tournaments_data:
                parsed_tournaments_data[tourney_id] = {
                    'tournament_id': tourney_id,
                    'session_id': session_id,
                    'ko_count': 0,
                    'reached_final_table': False,
                    'has_hh': False,
                    'has_ts': False
                }
            
            # Добавляем данные из HH к временной записи турнира
            parsed_tournaments_data[tourney_id]['start_time'] = (
                parsed_tournaments_data[tourney_id].get('start_time') or 
                hh_result.start_time
            )
            
            # Обновляем временные данные турнира из HH
            if hh_result.reached_final_table:
                parsed_tournaments_data[tourney_id]['reached_final_table'] = True
                parsed_tournaments_data[tourney_id]['final_table_initial_stack_chips'] = hh_result.final_table_initial_stack_chips
                parsed_tournaments_data[tourney_id]['final_table_initial_stack_bb'] = hh_result.final_table_initial_stack_bb
                parsed_tournaments_data[tourney_id]['final_table_start_players'] = hh_result.final_table_start_players

            parsed_tournaments_data[tourney_id]['has_hh'] = True
            
            # Собираем данные финальных раздач
            ft_hands_data = hh_result.final_table_hands_data
            for hand_data in ft_hands_data:
                hand_data['session_id'] = session_id
                all_final_table_hands_data.append(hand_data)
    
    def _parse_tournament_summary(
        self,
        parser: 'BaseParserPlugin',
        content: str,
        file_path: str,
        session_id: str,
        parsed_tournaments_data: Dict[str, Dict[str, Any]]
    ):
        """Обрабатывает файл сводки турнира."""
        ts_result = parser.parse(content, filename=os.path.basename(file_path))
        tourney_id = ts_result.tournament_id
        
        if tourney_id:
            # Инициализируем запись, если ее нет
            if tourney_id not in parsed_tournaments_data:
                parsed_tournaments_data[tourney_id] = {
                    'tournament_id': tourney_id,
                    'session_id': session_id,
                    'ko_count': 0,
                    'reached_final_table': False,
                    'has_hh': False,
                    'has_ts': False
                }
            
            # Обновляем временные данные турнира из TS (TS имеет приоритет)
            parsed_tournaments_data[tourney_id]['tournament_name'] = (
                ts_result.tournament_name or 
                parsed_tournaments_data[tourney_id].get('tournament_name')
            )
            parsed_tournaments_data[tourney_id]['start_time'] = (
                ts_result.start_time or 
                parsed_tournaments_data[tourney_id].get('start_time')
            )
            parsed_tournaments_data[tourney_id]['buyin'] = (
                ts_result.buyin or 
                parsed_tournaments_data[tourney_id].get('buyin')
            )
            parsed_tournaments_data[tourney_id]['payout'] = (
                ts_result.payout or 
                parsed_tournaments_data[tourney_id].get('payout')
            )
            parsed_tournaments_data[tourney_id]['finish_place'] = (
                ts_result.finish_place or
                parsed_tournaments_data[tourney_id].get('finish_place')
            )
            parsed_tournaments_data[tourney_id]['has_ts'] = True
    
    def _save_parsed_data(
        self,
        parsed_tournaments_data: Dict[str, Dict[str, Any]],
        all_final_table_hands_data: List[Dict[str, Any]],
        current_progress: int,
        total_steps: int,
        saving_weight: int,
        progress_callback: Optional[Callable[[int, int, str], None]],
        is_canceled_callback: Optional[Callable[[], bool]]
    ) -> Optional[Dict[str, Any]]:
        """
        Сохраняет распарсенные данные в БД.
        
        Returns:
            Словарь с сохраненными данными или None в случае отмены
        """
        # Проверяем флаг отмены перед сохранением
        if is_canceled_callback and is_canceled_callback():
            logger.warning(f"=== ИМПОРТ ОТМЕНЕН перед сохранением в БД ===")
            return None
        
        logger.info("Сохранение обработанных данных в БД...")
        if progress_callback:
            progress_callback(current_progress, total_steps, "Сохранение данных в базу...")
        
        # Списки для сбора сохраненных объектов
        saved_tournaments = []
        saved_hands = []
        updated_tournament_ids = []
        
        # Сохраняем турниры
        tournaments_saved, tournament_objects, updated_ids = self._save_tournaments(
            parsed_tournaments_data,
            current_progress,
            total_steps,
            saving_weight * 0.4,
            progress_callback
        )
        saved_tournaments.extend(tournament_objects)
        updated_tournament_ids.extend(updated_ids)
        
        logger.debug(f"Сохранено/обновлено {tournaments_saved} турниров.")
        
        # Сохраняем руки финального стола
        hands_saved, hand_objects = self._save_final_table_hands(
            all_final_table_hands_data,
            current_progress + int(saving_weight * 0.4),
            total_steps,
            saving_weight * 0.4,
            progress_callback
        )
        saved_hands.extend(hand_objects)
        
        logger.debug(f"Сохранение рук завершено: {hands_saved} из {len(all_final_table_hands_data)}")
        
        # Обновляем ko_count для турниров
        self._update_ko_counts(
            parsed_tournaments_data,
            current_progress + int(saving_weight * 0.8),
            total_steps,
            saving_weight * 0.2,
            progress_callback
        )
        
        logger.info(f"Сохранено/обновлено {tournaments_saved} турниров. "
                   f"Сохранено {hands_saved} рук финального стола.")
        
        return {
            'tournaments': saved_tournaments,
            'hands': saved_hands,
            'updated_tournament_ids': updated_tournament_ids
        }
    
    def _save_tournaments(
        self,
        parsed_tournaments_data: Dict[str, Dict[str, Any]],
        current_progress: int,
        total_steps: int,
        weight: float,
        progress_callback: Optional[Callable[[int, int, str], None]]
    ) -> tuple[int, List[Tournament], List[str]]:
        """
        Сохраняет или обновляет турниры в БД.
        
        Returns:
            Кортеж из (количество сохраненных, список объектов Tournament, список обновленных ID)
        """
        tournaments_saved = 0
        total_tournaments = len(parsed_tournaments_data)
        saved_objects: List[Tournament] = []
        updated_ids: List[str] = []
        tournaments_to_save: List[Tournament] = []

        for tourney_id, data in parsed_tournaments_data.items():
            try:
                existing_tourney = self.tournament_repo.get_tournament_by_id(tourney_id)

                final_tourney_data: Dict[str, Any] = {}
                if existing_tourney:
                    final_tourney_data.update(existing_tourney.as_dict())

                final_tourney_data.update(data)

                if existing_tourney:
                    final_tourney_data['has_ts'] = (
                        existing_tourney.has_ts or data.get('has_ts', False)
                    )
                    final_tourney_data['has_hh'] = (
                        existing_tourney.has_hh or data.get('has_hh', False)
                    )
                else:
                    final_tourney_data.setdefault('has_ts', False)
                    final_tourney_data.setdefault('has_hh', False)

                if existing_tourney and existing_tourney.reached_final_table:
                    final_tourney_data['reached_final_table'] = True

                if existing_tourney and existing_tourney.final_table_initial_stack_chips is not None:
                    final_tourney_data['final_table_initial_stack_chips'] = existing_tourney.final_table_initial_stack_chips
                    final_tourney_data['final_table_initial_stack_bb'] = existing_tourney.final_table_initial_stack_bb

                if existing_tourney and existing_tourney.final_table_start_players is not None:
                    final_tourney_data['final_table_start_players'] = existing_tourney.final_table_start_players

                if existing_tourney and existing_tourney.session_id:
                    final_tourney_data['session_id'] = existing_tourney.session_id

                # Не устанавливаем reached_final_table автоматически по месту!
                # Этот флаг должен устанавливаться только при наличии Hand History
                # с реальными данными о финальном столе (9-max)
                
                merged_tournament = Tournament.from_dict(final_tourney_data)

                if existing_tourney:
                    def _strip(t: Tournament) -> dict:
                        d = t.as_dict()
                        d.pop("id", None)
                        return d

                    if _strip(existing_tourney) == _strip(merged_tournament):
                        continue
                    updated_ids.append(tourney_id)
                else:
                    saved_objects.append(merged_tournament)

                tournaments_to_save.append(merged_tournament)
                tournaments_saved += 1
            except Exception as e:
                logger.error(f"Ошибка сохранения/обновления турнира {tourney_id}: {e}")

        if tournaments_to_save:
            self.tournament_repo.add_or_update_many(tournaments_to_save)

        if progress_callback:
            progress_callback(current_progress + int(weight), total_steps,
                             f"Сохранено турниров: {tournaments_saved}/{total_tournaments}")

        return tournaments_saved, saved_objects, updated_ids
    
    def _save_final_table_hands(
        self,
        all_final_table_hands_data: List[Dict[str, Any]],
        current_progress: int,
        total_steps: int,
        weight: float,
        progress_callback: Optional[Callable[[int, int, str], None]]
    ) -> tuple[int, List[FinalTableHand]]:
        """
        Сохраняет руки финального стола в БД.
        
        Returns:
            Кортеж из (количество сохраненных, список объектов FinalTableHand)
        """
        logger.debug(f"Начинаем сохранение {len(all_final_table_hands_data)} рук финального стола")
        
        total_hands_to_save = len(all_final_table_hands_data)
        saved_objects: List[FinalTableHand] = []

        for hand_data in all_final_table_hands_data:
            try:
                saved_objects.append(FinalTableHand.from_dict(hand_data))
            except Exception as e:
                logger.error(
                    f"Ошибка подготовки финальной раздачи {hand_data.get('hand_id')} "
                    f"турнира {hand_data.get('tournament_id')}: {e}"
                )

        if saved_objects:
            self.ft_hand_repo.add_hands(saved_objects)

        if progress_callback:
            progress_callback(current_progress + int(weight), total_steps,
                             f"Сохранено рук: {len(saved_objects)}/{total_hands_to_save}")

        return len(saved_objects), saved_objects
    
    def _update_ko_counts(
        self,
        parsed_tournaments_data: Dict[str, Dict[str, Any]],
        current_progress: int,
        total_steps: int,
        weight: float,
        progress_callback: Optional[Callable[[int, int, str], None]]
    ):
        """Обновляет ko_count для турниров на основе сохраненных рук."""
        logger.debug("Подсчет ko_count для турниров...")
        if progress_callback:
            progress_callback(current_progress, total_steps, "Подсчет нокаутов...")
        
        tournaments_processed = 0
        total_tournaments = len(parsed_tournaments_data)
        
        for tourney_id in parsed_tournaments_data:
            try:
                # Получаем все руки финального стола для этого турнира из БД
                tournament_ft_hands = self.ft_hand_repo.get_hands_by_tournament(tourney_id)
                # Суммируем KO из всех рук
                total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands)
                # Обновляем ko_count
                parsed_tournaments_data[tourney_id]['ko_count'] = total_ko
                tournaments_processed += 1
                
                # Обновляем прогресс
                if tournaments_processed % 5 == 0 or tournaments_processed == total_tournaments:
                    ko_progress = current_progress + int((tournaments_processed / max(total_tournaments, 1)) * weight)
                    if progress_callback:
                        progress_callback(ko_progress, total_steps, f"Обработано турниров: {tournaments_processed}/{total_tournaments}")
                        
            except Exception as e:
                logger.error(f"Ошибка подсчета KO для турнира {tourney_id}: {e}")