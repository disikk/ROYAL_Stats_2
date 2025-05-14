#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Полноценный парсер Tournament Summary‑файлов (GG/ПокерОК и схожих)
"""

import re
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from parsers.base_parser import BaseParser
from models.tournament import Tournament

# Настройка логирования для этого модуля
logger = logging.getLogger('ROYAL_Stats.TournamentSummaryParser')


class TournamentSummaryParser(BaseParser):
    """Парсер Tournament Summary файлов сезона 2023–2025.

    Attributes:
        hero_name: Имя игрока, для которого собираются статистика.
    """
    
    # Регулярные выражения для извлечения данных
    _ID_RE = re.compile(r"Tournament\s+#(?P<tid>\d+)")
    _BUYIN_RE = re.compile(r"Buy[- ]?In\s*:.*?\$(?P<amount>[\d,.]+)")
    # Обновленное регулярное выражение для Players, чтобы корректно обрабатывать 
    # случаи типа "Players: 500 / 1000"
    _PLAYERS_RE = re.compile(r"Players\s*:\s*(?P<count>\d+)(?:\s*/\s*\d+)?") # Берем первое число
    _START_RE = re.compile(
        r"Start\s*Time\s*:\s*(?P<ts>[\d\-/:\s]+)"  # 2025/05/01 18:34:07
    )
    _FINISH_RE = re.compile(
        r"(?P<place>\d+)(?:st|nd|rd|th)\s+place[\s\S]*?\$(?P<prize>[\d,.]+)",
        re.IGNORECASE,
    )

    def __init__(self, hero_name: str = "Hero"):
        """
        Инициализирует парсер сводки турниров.
        
        Args:
            hero_name: Имя игрока, для которого собираются статистика.
        """
        super().__init__(hero_name)

    def parse_file(self, file_path: str) -> Tournament:
        """
        Полностью парсит TS-файл и возвращает структурированный объект Tournament.
        
        Args:
            file_path: Путь к файлу сводки турнира
            
        Returns:
            Объект Tournament с данными о турнире
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если не удалось распарсить данные из файла
        """
        try:
            text = self.read_file_content(file_path)

            tournament_id = self._search_int(self._ID_RE, text, default=-1)
            buy_in = self._search_float(self._BUYIN_RE, text, default=0.0)
            players_parsed = self._search_int(self._PLAYERS_RE, text, default=0) # По умолчанию 0
            start_time = self._search_datetime(self._START_RE, text)

            # Hero section ── на GG бывает блок вида «25th : Hero … $16.37»
            hero_block_match = None
            # Ищем блок, где есть имя героя
            hero_pattern = rf"(?P<place>\d+)(?:st|nd|rd|th)\s*:\s*{re.escape(self.hero_name)}[\s\S]*?\$(?P<prize>[\d,.]+)"
            for match in re.finditer(hero_pattern, text, re.IGNORECASE): # IGNORECASE для имени героя
                hero_block_match = match  # берём последний (финальный) блок

            if hero_block_match is None:
                # fallback – взять первый встреченный «X place … $Y», если блок героя не найден
                logger.warning(
                    f"Блок с именем героя '{self.hero_name}' не найден в файле {file_path}. "
                    f"Попытка найти общее место."
                )
                hero_block_match = self._FINISH_RE.search(text) # Ищем любой блок с местом
            
            if hero_block_match is None:
                # Если даже общий блок с местом не найден, это проблема.
                raise ValueError(f"Не удалось определить место и приз для героя в файле: {file_path}")

            finish_place = int(hero_block_match.group("place"))
            prize_total = self._to_float(hero_block_match.group("prize"))

            # Корректировка количества игроков
            # Если распарсенное количество игроков меньше, чем место героя,
            # или если players_parsed равно 0 (не найдено),
            # устанавливаем количество игроков равным месту героя (минимально возможное).
            if players_parsed == 0:
                logger.warning(
                    f"Количество игроков не найдено в {file_path} для турнира {tournament_id}. "
                    f"Установлено по finish_place = {finish_place}."
                )
                players = finish_place
            elif players_parsed < finish_place:
                logger.warning(
                    f"Распарсенное количество игроков ({players_parsed}) меньше, чем место героя ({finish_place}) "
                    f"в турнире {tournament_id} ({file_path}). "
                    f"Количество игроков будет установлено как {finish_place}."
                )
                players = finish_place
            else:
                players = players_parsed
            
            # Дополнительная проверка перед созданием объекта
            if not (1 <= finish_place <= players):
                # Эта ситуация не должна возникать, если логика выше корректна
                logger.error(
                    f"Критическая ошибка валидации перед созданием Tournament: "
                    f"finish_place={finish_place}, players={players} для турнира {tournament_id} ({file_path}). "
                    f"Устанавливаем players = finish_place."
                )
                players = finish_place # Последняя попытка исправить

            # Ключевая логика: отделяем гарантированный пэйаут (1–3 места) от баунти
            base_payout = self._compute_base_payout(finish_place, buy_in)
            bounty_total = max(prize_total - base_payout, 0.0)

            # Считаем крупные нокауты
            k2, k10, k100, k1k, k10k = self._calculate_large_knockouts(bounty_total, buy_in, players)

            # Создаем объект Tournament
            tournament = Tournament(
                tournament_id=str(tournament_id),
                buy_in=buy_in,
                players_count=players,
                hero_name=self.hero_name,
                finish_place=finish_place,
                prize_total=prize_total,
                bounty_total=bounty_total,
                session_id="",  # Будет заполнено позже при сохранении
                tournament_name=f"Tournament #{tournament_id}",
                start_time=start_time,
                knockouts_x2=k2,
                knockouts_x10=k10,
                knockouts_x100=k100,
                knockouts_x1000=k1k,
                knockouts_x10000=k10k
            )
            
            return tournament
            
        except FileNotFoundError:
            raise
        except ValueError as e:
            logger.error(
                f"Ошибка при создании Tournament для {file_path} (ID: {tournament_id if 'tournament_id' in locals() else 'неизвестно'}): {e}. "
                f"Данные: finish_place={finish_place if 'finish_place' in locals() else 'неизвестно'}, "
                f"players={players if 'players' in locals() else 'неизвестно'}"
            )
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при парсинге файла {file_path}: {e}", exc_info=True)
            raise ValueError(f"Ошибка при парсинге файла {file_path}: {e}")

    def parse_multiple_files(self, file_paths: List[str]) -> List[Tournament]:
        """
        Парсит несколько файлов сводки турниров.
        
        Args:
            file_paths: Список путей к файлам
            
        Returns:
            Список объектов Tournament
        """
        tournaments = []
        errors = []
        
        for file_path in file_paths:
            try:
                tournament = self.parse_file(file_path)
                tournaments.append(tournament)
            except Exception as e:
                logger.error(f"Ошибка при парсинге файла {file_path}: {e}", exc_info=True)
                errors.append(f"{file_path}: {e}")
                
        if errors:
            logger.warning(f"При парсинге файлов возникли ошибки: {len(errors)} из {len(file_paths)}")
            
        return tournaments

    @staticmethod
    def _to_float(text: str) -> float:
        """Преобразует строку в число с плавающей точкой."""
        if not text:
            return 0.0
        return float(text.replace(",", ""))

    @staticmethod
    def _search_int(pattern: re.Pattern[str], text: str, default: int = 0) -> int:
        """Находит целое число в тексте по регулярному выражению."""
        m = pattern.search(text)
        return int(m.group("count" if "count" in pattern.groupindex else 1)) if m else default

    @staticmethod
    def _search_float(pattern: re.Pattern[str], text: str, default: float = 0.0) -> float:
        """Находит число с плавающей точкой в тексте по регулярному выражению."""
        m = pattern.search(text)
        # Убедимся, что используем именованную группу 'amount', если она есть
        group_name = "amount" if "amount" in pattern.groupindex else 1
        return TournamentSummaryParser._to_float(m.group(group_name)) if m else default

    @staticmethod
    def _search_datetime(pattern: re.Pattern[str], text: str) -> Optional[datetime]:
        """Находит дату и время в тексте по регулярному выражению."""
        m = pattern.search(text)
        if not m:
            return None
        raw = m.group("ts").strip()
        # Поддерживаемые форматы даты и времени
        # Порядок важен: сначала более специфичные или часто встречающиеся
        formats_to_try = (
            "%Y/%m/%d %H:%M:%S",  # 2025/05/01 18:34:07
            "%Y-%m-%d %H:%M:%S",  # 2025-05-01 18:34:07
            "%d/%m/%Y %H:%M:%S",  # 01/05/2025 18:34:07
            "%m/%d/%Y %H:%M:%S",  # 05/01/2025 18:34:07
            # Можно добавить другие форматы, если они встречаются
        )
        for fmt in formats_to_try:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        try:  # optional graceful fallback using dateutil
            from dateutil import parser as _dt_parser  # type: ignore

            return _dt_parser.parse(raw)
        except ImportError: # Если dateutil не установлен
            logger.warning(
                "Модуль python-dateutil не найден. Парсинг дат может быть ограничен."
            )
            return None
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Не удалось распарсить дату '{raw}': {e}")
            return None

    @staticmethod
    def _compute_base_payout(place: int, buy_in: float) -> float:
        """
        Фикс‑пэйаут за топ‑3 (иначе 0).
        
        Args:
            place: Место в турнире
            buy_in: Бай-ин турнира
            
        Returns:
            Гарантированный выигрыш за место
        """
        if place == 1:
            return 4 * buy_in
        if place == 2:
            return 3 * buy_in
        if place == 3:
            return 2 * buy_in
        return 0.0

    @staticmethod
    def _calculate_large_knockouts(bounty: float, buy_in: float, players: int = 9) -> tuple[int, int, int, int, int]:
        """
        Возвращает количество нокаутов х2, х10, х100, х1000, х10000.

        Алгоритм: начинаем с самых маленьких (x2) и идем по возрастанию; каждая
        «выкупленная» категория вычитается из *bounty*.
        Макс. нокаутов любого класса за турнир — (игроков - 1).
        
        Args:
            bounty: Общая сумма баунти
            buy_in: Бай-ин турнира
            players: Количество игроков в турнире
            
        Returns:
            Кортеж с количеством нокаутов (x2, x10, x100, x1000, x10000)
        """
        # Гарантируем, что players не меньше 1, чтобы players - 1 было не отрицательным
        max_possible_kos = max(0, players - 1)

        # Проверка чтобы не было деления на ноль
        if buy_in <= 0:
            return 0, 0, 0, 0, 0  # Если buy-in 0 или отрицателен, нокауты невозможны

        def _extract(remaining_bounty: float, multiplier: int) -> tuple[int, float]:
            # Цена одного нокаута данного типа
            one_price = buy_in * multiplier
            
            # Если цена нокаута 0, нет смысла его считать
            if one_price <= 0:
                return 0, remaining_bounty
                
            # Количество нокаутов этого типа (с учетом максимально возможного)
            qty = min(int(remaining_bounty // one_price), max_possible_kos)
            
            # Вычитаем стоимость всех нокаутов из оставшегося баунти
            new_remaining = remaining_bounty - qty * one_price
            
            # Может быть потеря точности при делении, проверяем остаток
            if new_remaining < 0:
                new_remaining = 0.0
            
            return qty, new_remaining

        # Начинаем с наименее ценных (от маленьких к большим)
        x2, remainder = _extract(bounty, 2)
        x10, remainder = _extract(remainder, 10)
        x100, remainder = _extract(remainder, 100)
        x1k, remainder = _extract(remainder, 1000)
        x10k, remainder = _extract(remainder, 10000)
        
        # Проверяем ограничение на максимальное количество нокаутов
        total_kos = x2 + x10 + x100 + x1k + x10k
        if total_kos > max_possible_kos:
            # Если сумма всех нокаутов превышает возможное количество, корректируем
            # Начинаем с наименее ценных множителей
            excess = total_kos - max_possible_kos
            
            if excess > 0 and x2 > 0:
                reduction = min(excess, x2)
                x2 -= reduction
                excess -= reduction
                
            if excess > 0 and x10 > 0:
                reduction = min(excess, x10)
                x10 -= reduction
                excess -= reduction
                
            if excess > 0 and x100 > 0:
                reduction = min(excess, x100)
                x100 -= reduction
                excess -= reduction
                
            if excess > 0 and x1k > 0:
                reduction = min(excess, x1k)
                x1k -= reduction
                excess -= reduction
                
            if excess > 0 and x10k > 0:
                reduction = min(excess, x10k)
                x10k -= reduction
        
        logger.debug(
            f"Рассчитаны нокауты: bounty={bounty}, buy_in={buy_in}, players={players}, "
            f"нокауты: x2={x2}, x10={x10}, x100={x100}, x1k={x1k}, x10k={x10k}"
        )
                
        return x2, x10, x100, x1k, x10k