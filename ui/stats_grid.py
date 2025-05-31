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
    AvgFinishPlaceStat,
    AvgFinishPlaceFTStat,
    AvgFinishPlaceNoFTStat,
    PreFTKOStat,
    IncompleteFTPercentStat,
    KOLuckStat,
    ROIAdjustedStat,
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
                padding: 4px 8px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 12px;
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
                font-size: 18px;
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


class SpecialStatCard(QtWidgets.QFrame):
    """Специальная карточка для статов с переносом строки (FT стек и Early FT KO)."""
    
    def __init__(self, title: str, value: str = "-", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QtWidgets.QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                background-color: #27272A;
                border-radius: 8px;
                padding: 4px 8px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Верхняя строка с заголовком и значением
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(4)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 12px;
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
                font-size: 18px;
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
        if self.subtitle_label and subtitle:
            self.subtitle_label.setText(subtitle)
        elif subtitle and not self.subtitle_label:
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
        self._session_map = {}
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
        content_layout.setSpacing(4)
        
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

        header_layout.addWidget(QtWidgets.QLabel("Бай-ин:"))
        self.buyin_filter = QtWidgets.QComboBox()
        self.buyin_filter.setMinimumWidth(100)
        self.buyin_filter.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.buyin_filter)

        header_layout.addWidget(QtWidgets.QLabel("Сессия:"))
        self.session_filter = QtWidgets.QComboBox()
        self.session_filter.setMinimumWidth(140)
        self.session_filter.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.session_filter)

        content_layout.addLayout(header_layout)

        self._update_filters()
        
        # Сетка карточек статистики
        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setSpacing(3)
        
        # Создаем карточки для основных показателей
        self.cards = {
            'tournaments': StatCard("Турниров сыграно", "-"),
            'knockouts': StatCard("Всего нокаутов", "-"),
            'avg_ko': StatCard("Среднее KO за турнир", "-"),
            'roi': StatCard("ROI", "-"),
            'itm': StatCard("ITM%", "-"),
            'ft_reach': StatCard("% Достижения FT", "-"),
            'avg_ft_stack': SpecialStatCard("Средний стек на FT", "-"),
            'early_ft_ko': SpecialStatCard("KO в ранней FT", "-"),
            'early_ft_bust': SpecialStatCard("Вылеты ранней FT", "-"),
            'avg_place_all': StatCard("Среднее место (все)", "-"),
            'avg_place_ft': StatCard("Среднее место (FT)", "-"),
            'avg_place_no_ft': StatCard("Среднее место (не FT)", "-"),
            'pre_ft_ko': StatCard("KO до FT", "-"),
            'incomplete_ft': StatCard("Неполные финалки", "-"),
        }
        
        # Размещаем карточки в сетке (4 колонки)
        positions = [
            ('tournaments', 0, 0), ('knockouts', 0, 1), ('avg_ko', 0, 2), ('roi', 0, 3),
            ('itm', 1, 0), ('ft_reach', 1, 1), ('avg_ft_stack', 1, 2), ('early_ft_ko', 1, 3),
            ('avg_place_all', 2, 0), ('avg_place_ft', 2, 1), ('avg_place_no_ft', 2, 2), ('early_ft_bust', 2, 3),
            ('pre_ft_ko', 3, 0), ('incomplete_ft', 3, 1),
        ]
        
        for key, row, col in positions:
            if key in self.cards:
                stats_grid.addWidget(self.cards[key], row, col)
            
        content_layout.addLayout(stats_grid)
        
        # Разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 5px 0; }")
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

        content_layout.addWidget(self.chart_header)

        # Переключатель типа гистограммы
        self.chart_selector = QtWidgets.QComboBox()
        self.chart_selector.addItems([
            "Финальный стол",
            "До финального стола",
            "Все места",
        ])
        self.chart_selector.currentIndexChanged.connect(self._on_chart_selector_changed)
        self.chart_type = 'ft'
        content_layout.addWidget(self.chart_selector, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        
        # Создаем виджет для графика
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(315)
        self.chart_view.setMaximumHeight(405)
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
            'x1.5': StatCard("KO x1.5", "-"),
            'x2': StatCard("KO x2", "-"),
            'x10': StatCard("KO x10", "-"),
            'x100': StatCard("KO x100", "-"),
            'x1000': StatCard("KO x1000", "-"),
            'x10000': StatCard("KO x10000", "-"),
        }

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
        """Реагирует на изменение фильтров и перезагружает данные."""
        buyin = self.buyin_filter.currentText()
        self.current_buyin_filter = float(buyin) if buyin and buyin != "Все" else None
        session_name = self.session_filter.currentText()
        self.current_session_id = (
            self._session_map.get(session_name) if session_name and session_name != "Все" else None
        )
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
        
        def load_data():
            tournaments = self.app_service.tournament_repo.get_all_tournaments(
                session_id=self.current_session_id,
                buyin_filter=self.current_buyin_filter,
            )
            if self.current_session_id:
                ft_hands = self.app_service.ft_hand_repo.get_hands_by_session(self.current_session_id)
            else:
                ft_hands = self.app_service.ft_hand_repo.get_all_hands()
            if self.current_buyin_filter is not None:
                allowed_ids = {t.tournament_id for t in tournaments}
                ft_hands = [h for h in ft_hands if h.tournament_id in allowed_ids]

            overall_stats = self._compute_overall_stats_filtered(tournaments, ft_hands)

            place_dist = {i: 0 for i in range(1, 10)}
            place_dist_pre_ft = {i: 0 for i in range(10, 19)}
            place_dist_all = {i: 0 for i in range(1, 19)}
            for t in tournaments:
                if t.finish_place is None:
                    continue
                if 1 <= t.finish_place <= 9:
                    place_dist[t.finish_place] += 1
                if 10 <= t.finish_place <= 18:
                    place_dist_pre_ft[t.finish_place] += 1
                if 1 <= t.finish_place <= 18:
                    place_dist_all[t.finish_place] += 1

            roi_value = ROIStat().compute([], [], [], overall_stats).get('roi', 0.0)
            itm_value = ITMStat().compute(tournaments, [], [], overall_stats).get('itm_percent', 0.0)
            ft_reach = FinalTableReachStat().compute(tournaments, [], [], overall_stats).get('final_table_reach_percent', 0.0)
            avg_stack_res = AvgFTInitialStackStat().compute(tournaments, [], [], overall_stats)
            avg_chips = avg_stack_res.get('avg_ft_initial_stack_chips', 0.0)
            avg_bb = avg_stack_res.get('avg_ft_initial_stack_bb', 0.0)
            early_res = EarlyFTKOStat().compute(tournaments, ft_hands, [], overall_stats)
            early_ko = early_res.get('early_ft_ko_count', 0)
            early_ko_per = early_res.get('early_ft_ko_per_tournament', 0.0)
            pre_ft_ko_res = PreFTKOStat().compute(tournaments, ft_hands, [], overall_stats)
            pre_ft_ko_count = pre_ft_ko_res.get('pre_ft_ko_count', 0.0)
            incomplete_ft_percent = IncompleteFTPercentStat().compute(tournaments, ft_hands, [], overall_stats).get('incomplete_ft_percent', 0)
            ko_luck_value = KOLuckStat().compute(tournaments, [], [], overall_stats).get('ko_luck', 0.0)
            roi_adj_value = ROIAdjustedStat().compute(tournaments, ft_hands, [], overall_stats).get('roi_adj', 0.0)
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
                'roi': roi_value,
                'itm': itm_value,
                'ft_reach': ft_reach,
                'avg_chips': avg_chips,
                'avg_bb': avg_bb,
                'early_ko': early_ko,
                'early_ko_per': early_ko_per,
                'pre_ft_ko_count': pre_ft_ko_count,
                'incomplete_ft_percent': incomplete_ft_percent,
                'avg_place_all': avg_all,
                'avg_place_ft': avg_ft,
                'avg_place_no_ft': avg_no_ft,
                'ko_luck': ko_luck_value,
                'roi_adj': roi_adj_value,
            }
        thread_manager.run_in_thread(
            widget_id=str(id(self)),
            fn=load_data,
            callback=self._on_data_loaded,
            error_callback=lambda e: logger.error(f"Ошибка загрузки данных StatsGrid: {e}"),
            owner=self
        )
        
    def _on_data_loaded(self, data: dict):
        """Применяет загруженные данные к UI."""
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

            bust_result = EarlyFTBustStat().compute(all_tournaments, [], [], overall_stats)
            logger.debug(f"Early FT Bust result: {bust_result}")
            bust_count = bust_result.get('early_ft_bust_count', 0)
            bust_per = bust_result.get('early_ft_bust_per_tournament', 0.0)
            self.cards['early_ft_bust'].update_value(
                str(bust_count),
                f"{bust_per:.2f} за турнир с FT"
            )
            logger.debug(f"Обновлена карточка early_ft_bust: {bust_count} / {bust_per:.2f}")
            
            self.bigko_cards['x1.5'].update_value(str(overall_stats.big_ko_x1_5))
            self.bigko_cards['x2'].update_value(str(overall_stats.big_ko_x2))
            self.bigko_cards['x10'].update_value(str(overall_stats.big_ko_x10))
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
            # Обновляем текст над карточкой KO x10
            if overall_stats.big_ko_x10 > 0:
                per_tourn = overall_stats.total_tournaments / overall_stats.big_ko_x10
                per_ko = overall_stats.total_knockouts / overall_stats.big_ko_x10 if overall_stats.total_knockouts > 0 else 0
                info_text = f"1 на {per_tourn:.0f} турниров\n1 на {per_ko:.0f} нокаутов"
            else:
                info_text = "нет"
            self.bigko_x10_info_label.setText(info_text)
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

            incomplete_percent = data.get('incomplete_ft_percent', 0)
            self.cards['incomplete_ft'].update_value(f"{incomplete_percent}%")
            logger.debug(f"Обновлена карточка incomplete_ft: {incomplete_percent}%")
            

            self.place_dist_ft = data['place_dist']
            self.place_dist_pre_ft = data.get('place_dist_pre_ft', {})
            self.place_dist_all = data.get('place_dist_all', {})
            self._update_chart(self._get_current_distribution())
            self.overallStatsChanged.emit(overall_stats)
            logger.debug("=== Конец reload StatsGrid ===")

        finally:
            # Скрываем индикатор загрузки
            if getattr(self, "_show_overlay", False):
                self.hide_loading_overlay()

    def _compute_overall_stats_filtered(self, tournaments, ft_hands):
        """Вычисляет агрегированную статистику по отфильтрованным данным."""
        stats = OverallStats()
        stats.total_tournaments = len(tournaments)
        ft_tournaments = [t for t in tournaments if t.reached_final_table]
        stats.total_final_tables = len(ft_tournaments)
        stats.total_buy_in = sum(t.buyin for t in tournaments if t.buyin is not None)
        stats.total_prize = sum(t.payout for t in tournaments if t.payout is not None)
        stats.total_knockouts = sum(t.ko_count for t in tournaments)
        stats.avg_ko_per_tournament = (
            stats.total_knockouts / stats.total_tournaments if stats.total_tournaments else 0.0
        )
        stats.final_table_reach_percent = (
            stats.total_final_tables / stats.total_tournaments * 100 if stats.total_tournaments else 0.0
        )
        ft_chips = [t.final_table_initial_stack_chips for t in ft_tournaments if t.final_table_initial_stack_chips is not None]
        stats.avg_ft_initial_stack_chips = sum(ft_chips) / len(ft_chips) if ft_chips else 0.0
        ft_bb = [t.final_table_initial_stack_bb for t in ft_tournaments if t.final_table_initial_stack_bb is not None]
        stats.avg_ft_initial_stack_bb = sum(ft_bb) / len(ft_bb) if ft_bb else 0.0
        early_hands = [h for h in ft_hands if h.is_early_final]
        stats.early_ft_ko_count = sum(h.hero_ko_this_hand for h in early_hands)
        stats.early_ft_ko_per_tournament = (
            stats.early_ft_ko_count / stats.total_final_tables if stats.total_final_tables else 0.0
        )
        stats.early_ft_bust_count = sum(
            1 for t in ft_tournaments if t.finish_place is not None and 6 <= t.finish_place <= 9
        )
        stats.early_ft_bust_per_tournament = (
            stats.early_ft_bust_count / stats.total_final_tables if stats.total_final_tables else 0.0
        )
        stats.pre_ft_ko_count = sum(h.pre_ft_ko for h in ft_hands)
        first_hands = {}
        for hand in ft_hands:
            if hand.table_size == config.FINAL_TABLE_SIZE:
                saved = first_hands.get(hand.tournament_id)
                if saved is None or hand.hand_number < saved.hand_number:
                    first_hands[hand.tournament_id] = hand
        stats.incomplete_ft_count = sum(
            1 for h in first_hands.values() if h.players_count < config.FINAL_TABLE_SIZE
        )
        stats.incomplete_ft_percent = (
            int(round(stats.incomplete_ft_count / stats.total_final_tables * 100))
            if stats.total_final_tables
            else 0
        )
        all_places = [t.finish_place for t in tournaments if t.finish_place is not None]
        stats.avg_finish_place = sum(all_places) / len(all_places) if all_places else 0.0
        ft_places = [
            t.finish_place
            for t in ft_tournaments
            if t.finish_place is not None and 1 <= t.finish_place <= 9
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
        stats.pre_ft_ko_count = round(stats.pre_ft_ko_count, 2)
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
        
    def _update_chart(self, place_dist=None):
        """Обновляет гистограмму распределения мест."""
        if place_dist is None:
            place_dist = self._get_current_distribution()
        
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

        if self.chart_type == 'ft':
            colors = colors_ft
        elif self.chart_type == 'pre_ft':
            colors = colors_pre_ft
        else:
            colors = colors_all
        
        # Подсчитываем общее количество финишей для расчета процентов
        total_finishes = sum(place_dist.values())

        categories = sorted(place_dist.keys())

        # Создаем отдельный QBarSet для каждого места
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
        axis_x.setTitleText("Место")
        axis_x.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_x.setGridLineVisible(False)
        
        # Настройка оси Y (значения)
        axis_y = QValueAxis()
        axis_y.setTitleText("Количество финишей")
        axis_y.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_y.setGridLineColor(QtGui.QColor("#3F3F46"))
        axis_y.setMinorGridLineVisible(False)
        
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
        if total_finishes > 0:
            # Подключаем обработчик изменения геометрии
            self.chart_view.chart().plotAreaChanged.connect(
                lambda: self._update_percentage_labels_position(chart, place_dist, total_finishes)
            )
            # Первоначальное размещение меток
            QtCore.QTimer.singleShot(100, lambda: self._add_percentage_labels(chart, place_dist, total_finishes))
    
    def _add_percentage_labels(self, chart, place_dist, total_finishes):
        """Добавляет текстовые метки с процентами над барами."""
        # Удаляем старые метки, если есть
        for label in getattr(self.chart_view, 'chart_labels', []):
            chart.scene().removeItem(label)
        self.chart_view.chart_labels = []
        
        # Создаем новые метки
        plot_area = chart.plotArea()
        categories = sorted(place_dist.keys())
        num_places = len(categories)
        bar_width = plot_area.width() / num_places

        for idx, place in enumerate(categories):
            count = place_dist.get(place, 0)
            if count > 0:
                percentage = (count / total_finishes) * 100
                
                text = QtWidgets.QGraphicsTextItem(f"{percentage:.1f}%")
                text.setDefaultTextColor(QtGui.QColor("#FAFAFA"))
                text.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Weight.Bold))
                
                # Вычисляем позицию
                x_pos = plot_area.left() + bar_width * (idx + 0.5) - text.boundingRect().width() / 2
                max_y_value = max(place_dist.values()) * 1.1
                bar_height_ratio = count / max_y_value
                # Немного поднимаем процентные метки, чтобы они не перекрывались с барами
                y_pos = plot_area.bottom() - (plot_area.height() * bar_height_ratio) - text.boundingRect().height() - 8
                
                text.setPos(x_pos, y_pos)
                chart.scene().addItem(text)
                self.chart_view.chart_labels.append(text)
    
    def _update_percentage_labels_position(self, chart, place_dist, total_finishes):
        """Обновляет позиции меток при изменении размера графика."""
        self._add_percentage_labels(chart, place_dist, total_finishes)

    def _get_current_distribution(self):
        """Возвращает распределение в зависимости от выбранного типа графика."""
        if self.chart_type == 'pre_ft':
            return getattr(self, 'place_dist_pre_ft', {})
        if self.chart_type == 'all':
            return getattr(self, 'place_dist_all', {})
        return getattr(self, 'place_dist_ft', {})

    def _on_chart_selector_changed(self, index: int):
        types = ['ft', 'pre_ft', 'all']
        self.chart_type = types[index]
        if self.chart_type == 'ft':
            self.chart_header.setText("Распределение финишных мест на финальном столе")
        elif self.chart_type == 'pre_ft':
            self.chart_header.setText("Распределение мест до финального стола (10-18)")
        else:
            self.chart_header.setText("Распределение финишных мест (1-18)")

        self._update_chart(self._get_current_distribution())
