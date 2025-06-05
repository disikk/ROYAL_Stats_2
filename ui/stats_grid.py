# -*- coding: utf-8 -*-

"""
Компонент для отображения общей статистики и графиков.
Отображает карточки с ключевыми показателями и гистограмму распределения мест.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
    QStackedBarSeries,
)
import logging
from typing import Dict, List, Any
import math
from statistics import median
from datetime import datetime

import config
from application_service import ApplicationService
from models import OverallStats

# Импортируем функции стилизации
from ui.app_style import (
    format_money,
    format_percentage,
    apply_cell_color_by_value,
    apply_bigko_x10_color,
    apply_bigko_high_tier_color,
)

# Импортируем плагины для получения их результатов
from stats import (
    TotalKOStat,
    ITMStat,
    ROIStat,
    BigKOStat,
    AvgKOPerTournamentStat,
    FinalTableReachStat,
    AvgFTInitialStackStat,
    EarlyFTKOStat,
    EarlyFTBustStat,
    FTStackConversionStat,
    FTStackConversionAttemptsStat,
    AvgFinishPlaceStat,
    AvgFinishPlaceFTStat,
    AvgFinishPlaceNoFTStat,
    PreFTKOStat,
    IncompleteFTPercentStat,
    KOLuckStat,
    ROIAdjustedStat,
    KOContributionStat,
)

from ui.background import thread_manager

logger = logging.getLogger('ROYAL_Stats.StatsGrid')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)


class StatCard(QtWidgets.QFrame):
    """Карточка для отображения одного показателя статистики."""
    
    def __init__(self, title: str, value: str = "-", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272A;
                border-radius: 8px;
                padding: 3px 6px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 11px;
                font-weight: 500;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Растягиваем пространство между заголовком и значением
        layout.addStretch()
        
        self.value_label = QtWidgets.QLabel(value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.value_label)
        
        # Сохраняем subtitle для специальных карточек
        self.subtitle = subtitle
        
    def update_value(self, value: str, subtitle: str = ""):
        """Обновляет значение карточки."""
        self.value_label.setText(value)
        self.subtitle = subtitle
    
    def setTooltip(self, text: str):
        """Устанавливает тултип для всей карточки."""
        self.setToolTip(text)


class SpecialStatCard(QtWidgets.QFrame):
    """Специальная карточка для статов с переносом строки (FT стек и Early FT KO)."""
    
    def __init__(self, title: str, value: str = "-", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272A;
                border-radius: 8px;
                padding: 3px 6px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Верхняя строка с заголовком и значением
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(3)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 11px;
                font-weight: 500;
                background-color: transparent;
            }
        """)
        top_layout.addWidget(self.title_label)
        
        top_layout.addStretch()
        
        self.value_label = QtWidgets.QLabel(value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        top_layout.addWidget(self.value_label)
        
        layout.addLayout(top_layout)
        
        # Подзаголовок (для отображения дополнительной информации)
        if subtitle:
            self.subtitle_label = QtWidgets.QLabel(subtitle)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: #71717A;
                    font-size: 11px;
                    background-color: transparent;
                    margin-top: 0px;
                }
            """)
            self.subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None
            
    def update_value(self, value: str, subtitle: str = ""):
        """Обновляет значение и подзаголовок карточки."""
        self.value_label.setText(value)
        if subtitle:
            if self.subtitle_label:
                self.subtitle_label.setText(subtitle)
            else:
                self.subtitle_label = QtWidgets.QLabel(subtitle)
                self.subtitle_label.setStyleSheet("""
                    QLabel {
                        color: #71717A;
                        font-size: 11px;
                        background-color: transparent;
                        margin-top: 0px;
                    }
                """)
                self.subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
                self.layout().addWidget(self.subtitle_label)
        else:
            if self.subtitle_label:
                self.layout().removeWidget(self.subtitle_label)
                self.subtitle_label.deleteLater()
                self.subtitle_label = None
    
    def setTooltip(self, text: str):
        """Устанавливает тултип для всей карточки."""
        self.setToolTip(text)


class StatsGrid(QtWidgets.QWidget):
    """Виджет с сеткой статистических показателей и графиками."""

    overallStatsChanged = QtCore.pyqtSignal(OverallStats)
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self._data_cache = {}  # Кеш для данных
        self._cache_valid = False  # Флаг валидности кеша
        self.current_buyin_filter = None
        self.current_session_id = None
        # По умолчанию показываем статистику начиная с 1 января 2024 года
        self.current_date_from = datetime(2024, 1, 1, 0, 0)
        self.current_date_to = datetime.now()
        self._session_map = {}
        
        # Таймер для debounce фильтров
        self._filter_timer = QtCore.QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self._apply_filters)

        # Настройки гистограммы стеков FT
        self.ft_stack_step = 2  # шаг интервалов в BB
        self._current_tournaments = []  # сохраненные турниры для перерасчета
        self.ft_stack_roi_dist = {}  # распределение ROI по стекам FT

        self._init_ui()
        
    def _init_ui(self):
        """Инициализирует UI компоненты."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Создаем QScrollArea для всего содержимого
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        
        # Контейнер для всего содержимого
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)
        
        # Заголовок с панелью фильтров
        header_layout = QtWidgets.QHBoxLayout()
        header_label = QtWidgets.QLabel("Общая статистика")
        header_label.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FAFAFA;
            }
            """
        )
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Бай-ин
        buyin_widget = QtWidgets.QWidget()
        buyin_layout = QtWidgets.QVBoxLayout(buyin_widget)
        buyin_layout.setContentsMargins(0, 0, 0, 0)
        buyin_layout.setSpacing(2)
        buyin_label = QtWidgets.QLabel("Бай-ин")
        self.buyin_filter = QtWidgets.QComboBox()
        self.buyin_filter.setMinimumWidth(100)
        self.buyin_filter.currentTextChanged.connect(self._on_filter_changed)
        buyin_layout.addWidget(buyin_label)
        buyin_layout.addWidget(self.buyin_filter)
        header_layout.addWidget(buyin_widget)

        # Сессия
        session_widget = QtWidgets.QWidget()
        session_layout = QtWidgets.QVBoxLayout(session_widget)
        session_layout.setContentsMargins(0, 0, 0, 0)
        session_layout.setSpacing(2)
        session_label = QtWidgets.QLabel("Сессия")
        self.session_filter = QtWidgets.QComboBox()
        self.session_filter.setMinimumWidth(140)
        self.session_filter.currentTextChanged.connect(self._on_filter_changed)
        session_layout.addWidget(session_label)
        session_layout.addWidget(self.session_filter)
        header_layout.addWidget(session_widget)

        # Диапазон дат
        from_widget = QtWidgets.QWidget()
        from_layout = QtWidgets.QVBoxLayout(from_widget)
        from_layout.setContentsMargins(0, 0, 0, 0)
        from_layout.setSpacing(2)
        from_label = QtWidgets.QLabel("С")
        self.date_from_edit = QtWidgets.QDateTimeEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        # Значение по умолчанию — начало 2024 года
        self.date_from_edit.setDateTime(QtCore.QDateTime.fromString("2024-01-01 00:00:00", "yyyy-MM-dd HH:mm:ss"))
        self.date_from_edit.dateTimeChanged.connect(self._on_filter_changed)
        from_layout.addWidget(from_label)
        from_layout.addWidget(self.date_from_edit)
        header_layout.addWidget(from_widget)

        to_widget = QtWidgets.QWidget()
        to_layout = QtWidgets.QVBoxLayout(to_widget)
        to_layout.setContentsMargins(0, 0, 0, 0)
        to_layout.setSpacing(2)
        to_label = QtWidgets.QLabel("По")
        self.date_to_edit = QtWidgets.QDateTimeEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_to_edit.setDateTime(QtCore.QDateTime.currentDateTime())
        self.date_to_edit.dateTimeChanged.connect(self._on_filter_changed)
        to_layout.addWidget(to_label)
        to_layout.addWidget(self.date_to_edit)
        header_layout.addWidget(to_widget)

        content_layout.addLayout(header_layout)

        self._update_filters()
        
        # Сетка карточек статистики
        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setSpacing(2)
        
        # Создаем карточки для основных показателей
        self.cards = {
            'tournaments': StatCard("Турниров сыграно", "-"),
            'knockouts': StatCard("Всего нокаутов", "-"),
            'avg_ko': StatCard("Среднее KO за турнир", "-"),
            'roi': StatCard("ROI", "-"),
            'ko_contribution': SpecialStatCard("Вклад KO в ROI", "-"),
            'itm': StatCard("ITM%", "-"),
            'ft_reach': StatCard("% Достижения FT", "-"),
            'avg_ft_stack': SpecialStatCard("Средний стек проходки на FT", "-"),
            'early_ft_ko': SpecialStatCard("KO в ранней FT (6-9max)", "-"),
            'early_ft_bust': SpecialStatCard("Вылеты в ранней FT\n(6-9max)", "-"),
            'ft_stack_conv': SpecialStatCard("Конверсия стека в KO\nв 6-9max", "-"),
            'avg_place_all': StatCard("Среднее место (все)", "-"),
            'avg_place_ft': StatCard("Среднее место (FT)", "-"),
            'avg_place_no_ft': StatCard("Среднее место (не FT)", "-"),
            'pre_ft_ko': StatCard("KO до FT", "-"),
        }
        
        # Словарь с описаниями для тултипов
        self.stat_tooltips = {
            'tournaments': "Общее количество сыгранных турниров в выбранном периоде",
            'knockouts': "Суммарное количество нокаутов (выбитых игроков) за все турниры",
            'avg_ko': "Среднее количество нокаутов за один турнир",
            'roi': "Return On Investment - процент прибыли относительно вложенных средств.\nФормула: (Выигрыш - Бай-ин) / Бай-ин × 100%",
            'ko_contribution': "Показывает, какую часть ROI обеспечивают нокауты.\nС поправкой (adj) - учитывает везение в размерах KO",
            'itm': "In The Money - процент попаданий в призовые места (топ-3)",
            'ft_reach': "Процент турниров, в которых вы достигли финального стола (9 игроков)",
            'avg_ft_stack': "Средний размер стека при выходе на финальный стол.\nПоказывается в фишках и больших блайндах (BB)",
            'early_ft_ko': "Количество нокаутов в ранней стадии финального стола (9-6 игроков).\nПоказывает агрессивность игры на этом этапе",
            'early_ft_bust': "Количество вылетов в ранней стадии финального стола (места 6-9).\nПоказывает стабильность игры после выхода на FT",
            'ft_stack_conv': "Эффективность конверсии медианного размера стека выхода на FT в нокауты на ранней стадии FT (6-9max).\nВо второй строке \u2014 среднее число попыток нокаута на турнир с FT.\n>1.0 - выбиваете больше ожидаемого\n=1.0 - выбиваете как ожидается\n<1.0 - выбиваете меньше ожидаемого",
            'avg_place_all': "Среднее место по всем сыгранным турнирам",
            'avg_place_ft': "Среднее место среди турниров с достижением финального стола",
            'avg_place_no_ft': "Среднее место среди турниров без достижения финального стола",
            'pre_ft_ko': "Количество нокаутов до выхода на финальный стол"
        }
        
        # Устанавливаем тултипы для карточек
        for key, card in self.cards.items():
            if key in self.stat_tooltips:
                card.setTooltip(self.stat_tooltips[key])
        
        # Размещаем карточки в сетке (5 колонок)
        positions = [
            ('tournaments', 0, 0), ('roi', 0, 1), ('itm', 0, 2), ('knockouts', 0, 3), ('avg_ko', 0, 4),
            ('ft_reach', 1, 0), ('avg_ft_stack', 1, 1), ('early_ft_ko', 1, 2), ('ft_stack_conv', 1, 3), ('pre_ft_ko', 1, 4),
            ('avg_place_all', 2, 0), ('avg_place_ft', 2, 1), ('avg_place_no_ft', 2, 2), ('early_ft_bust', 2, 3), ('ko_contribution', 2, 4),
        ]
        
        for key, row, col in positions:
            if key in self.cards:
                stats_grid.addWidget(self.cards[key], row, col)
            
        content_layout.addLayout(stats_grid)
        
        # Разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 3px 0; }")
        content_layout.addWidget(separator)
        
        # График распределения мест
        self.chart_header = QtWidgets.QLabel("Распределение финишных мест на финальном столе")
        self.chart_header.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 3px;
            }
        """)

        # Заголовок и переключатель типа гистограммы в одной строке
        chart_header_layout = QtWidgets.QHBoxLayout()
        chart_header_layout.addWidget(self.chart_header)
        chart_header_layout.addStretch()

        # Выбор плотности баров для гистограммы стеков FT
        self.ft_stack_density_selector = QtWidgets.QComboBox()
        self.ft_stack_density_selector.addItems(["2 BB", "5 BB", "10 BB"])
        self.ft_stack_density_selector.currentIndexChanged.connect(
            self._on_density_selector_changed
        )
        self.ft_stack_density_selector.setVisible(False)
        chart_header_layout.addWidget(self.ft_stack_density_selector)

        self.chart_selector = QtWidgets.QComboBox()
        self.chart_selector.addItems([
            "Финальный стол",
            "До финального стола",
            "Все места",
            "Стек FT (BB)",
            "ROI по стекам FT",
        ])
        self.chart_selector.currentIndexChanged.connect(self._on_chart_selector_changed)
        self.chart_type = 'ft'
        chart_header_layout.addWidget(self.chart_selector)
        content_layout.addLayout(chart_header_layout)
        
        # Создаем виджет для графика
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(236)
        self.chart_view.setMaximumHeight(304)
        content_layout.addWidget(self.chart_view)
        self.chart_view.chart_labels = []  # Список для хранения меток
        
        # Разделитель
        separator2 = QtWidgets.QFrame()
        separator2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator2.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 5px 0; }")
        content_layout.addWidget(separator2)
        
        # Карточки для Big KO
        bigko_header = QtWidgets.QLabel("Статистика больших нокаутов")
        bigko_header.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #FAFAFA;
                margin-top: 1px;
                margin-bottom: 3px;
            }
        """)

        # Текст с информацией о частоте KO x10
        self.bigko_x10_info_label = QtWidgets.QLabel("")
        self.bigko_x10_info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.bigko_x10_info_label.setStyleSheet(
            "QLabel { color: #A1A1AA; font-size: 10px; }"
        )

        # Шапка секции Big KO с выравниванием текста x10 по карточке
        bigko_header_layout = QtWidgets.QGridLayout()
        bigko_header_layout.setContentsMargins(0, 0, 0, 0)
        bigko_header_layout.setSpacing(0)
        for i in range(6):
            bigko_header_layout.setColumnStretch(i, 1)
        bigko_header_layout.addWidget(bigko_header, 0, 0, 1, 2, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        bigko_header_layout.addWidget(self.bigko_x10_info_label, 0, 2, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        content_layout.addLayout(bigko_header_layout)

        # Горизонтальный layout для всех карточек Big KO в одну строку
        bigko_layout = QtWidgets.QHBoxLayout()
        bigko_layout.setSpacing(3)
        
        self.bigko_cards = {
            'x1.5': SpecialStatCard("KO x1.5", "-"),
            'x2': SpecialStatCard("KO x2", "-"),
            'x10': SpecialStatCard("KO x10", "-"),
            'x100': StatCard("KO x100", "-"),
            'x1000': StatCard("KO x1000", "-"),
            'x10000': StatCard("KO x10000", "-"),
        }
        
        # Фиксируем минимальную высоту для карточек Big KO
        for card in self.bigko_cards.values():
            card.setMinimumHeight(40)

        # Добавляем все карточки Big KO в горизонтальный layout
        bigko_layout.addWidget(self.bigko_cards['x1.5'])
        bigko_layout.addWidget(self.bigko_cards['x2'])
        bigko_layout.addWidget(self.bigko_cards['x10'])
        bigko_layout.addWidget(self.bigko_cards['x100'])
        bigko_layout.addWidget(self.bigko_cards['x1000'])
        bigko_layout.addWidget(self.bigko_cards['x10000'])
            
        content_layout.addLayout(bigko_layout)
        
        # Добавляем стат KO Luck
        ko_luck_layout = QtWidgets.QHBoxLayout()
        ko_luck_layout.setSpacing(5)
        ko_luck_layout.setContentsMargins(0, 5, 0, 0)
        
        # Заголовок стата
        self.ko_luck_label = QtWidgets.QLabel("Удача KO:")
        self.ko_luck_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        ko_luck_layout.addWidget(self.ko_luck_label)
        
        # Значение стата
        self.ko_luck_value = QtWidgets.QLabel("-")
        self.ko_luck_value.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
            }
        """)
        ko_luck_layout.addWidget(self.ko_luck_value)

        # Иконка информации
        self.ko_luck_info = QtWidgets.QLabel("ⓘ")
        self.ko_luck_info.setStyleSheet("""
            QLabel {
                color: #71717A;
                font-size: 14px;
            }
        """)
        # Устанавливаем курсор-указатель
        self.ko_luck_info.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        tooltip_text = ("Показывает отклонение полученных денег от нокаутов относительно среднего.\n"
                       "Формула: сумма моих нокаутов ($) – количество_нокаутов × средний нокаут ($)\n"
                       "Положительное значение означает удачу (выше среднего), отрицательное - неудачу.")
        
        # Создаем кастомный tooltip виджет
        self.ko_luck_tooltip = QtWidgets.QLabel(tooltip_text, self)
        self.ko_luck_tooltip.setWindowFlags(QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint)
        self.ko_luck_tooltip.setStyleSheet("""
            QLabel {
                color: #1F2937;
                background-color: #F3F4F6;
                border: 1px solid #E5E7EB;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self.ko_luck_tooltip.hide()
        
        # Подключаем события для показа/скрытия кастомной подсказки
        self.ko_luck_info.enterEvent = lambda event: self._show_ko_luck_tooltip()
        self.ko_luck_info.leaveEvent = lambda event: self.ko_luck_tooltip.hide()

        ko_luck_layout.addWidget(self.ko_luck_info)

        # ROI с поправкой на KO Luck
        ko_luck_layout.addSpacing(10)
        self.roi_adj_label = QtWidgets.QLabel("ROI adj:")
        self.roi_adj_label.setStyleSheet(
            """
            QLabel {
                color: #A1A1AA;
                font-size: 14px;
                font-weight: 500;
            }
            """
        )
        ko_luck_layout.addWidget(self.roi_adj_label)

        self.roi_adj_value = QtWidgets.QLabel("-")
        self.roi_adj_value.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
            }
            """
        )
        ko_luck_layout.addWidget(self.roi_adj_value)

        # Иконка информации для ROI adj
        self.roi_adj_info = QtWidgets.QLabel("ⓘ")
        self.roi_adj_info.setStyleSheet("""
            QLabel {
                color: #71717A;
                font-size: 14px;
            }
        """)
        # Устанавливаем курсор-указатель
        self.roi_adj_info.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        roi_adj_tooltip_text = ("ROI с поправкой на удачу в нокаутах.\n"
                               "Формула: (Прибыль - KO Luck) / Общий байин × 100%\n"
                               "Показывает реальную доходность с учетом везения/невезения в размерах KO.")
        
        # Создаем кастомный tooltip виджет для ROI adj
        self.roi_adj_tooltip = QtWidgets.QLabel(roi_adj_tooltip_text, self)
        self.roi_adj_tooltip.setWindowFlags(QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint)
        self.roi_adj_tooltip.setStyleSheet("""
            QLabel {
                color: #1F2937;
                background-color: #F3F4F6;
                border: 1px solid #E5E7EB;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self.roi_adj_tooltip.hide()
        
        # Подключаем события для показа/скрытия кастомной подсказки
        self.roi_adj_info.enterEvent = lambda event: self._show_roi_adj_tooltip()
        self.roi_adj_info.leaveEvent = lambda event: self.roi_adj_tooltip.hide()
        
        ko_luck_layout.addWidget(self.roi_adj_info)

        # Добавляем растяжку для выравнивания по левому краю
        ko_luck_layout.addStretch()
        
        content_layout.addLayout(ko_luck_layout)
        
        # Добавляем отступ внизу
        content_layout.addSpacing(5)
        
        # Устанавливаем контент в scroll area
        self.scroll_area.setWidget(content_widget)
        
        # Добавляем scroll area в основной layout
        main_layout.addWidget(self.scroll_area)
        
        # Создаем loading overlay
        self._create_loading_overlay()
        
    def _create_loading_overlay(self):
        """Создает оверлей загрузки."""
        self.loading_overlay = QtWidgets.QWidget(self)
        self.loading_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self.loading_overlay)
        
        # Контейнер для индикатора
        container = QtWidgets.QWidget()
        container.setMaximumWidth(300)
        container.setStyleSheet("""
            QWidget {
                background-color: #27272A;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        container_layout = QtWidgets.QVBoxLayout(container)
        
        # Индикатор загрузки
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3F3F46;
                border-radius: 6px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 6px;
            }
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Текст загрузки
        self.loading_label = QtWidgets.QLabel("Загрузка данных...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        self.loading_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.loading_label)
        
        layout.addWidget(container, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.loading_overlay.hide()
        
    def show_loading_overlay(self):
        """Показывает оверлей загрузки."""
        self.loading_overlay.resize(self.size())
        self.loading_overlay.raise_()
        self.loading_overlay.show()
        
    def hide_loading_overlay(self):
        """Скрывает оверлей загрузки."""
        self.loading_overlay.hide()

    def resizeEvent(self, event):
        """Обрабатывает изменение размера виджета."""
        super().resizeEvent(event)
        # Обновляем размер оверлея при изменении размера виджета
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())

    def _update_filters(self):
        """Обновляет доступные значения фильтров."""
        self.buyin_filter.blockSignals(True)
        self.buyin_filter.clear()
        self.buyin_filter.addItem("Все")
        for b in sorted(self.app_service.get_distinct_buyins()):
            self.buyin_filter.addItem(str(b))
        self.buyin_filter.blockSignals(False)

        self.session_filter.blockSignals(True)
        self.session_filter.clear()
        self.session_filter.addItem("Все")
        self._session_map.clear()
        for s in self.app_service.get_all_sessions():
            self.session_filter.addItem(s.session_name)
            self._session_map[s.session_name] = s.session_id
        self.session_filter.blockSignals(False)

    def _on_filter_changed(self):
        """Запускает таймер для отложенного применения фильтров."""
        # Отменяем предыдущий таймер и запускаем новый
        self._filter_timer.stop()
        self._filter_timer.start(300)  # 300мс задержка
        
    def _apply_filters(self):
        """Применяет выбранные фильтры и перезагружает данные."""
        buyin = self.buyin_filter.currentText()
        self.current_buyin_filter = float(buyin) if buyin and buyin != "Все" else None
        session_name = self.session_filter.currentText()
        self.current_session_id = (
            self._session_map.get(session_name) if session_name and session_name != "Все" else None
        )
        self.current_date_from = self.date_from_edit.dateTime().toPyDateTime()
        self.current_date_to = self.date_to_edit.dateTime().toPyDateTime()
        self.invalidate_cache()
        self.reload()
            
    def invalidate_cache(self):
        """Сбрасывает кеш данных."""
        self._cache_valid = False
        self._data_cache.clear()
        
    def reload(self, show_overlay: bool = True):
        """Перезагружает все данные из ApplicationService."""
        logger.debug("=== Начало reload StatsGrid ===")
        self._show_overlay = show_overlay
        if show_overlay:
            self.show_loading_overlay()

        # Перед загрузкой данных обновляем фильтры, чтобы они отражали текущее
        # состояние базы данных. Сохраняем выбранные значения, если они все ещё
        # присутствуют в новой выборке.
        prev_buyin = self.buyin_filter.currentText()
        prev_session = self.session_filter.currentText()
        self._update_filters()
        self.buyin_filter.blockSignals(True)
        if prev_buyin in [self.buyin_filter.itemText(i) for i in range(self.buyin_filter.count())]:
            self.buyin_filter.setCurrentText(prev_buyin)
        self.buyin_filter.blockSignals(False)
        self.session_filter.blockSignals(True)
        if prev_session in [self.session_filter.itemText(i) for i in range(self.session_filter.count())]:
            self.session_filter.setCurrentText(prev_session)
        self.session_filter.blockSignals(False)
        buyin = self.buyin_filter.currentText()
        self.current_buyin_filter = float(buyin) if buyin and buyin != "Все" else None
        session_name = self.session_filter.currentText()
        self.current_session_id = (
            self._session_map.get(session_name) if session_name and session_name != "Все" else None
        )
        
        def load_data(is_cancelled_callback=None):
            # Проверяем отмену перед загрузкой турниров
            if is_cancelled_callback and is_cancelled_callback():
                return None

            tournaments = self.app_service.tournament_repo.get_all_tournaments(
                session_id=self.current_session_id,
                buyin_filter=self.current_buyin_filter,
                # В БД дата хранится в формате "YYYY/MM/DD HH:MM:SS", поэтому
                # формируем строки фильтра аналогично, чтобы сравнение прошло корректно
                start_time_from=self.current_date_from.strftime("%Y/%m/%d %H:%M:%S"),
                start_time_to=self.current_date_to.strftime("%Y/%m/%d %H:%M:%S"),
            )
            
            # Проверяем отмену после загрузки турниров
            if is_cancelled_callback and is_cancelled_callback():
                return None
            
            # Получаем руки финального стола с фильтрацией на уровне SQL
            if self.current_buyin_filter is not None:
                # Если есть фильтр по байину, получаем список tournament_id для этого байина
                tournament_ids = [t.tournament_id for t in tournaments]
                ft_hands = self.app_service.ft_hand_repo.get_hands_by_filters(
                    session_id=self.current_session_id,
                    tournament_ids=tournament_ids if tournament_ids else None
                )
            else:
                # Если нет фильтра по байину, фильтруем только по сессии
                ft_hands = self.app_service.ft_hand_repo.get_hands_by_filters(
                    session_id=self.current_session_id
                )
                
            # Проверяем отмену после загрузки рук
            if is_cancelled_callback and is_cancelled_callback():
                return None

            # Вычисляем статистику в фоновом потоке
            overall_stats = self._compute_overall_stats_filtered(tournaments, ft_hands)
            
            # Проверяем отмену после вычисления статистики
            if is_cancelled_callback and is_cancelled_callback():
                return None

            place_dist = {i: 0 for i in range(1, 10)}
            place_dist_pre_ft = {i: 0 for i in range(10, 19)}
            place_dist_all = {i: 0 for i in range(1, 19)}
            # Новое распределение для стеков FT и медиана
            ft_stack_dist, ft_stack_median = self._calculate_ft_stack_distribution(
                tournaments, step=self.ft_stack_step
            )
            # Распределение среднего ROI по стекам FT
            ft_stack_roi_dist, _ = self._calculate_ft_stack_roi_distribution(
                tournaments, step=self.ft_stack_step
            )
            
            for t in tournaments:
                if t.finish_place is None:
                    continue
                if 1 <= t.finish_place <= 9:
                    place_dist[t.finish_place] += 1
                if 10 <= t.finish_place <= 18:
                    place_dist_pre_ft[t.finish_place] += 1
                if 1 <= t.finish_place <= 18:
                    place_dist_all[t.finish_place] += 1

            # Вычисляем статистики с проверками отмены
            roi_value = ROIStat().compute([], [], [], overall_stats).get('roi', 0.0)
            if is_cancelled_callback and is_cancelled_callback():
                return None
                
            itm_value = ITMStat().compute(tournaments, [], [], overall_stats).get('itm_percent', 0.0)
            ft_reach = FinalTableReachStat().compute(tournaments, [], [], overall_stats).get('final_table_reach_percent', 0.0)
            avg_stack_res = AvgFTInitialStackStat().compute(tournaments, [], [], overall_stats)
            avg_chips = avg_stack_res.get('avg_ft_initial_stack_chips', 0.0)
            avg_bb = avg_stack_res.get('avg_ft_initial_stack_bb', 0.0)
            
            if is_cancelled_callback and is_cancelled_callback():
                return None
                
            early_res = EarlyFTKOStat().compute(tournaments, ft_hands, [], overall_stats)
            early_ko = early_res.get('early_ft_ko_count', 0)
            early_ko_per = early_res.get('early_ft_ko_per_tournament', 0.0)
            conv_res = FTStackConversionStat().compute(tournaments, ft_hands, [], overall_stats)
            ft_stack_conv = conv_res.get('ft_stack_conversion', 0.0)
            attempts_res = FTStackConversionAttemptsStat().compute(tournaments, ft_hands, [], overall_stats)
            avg_attempts = attempts_res.get('avg_ko_attempts_per_ft', 0.0)
            pre_ft_ko_res = PreFTKOStat().compute(tournaments, ft_hands, [], overall_stats)
            pre_ft_ko_count = pre_ft_ko_res.get('pre_ft_ko_count', 0.0)
            
            if is_cancelled_callback and is_cancelled_callback():
                return None
            ko_luck_value = KOLuckStat().compute(tournaments, [], [], overall_stats).get('ko_luck', 0.0)
            roi_adj_value = ROIAdjustedStat().compute(tournaments, ft_hands, [], overall_stats).get('roi_adj', 0.0)
            ko_contrib_res = KOContributionStat().compute(tournaments, [], [], None)
            ko_contrib = ko_contrib_res.get('ko_contribution', 0.0)
            ko_contrib_adj = ko_contrib_res.get('ko_contribution_adj', 0.0)
            all_places = [t.finish_place for t in tournaments if t.finish_place is not None]
            avg_all = sum(all_places) / len(all_places) if all_places else 0.0
            ft_places = [t.finish_place for t in tournaments if t.reached_final_table and t.finish_place is not None and 1 <= t.finish_place <= 9]
            avg_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0
            no_ft_places = [t.finish_place for t in tournaments if not t.reached_final_table and t.finish_place is not None]
            avg_no_ft = sum(no_ft_places) / len(no_ft_places) if no_ft_places else 0.0
            return {
                'overall_stats': overall_stats,
                'all_tournaments': tournaments,
                'place_dist': place_dist,
                'place_dist_pre_ft': place_dist_pre_ft,
                'place_dist_all': place_dist_all,
                'ft_stack_dist': ft_stack_dist,
                'ft_stack_median': ft_stack_median,
                'roi': roi_value,
                'itm': itm_value,
                'ft_reach': ft_reach,
                'avg_chips': avg_chips,
                'avg_bb': avg_bb,
                'early_ko': early_ko,
                'early_ko_per': early_ko_per,
                'avg_ko_attempts_per_ft': avg_attempts,
                'ft_stack_conv': ft_stack_conv,
                'pre_ft_ko_count': pre_ft_ko_count,
                'avg_place_all': avg_all,
                'avg_place_ft': avg_ft,
                'avg_place_no_ft': avg_no_ft,
                'ko_luck': ko_luck_value,
                'roi_adj': roi_adj_value,
                'ko_contribution': ko_contrib,
                'ko_contribution_adj': ko_contrib_adj,
            }
        thread_manager.run_in_thread(
            widget_id=str(id(self)),
            fn=load_data,
            callback=self._on_data_loaded,
            error_callback=self._on_load_error,
            owner=self
        )
        
    def _on_data_loaded(self, data: dict):
        """Применяет загруженные данные к UI."""
        # Проверяем, что данные не были отменены
        if data is None:
            logger.debug("Загрузка данных была отменена")
            return
            
        try:
            overall_stats = data['overall_stats']
            all_tournaments = data['all_tournaments']
            
            self.cards['tournaments'].update_value(str(overall_stats.total_tournaments))
            logger.debug(f"Обновлена карточка tournaments: {overall_stats.total_tournaments}")

            self.cards['knockouts'].update_value(f"{overall_stats.total_knockouts:.1f}")
            logger.debug(f"Обновлена карточка knockouts: {overall_stats.total_knockouts:.1f}")

            self.cards['avg_ko'].update_value(f"{overall_stats.avg_ko_per_tournament:.2f}")
            logger.debug(f"Обновлена карточка avg_ko: {overall_stats.avg_ko_per_tournament:.2f}")

            roi_value = data['roi']
            roi_text = f"{roi_value:+.1f}%"
            self.cards['roi'].update_value(roi_text)
            logger.debug(f"Обновлена карточка roi: {roi_text}")
            # Применяем цвет только к тексту, а не к фону
            apply_cell_color_by_value(self.cards['roi'].value_label, roi_value)

            ko_contrib = data.get('ko_contribution', 0.0)
            ko_contrib_adj = data.get('ko_contribution_adj', 0.0)
            self.cards['ko_contribution'].update_value(
                f"{ko_contrib:.1f}%",
                f"С поправкой на удачу в КО (adj) {ko_contrib_adj:.1f}%"
            )
            logger.debug(
                f"Обновлена карточка ko_contribution: {ko_contrib:.1f}% / {ko_contrib_adj:.1f}%"
            )

            itm_value = data['itm']
            self.cards['itm'].update_value(f"{itm_value:.1f}%")
            logger.debug(f"Обновлена карточка itm: {itm_value:.1f}%")

            ft_reach_value = data['ft_reach']
            self.cards['ft_reach'].update_value(f"{ft_reach_value:.1f}%")
            logger.debug(f"Обновлена карточка ft_reach: {ft_reach_value:.1f}%")

            avg_chips = data['avg_chips']
            avg_bb = data['avg_bb']
            # Форматируем основное значение и подзаголовок
            self.cards['avg_ft_stack'].update_value(
                f"{avg_chips:,.0f}",
                f"{avg_chips:,.0f} фишек / {avg_bb:.1f} BB"
            )
            logger.debug(f"Обновлена карточка avg_ft_stack: {avg_chips:,.0f} / {avg_bb:.1f} BB")

            early_ko_count = data['early_ko']
            early_ko_per = data['early_ko_per']
            # Форматируем основное значение и подзаголовок
            self.cards['early_ft_ko'].update_value(
                f"{early_ko_count:.1f}",
                f"{early_ko_per:.2f} за турнир с FT"
            )
            logger.debug(f"Обновлена карточка early_ft_ko: {early_ko_count} / {early_ko_per:.2f}")

            ft_stack_conv = data.get('ft_stack_conv', 0.0)
            avg_attempts = data.get('avg_ko_attempts_per_ft', 0.0)
            self.cards['ft_stack_conv'].update_value(
                f"{ft_stack_conv:.2f}",
                f"{avg_attempts:.2f} попыток за турнир с FT"
            )
            logger.debug(
                f"Обновлена карточка ft_stack_conv: {ft_stack_conv:.2f} / {avg_attempts:.2f}"
            )
            

            bust_result = EarlyFTBustStat().compute(all_tournaments, [], [], overall_stats)
            logger.debug(f"Early FT Bust result: {bust_result}")
            bust_count = bust_result.get('early_ft_bust_count', 0)
            bust_per = bust_result.get('early_ft_bust_per_tournament', 0.0)
            self.cards['early_ft_bust'].update_value(
                str(bust_count),
                f"{bust_per:.2f} за турнир с FT"
            )
            logger.debug(f"Обновлена карточка early_ft_bust: {bust_count} / {bust_per:.2f}")
            
            if overall_stats.big_ko_x1_5 > 0:
                per = overall_stats.total_knockouts / overall_stats.big_ko_x1_5 if overall_stats.total_knockouts > 0 else 0
                subtitle = f"1 на {per:.0f} нокаутов"
            else:
                subtitle = ""
            self.bigko_cards['x1.5'].update_value(str(overall_stats.big_ko_x1_5), subtitle)

            if overall_stats.big_ko_x2 > 0:
                per = overall_stats.total_knockouts / overall_stats.big_ko_x2 if overall_stats.total_knockouts > 0 else 0
                subtitle = f"1 на {per:.0f} нокаутов"
            else:
                subtitle = ""
            self.bigko_cards['x2'].update_value(str(overall_stats.big_ko_x2), subtitle)

            if overall_stats.big_ko_x10 > 0:
                per = overall_stats.total_knockouts / overall_stats.big_ko_x10 if overall_stats.total_knockouts > 0 else 0
                subtitle = f"1 на {per:.0f} нокаутов"
            else:
                subtitle = ""
            self.bigko_cards['x10'].update_value(str(overall_stats.big_ko_x10), subtitle)
            self.bigko_cards['x100'].update_value(str(overall_stats.big_ko_x100))
            self.bigko_cards['x1000'].update_value(str(overall_stats.big_ko_x1000))
            self.bigko_cards['x10000'].update_value(str(overall_stats.big_ko_x10000))
            apply_bigko_x10_color(
                self.bigko_cards['x10'].value_label,
                overall_stats.total_tournaments,
                overall_stats.big_ko_x10,
            )
            apply_bigko_high_tier_color(
                self.bigko_cards['x100'].value_label,
                overall_stats.big_ko_x100,
            )
            apply_bigko_high_tier_color(
                self.bigko_cards['x1000'].value_label,
                overall_stats.big_ko_x1000,
            )
            apply_bigko_high_tier_color(
                self.bigko_cards['x10000'].value_label,
                overall_stats.big_ko_x10000,
            )
            # Текст над карточкой KO x10 больше не отображается
            self.bigko_x10_info_label.setText("")
            logger.debug(f"Обновлены карточки Big KO: x1.5={overall_stats.big_ko_x1_5}, x2={overall_stats.big_ko_x2}, x10={overall_stats.big_ko_x10}, x100={overall_stats.big_ko_x100}, x1000={overall_stats.big_ko_x1000}, x10000={overall_stats.big_ko_x10000}")
            
            # Обновляем стат KO Luck
            ko_luck = data.get('ko_luck', 0.0)
            if ko_luck == 0:
                ko_luck_text = "$0.00"
            else:
                ko_luck_text = f"${ko_luck:+.2f}"
            self.ko_luck_value.setText(ko_luck_text)
            # Применяем цвет в зависимости от значения
            if ko_luck > 0:
                self.ko_luck_value.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                        color: #10B981;
                    }
                """)
            elif ko_luck < 0:
                self.ko_luck_value.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                        color: #EF4444;
                    }
                """)
            else:
                self.ko_luck_value.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                    }
                """)
            logger.debug(f"Обновлен KO Luck: {ko_luck_text}")

            # Обновляем ROI с поправкой на KO Luck
            roi_adj = data.get('roi_adj', 0.0)
            roi_adj_text = f"{roi_adj:+.1f}%"
            self.roi_adj_value.setText(roi_adj_text)
            apply_cell_color_by_value(self.roi_adj_value, roi_adj)
            logger.debug(f"Обновлен ROI adj: {roi_adj_text}")
            
            # Статы средних мест (fallback расчет, пока не обновлены другие компоненты)
            # Среднее место по всем турнирам
            all_places = [t.finish_place for t in all_tournaments if t.finish_place is not None]
            avg_all = sum(all_places) / len(all_places) if all_places else 0.0
            self.cards['avg_place_all'].update_value(f"{avg_all:.2f}")
            # Среднее место на финалке
            ft_places = [t.finish_place for t in all_tournaments 
                         if t.reached_final_table and t.finish_place is not None 
                         and 1 <= t.finish_place <= 9]
            avg_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0
            self.cards['avg_place_ft'].update_value(f"{avg_ft:.2f}")
            # Среднее место без финалки
            no_ft_places = [t.finish_place for t in all_tournaments 
                            if not t.reached_final_table and t.finish_place is not None]
            avg_no_ft = sum(no_ft_places) / len(no_ft_places) if no_ft_places else 0.0
            self.cards['avg_place_no_ft'].update_value(f"{avg_no_ft:.2f}")
            
            # Pre-FT KO count
            pre_ft_ko_count = data.get('pre_ft_ko_count', 0.0)
            self.cards['pre_ft_ko'].update_value(f"{pre_ft_ko_count:.1f}")
            logger.debug(f"Обновлена карточка pre_ft_ko: {pre_ft_ko_count:.1f}")

            

            self.place_dist_ft = data['place_dist']
            self.place_dist_pre_ft = data.get('place_dist_pre_ft', {})
            self.place_dist_all = data.get('place_dist_all', {})

            # Сохраняем турниры для возможного перерасчета распределения стеков
            self._current_tournaments = all_tournaments
            self.ft_stack_dist, self.ft_stack_median = self._calculate_ft_stack_distribution(
                self._current_tournaments, step=self.ft_stack_step
            )
            self.ft_stack_roi_dist, _ = self._calculate_ft_stack_roi_distribution(
                self._current_tournaments, step=self.ft_stack_step
            )
            self._update_chart(self._get_current_distribution())
            self.overallStatsChanged.emit(overall_stats)
            logger.debug("=== Конец reload StatsGrid ===")

        finally:
            # Скрываем индикатор загрузки
            if getattr(self, "_show_overlay", False):
                self.hide_loading_overlay()

    def _on_load_error(self, error):
        """Обрабатывает ошибки при загрузке данных."""
        logger.error(f"Ошибка загрузки данных StatsGrid: {error}")
        if getattr(self, "_show_overlay", False):
            self.hide_loading_overlay()
        QtWidgets.QMessageBox.critical(
            self,
            "Ошибка загрузки",
            str(error)
        )

    def _compute_overall_stats_filtered(self, tournaments, ft_hands):
        """Вычисляет агрегированную статистику по отфильтрованным данным."""
        stats = OverallStats()
        stats.total_tournaments = len(tournaments)
        
        # Оптимизированный подсчет с одним проходом по турнирам
        ft_count = 0
        total_buyin = 0.0
        total_prize = 0.0
        total_ko = 0.0
        ft_chips_sum = 0.0
        ft_chips_count = 0
        ft_bb_sum = 0.0
        ft_bb_count = 0
        early_bust_count = 0
        
        for t in tournaments:
            if t.reached_final_table:
                ft_count += 1
                if t.final_table_initial_stack_chips is not None:
                    ft_chips_sum += t.final_table_initial_stack_chips
                    ft_chips_count += 1
                if t.final_table_initial_stack_bb is not None:
                    ft_bb_sum += t.final_table_initial_stack_bb
                    ft_bb_count += 1
                if t.finish_place is not None and 6 <= t.finish_place <= 9:
                    early_bust_count += 1
            
            if t.buyin is not None:
                total_buyin += t.buyin
            if t.payout is not None:
                total_prize += t.payout
            total_ko += t.ko_count
        
        stats.total_final_tables = ft_count
        stats.total_buy_in = total_buyin
        stats.total_prize = total_prize
        # Округляем с точностью до одной цифры для единообразия отображения
        stats.total_knockouts = round(total_ko, 1)
        stats.avg_ko_per_tournament = total_ko / stats.total_tournaments if stats.total_tournaments else 0.0
        stats.final_table_reach_percent = ft_count / stats.total_tournaments * 100 if stats.total_tournaments else 0.0
        stats.avg_ft_initial_stack_chips = ft_chips_sum / ft_chips_count if ft_chips_count else 0.0
        stats.avg_ft_initial_stack_bb = ft_bb_sum / ft_bb_count if ft_bb_count else 0.0
        stats.early_ft_bust_count = early_bust_count
        stats.early_ft_bust_per_tournament = early_bust_count / ft_count if ft_count else 0.0
        
        # Оптимизированный подсчет по рукам
        early_ko_count = 0.0
        pre_ft_ko_count = 0.0
        first_hands = {}
        
        for h in ft_hands:
            if h.is_early_final:
                early_ko_count += h.hero_ko_this_hand
            pre_ft_ko_count += h.pre_ft_ko
            
            if h.table_size == config.FINAL_TABLE_SIZE:
                saved = first_hands.get(h.tournament_id)
                if saved is None or h.hand_number < saved.hand_number:
                    first_hands[h.tournament_id] = h
        
        stats.early_ft_ko_count = round(early_ko_count, 1)
        stats.early_ft_ko_per_tournament = early_ko_count / ft_count if ft_count else 0.0
        stats.pre_ft_ko_count = round(pre_ft_ko_count, 1)
        stats.incomplete_ft_count = sum(
            1 for h in first_hands.values() if h.players_count < config.FINAL_TABLE_SIZE
        )
        all_places = [t.finish_place for t in tournaments if t.finish_place is not None]
        stats.avg_finish_place = sum(all_places) / len(all_places) if all_places else 0.0
        ft_places = [
            t.finish_place
            for t in tournaments
            if t.reached_final_table and t.finish_place is not None and 1 <= t.finish_place <= 9
        ]
        stats.avg_finish_place_ft = sum(ft_places) / len(ft_places) if ft_places else 0.0
        no_ft_places = [
            t.finish_place
            for t in tournaments
            if not t.reached_final_table and t.finish_place is not None
        ]
        stats.avg_finish_place_no_ft = sum(no_ft_places) / len(no_ft_places) if no_ft_places else 0.0
        bigko = BigKOStat().compute(tournaments, ft_hands, [], None)
        stats.big_ko_x1_5 = bigko.get("x1.5", 0)
        stats.big_ko_x2 = bigko.get("x2", 0)
        stats.big_ko_x10 = bigko.get("x10", 0)
        stats.big_ko_x100 = bigko.get("x100", 0)
        stats.big_ko_x1000 = bigko.get("x1000", 0)
        stats.big_ko_x10000 = bigko.get("x10000", 0)
        stats.avg_finish_place = round(stats.avg_finish_place, 2)
        stats.avg_finish_place_ft = round(stats.avg_finish_place_ft, 2)
        stats.avg_finish_place_no_ft = round(stats.avg_finish_place_no_ft, 2)
        stats.avg_ko_per_tournament = round(stats.avg_ko_per_tournament, 2)
        stats.avg_ft_initial_stack_chips = round(stats.avg_ft_initial_stack_chips, 2)
        stats.avg_ft_initial_stack_bb = round(stats.avg_ft_initial_stack_bb, 2)
        stats.early_ft_ko_per_tournament = round(stats.early_ft_ko_per_tournament, 2)
        stats.early_ft_bust_per_tournament = round(stats.early_ft_bust_per_tournament, 2)
        stats.final_table_reach_percent = round(stats.final_table_reach_percent, 2)
        # Финальное округление до одного знака после запятой
        stats.pre_ft_ko_count = round(stats.pre_ft_ko_count, 1)
        stats.total_knockouts = round(stats.total_knockouts, 1)
        stats.early_ft_ko_count = round(stats.early_ft_ko_count, 1)
        return stats
    
    def _show_ko_luck_tooltip(self):
        """Показывает кастомную подсказку для KO Luck."""
        # Получаем глобальную позицию иконки
        global_pos = self.ko_luck_info.mapToGlobal(QtCore.QPoint(0, 0))
        # Позиционируем подсказку выше иконки
        tooltip_pos = QtCore.QPoint(global_pos.x() - 50, global_pos.y() - self.ko_luck_tooltip.sizeHint().height() - 5)
        self.ko_luck_tooltip.move(tooltip_pos)
        self.ko_luck_tooltip.show()
    
    def _show_roi_adj_tooltip(self):
        """Показывает кастомную подсказку для ROI adj."""
        # Получаем глобальную позицию иконки
        global_pos = self.roi_adj_info.mapToGlobal(QtCore.QPoint(0, 0))
        # Позиционируем подсказку выше иконки
        tooltip_pos = QtCore.QPoint(global_pos.x() - 50, global_pos.y() - self.roi_adj_tooltip.sizeHint().height() - 5)
        self.roi_adj_tooltip.move(tooltip_pos)
        self.roi_adj_tooltip.show()
    
    def _calculate_ft_stack_distribution(self, tournaments, step: int = 2):
        """Рассчитывает распределение стеков выхода на FT в больших блайндах
        и медиану значений.

        :param tournaments: список турниров
        :param step: величина интервала для баров
        """
        # Инициализируем словарь для распределения
        ft_stack_dist = {}
        stack_values = []

        # Края распределения
        ft_stack_dist["≤7"] = 0

        # Промежуточные интервалы с заданным шагом
        for i in range(8, 50, step):
            end = min(i + step - 1, 49)
            ft_stack_dist[f"{i}-{end}"] = 0

        ft_stack_dist["≥50"] = 0

        # Подсчитываем распределение
        for t in tournaments:
            if t.reached_final_table and t.final_table_initial_stack_bb is not None:
                bb = t.final_table_initial_stack_bb
                stack_values.append(bb)

                if bb <= 7:
                    ft_stack_dist["≤7"] += 1
                elif bb >= 50:
                    ft_stack_dist["≥50"] += 1
                else:
                    # Находим подходящий интервал
                    interval_start = ((int((bb - 8) / step)) * step) + 8
                    interval_start = max(8, interval_start)
                    interval_end = min(interval_start + step - 1, 49)
                    interval_key = f"{interval_start}-{interval_end}"
                    if interval_key in ft_stack_dist:
                        ft_stack_dist[interval_key] += 1

        median_value = median(stack_values) if stack_values else None

        return ft_stack_dist, median_value
    
    def _calculate_ft_stack_roi_distribution(self, tournaments, step: int = 2):
        """Рассчитывает средний ROI для каждого интервала стеков на FT в больших блайндах.
        
        :param tournaments: список турниров
        :param step: величина интервала для баров
        :returns: (словарь интервалов со средним ROI, медиана стеков)
        """
        # Инициализируем словари для хранения сумм прибыли и бай-инов
        # для каждого интервала. Такой подход позволяет получить средний ROI
        # с учетом размера бай-ина, а не простым средним арифметическим
        # значений отдельных турниров.
        roi_by_interval = {}
        stack_values = []
        
        # Создаём ключи интервалов
        interval_keys = ["≤7"]
        for i in range(8, 50, step):
            end = min(i + step - 1, 49)
            interval_keys.append(f"{i}-{end}")
        interval_keys.append("≥50")
        
        # Инициализируем словари для каждого интервала
        for key in interval_keys:
            roi_by_interval[key] = {
                'profit_sum': 0.0,
                'buyin_sum': 0.0,
            }
        
        # Собираем данные по турнирам
        for t in tournaments:
            if t.reached_final_table and t.final_table_initial_stack_bb is not None:
                bb = t.final_table_initial_stack_bb
                stack_values.append(bb)
                
                # Вычисляем прибыль и учитываем бай-ин. Если бай-ин отсутствует,
                # такой турнир пропускаем, так как ROI для него некорректен.
                if not t.buyin or t.buyin <= 0:
                    continue
                profit = (t.payout - t.buyin) if t.payout else -t.buyin
                
                # Определяем интервал
                if bb <= 7:
                    roi_key = "≤7"
                elif bb >= 50:
                    roi_key = "≥50"
                else:
                    # Находим подходящий интервал
                    interval_start = ((int((bb - 8) / step)) * step) + 8
                    interval_start = max(8, interval_start)
                    interval_end = min(interval_start + step - 1, 49)
                    roi_key = f"{interval_start}-{interval_end}"
                if roi_key in roi_by_interval:
                    roi_by_interval[roi_key]['profit_sum'] += profit
                    roi_by_interval[roi_key]['buyin_sum'] += t.buyin
        
        # Рассчитываем средний ROI для каждого интервала
        avg_roi_by_interval = {}
        for key in interval_keys:
            data = roi_by_interval[key]
            if data['buyin_sum'] > 0:
                avg_roi_by_interval[key] = (data['profit_sum'] / data['buyin_sum']) * 100
            else:
                avg_roi_by_interval[key] = 0
        
        median_value = median(stack_values) if stack_values else None
        
        return avg_roi_by_interval, median_value

    def _clear_chart_overlays(self):
        """Удаляет вспомогательные элементы (метки и медианную линию) с графика."""
        current_chart = self.chart_view.chart()
        if not current_chart:
            return
        for label in getattr(self.chart_view, "chart_labels", []):
            try:
                current_chart.scene().removeItem(label)
            except Exception:
                pass
        self.chart_view.chart_labels = []
        for line in getattr(self.chart_view, "median_lines", []):
            try:
                current_chart.scene().removeItem(line)
            except Exception:
                pass
        self.chart_view.median_lines = []

    def _update_chart(self, place_dist=None):
        """Обновляет гистограмму распределения мест."""
        if place_dist is None:
            place_dist = self._get_current_distribution()

        # Удаляем элементы предыдущего графика, если они есть
        self._clear_chart_overlays()

        # Проверяем, есть ли данные
        if not place_dist or all(count == 0 for count in place_dist.values()):
            logger.warning("Нет данных для построения гистограммы распределения мест")
            chart = QChart()
            chart.setTitle("Нет данных о финишах на финальном столе")
            chart.setTheme(QChart.ChartTheme.ChartThemeDark)
            chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#18181B")))
            self.chart_view.setChart(chart)
            return
            
        chart = QChart()
        chart.setTitle("")  # Убираем заголовок, так как он уже есть над графиком
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#18181B")))
        chart.legend().setVisible(False)
        
        # Создаем серию стековых баров
        series = QStackedBarSeries()

        # Цветовые палитры для разных типов гистограмм
        colors_ft = [
            "#10B981", "#34D399", "#6EE7B7", "#FCD34D", "#F59E0B", "#EF4444",
            "#DC2626", "#B91C1C", "#991B1B",
        ]

        colors_pre_ft = [
            "#6366F1", "#3B82F6", "#0EA5E9", "#06B6D4", "#0891B2", "#14B8A6",
            "#0D9488", "#0F766E", "#134E4A",
        ]

        # Для общего распределения оттенки идут от красного к зеленому
        colors_all = [
            "#10B981", "#34D399", "#6EE7B7", "#14B8A6", "#0D9488", "#0F766E",
            "#134E4A", "#0891B2", "#06B6D4", "#0EA5E9", "#3B82F6", "#6366F1",
            "#FCD34D", "#F59E0B", "#EF4444", "#DC2626", "#B91C1C", "#991B1B",
        ]
        
        # Цвета для распределения стеков FT - от красного (мало BB) к зеленому (много BB)
        colors_ft_stack = [
            "#EF4444", "#F87171", "#FB923C", "#FDBA74", "#FCD34D", "#FDE047",
            "#FDE68A", "#FBBF24", "#A3E635", "#84CC16", "#65A30D", "#4ADE80",
            "#34D399", "#10B981", "#14B8A6", "#0D9488", "#0F766E", "#134E4A",
            "#0891B2", "#06B6D4", "#0EA5E9", "#3B82F6", "#6366F1",
        ]

        if self.chart_type == 'ft':
            colors = colors_ft
        elif self.chart_type == 'pre_ft':
            colors = colors_pre_ft
        elif self.chart_type in ['ft_stack', 'ft_stack_roi']:
            colors = colors_ft_stack
        else:
            colors = colors_all
        
        # Подсчитываем общее количество финишей для расчета процентов
        total_finishes = sum(place_dist.values())

        # Специальная сортировка для стеков FT
        if self.chart_type in ['ft_stack', 'ft_stack_roi']:
            step = self.ft_stack_step
            categories = ["≤7"]
            for i in range(8, 50, step):
                end = min(i + step - 1, 49)
                categories.append(f"{i}-{end}")
            categories.append("≥50")
            categories = [cat for cat in categories if cat in place_dist]
        else:
            categories = sorted(place_dist.keys())

        # Создаем отдельный QBarSet для каждого места (для всех графиков)
        for idx, place in enumerate(categories):
            bar_set = QBarSet("")

            for cat in categories:
                if cat == place:
                    bar_set.append(place_dist.get(cat, 0))
                else:
                    bar_set.append(0)

            color = QtGui.QColor(colors[idx % len(colors)])
            color.setAlpha(int(255 * 0.65))
            bar_set.setColor(color)

            series.append(bar_set)
        
        # Устанавливаем ширину баров
        series.setBarWidth(0.8)
        
        chart.addSeries(series)
        
        # Настройка оси X (категории)
        axis_x = QBarCategoryAxis()
        axis_x.append([str(c) for c in categories])
        if self.chart_type in ['ft_stack', 'ft_stack_roi']:
            axis_x.setTitleText("Стек (BB)")
        else:
            axis_x.setTitleText("Место")
        axis_x.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_x.setGridLineVisible(False)
        
        # Настройка оси Y (значения)
        axis_y = QValueAxis()
        if self.chart_type == 'ft_stack':
            axis_y.setTitleText("Количество выходов на FT")
        elif self.chart_type == 'ft_stack_roi':
            axis_y.setTitleText("Средний ROI (%)")
        else:
            axis_y.setTitleText("Количество финишей")
        axis_y.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_y.setGridLineColor(QtGui.QColor("#3F3F46"))
        axis_y.setMinorGridLineVisible(False)
        
        # Специальная обработка для ROI графика
        if self.chart_type == 'ft_stack_roi':
            # Для ROI находим минимальное и максимальное значение
            roi_values = list(place_dist.values())
            if roi_values:
                min_roi = min(roi_values)
                max_roi = max(roi_values)
                
                # Функция для поиска красивого шага
                def _nice_step_roi(value_range: float) -> float:
                    if value_range == 0:
                        return 10
                    raw_step = value_range / 10
                    magnitude = 10 ** int(math.floor(math.log10(abs(raw_step))))
                    for m in (1, 2, 2.5, 5, 10):
                        step = m * magnitude
                        if abs(raw_step) <= step:
                            break
                    return step
                
                # Расширяем диапазон с учетом красивых шагов
                value_range = max_roi - min_roi
                if value_range > 0:
                    step = _nice_step_roi(value_range)
                    # Округляем границы до ближайших кратных шагу
                    min_val = math.floor(min_roi / step) * step
                    max_val = math.ceil(max_roi / step) * step
                    # Добавляем небольшой отступ
                    min_val -= step * 0.5
                    max_val += step * 0.5
                else:
                    # Если все значения одинаковые
                    step = 10
                    min_val = min_roi - step
                    max_val = max_roi + step
                
                axis_y.setRange(min_val, max_val)
                # Устанавливаем количество меток
                tick_count = int((max_val - min_val) / step) + 1
                axis_y.setTickCount(min(tick_count, 11))  # Максимум 11 меток
                axis_y.setLabelFormat("%.0f")
            else:
                axis_y.setRange(-100, 100)
                axis_y.setTickCount(11)
                axis_y.setLabelFormat("%.0f")
        else:
            max_count = max(place_dist.values()) if place_dist.values() else 1

            if max_count <= 10:
                axis_y.setRange(0, max_count)
                axis_y.setTickCount(max_count + 1)
            else:
                def _nice_step(value: int) -> int:
                    raw_step = value / 10
                    magnitude = 10 ** int(math.floor(math.log10(raw_step)))
                    for m in (1, 2, 5, 10):
                        step = m * magnitude
                        if raw_step <= step:
                            break
                    if step >= 10 and step % 10 != 0:
                        step = math.ceil(step / 10) * 10
                    return step

                step = _nice_step(max_count)
                max_val = int(math.ceil(max_count / step) * step)
                axis_y.setRange(0, max_val)
                axis_y.setTickCount(max_val // step + 1)

            axis_y.setLabelFormat("%d")
        
        # Привязываем оси к графику
        chart.addAxis(axis_x, QtCore.Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, QtCore.Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        
        # Устанавливаем отступы для графика
        chart.setMargins(QtCore.QMargins(10, 10, 10, 10))
        
        # Устанавливаем график в view
        self.chart_view.setChart(chart)
        
        # Добавляем кастомные текстовые метки с процентами после установки графика
        if total_finishes > 0 or self.chart_type == 'ft_stack_roi':
            # Подключаем обработчик изменения геометрии
            self.chart_view.chart().plotAreaChanged.connect(
                lambda: self._update_percentage_labels_position(chart, place_dist, total_finishes, self.chart_type)
            )
            # Первоначальное размещение меток
            QtCore.QTimer.singleShot(100, lambda: self._add_percentage_labels(chart, place_dist, total_finishes, self.chart_type))
            if self.chart_type == 'ft_stack':
                self.chart_view.chart().plotAreaChanged.connect(
                    lambda: self._update_median_line_position(chart, place_dist)
                )
                QtCore.QTimer.singleShot(100, lambda: self._add_median_line(chart, place_dist))
    
    def _add_percentage_labels(self, chart, place_dist, total_finishes, chart_type=None):
        """Добавляет текстовые метки с процентами над барами."""
        # Удаляем старые метки, если есть
        for label in getattr(self.chart_view, 'chart_labels', []):
            chart.scene().removeItem(label)
        self.chart_view.chart_labels = []
        
        # Создаем новые метки
        plot_area = chart.plotArea()
        
        # Специальная сортировка для стеков FT
        if chart_type in ['ft_stack', 'ft_stack_roi']:
            step = self.ft_stack_step
            categories = ["≤7"]
            for i in range(8, 50, step):
                end = min(i + step - 1, 49)
                categories.append(f"{i}-{end}")
            categories.append("≥50")
            categories = [cat for cat in categories if cat in place_dist]
        else:
            categories = sorted(place_dist.keys())
            
        num_places = len(categories)
        bar_width = plot_area.width() / num_places

        # Получаем максимальное значение по оси Y, чтобы корректно рассчитывать
        # высоту баров. Это значение соответствует диапазону, заданному для
        # оси графика, поэтому вычисленные координаты будут совпадать с
        # реальным размером столбцов.
        # В Qt6 метод axisY() отсутствует, поэтому используем общий способ
        # получения осей графика
        if hasattr(chart, "axisY"):
            axis_y = chart.axisY()
        else:
            vertical_axes = chart.axes(QtCore.Qt.Orientation.Vertical)
            axis_y = vertical_axes[0] if vertical_axes else None

        try:
            y_max = float(axis_y.max()) if axis_y is not None else None
        except Exception:
            y_max = None

        if y_max is None:
            # На случай, если метод или свойство отличаются в версии Qt
            # используем максимальное значение из данных как резервное
            y_max = float(max(place_dist.values())) if place_dist else 1

        for idx, place in enumerate(categories):
            count = place_dist.get(place, 0)
            if count > 0 or (chart_type == 'ft_stack_roi' and count != 0):
                # Для ROI графика показываем значение ROI, для остальных - проценты
                if chart_type == 'ft_stack_roi':
                    text = QtWidgets.QGraphicsTextItem(f"{count:.0f}%")
                else:
                    percentage = (count / total_finishes) * 100
                    text = QtWidgets.QGraphicsTextItem(f"{percentage:.1f}%")
                text.setDefaultTextColor(QtGui.QColor("#FAFAFA"))
                # Увеличиваем шрифт на 30% по сравнению с исходным
                text.setFont(QtGui.QFont("Arial", 13, QtGui.QFont.Weight.Bold))

                # Вычисляем позицию
                x_pos = (
                    plot_area.left()
                    + bar_width * (idx + 0.5)
                    - text.boundingRect().width() / 2
                )

                # Для ROI графика нужна особая обработка, так как значения могут быть отрицательными
                if chart_type == 'ft_stack_roi':
                    # Получаем минимальное и максимальное значение по оси Y
                    if hasattr(chart, "axisY"):
                        axis_y = chart.axisY()
                    else:
                        vertical_axes = chart.axes(QtCore.Qt.Orientation.Vertical)
                        axis_y = vertical_axes[0] if vertical_axes else None
                    
                    y_min = float(axis_y.min()) if axis_y else 0
                    y_max = float(axis_y.max()) if axis_y else 0
                    y_range = y_max - y_min
                    
                    # Позиция нуля на графике
                    zero_ratio = -y_min / y_range if y_range else 0.5
                    zero_y = plot_area.bottom() - (plot_area.height() * zero_ratio)
                    
                    # Позиция верха бара
                    value_ratio = (count - y_min) / y_range if y_range else 0
                    bar_top = plot_area.bottom() - (plot_area.height() * value_ratio)
                else:
                    # Для остальных графиков используем старую логику
                    bar_height_ratio = count / y_max if y_max else 0
                    bar_top = plot_area.bottom() - (plot_area.height() * bar_height_ratio)
                
                label_height = text.boundingRect().height()

                # Для гистограммы стеков FT всегда размещаем метки сверху баров
                if chart_type == 'ft_stack':
                    # Фиксированный отступ сверху бара
                    y_pos = bar_top - label_height - 5
                elif chart_type == 'ft_stack_roi':
                    # Для ROI графика размещаем метки с учетом направления бара
                    if count < 0:
                        # Для отрицательных значений добавляем больший отступ
                        y_pos = bar_top - label_height - 20
                    else:
                        # Для положительных значений стандартный отступ
                        y_pos = bar_top - label_height - 5
                else:
                    # Для остальных гистограмм используем адаптивную логику
                    inside_offset = 3
                    bar_height = plot_area.bottom() - bar_top

                    if bar_height >= label_height + inside_offset:
                        # Размещаем метку внутри бара
                        y_pos = bar_top + inside_offset
                    else:
                        # Бар слишком низкий, помещаем метку сверху с отступом 12px
                        y_pos = bar_top - label_height - 12

                shadow = QtWidgets.QGraphicsDropShadowEffect()
                shadow.setBlurRadius(10)
                shadow.setOffset(0, 0)
                shadow.setColor(QtGui.QColor("#000000"))
                text.setGraphicsEffect(shadow)

                text.setPos(x_pos, y_pos)
                chart.scene().addItem(text)
                self.chart_view.chart_labels.append(text)
    
    def _update_percentage_labels_position(self, chart, place_dist, total_finishes, chart_type=None):
        """Обновляет позиции меток при изменении размера графика."""
        self._add_percentage_labels(chart, place_dist, total_finishes, chart_type)

    def _add_median_line(self, chart, place_dist):
        """Отрисовывает вертикальную линию медианного значения стеков FT."""
        # Удаляем старую линию, если есть
        for line in getattr(self.chart_view, 'median_lines', []):
            chart.scene().removeItem(line)
        self.chart_view.median_lines = []

        median_value = getattr(self, 'ft_stack_median', None)
        if median_value is None:
            return

        plot_area = chart.plotArea()

        # Список категорий в порядке следования
        step = self.ft_stack_step
        categories = ["≤7"]
        for i in range(8, 50, step):
            end = min(i + step - 1, 49)
            categories.append(f"{i}-{end}")
        categories.append("≥50")

        num_places = len(categories)
        if num_places == 0:
            return

        bar_width = plot_area.width() / num_places

        if median_value <= 7:
            idx = categories.index("≤7")
        elif median_value >= 50:
            idx = categories.index("≥50")
        else:
            interval_start = ((int((median_value - 8) / step)) * step) + 8
            interval_start = max(8, interval_start)
            interval_end = min(interval_start + step - 1, 49)
            interval_key = f"{interval_start}-{interval_end}"
            idx = categories.index(interval_key)

        x_pos = plot_area.left() + bar_width * (idx + 0.5)

        line = QtWidgets.QGraphicsLineItem(
            x_pos, plot_area.top(), x_pos, plot_area.bottom()
        )
        pen = QtGui.QPen(QtGui.QColor("#FBBF24"))
        pen.setWidth(2)
        line.setPen(pen)
        line.setZValue(5)

        chart.scene().addItem(line)
        self.chart_view.median_lines.append(line)

    def _update_median_line_position(self, chart, place_dist):
        """Обновляет позицию медианной линии при изменении размера графика."""
        self._add_median_line(chart, place_dist)

    def _get_current_distribution(self):
        """Возвращает распределение в зависимости от выбранного типа графика."""
        if self.chart_type == 'pre_ft':
            return getattr(self, 'place_dist_pre_ft', {})
        if self.chart_type == 'all':
            return getattr(self, 'place_dist_all', {})
        if self.chart_type == 'ft_stack':
            return getattr(self, 'ft_stack_dist', {})
        if self.chart_type == 'ft_stack_roi':
            return getattr(self, 'ft_stack_roi_dist', {})
        return getattr(self, 'place_dist_ft', {})

    def _on_chart_selector_changed(self, index: int):
        types = ['ft', 'pre_ft', 'all', 'ft_stack', 'ft_stack_roi']
        self.chart_type = types[index]
        if self.chart_type == 'ft':
            self.chart_header.setText("Распределение финишных мест на финальном столе")
            self.ft_stack_density_selector.setVisible(False)
        elif self.chart_type == 'pre_ft':
            self.chart_header.setText("Распределение мест до финального стола (10-18)")
            self.ft_stack_density_selector.setVisible(False)
        elif self.chart_type == 'all':
            self.chart_header.setText("Распределение финишных мест (1-18)")
            self.ft_stack_density_selector.setVisible(False)
        elif self.chart_type == 'ft_stack':
            self.chart_header.setText("Распределение стеков выхода на FT (в больших блайндах)")
            self.ft_stack_density_selector.setVisible(True)
        else:  # ft_stack_roi
            self.chart_header.setText("Средний ROI по стекам выхода на FT")
            self.ft_stack_density_selector.setVisible(True)

        self._update_chart(self._get_current_distribution())

    def _on_density_selector_changed(self, index: int):
        """Меняет шаг интервалов гистограммы стеков FT."""
        steps = [2, 5, 10]
        self.ft_stack_step = steps[index]
        if self._current_tournaments:
            self.ft_stack_dist, self.ft_stack_median = self._calculate_ft_stack_distribution(
                self._current_tournaments, step=self.ft_stack_step
            )
            self.ft_stack_roi_dist, _ = self._calculate_ft_stack_roi_distribution(
                self._current_tournaments, step=self.ft_stack_step
            )
        if self.chart_type in ['ft_stack', 'ft_stack_roi']:
            self._update_chart(self._get_current_distribution())

