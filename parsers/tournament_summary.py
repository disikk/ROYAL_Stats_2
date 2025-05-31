# -*- coding: utf-8 -*-

"""
Парсер итогового Tournament Summary для Hero.
Бай-ин приоритетно извлекаем из первой строки (названия турнира), 
а если не найден - из специальной строки Buy-in.
Выплату берем из строки "You received a total of".
"""

import re
import logging
from typing import Dict, Any, Optional
import config
from .base_parser import BaseParser # Наследуем от BaseParser

logger = logging.getLogger('ROYAL_Stats.TournamentSummaryParser')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)


class TournamentSummaryParser(BaseParser):
    """
    Парсер summary-файла турнира только для Hero.
    """

    def __init__(self, hero_name: str = config.HERO_NAME):
        super().__init__(hero_name)
        # --- Регулярки для парсинга TS ---
        self.re_tournament_id_title = re.compile(r"Tournament #(\d+)") # Из заголовка (первая строка)
        self.re_buyin_line = re.compile(r"Buy-in:.*?(\$|€)([\d]+(?:[.,]\d+)?)(?:\+(\$|€)?([\d]+(?:[.,]\d+)?))?") # Для поиска бай-ина в специальной строке "Buy-in:"
        self.re_place = re.compile(r"You finished the tournament in (\d+)[a-z]{0,2} place") # Место Hero
        self.re_payout = re.compile(r"You received a total of (?:\$|€)?([\d,]+(?:\.\d+)?)") # Выплата Hero
        self.re_start_time = re.compile(r"Tournament started (\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})") # Время старта
        self.re_tournament_name_title = re.compile(r"Tournament #\d+,\s*(.+)") # Название турнира из заголовка (первая строка)


    def parse(self, file_content: str, filename: str = "") -> Dict[str, Any]:
        """
        Парсит summary-файл, извлекая информацию о турнире для Hero.

        Args:
            file_content: Содержимое файла в виде строки.
            filename: Имя файла.

        Returns:
             Словарь с ключами:
             'tournament_id': str,
             'tournament_name': str,
             'start_time': str,
             'buyin': float,
             'payout': float,
             'finish_place': int
             (Значения могут быть None, если не найдены)
        """
        lines = file_content.splitlines()
        tournament_id: Optional[str] = None
        tournament_name: Optional[str] = None
        start_time: Optional[str] = None
        buyin: Optional[float] = None
        payout: Optional[float] = None
        finish_place: Optional[int] = None

        # 1. Парсим первую строку для ID, названия и бай-ина (приоритетно из первой строки)
        if lines:
            first_line = lines[0]
            m_tid_title = self.re_tournament_id_title.search(first_line)
            if m_tid_title:
                tournament_id = m_tid_title.group(1)

            m_name_title = self.re_tournament_name_title.search(first_line)
            if m_name_title:
                 # Удаляем символы валюты и "Mystery Battle Royale" из названия, если есть
                 name_part = m_name_title.group(1).split(',')[0]
                 name_part = re.sub(r'[$€]', '', name_part).strip()
                 name_part = name_part.replace("Mystery Battle Royale", "").strip()
                 tournament_name = name_part
            
            # Извлекаем бай-ин из первой строки (приоритетный метод)
            # Ищем сумму после символа валюты, возможно с +fee
            m_buyin_title = re.search(r"[$€]([\d]+(?:[.,]\d+)?)(?:\+[$€]?([\d]+(?:[.,]\d+)?)?)?", first_line)
            if m_buyin_title:
                try:
                    main_buyin_str = m_buyin_title.group(1).replace(',', '.')
                    buyin = float(main_buyin_str)
                    # Если есть fee (группа 2), добавляем её к бай-ину
                    if m_buyin_title.group(2):
                        fee_str = m_buyin_title.group(2).replace(',', '.')
                        buyin += float(fee_str)
                    logger.debug(f"Бай-ин из заголовка (приоритетный метод): {buyin}")
                except (ValueError, IndexError, AttributeError) as e:
                    logger.warning(f"Не удалось распарсить бай-ин из заголовка: {e} в файле {filename}")


        # 2. Парсим файл целиком для остальных данных
        file_content_str = file_content # Работаем с полной строкой для поиска по всему файлу

        m_start_time = self.re_start_time.search(file_content_str)
        if m_start_time:
            start_time = m_start_time.group(1)

        m_place = self.re_place.search(file_content_str)
        if m_place:
            try:
                finish_place = int(m_place.group(1))
            except ValueError:
                 logger.warning(f"Не удалось распарсить место из '{m_place.group(1)}' в файле {filename}")


        m_payout = self.re_payout.search(file_content_str)
        if m_payout:
            try:
                # Удаляем запятые-разделители тысяч
                payout_str = m_payout.group(1).replace(',', '')
                payout = float(payout_str)
            except ValueError:
                 logger.warning(f"Не удалось распарсить выплату из '{m_payout.group(1)}' в файле {filename}")


        # 3. Поиск бай-ина из специальной строки "Buy-in:" если не найден в заголовке
        if buyin is None:
            m_buyin_line = self.re_buyin_line.search(file_content_str)
            if m_buyin_line:
                try:
                    # Группы: 1 - символ валюты 1, 2 - основная часть бай-ина, 3 - символ валюты 2 (для фи), 4 - часть фи
                    main_buyin_str = m_buyin_line.group(2).replace(',', '.')
                    fee_str = m_buyin_line.group(4)
                    buyin = float(main_buyin_str)
                    if fee_str:
                        buyin += float(fee_str.replace(',', '.'))
                    logger.debug(f"Бай-ин из строки Buy-in: {buyin}")
                except ValueError:
                    logger.warning(f"Не удалось распарсить бай-ин из строки Buy-in: в файле {filename}")


        if tournament_id is None:
            logger.warning(f"Не удалось извлечь Tournament ID из файла Summary: {filename}. Файл пропущен.")
            return {'tournament_id': None} # Пропускаем файл без ID


        result = {
            "tournament_id": tournament_id,
            "tournament_name": tournament_name,
            "start_time": start_time,
            "buyin": buyin,
            "payout": payout,
            "finish_place": finish_place,
        }

        logger.debug(f"Парсинг TS завершен для {tournament_id}. Данные: {result}")

        return result