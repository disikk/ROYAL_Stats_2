# -*- coding: utf-8 -*-
"""
Парсер файлов истории рук (hand history) для покерного трекера ROYAL_Stats (Hero-only).
Переписан под новую архитектуру и требования.

Основные принципы:
- Извлекает данные турнира (ID, дату, общее KO).
- Извлекает данные по каждой раздаче финального стола (9-max, >=50/100 BB) для Hero.
- Определяет первую раздачу финального стола и стек Hero в ней.
- Корректно считает KO Hero в каждой раздаче финалки.
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
import config
from models import Tournament, FinalTableHand # Импортируем модели
from .base_parser import BaseParser # ИМПОРТИРУЕМ BaseParser

logger = logging.getLogger('ROYAL_Stats.HandHistoryParser')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

# --- Регулярки для парсинга HH ---
RE_HAND_START = re.compile(r'^Poker Hand #(?P<hand_id>[A-Za-z0-9]+): Tournament #(?P<tournament_id>\d+),') # Адаптировано для GG формата
RE_TABLE_INFO = re.compile(r"^Table '\d+' (?P<table_size>\d+)-max Seat #\d+ is the button")
RE_BLINDS_HEADER = re.compile(r"Level\d+\(([\d,]+)/([\d,]+)\)") # Для поиска блайндов в заголовке раздачи
RE_SEAT = re.compile(r'^Seat \d+: (?P<player_name>[^()]+?) \((?P<stack>[-\d,]+) in chips\)')
RE_ACTION = re.compile(r'^(?P<player_name>[^:]+): (?P<action>posts|bets|calls|raises|all-in|checks|folds)\b(?:.*?)(?P<amount>[\d,]+)?')
RE_RAISE_TO = re.compile(r'raises [\d,]+ to ([\d,]+)')
RE_UNCALLED = re.compile(r'^Uncalled bet \(([\d,]+)\) returned to ([^\n]+)')
RE_COLLECTED = re.compile(r'^([^:]+) collected ([\d,]+) from pot')
RE_SUMMARY = re.compile(r'^\*\*\* SUMMARY \*\*\*')
RE_DATE = re.compile(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})") # Для поиска даты/времени турнира

CHIP = lambda s: int(s.replace(',', '')) if s else 0
NAME = lambda s: s.strip()

class Pot:
    """Внутреннее представление банка для подсчета KO."""
    __slots__ = ('size', 'eligible', 'winners')
    def __init__(self, size: int, eligible: Set[str]):
        self.size = size
        self.eligible: Set[str] = eligible.copy()
        self.winners: Set[str] = set()

class HandData:
    """Внутреннее представление данных раздачи для парсинга KO."""
    __slots__ = ('hand_id', 'hand_number', 'tournament_id', 'table_size', 'bb', 'seats', 'contrib', 'collects', 'pots', 'hero_stack', 'hero_ko_this_hand', 'is_early_final')

    def __init__(self, hand_id: str, hand_number: int, tournament_id: str, table_size: int, bb: float, seats: Dict[str, int]):
        self.hand_id = hand_id
        self.hand_number = hand_number
        self.tournament_id = tournament_id
        self.table_size = table_size
        self.bb = bb
        self.seats = seats
        self.contrib: Dict[str, int] = {}
        self.collects: Dict[str, int] = {}
        self.pots: List[Pot] = []
        self.hero_stack = seats.get(config.HERO_NAME) # Стек Hero в начале раздачи
        self.hero_ko_this_hand = 0 # KO Hero в этой раздаче
        self.is_early_final = False # Флаг ранней стадии финалки

class HandHistoryParser(BaseParser):
    def __init__(self, hero_name: str = config.HERO_NAME):
        super().__init__(hero_name)
        self._tournament_id: Optional[str] = None
        self._start_time: Optional[str] = None
        self._hands: List[HandData] = [] # Все раздачи из файла
        self._final_table_hands: List[HandData] = [] # Только раздачи финального стола (9-max, >=50/100 BB)


    def parse(self, file_content: str, filename: str = "") -> Dict[str, Any]:
        """
        Парсит HH-файл. Возвращает данные турнира и список данных раздач финального стола.

        Returns:
            Словарь с ключами:
            'tournament_id': str,
            'start_time': str,
            'reached_final_table': bool,
            'final_table_initial_stack_chips': float,
            'final_table_initial_stack_bb': float,
            'final_table_hands_data': List[Dict[str, Any]] # Список данных по рукам финалки
        """
        lines = file_content.splitlines()
        self._reset() # Сброс состояния парсера для нового файла

        hand_number_counter = 0
        i = 0
        first_ft_hand_data: Optional[HandData] = None # Временная переменная для первой руки финалки

        # Пробуем найти Tournament ID и Start Time в первых строках файла
        for line in lines[:20]: # Проверяем первые 20 строк
             if not self._tournament_id:
                 m_tid = RE_HAND_START.search(line)
                 if m_tid:
                     self._tournament_id = m_tid.group('tournament_id')
             if not self._start_time:
                  m_dt = RE_DATE.search(line)
                  if m_dt:
                       self._start_time = m_dt.group(1)
             if self._tournament_id and self._start_time:
                 break

        if not self._tournament_id:
             # Попытка извлечь Tournament ID из имени файла как fallback
             m_tid_fn = re.search(r"Tournament #(\d+)", filename)
             if m_tid_fn:
                 self._tournament_id = m_tid_fn.group(1)
                 logger.debug(f"Турнир ID из имени файла: {self._tournament_id}")

        if not self._tournament_id:
            logger.warning(f"Не удалось извлечь Tournament ID из файла HH: {filename}. Файл пропущен.")
            return {'tournament_id': None} # Пропускаем файл без ID

        logger.debug(f"Начат парсинг HH для турнира {self._tournament_id}, файл: {filename}")

        # --- Парсим все раздачи ---
        current_line_idx = 0
        while current_line_idx < len(lines):
            if RE_HAND_START.match(lines[current_line_idx]):
                hand_number_counter += 1
                try:
                     # Парсим только базовые данные раздачи и определяем, относится ли она к финалке
                     current_line_idx, hand_data = self._parse_single_hand_initial_data(lines, current_line_idx, self._tournament_id, hand_number_counter)

                     if hand_data:
                         self._hands.append(hand_data) # Сохраняем все раздачи (опционально)

                         # Проверяем условия финального стола (9-max и >=50/100 BB)
                         if hand_data.table_size == config.FINAL_TABLE_SIZE and hand_data.bb >= config.MIN_KO_BLIND_LEVEL_BB:
                              # Это раздача финального стола (по нашим критериям)
                              self._final_table_hands.append(hand_data)

                              # Если это первая раздача финального стола, сохраняем ее данные
                              if first_ft_hand_data is None:
                                  first_ft_hand_data = hand_data
                                  logger.debug(f"Найдена первая раздача финального стола ({hand_data.table_size}-max, BB={hand_data.bb}) в турнире {self._tournament_id}. Раздача #{hand_data.hand_number}. Стек Hero: {hand_data.hero_stack}")

                              # Определяем, является ли раздача "ранней" стадией финалки (9-6 игроков)
                              if 6 <= hand_data.table_size <= config.FINAL_TABLE_SIZE: # Проверяем размер стола в раздаче
                                   hand_data.is_early_final = True


                    # Если hand_data is None, _parse_single_hand_initial_data уже сдвинул current_line_idx
                except Exception as e:
                    logger.error(f"Ошибка парсинга раздачи в файле {filename}, строка {current_line_idx}: {e}")
                    # Находим начало следующей раздачи, чтобы продолжить парсинг
                    temp_idx = current_line_idx + 1
                    while temp_idx < len(lines) and not RE_HAND_START.match(lines[temp_idx]):
                        temp_idx += 1
                    current_line_idx = temp_idx # Сдвигаем индекс к началу следующей раздачи или концу файла
                    continue # Переходим к следующей итерации цикла


            else:
                current_line_idx += 1

        # --- Повторный проход по раздачам финалки для подсчета KO ---
        # Теперь, когда у нас есть все HandData для финалки, парсим действия и сборы
        # для КАЖДОЙ раздачи финалки, чтобы построить поты и определить победителей, а затем посчитать KO.
        # Важно: _parse_single_hand_initial_data только извлек базовые данные,
        # парсинг действий/сборов/потов делается здесь.

        final_table_data_for_db: List[Dict[str, Any]] = []

        # Находим индексы начала каждой раздачи в исходных линиях файла
        hand_start_indices = {}
        for idx, line in enumerate(lines):
            m_hand_start = RE_HAND_START.match(line)
            if m_hand_start:
                hand_id = m_hand_start.group('hand_id')
                # Находим соответствующую HandData по hand_id
                related_hand_data = next((h for h in self._final_table_hands if h.hand_id == hand_id), None)
                if related_hand_data:
                    hand_start_indices[hand_id] = idx


        for hand_data in self._final_table_hands:
             start_idx_in_lines = hand_start_indices.get(hand_data.hand_id)
             if start_idx_in_lines is None:
                  logger.warning(f"Не найдена начальная строка для раздачи {hand_data.hand_id} в файле {filename}.")
                  continue # Пропускаем эту раздачу финалки если не можем ее найти в исходных линиях

             try:
                 # Парсим действия, сборы и строим поты для этой раздачи
                 _, contrib, collects = self._parse_hand_actions_and_collects(lines, start_idx_in_lines)

                 if contrib: # Если были ставки/блайнды
                      hand_data.contrib = contrib
                      hand_data.collects = collects
                      hand_data.pots = self._build_pots(hand_data.contrib)
                      self._assign_winners(hand_data.pots, hand_data.collects)

                 # Определяем, кто выбыл в этой раздаче
                 # Ищем следующую раздачу финалки, чтобы сравнить стеки
                 next_hand_data = None
                 current_hand_idx_in_ft_list = self._final_table_hands.index(hand_data)
                 if current_hand_idx_in_ft_list + 1 < len(self._final_table_hands):
                      next_hand_data = self._final_table_hands[current_hand_idx_in_ft_list + 1]
                      # Если следующая раздача есть, используем стеки из нее
                      eliminated_players = [p for p in hand_data.seats if p not in next_hand_data.seats]
                 else:
                      # Если это последняя раздача финалки в файле, смотрим на тех, кто собрал деньги
                      # Те, кто не собрал и были за столом в начале раздачи - выбыли.
                      # Или более надежно: смотрим на место Hero из TS. Если Hero вылетел,
                      # смотрим кто был за столом в начале последней раздачи и кого нет в TS.
                      # **Упрощение**: В рамках HH парсера, мы можем только определить выбывших
                      # сравнивая с *началом следующей раздачи* в этом файле.
                      # Если следующей раздачи нет, мы не можем точно определить выбывших только по HH.
                      # Финальное место Hero из TS - это лучший индикатор.
                      # **Решение**: Для определения выбывших, сравним Hero.seats с Hero.collects
                      # в ПОСЛЕДНЕЙ раздаче. Это не идеально, но может быть индикатором.
                      # Лучше использовать флаг is_eliminated в HandData и заполнять его
                      # на уровне ApplicationService, мерджа данные с TS.
                      # **Пересмотр**: Парсер HH должен просто подсчитать KO в раздаче.
                      # Кто выбыл - это уже логика ApplicationService при объединении HH и TS.
                      # KO засчитывается, если Hero выиграл пот, к которому выбывший имел отношение.
                      # Давайте посчитаем KO только по инфе в текущей раздаче (кто выиграл пот, кто был покрыт).

                      # KO count for a hand logic remains the same based on pots and coverage
                      # The list of eliminated players is technically not needed directly for THIS KO logic
                      # but useful for context. Let's keep the _count_ko_in_hand logic as is.
                      eliminated_players = [] # Очищаем список выбывших для этой логики


                 # Подсчитываем KO Hero в этой раздаче
                 # Используем hand_data, которая теперь содержит pots, contrib, collects
                 ko_this_hand = self._count_ko_in_hand_from_data(hand_data)
                 hand_data.hero_ko_this_hand = ko_this_hand # Обновляем модель раздачи


                 # Подготавливаем данные раздачи для сохранения в БД
                 final_table_data_for_db.append({
                     'tournament_id': hand_data.tournament_id,
                     'hand_id': hand_data.hand_id,
                     'hand_number': hand_data.hand_number,
                     'table_size': hand_data.table_size,
                     'bb': hand_data.bb,
                     'hero_stack': hand_data.hero_stack,
                     'hero_ko_this_hand': hand_data.hero_ko_this_hand,
                     'is_early_final': hand_data.is_early_final,
                     # session_id будет добавлен в ApplicationService
                 })

             except Exception as e:
                  logger.error(f"Ошибка обработки данных финальной раздачи {hand_data.hand_id} в турнире {hand_data.tournament_id}: {e}")


        # --- Собираем итоговый результат для ApplicationService ---
        result = {
            'tournament_id': self._tournament_id,
            'start_time': self._start_time,
            'reached_final_table': first_ft_hand_data is not None,
            'final_table_initial_stack_chips': first_ft_hand_data.hero_stack if first_ft_hand_data else None,
            'final_table_initial_stack_bb': (first_ft_hand_data.hero_stack / first_ft_hand_data.bb) if first_ft_hand_data and first_ft_hand_data.bb > 0 else None,
            'final_table_hands_data': final_table_data_for_db, # Список данных по рукам финалки для сохранения
        }

        logger.debug(f"Парсинг HH завершен для {self._tournament_id}. Финалка: {result['reached_final_table']}, Рук на финалке: {len(self._final_table_hands)}")

        return result

    def _reset(self):
        """Сбрасывает состояние парсера для нового файла."""
        self._tournament_id = None
        self._start_time = None
        self._hands = []
        self._final_table_hands = []
        logger.debug("Состояние парсера HH сброшено.")


    def _parse_single_hand_initial_data(self, lines: List[str], idx: int, tournament_id: str, hand_number: int) -> Tuple[int, Optional[HandData]]:
        """
        Парсит одну раздачу до секции действий, извлекая базовую информацию, стеки, блайнды и размер стола.
        Возвращает индекс строки, с которой нужно продолжить парсинг действий/сборов.
        """
        hand_start_line = lines[idx]
        m_hand_start = RE_HAND_START.match(hand_start_line)
        if not m_hand_start:
            return idx + 1, None # Пропускаем, если это не начало раздачи

        hand_id = m_hand_start.group('hand_id')

        current_idx = idx + 1
        seats: Dict[str, int] = {}
        table_size: int = 0
        bb: float = 0.0
        hero_participated = False

        # Ищем информацию о столе, блайндах и стеках до *** HOLE CARDS ***
        while current_idx < len(lines) and not lines[current_idx].startswith('*** HOLE'):
            line = lines[current_idx]
            m_table_info = RE_TABLE_INFO.match(line)
            if m_table_info:
                 table_size = int(m_table_info.group('table_size'))

            m_blinds = RE_BLINDS_HEADER.search(line)
            if m_blinds:
                 bb = float(m_blinds.group(2).replace(',', '.')) # Заменяем запятую на точку

            m_seat = RE_SEAT.match(line)
            if m_seat:
                name, stack_str = m_seat.groups()
                player_name = NAME(name)
                seats[player_name] = CHIP(stack_str)
                if player_name == config.HERO_NAME:
                    hero_participated = True

            current_idx += 1

        # Если Hero не участвовал в этой раздаче, пропускаем ее полностью
        if not hero_participated:
            # logger.debug(f"Раздача #{hand_number} ({hand_id}) - Hero не участвует. Пропускаем.")
            return self._skip_to_next_hand(lines, idx), None


        # Если не удалось найти размер стола или BB в заголовке раздачи,
        # и Hero участвует, все равно создаем HandData, но с неполной инфой.
        # Это нужно, чтобы _eliminated мог сравнить стеки даже для не-финальных рук.
        # Однако, для подсчета KO и определения финалки эти поля критичны.
        # Давайте требовать наличия table_size и bb >= MIN_KO_BLIND_LEVEL_BB для рассмотрения как финалки.
        # Но HandData создадим в любом случае, если Hero участвует.

        hand_data = HandData(hand_id, hand_number, tournament_id, table_size, bb, seats)

        # Теперь парсим секции действий, сборов и строим поты
        # current_idx находится после "*** HOLE CARDS ***"
        current_idx, hand_data.contrib, hand_data.collects = self._parse_hand_actions_and_collects(lines, current_idx)

        if hand_data.contrib: # Строим банки только если были ставки/блайнды
            hand_data.pots = self._build_pots(hand_data.contrib)
            self._assign_winners(hand_data.pots, hand_data.collects)


        # logger.debug(f"Раздача #{hand_number} ({hand_id}) базовая информация спарсена.")

        return current_idx, hand_data


    def _parse_hand_actions_and_collects(self, lines: List[str], idx: int) -> Tuple[int, Dict[str, int], Dict[str, int]]:
        """
        Парсит секции *** HOLE CARDS ***, ACTIONS, *** SHOWDOWN ***, *** SUMMARY ***
        для извлечения вкладов в банк и сборов. Возвращает индекс строки ПОСЛЕ секции SUMMARY.
        """
        current_idx = idx
        contrib: Dict[str, int] = {}
        committed: Dict[str, int] = {} # Сколько вложено в текущем стрите
        collects: Dict[str, int] = {}

        # Пропускаем секции до действий (*** HOLE CARDS ***, *** FLOP ***, *** TURN ***, *** RIVER ***)
        while current_idx < len(lines) and not lines[current_idx].strip().startswith(('*** SHOWDOWN', '*** SUMMARY', '***')) :
             line = lines[current_idx].strip()
             # Парсим действия
             m_action = RE_ACTION.match(line)
             if m_action:
                 action_groups = m_action.groupdict()
                 pl = NAME(action_groups['player_name'])
                 act = action_groups['action']
                 amt_str = action_groups.get('amount')
                 amt = CHIP(amt_str)

                 if act in ('posts', 'bets', 'calls', 'all-in'):
                     contrib[pl] = contrib.get(pl, 0) + amt
                     committed[pl] = committed.get(pl, 0) + amt
                     # logger.debug(f"Action: {pl} {act} {amt}")
                 elif act == 'raises':
                     m_raise_to = RE_RAISE_TO.search(line)
                     if m_raise_to:
                         total_to = CHIP(m_raise_to.group(1))
                         prev_committed = committed.get(pl, 0)
                         diff = total_to - prev_committed
                         contrib[pl] = contrib.get(pl, 0) + diff
                         committed[pl] = total_to # Committed becomes the total amount of the raise
                     else:
                         logger.warning(f"Found 'raises' action without 'to' amount: {line}")

             # Парсим Uncalled bet (может быть до SHOWDOWN)
             m_unc = RE_UNCALLED.match(line)
             if m_unc:
                 amt_str, pl_name = m_unc.groups()
                 pl = NAME(pl_name)
                 val = CHIP(amt_str)
                 contrib[pl] = contrib.get(pl, 0) - val
                 committed[pl] = committed.get(pl, 0) - val
                 # logger.debug(f"Uncalled bet {val} returned to {pl}")

             current_idx += 1

        # Теперь парсим *** SHOWDOWN *** и *** SUMMARY *** для сборов
        # Ищем строку SUMMARY, чтобы начать оттуда сканировать сборы
        summary_idx = -1
        for j in range(current_idx, len(lines)):
            if RE_SUMMARY.match(lines[j]):
                summary_idx = j
                break

        if summary_idx != -1:
            collect_search_idx = summary_idx + 1
            # Читаем строки после SUMMARY пока не пустая строка или начало новой раздачи
            while collect_search_idx < len(lines) and lines[collect_search_idx].strip() and not RE_HAND_START.match(lines[collect_search_idx]):
                 line = lines[collect_search_idx]
                 m_collected = RE_COLLECTED.match(line)
                 if m_collected:
                     pl, amt_str = m_collected.groups()
                     collects[NAME(pl)] = collects.get(NAME(pl), 0) + CHIP(amt_str)
                     # logger.debug(f"Collected: {NAME(pl)} collected {CHIP(amt_str)}")
                 collect_search_idx += 1
            current_idx = collect_search_idx # Обновляем current_idx до конца секции SUMMARY


        # Пропускаем пустые строки между раздачами
        while current_idx < len(lines) and not lines[current_idx].strip() and not RE_HAND_START.match(lines[current_idx]):
             current_idx += 1


        return current_idx, contrib, collects


    def _build_pots(self, contrib: Dict[str, int]) -> List[Pot]:
        """Строит структуру банков (главный и сайд-поты) из вкладов игроков."""
        pots = []
        if not contrib:
            return pots # Нет вкладов, нет банков

        # Получаем уникальные уровни вкладов, сортируем по возрастанию
        levels = sorted(set(v for v in contrib.values() if v > 0))

        prev_level = 0
        for current_level in levels:
            # Игроки, которые вложили >= текущего уровня, участвуют в текущем "слое" банка
            eligible_players = {p for p, amount in contrib.items() if amount >= current_level}
            # Размер текущего "слоя" банка
            layer_size = current_level - prev_level
            # Общий размер банка на этом уровне (слой * количество участвующих игроков)
            pot_size_at_level = layer_size * len(eligible_players)

            if pot_size_at_level > 0:
                 # Создаем Pot для этого слоя
                 pots.append(Pot(pot_size_at_level, eligible_players))

            prev_level = current_level

        return pots

    def _assign_winners(self, pots: List[Pot], collects: Dict[str, int]):
        """Назначает победителей банкам на основе информации о сборах."""
        # Для определения победителей KO достаточно знать, кто собрал деньги из пота.
        # Упрощенно: если игрок собрал хоть что-то и он eligible для этого пота, считаем его победителем этого пота.
        for pot in pots:
            for player in pot.eligible:
                if collects.get(player, 0) > 0: # Проверяем общие сборы игрока
                    pot.winners.add(player)


    def _count_ko_in_hand_from_data(self, hand: HandData) -> int:
        """
        Подсчитывает количество нокаутов Hero в данной раздаче, используя данные HandData.
        Hero получает KO за выбитого игрока, если Hero выиграл ПОТ,
        к которому выбитый игрок имел отношение, И Hero покрывал стек выбывшего.
        Эта функция вызывается ПОСЛЕ того, как Pot и winners определены для раздачи.
        """
        if config.HERO_NAME not in hand.seats:
            return 0 # Hero не участвовал в раздаче

        hero_stack_at_start = hand.hero_stack # Стек Hero в начале раздачи

        ko_count = 0
        # Чтобы точно определить выбывших в этой раздаче, нам нужен список игроков
        # в *начале следующей* раздачи. Парсер HH сам по себе в момент парсинга
        # одной раздачи не знает состояние следующей.
        # **Решение:** Логика определения выбывших должна быть в ApplicationService,
        # который имеет доступ ко всем спарсенным HandData для турнира.
        # Парсер HH просто извлекает потенциальных кандидатов на KO:
        # игроки, которые были в начале этой раздачи, имеют отношение к поту,
        # и чей стек был покрыт Hero.
        # ApplicationService затем подтвердит, выбыл ли этот игрок, сверившись с TS.

        # **Пересмотр логики KO в парсере HH:**
        # Парсер HH должен просто определить, кто потенциально был выбит Hero В ЭТОЙ РАЗДАЧЕ
        # на основе того, кто проиграл алл-ин Hero (Hero покрывал и выиграл пот).
        # Наличие строки "Player eliminated" в HH было бы идеальным, но не всегда есть.
        # Самый надежный индикатор в HH: игрок пошел олл-ин, Hero покрывал, Hero выиграл пот,
        # и у игрока 0 фишек в конце раздачи (нужен доступ к стекам в конце раздачи,
        # чего в HandData пока нет).

        # **Простое решение для парсера HH:** Игрок P потенциально выбит Hero в раздаче H, если:
        # 1. P пошел олл-ин в раздаче H.
        # 2. Hero покрывал стек P в начале раздачи H (Hero.stack >= P.stack).
        # 3. Hero выиграл ПОТ, к которому P имел отношение.
        # 4. (Опционально, но надежнее) Стек P в начале следующей раздачи равен 0.

        # Давайте модифицируем HandData для хранения стеков в конце раздачи,
        # ИЛИ просто определять выбывших как тех, кто был в начале раздачи, но не собрал деньги.
        # Последнее ближе к текущей структуре HandData.
        # Выбывшие в этой раздаче: игроки, которые были в `hand.seats` но НЕ в `hand.collects`.

        eliminated_players_this_hand = [p for p in hand.seats if p not in hand.collects]

        for knocked_out_player in eliminated_players_this_hand:
             if knocked_out_player == config.HERO_NAME:
                 continue

             # Находим пот(ы), к которым имел отношение выбывший игрок
             relevant_pots = [
                 pot for pot in hand.pots
                 if knocked_out_player in pot.eligible
             ]

             # Проверяем условие покрытия стека
             knocked_out_stack = hand.seats.get(knocked_out_player, 0)
             covered = hero_stack_at_start is not None and hero_stack_at_start >= knocked_out_stack # Проверяем, что стек Hero не None

             if covered:
                 # Если Hero покрывал стек, проверяем, выиграл ли Hero какой-либо из релевантных потов
                 hero_won_relevant_pot = any(
                     config.HERO_NAME in pot.winners for pot in relevant_pots
                 )

                 if hero_won_relevant_pot:
                     ko_count += 1
                     # logger.debug(f"Турнир {hand.tournament_id}, Раздача {hand.hand_number}: Потенциальный KO Hero за {knocked_out_player}. Покрывал: {covered}, Hero выиграл пот: {hero_won_relevant_pot}.")

        return ko_count

    def _skip_to_next_hand(self, lines: List[str], idx: int) -> int:
        """Пропускает строки текущей раздачи до начала следующей или конца файла."""
        current_idx = idx + 1
        while current_idx < len(lines):
            if RE_HAND_START.match(lines[current_idx]):
                return current_idx # Нашли начало следующей раздачи
            current_idx += 1
        return current_idx # Достигли конца файла