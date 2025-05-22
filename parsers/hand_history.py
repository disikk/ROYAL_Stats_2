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
RE_ACTION = re.compile(
    r'^(?P<player_name>[^:]+): (?P<action>posts|bets|calls|raises|all-in|checks|folds)\b'
    r'(?:.*?)(?P<amount>[\d,]+)?'
)
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
    __slots__ = (
        'hand_id', 'hand_number', 'tournament_id', 'table_size',
        'bb', 'seats', 'contrib', 'collects', 'pots',
        'final_stacks', 'all_in_players',
        'hero_stack', 'hero_ko_this_hand',
        'is_early_final', 'timestamp',
        'players', 'eliminated_players'
    )

    def __init__(self, hand_id: str, hand_number: int, tournament_id: str, table_size: int, bb: float, seats: Dict[str, int], timestamp: str = None):
        self.hand_id = hand_id
        self.hand_number = hand_number
        self.tournament_id = tournament_id
        self.table_size = table_size
        self.bb = bb
        self.seats = seats
        self.contrib: Dict[str, int] = {}
        self.collects: Dict[str, int] = {}
        self.pots: List[Pot] = []
        self.final_stacks: Dict[str, int] = {}
        self.all_in_players: Set[str] = set()
        self.hero_stack = seats.get(config.HERO_NAME) # Стек Hero в начале раздачи
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
        logger.debug("Состояние парсера HH сброшено.")

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
        hero_participated = False
        
        # Ищем информацию о столе, блайндах и стеках
        idx = 0
        while idx < len(lines) and not lines[idx].startswith('*** HOLE'):
            line = lines[idx]
            m_table_info = RE_TABLE_INFO.match(line)
            if m_table_info:
                table_size = int(m_table_info.group('table_size'))
                
            m_blinds = RE_BLINDS_HEADER.search(line)
            if m_blinds:
                bb = float(m_blinds.group(2).replace(',', '.'))
                
            m_seat = RE_SEAT.match(line)
            if m_seat:
                name, stack_str = m_seat.groups()
                player_name = NAME(name)
                seats[player_name] = CHIP(stack_str)
                if player_name == config.HERO_NAME:
                    hero_participated = True
                    
            idx += 1
            
        # Если Hero не участвовал, пропускаем раздачу
        if not hero_participated:
            return None
            
        # Создаем HandData
        hand_data = HandData(hand_id, hand_number, tournament_id, table_size, bb, seats, timestamp)
        
        # --- ante / SB / BB до HOLE CARDS ---
        preflop_contrib: Dict[str, int] = {}
        for pre_line in lines[:idx]:
            m_post = RE_ACTION.match(pre_line.strip())
            if m_post and m_post.group('action') == 'posts':
                pl = NAME(m_post.group('player_name'))
                preflop_contrib[pl] = preflop_contrib.get(pl, 0) + CHIP(m_post.group('amount'))

        contrib_act, collects = self._parse_actions_and_collects(lines[idx:])

        # объединяем
        contrib = contrib_act
        for pl, val in preflop_contrib.items():
            contrib[pl] = contrib.get(pl, 0) + val

        # финальные стеки и all-in статусы
        final_stacks = {pl: seats[pl] - contrib.get(pl, 0) + collects.get(pl, 0) for pl in seats}
        all_in_players = {pl for pl in seats if contrib.get(pl, 0) >= seats[pl]}

        hand_data.contrib = contrib
        hand_data.collects = collects
        hand_data.final_stacks = final_stacks
        hand_data.all_in_players = all_in_players
        
        if hand_data.contrib:  # Строим банки только если были вклады
            hand_data.pots = self._build_pots(hand_data.contrib)
            self._assign_winners(hand_data.pots, hand_data.collects)
            
        return hand_data
        
    def _parse_actions_and_collects(self, lines: List[str]) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Парсит действия и сборы из части раздачи, начиная с *** HOLE CARDS ***.
        """
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
                amt_str, pl_name = m_unc.groups()
                pl = NAME(pl_name)
                val = CHIP(amt_str)
                contrib[pl] = contrib.get(pl, 0) - val
                committed[pl] = committed.get(pl, 0) - val
                
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
                m_collected = RE_COLLECTED.match(line)
                if m_collected:
                    pl, amt_str = m_collected.groups()
                    collects[NAME(pl)] = collects.get(NAME(pl), 0) + CHIP(amt_str)
                collect_idx += 1
                
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

        # --- последняя раздача турнира ---
        if self._hands:
            last = self._hands[-1]
            last.eliminated_players = {p for p, stk in last.final_stacks.items() if stk == 0}

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
        remaining = collects.copy()
        for pot in pots:  # main → side1 → side2 …
            elig = {p for p in pot.eligible if remaining.get(p, 0) > 0}
            if not elig:
                continue
            pot.winners.update(elig)
            share = pot.size // len(elig)
            for p in elig:
                remaining[p] = max(0, remaining[p] - share)


    def _count_ko_in_hand_from_data(self, hand: HandData) -> int:
        """
        Подсчитывает количество нокаутов Hero в данной раздаче, используя данные HandData.
        Игрок считается выбитым Hero если:
        1. Он отсутствует в следующей раздаче (определено в _identify_eliminated_players)
        2. Hero покрывал его стек
        3. Hero выиграл пот, к которому игрок имел отношение
        """
        if config.HERO_NAME not in hand.seats:
            return 0 # Hero не участвовал в раздаче

        hero_stack_at_start = hand.hero_stack # Стек Hero в начале раздачи
        ko_count = 0
        
        # Используем информацию о выбывших игроках, добавленную методом _identify_eliminated_players
        for knocked_out_player in hand.eliminated_players:
            if knocked_out_player == config.HERO_NAME:
                continue

            # Находим пот(ы), к которым имел отношение выбывший игрок
            relevant_pots = [
                pot for pot in hand.pots
                if knocked_out_player in pot.eligible
            ]

            knocked_out_stack = hand.seats.get(knocked_out_player, 0)
            went_all_in = knocked_out_player in hand.all_in_players
            covered = hero_stack_at_start is not None and hero_stack_at_start >= knocked_out_stack

            if went_all_in and covered and relevant_pots:
                # Последний пот, куда игрок вложил фишки
                last_pot = sorted(relevant_pots, key=lambda p: len(p.eligible))[0]
                if config.HERO_NAME in last_pot.winners:
                    ko_count += 1
                    logger.debug(
                        f"Турнир {hand.tournament_id}, Раздача {hand.hand_number}: KO Hero за {knocked_out_player}. Покрывал: {covered}, Pot size: {last_pot.size}."
                    )

        return ko_count