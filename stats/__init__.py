#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROYAL_Stats - Модули статистики для покерного трекера.
Данный модуль служит для импорта всех модулей статистики.
"""

from stats.base_stat import BaseStat
from stats.positions_stat import PositionsStat
from stats.knockouts_stat import KnockoutsStat
from stats.large_ko_stat import LargeKOStat
from stats.profit_stat import ProfitStat

# Список всех доступных модулей статистики
AVAILABLE_STATS = [
    PositionsStat,
    KnockoutsStat,
    LargeKOStat,
    ProfitStat
]

__all__ = [
    'BaseStat',
    'PositionsStat',
    'KnockoutsStat',
    'LargeKOStat',
    'ProfitStat',
    'AVAILABLE_STATS'
]