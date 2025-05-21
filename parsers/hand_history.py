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
logger.setLevel(logging.DEBUG) # Force DEBUG level for this task

# --- Регулярки для парсинга HH ---
RE_HAND_START = re.compile(r'^Poker Hand #(?P<hand_id>[A-Za-z0-9_]+): Tournament #(?P<tournament_id>\d+),') # Адаптировано для GG формата, added _ to hand_id
RE_TABLE_INFO = re.compile(r"^Table '\d+' (?P<table_size>\d+)-max Seat #\d+ is the button")
RE_BLINDS_HEADER = re.compile(r"Level\d+\(([\d,]+)/([\d,]+)\)") # Для поиска блайндов в заголовке раздачи
RE_SEAT = re.compile(r'^Seat \d+: (?P<player_name>.+?) \((?P<stack>[-\d,]+) in chips\)') # Changed [^()]+? to .+?
RE_ACTION = re.compile(r'^(?P<player_name>[^:]+): (?P<action>posts|bets|calls|raises|all-in|checks|folds)\b(?:[^0-9,]*?(?P<amount>[\d,]+))?') # Improved amount parsing
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
    __slots__ = ('hand_id', 'hand_number', 'tournament_id', 'table_size', 'bb', 'seats', 'contrib', 'collects', 'pots', 'hero_stack', 'hero_actual_name_in_hand', 'hero_ko_this_hand', 'is_early_final', 'timestamp', 'players', 'eliminated_players')

    def __init__(self, hand_id: str, hand_number: int, tournament_id: str, table_size: int, bb: float, seats: Dict[str, int], timestamp: str = None, hero_actual_name: Optional[str] = None):
        self.hand_id = hand_id
        self.hand_number = hand_number
        self.tournament_id = tournament_id
        self.table_size = table_size
        self.bb = bb
        self.seats = seats
        self.contrib: Dict[str, int] = {}
        self.collects: Dict[str, int] = {}
        self.pots: List[Pot] = []
        self.hero_actual_name_in_hand = hero_actual_name
        self.hero_stack = seats.get(hero_actual_name) if hero_actual_name else None # Стек Hero в начале раздачи
        self.hero_ko_this_hand = 0 # KO Hero в этой раздаче
        self.is_early_final = False # Флаг ранней стадии финалки
        self.timestamp = timestamp  # Время начала раздачи
        self.players = list(seats.keys())  # Список игроков за столом в этой раздаче
        self.eliminated_players = set()  # Игроки, выбывшие в этой раздаче

class HandHistoryParser(BaseParser):
    def __init__(self, hero_name: str = config.HERO_NAME):
        super().__init__(hero_name)
        self._tournament_id: Optional[str] = None
        self._start_time: Optional[str] = None
        self._hands: List[HandData] = [] # Все раздачи из файла
        self._final_table_hands: List[HandData] = [] # Только раздачи финального стола (9-max, >=50/100 BB)
        # _hero_actual_name_in_current_hand is not needed as a class member if passed around or stored in HandData

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

        # Сначала определим все начала раздач в файле
        hand_chunks = self._split_file_into_hand_chunks(lines)
        
        # Если не нашли ни одной руки, вернем пустой результат
        if not hand_chunks:
            logger.warning(f"Не найдено раздач в файле: {filename}")
            return {'tournament_id': None}
            
        # Определяем Tournament ID из первой найденной раздачи
        first_chunk = hand_chunks[0]
        for line in first_chunk[:10]:  # Ищем в первых строках первой раздачи
            m_tid = RE_HAND_START.search(line)
            if m_tid:
                self._tournament_id = m_tid.group('tournament_id')
                break
                
        # Если не нашли Tournament ID, попробуем извлечь из имени файла
        if not self._tournament_id:
            m_tid_fn = re.search(r"Tournament #(\d+)", filename)
            if m_tid_fn:
                self._tournament_id = m_tid_fn.group(1)
                logger.debug(f"Турнир ID из имени файла: {self._tournament_id}")
                
        if not self._tournament_id:
            logger.warning(f"Не удалось извлечь Tournament ID из файла HH: {filename}. Файл пропущен.")
            return {'tournament_id': None} # Пропускаем файл без ID
            
        logger.debug(f"Начат парсинг HH для турнира {self._tournament_id}, файл: {filename}")
        
        # Обрабатываем раздачи в хронологическом порядке (от первой к последней)
        # Поскольку в файле они идут в ОБРАТНОМ порядке, мы обрабатываем chunks в обратном порядке
        hand_number_counter = 0
        first_ft_hand_data: Optional[HandData] = None
        
        # Получаем хронологически первую раздачу для определения start_time турнира
        first_chunk = hand_chunks[-1]  # Последний chunk в массиве - это первая раздача хронологически
        for line in first_chunk[:20]:
            m_dt = RE_DATE.search(line)
            if m_dt:
                self._start_time = m_dt.group(1)
                break
        
        # Теперь обрабатываем раздачи в хронологическом порядке (от первой к последней)
        for hand_chunk in reversed(hand_chunks):  # Обрабатываем от последней в файле (первой хронологически)
            hand_number_counter += 1
            try:
                hand_data = self._parse_hand_chunk(hand_chunk, self._tournament_id, hand_number_counter)
                
                if hand_data:
                    self._hands.append(hand_data)  # Сохраняем все раздачи
                    
                    # Проверяем условия финального стола
                    if hand_data.table_size == config.FINAL_TABLE_SIZE and hand_data.bb >= config.MIN_KO_BLIND_LEVEL_BB:
                        # Это раздача финального стола
                        self._final_table_hands.append(hand_data)
                        
                        # Если это первая раздача финального стола, сохраняем ее данные
                        if first_ft_hand_data is None:
                            first_ft_hand_data = hand_data
                            logger.debug(f"Найдена первая раздача финального стола ({hand_data.table_size}-max, BB={hand_data.bb}) в турнире {self._tournament_id}. Раздача #{hand_data.hand_number}. Стек Hero: {hand_data.hero_stack}")
                        
                        # Определяем, является ли раздача "ранней" стадией финалки (9-6 игроков)
                        if 6 <= hand_data.table_size <= config.FINAL_TABLE_SIZE:
                            hand_data.is_early_final = True
                            
            except Exception as e:
                logger.error(f"Ошибка парсинга раздачи в файле {filename}: {e}")
                continue  # Переходим к следующей раздаче
        
        # Определяем выбывших игроков путем сравнения списков игроков в соседних раздачах
        self._identify_eliminated_players()
        
        # Подсчитываем KO Hero для всех раздач финального стола
        final_table_data_for_db: List[Dict[str, Any]] = []
        
        for hand_data in self._final_table_hands:
            try:
                # Теперь _count_ko_in_hand_from_data будет использовать информацию о выбывших игроках
                ko_this_hand = self._count_ko_in_hand_from_data(hand_data)
                hand_data.hero_ko_this_hand = ko_this_hand
                
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
        
        # Собираем итоговый результат для ApplicationService
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
        # No need to reset _hero_actual_name_in_current_hand if it's not a member
        logger.debug("Состояние парсера HH сброшено.")

    def _find_hero_actual_name(self, parsed_player_names: List[str]) -> Optional[str]:
        """
        Находит актуальное имя Hero из списка спарсенных имен,
        если config.HERO_NAME является его частью.
        Предпочитает точное совпадение, затем частичное.
        """
        if self.hero_name in parsed_player_names: # Точное совпадение
            return self.hero_name
        for name in parsed_player_names:
            if self.hero_name in name: # Частичное совпадение (вхождение строки)
                logger.debug(f"Актуальное имя Hero найдено: '{name}' (из конфига: '{self.hero_name}')")
                return name
        logger.debug(f"Hero '{self.hero_name}' не найден среди игроков: {parsed_player_names}")
        return None

    def _split_file_into_hand_chunks(self, lines: List[str]) -> List[List[str]]:
        """
        Разбивает файл на chunks, каждый из которых содержит одну раздачу.
        Возвращает chunks в том порядке, в котором они находятся в файле
        (последние хронологические раздачи в начале списка).
        """
        chunks = []
        current_chunk = []
        
        for line in lines:
            if RE_HAND_START.match(line) and current_chunk:
                # Нашли начало новой раздачи, сохраняем предыдущую
                chunks.append(current_chunk)
                current_chunk = [line]
            else:
                current_chunk.append(line)
                
        # Не забываем добавить последний chunk
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
            
    def _parse_hand_chunk(self, lines: List[str], tournament_id: str, hand_number: int) -> Optional[HandData]:
        """
        Парсит chunk строк, относящийся к одной раздаче.
        """
        if not lines:
            return None
            
        # Проверяем, что первая строка действительно начало раздачи
        m_hand_start = RE_HAND_START.match(lines[0])
        if not m_hand_start:
            return None
            
        hand_id = m_hand_start.group('hand_id')
        timestamp = None
        
        # Ищем timestamp раздачи
        for line in lines[:5]:
            m_dt = RE_DATE.search(line)
            if m_dt:
                timestamp = m_dt.group(1)
                break
                
        seats: Dict[str, int] = {}
        table_size: int = 0
        bb: float = 0.0
        
        parsed_player_names_in_seats = []

        # Ищем информацию о столе, блайндах и стеках
        idx = 0
        while idx < len(lines) and not lines[idx].startswith('*** HOLE'):
            line = lines[idx]
            m_table_info = RE_TABLE_INFO.match(line)
            if m_table_info:
                table_size = int(m_table_info.group('table_size'))
                
            m_blinds = RE_BLINDS_HEADER.search(line)
            if m_blinds:
                # Группа 1 это SB, группа 2 это BB
                bb_str = m_blinds.group(2).replace(',', '') 
                bb = float(bb_str)
                
            m_seat = RE_SEAT.match(line)
            if m_seat:
                name_raw, stack_str = m_seat.groups()
                player_name = NAME(name_raw) # NAME strips whitespace
                seats[player_name] = CHIP(stack_str)
                parsed_player_names_in_seats.append(player_name)
                            
            idx += 1
        
        # Определяем актуальное имя Hero и его участие
        hero_actual_name = self._find_hero_actual_name(parsed_player_names_in_seats)
        
        if not hero_actual_name: # Если Hero не найден среди имен за столом
            # logger.debug(f"Hero ({self.hero_name}) не участвовал в раздаче {hand_id}")
            return None # Пропускаем раздачу, если Hero не участвовал
            
        # Создаем HandData, передавая актуальное имя Hero
        hand_data = HandData(hand_id, hand_number, tournament_id, table_size, bb, seats, timestamp, hero_actual_name=hero_actual_name)
        
        # Парсим действия и сборы
        # _parse_actions_and_collects использует NAME() для ключей, что должно совпадать с ключами в seats
        # Pass hand_id for logging
        contrib, collects = self._parse_actions_and_collects(lines[idx:], hero_actual_name, hand_id)
        hand_data.contrib = contrib
        hand_data.collects = collects
        
        if hand_data.contrib:  # Строим банки только если были вклады
            # Pass hero_actual_name and hand_id for logging
            hand_data.pots = self._build_pots(hand_data.contrib, hero_actual_name, hand_id)
            # Передаем hero_actual_name в _assign_winners для возможного использования, хотя текущая логика общая
            # Pass hand_id for logging
            self._assign_winners(hand_data.pots, hand_data.collects, hero_actual_name, hand_id)
            
        return hand_data
        
    def _parse_actions_and_collects(self, lines: List[str], hero_actual_name: Optional[str], hand_id_for_log: str) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Парсит действия и сборы из части раздачи, начиная с *** HOLE CARDS ***.
        hero_actual_name передается для информации, текущая логика парсинга общая.
        """
        logger.debug(f"[{hand_id_for_log}] _parse_actions_and_collects: hero_actual_name='{hero_actual_name}'")
        contrib: Dict[str, int] = {}
        committed: Dict[str, int] = {}  # Сколько вложено в текущем стрите
        collects: Dict[str, int] = {}
        
        idx = 0
        # Парсим действия до SHOWDOWN или SUMMARY
        while idx < len(lines) and not lines[idx].strip().startswith(('*** SHOWDOWN', '*** SUMMARY')):
            line = lines[idx].strip()
            
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
                elif act == 'raises':
                    m_raise_to = RE_RAISE_TO.search(line)
                    if m_raise_to:
                        total_to = CHIP(m_raise_to.group(1))
                        prev_committed = committed.get(pl, 0)
                        diff = total_to - prev_committed
                        contrib[pl] = contrib.get(pl, 0) + diff
                        committed[pl] = total_to
                    else:
                        logger.warning(f"Found 'raises' action without 'to' amount: {line}")
                        
            # Парсим Uncalled bet
            m_unc = RE_UNCALLED.match(line)
            if m_unc:
                amt_str, pl_name_raw = m_unc.groups()
                pl = NAME(pl_name_raw) # Используем NAME для консистентности
                val = CHIP(amt_str)
                contrib[pl] = contrib.get(pl, 0) - val
                # Обновляем committed, если игрок есть в нем
                if pl in committed:
                    committed[pl] = max(0, committed.get(pl, 0) - val)
            
            # Сброс committed после каждого раунда торговли (улицы)
            # Это важно для корректного расчета raises "to X" vs "by Y"
            if line.strip() in ('*** FLOP ***', '*** TURN ***', '*** RIVER ***'):
                committed = {} # Сбрасываем committed для новой улицы

            idx += 1
            
        # Ищем секцию SUMMARY
        summary_idx = -1
        for j in range(idx, len(lines)):
            if RE_SUMMARY.match(lines[j]):
                summary_idx = j
                break
                
        # Парсим сборы после SUMMARY
        if summary_idx != -1:
            collect_idx = summary_idx + 1
            while collect_idx < len(lines):
                line = lines[collect_idx]
                m_collected = RE_COLLECTED.match(line.strip()) # Ensure line is stripped for regex matching
                if m_collected:
                    pl_raw, amt_str = m_collected.groups()
                    player_name_key = NAME(pl_raw)
                    amount_collected = CHIP(amt_str)
                    collects[player_name_key] = collects.get(player_name_key, 0) + amount_collected
                    logger.debug(f"[{hand_id_for_log}] _parse_actions_and_collects: Populating collects: player='{player_name_key}', amount='{amount_collected}'")
                    if hero_actual_name and hero_actual_name == player_name_key: # Check exact match after NAME()
                        logger.debug(f"[{hand_id_for_log}] _parse_actions_and_collects: HERO ('{hero_actual_name}') collected '{amount_collected}' (key: '{player_name_key}')")
                collect_idx += 1
        logger.debug(f"[{hand_id_for_log}] _parse_actions_and_collects: Final contrib dict: {contrib}")
        logger.debug(f"[{hand_id_for_log}] _parse_actions_and_collects: Final collects dict: {collects}")
        return contrib, collects

    def _identify_eliminated_players(self):
        """
        Определяет выбывших игроков путем сравнения списков игроков между 
        последовательными раздачами. Игрок считается выбывшим в раздаче, если
        он присутствует в ней, но отсутствует в следующей раздаче.
        """
        # Раздачи уже отсортированы по хронологии (в self._hands)
        for i in range(len(self._hands) - 1):
            current_hand = self._hands[i]
            next_hand = self._hands[i + 1]
            
            # Игроки, которые были в текущей раздаче, но отсутствуют в следующей
            eliminated_in_current_hand = set(current_hand.players) - set(next_hand.players)
            
            # Добавляем атрибут eliminated_players к текущей раздаче
            current_hand.eliminated_players = eliminated_in_current_hand
            if current_hand.eliminated_players:
                 logger.debug(f"[{current_hand.hand_id}] _identify_eliminated_players: Players eliminated in this hand: {current_hand.eliminated_players}")


    def _build_pots(self, contrib: Dict[str, int], hero_actual_name: Optional[str], hand_id_for_log: str) -> List[Pot]:
        """Строит структуру банков (главный и сайд-поты) из вкладов игроков."""
        logger.warning(f"[{hand_id_for_log}] _build_pots: Starting for hero='{hero_actual_name}'. Contributions: {contrib}") # Changed to WARNING
        pots = []
        if not contrib:
            logger.warning(f"[{hand_id_for_log}] _build_pots: No contributions, returning empty pots.") # Changed to WARNING
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
                current_pot = Pot(pot_size_at_level, eligible_players)
                logger.warning(f"[{hand_id_for_log}] _build_pots: Created pot: size={current_pot.size}, eligible={eligible_players}") # Changed to WARNING
                if hero_actual_name and hero_actual_name in current_pot.eligible:
                    logger.warning(f"[{hand_id_for_log}] _build_pots: HERO ('{hero_actual_name}') is eligible for this pot.") # Changed to WARNING
                pots.append(current_pot)
            prev_level = current_level
        
        logger.warning(f"[{hand_id_for_log}] _build_pots: Final pots list (size, eligible, winners): {[(p.size, p.eligible, p.winners) for p in pots]}") # Changed to WARNING
        return pots

    def _assign_winners(self, pots: List[Pot], collects: Dict[str, int], hero_actual_name: Optional[str], hand_id_for_log: str):
        """Назначает победителей банкам на основе информации о сборах."""
        logger.warning(f"[{hand_id_for_log}] _assign_winners: Starting for hero='{hero_actual_name}'. Collects dict: {collects}") # Changed to WARNING
        if hero_actual_name: # Log what hero collected based on collects dict
            hero_collected_amount = collects.get(hero_actual_name, 0)
            logger.warning(f"[{hand_id_for_log}] _assign_winners: Hero ('{hero_actual_name}') according to collects dict, collected amount: {hero_collected_amount}") # Changed to WARNING

        for i, pot in enumerate(pots):
            logger.warning(f"[{hand_id_for_log}] _assign_winners: Processing pot #{i+1} (size={pot.size}, eligible={pot.eligible})") # Changed to WARNING
            # pot.winners should be empty before this loop if Pot class initializes it so.
            # Let's log initial state of pot.winners for clarity.
            logger.warning(f"[{hand_id_for_log}] _assign_winners: Pot #{i+1} initial winners: {pot.winners}") # Changed to WARNING
            for player_name_in_pot_eligible_set in pot.eligible: 
                if collects.get(player_name_in_pot_eligible_set, 0) > 0:
                    pot.winners.add(player_name_in_pot_eligible_set)
                    logger.warning(f"[{hand_id_for_log}] _assign_winners: Added '{player_name_in_pot_eligible_set}' to Pot #{i+1} winners (collected {collects.get(player_name_in_pot_eligible_set)})") # Changed to WARNING
                    if player_name_in_pot_eligible_set == hero_actual_name:
                         logger.warning(f"[{hand_id_for_log}] _assign_winners: HERO ('{hero_actual_name}') added to pot #{i+1} winners.") # Changed to WARNING
            
            logger.warning(f"[{hand_id_for_log}] _assign_winners: Pot #{i+1} final winners: {pot.winners}") # Changed to WARNING
            if hero_actual_name and hero_actual_name in pot.eligible:
                 logger.warning(f"[{hand_id_for_log}] _assign_winners: For pot Hero ('{hero_actual_name}') is eligible for, final winners are: {pot.winners}. Hero is in winners? {hero_actual_name in pot.winners}") # Changed to WARNING


    def _count_ko_in_hand_from_data(self, hand: HandData) -> int:
        """
        Подсчитывает количество нокаутов Hero в данной раздаче, используя данные HandData.
        Игрок считается выбитым Hero если:
        1. Он отсутствует в следующей раздаче (определено в _identify_eliminated_players)
        2. Hero покрывал его стек (hand.hero_stack теперь корректно установлен)
        3. Hero выиграл пот, к которому игрок имел отношение (используя hand.hero_actual_name_in_hand)
        """
        actual_hero_name = hand.hero_actual_name_in_hand
        log_hand_ref = hand.hand_id if hand.hand_id else f"Num{hand.hand_number}"
        logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Starting for hero='{actual_hero_name}'") # Changed to WARNING
        
        if not actual_hero_name or actual_hero_name not in hand.seats:
            logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero not in seats or no actual_hero_name. Hero: '{actual_hero_name}', Seats: {list(hand.seats.keys())}. Returning 0 KOs.") # Changed to WARNING
            return 0

        hero_stack_at_start = hand.hero_stack
        logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero stack at start: {hero_stack_at_start}") # Changed to WARNING
        ko_count = 0
        
        if hero_stack_at_start is None: 
            logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero stack is None, though hero is present. Returning 0 KOs.")
            return 0
        
        if not hand.eliminated_players:
             logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: No players eliminated in this hand. Returning 0 KOs.") # Changed to WARNING
             return 0
        
        logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Eliminated players in this hand: {hand.eliminated_players}") # Changed to WARNING

        for knocked_out_player in hand.eliminated_players:
            logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Processing knocked_out_player='{knocked_out_player}'") # Changed to WARNING
            if knocked_out_player == actual_hero_name:
                logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Skipping self-elimination.") # Changed to WARNING
                continue

            relevant_pots = [
                pot for pot in hand.pots
                if knocked_out_player in pot.eligible
            ]
            if not relevant_pots:
                logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: No relevant pots for knocked_out_player='{knocked_out_player}'. This might be unusual if player contributed to pot.") 
                continue
            else:
                logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Found {len(relevant_pots)} relevant pot(s) for '{knocked_out_player}'.") # Changed to WARNING


            knocked_out_stack = hand.seats.get(knocked_out_player, 0) 
            logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Knocked_out_player='{knocked_out_player}' stack: {knocked_out_stack}") # Changed to WARNING
            
            covered = hero_stack_at_start >= knocked_out_stack
            logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero ({hero_stack_at_start}) covered knocked_out_player ({knocked_out_stack})? {covered}") # Changed to WARNING

            if covered:
                hero_won_relevant_pot = False
                for i, pot_instance in enumerate(relevant_pots): 
                    logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Checking relevant pot #{i+1} for KO of '{knocked_out_player}': Pot eligible={pot_instance.eligible}, Pot winners={pot_instance.winners}") # Changed to WARNING
                    if actual_hero_name in pot_instance.winners:
                        hero_won_relevant_pot = True
                        logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero ('{actual_hero_name}') IS in winners for this pot #{i+1}.") # Changed to WARNING
                        break 
                    else:
                        logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero ('{actual_hero_name}') IS NOT in winners for this pot #{i+1}.") # Changed to WARNING
                
                logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: hero_won_relevant_pot for '{knocked_out_player}'? {hero_won_relevant_pot}") # Changed to WARNING

                if hero_won_relevant_pot:
                    ko_count += 1
                    logger.info(f"[{log_hand_ref}] KO Event: Hero ({actual_hero_name}) KO'd ({knocked_out_player}). Covered: {covered}. Hero won pot. KO count: {ko_count}")
            else:
                 logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Hero did not cover '{knocked_out_player}'. No KO.") # Changed to WARNING
        
        logger.warning(f"[{log_hand_ref}] _count_ko_in_hand_from_data: Final ko_this_hand for hero='{actual_hero_name}': {ko_count}") # Changed to WARNING
        return ko_count