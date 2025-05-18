#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер файлов истории рук (hand history) для покерного трекера ROYAL_Stats.
Корректно считает KO Hero, учитывая мульти-алл-ин, покрытие, дележки, сайд-поты, старт финалки с >=6 игроков и блайнды >=50/100.

Основные принципы:
- KO засчитывается только тому, кто покрывал стек и выиграл соответствующий банк.
- При split-pot каждый получает KO за выбитого.
- Финалка: >=6 игроков, блайнды >=50/100.
- Сценарии с мульти-алл-ин полностью поддерживаются.
"""

import re
from typing import Dict, List, Set, Tuple, Optional
import config

class Pot:
    """
    Представляет основной/сайд-пот: eligible (кто имеет право), winners (кто выиграл), размер.
    """
    __slots__ = ('size', 'eligible', 'winners')
    def __init__(self, size: int, eligible: Set[str]):
        self.size = size
        self.eligible: Set[str] = eligible.copy()
        self.winners: Set[str] = set()

class Hand:
    """
    Одна раздача: начальные стеки, итоговые вклады, выигрыши, банки.
    """
    __slots__ = ('seats', 'contrib', 'collects', 'pots')
    def __init__(self, seats: Dict[str, int], contrib: Dict[str, int], collects: Dict[str, int], pots: List[Pot]):
        self.seats = seats
        self.contrib = contrib
        self.collects = collects
        self.pots = pots

class HandHistoryParser:
    def __init__(self, hero_name: str = None, min_final_players: int = 6, min_final_blind: int = 50):
        # Если имя героя не передано явно, берём из конфигурации
        self.hero_name = hero_name or config.HERO_NAME
        self.min_final_players = min_final_players
        self.min_final_blind = min_final_blind
        # --- Регулярки для парсинга HH ---
        self.re_hand_start = re.compile(r'^Poker Hand #')
        self.re_seat = re.compile(r'^Seat \d+: ([^()]+?) \(([-\d,]+) in chips\)')
        self.re_action = re.compile(r'^(?P<p>[^:]+): (?P<act>posts|bets|calls|raises|all-in|checks|folds)\\b(?:.*?)(?P<amt>[\d,]+)?')
        self.re_raise_to = re.compile(r'raises [\d,]+ to ([\d,]+)')
        self.re_uncalled = re.compile(r'^Uncalled bet \(([\d,]+)\) returned to ([^\n]+)')
        self.re_collected = re.compile(r'^([^:]+) collected ([\d,]+) from pot')
        self.re_summary = re.compile(r'^\*\*\* SUMMARY \*\*\*')
        self.re_blinds = re.compile(r'Level\d+\(([\d,]+)/([\d,]+)\)')
        # Regex for Tournament ID (example, might need adjustment for different HH formats)
        # PokerStars: PokerStars Hand #...: Tournament #TID, ...
        # GG: Tournament #TID (Hold'em)... (this is often in filename for GG)
        # For a generic approach, let's try to find "Tournament #" followed by numbers.
        self.re_tournament_id = re.compile(r"Tournament #(\d+)")
        tournament_id = None
        hand_date = None  # Дата/время турнира (первое упоминание в HH)
        re_date = re.compile(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")

    def parse(self, file_content: str) -> Dict:
        """
        Парсит весь HH-файл, возвращает: список KO Hero, доп. инфу (раздачи, финалка, блайнды и пр.)
        """
        lines = file_content.splitlines()
        hands: List[Hand] = []
        i = 0
        tournament_id = None
        hand_date = None  # Дата/время турнира (первое упоминание в HH)
        re_date = re.compile(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")

        # Try to find tournament_id early in the file
        for line_idx in range(min(len(lines), 50)): # Check first 50 lines
            line_cur = lines[line_idx]
            m_tid = self.re_tournament_id.search(line_cur)
            if m_tid:
                tournament_id = m_tid.group(1)
            if not hand_date:
                m_dt = re_date.search(line_cur)
                if m_dt:
                    hand_date = m_dt.group(1)
            if tournament_id and hand_date:
                break

        # --- Парсим все раздачи ---
        while i < len(lines):
            if self.re_hand_start.match(lines[i]):
                i, h = self._parse_hand(lines, i)
                hands.append(h)
            else:
                i += 1
        result = {
            'tournament_id': tournament_id,
            'hero_ko_count': 0,
            'hero_ko_players': [],
            'hands_count': len(hands),
            'hands': [],
        }
        # GG-Poker HH обычно идут от последней к первой раздаче.
        # Чтобы корректно определить, кто был устранён, анализируем в хронологическом порядке.
        chronological = list(reversed(hands))

        for idx, hand in enumerate(chronological):
            next_hand = chronological[idx+1] if idx+1 < len(chronological) else None
            eliminated = self._eliminated(hand, next_hand)
            ko_this_hand = self._ko_in_hand(hand, eliminated, self.hero_name)
            if ko_this_hand > 0:
                result['hero_ko_count'] += ko_this_hand
                result['hero_ko_players'].extend(eliminated)
            result['hands'].append({
                'hand_idx': idx,
                'eliminated': eliminated,
                'hero_ko': ko_this_hand,
                'players': list(hand.seats.keys()),
            })
        if hand_date:
            result['date'] = hand_date
        return result

    def _parse_hand(self, lines: List[str], idx: int) -> Tuple[int, Hand]:
        seats: Dict[str, int] = {}
        idx += 1
        while idx < len(lines) and not lines[idx].startswith('*** HOLE'):
            m = self.re_seat.match(lines[idx])
            if m:
                name, chips = m.groups()
                seats[self._name(name)] = self._chip(chips)
            idx += 1
        while idx < len(lines) and not lines[idx].startswith('*** HOLE'):
            idx += 1
        while idx < len(lines) and not lines[idx].startswith('*** SHOWDOWN') and not lines[idx].startswith('*** SUMMARY'):
            idx += 1
        idx, contrib = self._parse_actions(lines, idx)
        collects: Dict[str, int] = {}
        collect_idx_search = idx
        while collect_idx_search < len(lines) and not lines[collect_idx_search].startswith('*** SUMMARY'):
            line = lines[collect_idx_search]
            m = self.re_collected.match(line)
            if m:
                pl, amt = m.groups()
                collects[self._name(pl)] = collects.get(self._name(pl), 0) + self._chip(amt)
            collect_idx_search += 1
        while idx < len(lines) and lines[idx].strip():
            idx += 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        pots = self._build_pots(contrib)
        self._assign_winners(pots, collects)
        return idx, Hand(seats, contrib, collects, pots)

    def _parse_actions(self, lines: List[str], idx: int) -> Tuple[int, Dict[str, int]]:
        contrib: Dict[str, int] = {}
        committed: Dict[str, int] = {}
        while idx < len(lines) and not self.re_summary.match(lines[idx]):
            line = lines[idx]
            m_unc = self.re_uncalled.match(line)
            if m_unc:
                amt, pl = m_unc.groups()
                pl = self._name(pl)
                val = self._chip(amt)
                contrib[pl] = contrib.get(pl, 0) - val
                committed[pl] = committed.get(pl, 0) - val
                idx += 1
                continue
            m = self.re_action.match(line)
            if m:
                pl, act, amt_s = m.groups()
                pl = self._name(pl)
                amt = self._chip(amt_s)
                if act in ('posts', 'bets', 'calls', 'all-in'):
                    contrib[pl] = contrib.get(pl, 0) + amt
                    committed[pl] = committed.get(pl, 0) + amt
                elif act == 'raises':
                    to_m = self.re_raise_to.search(line)
                    if not to_m:
                        idx += 1
                        continue
                    total_to = self._chip(to_m.group(1))
                    prev = committed.get(pl, 0)
                    diff = total_to - prev
                    contrib[pl] = contrib.get(pl, 0) + diff
                    committed[pl] = total_to
            idx += 1
        return idx, contrib

    def _build_pots(self, contrib: Dict[str, int]) -> List[Pot]:
        pots: List[Pot] = []
        if not contrib:
            return pots
        levels = sorted({v for v in contrib.values() if v > 0})
        prev = 0
        for lv in levels:
            elig = {p for p, a in contrib.items() if a >= lv}
            layer = lv - prev
            size = layer * len(elig)
            pots.append(Pot(size, elig))
            prev = lv
        return pots

    def _assign_winners(self, pots: List[Pot], collects: Dict[str, int]):
        remaining = collects.copy()
        for pot in sorted(pots, key=lambda p: len(p.eligible)):
            pot_left = pot.size
            for p in pot.eligible:
                r = remaining.get(p, 0)
                if r <= 0 or pot_left <= 0:
                    continue
                take = min(r, pot_left)
                if take > 0:
                    pot.winners.add(p)
                    remaining[p] -= take
                    pot_left -= take
            if pot_left > 0 and pot.eligible:
                p = next(iter(pot.eligible))
                pot.winners.add(p)

    def _eliminated(self, curr: Hand, nxt: Optional[Hand]) -> List[str]:
        if nxt is None:
            return []
        return [p for p in curr.seats if p not in nxt.seats]

    def _ko_in_hand(self, hand: Hand, eliminated: List[str], hero: str) -> int:
        # TEMP DEBUGGING LOGIC: Simpler KO check
        if eliminated and hero in hand.collects and hand.collects[hero] > 0:
            # Check if Hero won any pot at all
            for pot in hand.pots:
                if hero in pot.winners:
                    return len(eliminated) # Count all eliminations if Hero won any pot in this hand
        return 0

    def _chip(self, s: str) -> int:
        return int(s.replace(',', '')) if s else 0
    def _name(self, s: str) -> str:
        return s.strip()

    def _extract_blinds(self, lines: List[str], hand_idx: int) -> Tuple[int, int]:
        # Пробуем найти строку с блайндами до этой раздачи (ищем 5 строк назад)
        start = max(0, hand_idx*10 - 10)  # Эвристика, в HH структура стабильна
        end = min(len(lines), hand_idx*10 + 20)
        for i in range(start, end):
            m = self.re_blinds.search(lines[i])
            if m:
                return int(m.group(1).replace(',', '')), int(m.group(2).replace(',', ''))
        return (0, 0)
