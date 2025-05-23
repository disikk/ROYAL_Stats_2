# -*- coding: utf-8 -*-

"""
Компонент для отображения общей статистики и графиков.
Отображает карточки с ключевыми показателями и гистограмму распределения мест.
"""

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
import logging
from typing import Dict, List, Any

import config
from application_service import ApplicationService
from models import OverallStats

# Импортируем функции стилизации
from ui.app_style import format_money, format_percentage, apply_cell_color_by_value

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
)

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
                border-radius: 12px;
                padding: 16px;
                border: 1px solid #3F3F46;
            }
            QFrame:hover {
                border: 1px solid #52525B;
                background-color: #2D2D30;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Заголовок
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #A1A1AA;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Значение
        self.value_label = QtWidgets.QLabel(value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FAFAFA;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.value_label)
        
        # Подзаголовок (опционально)
        if subtitle:
            self.subtitle_label = QtWidgets.QLabel(subtitle)
            self.subtitle_label.setStyleSheet("""
                QLabel {
                    color: #71717A;
                    font-size: 12px;
                }
            """)
            layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None
            
        layout.addStretch()
        
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
                    font-size: 12px;
                }
            """)
            self.layout().insertWidget(2, self.subtitle_label)


class StatsGrid(QtWidgets.QWidget):
    """Виджет с сеткой статистических показателей и графиками."""
    
    def __init__(self, app_service: ApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        self._init_ui()
        
    def _init_ui(self):
        """Инициализирует UI компоненты."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Заголовок
        header = QtWidgets.QLabel("Общая статистика")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 16px;
            }
        """)
        main_layout.addWidget(header)
        
        # Сетка карточек статистики
        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setSpacing(12)
        
        # Создаем карточки для основных показателей
        self.cards = {
            'tournaments': StatCard("Турниров сыграно", "-"),
            'knockouts': StatCard("Всего нокаутов", "-"),
            'avg_ko': StatCard("Среднее KO за турнир", "-"),
            'roi': StatCard("ROI", "-"),
            'itm': StatCard("ITM%", "-"),
            'ft_reach': StatCard("% Достижения FT", "-"),
            'avg_ft_stack': StatCard("Средний стек на FT", "-", "в фишках / BB"),
            'early_ft_ko': StatCard("KO в ранней FT", "-", "9-6 игроков"),
        }
        
        # Размещаем карточки в сетке (4 колонки)
        positions = [
            ('tournaments', 0, 0), ('knockouts', 0, 1), ('avg_ko', 0, 2), ('roi', 0, 3),
            ('itm', 1, 0), ('ft_reach', 1, 1), ('avg_ft_stack', 1, 2), ('early_ft_ko', 1, 3),
        ]
        
        for key, row, col in positions:
            stats_grid.addWidget(self.cards[key], row, col)
            
        main_layout.addLayout(stats_grid)
        
        # Разделитель
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { background-color: #3F3F46; max-height: 1px; margin: 24px 0; }")
        main_layout.addWidget(separator)
        
        # График распределения мест
        chart_header = QtWidgets.QLabel("Распределение финишных мест на финальном столе")
        chart_header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #FAFAFA;
                margin-bottom: 12px;
            }
        """)
        main_layout.addWidget(chart_header)
        
        # Создаем виджет для графика
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(400)
        main_layout.addWidget(self.chart_view)
        
        # Карточки для Big KO
        bigko_header = QtWidgets.QLabel("Статистика больших нокаутов")
        bigko_header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #FAFAFA;
                margin-top: 24px;
                margin-bottom: 12px;
            }
        """)
        main_layout.addWidget(bigko_header)
        
        bigko_grid = QtWidgets.QGridLayout()
        bigko_grid.setSpacing(12)
        
        self.bigko_cards = {
            'x1.5': StatCard("KO x1.5", "-"),
            'x2': StatCard("KO x2", "-"),
            'x10': StatCard("KO x10", "-"),
            'x100': StatCard("KO x100", "-"),
            'x1000': StatCard("KO x1000", "-"),
            'x10000': StatCard("KO x10000", "-"),
        }
        
        bigko_positions = [
            ('x1.5', 0, 0), ('x2', 0, 1), ('x10', 0, 2),
            ('x100', 0, 3), ('x1000', 0, 4), ('x10000', 0, 5),
        ]
        
        for key, row, col in bigko_positions:
            bigko_grid.addWidget(self.bigko_cards[key], row, col)
            
        main_layout.addLayout(bigko_grid)
        main_layout.addStretch()
        
    def reload(self):
        """Перезагружает все данные из ApplicationService."""
        logger.debug("Обновление UI StatsGrid...")
        
        # Получаем общую статистику
        overall_stats = self.app_service.get_overall_stats()
        
        # Получаем все турниры и руки для плагинов
        all_tournaments = self.app_service.get_all_tournaments()
        
        # Обновляем основные карточки
        self.cards['tournaments'].update_value(str(overall_stats.total_tournaments))
        self.cards['knockouts'].update_value(str(overall_stats.total_knockouts))
        self.cards['avg_ko'].update_value(f"{overall_stats.avg_ko_per_tournament:.2f}")
        
        # ROI
        roi_result = ROIStat().compute([], [], [], overall_stats)
        roi_value = roi_result.get('roi', 0.0)
        roi_text = f"{roi_value:+.1f}%"
        self.cards['roi'].update_value(roi_text)
        apply_cell_color_by_value(self.cards['roi'].value_label, roi_value)
        
        # ITM%
        itm_result = ITMStat().compute(all_tournaments, [], [], overall_stats)
        itm_value = itm_result.get('itm_percent', 0.0)
        self.cards['itm'].update_value(f"{itm_value:.1f}%")
        
        # % Достижения FT
        ft_reach_result = FinalTableReachStat().compute(all_tournaments, [], [], overall_stats)
        ft_reach_value = ft_reach_result.get('final_table_reach_percent', 0.0)
        self.cards['ft_reach'].update_value(f"{ft_reach_value:.1f}%")
        
        # Средний стек на FT
        avg_ft_stack_result = AvgFTInitialStackStat().compute(all_tournaments, [], [], overall_stats)
        avg_chips = avg_ft_stack_result.get('avg_ft_initial_stack_chips', 0.0)
        avg_bb = avg_ft_stack_result.get('avg_ft_initial_stack_bb', 0.0)
        self.cards['avg_ft_stack'].update_value(
            f"{avg_chips:,.0f}",
            f"{avg_chips:,.0f} фишек / {avg_bb:.1f} BB"
        )
        
        # Early FT KO
        early_ft_result = EarlyFTKOStat().compute([], [], [], overall_stats)
        early_ko_count = early_ft_result.get('early_ft_ko_count', 0)
        early_ko_per = early_ft_result.get('early_ft_ko_per_tournament', 0.0)
        self.cards['early_ft_ko'].update_value(
            str(early_ko_count),
            f"{early_ko_per:.2f} за турнир с FT"
        )
        
        # Обновляем Big KO карточки
        self.bigko_cards['x1.5'].update_value(str(overall_stats.big_ko_x1_5))
        self.bigko_cards['x2'].update_value(str(overall_stats.big_ko_x2))
        self.bigko_cards['x10'].update_value(str(overall_stats.big_ko_x10))
        self.bigko_cards['x100'].update_value(str(overall_stats.big_ko_x100))
        self.bigko_cards['x1000'].update_value(str(overall_stats.big_ko_x1000))
        self.bigko_cards['x10000'].update_value(str(overall_stats.big_ko_x10000))
        
        # Обновляем гистограмму
        self._update_chart()
        
    def _update_chart(self):
        """Обновляет гистограмму распределения мест."""
        place_dist = self.app_service.get_place_distribution()
        
        # Проверяем, есть ли данные
        if not place_dist or all(count == 0 for count in place_dist.values()):
            logger.warning("Нет данных для построения гистограммы распределения мест")
            # Показываем пустой график с сообщением
            chart = QChart()
            chart.setTitle("Нет данных о финишах на финальном столе")
            chart.setTheme(QChart.ChartTheme.ChartThemeDark)
            chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#18181B")))
            self.chart_view.setChart(chart)
            return
        
        # Создаем новый график
        chart = QChart()
        chart.setTitle("")  # Убираем заголовок, так как он уже есть над графиком
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#18181B")))
        chart.legend().setVisible(False)
        
        # Создаем серию данных
        series = QBarSeries()
        
        # Цвета для разных мест (от зеленого к красному)
        colors = [
            "#10B981",  # 1 место - ярко-зеленый
            "#34D399",  # 2 место - зеленый
            "#6EE7B7",  # 3 место - светло-зеленый
            "#FCD34D",  # 4 место - желтый
            "#F59E0B",  # 5 место - оранжевый
            "#EF4444",  # 6 место - красный
            "#DC2626",  # 7 место - темно-красный
            "#B91C1C",  # 8 место - еще темнее
            "#991B1B",  # 9 место - самый темный красный
        ]
        
        # Создаем отдельный BarSet для каждого места, чтобы можно было задать цвет
        categories = []
        for place in range(1, 10):
            count = place_dist.get(place, 0)
            bar_set = QBarSet(str(place))
            bar_set.append(count)
            bar_set.setColor(QtGui.QColor(colors[place-1]))
            series.append(bar_set)
            categories.append(str(place))
        
        chart.addSeries(series)
        
        # Настраиваем оси
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setTitleText("Место")
        axis_x.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_x.setGridLineVisible(False)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("Количество финишей")
        axis_y.setLabelsColor(QtGui.QColor("#E4E4E7"))
        axis_y.setGridLineColor(QtGui.QColor("#3F3F46"))
        axis_y.setMinorGridLineVisible(False)
        
        # Определяем максимум для оси Y
        max_count = max(place_dist.values())
        axis_y.setRange(0, max_count * 1.1)  # Добавляем 10% сверху
        
        # Устанавливаем целочисленные метки
        if max_count <= 10:
            axis_y.setTickCount(max_count + 1)
        else:
            axis_y.setTickCount(min(11, max_count // 5 + 1))  # Максимум 11 меток
        axis_y.setLabelFormat("%d")  # Целые числа
        
        chart.addAxis(axis_x, QtCore.Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, QtCore.Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        
        # Устанавливаем график в view
        self.chart_view.setChart(chart)