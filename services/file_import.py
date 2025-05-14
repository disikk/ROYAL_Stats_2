#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис для импорта файлов в покерном трекере ROYAL_Stats.
"""

import os
import logging
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable, Tuple, Union

from config.settings import MAX_THREADS, DEFAULT_HERO_NAME
from parsers.detector import detect_file_type
from parsers.hand_history import HandHistoryParser
from parsers.tournament_summary import TournamentSummaryParser
from models.tournament import Tournament
from models.knockout import Knockout
from core.error_handler import log_error, transaction, ImportError

# Настройка логирования
logger = logging.getLogger('ROYAL_Stats.FileImportService')


class FileImportService:
    """
    Сервис для обработки и импорта файлов истории рук и сводок турниров.
    """
    
    def __init__(self, db_repository, hero_name: str = DEFAULT_HERO_NAME):
        """
        Инициализирует сервис импорта файлов.
        
        Args:
            db_repository: Репозиторий для доступа к данным.
            hero_name: Имя игрока, для которого собираются статистика.
        """
        self.db_repository = db_repository
        self.hero_name = hero_name
        self.hand_history_parser = HandHistoryParser(hero_name=hero_name)
        self.tournament_summary_parser = TournamentSummaryParser(hero_name=hero_name)
    
    @log_error
    def process_files(self, 
                     file_paths: List[str], 
                     session_id: str,
                     progress_callback: Optional[Callable[[int, int], None]] = None,
                     cancel_check: Optional[Callable[[], bool]] = None) -> Dict[str, Any]:
        """
        Обрабатывает файлы истории рук и сводки турниров.
        
        Args:
            file_paths: Список путей к файлам.
            session_id: ID сессии для группировки данных.
            progress_callback: Функция обратного вызова для обновления прогресса (опционально).
            cancel_check: Функция для проверки отмены операции (опционально).
            
        Returns:
            Словарь с результатами обработки:
            - 'processed_files': Количество обработанных файлов
            - 'processed_tournaments': Количество обработанных турниров
            - 'processed_knockouts': Количество обработанных нокаутов
            - 'errors': Список строк с описанием ошибок
            - 'skipped_files': Количество пропущенных файлов
            - 'hand_history_files_found': Количество найденных файлов истории рук
            - 'tournament_summary_files_found': Количество найденных файлов сводки турниров
        """
        # Словарь для хранения результатов
        results = {
            'processed_files': 0,
            'total_files': len(file_paths),
            'processed_tournaments': 0,
            'processed_knockouts': 0,
            'errors': [],
            'skipped_files': 0,
            'hand_history_files_found': 0,
            'tournament_summary_files_found': 0,
            'skipped_tournaments_high_finish_place': 0
        }
        
        # Проверяем и классифицируем файлы
        hand_history_files = []
        tournament_summary_files = []
        
        for file_path in file_paths:
            # Проверка отмены операции
            if cancel_check and cancel_check():
                results['cancelled'] = True
                return results
                
            try:
                file_type = detect_file_type(file_path)
                
                if file_type == 'hand_history':
                    hand_history_files.append(file_path)
                    results['hand_history_files_found'] += 1
                elif file_type == 'tournament_summary':
                    tournament_summary_files.append(file_path)
                    results['tournament_summary_files_found'] += 1
                else:
                    results['skipped_files'] += 1
                    logger.info(f"Файл {file_path} пропущен: неизвестный тип")
            except Exception as e:
                results['errors'].append(f"Ошибка при определении типа файла {file_path}: {str(e)}")
                results['skipped_files'] += 1
                logger.error(f"Ошибка при определении типа файла {file_path}: {str(e)}", exc_info=True)
            
            # Обновление прогресса
            results['processed_files'] += 1
            if progress_callback:
                progress_callback(results['processed_files'], results['total_files'])
                
        logger.info(f"Найдено файлов истории рук: {len(hand_history_files)}")
        logger.info(f"Найдено файлов сводки турниров: {len(tournament_summary_files)}")
        
        # Обрабатываем файлы сводки турниров
        processed_tournaments = self._process_tournament_summaries(
            tournament_summary_files, 
            session_id, 
            results, 
            progress_callback,
            cancel_check
        )
        
        # Обрабатываем файлы истории рук
        processed_knockouts = self._process_hand_histories(
            hand_history_files, 
            session_id, 
            processed_tournaments,  # Передаем обработанные турниры для связывания с нокаутами
            results, 
            progress_callback,
            cancel_check
        )
        
        # Обновляем статистику сессии
        try:
            self.db_repository.update_session_stats(session_id)
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики сессии: {str(e)}", exc_info=True)
            results['errors'].append(f"Ошибка при обновлении статистики сессии: {str(e)}")
        
        return results
    
    def _process_tournament_summaries(self, 
                                     file_paths: List[str], 
                                     session_id: str,
                                     results: Dict[str, Any],
                                     progress_callback: Optional[Callable[[int, int], None]] = None,
                                     cancel_check: Optional[Callable[[], bool]] = None) -> Dict[str, Tournament]:
        """
        Обрабатывает файлы сводки турниров.
        
        Args:
            file_paths: Список путей к файлам сводки турниров.
            session_id: ID сессии для группировки данных.
            results: Словарь с результатами обработки для обновления.
            progress_callback: Функция обратного вызова для обновления прогресса (опционально).
            cancel_check: Функция для проверки отмены операции (опционально).
            
        Returns:
            Словарь {id_турнира: объект_Tournament} с обработанными турнирами.
        """
        processed_tournaments = {}
        
        # Создаем отдельное соединение с БД для этого метода
        db_connection = self.db_repository.db_manager.create_connection()
        
        # Создаем временный репозиторий с новым соединением
        # Это обеспечит потокобезопасность при обработке файлов
        from db.repositories.tournament_repo import TournamentRepository
        temp_repository = TournamentRepository(None)
        temp_repository.db_manager = self.db_repository.db_manager
        temp_repository.db_manager.connection = db_connection
        temp_repository.db_manager.cursor = db_connection.cursor()
        
        try:
            # Обрабатываем файлы в пуле потоков
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                # Отправляем задачи в пул
                future_to_file = {
                    executor.submit(self._parse_tournament_summary, file_path): file_path
                    for file_path in file_paths
                }
                
                # Обрабатываем результаты по мере их завершения
                for future in concurrent.futures.as_completed(future_to_file):
                    # Проверка отмены операции
                    if cancel_check and cancel_check():
                        executor.shutdown(wait=False)
                        results['cancelled'] = True
                        return processed_tournaments
                        
                    file_path = future_to_file[future]
                    try:
                        tournament = future.result()
                        
                        # Проверяем finish_place перед сохранением
                        if tournament.finish_place >= 10:
                            logger.info(
                                f"Турнир {tournament.tournament_id} из файла {file_path} пропущен "
                                f"(finish_place: {tournament.finish_place} >= 10)."
                            )
                            results['skipped_tournaments_high_finish_place'] += 1
                            continue
                        
                        # Устанавливаем session_id
                        tournament.session_id = session_id
                        
                        # Начинаем транзакцию
                        temp_repository.db_manager.begin_transaction()
                        
                        try:
                            # Сохраняем турнир в БД
                            temp_repository.save_tournament(tournament)
                            
                            # Фиксируем транзакцию
                            temp_repository.db_manager.commit()
                            
                            # Добавляем турнир в словарь обработанных турниров
                            processed_tournaments[tournament.tournament_id] = tournament
                            
                            # Обновляем счетчик обработанных турниров
                            results['processed_tournaments'] += 1
                            
                            logger.debug(f"Турнир {tournament.tournament_id} успешно обработан")
                        except Exception as e:
                            # Откатываем транзакцию при ошибке
                            temp_repository.db_manager.rollback()
                            logger.error(f"Ошибка при сохранении турнира {tournament.tournament_id}: {str(e)}", exc_info=True)
                            results['errors'].append(f"Ошибка при сохранении турнира {tournament.tournament_id}: {str(e)}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}", exc_info=True)
                        results['errors'].append(f"Ошибка при обработке файла {file_path}: {str(e)}")
                    
                    # Обновление прогресса
                    if progress_callback:
                        progress_callback(results['processed_files'], results['total_files'])
        finally:
            # Закрываем временное соединение с БД
            db_connection.close()
        
        return processed_tournaments
    
    def _parse_tournament_summary(self, file_path: str) -> Tournament:
        """
        Парсит файл сводки турнира.
        
        Args:
            file_path: Путь к файлу сводки турнира.
            
        Returns:
            Объект Tournament с данными о турнире.
            
        Raises:
            Exception: Если произошла ошибка при парсинге файла.
        """
        try:
            # Парсим файл
            tournament = self.tournament_summary_parser.parse_file(file_path)
            
            return tournament
        except Exception as e:
            logger.error(f"Ошибка при парсинге файла {file_path}: {str(e)}", exc_info=True)
            raise
    
    def _process_hand_histories(self, 
                               file_paths: List[str], 
                               session_id: str,
                               processed_tournaments: Dict[str, Tournament],
                               results: Dict[str, Any],
                               progress_callback: Optional[Callable[[int, int], None]] = None,
                               cancel_check: Optional[Callable[[], bool]] = None) -> List[Knockout]:
        """
        Обрабатывает файлы истории рук.
        
        Args:
            file_paths: Список путей к файлам истории рук.
            session_id: ID сессии для группировки данных.
            processed_tournaments: Словарь с обработанными турнирами.
            results: Словарь с результатами обработки для обновления.
            progress_callback: Функция обратного вызова для обновления прогресса (опционально).
            cancel_check: Функция для проверки отмены операции (опционально).
            
        Returns:
            Список объектов Knockout с данными о нокаутах.
        """
        processed_knockouts = []
        
        # Создаем отдельное соединение с БД для этого метода
        db_connection = self.db_repository.db_manager.create_connection()
        
        # Создаем временный репозиторий с новым соединением
        from db.repositories.knockout_repo import KnockoutRepository
        from db.repositories.tournament_repo import TournamentRepository
        
        ko_repository = KnockoutRepository(None)
        ko_repository.db_manager = self.db_repository.db_manager
        ko_repository.db_manager.connection = db_connection
        ko_repository.db_manager.cursor = db_connection.cursor()
        
        tournament_repository = TournamentRepository(None)
        tournament_repository.db_manager = self.db_repository.db_manager
        tournament_repository.db_manager.connection = db_connection
        tournament_repository.db_manager.cursor = db_connection.cursor()
        
        try:
            # Обрабатываем файлы в пуле потоков
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                # Отправляем задачи в пул
                future_to_file = {
                    executor.submit(self._parse_hand_history, file_path): file_path
                    for file_path in file_paths
                }
                
                # Обрабатываем результаты по мере их завершения
                for future in concurrent.futures.as_completed(future_to_file):
                    # Проверка отмены операции
                    if cancel_check and cancel_check():
                        executor.shutdown(wait=False)
                        results['cancelled'] = True
                        return processed_knockouts
                        
                    file_path = future_to_file[future]
                    try:
                        hand_history_data = future.result()
                        
                        # Если есть ID турнира и нокауты
                        tournament_id = hand_history_data.get('tournament_id')
                        if tournament_id and hand_history_data.get('knockouts'):
                            # Для каждого нокаута устанавливаем session_id
                            for knockout in hand_history_data['knockouts']:
                                knockout.session_id = session_id
                                
                            # Начинаем транзакцию
                            ko_repository.db_manager.begin_transaction()
                            
                            try:
                                # Сохраняем нокауты в БД
                                ko_repository.save_knockouts(hand_history_data['knockouts'], tournament_id, session_id)
                                
                                # Добавляем нокауты в список обработанных
                                processed_knockouts.extend(hand_history_data['knockouts'])
                                
                                # Обновляем счетчик обработанных нокаутов
                                results['processed_knockouts'] += len(hand_history_data['knockouts'])
                                
                                # Обновляем средний начальный стек для турнира, если он есть в processed_tournaments
                                if tournament_id in processed_tournaments and hand_history_data.get('average_initial_stack', 0) > 0:
                                    tournament = processed_tournaments[tournament_id]
                                    tournament.average_initial_stack = hand_history_data['average_initial_stack']
                                    tournament_repository.update_tournament(tournament)
                                
                                # Фиксируем транзакцию
                                ko_repository.db_manager.commit()
                            except Exception as e:
                                # Откатываем транзакцию при ошибке
                                ko_repository.db_manager.rollback()
                                logger.error(f"Ошибка при сохранении нокаутов для турнира {tournament_id}: {str(e)}", exc_info=True)
                                results['errors'].append(f"Ошибка при сохранении нокаутов для турнира {tournament_id}: {str(e)}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}", exc_info=True)
                        results['errors'].append(f"Ошибка при обработке файла {file_path}: {str(e)}")
                    
                    # Обновление прогресса
                    if progress_callback:
                        progress_callback(results['processed_files'], results['total_files'])
        finally:
            # Закрываем временное соединение с БД
            db_connection.close()
            
        return processed_knockouts
    
    def _parse_hand_history(self, file_path: str) -> Dict[str, Any]:
        """
        Парсит файл истории рук.
        
        Args:
            file_path: Путь к файлу истории рук.
            
        Returns:
            Словарь с данными о нокаутах.
            
        Raises:
            Exception: Если произошла ошибка при парсинге файла.
        """
        try:
            # Парсим файл
            hand_history_data = self.hand_history_parser.parse_file(file_path)
            
            return hand_history_data
        except Exception as e:
            logger.error(f"Ошибка при парсинге файла {file_path}: {str(e)}", exc_info=True)
            raise