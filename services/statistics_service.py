# -*- coding: utf-8 -*-

"""
Сервис расчета статистики для Royal Stats.
Отвечает за расчет всех статистических показателей,
управление кешем и работу со стат-плагинами.
"""

import os
import json
import hashlib
import logging
import threading
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from models import Tournament, Session, OverallStats, FinalTableHand
from db.repositories import (
    TournamentRepository,
    SessionRepository,
    OverallStatsRepository,
    PlaceDistributionRepository,
    FinalTableHandRepository,
)
from stats import BaseStat, discover_plugins
from .event_bus import EventBus
from .events import StatisticsUpdatedEvent, CacheInvalidatedEvent

logger = logging.getLogger('ROYAL_Stats.StatisticsService')


class StatisticsService:
    """
    Сервис для расчета и управления статистикой турниров.
    """
    
    def __init__(
        self,
        tournament_repo: TournamentRepository,
        session_repo: SessionRepository,
        overall_stats_repo: OverallStatsRepository,
        place_dist_repo: PlaceDistributionRepository,
        ft_hand_repo: FinalTableHandRepository,
        cache_file_path: str = None,
        stat_plugins: List[BaseStat] = None,
        event_bus: Optional[EventBus] = None
    ):
        """
        Инициализация сервиса статистики.
        
        Args:
            tournament_repo: Репозиторий турниров
            session_repo: Репозиторий сессий
            overall_stats_repo: Репозиторий общей статистики
            place_dist_repo: Репозиторий распределения мест
            ft_hand_repo: Репозиторий рук финального стола
            cache_file_path: Путь к файлу кеша (по умолчанию из config)
            stat_plugins: Список плагинов статистики. Если None, плагины
                автоматически загружаются из пакета ``stats`` и entry points
            event_bus: Шина событий для публикации событий статистики
        """
        self.tournament_repo = tournament_repo
        self.session_repo = session_repo
        self.overall_stats_repo = overall_stats_repo
        self.place_dist_repo = place_dist_repo
        self.ft_hand_repo = ft_hand_repo
        self.event_bus = event_bus
        
        # Кеш статистики по БД. Ключ - путь к БД, значение - OverallStats
        self._overall_stats_cache: Dict[str, OverallStats] = {}
        # Кеш гистограммы распределения финишных позиций
        self._place_distribution_cache: Dict[str, Dict[int, int]] = {}
        
        # Файл для сохранения кеша между перезапусками
        if cache_file_path:
            self._cache_file = cache_file_path
            # Создаём папку для файла кеша, если её ещё нет
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
        else:
            # Если путь не передан, используем временный файл в папке с БД
            self._cache_file = None
        self._persistent_cache = self._load_persistent_cache()
        
        # Блокировка для предотвращения параллельного пересчета статистики
        self._stats_update_lock = threading.Lock()
        self._is_updating_stats = False
        
        # Инициализируем плагины статистики
        self.stat_plugins = stat_plugins or self._get_default_stat_plugins()
    
    def _get_default_stat_plugins(self) -> List[BaseStat]:
        """Возвращает список стандартных плагинов статистики."""
        plugins = []
        for plugin_cls in discover_plugins():
            try:
                plugins.append(plugin_cls())
            except Exception as e:  # pragma: no cover - защитная логика
                logger.error(f"Не удалось инициализировать плагин {plugin_cls}: {e}")
        return plugins
    
    def calculate_stats_with_plugins(
        self,
        tournaments: List[Tournament],
        final_table_hands: List[FinalTableHand],
        sessions: Optional[List[Session]] = None,
        precomputed_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Рассчитывает статистику используя плагины.
        
        Args:
            tournaments: Список турниров для расчета
            final_table_hands: Список рук финального стола
            sessions: Список сессий (опционально)
            precomputed_stats: Предварительно рассчитанные значения для оптимизации
            
        Returns:
            Словарь {plugin_name: results} с результатами каждого плагина
        """
        results = {}
        
        for plugin in self.stat_plugins:
            try:
                # Вызываем compute с новой сигнатурой
                plugin_results = plugin.compute(
                    tournaments=tournaments,
                    final_table_hands=final_table_hands,
                    sessions=sessions,
                    precomputed_stats=precomputed_stats or {}
                )
                results[plugin.name] = plugin_results
                logger.debug(f"Плагин {plugin.name} вернул: {plugin_results}")
            except Exception as e:
                logger.error(f"Ошибка в плагине {plugin.name}: {e}")
                results[plugin.name] = {}
        
        return results
    
    def ensure_overall_stats_cached(
        self, 
        db_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> None:
        """
        Гарантирует наличие кешированных статистик для указанной БД.
        
        Args:
            db_path: Путь к файлу базы данных
            progress_callback: Callback для отслеживания прогресса
        """
        if db_path in self._overall_stats_cache and db_path in self._place_distribution_cache:
            return
        
        # Проверяем, не идет ли уже пересчет
        with self._stats_update_lock:
            if self._is_updating_stats:
                logger.debug("Пересчет статистики уже идет, пропускаем")
                return
            self._is_updating_stats = True
        
        try:
            checksum = self._compute_db_checksum(db_path)
            cached = self._persistent_cache.get(db_path)
            if cached and cached.get("checksum") == checksum:
                self._overall_stats_cache[db_path] = cached.get("overall_stats", OverallStats())
                self._place_distribution_cache[db_path] = cached.get("place_distribution", {i: 0 for i in range(1, 10)})
                logger.debug("Используется сохранённый кэш статистики")
                return
            logger.debug("Кэш не найден или устарел, пересчёт статистики")
            
            # Проверяем, есть ли данные в таблице турниров
            count = self.tournament_repo.get_all_tournaments()
            tournaments_num = len(count)
            
            if tournaments_num > 0:
                # Если база не пуста и статистика ещё не рассчитана, пересчитываем
                # НО! Проверяем, есть ли уже статистика в БД
                existing_stats = self.overall_stats_repo.get_overall_stats()
                if existing_stats and existing_stats.total_tournaments > 0:
                    # Используем существующую статистику из БД
                    logger.debug("Используется существующая статистика из БД")
                    self._overall_stats_cache[db_path] = existing_stats
                    distribution = self.place_dist_repo.get_distribution()
                    self._place_distribution_cache[db_path] = distribution
                    return
                else:
                    # Только если статистики нет, запускаем пересчет
                    logger.debug("Статистика отсутствует, запускаем пересчет")
                    self.update_all_statistics("", db_path, progress_callback=progress_callback)
            else:
                # Пустая база — статистика нулевая
                self.overall_stats_repo.update_overall_stats(OverallStats())
            
            # Загружаем статистику из БД и кладём в кеш и файл
            stats = self.overall_stats_repo.get_overall_stats()
            distribution = self.place_dist_repo.get_distribution()
            self._overall_stats_cache[db_path] = stats
            self._place_distribution_cache[db_path] = distribution
            self._persistent_cache[db_path] = {
                "checksum": checksum,
                "overall_stats": stats,
                "place_distribution": distribution,
            }
            self._save_persistent_cache()
        
        finally:
            # Освобождаем флаг
            with self._stats_update_lock:
                self._is_updating_stats = False
    
    def update_all_statistics(
        self, 
        session_id: str,
        db_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        added_tournaments: Optional[List[Tournament]] = None,
        added_hands: Optional[List[FinalTableHand]] = None,
        use_incremental: bool = True
    ):
        """
        Пересчитывает и обновляет все агрегированные статистики (общие и по сессии).
        Вызывается после импорта данных.
        
        Args:
            session_id: ID сессии для обновления статистики (может быть пустой строкой)
            db_path: Путь к файлу базы данных
            progress_callback: Callback для отслеживания прогресса
            added_tournaments: Список добавленных турниров (для инкрементального обновления)
            added_hands: Список добавленных рук (для инкрементального обновления)
            use_incremental: Использовать инкрементальное обновление если возможно
        """
        
        # Если переданы данные для инкрементального обновления и флаг разрешает
        if use_incremental and added_tournaments is not None and added_hands is not None:
            # Собираем ID затронутых турниров
            affected_tournament_ids = list(set(h.tournament_id for h in added_hands))
            
            logger.info(f"Используется инкрементальное обновление статистики")
            self.update_statistics_incremental(
                session_id=session_id,
                db_path=db_path,
                added_tournaments=added_tournaments,
                added_hands=added_hands,
                affected_tournament_ids=affected_tournament_ids,
                progress_callback=progress_callback
            )
            return
        
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
                progress_callback(current_step, total_steps, "Обновление общей статистики...")
            overall_stats = self._calculate_overall_stats()
            self.overall_stats_repo.update_overall_stats(overall_stats)
            # Обновляем кеш для текущей БД
            self._overall_stats_cache[db_path] = overall_stats
            logger.debug("Общая статистика обновлена успешно.")
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, "Общая статистика обновлена")
        except Exception as e:
            logger.error(f"Ошибка при обновлении overall_stats: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # --- Обновление Place Distribution ---
        try:
            new_distribution = {i: 0 for i in range(1, 10)}
            for tourney in all_final_tournaments:
                new_distribution[tourney.finish_place] += 1
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps, f"Обновлено мест: {current_step-1}/{len(all_final_tournaments)}")
            self.place_dist_repo.update_distribution(new_distribution)
            logger.debug(
                f"Распределение мест обновлено для {len(all_final_tournaments)} турниров."
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении place_distribution: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # --- Обновление KO count для турниров ---
        try:
            for tournament in all_tournaments:
                tournament_ft_hands = self.ft_hand_repo.get_hands_by_tournament(tournament.tournament_id)
                total_ko = sum(hand.hero_ko_this_hand for hand in tournament_ft_hands)
                tournament.ko_count = total_ko
                self.tournament_repo.add_or_update_tournament(tournament)
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps, f"Обновлено турниров: {current_step - 1 - len(all_final_tournaments)}/{len(all_tournaments)}")
            logger.debug(
                f"KO count обновлен для {len(all_tournaments)} турниров."
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении ko_count: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # --- Обновление Session Stats ---
        try:
            for session in sessions_to_update:
                try:
                    self._calculate_and_update_session_stats(session.session_id)
                except Exception as e:
                    logger.error(f"Ошибка при обновлении сессии {session.session_id}: {e}")
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps, f"Обновлено сессий: {current_step - 1 - len(all_final_tournaments) - len(all_tournaments)}/{len(sessions_to_update)}")
            logger.debug(
                f"Статистика обновлена для {len(sessions_to_update)} сессий."
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении session stats: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        if progress_callback:
            progress_callback(total_steps, total_steps, "Статистика обновлена")
        
        logger.info("Обновление всей статистики завершено (с учетом возможных ошибок).")
        
        # Сохраняем обновленную статистику в файл кеша
        checksum = self._compute_db_checksum(db_path)
        current_stats = self._overall_stats_cache.get(db_path, OverallStats())
        current_dist = self.place_dist_repo.get_distribution()
        self._place_distribution_cache[db_path] = current_dist
        self._persistent_cache[db_path] = {
            "checksum": checksum,
            "overall_stats": current_stats,
            "place_distribution": current_dist,
        }
        self._save_persistent_cache()
        
        # Публикуем событие об обновлении статистики
        if self.event_bus:
            self.event_bus.publish(StatisticsUpdatedEvent(
                timestamp=datetime.now(),
                source="StatisticsService",
                db_path=db_path,
                session_id=session_id if session_id else None,
                is_overall=True,
                is_session=bool(session_id)
            ))
    
    def get_overall_stats(self, db_path: str) -> OverallStats:
        """Возвращает объект OverallStats с общей статистикой."""
        self.ensure_overall_stats_cached(db_path)
        return self._overall_stats_cache.get(db_path, OverallStats())
    
    def get_place_distribution(self, db_path: str) -> Dict[int, int]:
        """Возвращает распределение мест на финальном столе (1-9)."""
        self.ensure_overall_stats_cached(db_path)
        return self._place_distribution_cache.get(
            db_path,
            self.place_dist_repo.get_distribution(),
        )
    
    def get_place_distribution_for_session(self, session_id: str) -> tuple[Dict[int, int], int]:
        """
        Рассчитывает и возвращает распределение мест (1-9) только для турниров в указанной сессии.
        
        Returns:
            Tuple из распределения мест и общего количества финальных столов в сессии
        """
        tournaments_in_session = self.tournament_repo.get_all_tournaments(session_id=session_id)
        distribution = {i: 0 for i in range(1, 10)}
        total_final_tables_in_session = 0
        
        for tourney in tournaments_in_session:
            if tourney.reached_final_table:
                total_final_tables_in_session += 1
                if tourney.finish_place is not None and 1 <= tourney.finish_place <= 9:
                    distribution[tourney.finish_place] += 1
        
        return distribution, total_final_tables_in_session
    
    def invalidate_cache(self, db_path: str):
        """Инвалидирует кеш для указанной БД."""
        if db_path in self._overall_stats_cache:
            del self._overall_stats_cache[db_path]
        if db_path in self._place_distribution_cache:
            del self._place_distribution_cache[db_path]
        if db_path in self._persistent_cache:
            del self._persistent_cache[db_path]
            self._save_persistent_cache()
        
        # Публикуем событие об инвалидации кеша
        if self.event_bus:
            self.event_bus.publish(CacheInvalidatedEvent(
                timestamp=datetime.now(),
                source="StatisticsService",
                db_path=db_path,
                reason="Manual cache invalidation"
            ))
    
    def update_cache_for_renamed_db(self, old_path: str, new_path: str):
        """Обновляет кеши при переименовании БД."""
        if old_path in self._overall_stats_cache:
            self._overall_stats_cache[new_path] = self._overall_stats_cache.pop(old_path)
        if old_path in self._place_distribution_cache:
            self._place_distribution_cache[new_path] = self._place_distribution_cache.pop(old_path)
        if old_path in self._persistent_cache:
            self._persistent_cache[new_path] = self._persistent_cache.pop(old_path)
            self._save_persistent_cache()
    
    def _calculate_overall_stats(self) -> OverallStats:
        """
        Рассчитывает все показатели для OverallStats на основе данных из БД.
        """
        all_tournaments = self.tournament_repo.get_all_tournaments()
        all_ft_hands = self.ft_hand_repo.get_all_hands()
        logger.debug(
            f"_calculate_overall_stats: Загружено {len(all_tournaments)} турниров"
        )
        logger.debug(
            f"_calculate_overall_stats: Загружено {len(all_ft_hands)} рук финального стола"
        )
        
        stats = OverallStats()
        
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
        
        # Общее количество KO
        stats.total_knockouts = sum(hand.hero_ko_this_hand for hand in all_ft_hands)
        logger.debug(f"Рассчитано total_knockouts: {stats.total_knockouts}")
        
        # Avg KO / Tournament
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
        
        # Среднее KO в ранней финалке на турнир
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
        
        # Финальные столы, начавшиеся неполным составом
        # Используем константу 9 для размера финального стола
        FINAL_TABLE_SIZE = 9
        first_ft_hands: dict[str, FinalTableHand] = {}
        for hand in all_ft_hands:
            if hand.table_size == FINAL_TABLE_SIZE:
                saved = first_ft_hands.get(hand.tournament_id)
                if saved is None or hand.hand_number < saved.hand_number:
                    first_ft_hands[hand.tournament_id] = hand
        
        stats.incomplete_ft_count = sum(
            1 for h in first_ft_hands.values() if h.players_count < FINAL_TABLE_SIZE
        )
        
        # KO в последней 5-max раздаче перед финальным столом
        stats.pre_ft_ko_count = sum(hand.pre_ft_ko for hand in all_ft_hands)

        # Средний результат до финального стола (ChipEV)
        ft_stack_sum = sum(
            t.final_table_initial_stack_chips for t in final_table_tournaments
            if t.final_table_initial_stack_chips is not None
        )
        not_ft_count = stats.total_tournaments - stats.total_final_tables
        if stats.total_tournaments > 0:
            stats.pre_ft_chipev = (
                ft_stack_sum - not_ft_count * 1000
            ) / stats.total_tournaments
        else:
            stats.pre_ft_chipev = 0.0
        
        # Логируем статистику по выплатам для отладки
        tournaments_with_payout = sum(1 for t in all_tournaments if t.payout is not None and t.payout > 0)
        tournaments_without_payout = sum(1 for t in all_tournaments if t.payout is None or t.payout == 0)
        logger.debug(
            f"Турниры с выплатами: {tournaments_with_payout}, без выплат: {tournaments_without_payout}"
        )
        
        # Подготовка предварительно рассчитанных значений для плагинов
        precomputed_stats = {
            'total_tournaments': stats.total_tournaments,
            'total_final_tables': stats.total_final_tables,
            'total_buy_in': stats.total_buy_in,
            'total_prize': stats.total_prize,
            'total_knockouts': stats.total_knockouts,
            'avg_ko_per_tournament': stats.avg_ko_per_tournament,
            'early_ft_ko_count': stats.early_ft_ko_count,
            'early_ft_ko_per_tournament': stats.early_ft_ko_per_tournament,
            'pre_ft_ko_count': stats.pre_ft_ko_count,
            'pre_ft_chipev': stats.pre_ft_chipev,
            'avg_finish_place': stats.avg_finish_place,
            'avg_finish_place_ft': stats.avg_finish_place_ft,
            'avg_finish_place_no_ft': stats.avg_finish_place_no_ft,
            'avg_ft_initial_stack_chips': stats.avg_ft_initial_stack_chips,
            'avg_ft_initial_stack_bb': stats.avg_ft_initial_stack_bb,
            'early_ft_bust_count': stats.early_ft_bust_count,
            'early_ft_bust_per_tournament': stats.early_ft_bust_per_tournament,
            'incomplete_ft_percent': stats.incomplete_ft_count / stats.total_final_tables * 100 if stats.total_final_tables > 0 else 0.0,
            'final_table_reach_percent': stats.final_table_reach_percent,
        }
        
        # Вызов плагинов для расчета специфичных статистик
        plugin_results = self.calculate_stats_with_plugins(
            tournaments=all_tournaments,
            final_table_hands=all_ft_hands,
            sessions=[],  # Для общей статистики сессии не нужны
            precomputed_stats=precomputed_stats
        )
        
        # Обработка результатов Big KO
        if 'Big KO' in plugin_results:
            big_ko_results = plugin_results['Big KO']
            logger.debug(f"BigKO результаты: {big_ko_results}")
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
        
        # Округляем значения для хранения
        stats.avg_finish_place = round(stats.avg_finish_place, 2)
        stats.avg_finish_place_ft = round(stats.avg_finish_place_ft, 2)
        stats.avg_ko_per_tournament = round(stats.avg_ko_per_tournament, 2)
        stats.avg_ft_initial_stack_chips = round(stats.avg_ft_initial_stack_chips, 2)
        stats.avg_ft_initial_stack_bb = round(stats.avg_ft_initial_stack_bb, 2)
        stats.early_ft_ko_per_tournament = round(stats.early_ft_ko_per_tournament, 2)
        stats.early_ft_bust_per_tournament = round(stats.early_ft_bust_per_tournament, 2)
        stats.final_table_reach_percent = round(stats.final_table_reach_percent, 2)
        stats.pre_ft_ko_count = round(stats.pre_ft_ko_count, 2)
        stats.pre_ft_chipev = round(stats.pre_ft_chipev, 2)
        
        logger.debug(
            f"Итоговая статистика: tournaments={stats.total_tournaments}, "
            f"knockouts={stats.total_knockouts}, prize={stats.total_prize}, "
            f"buyin={stats.total_buy_in}"
        )
        return stats
    
    def _calculate_and_update_session_stats(self, session_id: str):
        """
        Рассчитывает и обновляет статистику для конкретной сессии.
        Оптимизирован для эффективной работы с БД.
        """
        session = self.session_repo.get_session_by_id(session_id)
        if not session:
            logger.warning(f"Сессия с ID {session_id} не найдена для обновления статистики.")
            return
        
        # Эффективно получаем все необходимые статистики одним вызовом
        stats = self.session_repo.calculate_session_stats_efficient(session_id)
        
        # Обновляем поля сессии
        session.tournaments_count = stats['tournaments_count']
        session.knockouts_count = stats['knockouts_count']
        session.avg_finish_place = stats['avg_finish_place']
        session.total_prize = stats['total_prize']
        session.total_buy_in = stats['total_buy_in']
        
        self.session_repo.update_session_stats(session)
    
    def _compute_db_checksum(self, path: str) -> str:
        """Возвращает MD5-хеш файла БД."""
        try:
            hasher = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def _load_persistent_cache(self) -> Dict[str, Dict[str, Any]]:
        """Загружает кеш статистики из файла."""
        if not self._cache_file:
            return {}
            
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result = {}
                for db_path, entry in data.items():
                    stats = OverallStats.from_dict(entry.get("overall_stats", {}))
                    distribution = {int(k): int(v) for k, v in entry.get("place_distribution", {}).items()}
                    result[db_path] = {
                        "checksum": entry.get("checksum", ""),
                        "overall_stats": stats,
                        "place_distribution": distribution,
                    }
                return result
            except Exception as e:
                logger.warning(f"Не удалось загрузить кеш статистики: {e}")
        return {}
    
    def _save_persistent_cache(self) -> None:
        """Сохраняет кеш статистики в файл."""
        if not self._cache_file:
            return
            
        data = {}
        for db_path, entry in self._persistent_cache.items():
            data[db_path] = {
                "checksum": entry.get("checksum", ""),
                "overall_stats": entry.get("overall_stats", OverallStats()).as_dict(),
                "place_distribution": entry.get("place_distribution", {i: 0 for i in range(1, 10)}),
            }
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить кеш статистики: {e}")
    
    def increment_overall_stats(
        self,
        db_path: str,
        added_tournaments: List[Tournament],
        added_hands: List[FinalTableHand],
        removed_tournaments: Optional[List[Tournament]] = None,
        removed_hands: Optional[List[FinalTableHand]] = None
    ) -> OverallStats:
        """
        Инкрементально обновляет общую статистику.
        
        Args:
            db_path: Путь к БД
            added_tournaments: Добавленные турниры
            added_hands: Добавленные руки финального стола
            removed_tournaments: Удаленные турниры (опционально)
            removed_hands: Удаленные руки (опционально)
            
        Returns:
            Обновленный объект OverallStats
        """
        # Получаем текущую статистику из кеша или БД
        current_stats = self._overall_stats_cache.get(db_path)
        if current_stats is None:
            current_stats = self.overall_stats_repo.get_overall_stats()
            if current_stats is None:
                current_stats = OverallStats()
        
        removed_tournaments = removed_tournaments or []
        removed_hands = removed_hands or []
        
        # Обновляем счетчики турниров
        delta_tournaments = len(added_tournaments) - len(removed_tournaments)
        current_stats.total_tournaments += delta_tournaments
        
        # Обновляем счетчики финальных столов
        added_ft = [t for t in added_tournaments if t.reached_final_table]
        removed_ft = [t for t in removed_tournaments if t.reached_final_table]
        delta_ft = len(added_ft) - len(removed_ft)
        current_stats.total_final_tables += delta_ft
        
        # Обновляем суммы байинов и выплат
        added_buyin = sum(t.buyin for t in added_tournaments if t.buyin is not None)
        removed_buyin = sum(t.buyin for t in removed_tournaments if t.buyin is not None)
        current_stats.total_buy_in += added_buyin - removed_buyin
        
        added_prize = sum(t.payout if t.payout is not None else 0 for t in added_tournaments)
        removed_prize = sum(t.payout if t.payout is not None else 0 for t in removed_tournaments)
        current_stats.total_prize += added_prize - removed_prize
        
        # Обновляем количество нокаутов
        added_ko = sum(hand.hero_ko_this_hand for hand in added_hands)
        removed_ko = sum(hand.hero_ko_this_hand for hand in removed_hands)
        current_stats.total_knockouts += added_ko - removed_ko
        
        # Обновляем KO в ранней стадии финалки
        added_early_ko = sum(hand.hero_ko_this_hand for hand in added_hands if hand.is_early_final)
        removed_early_ko = sum(hand.hero_ko_this_hand for hand in removed_hands if hand.is_early_final)
        current_stats.early_ft_ko_count += added_early_ko - removed_early_ko
        
        # Обновляем Pre-FT KO
        added_pre_ft_ko = sum(hand.pre_ft_ko for hand in added_hands)
        removed_pre_ft_ko = sum(hand.pre_ft_ko for hand in removed_hands)
        current_stats.pre_ft_ko_count += added_pre_ft_ko - removed_pre_ft_ko
        
        # Пересчитываем средние значения на основе обновленных счетчиков
        if current_stats.total_tournaments > 0:
            # Для среднего места нужны все турниры - инкрементальный подход сложен
            # Поэтому загружаем только места для расчета
            all_places = self.tournament_repo.get_all_finish_places()
            current_stats.avg_finish_place = sum(all_places) / len(all_places) if all_places else 0.0
            
            # Avg KO per tournament
            current_stats.avg_ko_per_tournament = current_stats.total_knockouts / current_stats.total_tournaments
            
            # % Reach FT
            current_stats.final_table_reach_percent = (current_stats.total_final_tables / current_stats.total_tournaments * 100)
        
        if current_stats.total_final_tables > 0:
            # Среднее место на финалке
            ft_places = self.tournament_repo.get_final_table_finish_places()
            current_stats.avg_finish_place_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0
            
            # Avg early FT KO per tournament
            current_stats.early_ft_ko_per_tournament = current_stats.early_ft_ko_count / current_stats.total_final_tables
            
            # Early FT bust
            early_bust_count = len([t for t in added_ft if t.finish_place is not None and 6 <= t.finish_place <= 9])
            early_bust_count -= len([t for t in removed_ft if t.finish_place is not None and 6 <= t.finish_place <= 9])
            current_stats.early_ft_bust_count += early_bust_count
            current_stats.early_ft_bust_per_tournament = current_stats.early_ft_bust_count / current_stats.total_final_tables
        
        # Обновляем стеки финального стола (требует полного пересчета средних)
        ft_stacks_chips = [t.final_table_initial_stack_chips for t in added_ft if t.final_table_initial_stack_chips is not None]
        ft_stacks_bb = [t.final_table_initial_stack_bb for t in added_ft if t.final_table_initial_stack_bb is not None]
        
        if ft_stacks_chips or ft_stacks_bb:
            # Для точного среднего нужно пересчитать полностью
            all_ft_stacks = self.tournament_repo.get_final_table_initial_stacks()
            if all_ft_stacks['chips']:
                current_stats.avg_ft_initial_stack_chips = sum(all_ft_stacks['chips']) / len(all_ft_stacks['chips'])
            if all_ft_stacks['bb']:
                current_stats.avg_ft_initial_stack_bb = sum(all_ft_stacks['bb']) / len(all_ft_stacks['bb'])

        # Пересчитываем средний ChipEV до финалки
        all_ft_stacks = self.tournament_repo.get_final_table_initial_stacks()
        ft_stack_sum = sum(all_ft_stacks['chips']) if all_ft_stacks['chips'] else 0.0
        not_ft_count = current_stats.total_tournaments - current_stats.total_final_tables
        if current_stats.total_tournaments > 0:
            current_stats.pre_ft_chipev = (ft_stack_sum - not_ft_count * 1000) / current_stats.total_tournaments
        else:
            current_stats.pre_ft_chipev = 0.0
        
        # Обновляем статистику Big KO через плагин
        all_tournaments = list(added_tournaments)  # Только новые для инкрементального расчета
        precomputed = {
            'total_tournaments': current_stats.total_tournaments,
            'total_buy_in': current_stats.total_buy_in,
            'total_prize': current_stats.total_prize,
        }
        
        big_ko_plugin = next((p for p in self.stat_plugins if p.name == "Big KO"), None)
        if big_ko_plugin:
            big_ko_delta = big_ko_plugin.compute(all_tournaments, [], precomputed_stats=precomputed)
            # Добавляем дельту к текущим значениям
            current_stats.big_ko_x1_5 += big_ko_delta.get("x1.5", 0)
            current_stats.big_ko_x2 += big_ko_delta.get("x2", 0)
            current_stats.big_ko_x10 += big_ko_delta.get("x10", 0)
            current_stats.big_ko_x100 += big_ko_delta.get("x100", 0)
            current_stats.big_ko_x1000 += big_ko_delta.get("x1000", 0)
            current_stats.big_ko_x10000 += big_ko_delta.get("x10000", 0)
        
        # Округляем значения
        current_stats.avg_finish_place = round(current_stats.avg_finish_place, 2)
        current_stats.avg_finish_place_ft = round(current_stats.avg_finish_place_ft, 2)
        current_stats.avg_ko_per_tournament = round(current_stats.avg_ko_per_tournament, 2)
        current_stats.avg_ft_initial_stack_chips = round(current_stats.avg_ft_initial_stack_chips, 2)
        current_stats.avg_ft_initial_stack_bb = round(current_stats.avg_ft_initial_stack_bb, 2)
        current_stats.early_ft_ko_per_tournament = round(current_stats.early_ft_ko_per_tournament, 2)
        current_stats.early_ft_bust_per_tournament = round(current_stats.early_ft_bust_per_tournament, 2)
        current_stats.final_table_reach_percent = round(current_stats.final_table_reach_percent, 2)
        current_stats.pre_ft_chipev = round(current_stats.pre_ft_chipev, 2)

        return current_stats
    
    def update_statistics_incremental(
        self,
        session_id: str,
        db_path: str,
        added_tournaments: Optional[List[Tournament]] = None,
        added_hands: Optional[List[FinalTableHand]] = None,
        removed_tournaments: Optional[List[Tournament]] = None,
        removed_hands: Optional[List[FinalTableHand]] = None,
        affected_tournament_ids: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        """
        Инкрементально обновляет статистику только для измененных данных.
        
        Args:
            session_id: ID сессии для обновления
            db_path: Путь к БД
            added_tournaments: Добавленные турниры
            added_hands: Добавленные руки
            removed_tournaments: Удаленные турниры
            removed_hands: Удаленные руки
            affected_tournament_ids: ID турниров, требующих обновления KO count
            progress_callback: Callback для отслеживания прогресса
        """
        added_tournaments = added_tournaments or []
        added_hands = added_hands or []
        removed_tournaments = removed_tournaments or []
        removed_hands = removed_hands or []
        affected_tournament_ids = affected_tournament_ids or []
        
        total_steps = 4  # Overall stats, place distribution, KO counts, sessions
        current_step = 0
        
        try:
            # 1. Инкрементальное обновление общей статистики
            if progress_callback:
                progress_callback(current_step, total_steps, "Обновление общей статистики...")
                
            updated_stats = self.increment_overall_stats(
                db_path,
                added_tournaments,
                added_hands,
                removed_tournaments,
                removed_hands
            )
            
            self.overall_stats_repo.update_overall_stats(updated_stats)
            self._overall_stats_cache[db_path] = updated_stats
            current_step += 1
            
            # 2. Инкрементальное обновление распределения мест
            if progress_callback:
                progress_callback(current_step, total_steps, "Обновление распределения мест...")
                
            current_distribution = self._place_distribution_cache.get(db_path, {i: 0 for i in range(1, 10)})
            
            # Добавляем места новых турниров
            for t in added_tournaments:
                if t.reached_final_table and t.finish_place is not None and 1 <= t.finish_place <= 9:
                    current_distribution[t.finish_place] = current_distribution.get(t.finish_place, 0) + 1
                    
            # Убираем места удаленных турниров
            for t in removed_tournaments:
                if t.reached_final_table and t.finish_place is not None and 1 <= t.finish_place <= 9:
                    current_distribution[t.finish_place] = max(0, current_distribution.get(t.finish_place, 0) - 1)
                    
            self.place_dist_repo.update_distribution(current_distribution)
            self._place_distribution_cache[db_path] = current_distribution
            current_step += 1
            
            # 3. Обновление KO count только для затронутых турниров
            if progress_callback:
                progress_callback(current_step, total_steps, "Обновление количества нокаутов...")
                
            # Собираем все затронутые турниры
            all_affected_ids = set(affected_tournament_ids)
            all_affected_ids.update(t.tournament_id for t in added_tournaments)
            all_affected_ids.update(h.tournament_id for h in added_hands)
            
            if all_affected_ids:
                # Эффективно получаем KO counts для всех затронутых турниров одним запросом
                ko_counts = self.ft_hand_repo.get_ko_counts_for_tournaments(list(all_affected_ids))
                
                # Обновляем только те турниры, для которых есть данные
                for tournament_id, ko_count in ko_counts.items():
                    tournament = self.tournament_repo.get_tournament_by_id(tournament_id)
                    if tournament:
                        tournament.ko_count = ko_count
                        self.tournament_repo.add_or_update_tournament(tournament)
                
                # Обновляем турниры без KO (новые турниры без рук финального стола)
                for tournament_id in all_affected_ids - set(ko_counts.keys()):
                    tournament = self.tournament_repo.get_tournament_by_id(tournament_id)
                    if tournament:
                        tournament.ko_count = 0
                        self.tournament_repo.add_or_update_tournament(tournament)
                    
            current_step += 1
            
            # 4. Обновление статистики затронутых сессий
            if progress_callback:
                progress_callback(current_step, total_steps, "Обновление статистики сессий...")
                
            # Определяем затронутые сессии
            affected_sessions = set()
            if session_id:
                affected_sessions.add(session_id)
            affected_sessions.update(t.session_id for t in added_tournaments if t.session_id)
            affected_sessions.update(t.session_id for t in removed_tournaments if t.session_id)
            
            for sess_id in affected_sessions:
                if sess_id:
                    self._calculate_and_update_session_stats(sess_id)
                    
            current_step += 1
            
            # Сохраняем обновленный кеш
            checksum = self._compute_db_checksum(db_path)
            self._persistent_cache[db_path] = {
                "checksum": checksum,
                "overall_stats": updated_stats,
                "place_distribution": current_distribution,
            }
            self._save_persistent_cache()
            
            if progress_callback:
                progress_callback(total_steps, total_steps, "Статистика обновлена")
                
            # Публикуем событие об обновлении
            if self.event_bus:
                self.event_bus.publish(StatisticsUpdatedEvent(
                    timestamp=datetime.now(),
                    source="StatisticsService",
                    db_path=db_path,
                    session_id=session_id if session_id else None,
                    is_overall=True,
                    is_session=bool(affected_sessions),
                    is_incremental=True,
                    added_tournaments=len(added_tournaments),
                    added_hands=len(added_hands)
                ))
                
            logger.info(f"Инкрементальное обновление завершено: +{len(added_tournaments)} турниров, +{len(added_hands)} рук")
            
        except Exception as e:
            logger.error(f"Ошибка при инкрементальном обновлении статистики: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # В случае ошибки можем откатиться к полному пересчету
            logger.warning("Выполняется полный пересчет статистики из-за ошибки инкрементального обновления")
            self.update_all_statistics(session_id, db_path, progress_callback)