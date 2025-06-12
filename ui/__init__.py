# -*- coding: utf-8 -*-

"""
GUI-пакет Royal Stats (Hero-only).
Импортирует основные компоненты интерфейса.
"""

from .main_window import MainWindow
from .stats_grid import StatsGrid
from .tournament_view import TournamentView
from .session_view import SessionView
from .session_select_dialog import SessionSelectDialog
from .app_style import apply_dark_theme  # Удобно импортировать напрямую для использования в app.py
from .gradient_label import GradientLabel

# Добавляй свои компоненты, если будут новые

__all__ = [
    'MainWindow',
    'StatsGrid',
    'TournamentView',
    'SessionView',
    'SessionSelectDialog',
    'apply_dark_theme',
    'GradientLabel',
]